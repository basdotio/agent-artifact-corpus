#!/usr/bin/env node

/**
 * Analyze transcription text and extract structured event information
 * Uses AI to parse Lithuanian text for event details
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const SKILL_DIR = path.dirname(__dirname);
const CONFIG = JSON.parse(fs.readFileSync(path.join(SKILL_DIR, 'config.json'), 'utf8'));
const OUTPUT_DIR = path.join(SKILL_DIR, 'output');
const TEMP_DIR = '/tmp/email-audio-analyzer';

// Ensure temp dir exists
if (!fs.existsSync(TEMP_DIR)) fs.mkdirSync(TEMP_DIR, { recursive: true });

const PHONE_PATTERNS = CONFIG.extraction.phonePatterns.map(p => new RegExp(p, 'g'));
const EMAIL_PATTERN = new RegExp(CONFIG.extraction.emailPattern, 'g');

function extractContactInfo(text) {
  const phones = [];
  const emails = [];
  
  // Extract phone numbers
  for (const pattern of PHONE_PATTERNS) {
    const matches = text.match(pattern);
    if (matches) phones.push(...matches);
  }
  
  // Extract emails
  const emailMatches = text.match(EMAIL_PATTERN);
  if (emailMatches) emails.push(...emailMatches);
  
  return {
    phones: [...new Set(phones)],
    emails: [...new Set(emails)]
  };
}

function formatDateISO(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function getUpcomingWeekday(baseDate, targetWeekday, includeToday = true) {
  const result = new Date(baseDate);
  result.setHours(0, 0, 0, 0);

  const currentWeekday = result.getDay();
  let daysAhead = (targetWeekday - currentWeekday + 7) % 7;
  if (!includeToday && daysAhead === 0) daysAhead = 7;

  result.setDate(result.getDate() + daysAhead);
  return result;
}

function inferDateFromText(text, now = new Date()) {
  if (!text) return { value: null, confidence: 0 };

  const normalized = text.toLowerCase();
  const mentionsSaturday = /(šeštadien(?:į|is|io|iui|iu)|sestadien(?:i|is|io|iui|iu)|saturday)/i.test(normalized);
  if (!mentionsSaturday) return { value: null, confidence: 0 };

  const hasExplicitDate = /\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b|\b(sausio|vasario|kovo|balandžio|gegužės|birželio|liepos|rugpjūčio|rugsėjo|spalio|lapkričio|gruodžio)\b/i.test(normalized);
  if (hasExplicitDate) return { value: null, confidence: 0 };

  const isNextSaturday = /(next\s+saturday|kit[aą]\s+šeštadien)/i.test(normalized);
  const isThisOrComingSaturday = /((this|coming)\s+saturday|(š[iį]s?|artėjant[iį]s?)\s+šeštadien)/i.test(normalized);

  const thisSaturday = getUpcomingWeekday(now, 6, true);
  const nextSaturday = new Date(thisSaturday);
  nextSaturday.setDate(nextSaturday.getDate() + 7);

  if (isNextSaturday) return { value: formatDateISO(nextSaturday), confidence: 0.92 };
  if (isThisOrComingSaturday) return { value: formatDateISO(thisSaturday), confidence: 0.9 };

  // Bare "šeštadienis" / "Saturday" without a date => upcoming Saturday
  return { value: formatDateISO(thisSaturday), confidence: 0.82 };
}

function buildPrompt(transcription, emailBody = '', phoneFromSubject = '') {
  const now = new Date();
  const today = formatDateISO(now);
  const thisSaturday = formatDateISO(getUpcomingWeekday(now, 6, true));
  const nextSaturdayDate = new Date(getUpcomingWeekday(now, 6, true));
  nextSaturdayDate.setDate(nextSaturdayDate.getDate() + 7);
  const nextSaturday = formatDateISO(nextSaturdayDate);

  return `You are analyzing a Lithuanian voice message transcription from a bar/venue inquiry.
Extract the following information and return as JSON:

CURRENT DATE CONTEXT:
- Today: ${today}
- This/coming Saturday: ${thisSaturday}
- Next Saturday (following week): ${nextSaturday}

TRANSCRIPTION:
${transcription}

${emailBody ? 'EMAIL CONTEXT:\n' + emailBody : ''}
${phoneFromSubject ? '\nEXTRACTED CALLER PHONE FROM EMAIL SUBJECT/BODY:\n' + phoneFromSubject + '\n' : ''}

Date inference rules (important):
- If weekday terms are mentioned without an explicit calendar date, infer a concrete date in YYYY-MM-DD.
- If "šeštadienis" / "Saturday" is mentioned without date, infer the upcoming Saturday from Today.
- "this Saturday" / "coming Saturday" / "šį šeštadienį" => use This/coming Saturday.
- "next Saturday" / "kitą šeštadienį" => use Next Saturday (following week).
- If explicit date exists, do not override it with weekday inference.

Extract:
1. eventType - What type of event? (birthday, wedding, corporate, concert, party, private, etc.)
2. date - Event date (format: YYYY-MM-DD or "Not specified")
3. time - Event time (format: HH:MM or "Not specified")
4. guestCount - Approximate number of people (integer or "Unknown")
5. contactName - Name of the person inquiring (or null)
6. contactPhone - Phone number from text (or null). If EXTRACTED CALLER PHONE is provided, prefer it as the main contact phone unless transcription clearly gives a different caller number.
7. contactEmail - Email from text (or null)
8. notes - Any special requirements, requests, or important details (string)
9. isPrivateEvent - true if it's a private booking, false if public event/concert
10. bookingStatus - What was the response? Use one of: "confirmed", "pending", "waitlist", "rejected", "unknown"
11. bookingNotes - Notes about availability, follow-up needed, waitlist status, etc. (string)
12. followUpRequired - true if staff needs to call back or follow up, false otherwise
13. confidence - Your confidence in the extraction (0-1)
14. inferredDate - inferred date object when weekday inference is used:
    { "value": "YYYY-MM-DD or null", "confidence": 0-1 }

Look for these Lithuanian keywords:
- Confirmed: "patvirtinta", "turime laisvą", "taip", "užsakyta", "rezervuota"
- Pending: "patikrinsiu", "susisieksime", "aptarsime", "pranešime"
- Waitlist: "laukimo sąrašas", "neturime", "užimta", "pilna", "vėliau"
- Rejected: "negalime", "atmesta", "netinka", "nevykdome"

Return ONLY valid JSON, no other text. Example:
{
  "eventType": "gimtadienis",
  "date": "2026-05-15",
  "time": "20:00",
  "guestCount": 30,
  "contactName": "Jonas",
  "contactPhone": "+370 612 34567",
  "contactEmail": null,
  "notes": "Reikia garso sistemos, privataus kambario",
  "isPrivateEvent": true,
  "bookingStatus": "pending",
  "bookingNotes": "Staff will contact customer soon. Availability confirmed.",
  "followUpRequired": true,
  "confidence": 0.85,
  "inferredDate": {
    "value": null,
    "confidence": 0
  }
}`;
}

async function analyzeWithAI(transcription, emailBody = '', phoneFromSubject = '') {
  console.log('🧠 Analyzing transcription with AI...');
  
  try {
    const prompt = buildPrompt(transcription, emailBody, phoneFromSubject);
    
    // Get OpenRouter API key from auth profiles
    const authProfilesPath = '/home/alex/.openclaw/agents/main/agent/auth-profiles.json';
    let [REDACTED_SECRET] || '';
    
    if (!apiKey && fs.existsSync(authProfilesPath)) {
      const authData = JSON.parse(fs.readFileSync(authProfilesPath, 'utf8'));
      [REDACTED_SECRET]'openrouter:default']?.key || '';
    }
    
    if (!apiKey) {
      throw new Error('OpenRouter API key not found');
    }
    
    // Call Bailian API directly (your configured model)
    const bailianKey = '[REDACTED_SECRET]';
    
    const response = await fetch('https://coding-intl.dashscope.aliyuncs.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${bailianKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'qwen3.5-plus',
        messages: [{ role: 'user', content: prompt }],
        temperature: 0.1,
        max_tokens: 500
      })
    });
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    const content = data.choices?.[0]?.message?.content || '';
    
    // Try to parse JSON from the response
    const jsonMatch = content.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      const analysis = JSON.parse(jsonMatch[0]);
      const inferred = inferDateFromText(`${transcription}\n${emailBody}`);

      if (!analysis.inferredDate || typeof analysis.inferredDate !== 'object') {
        analysis.inferredDate = inferred;
      }

      if ((analysis.date === 'Not specified' || !analysis.date) && inferred.value) {
        analysis.date = inferred.value;
      }

      console.log('✅ Analysis complete');
      return analysis;
    } else {
      throw new Error('No JSON found in API response');
    }
  } catch (error) {
    console.error('❌ AI analysis failed:', error.message);
    
    // Fallback to basic regex extraction
    console.log('   Using fallback extraction...');
    return fallbackAnalysis(transcription, emailBody, phoneFromSubject);
  }
}

function fallbackAnalysis(transcription, emailBody = '', phoneFromSubject = '') {
  const text = transcription + ' ' + emailBody;
  const contactInfo = extractContactInfo(text);
  
  // Very basic keyword matching for event type
  const eventKeywords = {
    'gimtadienis': 'birthday',
    'vestuvės': 'wedding',
    'koncertas': 'concert',
    'vakarėlis': 'party',
    'privatus': 'private',
    'korporacinis': 'corporate'
  };
  
  let eventType = 'general inquiry';
  for (const [lt, en] of Object.entries(eventKeywords)) {
    if (text.toLowerCase().includes(lt)) {
      eventType = en;
      break;
    }
  }
  
  const inferred = inferDateFromText(text);

  return {
    eventType,
    date: inferred.value || 'Not specified',
    time: 'Not specified',
    guestCount: 'Unknown',
    contactName: null,
    contactPhone: phoneFromSubject || contactInfo.phones[0] || null,
    contactEmail: contactInfo.emails[0] || null,
    notes: 'Extracted via fallback - review recommended',
    isPrivateEvent: eventType === 'private' || eventType === 'birthday' || eventType === 'wedding',
    confidence: 0.5,
    inferredDate: inferred
  };
}

function parseArgs() {
  const args = process.argv.slice(2);
  const options = {};
  
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--text' && args[i + 1]) {
      options.text = args[++i];
    } else if (args[i] === '--file' && args[i + 1]) {
      options.file = args[++i];
    } else if (args[i] === '--email' && args[i + 1]) {
      options.email = args[++i];
    } else if (args[i] === '--phone' && args[i + 1]) {
      options.phone = args[++i];
    } else if (args[i] === '--output') {
      options.output = true;
    }
  }
  
  return options;
}

async function main() {
  const options = parseArgs();
  
  let transcription = options.text;
  
  if (options.file) {
    if (!fs.existsSync(options.file)) {
      console.error(`❌ File not found: ${options.file}`);
      process.exit(1);
    }
    transcription = fs.readFileSync(options.file, 'utf8');
  }
  
  if (!transcription) {
    console.log('Usage: node analyze.js --text "<transcription>" [--email "<email body>"] [--phone "+370..."]');
    console.log('   or: node analyze.js --file <transcription.txt> [--email "<email body>"] [--phone "+370..."]');
    process.exit(1);
  }
  
  const analysis = await analyzeWithAI(transcription, options.email || '', options.phone || '');
  
  if (options.output) {
    console.log('\n--- ANALYSIS RESULT ---');
    console.log(JSON.stringify(analysis, null, 2));
    console.log('--- END ---');
  }
  
  // Always output JSON to stderr for piping
  console.error(JSON.stringify(analysis, null, 2));
}

main().catch(console.error);
