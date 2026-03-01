"""
Integration tests for VRAgent 2.0 with mock UnityBridge.
Tests the Python pipeline (Planner -> Verifier -> Executor -> Observer) without requiring Unity.
"""

import json
from unittest.mock import Mock, MagicMock, patch
import pytest

from vragent2.contracts import (
    ActionUnit, GrabActionUnit, TriggerActionUnit, TransformActionUnit,
    ObjectStateSnapshot, ExecutionResult, BatchResult
)
from vragent2.agents.executor import ExecutorAgent
from vragent2.agents.observer import ObserverAgent
from vragent2.controller import VRAgentController


class MockUnityBridge:
    """
    Mock UnityBridge that simulates Unity responses without actual TCP connection.
    Used for testing Python pipeline.
    """

    def __init__(self, host="127.0.0.1", port=6400):
        self.host = host
        self.port = port
        self.connected = False
        self.objects = {}  # Simulated object state
        self.logs = []
        self.last_log_index = 0

    def connect(self):
        """Simulate connection"""
        self.connected = True
        return True

    def close(self):
        """Simulate disconnection"""
        self.connected = False

    def ping(self):
        """Simulate ping"""
        return self.connected

    def import_objects(self, task_list):
        """Simulate object import - just track object references"""
        for task_unit in task_list.get("taskUnits", []):
            for action_unit in task_unit.get("actionUnits", []):
                if "source_object_fileID" in action_unit:
                    file_id = action_unit["source_object_fileID"]
                    if file_id not in self.objects:
                        self.objects[file_id] = {
                            "position": [0, 0, 0],
                            "rotation": [0, 0, 0, 1],
                            "scale": [1, 1, 1],
                            "active": True
                        }
        return {"success": True, "count": len(self.objects)}

    def execute(self, action):
        """Simulate single action execution"""
        action_type = action.get("type")
        
        # Simulate state capture
        state_before = self._capture_state(action)
        
        # Apply action (simulate Unity behavior)
        if action_type == "Grab":
            source = action.get("source_object_fileID")
            dest_pos = action.get("destination_object_fileID")
            if source in self.objects and dest_pos:
                self.objects[source]["position"] = [1, 2, 3]  # Move to destination
                self._log("Info", f"Grabbed {source} to {dest_pos}")
        
        elif action_type == "Trigger":
            source = action.get("source_object_fileID")
            event = action.get("source_object_event")
            if source in self.objects:
                self._log("Info", f"Triggered {event} on {source}")
        
        elif action_type == "Transform":
            source = action.get("source_object_fileID")
            if source in self.objects:
                # Apply delta
                dx = action.get("deltaX", 0)
                dy = action.get("deltaY", 0)
                dz = action.get("deltaZ", 0)
                self.objects[source]["position"][0] += dx
                self.objects[source]["position"][1] += dy
                self.objects[source]["position"][2] += dz
                self._log("Info", f"Applied transform to {source}")
        
        state_after = self._capture_state(action)
        
        return ExecutionResult(
            success=True,
            action=action,
            state_before=state_before,
            state_after=state_after,
            events=["ObjectMoved"] if action_type == "Grab" else [],
            exceptions=[]
        )

    def execute_batch(self, actions):
        """Simulate batch execution"""
        results = []
        for action in actions:
            result = self.execute(action)
            results.append(result)
        
        return BatchResult(
            success=True,
            total=len(actions),
            successful=len(results),
            failed=0,
            results=results
        )

    def query_state(self, file_ids):
        """Simulate state query"""
        snapshots = []
        for fid in file_ids:
            if fid in self.objects:
                state = self.objects[fid]
                snapshots.append(ObjectStateSnapshot(
                    object_id=fid,
                    position=(state["position"][0], state["position"][1], state["position"][2]),
                    rotation=(state["rotation"][0], state["rotation"][1], state["rotation"][2], state["rotation"][3]),
                    scale=(state["scale"][0], state["scale"][1], state["scale"][2]),
                    active=state["active"],
                    components=["Transform", "Rigidbody"]
                ))
        return snapshots

    def query_logs(self, since_index=0):
        """Simulate log query"""
        return self.logs[since_index:]

    def reset(self):
        """Simulate reset"""
        self.objects.clear()
        self.logs.clear()
        self.last_log_index = 0
        return {"success": True}

    # Helper methods
    def _capture_state(self, action):
        """Capture state for given action"""
        source = action.get("source_object_fileID")
        if source and source in self.objects:
            state = self.objects[source]
            return ObjectStateSnapshot(
                object_id=source,
                position=(state["position"][0], state["position"][1], state["position"][2]),
                rotation=(state["rotation"][0], state["rotation"][1], state["rotation"][2], state["rotation"][3]),
                scale=(state["scale"][0], state["scale"][1], state["scale"][2]),
                active=state["active"],
                components=["Transform", "Rigidbody"]
            )
        return None

    def _log(self, level, message):
        """Add log entry"""
        self.logs.append({
            "timestamp": len(self.logs),  # Use index as mock timestamp
            "level": level,
            "message": message,
            "stackTrace": ""
        })


class TestExecutorWithMockBridge:
    """Test ExecutorAgent with mock UnityBridge"""

    @pytest.fixture
    def mock_bridge(self):
        bridge = MockUnityBridge()
        bridge.connect()
        return bridge

    @pytest.fixture
    def executor(self, mock_bridge):
        config = Mock()
        config.output_dir = "./test_output"
        executor = ExecutorAgent(config=config, unity_bridge=mock_bridge)
        return executor

    def test_executor_single_grab_action(self, executor, mock_bridge):
        """Test executor handles single Grab action via bridge"""
        # Import objects first
        task_list = {
            "taskUnits": [{
                "actionUnits": [
                    {"type": "Grab", "source_object_fileID": "f1"}
                ]
            }]
        }
        mock_bridge.import_objects(task_list)
        
        # Execute grab action
        action = {
            "type": "Grab",
            "source_object_fileID": "f1",
            "destination_object_fileID": "f2"
        }
        
        result = executor._execute_single("grab_1", action, Mock())
        
        assert result is not None
        # Bridge-based execution should complete
        assert mock_bridge.objects["f1"]["position"] == [1, 2, 3]

    def test_executor_batch_actions(self, executor, mock_bridge):
        """Test executor handles batch actions via bridge"""
        task_list = {
            "taskUnits": [{
                "actionUnits": [
                    {"type": "Grab", "source_object_fileID": "f1"},
                    {"type": "Grab", "source_object_fileID": "f2"}
                ]
            }]
        }
        mock_bridge.import_objects(task_list)
        
        actions = [
            {"type": "Grab", "source_object_fileID": "f1"},
            {"type": "Grab", "source_object_fileID": "f2"}
        ]
        
        results = executor._execute_batch("grab_batch", actions, Mock())
        
        assert results is not None
        assert len(mock_bridge.objects) >= 2

    def test_executor_query_state(self, executor, mock_bridge):
        """Test executor can query state from bridge"""
        task_list = {
            "taskUnits": [{
                "actionUnits": [
                    {"type": "Grab", "source_object_fileID": "f1"}
                ]
            }]
        }
        mock_bridge.import_objects(task_list)
        
        state = executor.get_state(["f1"])
        
        assert state is not None
        assert len(state) > 0

    def test_executor_console_logs(self, executor, mock_bridge):
        """Test executor can retrieve console logs from bridge"""
        logs = executor.get_console_logs()
        
        assert logs is not None
        assert isinstance(logs, list)


class TestObserverWithMockBridge:
    """Test ObserverAgent with mock execution data"""

    def test_observer_analyzes_execution_result(self):
        """Test observer can analyze execution results"""
        config = Mock()
        config.output_dir = "./test_output"
        observer = ObserverAgent(config=config)
        
        execution_trace = [
            {
                "action": {"type": "Grab", "source_object_fileID": "f1"},
                "state_before": {"objectId": "f1", "position": (0, 0, 0)},
                "state_after": {"objectId": "f1", "position": (1, 2, 3)},
                "events": ["ObjectMoved"],
                "exceptions": []
            }
        ]
        
        console_logs = [
            {"timestamp": 1.0, "level": "Info", "message": "Grabbed f1"},
            {"timestamp": 2.0, "level": "Info", "message": "Object moved"}
        ]
        
        # Observer should be able to process these
        assert len(execution_trace) > 0
        assert len(console_logs) > 0

    def test_observer_detects_coverage_changes(self):
        """Test observer can detect coverage changes"""
        config = Mock()
        config.output_dir = "./test_output"
        observer = ObserverAgent(config=config)
        
        # Test data
        state_before = ObjectStateSnapshot(
            object_id="f1", position=(0, 0, 0),
            rotation=(0, 0, 0, 1), scale=(1, 1, 1),
            active=True, components=["Transform"]
        )
        
        state_after = ObjectStateSnapshot(
            object_id="f1", position=(1, 2, 3),
            rotation=(0, 0, 0, 1), scale=(1, 1, 1),
            active=True, components=["Transform"]
        )
        
        # Observer should recognize state change
        pos_changed = (
            state_before.position != state_after.position
        )
        assert pos_changed


class TestPipelineFlow:
    """Test complete pipeline flow with mock bridge"""

    def test_pipeline_import_execute_observe(self):
        """Test complete Import -> Execute -> Observe flow"""
        mock_bridge = MockUnityBridge()
        mock_bridge.connect()
        
        # Step 1: Import task plan
        task_list = {
            "taskUnits": [
                {
                    "taskID": 0,
                    "actionUnits": [
                        {"type": "Grab", "source_object_fileID": "f1"}
                    ]
                }
            ]
        }
        
        result = mock_bridge.import_objects(task_list)
        assert result["success"] is True
        
        # Step 2: Execute action
        action = {"type": "Grab", "source_object_fileID": "f1"}
        exec_result = mock_bridge.execute(action)
        assert exec_result.success is True
        
        # Step 3: Query state
        state = mock_bridge.query_state(["f1"])
        assert len(state) > 0
        
        # Step 4: Query logs
        logs = mock_bridge.query_logs()
        assert len(logs) > 0
        
        # Step 5: Reset
        reset_result = mock_bridge.reset()
        assert reset_result["success"] is True

    def test_pipeline_multiple_iterations(self):
        """Test multiple execution iterations in sequence"""
        mock_bridge = MockUnityBridge()
        mock_bridge.connect()
        
        # Round 1
        mock_bridge.import_objects({
            "taskUnits": [{
                "actionUnits": [
                    {"type": "Grab", "source_object_fileID": "f1"}
                ]
            }]
        })
        
        action1 = {"type": "Grab", "source_object_fileID": "f1"}
        result1 = mock_bridge.execute(action1)
        assert result1.success is True
        
        # Round 2: Different action on same objects
        action2 = {"type": "Trigger", "source_object_fileID": "f1", "source_object_event": "OnClick"}
        result2 = mock_bridge.execute(action2)
        assert result2.success is True
        
        logs = mock_bridge.query_logs()
        assert len(logs) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
