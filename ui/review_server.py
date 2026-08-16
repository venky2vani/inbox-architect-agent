"""FastAPI server for the Inbox Architect review UI."""

import asyncio
import json
import logging
import os
import queue
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ui.review_runner import ReviewBatch, ReviewRunner

logger = logging.getLogger(__name__)

app = FastAPI(title="Inbox Architect Review UI")

runner: Optional[ReviewRunner] = None


class StartRequest(BaseModel):
    limit: int = 500
    batch_size: int = 50
    archive_noise: bool = True
    dry_run: bool = True
    resume: bool = False


class RuleActionRequest(BaseModel):
    message_id: str


class ResumeRequest(BaseModel):
    pass


def _batch_to_dict(batch: ReviewBatch) -> Dict[str, Any]:
    return {
        "batch_number": batch.batch_number,
        "total_emails": batch.total_emails,
        "processed_count": batch.processed_count,
        "llm_required_count": batch.llm_required_count,
        "status": batch.status,
        "error": batch.error,
        "logs": batch.logs,
        "items": [
            {
                "message_id": item.message_id,
                "sender": item.sender,
                "subject": item.subject,
                "body_preview": item.body_preview,
                "llm_category": item.llm_category,
                "llm_priority": item.llm_priority,
                "llm_summary": item.llm_summary,
                "suggested_rule": item.suggested_rule,
            }
            for item in batch.items
        ],
    }


@app.get("/")
def read_root() -> FileResponse:
    """Serve the main UI page."""
    ui_dir = Path(__file__).parent
    return FileResponse(ui_dir / "index.html")


@app.post("/api/setup")
def setup(req: StartRequest) -> JSONResponse:
    """Initialize the review runner and authenticate connectors."""
    global runner
    try:
        new_runner = ReviewRunner(config_path=os.getenv("CONFIG_PATH", "config.yaml"))
        new_runner.setup(
            limit=req.limit,
            batch_size=req.batch_size,
            archive_noise=req.archive_noise,
            dry_run=req.dry_run,
            resume=req.resume,
        )
        runner = new_runner
        return JSONResponse(content={"ok": True, "status": runner.get_status()})
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Setup failed")
        runner = None
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/status")
def get_status() -> JSONResponse:
    """Return current runner status."""
    if runner is None:
        return JSONResponse(
            content={"ok": False, "error": "Not initialized. Call /api/setup first."},
            status_code=400,
        )
    return JSONResponse(content={"ok": True, "status": runner.get_status()})


@app.post("/api/run-batch")
def run_batch() -> JSONResponse:
    """Start the next batch in the background for live log streaming."""
    if runner is None:
        return JSONResponse(
            content={"ok": False, "error": "Not initialized. Call /api/setup first."},
            status_code=400,
        )
    started = runner.run_batch_async()
    if not started:
        return JSONResponse(
            content={"ok": False, "error": "Batch already running or no emails remaining."},
            status_code=409,
        )
    return JSONResponse(content={"ok": True, "started": True})


@app.get("/api/stream-logs")
async def stream_logs() -> StreamingResponse:
    """Server-sent events stream of live log lines from the running batch."""
    if runner is None:
        return JSONResponse(
            content={"ok": False, "error": "Not initialized"}, status_code=400
        )

    async def _event_generator() -> AsyncIterator[str]:
        while True:
            try:
                line = runner._stream_queue.get(timeout=0.5)
            except queue.Empty:
                if not runner._batch_running:
                    break
                await asyncio.sleep(0.2)
                continue
            if line is None:  # sentinel
                break
            yield f"data: {json.dumps({'log': line})}\n\n"

    return StreamingResponse(
        _event_generator(), media_type="text/event-stream"
    )


@app.get("/api/batch-result")
def batch_result() -> JSONResponse:
    """Return the result of the most recently completed batch."""
    if runner is None:
        return JSONResponse(
            content={"ok": False, "error": "Not initialized"}, status_code=400
        )
    if runner.current_batch is None:
        return JSONResponse(content={"ok": True, "ready": False})
    return JSONResponse(
        content={"ok": True, "ready": True, "batch": _batch_to_dict(runner.current_batch)}
    )


@app.post("/api/accept-rule")
def accept_rule(req: RuleActionRequest) -> JSONResponse:
    """Accept a suggested rule and persist it."""
    if runner is None:
        return JSONResponse(
            content={"ok": False, "error": "Not initialized"}, status_code=400
        )
    result = runner.accept_rule(req.message_id)
    return JSONResponse(content=result)


@app.post("/api/reject-rule")
def reject_rule(req: RuleActionRequest) -> JSONResponse:
    """Reject a suggested rule."""
    if runner is None:
        return JSONResponse(
            content={"ok": False, "error": "Not initialized"}, status_code=400
        )
    result = runner.reject_rule(req.message_id)
    return JSONResponse(content=result)


# Static assets (if any).
ui_dir = Path(__file__).parent
if (ui_dir / "static").is_dir():
    app.mount("/static", StaticFiles(directory=ui_dir / "static"), name="static")
