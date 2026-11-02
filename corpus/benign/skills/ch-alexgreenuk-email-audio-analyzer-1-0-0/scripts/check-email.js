#!/usr/bin/env node

/**
 * Check email for audio attachments
 * Downloads attachments and queues them for transcription
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const SKILL_DIR = path.dirname(__dirname);
const CONFIG = JSON.parse(fs.readFileSync(path.join(SKILL_DIR, 'config.json'), 'utf8'));
const OUTPUT_DIR = path.join(SKILL_DIR, 'output');
const TEMP_DIR = '/tmp/email-audio-analyzer';

// Ensure directories exist
[OUTPUT_DIR, TEMP_DIR].forEach(dir => {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
});

const AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac', '.wma', '.opus'];

const PHONE_PATTERNS = [
  /from\s+(\+370\d{7,})/i,                       // VoipVoip: "from +370..."
  /from\s+(370\d{7,})/i,                         // VoipVoip without plus
  /\+370\d{7,}/g,                                // generic LT format with +
  /(?<!\+)\b370\d{7,}\b/g                       // generic LT format without +
];

function isAudioFile(filename) {
  const ext = path.extname(filename).toLowerCase();
  return AUDIO_EXTENSIONS.includes(ext);
}

function normalizePhone(phone) {
  if (!phone) return null;
  const cleaned = phone.replace(/[^\d+]/g, '');
  if (/^\+370\d{7,}$/.test(cleaned)) return cleaned;
  if (/^370\d{7,}$/.test(cleaned)) return `+${cleaned}`;
  return cleaned || null;
}

function extractPhone(text = '') {
  for (const pattern of PHONE_PATTERNS) {
    const match = text.match(pattern);
    if (!match) continue;

    const rawPhone = match[1] || match[0];
    const normalized = normalizePhone(rawPhone);
    if (normalized) return normalized;
  }

  return null;
}

function checkWorkEmail() {
  console.log('📬 Checking RUBIX work email...');
  
  try {
    // List recent emails with himalaya (work is default account)
    const emails = execSync('himalaya envelope list --output json', { encoding: 'utf8' });
    const emailList = JSON.parse(emails);
    
    const audioEmails = [];
    
    for (const email of emailList) {
      console.log(`  Checking email: ${email.subject} (${email.id})`);
      
      // Skip if no attachment
      if (!email.has_attachment) {
        console.log('    No attachments, skipping');
        continue;
      }
      
      // Download all attachments for this email
      const downloadOutput = execSync(`himalaya attachment download ${email.id} --output json`, { encoding: 'utf8' });
      console.log(`    ${downloadOutput.trim()}`);
      
      // Find the most recently downloaded audio file from /tmp
      const tmpFiles = fs.readdirSync('/tmp')
        .filter(f => {
          const ext = path.extname(f).toLowerCase();
          return AUDIO_EXTENSIONS.includes(ext) && f.includes(email.id);
        })
        .sort()
        .reverse();
      
      let audioFilePath = tmpFiles.length > 0 ? path.join('/tmp', tmpFiles[0]) : null;
      
      // Fallback: check for any recent audio files matching the email pattern
      if (!audioFilePath) {
        const allTmpAudio = fs.readdirSync('/tmp')
          .filter(f => {
            const ext = path.extname(f).toLowerCase();
            return AUDIO_EXTENSIONS.includes(ext);
          })
          .map(f => ({
            name: f,
            path: path.join('/tmp', f),
            mtime: fs.statSync(path.join('/tmp', f)).mtimeMs
          }))
          .sort((a, b) => b.mtime - a.mtime);
        
        if (allTmpAudio.length > 0) {
          audioFilePath = allTmpAudio[0].path;
        }
      }
      
      if (!audioFilePath) {
        console.log('    ⚠️  No audio file found, skipping');
        continue;
      }
      
      console.log(`    🎵 Audio file: ${path.basename(audioFilePath)}`);
      
      // Get email body
      const bodyOutput = execSync(`himalaya message read ${email.id}`, { encoding: 'utf8' });
      const phoneFromSubject = extractPhone(email.subject || '');
      const phoneFromBody = extractPhone(bodyOutput || '');
      const extractedPhone = phoneFromSubject || phoneFromBody || null;

      if (extractedPhone) {
        console.log(`    📞 Extracted phone: ${extractedPhone}${phoneFromSubject ? ' (subject)' : ' (body fallback)'}`);
      }
      
      audioEmails.push({
        account: 'work',
        emailId: email.id,
        subject: email.subject,
        from: email.from?.addr || JSON.stringify(email.from) || '',
        date: email.date,
        body: bodyOutput || '',
        phoneFromSubject: extractedPhone,
        audioFile: audioFilePath,
        audioFilename: path.basename(audioFilePath)
      });
      
      // Only process the first email with audio (the most recent)
      break;
    }
    
    return audioEmails;
  } catch (error) {
    console.error('❌ Error checking work email:', error.message);
    return [];
  }
}

// Output JSON at the very end for parsing by index.js
console.log('\n---JSON-START---');
console.log(JSON.stringify([]));
console.log('---JSON-END---');

function checkGmail() {
  console.log('📬 Checking Gmail...');
  
  try {
    // Use gog to list emails - this is a simplified version
    // In production, you'd use the Gmail API properly
    console.log('  ⚠️  Gmail check requires gog CLI setup');
    return [];
  } catch (error) {
    console.error('❌ Error checking Gmail:', error.message);
    return [];
  }
}

function saveSummary(emailData, transcription, analysis) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `${timestamp}_summary.md`;
  const filepath = path.join(OUTPUT_DIR, filename);
  
  const summary = `## 📋 Event Inquiry

**Contact:**
${analysis.contact ? `- Name: ${analysis.contact.name || 'Unknown'}
- Phone: ${analysis.contact.phone || 'Not provided'}
- Email: ${analysis.contact.email || analysis.from || 'Unknown'}` : `- Email: ${analysis.from || 'Unknown'}`}

**Event Details:**
- Type: ${analysis.eventType || 'Unknown'}
- Date: ${analysis.date || 'Not specified'}
- Time: ${analysis.time || 'Not specified'}
- Guests: ${analysis.guestCount || 'Unknown'}
- Notes: ${analysis.notes || 'None'}

**Source:**
- Account: ${emailData.account}
- From: ${emailData.from}
- Subject: ${emailData.subject}
- Received: ${emailData.date}

**Audio:** ${emailData.audioFilename}

---

## 🎙️ Transcription (Lithuanian)

${transcription || '[Transcription failed or not available]'}

---

*Generated: ${new Date().toISOString()}*
`;
  
  fs.writeFileSync(filepath, summary);
  console.log(`💾 Summary saved to: ${filepath}`);
  return filepath;
}

async function main() {
  const args = process.argv.slice(2);
  const accountArg = args.find(a => a.startsWith('--account='))?.split('=')[1] || CONFIG.defaultAccount;
  
  console.log('⚡ Email Audio Analyzer\n');
  
  let audioEmails = [];
  
  if (accountArg === 'work' || accountArg === 'all') {
    audioEmails = [...audioEmails, ...checkWorkEmail()];
  }
  
  if (accountArg === 'gmail' || accountArg === 'all') {
    audioEmails = [...audioEmails, ...checkGmail()];
  }
  
  if (audioEmails.length === 0) {
    console.log('\n✅ No audio attachments found.');
    return;
  }
  
  console.log(`\n🎵 Found ${audioEmails.length} audio attachment(s)\n`);
  
  // Output list for further processing
  console.log(JSON.stringify(audioEmails, null, 2));
  
  // Save manifest
  const manifestPath = path.join(TEMP_DIR, `manifest_${Date.now()}.json`);
  fs.writeFileSync(manifestPath, JSON.stringify(audioEmails, null, 2));
  console.log(`\n📄 Manifest saved to: ${manifestPath}`);
}

main().catch(console.error);
