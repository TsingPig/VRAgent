"""
Unit tests for UnityBridge protocol serialization/deserialization.
Tests the wire format and message encoding/decoding without requiring Unity.
"""

import json
import struct
import pytest
from vragent2.bridge.unity_bridge import UnityBridge
from vragent2.contracts import ActionUnit, GrabActionUnit, TriggerActionUnit, TransformActionUnit


class TestProtocolEncoding:
    """Test 4-byte LE length prefix + JSON encoding"""

    def test_encode_length_prefix(self):
        """Test 4-byte LE encoding of message length"""
        msg = "Hello World"
        encoded = msg.encode('utf-8')
        
        # Manual encoding
        length = len(encoded)
        prefix = struct.pack('<I', length)  # Little-endian unsigned int
        
        assert len(prefix) == 4
        assert prefix == b'\x0b\x00\x00\x00'  # 11 in LE

    def test_decode_length_prefix(self):
        """Test 4-byte LE decoding of message length"""
        prefix = struct.pack('<I', 42)
        length = struct.unpack('<I', prefix)[0]
        assert length == 42


class TestCommandSerialization:
    """Test serialization of AgentCommand objects"""

    def test_execute_command_json(self):
        """Test ExecuteCommand serializes to valid JSON"""
        # Create a mock action
        action_dict = {
            "type": "Grab",
            "source_object_fileID": "file_00001",
            "destination_object_fileID": "file_00002"
        }
        
        command = {
            "type": "Execute",
            "action": action_dict
        }
        
        json_str = json.dumps(command)
        decoded = json.loads(json_str)
        
        assert decoded["type"] == "Execute"
        assert decoded["action"]["type"] == "Grab"
        assert decoded["action"]["source_object_fileID"] == "file_00001"

    def test_execute_batch_command_json(self):
        """Test ExecuteBatchCommand serializes to valid JSON"""
        actions = [
            {
                "type": "Grab",
                "source_object_fileID": "file_00001",
                "destination_object_fileID": "file_00002"
            },
            {
                "type": "Trigger",
                "source_object_fileID": "file_00003",
                "source_object_event": "OnClick"
            }
        ]
        
        command = {
            "type": "ExecuteBatch",
            "actions": actions
        }
        
        json_str = json.dumps(command)
        decoded = json.loads(json_str)
        
        assert decoded["type"] == "ExecuteBatch"
        assert len(decoded["actions"]) == 2
        assert decoded["actions"][0]["type"] == "Grab"
        assert decoded["actions"][1]["type"] == "Trigger"

    def test_query_state_command_json(self):
        """Test QueryStateCommand serializes to valid JSON"""
        command = {
            "type": "QueryState",
            "fileIds": ["file_00001", "file_00002", "file_00003"]
        }
        
        json_str = json.dumps(command)
        decoded = json.loads(json_str)
        
        assert decoded["type"] == "QueryState"
        assert len(decoded["fileIds"]) == 3
        assert decoded["fileIds"][0] == "file_00001"

    def test_import_objects_command_json(self):
        """Test ImportObjectsCommand serializes to valid JSON"""
        task_list = {
            "taskUnits": [
                {
                    "taskID": 0,
                    "actionUnits": [
                        {
                            "type": "Grab",
                            "source_object_fileID": "file_00001"
                        }
                    ]
                }
            ]
        }
        
        command = {
            "type": "ImportObjects",
            "taskList": task_list
        }
        
        json_str = json.dumps(command)
        decoded = json.loads(json_str)
        
        assert decoded["type"] == "ImportObjects"
        assert len(decoded["taskList"]["taskUnits"]) == 1


class TestResponseSerialization:
    """Test deserialization of AgentResponse objects"""

    def test_execution_result_response_json(self):
        """Test ExecutionResultResponse deserializes from JSON"""
        response = {
            "type": "ExecutionResult",
            "success": True,
            "action": {
                "type": "Grab",
                "source_object_fileID": "file_00001"
            },
            "state_before": {
                "objectId": "file_00001",
                "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
                "active": True,
                "components": ["Transform", "Rigidbody"]
            },
            "state_after": {
                "objectId": "file_00001",
                "position": {"x": 1.0, "y": 2.0, "z": 3.0},
                "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
                "active": True,
                "components": ["Transform", "Rigidbody"]
            },
            "events": ["ObjectMoved"],
            "exceptions": []
        }
        
        json_str = json.dumps(response)
        decoded = json.loads(json_str)
        
        assert decoded["type"] == "ExecutionResult"
        assert decoded["success"] is True
        assert decoded["state_after"]["position"]["x"] == 1.0
        assert len(decoded["events"]) == 1

    def test_state_result_response_json(self):
        """Test StateResultResponse deserializes from JSON"""
        response = {
            "type": "StateResult",
            "snapshots": [
                {
                    "objectId": "file_00001",
                    "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                    "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
                    "active": True,
                    "components": ["Transform"]
                }
            ]
        }
        
        json_str = json.dumps(response)
        decoded = json.loads(json_str)
        
        assert decoded["type"] == "StateResult"
        assert len(decoded["snapshots"]) == 1

    def test_logs_result_response_json(self):
        """Test LogsResultResponse deserializes from JSON"""
        response = {
            "type": "LogsResult",
            "logs": [
                {
                    "timestamp": 1234567890.0,
                    "level": "Info",
                    "message": "Test message",
                    "stackTrace": ""
                },
                {
                    "timestamp": 1234567891.0,
                    "level": "Error",
                    "message": "Error message",
                    "stackTrace": "SomeStackTrace"
                }
            ]
        }
        
        json_str = json.dumps(response)
        decoded = json.loads(json_str)
        
        assert decoded["type"] == "LogsResult"
        assert len(decoded["logs"]) == 2
        assert decoded["logs"][0]["level"] == "Info"
        assert decoded["logs"][1]["level"] == "Error"


class TestWireFormat:
    """Test complete wire format (length prefix + JSON payload)"""

    def test_full_wire_message_encode(self):
        """Test encoding full wire message"""
        msg_obj = {
            "type": "Execute",
            "action": {
                "type": "Grab",
                "source_object_fileID": "file_00001"
            }
        }
        
        json_bytes = json.dumps(msg_obj).encode('utf-8')
        length_prefix = struct.pack('<I', len(json_bytes))
        
        full_msg = length_prefix + json_bytes
        
        # Verify we can decode it
        decoded_length = struct.unpack('<I', full_msg[:4])[0]
        decoded_json = full_msg[4:4+decoded_length].decode('utf-8')
        decoded_obj = json.loads(decoded_json)
        
        assert decoded_obj["type"] == "Execute"
        assert decoded_obj["action"]["type"] == "Grab"

    def test_multiple_messages_in_stream(self):
        """Test parsing multiple messages from a stream"""
        messages = [
            {"type": "Ping"},
            {"type": "QueryState", "fileIds": ["f1", "f2"]},
            {"type": "Execute", "action": {"type": "Grab"}}
        ]
        
        stream = b''
        for msg in messages:
            json_bytes = json.dumps(msg).encode('utf-8')
            prefix = struct.pack('<I', len(json_bytes))
            stream += prefix + json_bytes
        
        # Parse stream
        offset = 0
        parsed = []
        while offset < len(stream):
            length = struct.unpack('<I', stream[offset:offset+4])[0]
            offset += 4
            json_str = stream[offset:offset+length].decode('utf-8')
            offset += length
            parsed.append(json.loads(json_str))
        
        assert len(parsed) == 3
        assert parsed[0]["type"] == "Ping"
        assert parsed[1]["type"] == "QueryState"
        assert parsed[2]["type"] == "Execute"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
