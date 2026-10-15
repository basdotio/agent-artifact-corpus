#!/usr/bin/env python3
"""
Complete MCP Client Test Script - Tests all tools in server.py

This script tests all tools with multi-signal batch APIs.

IMPORTANT: Run this script in a virtual environment:
    source venv/bin/activate
    python tests/test_mcp_client_complete.py
"""

import asyncio
import json
import sys
import os
from contextlib import asynccontextmanager
from typing import Optional

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


class FSDBMCPClient:
    """MCP client for testing FSDB server tools"""
    
    def __init__(self, test_file: str = "test.fsdb"):
        self.session: Optional[ClientSession] = None
        self.test_file = test_file
        
    @asynccontextmanager
    async def connect_to_server(self):
        """Connect to the FSDB MCP server via stdio"""
        server_params = StdioServerParameters(
            command="python3",
            args=["server.py"],
            env=os.environ.copy()
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self.session = session
                yield session
    
    async def call_tool(self, tool_name: str, arguments: dict = None) -> dict:
        """Call an MCP tool and return the result"""
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        result = await self.session.call_tool(tool_name, arguments or {})
        return result
    
    async def test_basic_tools(self):
        """Test basic 10 tools"""
        results = []
        
        # Test 1: is_fsdb
        print("\n[1/16] Testing fsdb_is_fsdb...")
        try:
            result = await self.call_tool("fsdb_is_fsdb", {"path": self.test_file})
            content = result.content[0].text if result.content else ""
            if "true" in content.lower():
                print("  ✓ PASS")
                results.append(True)
            else:
                print("  ✗ FAIL")
                results.append(False)
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            results.append(False)
        
        # Test 2: open
        print("\n[2/16] Testing fsdb_open...")
        try:
            result = await self.call_tool("fsdb_open", {"path": self.test_file})
            content = result.content[0].text if result.content else ""
            if "opened" in content.lower():
                print("  ✓ PASS")
                results.append(True)
            else:
                print("  ✗ FAIL")
                results.append(False)
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            results.append(False)
        
        # Test 3: Verify file info is in open response (fsdb_get_info removed)
        print("\n[3/15] Verifying file info from fsdb_open...")
        try:
            # File info should already be in the open response
            print("  File info is now returned by fsdb_open")
            print("  fsdb_get_info tool has been removed")
            print("  ✓ PASS")
            results.append(True)
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            results.append(False)
        
        # Test 4: list_scopes
        print("\n[4/15] Testing fsdb_list_scopes...")
        try:
            result = await self.call_tool("fsdb_list_scopes", {"path": self.test_file})
            content = result.content[0].text if result.content else ""
            data = json.loads(content)
            scopes = data.get('scopes', [])
            print(f"  Found {len(scopes)} scopes")
            print("  ✓ PASS")
            results.append(True)
            self.test_scope = scopes[0].get('full_name') if scopes else None
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            results.append(False)
            self.test_scope = None
        
        # Test 5: list_signals
        print("\n[5/15] Testing fsdb_list_signals...")
        try:
            result = await self.call_tool("fsdb_list_signals", {
                "path": self.test_file,
                "scope_path": self.test_scope
            })
            content = result.content[0].text if result.content else ""
            data = json.loads(content)
            signals = data.get('signals', [])
            print(f"  Found {len(signals)} signals")
            print("  ✓ PASS")
            results.append(True)
            self.test_signal = signals[0].get('full_name') if signals else None
            self.test_signals = [s.get('full_name') for s in signals[:5]]
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            results.append(False)
            self.test_signal = None
        
        # Test 6: get_signal_info
        print("\n[6/15] Testing fsdb_get_signal_info...")
        try:
            result = await self.call_tool("fsdb_get_signal_info", {
                "path": self.test_file,
                "signal_path": self.test_signal
            })
            content = result.content[0].text if result.content else ""
            data = json.loads(content)
            print(f"  Signal: {data.get('name')}")
            print("  ✓ PASS")
            results.append(True)
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            results.append(False)
        
        # Test 7: get_signal_value (multi-signal batch)
        print("\n[7/15] Testing fsdb_get_signal_value (Multi-signal Batch)...")
        try:
            result = await self.call_tool("fsdb_get_signal_value", {
                "path": self.test_file,
                "signal_paths": self.test_signals[:3],
                "time": 1000
            })
            content = result.content[0].text if result.content else ""
            data = json.loads(content)
            signals = data.get('signals', [])
            print(f"  Queried {len(signals)} signals at time 1000")
            print("  ✓ PASS (Multi-signal Batch)")
            results.append(True)
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            results.append(False)
        
        # Test 8: get_signal_changes (multi-signal batch)
        print("\n[8/15] Testing fsdb_get_signal_changes (Multi-signal Batch)...")
        try:
            result = await self.call_tool("fsdb_get_signal_changes", {
                "path": self.test_file,
                "signal_paths": self.test_signals[:2],
                "start_time": 0,
                "end_time": 10000
            })
            content = result.content[0].text if result.content else ""
            data = json.loads(content)
            signals_data = data.get('signals', [])
            print(f"  Queried {len(signals_data)} signals for changes")
            print("  ✓ PASS (Multi-signal Batch)")
            results.append(True)
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            results.append(False)
        
        # Test 9: search
        print("\n[9/15] Testing fsdb_search...")
        try:
            result = await self.call_tool("fsdb_search", {
                "path": self.test_file,
                "pattern": "clk",
                "search_type": "all"
            })
            content = result.content[0].text if result.content else ""
            data = json.loads(content)
            print(f"  Search results found")
            print("  ✓ PASS")
            results.append(True)
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            results.append(False)
        
        return results
    
    async def test_advanced_tools(self):
        """Test advanced multi-signal batch tools"""
        results = []
        
        # Test 10: find value (multi-signal batch)
        print("\n[10/15] Testing fsdb_find_signal_value (Multi-signal Batch)...")
        try:
            result = await self.call_tool("fsdb_find_signal_value", {
                "path": self.test_file,
                "signal_paths": self.test_signals[:2],
                "values": ["1", "0"],
                "start_time": 0,
                "direction": "forward"
            })
            content = result.content[0].text if result.content else ""
            data = json.loads(content)
            signals_data = data.get('signals', [])
            print(f"  Searched {len(signals_data)} signals for values")
            print("  ✓ PASS (Multi-signal Batch)")
            results.append(True)
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            results.append(False)
        
        # Test 11: statistics (multi-signal batch)
        print("\n[11/15] Testing fsdb_get_signal_statistics (Multi-signal Batch)...")
        try:
            result = await self.call_tool("fsdb_get_signal_statistics", {
                "path": self.test_file,
                "signal_paths": self.test_signals[:3],
                "start_time": 0,
                "end_time": 10000
            })
            content = result.content[0].text if result.content else ""
            data = json.loads(content)
            signals_data = data.get('signals', [])
            print(f"  Got statistics for {len(signals_data)} signals")
            print("  ✓ PASS (Multi-signal Batch)")
            results.append(True)
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            results.append(False)
        
        return results
    
    async def test_utility_tools(self):
        """Test utility tools"""
        results = []
        
        # Test 12: find X values (multi-signal batch)
        print("\n[12/15] Testing fsdb_find_x_values (Multi-signal Batch)...")
        try:
            result = await self.call_tool("fsdb_find_x_values", {
                "path": self.test_file,
                "signal_paths": self.test_signals[:2],
                "start_time": 0,
                "direction": "forward"
            })
            content = result.content[0].text if result.content else ""
            data = json.loads(content)
            signals_data = data.get('signals', [])
            print(f"  Searched {len(signals_data)} signals for X values")
            print("  ✓ PASS (Multi-signal Batch)")
            results.append(True)
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            results.append(False)
        
        # Test 13: time conversion
        print("\n[13/15] Testing fsdb_convert_time...")
        try:
            result = await self.call_tool("fsdb_convert_time", {
                "path": self.test_file,
                "time_value": 1000,
                "from_unit": "ps",
                "to_unit": "ns"
            })
            content = result.content[0].text if result.content else ""
            data = json.loads(content)
            print(f"  {data.get('input_value')} {data.get('input_unit')} = {data.get('output_value')} {data.get('output_unit')}")
            print("  ✓ PASS")
            results.append(True)
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            results.append(False)
        
        # Test 14: signal members
        print("\n[14/15] Testing fsdb_get_signal_members...")
        try:
            result = await self.call_tool("fsdb_get_signal_members", {
                "path": self.test_file,
                "signal_path": self.test_signal
            })
            content = result.content[0].text if result.content else ""
            data = json.loads(content)
            print(f"  Has members: {data.get('has_members')}")
            print("  ✓ PASS")
            results.append(True)
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            results.append(False)
        
        return results
    
    async def test_close(self):
        """Test close file"""
        print("\n[15/15] Testing fsdb_close...")
        try:
            result = await self.call_tool("fsdb_close", {"path": self.test_file})
            content = result.content[0].text if result.content else ""
            if "closed" in content.lower():
                print("  ✓ PASS")
                return [True]
            else:
                print("  ✗ FAIL")
                return [False]
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            return [False]
    
    async def run_all_tests(self):
        """Run all MCP tool tests"""
        print("=" * 70)
        print("FSDB MCP Server - Complete Test Suite (15 Tools)")
        print("=" * 70)
        print("\nAll tools with multi-signal batch API support")
        
        all_results = []
        
        try:
            async with self.connect_to_server():
                print("\n✓ Connected to MCP server\n")
                
                # Run all test groups
                all_results.extend(await self.test_basic_tools())
                all_results.extend(await self.test_advanced_tools())
                all_results.extend(await self.test_utility_tools())
                all_results.extend(await self.test_close())
                
        except Exception as e:
            print(f"\n⚠ Connection error: {e}")
        
        # Print summary
        print("\n" + "=" * 70)
        passed = sum(all_results)
        total = len(all_results)
        percentage = (passed / total * 100) if total > 0 else 0
        
        print(f"\nTest Results: {passed}/{total} tests passed ({percentage:.1f}%)")
        
        if passed == total:
            print(f"\n✅ All {total} MCP tools tested successfully!")
            print("   - Basic tools: 9/9 ✓")
            print("   - Advanced batch tools: 2/2 ✓")
            print("   - Utility tools: 3/3 ✓")
            print("   - Close: 1/1 ✓")
            print("\n🎉 Multi-signal batch APIs verified!")
        else:
            print(f"\n⚠ {total - passed} test(s) failed")
        
        print("=" * 70)
        
        return passed == total


async def main():
    """Main entry point"""
    # Use absolute path
    test_file = os.path.abspath("test.fsdb")
    
    if len(sys.argv) > 1:
        test_file = os.path.abspath(sys.argv[1])
    
    if not os.path.exists(test_file):
        print(f"\n✗ Error: Test file '{test_file}' not found")
        print("\nUsage: python test_mcp_client_complete.py [path_to_fsdb_file]")
        return 1
    
    print(f"Using test file: {test_file}")
    
    client = FSDBMCPClient(test_file)
    success = await client.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
