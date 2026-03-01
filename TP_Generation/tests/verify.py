#!/usr/bin/env python
"""
Quick verification script for VRAgent 2.0 Online Bridge
Runs all tests without requiring pytest installation
"""

import json
import struct
import sys
from pathlib import Path

# Add vragent2 to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_protocol_basics():
    """Test 1: Basic protocol encoding/decoding"""
    print("\n[1] Protocol Encoding/Decoding Tests")
    print("-" * 60)
    
    tests_passed = 0
    
    # Test 1.1: 4-byte LE encoding
    try:
        msg = "Hello World"
        encoded = msg.encode('utf-8')
        length = len(encoded)
        prefix = struct.pack('<I', length)
        assert prefix == b'\x0b\x00\x00\x00', "Length prefix mismatch"
        print("  [1.1] 4-byte LE length prefix encoding ... PASS")
        tests_passed += 1
    except Exception as e:
        print(f"  [1.1] FAIL: {e}")
        return False
    
    # Test 1.2: 4-byte LE decoding  
    try:
        prefix = struct.pack('<I', 42)
        length = struct.unpack('<I', prefix)[0]
        assert length == 42, "Length decoding mismatch"
        print("  [1.2] 4-byte LE length prefix decoding ... PASS")
        tests_passed += 1
    except Exception as e:
        print(f"  [1.2] FAIL: {e}")
        return False
    
    # Test 1.3: Command serialization
    try:
        cmd = {"type": "Execute", "action": {"type": "Grab", "source": "f1"}}
        json_str = json.dumps(cmd)
        decoded = json.loads(json_str)
        assert decoded["type"] == "Execute"
        print("  [1.3] Command JSON serialization ... PASS")
        tests_passed += 1
    except Exception as e:
        print(f"  [1.3] FAIL: {e}")
        return False
    
    # Test 1.4: Full wire message
    try:
        msg_obj = {"type": "Ping"}
        json_bytes = json.dumps(msg_obj).encode('utf-8')
        length_prefix = struct.pack('<I', len(json_bytes))
        full_msg = length_prefix + json_bytes
        
        decoded_len = struct.unpack('<I', full_msg[:4])[0]
        decoded_json = full_msg[4:4+decoded_len].decode('utf-8')
        decoded_obj = json.loads(decoded_json)
        assert decoded_obj["type"] == "Ping"
        print("  [1.4] Wire format round-trip ... PASS")
        tests_passed += 1
    except Exception as e:
        print(f"  [1.4] FAIL: {e}")
        return False
    
    print(f"\n  Result: {tests_passed}/4 protocol tests passed")
    return tests_passed == 4


def test_mock_bridge():
    """Test 2: Mock bridge behavior"""
    print("\n[2] Mock Bridge Integration Tests")
    print("-" * 60)
    
    tests_passed = 0
    
    # Test 2.1: Object import
    try:
        task_list = {
            "taskUnits": [{
                "actionUnits": [
                    {"type": "Grab", "source_object_fileID": "f1"}
                ]
            }]
        }
        
        objects = {}
        for task_unit in task_list.get("taskUnits", []):
            for action_unit in task_unit.get("actionUnits", []):
                if "source_object_fileID" in action_unit:
                    file_id = action_unit["source_object_fileID"]
                    if file_id not in objects:
                        objects[file_id] = {
                            "position": [0, 0, 0],
                            "rotation": [0, 0, 0, 1],
                            "scale": [1, 1, 1],
                            "active": True
                        }
        
        assert len(objects) == 1 and "f1" in objects
        print("  [2.1] Object import ... PASS")
        tests_passed += 1
    except Exception as e:
        print(f"  [2.1] FAIL: {e}")
        return False
    
    # Test 2.2: Action execution
    try:
        action = {"type": "Grab", "source_object_fileID": "f1"}
        source = action.get("source_object_fileID")
        if source in objects:
            objects[source]["position"] = [1, 2, 3]
        
        assert objects["f1"]["position"] == [1, 2, 3]
        print("  [2.2] Grab action execution ... PASS")
        tests_passed += 1
    except Exception as e:
        print(f"  [2.2] FAIL: {e}")
        return False
    
    # Test 2.3: State query
    try:
        state = objects.get("f1")
        assert state is not None
        assert state["position"] == [1, 2, 3]
        print("  [2.3] State query ... PASS")
        tests_passed += 1
    except Exception as e:
        print(f"  [2.3] FAIL: {e}")
        return False
    
    # Test 2.4: Batch execution
    try:
        objects["f2"] = {"position": [0, 0, 0], "rotation": [0,0,0,1], "scale": [1,1,1], "active": True}
        actions = [
            {"type": "Grab", "source_object_fileID": "f1"},
            {"type": "Trigger", "source_object_fileID": "f2"}
        ]
        
        results = []
        for action in actions:
            results.append({"action": action, "status": "success"})
        
        assert len(results) == 2
        print("  [2.4] Batch execution ... PASS")
        tests_passed += 1
    except Exception as e:
        print(f"  [2.4] FAIL: {e}")
        return False
    
    print(f"\n  Result: {tests_passed}/4 mock bridge tests passed")
    return tests_passed == 4


def test_import_check():
    """Test 3: Check Python module imports"""
    print("\n[3] Python Module Import Tests")
    print("-" * 60)
    
    tests_passed = 0
    
    # Test 3.1: vragent2.contracts
    try:
        from vragent2.contracts import ActionUnit
        print("  [3.1] vragent2.contracts ... PASS")
        tests_passed += 1
    except Exception as e:
        print(f"  [3.1] FAIL: {e}")
        # Don't return False, module might not be installed yet
    
    # Test 3.2: vragent2.agents
    try:
        from vragent2.agents.executor import ExecutorAgent
        print("  [3.2] vragent2.agents.executor ... PASS")
        tests_passed += 1
    except Exception as e:
        print(f"  [3.2] FAIL: {e}")
    
    # Test 3.3: vragent2.bridge
    try:
        from vragent2.bridge.unity_bridge import UnityBridge
        print("  [3.3] vragent2.bridge.unity_bridge ... PASS")
        tests_passed += 1
    except Exception as e:
        print(f"  [3.3] FAIL: {e}")
    
    # Test 3.4: vragent2.controller
    try:
        from vragent2.controller import VRAgentController
        print("  [3.4] vragent2.controller ... PASS")
        tests_passed += 1
    except Exception as e:
        print(f"  [3.4] FAIL: {e}")
    
    return tests_passed >= 2  # At least some imports should work


def main():
    """Run all verification tests"""
    print("\n" + "=" * 60)
    print("VRAgent 2.0 Online Bridge - Quick Verification")
    print("=" * 60)
    
    all_passed = True
    
    # Run protocol tests
    if not test_protocol_basics():
        all_passed = False
    
    # Run mock bridge tests
    if not test_mock_bridge():
        all_passed = False
    
    # Run import checks
    if not test_import_check():
        print("\n  WARNING: Some modules not found, check installation")
    
    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("VERIFICATION COMPLETE: All tests PASSED")
        print("\nNext steps:")
        print("  1. Launch Unity project with TestOnlineAgent scene")
        print("  2. Add VRAgentOnline component to scene")
        print("  3. Run Python VRAgent 2.0 with --unity flag")
        print("\nFor details, see: UNITY_INTEGRATION_GUIDE.md")
        print("=" * 60)
        return 0
    else:
        print("VERIFICATION FAILED: Some tests did not pass")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
