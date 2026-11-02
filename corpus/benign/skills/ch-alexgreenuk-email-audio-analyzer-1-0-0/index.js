#!/usr/bin/env node

/**
 * Email Audio Analyzer - Main Entry Point
 * Orchestrates email checking, transcription, and analysis
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const SKILL_DIR = __dirname;
const CONFIG = JSON.parse(fs.readFileSync(path.join(SKILL_DIR, 'config.json'), 'utf8'));
const OUTPUT_DIR = path.join(SKILL_DIR, 'output');
const TEMP_DIR = '/tmp/email-audio-analyzer';

// Ensure directories exist
[OUTPUT_DIR, TEMP_DIR].forEach(dir => {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
});

function runScript(scriptName, args = []) {
  const scriptPath = path.join(SKILL_DIR, 'scripts', scriptName);
  const cmd = `node "${scriptPath}" ${args.join(' ')}`;
  console.log(`Running: ${cmd}`);
  return execSync(cmd, { encoding: 'utf8', stderr: 'pipe' });
}

function sendTelegram(message) {
  // Escape markdown for Telegram
  const escaped = message.replace(/_/g, '\\_').replace(/\*/g, '\\*').replace(/\[/g, '\\[');
  try {
    // Send to user's Telegram DM (chat_id from config)
    execSync(`openclaw message send --target telegram:1341107300 --message "${escaped.replace(/"/g, '\\"')}"`, {
      encoding: 'utf8'
    });
    console.log('✅ Sent to Telegram');
  } catch (error) {
    console.error('❌ Failed to send Telegram:', error.message);
  }
}

function saveSummary(emailData, transcription, analysis) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `${timestamp}_summary.md`;
  const filepath = path.join(OUTPUT_DIR, filename);
  
  // Booking status emoji
  const statusEmoji = {
    'confirmed': '✅',
    'pending': '⏳',
    'waitlist': '📋',
    'rejected': '❌',
    'unknown': '❓'
  };
  
  const summary = `## 📋 Event Inquiry

**Booking Status:** ${statusEmoji[analysis.bookingStatus] || '❓'} ${analysis.bookingStatus?.toUpperCase() || 'UNKNOWN'}

**Contact:**
${analysis.contactName ? `- Name: ${analysis.contactName}` : ''}
${analysis.contactPhone ? `- Phone: ${analysis.contactPhone}` : ''}
${analysis.contactEmail ? `- Email: ${analysis.contactEmail}` : ''}
- Source: ${emailData.from}

**Event Details:**
- Type: ${analysis.eventType || 'Unknown'}
- Date: ${analysis.date || 'Not specified'}
- Time: ${analysis.time || 'Not specified'}
- Guests: ${analysis.guestCount || 'Unknown'}
- Private Event: ${analysis.isPrivateEvent ? 'Yes' : 'No/Unknown'}

**Booking Info:**
- Status: ${analysis.bookingStatus || 'Unknown'}
- Notes: ${analysis.bookingNotes || 'None'}
- Follow-up Required: ${analysis.followUpRequired ? '✅ Yes' : 'No'}

**Additional Notes:** ${analysis.notes || 'None'}

**Confidence:** ${analysis.confidence ? (analysis.confidence * 100).toFixed(0) + '%' : 'Unknown'}

**Source:**
- Account: ${emailData.account}
- From: ${emailData.from}
- Subject: ${emailData.subject}
- Received: ${emailData.date}

**Audio:** ${emailData.audioFilename}

---

## 🎙️ Transcription

${transcription || '[Transcription failed or not available]'}

---

*Generated: ${new Date().toISOString()}*
`;
  
  fs.writeFileSync(filepath, summary);
  console.log(`💾 Summary saved to: ${filepath}`);
  return filepath;
}

function formatTelegramMessage(emailData, analysis) {
  // Booking status emoji
  const statusEmoji = {
    'confirmed': '✅',
    'pending': '⏳',
    'waitlist': '📋',
    'rejected': '❌',
    'unknown': '❓'
  };
  
  const status = analysis.bookingStatus || 'unknown';
  const emoji = statusEmoji[status] || '❓';
  
  return `🎉 *New Event Inquiry* ${emoji}

*Status:* ${status.toUpperCase()}
*Type:* ${analysis.eventType || 'Unknown'}
*Date:* ${analysis.date || 'Not specified'}
*Time:* ${analysis.time || 'Not specified'}
*Guests:* ${analysis.guestCount || 'Unknown'}

*Contact:*
${analysis.contactName ? `Name: ${analysis.contactName}` : ''}
${analysis.contactPhone ? `Phone: ${analysis.contactPhone}` : ''}

*Booking Notes:* ${analysis.bookingNotes || 'None'}
*Follow-up:* ${analysis.followUpRequired ? '✅ Required' : 'Not needed'}

_From: ${emailData.from}_`;
}

async function processAudioEmail(emailData) {
  console.log(`\n🎵 Processing: ${emailData.audioFilename}`);
  
  // Step 1: Transcribe
  console.log('\n--- Step 1: Transcription ---');
  let transcriptionResult;
  try {
    const transcribeOutput = runScript('transcribe.js', [
      `--file "${emailData.audioFile}"`,
      '--language lt',
      '--output'
    ]);
    
    // Parse JSON from output (transcribe.js outputs to stderr)
    const jsonMatch = transcribeOutput.match(/\{[\s\S]*"text":[\s\S]*\}/);
    transcriptionResult = jsonMatch ? JSON.parse(jsonMatch[0]) : { success: false, text: '' };
    
    console.log(`Transcription: ${transcriptionResult.success ? '✅' : '❌'} (${transcriptionResult.text?.length || 0} chars)`);
  } catch (error) {
    console.error('Transcription failed:', error.message);
    transcriptionResult = { success: false, text: '', error: error.message };
  }
  
  // Step 2: Analyze
  console.log('\n--- Step 2: Analysis ---');
  let analysis;
  try {
    const textToAnalyze = transcriptionResult.text || '';
    const emailBody = emailData.body || '';
    
    console.log(`Analyzing ${textToAnalyze.length} chars of transcription...`);
    
    const analyzeArgs = [
      `--text "${textToAnalyze.substring(0, 3000).replace(/"/g, '\\"')}"`,
      `--email "${emailBody.substring(0, 1000).replace(/"/g, '\\"')}"`
    ];

    if (emailData.phoneFromSubject) {
      analyzeArgs.push(`--phone "${emailData.phoneFromSubject.replace(/"/g, '\\"')}"`);
    }

    analyzeArgs.push('--output');

    const analyzeOutput = runScript('analyze.js', analyzeArgs);
    
    const jsonMatch = analyzeOutput.match(/\{[\s\S]*\}/);
    analysis = jsonMatch ? JSON.parse(jsonMatch[0]) : {};
    
    console.log(`Analysis: ${analysis.eventType ? '✅' : '❌'}`);
  } catch (error) {
    console.error('Analysis failed:', error.message);
    analysis = { error: error.message };
  }
  
  // Step 3: Save Summary
  console.log('\n--- Step 3: Save Summary ---');
  const summaryPath = saveSummary(emailData, transcriptionResult.text, analysis);
  
  // Step 4: Send Telegram (if configured)
  if (CONFIG.output.telegram) {
    console.log('\n--- Step 4: Telegram Notification ---');
    const telegramMsg = formatTelegramMessage(emailData, analysis);
    sendTelegram(telegramMsg);
  }
  
  return {
    emailData,
    transcription: transcriptionResult,
    analysis,
    summaryPath
  };
}

async function main() {
  const args = process.argv.slice(2);
  const accountArg = args.find(a => a.startsWith('--account='))?.split('=')[1] || CONFIG.defaultAccount;
  const manifestArg = args.find(a => a.startsWith('--manifest='))?.split('=')[1];
  
  console.log('⚡ Email Audio Analyzer\n');
  console.log(`Account: ${accountArg}`);
  
  let audioEmails = [];
  
  if (manifestArg) {
    // Use existing manifest
    if (fs.existsSync(manifestArg)) {
      audioEmails = JSON.parse(fs.readFileSync(manifestArg, 'utf8'));
      console.log(`Loaded ${audioEmails.length} audio file(s) from manifest`);
    }
  } else {
    // Check email first
    console.log('\n--- Checking Email ---');
    try {
      const checkOutput = runScript('check-email.js', [`--account=${accountArg}`]);
      
      // Parse JSON from output (look for JSON array - greedy match to end)
      const jsonMatch = checkOutput.match(/\[[\s\S]*?\]\s*(?=\s*$)/);
      if (jsonMatch && jsonMatch[0].trim()) {
        try {
          audioEmails = JSON.parse(jsonMatch[0].trim());
        } catch (e) {
          // Try finding just the array
          const simpleMatch = checkOutput.match(/^\[.*\]/m);
          if (simpleMatch) {
            audioEmails = JSON.parse(simpleMatch[0]);
          }
        }
      }
      
      // Fallback: check for most recent manifest
      if (audioEmails.length === 0) {
        const manifestFiles = fs.readdirSync(TEMP_DIR)
          .filter(f => f.startsWith('manifest_') && f.endsWith('.json'))
          .sort()
          .reverse();
        
        if (manifestFiles.length > 0) {
          const latestManifest = path.join(TEMP_DIR, manifestFiles[0]);
          audioEmails = JSON.parse(fs.readFileSync(latestManifest, 'utf8'));
          console.log(`Loaded from manifest: ${manifestFiles[0]}`);
        }
      }
    } catch (error) {
      console.error('Error parsing check-email output:', error.message);
    }
  }
  
  if (audioEmails.length === 0) {
    console.log('\n✅ No audio attachments found.');
    return;
  }
  
  console.log(`\n🎵 Found ${audioEmails.length} audio attachment(s)\n`);
  
  // Process each audio email
  const results = [];
  for (const email of audioEmails) {
    try {
      const result = await processAudioEmail(email);
      results.push(result);
    } catch (error) {
      console.error(`\n❌ Failed to process ${email.audioFilename}:`, error.message);
    }
  }
  
  console.log('\n✅ Processing complete!');
  console.log(`Processed: ${results.length}/${audioEmails.length}`);
  
  // Save full results
  const resultsPath = path.join(OUTPUT_DIR, `results_${Date.now()}.json`);
  fs.writeFileSync(resultsPath, JSON.stringify(results, null, 2));
  console.log(`📄 Full results: ${resultsPath}`);
}

main().catch(console.error);
