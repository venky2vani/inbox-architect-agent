/**
 * Inbox Architect Agent — Google Apps Script Edition
 *
 * Zero-infrastructure version that runs entirely inside Google's cloud.
 * Reads unread Gmail, categorizes/summarizes via OpenAI, writes metadata to
 * Google Sheets, stores attachments in Google Drive, and archives noise.
 */

// --- Configuration ---

const CONFIG = {
  SHEET_NAME: 'Email Agent Index',
  DRIVE_ROOT_FOLDER: 'EmailAgent',
  OPENAI_MODEL: 'gpt-4o-mini',
  MAX_EMAILS: 50,
  ARCHIVE_NOISE: true,
};

const SYSTEM_PROMPT = `You are an Inbox Architect. Analyze emails and output strict JSON with this schema:
{
  "category": "action_needed|waiting_for|reference|noise",
  "priority": 1-5,
  "summary": "2-3 sentence summary",
  "action_items": ["specific task 1", "task 2"],
  "extracted_data": {"key": "value from email"},
  "should_archive": true|false
}

Rules:
- action_needed: Requires YOUR response/action
- waiting_for: You're waiting on someone else
- reference: Info you might need later
- noise: Newsletters, promos, notifications
- Priority 5 = Urgent (boss, deadline today), 1 = Low
- should_archive = true only for newsletters, promos, automated notifications, and anything categorized as noise.`;

// --- Entry Points ---

/**
 * Main entry point. Run this manually from the Apps Script editor or via trigger.
 */
function runInboxArchitect() {
  ensureSheet();
  const rootFolder = ensureDriveFolder(CONFIG.DRIVE_ROOT_FOLDER);
  const threads = GmailApp.search('is:unread in:inbox', 0, CONFIG.MAX_EMAILS);

  console.log(`Found ${threads.length} unread thread(s).`);

  for (const thread of threads) {
    const messages = thread.getMessages();
    // Process the newest message in each thread.
    const message = messages[messages.length - 1];
    processMessage(message, rootFolder);
  }

  console.log('Inbox Architect run complete.');
}

/**
 * Creates a daily trigger at 08:00 if one does not already exist.
 */
function createDailyTrigger() {
  const triggers = ScriptApp.getProjectTriggers();
  const exists = triggers.some(t => t.getHandlerFunction() === 'runInboxArchitect');
  if (exists) {
    console.log('Daily trigger already exists.');
    return;
  }

  ScriptApp.newTrigger('runInboxArchitect')
    .timeBased()
    .everyDays(1)
    .atHour(8)
    .nearMinute(0)
    .create();

  console.log('Daily trigger created for 08:00.');
}

/**
 * Removes all existing Inbox Architect triggers.
 */
function removeTriggers() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'runInboxArchitect')
    .forEach(t => ScriptApp.deleteTrigger(t));
  console.log('Triggers removed.');
}

// --- Message Processing ---

/**
 * Process a single Gmail message: categorize, store attachments, index, archive.
 */
function processMessage(message, rootFolder) {
  const subject = message.getSubject();
  const sender = message.getFrom();
  console.log(`Processing: ${subject}`);

  const bodyText = message.getPlainBody().substring(0, 6000);
  const processed = categorizeWithLLM(sender, subject, bodyText);

  // Store attachments in Drive under a date folder.
  const dateFolder = ensureDriveFolder(Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd'), rootFolder);
  const driveLinks = [];
  const attachments = message.getAttachments();
  for (const attachment of attachments) {
    const file = dateFolder.createFile(attachment.copyBlob());
    file.setName(`${message.getId()}_${attachment.getName()}`);
    driveLinks.push(file.getUrl());
  }

  // Append metadata to the index sheet.
  appendIndexRow({
    date: new Date(),
    emailId: message.getId(),
    sender: sender,
    subject: subject,
    category: processed.category,
    priority: processed.priority,
    summary: processed.summary,
    actionItems: processed.action_items,
    driveLink: driveLinks.join('\n'),
    status: processed.should_archive ? 'archived' : 'pending',
  });

  // Archive noise if configured.
  if (CONFIG.ARCHIVE_NOISE && processed.should_archive) {
    console.log(`  Archiving noise: ${subject}`);
    thread = message.getThread();
    thread.moveToArchive();
  }
}

/**
 * Call OpenAI to categorize and summarize an email.
 */
function categorizeWithLLM(sender, subject, bodyText) {
  const apiKey = getOpenAIApiKey();
  if (!apiKey) {
    console.warn('No OpenAI API key configured. Using fallback rules.');
    return fallbackCategorization(sender, subject, bodyText);
  }

  const content = `From: ${sender}\nSubject: ${subject}\n\n${bodyText}`;
  const payload = {
    model: CONFIG.OPENAI_MODEL,
    messages: [
      { role: 'system', content: SYSTEM_PROMPT },
      { role: 'user', content: content },
    ],
    response_format: { type: 'json_object' },
    temperature: 0.2,
  };

  const options = {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  };

  const response = UrlFetchApp.fetch('https://api.openai.com/v1/chat/completions', options);
  const status = response.getResponseCode();
  if (status !== 200) {
    console.error(`OpenAI request failed (${status}): ${response.getContentText()}`);
    return fallbackCategorization(sender, subject, bodyText);
  }

  const json = JSON.parse(response.getContentText());
  const result = JSON.parse(json.choices[0].message.content || '{}');
  return normalizeResult(result);
}

/**
 * Rule-based fallback when OpenAI is unavailable.
 */
function fallbackCategorization(sender, subject, bodyText) {
  const text = (subject + ' ' + bodyText).toLowerCase();
  const noiseKeywords = ['unsubscribe', 'newsletter', 'promotion', 'sale', 'no reply'];
  const urgentKeywords = ['urgent', 'asap', 'deadline', 'action required'];

  const isNoise = noiseKeywords.some(k => text.includes(k));
  const isUrgent = urgentKeywords.some(k => text.includes(k));

  if (isNoise) {
    return { category: 'noise', priority: 1, summary: 'Fallback: newsletter/promo.', action_items: [], should_archive: true };
  }
  if (isUrgent) {
    return { category: 'action_needed', priority: 5, summary: 'Fallback: urgent request.', action_items: ['Review manually'], should_archive: false };
  }
  if (text.includes('?') || text.includes('please')) {
    return { category: 'action_needed', priority: 3, summary: 'Fallback: likely needs a response.', action_items: ['Review manually'], should_archive: false };
  }
  return { category: 'reference', priority: 2, summary: 'Fallback: reference material.', action_items: [], should_archive: false };
}

/**
 * Normalize and sanitize the LLM result.
 */
function normalizeResult(result) {
  const validCategories = ['action_needed', 'waiting_for', 'reference', 'noise'];
  const category = validCategories.includes(result.category) ? result.category : 'reference';
  let priority = parseInt(result.priority, 10);
  if (isNaN(priority) || priority < 1 || priority > 5) priority = 3;

  return {
    category: category,
    priority: priority,
    summary: result.summary || '',
    action_items: Array.isArray(result.action_items) ? result.action_items : [],
    extracted_data: result.extracted_data || {},
    should_archive: result.should_archive || (category === 'noise'),
  };
}

// --- Google Sheets Index ---

/**
 * Ensure the index spreadsheet exists with the correct headers.
 */
function ensureSheet() {
  let spreadsheet;
  const files = DriveApp.getFilesByName(CONFIG.SHEET_NAME);
  if (files.hasNext()) {
    spreadsheet = SpreadsheetApp.open(files.next());
  } else {
    spreadsheet = SpreadsheetApp.create(CONFIG.SHEET_NAME);
  }

  const sheet = spreadsheet.getActiveSheet();
  const headers = ['Date', 'Email ID', 'Sender', 'Subject', 'Category', 'Priority', 'Summary', 'Action Items', 'Drive Link', 'Status'];
  const firstRow = sheet.getRange(1, 1, 1, headers.length).getValues()[0];

  if (firstRow.join(',') !== headers.join(',')) {
    sheet.clear();
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');
  }

  return sheet;
}

/**
 * Append a single processed row to the index sheet.
 */
function appendIndexRow(item) {
  const sheet = ensureSheet();
  const actionItemsText = item.actionItems.map(a => `- ${a}`).join('\n');
  sheet.appendRow([
    item.date,
    item.emailId,
    item.sender,
    item.subject,
    item.category,
    item.priority,
    item.summary,
    actionItemsText,
    item.driveLink,
    item.status,
  ]);
}

// --- Google Drive Storage ---

/**
 * Return a Drive folder, creating it (and its parent if provided) if necessary.
 */
function ensureDriveFolder(name, parentFolder) {
  let query = `mimeType = 'application/vnd.google-apps.folder' and title = '${name}' and trashed = false`;
  if (parentFolder) {
    query += ` and '${parentFolder.getId()}' in parents`;
  }

  const folders = DriveApp.searchFolders(query);
  if (folders.hasNext()) {
    return folders.next();
  }

  if (parentFolder) {
    return parentFolder.createFolder(name);
  }
  return DriveApp.createFolder(name);
}

// --- Secrets Management ---

/**
 * Store the OpenAI API key in Script Properties.
 * Run this once from the editor: setOpenAIApiKey('sk-...')
 */
function setOpenAIApiKey(apiKey) {
  PropertiesService.getScriptProperties().setProperty('OPENAI_API_KEY', apiKey);
  console.log('OpenAI API key saved to script properties.');
}

/**
 * Retrieve the OpenAI API key from Script Properties.
 */
function getOpenAIApiKey() {
  return PropertiesService.getScriptProperties().getProperty('OPENAI_API_KEY');
}
