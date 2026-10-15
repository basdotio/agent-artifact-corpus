#!/usr/bin/env python3
"""
Test script for FSDB reading functionality.
This script tests the waveform.py API without MCP dependencies.
"""

import os
import sys

# Setup VERDI environment
if "VERDI_HOME" in os.environ:
    rel_lib_path = os.environ["VERDI_HOME"] + "/share/NPI/python"
    sys.path.append(os.path.abspath(rel_lib_path))
    
    # Add LD_LIBRARY_PATH if needed
    if "LD_LIBRARY_PATH" in os.environ:
        os.environ['LD_LIBRARY_PATH'] = (
            os.environ['VERDI_HOME'] + '/share/NPI/lib/linux64:' +
            os.environ['VERDI_HOME'] + '/platform/linux64/bin:' +
            os.environ['LD_LIBRARY_PATH']
        )

try:
    from pynpi import npisys, waveform
    print("✓ Successfully imported pynpi and waveform")
except ImportError as e:
    print(f"✗ Failed to import pynpi: {e}")
    print("\nPlease ensure:")
    print("1. VERDI_HOME environment variable is set")
    print("2. Verdi is properly installed")
    print("3. LD_LIBRARY_PATH includes Verdi libraries")
    sys.exit(1)


def test_basic_functionality():
    """Test basic FSDB reading functionality."""
    print("\n=== Testing FSDB Basic Functionality ===\n")
    
    # Initialize NPI with proper arguments
    try:
        # npisys.init() expects sys.argv or empty list
        # Pass program name to avoid warning
        npisys.init(['test_fsdb'])
        print("✓ NPI initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize NPI: {e}")
        return False
    
    # Test is_fsdb function
    print("\n--- Testing is_fsdb() ---")
    test_file = "test.fsdb"
    
    if not os.path.exists(test_file):
        print(f"Note: Test file '{test_file}' not found")
        print("To fully test, provide a valid FSDB file path")
        # Cleanup and return
        try:
            npisys.end()
            print("\n✓ NPI shutdown successfully")
        except:
            pass
        return True
    
    is_fsdb = waveform.is_fsdb(test_file)
    print(f"is_fsdb('{test_file}'): {is_fsdb}")
    
    if not is_fsdb:
        print(f"✗ File is not a valid FSDB file")
        try:
            npisys.end()
            print("\n✓ NPI shutdown successfully")
        except:
            pass
        return True
    
    # Test open function
    print(f"\n--- Testing open() ---")
    try:
        file_handle = waveform.open(test_file)
        if file_handle:
            print(f"✓ Successfully opened: {test_file}")
            
            # Get file info
            print("\n--- File Information ---")
            print(f"Name: {file_handle.name()}")
            print(f"Min Time: {file_handle.min_time()}")
            print(f"Max Time: {file_handle.max_time()}")
            print(f"Scale Unit: {file_handle.scale_unit()}")
            print(f"Version: {file_handle.version()}")
            print(f"Sim Date: {file_handle.sim_date()}")
            print(f"Is Completed: {file_handle.is_completed()}")
            print(f"Has Glitch: {file_handle.has_glitch()}")
            
            # List top scopes
            print("\n--- Top Scopes ---")
            top_scopes = file_handle.top_scope_list()
            print(f"Found {len(top_scopes)} top-level scope(s)")
            for i, scope in enumerate(top_scopes[:5]):  # Show first 5
                print(f"  {i+1}. {scope.name()} (full: {scope.full_name()})")
            
            # List signals in first scope if available
            if top_scopes:
                print("\n--- Signals in First Scope ---")
                signals = top_scopes[0].sig_list()
                print(f"Found {len(signals)} signal(s)")
                for i, sig in enumerate(signals[:5]):  # Show first 5
                    print(f"  {i+1}. {sig.name()} (full: {sig.full_name()})")
                    print(f"      Range: [{sig.left_range()}:{sig.right_range()}], Size: {sig.range_size()}")
                
                # Test waveform reading
                if signals:
                    print("\n--- Testing Waveform Reading ---")
                    test_signal = signals[0]  # Use first signal
                    signal_path = test_signal.full_name()
                    print(f"Testing signal: {signal_path}")
                    
                    try:
                        # Test 1: Read signal value at specific time
                        print("\n1. Reading signal value at specific time:")
                        min_time = file_handle.min_time()
                        max_time = file_handle.max_time()
                        mid_time = (min_time + max_time) // 2
                        
                        # Add signal to load list
                        file_handle.reset_sig_list()
                        file_handle.add_to_sig_list(test_signal)
                        
                        # Load value changes for a time range
                        time_start = min_time
                        time_end = min(min_time + 10000, max_time)  # First 10000 time units
                        
                        print(f"   Loading value changes from {time_start} to {time_end}...")
                        file_handle.load_vc_by_range(time_start, time_end)
                        
                        # Create VCT (Value Change Table) handle
                        vct = test_signal.create_vct()
                        if vct:
                            # Get value at start time
                            if vct.goto_time(time_start):
                                val_hex = vct.value(waveform.VctFormat_e.HexStrVal)
                                val_bin = vct.value(waveform.VctFormat_e.BinStrVal)
                                print(f"   Time {time_start}: {val_hex} (hex), {val_bin} (bin)")
                            
                            # Test 2: Get all value changes
                            print("\n2. Reading value changes:")
                            changes = []
                            if vct.goto_first():
                                count = 0
                                max_changes = 10  # Limit to first 10 changes
                                
                                while count < max_changes:
                                    current_time = vct.time()
                                    value = vct.value(waveform.VctFormat_e.HexStrVal)
                                    changes.append((current_time, value))
                                    count += 1
                                    if not vct.goto_next():
                                        break
                                
                                print(f"   Found {len(changes)} value changes (showing first {max_changes}):")
                                for time, value in changes:
                                    print(f"   Time {time:12d}: {value}")
                            
                            # Test 3: Get value at specific time points
                            print("\n3. Sampling signal at multiple time points:")
                            sample_times = [time_start + i * 1000 for i in range(5)]
                            for t in sample_times:
                                if t <= time_end and vct.goto_time(t):
                                    val = vct.value(waveform.VctFormat_e.HexStrVal)
                                    print(f"   Time {t:12d}: {val}")
                        else:
                            print("   ✗ Failed to create VCT handle")
                        
                        # Unload value changes
                        file_handle.unload_vc()
                        print("\n   ✓ Value changes unloaded")
                        
                    except Exception as e:
                        print(f"   ✗ Error reading waveform: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Test with multiple signals
                if len(signals) >= 2:
                    print("\n--- Testing Multiple Signals ---")
                    print("Reading first 3 signals simultaneously:")
                    
                    try:
                        # Reset and add multiple signals
                        file_handle.reset_sig_list()
                        test_signals = signals[:3]
                        for sig in test_signals:
                            file_handle.add_to_sig_list(sig)
                        
                        # Load value changes
                        time_start = file_handle.min_time()
                        time_end = min(time_start + 5000, file_handle.max_time())
                        file_handle.load_vc_by_range(time_start, time_end)
                        
                        # Read values for each signal
                        for sig in test_signals:
                            vct = sig.create_vct()
                            if vct and vct.goto_time(time_start):
                                val = vct.value(waveform.VctFormat_e.HexStrVal)
                                print(f"  {sig.name():20s} @ {time_start}: {val}")
                        
                        file_handle.unload_vc()
                        print("  ✓ Multiple signals read successfully")
                        
                    except Exception as e:
                        print(f"  ✗ Error reading multiple signals: {e}")
            
            # Close file
            waveform.close(file_handle)
            print("\n✓ File closed successfully")
        else:
            print(f"✗ Failed to open file: {test_file}")
    except Exception as e:
        print(f"✗ Error during file operations: {e}")
        import traceback
        traceback.print_exc()
    
    # Cleanup
    try:
        npisys.end()
        print("\n✓ NPI shutdown successfully")
    except Exception as e:
        print(f"✗ Failed to shutdown NPI: {e}")
    
    return True


def main():
    """Main test function."""
    print("=" * 60)
    print("FSDB Waveform API Test")
    print("=" * 60)
    
    # Check environment
    print("\n--- Environment Check ---")
    verdi_home = os.environ.get("VERDI_HOME")
    if verdi_home:
        print(f"✓ VERDI_HOME: {verdi_home}")
    else:
        print("✗ VERDI_HOME not set")
        print("\nPlease set VERDI_HOME environment variable:")
        print("  export VERDI_HOME=/path/to/verdi")
        return 1
    
    ld_library_path = os.environ.get("LD_LIBRARY_PATH", "")
    if "verdi" in ld_library_path.lower() or "npi" in ld_library_path.lower():
        print(f"✓ LD_LIBRARY_PATH includes Verdi paths")
    else:
        print("⚠ LD_LIBRARY_PATH may not include Verdi libraries")
        print("  Consider adding:")
        print(f"  export LD_LIBRARY_PATH=$VERDI_HOME/share/NPI/lib/linux64:$VERDI_HOME/platform/linux64/bin:$LD_LIBRARY_PATH")
    
    # Check for test file
    test_file = "test.fsdb"
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    
    if not os.path.exists(test_file):
        print(f"\n⚠ Note: Test file '{test_file}' not found")
        print("The basic NPI initialization test will still run.")
        print("\nTo test with a real FSDB file:")
        print("  Usage: python test_fsdb.py [path_to_fsdb_file]")
        print("\nTo generate a test FSDB file, you can:")
        print("  1. Use Verdi to dump waveforms from a simulation")
        print("  2. Run a Verilog/SystemVerilog simulation with FSDB dumping enabled")
    
    # Run tests
    success = test_basic_functionality()
    
    print("\n" + "=" * 60)
    if success:
        print("Test completed!")
        if not os.path.exists(test_file):
            print("\nTo test with a real FSDB file:")
            print("1. Place an FSDB file in this directory named 'test.fsdb'")
            print("2. Or run: python test_fsdb.py /path/to/your/file.fsdb")
    else:
        print("Test failed - see errors above")
    print("=" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
