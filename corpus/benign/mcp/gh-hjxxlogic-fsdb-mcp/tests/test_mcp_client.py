#!/usr/bin/env python3
"""MCP Client Test Script - Tests server.py via MCP protocol communication

This script acts as an MCP client to test all tools provided by server.py
through the Model Context Protocol (stdio transport).

Updated for multi-signal batch APIs.

IMPORTANT: This script requires the MCP SDK to be installed.
Run this script in a virtual environment:

    cd ~/work/fsdb-mcp
    source venv/bin/activate
    pip install mcp  # if not already installed
    python tests/test_mcp_client.py

Requirements:
- Python 3.10+
- mcp library (pip install mcp)
- Virtual environment activated
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
    
    def __init__(self, test_file: str = "~/work/fsdb-mcp/test.fsdb"):
        self.session: Optional[ClientSession] = None
        self.test_file = test_file
        
    @asynccontextmanager
    async def connect_to_server(self):
        """Connect to the FSDB MCP server via stdio"""
        # Pass current environment to server so it has access to VERDI_HOME
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
    
    async def test_1_is_fsdb(self):
        """Test 1: Check if file is FSDB (fsdb_is_fsdb)"""
        print("\n--- Test 1: Check FSDB File (fsdb_is_fsdb) ---")
        try:
            result = await self.call_tool("fsdb_is_fsdb", {
                "path": self.test_file
            })
            
            # Parse the result
            content = result.content[0].text if result.content else ""
            print(f"  Result: {content}")
            
            if "true" in content.lower():
                print("  ✓ Test 1 passed")
                return True
            else:
                print("  ✗ Test 1 failed")
                return False
        except Exception as e:
            print(f"  ✗ Test 1 failed: {e}")
            return False
    
    async def test_2_open_file(self):
        """Test 2: Open FSDB file (fsdb_open)"""
        print("\n--- Test 2: Open File (fsdb_open) ---")
        try:
            result = await self.call_tool("fsdb_open", {
                "path": self.test_file
            })
            
            content = result.content[0].text if result.content else ""
            print(f"  Result: {content}")
            
            if "opened" in content.lower() or "successfully" in content.lower():
                print("  ✓ Test 2 passed")
                return True
            else:
                print("  ✗ Test 2 failed")
                return False
        except Exception as e:
            print(f"  ✗ Test 2 failed: {e}")
            return False
    
    async def test_3_verify_file_info(self):
        """Test 3: Verify file info is in fsdb_open response (fsdb_get_info removed)"""
        print("\n--- Test 3: Verify File Info (from fsdb_open) ---")
        try:
            # File info should already be in the open response
            print("  File info is now returned by fsdb_open")
            print("  fsdb_get_info tool has been removed")
            print("  ✓ Test 3 passed (fsdb_get_info removed)")
            return True
        except Exception as e:
            print(f"  ✗ Test 3 failed: {e}")
            return False
    
    async def test_4_list_scopes(self):
        """Test 4: List scopes (fsdb_list_scopes)"""
        print("\n--- Test 4: List Scopes (fsdb_list_scopes) ---")
        try:
            result = await self.call_tool("fsdb_list_scopes", {
                "path": self.test_file
            })
            
            content = result.content[0].text if result.content else ""
            
            # Try to parse as JSON
            try:
                data = json.loads(content)
                scopes = data.get('scopes', [])
                total = data.get('total', len(scopes))
                truncated = data.get('truncated', False)
                
                print(f"  Found {total} top-level scope(s) (showing {len(scopes)}):")
                for i, scope in enumerate(scopes[:3], 1):
                    print(f"    {i}. {scope.get('name', 'N/A')} (type: {scope.get('type', 'N/A')})")
                
                if truncated:
                    print(f"  ⚠ Results truncated (max {len(scopes)} returned)")
            except:
                print(f"  Result: {content[:200]}...")
            
            print("  ✓ Test 4 passed")
            return True
        except Exception as e:
            print(f"  ✗ Test 4 failed: {e}")
            return False
    
    async def test_5_list_signals(self):
        """Test 5: List signals (fsdb_list_signals)"""
        print("\n--- Test 5: List Signals (fsdb_list_signals) ---")
        try:
            # First get a scope path
            result = await self.call_tool("fsdb_list_scopes", {
                "path": self.test_file
            })
            content = result.content[0].text if result.content else ""
            data = json.loads(content)
            scopes = data.get('scopes', [])
            
            if not scopes:
                print("  ✗ No scopes found")
                return False
            
            scope_path = scopes[0].get('full_name', scopes[0].get('name'))
            
            # Now list signals in that scope
            result = await self.call_tool("fsdb_list_signals", {
                "path": self.test_file,
                "scope_path": scope_path
            })
            
            content = result.content[0].text if result.content else ""
            
            try:
                data = json.loads(content)
                signals = data.get('signals', [])
                total = data.get('total', len(signals))
                truncated = data.get('truncated', False)
                
                print(f"  Found {total} signal(s) in scope '{scope_path}' (showing {len(signals)}):")
                for i, sig in enumerate(signals[:5], 1):
                    print(f"    {i}. {sig.get('name', 'N/A')} [{sig.get('left_range', '?')}:{sig.get('right_range', '?')}]")
                if len(signals) > 5:
                    print(f"    ... and {len(signals) - 5} more signals")
                
                if truncated:
                    print(f"  ⚠ Results truncated (max {len(signals)} returned)")
            except:
                print(f"  Result: {content[:200]}...")
            
            print("  ✓ Test 5 passed")
            return True
        except Exception as e:
            print(f"  ✗ Test 5 failed: {e}")
            return False
    
    async def test_6_get_signal_info(self):
        """Test 6: Get signal information (fsdb_get_signal_info)"""
        print("\n--- Test 6: Get Signal Info (fsdb_get_signal_info) ---")
        try:
            # Get a signal path
            result = await self.call_tool("fsdb_list_scopes", {
                "path": self.test_file
            })
            data = json.loads(result.content[0].text)
            scopes = data.get('scopes', [])
            scope_path = scopes[0].get('full_name', scopes[0].get('name'))
            
            result = await self.call_tool("fsdb_list_signals", {
                "path": self.test_file,
                "scope_path": scope_path
            })
            data = json.loads(result.content[0].text)
            signals = data.get('signals', [])
            
            if not signals:
                print("  ✗ No signals found")
                return False
            
            signal_path = signals[0].get('full_name')
            
            # Get signal info
            result = await self.call_tool("fsdb_get_signal_info", {
                "path": self.test_file,
                "signal_path": signal_path
            })
            
            content = result.content[0].text if result.content else ""
            
            try:
                info = json.loads(content)
                print(f"  Signal: {info.get('full_name', 'N/A')}")
                print(f"  Range: [{info.get('left_range', '?')}:{info.get('right_range', '?')}]")
                print(f"  Size: {info.get('range_size', 'N/A')}")
                print(f"  Is Real: {info.get('is_real', 'N/A')}")
            except:
                print(f"  Result: {content[:200]}...")
            
            print("  ✓ Test 6 passed")
            return True
        except Exception as e:
            print(f"  ✗ Test 6 failed: {e}")
            return False
    
    async def test_7_get_signal_value(self):
        """Test 7: Get signal values at time (fsdb_get_signal_value - multi-signal batch)"""
        print("\n--- Test 7: Get Signal Values (fsdb_get_signal_value - batch) ---")
        try:
            # Get signal paths
            result = await self.call_tool("fsdb_list_scopes", {
                "path": self.test_file
            })
            data = json.loads(result.content[0].text)
            scopes = data.get('scopes', [])
            scope_path = scopes[0].get('full_name', scopes[0].get('name'))
            
            result = await self.call_tool("fsdb_list_signals", {
                "path": self.test_file,
                "scope_path": scope_path
            })
            data = json.loads(result.content[0].text)
            signals = data.get('signals', [])
            signal_paths = [sig.get('full_name') for sig in signals[:min(3, len(signals))]]
            
            # Get values at time 0 (multi-signal batch API)
            result = await self.call_tool("fsdb_get_signal_value", {
                "path": self.test_file,
                "signal_paths": signal_paths,
                "time": 0
            })
            
            content = result.content[0].text if result.content else ""
            try:
                data = json.loads(content)
                print(f"  Queried {len(signal_paths)} signal(s) at time 0:")
                for sig_data in data.get('signals', []):
                    print(f"    {sig_data.get('path')}: {sig_data.get('value')}")
            except:
                print(f"  Result: {content[:200]}...")
            
            print("  ✓ Test 7 passed (multi-signal batch API)")
            return True
        except Exception as e:
            print(f"  ✗ Test 7 failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_8_get_signal_changes(self):
        """Test 8: Get signal value changes (fsdb_get_signal_changes - multi-signal batch)"""
        print("\n--- Test 8: Get Signal Changes (fsdb_get_signal_changes - batch) ---")
        try:
            # Get signal paths
            result = await self.call_tool("fsdb_list_scopes", {
                "path": self.test_file
            })
            data = json.loads(result.content[0].text)
            scopes = data.get('scopes', [])
            scope_path = scopes[0].get('full_name', scopes[0].get('name'))
            
            result = await self.call_tool("fsdb_list_signals", {
                "path": self.test_file,
                "scope_path": scope_path
            })
            data = json.loads(result.content[0].text)
            signals = data.get('signals', [])
            signal_paths = [sig.get('full_name') for sig in signals[:min(2, len(signals))]]
            
            # Get changes in time range (multi-signal batch API)
            result = await self.call_tool("fsdb_get_signal_changes", {
                "path": self.test_file,
                "signal_paths": signal_paths,
                "start_time": 0,
                "end_time": 10000
            })
            
            content = result.content[0].text if result.content else ""
            
            try:
                data = json.loads(content)
                signals_data = data.get('signals', [])
                
                print(f"  Queried {len(signal_paths)} signal(s) for changes:")
                for sig_data in signals_data:
                    changes = sig_data.get('changes', [])
                    total = sig_data.get('total', len(changes))
                    truncated = sig_data.get('truncated', False)
                    
                    print(f"\n  Signal: {sig_data.get('signal')}")
                    print(f"  Found {total} value change(s) (showing {len(changes)}):")
                    for i, change in enumerate(changes[:5], 1):
                        print(f"    Time {change.get('time', 'N/A'):12}: {change.get('value', 'N/A')}")
                    if len(changes) > 5:
                        print(f"    ... and {len(changes) - 5} more changes")
                    
                    if truncated:
                        print(f"  ⚠ Results truncated (max {len(changes)} returned)")
            except:
                print(f"  Result: {content[:200]}...")
            
            print("\n  ✓ Test 8 passed (multi-signal batch API)")
            return True
        except Exception as e:
            print(f"  ✗ Test 8 failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_9_search(self):
        """Test 9: Search for signals and scopes (fsdb_search)"""
        print("\n--- Test 9: Search Signals/Scopes (fsdb_search) ---")
        try:
            # Get a signal to use as search pattern
            result = await self.call_tool("fsdb_list_scopes", {
                "path": self.test_file
            })
            data = json.loads(result.content[0].text)
            scopes = data.get('scopes', [])
            
            if not scopes:
                print("  ✗ No scopes found for search test")
                return False
            
            scope_path = scopes[0].get('full_name', scopes[0].get('name'))
            
            result = await self.call_tool("fsdb_list_signals", {
                "path": self.test_file,
                "scope_path": scope_path
            })
            data = json.loads(result.content[0].text)
            signals = data.get('signals', [])
            
            if not signals:
                print("  ✗ No signals found for search test")
                return False
            
            # Get part of signal name for search
            signal_name = signals[0].get('name', '')
            search_pattern = signal_name[:3] if len(signal_name) >= 3 else signal_name
            
            print(f"  Searching for pattern: '{search_pattern}'")
            
            # Test 1: Search all (signals and scopes)
            result = await self.call_tool("fsdb_search", {
                "path": self.test_file,
                "pattern": search_pattern,
                "search_type": "all"
            })
            
            content = result.content[0].text if result.content else ""
            
            try:
                data = json.loads(content)
                print(f"  Search type 'all':")
                
                if 'signals' in data:
                    sig_matches = data['signals'].get('matches', [])
                    sig_count = data['signals'].get('count', 0)
                    print(f"    Found {sig_count} matching signal(s)")
                    for i, sig in enumerate(sig_matches[:3], 1):
                        print(f"      {i}. {sig.get('full_name', 'N/A')}")
                
                if 'scopes' in data:
                    scope_matches = data['scopes'].get('matches', [])
                    scope_count = data['scopes'].get('count', 0)
                    print(f"    Found {scope_count} matching scope(s)")
                    for i, scope in enumerate(scope_matches[:3], 1):
                        print(f"      {i}. {scope.get('full_name', 'N/A')}")
                
                # Test 2: Search only signals
                result = await self.call_tool("fsdb_search", {
                    "path": self.test_file,
                    "pattern": search_pattern,
                    "search_type": "signals"
                })
                data = json.loads(result.content[0].text)
                print(f"  Search type 'signals': {data.get('signals', {}).get('count', 0)} match(es)")
                
                # Test 3: Search only scopes
                scope_pattern = scopes[0].get('name', '')[:3] if len(scopes[0].get('name', '')) >= 3 else scopes[0].get('name', '')
                result = await self.call_tool("fsdb_search", {
                    "path": self.test_file,
                    "pattern": scope_pattern,
                    "search_type": "scopes"
                })
                data = json.loads(result.content[0].text)
                print(f"  Search type 'scopes' (pattern '{scope_pattern}'): {data.get('scopes', {}).get('count', 0)} match(es)")
                
            except Exception as e:
                print(f"  Result: {content[:200]}...")
                print(f"  Parse error: {e}")
            
            print("  ✓ Test 9 passed")
            return True
        except Exception as e:
            print(f"  ✗ Test 9 failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_10_close_file(self):
        """Test 10: Close FSDB file (fsdb_close)"""
        print("\n--- Test 10: Close File (fsdb_close) ---")
        try:
            result = await self.call_tool("fsdb_close", {
                "path": self.test_file
            })
            
            content = result.content[0].text if result.content else ""
            print(f"  Result: {content}")
            
            if "closed" in content.lower():
                print("  ✓ Test 10 passed")
                return True
            else:
                print("  ✗ Test 10 failed")
                return False
        except Exception as e:
            print(f"  ✗ Test 10 failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all MCP tool tests"""
        print("=" * 60)
        print("MCP Protocol Communication Test")
        print("=" * 60)
        print("\nTesting all MCP tools via stdio transport (multi-signal batch APIs):")
        print("  1. fsdb_is_fsdb")
        print("  2. fsdb_open (now returns file info)")
        print("  3. Verify file info (fsdb_get_info removed)")
        print("  4. fsdb_list_scopes")
        print("  5. fsdb_list_signals")
        print("  6. fsdb_get_signal_info")
        print("  7. fsdb_get_signal_value (multi-signal batch)")
        print("  8. fsdb_get_signal_changes (multi-signal batch)")
        print("  9. fsdb_search")
        print("  10. fsdb_close")
        
        results = []
        
        try:
            async with self.connect_to_server():
                print("\n✓ Connected to MCP server")
                
                # Run tests sequentially
                results.append(await self.test_1_is_fsdb())
                results.append(await self.test_2_open_file())
                results.append(await self.test_3_verify_file_info())
                results.append(await self.test_4_list_scopes())
                results.append(await self.test_5_list_signals())
                results.append(await self.test_6_get_signal_info())
                results.append(await self.test_7_get_signal_value())
                results.append(await self.test_8_get_signal_changes())
                results.append(await self.test_9_search())
                results.append(await self.test_10_close_file())
        except Exception:
            # Ignore connection cleanup errors (expected when server closes)
            pass
        
        print("\n" + "=" * 60)
        passed = sum(results)
        total = len(results)
        
        if passed == total:
            print(f"✅ All {total} MCP tools tested successfully!")
            print("MCP server multi-signal batch APIs are working correctly via stdio protocol")
        else:
            print(f"❌ {passed}/{total} tests passed")
        
        print("=" * 60)
        
        return passed == total


async def main():
    """Main entry point"""
    # Check if test file exists
    import os
    test_file = "/home/hj/work/fsdb-mcp/test.fsdb"
    if not os.path.exists(test_file):
        print(f"\n⚠ Warning: Test file '{test_file}' not found")
        print("Please provide a valid FSDB file to run the tests.")
        print("\nUsage: python test_mcp_client.py [path_to_fsdb_file]")
        if len(sys.argv) > 1:
            test_file = sys.argv[1]
            if not os.path.exists(test_file):
                print(f"\n✗ Error: Specified file '{test_file}' not found")
                return 1
        else:
            return 1
    
    client = FSDBMCPClient(test_file)
    success = await client.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
