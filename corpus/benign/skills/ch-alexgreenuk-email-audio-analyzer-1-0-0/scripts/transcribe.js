#!/usr/bin/env node

/**
 * Transcribe audio files using Whisper CLI
 * Supports Lithuanian and English
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const SKILL_DIR = path.dirname(__dirname);
const CONFIG = JSON.parse(fs.readFileSync(path.join(SKILL_DIR, 'config.json'), 'utf8'));
const OUTPUT_DIR = path.join(SKILL_DIR, 'output');

function transcribe(audioFile, language = 'lt', model = null) {
  const whisperModel = model || CONFIG.whisper.model || 'base';
  const timeout = CONFIG.whisper.timeout || 120;
  
  console.log(`🎙️  Transcribing: ${path.basename(audioFile)}`);
  console.log(`   Language: ${language}, Model: ${whisperModel}`);
  
  try {
    // Check if whisper is available
    execSync('which whisper', { stdio: 'pipe' });
    
    // Run whisper transcription
    const outputDir = OUTPUT_DIR;
    const cmd = `whisper "${audioFile}" --model ${whisperModel} --language ${language} --output_dir "${outputDir}" --output_format txt`;
    
    console.log(`   Running: ${cmd}`);
    execSync(cmd, { 
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'pipe'],
      timeout: timeout * 1000 * 2 // Give it extra time
    });
    
    // Read the transcription file
    const baseName = path.basename(audioFile, path.extname(audioFile));
    const txtFile = path.join(outputDir, `${baseName}.txt`);
    
    if (fs.existsSync(txtFile)) {
      const transcription = fs.readFileSync(txtFile, 'utf8');
      console.log(`✅ Transcription complete (${transcription.length} chars)`);
      return {
        success: true,
        text: transcription,
        file: txtFile
      };
    } else {
      throw new Error('Transcription file not found');
    }
  } catch (error) {
    console.error(`❌ Transcription failed: ${error.message}`);
    
    // Try fallback to English if Lithuanian failed
    if (language === 'lt') {
      console.log('   Trying English fallback...');
      return transcribe(audioFile, 'en', whisperModel);
    }
    
    return {
      success: false,
      error: error.message,
      text: ''
    };
  }
}

function parseArgs() {
  const args = process.argv.slice(2);
  const options = {};
  
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--file' && args[i + 1]) {
      options.file = args[++i];
    } else if (args[i] === '--language' && args[i + 1]) {
      options.language = args[++i];
    } else if (args[i] === '--model' && args[i + 1]) {
      options.model = args[++i];
    } else if (args[i] === '--output') {
      options.output = true;
    }
  }
  
  return options;
}

async function main() {
  const options = parseArgs();
  
  if (!options.file) {
    console.log('Usage: node transcribe.js --file <audio.mp3> [--language lt|en] [--model tiny|base|small|medium|large]');
    process.exit(1);
  }
  
  if (!fs.existsSync(options.file)) {
    console.error(`❌ File not found: ${options.file}`);
    process.exit(1);
  }
  
  const result = transcribe(options.file, options.language || 'lt', options.model);
  
  if (options.output || !options.file) {
    console.log('\n--- TRANSCRIPTION ---');
    console.log(result.text);
    console.log('--- END ---');
  }
  
  // Output JSON for piping
  console.error(JSON.stringify(result, null, 2));
}

main().catch(console.error);
