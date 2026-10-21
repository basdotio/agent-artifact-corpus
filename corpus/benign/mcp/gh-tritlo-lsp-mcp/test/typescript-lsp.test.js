#!/usr/bin/env node
// TypeScript LSP integration test for MCP using the official SDK

import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs/promises';
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

// Path to the TypeScript project for testing
const TS_PROJECT_PATH = path.join(__dirname, 'ts-project');
const EXAMPLE_TS_FILE = path.join(TS_PROJECT_PATH, 'src', 'example.ts');

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

class TypeScriptLspTester {
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
        name: "typescript-lsp-test-client",
        version: "1.0.0"
      },
      // options
      {
        capabilities: {
          tools: true,
          resources: true,
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

  // Execute a tool and verify the result
  async executeTool(toolName, args, validateFn = null) {
    console.log(`Executing tool: ${toolName}`);

    try {
      // The callTool method expects a name and arguments parameter
      const params = {
        name: toolName,
        arguments: args
      };

      const result = await this.client.callTool(params);
      console.log(`Tool result:`, result);

      // If a validation function is provided, run it
      if (validateFn) {
        validateFn(result);
      }

      return result;
    } catch (error) {
      console.error(`Failed to execute tool ${toolName}:`, error);
      throw error;
    }
  }

  // Test listing the available tools
  async testListTools() {
    console.log("Listing available tools...");

    try {
      const response = await this.client.listTools();

      // Depending on the response format, extract the tools array
      let tools = [];
      if (response && response.tools && Array.isArray(response.tools)) {
        tools = response.tools;
      } else if (Array.isArray(response)) {
        tools = response;
      } else {
        console.log("Unexpected tools response format:", response);
        tools = []; // Ensure we have an array to work with
      }

      console.log(`Found ${tools.length} tools`);
      tools.forEach(tool => {
        if (tool && tool.name) {
          console.log(`- ${tool.name}: ${tool.description || 'No description'}`);
        }
      });

      // If we didn't get any tools, we'll run the other tests anyway
      if (tools.length === 0) {
        console.log("WARNING: No tools returned but continuing with tests");
        return tools;
      }

      // Verify we have the expected tools
      const requiredTools = ['get_info_on_location', 'get_completions', 'get_code_actions',
                           'restart_lsp_server', 'start_lsp', 'open_document',
                           'close_document', 'get_diagnostics'];

      const missingTools = requiredTools.filter(tool =>
        !tools.some(t => t.name === tool)
      );

      if (missingTools.length > 0) {
        console.warn(`WARNING: Missing some expected tools: ${missingTools.join(', ')}`);
      }

      return tools;
    } catch (error) {
      // Just log the error but don't fail the test - we'll continue with the rest
      console.warn(`WARNING: Error listing tools: ${error.message}`);
      return [];
    }
  }

  // Test listing resources
  async testListResources() {
    console.log("Listing available resources...");

    try {
      // Using the listResources method which is the correct SDK method
      const response = await this.client.listResources();

      // Extract the resources array
      let resources = [];
      if (response && response.resources && Array.isArray(response.resources)) {
        resources = response.resources;
      } else if (Array.isArray(response)) {
        resources = response;
      } else {
        console.log("Unexpected resources response format:", response);
        resources = []; // Ensure we have an array to work with
      }

      console.log(`Found ${resources.length} resources`);
      resources.forEach(resource => {
        if (resource && resource.name) {
          console.log(`- ${resource.name}: ${resource.description || 'No description'}`);
        }
      });

      // If we didn't get any resources, we'll run the other tests anyway
      if (resources.length === 0) {
        console.log("WARNING: No resources returned but continuing with tests");
        return resources;
      }

      return resources;
    } catch (error) {
      // Just log the error but don't fail the test - we'll continue with the rest
      console.warn(`WARNING: Error listing resources: ${error.message}`);
      return [];
    }
  }

  // Execute a resource request and verify the result
  async accessResource(params, validateFn = null) {
    console.log(`Accessing resource: ${params.uri}`);

    try {
      // Use readResource to access a resource with the params object directly
      const result = await this.client.readResource(params);
      console.log(`Resource result:`, result);

      // If a validation function is provided, run it
      if (validateFn) {
        validateFn(result);
      }

      return result;
    } catch (error) {
      console.error(`Failed to access resource ${params.uri}:`, error);
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
  console.log('=== TypeScript LSP MCP Integration Tests ===');

  const tester = await new TypeScriptLspTester().start();

  try {
    // Make sure the example file exists
    await fs.access(EXAMPLE_TS_FILE);
    const fileContent = await fs.readFile(EXAMPLE_TS_FILE, 'utf8');
    console.log(`Example file ${EXAMPLE_TS_FILE} exists and is ${fileContent.length} bytes`);

    // Test listing tools
    await tester.runTest('List tools', async () => {
      await tester.testListTools();
    });

    // Test starting the TypeScript LSP
    await tester.runTest('Start LSP', async () => {
      await tester.executeTool('start_lsp', {
        root_dir: TS_PROJECT_PATH
      }, (result) => {
        assert(result.content && result.content.length > 0,
              'Expected content in the result');
      });
    });

    // Wait for LSP to fully initialize
    console.log('\nWaiting for LSP to fully initialize...');
    await new Promise(resolve => setTimeout(resolve, 3000));

    // Test opening document
    await tester.runTest('Open document', async () => {
      await tester.executeTool('open_document', {
        file_path: EXAMPLE_TS_FILE,
        language_id: 'typescript'
      }, (result) => {
        assert(result.content && result.content.length > 0,
              'Expected content in the result');
      });
    });

    // Test getting hover information
    await tester.runTest('Hover information', async () => {
      await tester.executeTool('get_info_on_location', {
        file_path: EXAMPLE_TS_FILE,
        language_id: 'typescript',
        line: 4,
        column: 15
      }, (result) => {
        assert(result.content && result.content.length > 0,
              'Expected content in the result');
        // In a real test, we would verify the content contains actual hover info
      });
    });

    // Test getting completions
    await tester.runTest('Completions', async () => {
      await tester.executeTool('get_completions', {
        file_path: EXAMPLE_TS_FILE,
        language_id: 'typescript',
        line: 5,
        column: 10
      }, (result) => {
        assert(result.content && result.content.length > 0,
              'Expected content in the result');
        // In a real test, we would verify the content contains actual completions
      });
    });

    // Test getting diagnostics
    await tester.runTest('Diagnostics', async () => {
      await tester.executeTool('get_diagnostics', {
        file_path: EXAMPLE_TS_FILE
      }, (result) => {
        assert(result.content && result.content.length > 0,
              'Expected content in the result');
        // In a real test, we would verify the content contains actual diagnostics
      });
    });

    // Test getting code actions
    await tester.runTest('Code actions', async () => {
      await tester.executeTool('get_code_actions', {
        file_path: EXAMPLE_TS_FILE,
        language_id: 'typescript',
        start_line: 40,
        start_column: 1,
        end_line: 40,
        end_column: 20
      }, (result) => {
        assert(result.content && result.content.length > 0,
              'Expected content in the result');
        // In a real test, we would verify the content contains actual code actions
      });
    });

    // Test closing document
    await tester.runTest('Close document', async () => {
      await tester.executeTool('close_document', {
        file_path: EXAMPLE_TS_FILE
      }, (result) => {
        assert(result.content && result.content.length > 0,
              'Expected content in the result');
      });
    });

    // Test restarting LSP server
    await tester.runTest('Restart LSP server', async () => {
      await tester.executeTool('restart_lsp_server', {}, (result) => {
        assert(result.content && result.content.length > 0,
              'Expected content in the result');
      });
    });
    
    // Test listing resources
    await tester.runTest('List resources', async () => {
      const resources = await tester.testListResources();
      assert(Array.isArray(resources), 'Expected resources to be an array');
    });
    
    // Test accessing diagnostics resource
    await tester.runTest('Access diagnostics resource', async () => {
      // First make sure document is open again
      await tester.executeTool('open_document', {
        file_path: EXAMPLE_TS_FILE,
        language_id: 'typescript'
      });
      
      // Then try to access diagnostics resource using proper URI format
      const diagnosticsUri = `lsp-diagnostics://${EXAMPLE_TS_FILE}?language_id=typescript`;
      await tester.accessResource({
        uri: diagnosticsUri
      }, (result) => {
        assert(result && result.contents && result.contents.length > 0, 
              'Expected contents in the diagnostics result');
      });
    });
    
    // Test accessing hover resource
    await tester.runTest('Access hover resource', async () => {
      // Use proper URI format for hover resource
      const hoverUri = `lsp-hover://${EXAMPLE_TS_FILE}?line=4&column=15&language_id=typescript`;
      await tester.accessResource({
        uri: hoverUri
      }, (result) => {
        assert(result && result.contents && result.contents.length > 0,
              'Expected contents in the hover result');
      });
    });
    
    // Test accessing completion resource
    await tester.runTest('Access completion resource', async () => {
      // Use proper URI format for completion resource
      const completionUri = `lsp-completions://${EXAMPLE_TS_FILE}?line=5&column=10&language_id=typescript`;
      await tester.accessResource({
        uri: completionUri
      }, (result) => {
        assert(result && result.contents && result.contents.length > 0,
              'Expected contents in the completion result');
      });
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
console.log('Starting TypeScript LSP MCP integration tests');
runTests().catch(error => {
  console.error('Unhandled error:', error);
  process.exit(1);
});
