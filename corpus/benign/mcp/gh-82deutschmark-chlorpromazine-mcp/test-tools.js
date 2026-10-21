#!/usr/bin/env node
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';

async function testTools() {
  const transport = new SSEClientTransport(new URL('http://localhost:3000/sse'));
  const client = new Client({ name: 'test-client', version: '1.0.0' }, { capabilities: {} });
  
  try {
    await client.connect(transport);
    console.log('✅ Connected to MCP server');
    
    // List tools
    const toolsList = await client.listTools();
    console.log('\n📋 Available tools:', toolsList.tools.map(t => t.name));
    
    // Test sober_thinking
    console.log('\n🧪 Testing sober_thinking...');
    const soberResult = await client.callTool({ name: 'sober_thinking', arguments: {} });
    console.log('Result:', JSON.stringify(soberResult, null, 2).substring(0, 500));
    
    console.log('\n✅ All tests passed!');
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    process.exit(1);
  } finally {
    await client.close();
  }
}

testTools();
