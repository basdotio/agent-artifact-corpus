#!/usr/bin/env node
// Prompts feature test for LSP MCP server

import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import path from 'path';
import fsSync from 'fs';
import assert from 'assert';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { ReadBuffer, serializeMessage } from '@modelcontextprotocol/sdk/shared/stdio.js';

// Get the current file's directory
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Custom transport that works with an existing child process
class CustomStdioTransport {
  constructor(childProcess) {
    this.childProcess = childProcess;
    this.readBuffer = new ReadBuffer();
    this.onmessage = null;
    this.onerror = null;
    this.onclose = null;

    this._setupListeners();
  }

  _setupListeners() {
    // Set up stdout handler for responses
    this.childProcess.stdout.on('data', (data) => {
      this.readBuffer.append(data);
      this._processReadBuffer();
    });

    // Set up error handler
    this.childProcess.on('error', (error) => {
      if (this.onerror) this.onerror(error);
    });

    // Set up close handler
    this.childProcess.on('close', (code) => {
      if (this.onclose) this.onclose();
    });

    // Handle errors on streams
    this.childProcess.stdout.on('error', (error) => {
      if (this.onerror) this.onerror(error);
    });

    this.childProcess.stdin.on('error', (error) => {
      if (this.onerror) this.onerror(error);
    });
  }

  _processReadBuffer() {
    while (true) {
      try {
        const message = this.readBuffer.readMessage();
        if (message === null) {
          break;
        }
        if (this.onmessage) this.onmessage(message);
      } catch (error) {
        if (this.onerror) this.onerror(error);
      }
    }
  }

  async start() {
    // No need to start since we're using an existing process
    return Promise.resolve();
  }

  async close() {
    // Don't actually kill the process here - we'll handle that separately
    this.readBuffer.clear();
  }

  send(message) {
    return new Promise((resolve) => {
      if (!this.childProcess.stdin) {
        throw new Error('Not connected');
      }

      const json = serializeMessage(message);
      console.log('>>> SENDING:', json.toString().trim());

      if (this.childProcess.stdin.write(json)) {
        resolve();
      } else {
        this.childProcess.stdin.once('drain', resolve);
      }
    });
  }
}

// Path to our compiled server script and the typescript-language-server binary
const LSP_MCP_SERVER = path.join(__dirname, '..', 'dist', 'index.js');
const TS_SERVER_BIN = path.join(__dirname, '..', 'node_modules', '.bin', 'typescript-language-server');

// Check prerequisites
try {
  const stats = fsSync.statSync(TS_SERVER_BIN);
  if (!stats.isFile()) {
    console.error(`Error: The typescript-language-server at '${TS_SERVER_BIN}' is not a file`);
    process.exit(1);
  }
} catch (error) {
  console.error(`Error: Could not find typescript-language-server at '${TS_SERVER_BIN}'`);
  console.error('Make sure you have installed the typescript-language-server as a dev dependency');
  process.exit(1);
}

if (!fsSync.existsSync(LSP_MCP_SERVER)) {
  console.error(`ERROR: LSP MCP server not found at ${LSP_MCP_SERVER}`);
  console.error(`Make sure you've built the project with 'npm run build'`);
  process.exit(1);
}

class PromptsTester {
  constructor() {
    this.client = null;
    this.serverProcess = null;
    this.testResults = {
      passed: [],
      failed: []
    };
  }

  async start() {
    // Start the MCP server
    console.log(`Starting MCP server: node ${LSP_MCP_SERVER} typescript ${TS_SERVER_BIN} --stdio`);

    this.serverProcess = spawn('node', [LSP_MCP_SERVER, 'typescript', TS_SERVER_BIN, '--stdio'], {
      env: {
        ...process.env,
        DEBUG: 'true',
        LOG_LEVEL: 'debug'
      },
      stdio: ['pipe', 'pipe', 'pipe']
    });

    console.log(`MCP server started with PID: ${this.serverProcess.pid}`);

    // Set up stderr handler for logging
    this.serverProcess.stderr.on('data', (data) => {
      console.log(`SERVER STDERR: ${data.toString().trim()}`);
    });

    // Set up error handler
    this.serverProcess.on('error', (error) => {
      console.error(`SERVER ERROR: ${error.message}`);
    });

    // Create our custom transport with the existing server process
    const transport = new CustomStdioTransport(this.serverProcess);

    // Create the client with proper initialization
    this.client = new Client(
      // clientInfo
      {
        name: "prompts-test-client",
        version: "1.0.0"
      },
      // options
      {
        capabilities: {
          tools: true,
          resources: true,
          prompts: true,
          logging: true
        }
      }
    );

    // Connect client to the transport
    try {
      await this.client.connect(transport);
      console.log("Connected to MCP server successfully");
    } catch (error) {
      console.error("Failed to connect to MCP server:", error);
      throw error;
    }

    // Wait a bit to ensure everything is initialized
    await new Promise(resolve => setTimeout(resolve, 2000));

    return this;
  }

  stop() {
    if (this.serverProcess) {
      console.log("Sending SIGINT to MCP server");
      this.serverProcess.kill('SIGINT');
      this.serverProcess = null;
    }
  }

  // Helper method to run a test case and record result
  async runTest(name, func) {
    console.log(`\nTest: ${name}`);
    try {
      await func();
      console.log(`✅ Test passed: ${name}`);
      this.testResults.passed.push(name);
      return true;
    } catch (error) {
      console.error(`❌ Test failed: ${name}`);
      console.error(`Error: ${error.message}`);
      this.testResults.failed.push(name);
      return false;
    }
  }

  // Test listing the available prompts
  async testListPrompts() {
    console.log("Listing available prompts...");

    try {
      const response = await this.client.listPrompts();

      // Extract the prompts array
      let prompts = [];
      if (response && response.prompts && Array.isArray(response.prompts)) {
        prompts = response.prompts;
      } else if (Array.isArray(response)) {
        prompts = response;
      } else {
        console.log("Unexpected prompts response format:", response);
        prompts = []; // Ensure we have an array to work with
      }

      console.log(`Found ${prompts.length} prompts`);
      prompts.forEach(prompt => {
        if (prompt && prompt.name) {
          console.log(`- ${prompt.name}: ${prompt.description || 'No description'}`);
          
          if (prompt.arguments && prompt.arguments.length > 0) {
            console.log(`  Arguments:`);
            prompt.arguments.forEach(arg => {
              console.log(`  - ${arg.name}: ${arg.description} (${arg.required ? 'required' : 'optional'})`);
            });
          }
        }
      });

      // If we didn't get any prompts, we'll fail the test
      if (prompts.length === 0) {
        throw new Error("No prompts returned");
      }

      // Verify we have the expected prompts
      const requiredPrompts = ['lsp_guide'];

      const missingPrompts = requiredPrompts.filter(prompt =>
        !prompts.some(p => p.name === prompt)
      );

      if (missingPrompts.length > 0) {
        throw new Error(`Missing expected prompts: ${missingPrompts.join(', ')}`);
      }

      return prompts;
    } catch (error) {
      console.error(`Error listing prompts: ${error.message}`);
      throw error;
    }
  }

  // Test getting a prompt
  async testGetPrompt(name, args = {}) {
    console.log(`Getting prompt: ${name}`);
    
    try {
      const params = {
        name: name,
        arguments: args
      };

      const result = await this.client.getPrompt(params);
      console.log(`Prompt result:`, JSON.stringify(result, null, 2));

      // Basic validation
      assert(result && result.messages && Array.isArray(result.messages),
        'Expected messages array in the result');
      
      assert(result.messages.length > 0,
        'Expected at least one message in the result');
      
      // Check for user and assistant roles
      const hasUserMessage = result.messages.some(m => m.role === 'user');
      const hasAssistantMessage = result.messages.some(m => m.role === 'assistant');
      
      assert(hasUserMessage, 'Expected a user message in the result');
      assert(hasAssistantMessage, 'Expected an assistant message in the result');

      return result;
    } catch (error) {
      console.error(`Failed to get prompt ${name}:`, error);
      throw error;
    }
  }

  // Print a summary of the test results
  printResults() {
    console.log('\n=== Test Results ===');
    console.log(`Passed: ${this.testResults.passed.length}/${this.testResults.passed.length + this.testResults.failed.length}`);

    console.log('\nPassed Tests:');
    for (const test of this.testResults.passed) {
      console.log(`  ✅ ${test}`);
    }

    console.log('\nFailed Tests:');
    for (const test of this.testResults.failed) {
      console.log(`  ❌ ${test}`);
    }

    if (this.testResults.failed.length > 0) {
      console.log('\n❌ Some tests failed');
      return false;
    } else if (this.testResults.passed.length === 0) {
      console.log('\n❌ No tests passed');
      return false;
    } else {
      console.log('\n✅ All tests passed');
      return true;
    }
  }
}

// Run the tests
async function runTests() {
  console.log('=== LSP MCP Prompts Feature Tests ===');

  const tester = await new PromptsTester().start();

  try {
    // Test listing prompts
    await tester.runTest('List prompts', async () => {
      await tester.testListPrompts();
    });

    // Test getting the LSP guide prompt
    await tester.runTest('Get LSP guide prompt', async () => {
      await tester.testGetPrompt('lsp_guide');
    });

  } catch (error) {
    console.error('ERROR in tests:', error);
  } finally {
    // Print results
    const allPassed = tester.printResults();

    // Clean up
    console.log('\nShutting down tester...');
    tester.stop();

    // Exit with appropriate status code
    process.exit(allPassed ? 0 : 1);
  }
}

// Execute the tests
console.log('Starting LSP MCP Prompts tests');
runTests().catch(error => {
  console.error('Unhandled error:', error);
  process.exit(1);
});
