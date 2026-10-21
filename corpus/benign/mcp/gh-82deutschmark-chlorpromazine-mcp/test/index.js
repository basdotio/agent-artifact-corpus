/**
 * Chlorpromazine MCP Server - MCP Protocol Test Suite
 * 
 * This file implements a test suite that:
 * 1. Starts the MCP server
 * 2. Tests MCP JSON-RPC protocol endpoints
 * 3. Validates proper MCP responses
 * 
 * Author: Claude
 */

import { spawn } from 'child_process';
import { setTimeout } from 'timers/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = process.env.TEST_PORT || 8081;

// Simple test framework
let testsPassed = 0;
let testsFailed = 0;

function assert(condition, message) {
  if (!condition) {
    console.error(`❌ FAIL: ${message}`);
    testsFailed++;
    return false;
  }
  console.log(`✅ PASS: ${message}`);
  testsPassed++;
  return true;
}

// MCP JSON-RPC client helper
async function mcpCall(method, params = {}) {
  const payload = {
    jsonrpc: '2.0',
    id: Math.random().toString(36).substring(7),
    method,
    params
  };
  
  const response = await fetch(`http://localhost:${PORT}`, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'Accept': 'application/json, text/event-stream'
    },
    body: JSON.stringify(payload)
  });
  
  const json = await response.json();
  return { status: response.status, json };
}

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, options);
  const status = response.status;
  let json = null;
  
  try {
    json = await response.json();
  } catch (e) {
    // Not JSON or empty response
  }
  
  return { status, json };
}

// Start server for testing
console.log('Starting test server...');
const server = spawn('node', ['dist/src/server.js'], {
  stdio: 'pipe',
  env: { 
    ...process.env, 
    PORT,
    SITE_FILTER: 'example.com',
    SERPAPI_KEY: 'test_key'
  }
});

let serverOutput = '';

server.stdout.on('data', (data) => {
  serverOutput += data.toString();
  console.log(`[Server]: ${data.toString().trim()}`);
});

server.stderr.on('data', (data) => {
  serverOutput += data.toString();
  console.error(`[Server Error]: ${data.toString().trim()}`);
});

// Wait for server to start
await setTimeout(1000);
console.log('Beginning tests...');

try {
  // Test 1: Health check endpoint (REST)
  const healthCheck = await fetch(`http://localhost:${PORT}/healthz`);
  assert(healthCheck.status === 200, 'Health check endpoint returns 200');
  
  // Test 2: MCP prompts/list
  const { status: promptsListStatus, json: promptsListResponse } = await mcpCall('prompts/list');
  assert(promptsListStatus === 200, 'MCP prompts/list returns 200 status');
  assert(!promptsListResponse.error, 'MCP prompts/list has no error');
  assert(promptsListResponse.result && promptsListResponse.result.prompts && promptsListResponse.result.prompts.length > 0, 'MCP prompts/list returns non-empty prompts array');
  
  // Test 3: MCP prompts/get
  const { status: promptsGetStatus, json: promptsGetResponse } = await mcpCall('prompts/get', {
    name: 'sober_thinking',
    arguments: { 'QUESTION_TEXT': 'Test question' }
  });
  
  assert(promptsGetStatus === 200, 'MCP prompts/get returns 200 status');
  assert(!promptsGetResponse.error, 'MCP prompts/get has no error');
  assert(promptsGetResponse.result && promptsGetResponse.result.messages && promptsGetResponse.result.messages.length > 0, 'MCP prompts/get returns non-empty messages array');
  
  // Test 4: MCP tools/list
  const { status: toolsListStatus, json: toolsListResponse } = await mcpCall('tools/list');
  assert(toolsListStatus === 200, 'MCP tools/list returns 200 status');
  assert(!toolsListResponse.error, 'MCP tools/list has no error');
  assert(toolsListResponse.result && toolsListResponse.result.tools && toolsListResponse.result.tools.length > 0, 'MCP tools/list returns non-empty tools array');
  
  // Test 5: MCP tools/call
  const { status: toolsCallStatus, json: toolsCallResponse } = await mcpCall('tools/call', {
    name: 'sober_thinking',
    arguments: {},
    toolRunId: 'test-run-' + Date.now()
  });
  
  assert(toolsCallStatus === 200, 'MCP tools/call returns 200 status');
  assert(!toolsCallResponse.error, 'MCP tools/call has no error');
  assert(toolsCallResponse.result && toolsCallResponse.result.content && toolsCallResponse.result.content.length > 0, 'MCP tools/call returns non-empty content array');
  
} catch (error) {
  console.error('Test error:', error);
  testsFailed++;
} finally {
  // Shut down the server
  server.kill();
  console.log(`\nTests completed: ${testsPassed} passed, ${testsFailed} failed`);
  process.exit(testsFailed > 0 ? 1 : 0);
}
