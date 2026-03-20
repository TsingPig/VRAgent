"""
Smoke tests for VRAgent 2.0 architecture changes.

Uses only stdlib unittest — no pytest needed.
Run: python -m tests.test_vragent2_smoke
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

# Ensure TP_Generation is on the path
_HERE = Path(__file__).resolve().parent
_TP = _HERE.parent
if str(_TP) not in sys.path:
    sys.path.insert(0, str(_TP))


# ======================================================================
# 1. Contracts
# ======================================================================

class TestContracts(unittest.TestCase):

    def test_scene_understanding_output_roundtrip(self):
        from vragent2.contracts import SceneUnderstandingOutput, InteractionDependency

        orig = SceneUnderstandingOutput(
            scene_overview="A kitchen scene",
            key_objects=["Knife", "Oven", "Plate"],
            interaction_dependencies=[
                InteractionDependency(source="Knife", target="Bread", relation="cuts"),
            ],
            gate_chains=["Open drawer first"],
            main_path=["Pick up knife", "Cut bread"],
            failure_paths=["Knife falls through floor"],
            object_priority_ranking=["Knife", "Oven", "Plate"],
        )
        d = orig.to_dict()
        restored = SceneUnderstandingOutput.from_dict(d)
        self.assertEqual(restored.scene_overview, orig.scene_overview)
        self.assertEqual(restored.key_objects, orig.key_objects)
        self.assertEqual(len(restored.interaction_dependencies), 1)
        self.assertEqual(restored.interaction_dependencies[0].relation, "cuts")
        self.assertEqual(restored.object_priority_ranking, orig.object_priority_ranking)

    def test_scene_understanding_to_prompt_text(self):
        from vragent2.contracts import SceneUnderstandingOutput, InteractionDependency
        su = SceneUnderstandingOutput(
            scene_overview="Kitchen",
            key_objects=["A", "B"],
            interaction_dependencies=[InteractionDependency("A", "B", "unlocks")],
            gate_chains=["Step 1"],
            main_path=["Do A", "Do B"],
        )
        text = su.to_prompt_text()
        self.assertIn("Kitchen", text)
        self.assertIn("A --[unlocks]--> B", text)
        self.assertIn("Gate Chains", text)

    def test_scheduler_decision_defaults(self):
        from vragent2.contracts import SchedulerDecision
        sd = SchedulerDecision(object_name="Knife", reason="high priority")
        self.assertEqual(sd.object_name, "Knife")
        self.assertEqual(sd.priority_score, 0.0)
        self.assertEqual(sd.skip_list, [])

    def test_empty_scene_understanding_from_dict(self):
        from vragent2.contracts import SceneUnderstandingOutput
        empty = SceneUnderstandingOutput.from_dict({})
        self.assertEqual(empty.scene_overview, "")
        self.assertEqual(empty.key_objects, [])


# ======================================================================
# 2. Config
# ======================================================================

class TestConfig(unittest.TestCase):

    def test_agent_llm_config_effective_model(self):
        from vragent2.utils.config_loader import AgentLLMConfig
        cfg = AgentLLMConfig(model="", temperature=0.5, enabled=True)
        self.assertEqual(cfg.effective_model("gpt-4o"), "gpt-4o")
        cfg2 = AgentLLMConfig(model="gpt-3.5-turbo", temperature=0.3, enabled=True)
        self.assertEqual(cfg2.effective_model("gpt-4o"), "gpt-3.5-turbo")

    def test_info_sharing_defaults(self):
        from vragent2.utils.config_loader import InfoSharingConfig
        sharing = InfoSharingConfig()
        self.assertTrue(sharing.planner_summary_to_verifier)
        self.assertTrue(sharing.verifier_evidence_to_planner)
        self.assertTrue(sharing.scene_summary_to_planner)
        self.assertFalse(sharing.planner_summary_to_observer)

    def test_vragent_config_has_new_fields(self):
        from vragent2.utils.config_loader import VRAgentConfig
        cfg = VRAgentConfig()
        self.assertIsNotNone(cfg.planner_llm)
        self.assertIsNotNone(cfg.verifier_llm)
        self.assertIsNotNone(cfg.observer_llm)
        self.assertIsNotNone(cfg.scene_understanding_llm)
        self.assertIsNotNone(cfg.info_sharing)
        self.assertEqual(cfg.scene_doc_path, "")


# ======================================================================
# 3. Verifier LLM integration
# ======================================================================

class TestVerifierLLM(unittest.TestCase):

    def _make_verifier(self, llm=None, enabled=True):
        from vragent2.agents.verifier import VerifierAgent
        from vragent2.utils.config_loader import AgentLLMConfig
        from vragent2.retrieval.data_types import ContextPack

        retrieval = MagicMock()
        retrieval.object_exists.return_value = True
        retrieval.build_verifier_context.return_value = ContextPack(target_agent="verifier")
        config = AgentLLMConfig(model="test-model", temperature=0.1, enabled=enabled)
        return VerifierAgent(retrieval, llm=llm, llm_config=config)

    def test_verifier_without_llm(self):
        """Verifier should still work when no LLM is provided."""
        v = self._make_verifier(llm=None, enabled=False)
        result = v.run({"actions": []})
        self.assertIn("errors", result)
        self.assertIn("executable_score", result)

    def test_verifier_with_mock_llm(self):
        """Verifier calls LLM when enabled."""
        mock_llm = MagicMock()
        mock_llm.ask.return_value = "OK"
        v = self._make_verifier(llm=mock_llm, enabled=True)
        result = v.run({"actions": [
            {"actionType": "Grab", "objectA_fileId": "123", "objectB_fileId": "456"},
        ]})
        self.assertIn("llm_review", result)
        # LLM should have been called
        mock_llm.ask.assert_called_once()


# ======================================================================
# 4. Observer LLM integration
# ======================================================================

class TestObserverLLM(unittest.TestCase):

    def _make_observer(self, llm=None, enabled=True):
        from vragent2.agents.observer import ObserverAgent
        from vragent2.utils.config_loader import AgentLLMConfig
        config = AgentLLMConfig(model="test-model", temperature=0.2, enabled=enabled)
        return ObserverAgent(llm=llm, llm_config=config)

    def test_observer_without_llm(self):
        obs = self._make_observer(llm=None, enabled=False)
        result = obs.run({
            "executor_output": {"trace": [], "coverage_delta": {}, "exceptions": []},
            "console_logs": [],
        })
        self.assertIn("coverage_delta", result)
        self.assertIn("llm_analysis", result)
        self.assertEqual(result["llm_analysis"], "")

    def test_observer_with_mock_llm(self):
        mock_llm = MagicMock()
        fake_llm_result = {
            "state_delta": {
                "changed_objects": [], "expected_changes": [],
                "unexpected_changes": [], "gates_opened": [],
                "gates_still_blocked": [], "semantic_failures": [],
            },
            "failure_hypotheses": [],
            "strategy": {
                "new_facts": ["collider missing"],
                "gates_inferred": [],
                "planner_instruction": "Fix collider",
                "scheduler_bias": [],
                "oracle_updates": [],
            },
        }
        mock_llm.chat.return_value = json.dumps(fake_llm_result)
        mock_llm.extract_json.return_value = fake_llm_result
        obs = self._make_observer(llm=mock_llm, enabled=True)
        result = obs.run({
            "executor_output": {
                "trace": [{"action": "grab", "state_before": {}, "state_after": {}, "events": []}],
                "coverage_delta": {"LC": 0.1, "MC": 0.05, "CoIGO": 0.02},
                "exceptions": ["NullRef"],
            },
            "console_logs": ["NullReferenceException at line 42"],
        })
        self.assertIn("llm_analysis", result)
        mock_llm.chat.assert_called_once()
        self.assertTrue(len(result["bug_signals"]) > 0)


# ======================================================================
# 5. SceneUnderstandingAgent
# ======================================================================

class TestSceneUnderstandingAgent(unittest.TestCase):

    def test_with_mock_llm(self):
        from vragent2.agents.scene_understanding import SceneUnderstandingAgent
        from vragent2.utils.config_loader import AgentLLMConfig

        fake_response = json.dumps({
            "scene_overview": "A VR kitchen",
            "key_objects": ["Knife", "Oven"],
            "interaction_dependencies": [
                {"source": "Knife", "target": "Bread", "relation": "cuts"}
            ],
            "gate_chains": [],
            "main_path": ["Pick up knife"],
            "failure_paths": [],
            "object_priority_ranking": ["Knife", "Oven"],
        })

        mock_llm = MagicMock()
        mock_llm.chat.return_value = f"```json\n{fake_response}\n```"
        mock_llm.extract_json.return_value = json.loads(fake_response)

        agent = SceneUnderstandingAgent(
            llm=mock_llm,
            llm_config=AgentLLMConfig(model="gpt-4o", temperature=0.2),
        )

        # Create a temp .md file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("# Kitchen Scene\nThis is a kitchen with a knife and oven.")
            tmp_path = f.name

        try:
            result = agent.run({"scene_doc_path": tmp_path})
            self.assertEqual(result["scene_overview"], "A VR kitchen")
            self.assertIn("Knife", result["key_objects"])
            self.assertEqual(len(result["interaction_dependencies"]), 1)
            mock_llm.chat.assert_called_once()
        finally:
            os.unlink(tmp_path)

    def test_missing_doc_path(self):
        from vragent2.agents.scene_understanding import SceneUnderstandingAgent
        mock_llm = MagicMock()
        agent = SceneUnderstandingAgent(llm=mock_llm)
        result = agent.run({"scene_doc_path": ""})
        self.assertEqual(result["scene_overview"], "")
        mock_llm.chat.assert_not_called()


# ======================================================================
# 6. ObjectScheduler
# ======================================================================

class TestObjectScheduler(unittest.TestCase):

    def _candidates(self):
        return [
            {"gameobject_name": "Knife"},
            {"gameobject_name": "Oven"},
            {"gameobject_name": "Plate"},
        ]

    def test_fallback_linear(self):
        from vragent2.scheduling.object_scheduler import ObjectScheduler
        from vragent2.utils.config_loader import AgentLLMConfig

        scheduler = ObjectScheduler(
            llm=MagicMock(),
            llm_config=AgentLLMConfig(enabled=False),
        )
        decision = scheduler.select_next(self._candidates(), processed=set())
        self.assertIsNotNone(decision)
        self.assertEqual(decision.object_name, "Knife")
        self.assertIn("fallback", decision.reason)

    def test_fallback_with_priority_ranking(self):
        from vragent2.scheduling.object_scheduler import ObjectScheduler
        from vragent2.contracts import SceneUnderstandingOutput
        from vragent2.utils.config_loader import AgentLLMConfig

        su = SceneUnderstandingOutput(
            object_priority_ranking=["Oven", "Knife", "Plate"],
        )
        scheduler = ObjectScheduler(
            llm=MagicMock(),
            llm_config=AgentLLMConfig(enabled=False),
        )
        decision = scheduler.select_next(
            self._candidates(), processed=set(), scene_understanding=su,
        )
        self.assertEqual(decision.object_name, "Oven")

    def test_all_processed_returns_none(self):
        from vragent2.scheduling.object_scheduler import ObjectScheduler
        from vragent2.utils.config_loader import AgentLLMConfig
        scheduler = ObjectScheduler(
            llm=MagicMock(),
            llm_config=AgentLLMConfig(enabled=False),
        )
        result = scheduler.select_next(
            self._candidates(), processed={"Knife", "Oven", "Plate"},
        )
        self.assertIsNone(result)

    def test_llm_driven_selection(self):
        from vragent2.scheduling.object_scheduler import ObjectScheduler
        from vragent2.utils.config_loader import AgentLLMConfig

        mock_llm = MagicMock()
        mock_llm.chat.return_value = json.dumps({
            "object_name": "Plate",
            "reason": "highest coverage potential",
            "priority_score": 0.9,
            "skip_list": [],
        })
        mock_llm.extract_json.return_value = {
            "object_name": "Plate",
            "reason": "highest coverage potential",
            "priority_score": 0.9,
            "skip_list": [],
        }

        scheduler = ObjectScheduler(
            llm=mock_llm,
            llm_config=AgentLLMConfig(enabled=True),
        )
        decision = scheduler.select_next(self._candidates(), processed=set())
        self.assertEqual(decision.object_name, "Plate")
        self.assertAlmostEqual(decision.priority_score, 0.9)
        mock_llm.chat.assert_called_once()

    def test_llm_hallucinated_name_falls_back(self):
        from vragent2.scheduling.object_scheduler import ObjectScheduler
        from vragent2.utils.config_loader import AgentLLMConfig

        mock_llm = MagicMock()
        mock_llm.chat.return_value = json.dumps({
            "object_name": "NonExistent",
            "reason": "test",
            "priority_score": 0.5,
        })
        mock_llm.extract_json.return_value = {
            "object_name": "NonExistent",
            "reason": "test",
            "priority_score": 0.5,
        }

        scheduler = ObjectScheduler(
            llm=mock_llm,
            llm_config=AgentLLMConfig(enabled=True),
        )
        decision = scheduler.select_next(self._candidates(), processed=set())
        # Should fall back since "NonExistent" is not in candidates
        self.assertIn(decision.object_name, ["Knife", "Oven", "Plate"])
        self.assertIn("fallback", decision.reason)


# ======================================================================
# 7. Controller shared context builder
# ======================================================================

class TestControllerSharedContext(unittest.TestCase):

    def _make_controller(self):
        from vragent2.utils.config_loader import VRAgentConfig
        from vragent2.controller import VRAgentController

        config = VRAgentConfig()
        mock_llm = MagicMock()
        mock_retrieval = MagicMock()
        mock_retrieval.build_planner_context.return_value = {}
        mock_retrieval.build_verifier_context.return_value = {}

        controller = VRAgentController(
            config=config,
            llm=mock_llm,
            retrieval=mock_retrieval,
            output_dir=tempfile.mkdtemp(),
        )
        return controller

    def test_empty_shared_context(self):
        ctrl = self._make_controller()
        ctx = ctrl._build_shared_context()
        # No scene understanding → no scene key
        self.assertNotIn("scene_understanding_summary", ctx)

    def test_shared_context_with_scene_understanding(self):
        from vragent2.contracts import SceneUnderstandingOutput
        ctrl = self._make_controller()
        su = SceneUnderstandingOutput(
            scene_overview="Kitchen scene",
            key_objects=["Knife"],
        )
        ctrl._scene_understanding = su
        # Also write to blackboard so _build_shared_context finds it
        ctrl.world_state.scene_understanding = su
        ctx = ctrl._build_shared_context()
        self.assertIn("scene_understanding_summary", ctx)
        self.assertIn("Kitchen scene", ctx["scene_understanding_summary"])

    def test_shared_context_with_planner_output(self):
        ctrl = self._make_controller()
        ctx = ctrl._build_shared_context(
            planner_output={"intent": "test all objects", "expected_reward": 0.5},
        )
        # planner_summary_to_verifier is True by default
        self.assertIn("planner_intent", ctx)

    def test_info_sharing_disabled(self):
        from vragent2.utils.config_loader import InfoSharingConfig
        ctrl = self._make_controller()
        ctrl.config.info_sharing = InfoSharingConfig(
            planner_summary_to_verifier=False,
            planner_summary_to_observer=False,
            scene_summary_to_planner=False,
            scene_summary_to_verifier=False,
            scene_summary_to_observer=False,
        )
        from vragent2.contracts import SceneUnderstandingOutput
        ctrl._scene_understanding = SceneUnderstandingOutput(scene_overview="X")

        ctx = ctrl._build_shared_context(
            planner_output={"intent": "test", "expected_reward": 0.1},
        )
        self.assertNotIn("planner_intent", ctx)
        self.assertNotIn("scene_understanding_summary", ctx)


# ======================================================================
# 8. Integration: full pipeline with mocks
# ======================================================================

class TestPipelineIntegration(unittest.TestCase):

    def test_scene_understanding_phase(self):
        """SceneUnderstandingAgent is called when scene_doc_path is set."""
        from vragent2.utils.config_loader import VRAgentConfig
        from vragent2.controller import VRAgentController

        config = VRAgentConfig()
        config.scene_doc_path = "/nonexistent/path"  # will produce empty output

        mock_llm = MagicMock()
        mock_retrieval = MagicMock()
        mock_retrieval.build_planner_context.return_value = {}

        out_dir = tempfile.mkdtemp()
        ctrl = VRAgentController(
            config=config,
            llm=mock_llm,
            retrieval=mock_retrieval,
            output_dir=out_dir,
        )

        ctrl._run_scene_understanding()
        # With an invalid path, scene_understanding should be empty but not crash
        self.assertIsNotNone(ctrl._scene_understanding)
        self.assertEqual(ctrl._scene_understanding.scene_overview, "")


# ======================================================================
# 9. SharedWorldState (blackboard)
# ======================================================================

class TestSharedWorldState(unittest.TestCase):

    def _make_ws(self):
        from vragent2.contracts import SharedWorldState
        return SharedWorldState()

    def test_add_fact_dedup(self):
        ws = self._make_ws()
        ws.add_fact("Knife is sharp")
        ws.add_fact("Knife is sharp")
        ws.add_fact("Oven is hot")
        self.assertEqual(len(ws.facts), 2)

    def test_mark_tested(self):
        ws = self._make_ws()
        ws.mark_tested("Knife")
        ws.mark_tested("Knife")
        self.assertEqual(ws.tested_objects, ["Knife"])

    def test_record_failure(self):
        ws = self._make_ws()
        ws.record_failure("Knife", "grab failed")
        ws.record_failure("Knife", "grab failed again")
        self.assertEqual(ws.object_failure_counts["Knife"], 2)
        self.assertEqual(len(ws.recent_failures), 2)

    def test_to_dict_roundtrip(self):
        ws = self._make_ws()
        ws.add_fact("fact1")
        ws.open_gates = ["gate_A"]
        ws.blocked_gates = ["gate_B"]
        ws.mark_tested("Obj1")
        ws.record_failure("Obj2", "err")
        ws.total_coverage = 0.5
        ws.coverage_history = [0.1, 0.2, 0.2]
        ws.scheduler_bias = ["try Knife next"]
        d = ws.to_dict()
        self.assertEqual(d["facts"], ["fact1"])
        self.assertEqual(d["open_gates"], ["gate_A"])
        self.assertEqual(d["blocked_gates"], ["gate_B"])
        self.assertEqual(d["tested_objects"], ["Obj1"])
        self.assertEqual(d["object_failure_counts"]["Obj2"], 1)
        self.assertAlmostEqual(d["total_coverage"], 0.5)
        self.assertEqual(d["scheduler_bias"], ["try Knife next"])

    def test_to_prompt_summary_not_empty(self):
        ws = self._make_ws()
        ws.add_fact("The door is locked")
        ws.blocked_gates = ["door_A"]
        ws.oracle_rules = ["Must unlock door before entering"]
        text = ws.to_prompt_summary()
        self.assertIn("door is locked", text)
        self.assertIn("Blocked Gates", text)
        self.assertIn("Oracle Rules", text)

    def test_to_prompt_summary_empty(self):
        ws = self._make_ws()
        text = ws.to_prompt_summary()
        # Empty state should produce empty or minimal summary
        self.assertIsInstance(text, str)


# ======================================================================
# 10. SemanticVerifierOutput
# ======================================================================

class TestSemanticVerifierOutput(unittest.TestCase):

    def test_from_dict(self):
        from vragent2.contracts import SemanticVerifierOutput
        d = {
            "semantic_risk_score": 0.7,
            "missing_preconditions": ["need blue key"],
            "suspicious_steps": ["step 3: grab locked door"],
            "counter_plan": [{"actionType": "Grab"}],
            "verdict": "revise",
        }
        sv = SemanticVerifierOutput.from_dict(d)
        self.assertAlmostEqual(sv.semantic_risk_score, 0.7)
        self.assertEqual(sv.verdict, "revise")
        self.assertEqual(len(sv.missing_preconditions), 1)
        self.assertEqual(len(sv.counter_plan), 1)

    def test_from_dict_defaults(self):
        from vragent2.contracts import SemanticVerifierOutput
        sv = SemanticVerifierOutput.from_dict({})
        self.assertAlmostEqual(sv.semantic_risk_score, 0.0)
        self.assertEqual(sv.verdict, "accept")
        self.assertEqual(sv.missing_preconditions, [])

    def test_to_dict(self):
        from vragent2.contracts import SemanticVerifierOutput
        sv = SemanticVerifierOutput(
            semantic_risk_score=0.3,
            missing_preconditions=[],
            suspicious_steps=[],
            counter_plan=[],
            verdict="accept",
        )
        d = sv.to_dict()
        self.assertEqual(d["verdict"], "accept")
        self.assertAlmostEqual(d["semantic_risk_score"], 0.3)


# ======================================================================
# 11. StateDelta / FailureHypothesis / StrategyRecommendation
# ======================================================================

class TestObserverContracts(unittest.TestCase):

    def test_state_delta(self):
        from vragent2.contracts import StateDelta
        sd = StateDelta(
            changed_objects=["Knife"],
            expected_changes=["move"],
            unexpected_changes=[],
            gates_opened=["drawer"],
            gates_still_blocked=["oven_door"],
            semantic_failures=[],
        )
        d = sd.to_dict()
        self.assertEqual(d["gates_opened"], ["drawer"])

    def test_failure_hypothesis(self):
        from vragent2.contracts import FailureHypothesis
        fh = FailureHypothesis(
            hypothesis="Door is locked",
            evidence=["error: locked"],
            confidence=0.8,
            blocked_object="Door",
            needed_condition="Key",
        )
        d = fh.to_dict()
        self.assertAlmostEqual(d["confidence"], 0.8)
        self.assertEqual(d["blocked_object"], "Door")

    def test_strategy_recommendation(self):
        from vragent2.contracts import StrategyRecommendation
        sr = StrategyRecommendation(
            new_facts=["Key is in drawer"],
            gates_inferred=["drawer_unlocked"],
            planner_instruction="Try drawer first",
            scheduler_bias=["Drawer"],
            oracle_updates=["unlock drawer → use key"],
        )
        d = sr.to_dict()
        self.assertEqual(d["planner_instruction"], "Try drawer first")
        self.assertEqual(d["scheduler_bias"], ["Drawer"])


# ======================================================================
# 12. SemanticVerifier agent
# ======================================================================

class TestSemanticVerifier(unittest.TestCase):

    def test_with_mock_llm(self):
        from vragent2.agents.verifier import SemanticVerifier
        from vragent2.utils.config_loader import AgentLLMConfig

        fake_response = json.dumps({
            "semantic_risk_score": 0.2,
            "missing_preconditions": [],
            "suspicious_steps": [],
            "counter_plan": [],
            "verdict": "accept",
        })
        mock_llm = MagicMock()
        mock_llm.chat.return_value = fake_response
        mock_llm.extract_json.return_value = json.loads(fake_response)

        sv = SemanticVerifier(
            llm=mock_llm,
            llm_config=AgentLLMConfig(model="gpt-4o", temperature=0.2, enabled=True),
        )
        result = sv.run({
            "actions": [{"actionType": "Grab"}],
            "world_state": "test context",
            "planner_intent": "test all",
            "recent_failures": [],
        })
        self.assertEqual(result["verdict"], "accept")
        self.assertAlmostEqual(result["semantic_risk_score"], 0.2)
        mock_llm.chat.assert_called_once()

    def test_without_llm_returns_accept(self):
        from vragent2.agents.verifier import SemanticVerifier
        from vragent2.utils.config_loader import AgentLLMConfig

        sv = SemanticVerifier(
            llm=None,
            llm_config=AgentLLMConfig(enabled=False),
        )
        result = sv.run({"actions": []})
        self.assertEqual(result["verdict"], "accept")


# ======================================================================
# 13. Observer O1/O2/O3 outputs
# ======================================================================

class TestObserverO1O2O3(unittest.TestCase):

    def _make_observer(self, llm=None, enabled=True):
        from vragent2.agents.observer import ObserverAgent
        from vragent2.utils.config_loader import AgentLLMConfig
        config = AgentLLMConfig(model="test-model", temperature=0.2, enabled=enabled)
        return ObserverAgent(llm=llm, llm_config=config)

    def test_observer_produces_state_delta(self):
        """Observer run() should produce state_delta in output."""
        obs = self._make_observer(llm=None, enabled=False)
        result = obs.run({
            "executor_output": {
                "trace": [{"action": "grab", "state_before": {"pos": [0,0,0]},
                           "state_after": {"pos": [1,1,1]}, "events": []}],
                "coverage_delta": {"LC": 0.1},
                "exceptions": [],
            },
            "console_logs": [],
            "actions": [{"actionType": "Grab", "objectA_fileId": "123"}],
        })
        self.assertIn("state_delta", result)
        sd = result["state_delta"]
        self.assertIsInstance(sd, dict)

    def test_observer_produces_failure_hypotheses(self):
        obs = self._make_observer(llm=None, enabled=False)
        result = obs.run({
            "executor_output": {
                "trace": [],
                "coverage_delta": {},
                "exceptions": ["NullReferenceException"],
            },
            "console_logs": ["Error: object not found"],
            "actions": [{"actionType": "Trigger", "target_fileId": "999"}],
        })
        self.assertIn("failure_hypotheses", result)
        # Should detect issues from exceptions
        self.assertIsInstance(result["failure_hypotheses"], list)

    def test_observer_with_llm_produces_strategy(self):
        """When LLM is available, Observer should produce strategy."""
        fake_llm_response = json.dumps({
            "state_delta": {
                "changed_objects": ["Knife"],
                "expected_changes": ["moved"],
                "unexpected_changes": [],
                "gates_opened": [],
                "gates_still_blocked": [],
                "semantic_failures": [],
            },
            "failure_hypotheses": [],
            "strategy": {
                "new_facts": ["Knife can be grabbed"],
                "gates_inferred": [],
                "planner_instruction": "Try oven next",
                "scheduler_bias": ["Oven"],
                "oracle_updates": [],
            },
        })
        mock_llm = MagicMock()
        mock_llm.ask.return_value = fake_llm_response
        mock_llm.extract_json.return_value = json.loads(fake_llm_response)

        obs = self._make_observer(llm=mock_llm, enabled=True)
        result = obs.run({
            "executor_output": {
                "trace": [{"action": "grab", "state_before": {}, "state_after": {}, "events": []}],
                "coverage_delta": {"LC": 0.1},
                "exceptions": [],
            },
            "console_logs": [],
            "actions": [{"actionType": "Grab"}],
        })
        self.assertIn("strategy", result)
        if result.get("strategy"):
            self.assertIn("planner_instruction", result["strategy"])


# ======================================================================
# 14. Scheduler with blackboard inputs
# ======================================================================

class TestSchedulerBlackboard(unittest.TestCase):

    def _candidates(self):
        return [
            {"gameobject_name": "Knife"},
            {"gameobject_name": "Oven"},
            {"gameobject_name": "Plate"},
        ]

    def test_scheduler_accepts_bias_and_failure_counts(self):
        """Scheduler should accept scheduler_bias and failure_counts without error."""
        from vragent2.scheduling.object_scheduler import ObjectScheduler
        from vragent2.utils.config_loader import AgentLLMConfig

        scheduler = ObjectScheduler(
            llm=MagicMock(),
            llm_config=AgentLLMConfig(enabled=False),
        )
        decision = scheduler.select_next(
            self._candidates(),
            processed=set(),
            scheduler_bias=["Oven", "Plate"],
            failure_counts={"Knife": 3},
        )
        self.assertIsNotNone(decision)

    def test_scheduler_prompt_includes_bias(self):
        """When LLM is enabled, scheduler prompt should include bias info."""
        from vragent2.scheduling.object_scheduler import ObjectScheduler
        from vragent2.utils.config_loader import AgentLLMConfig

        mock_llm = MagicMock()
        mock_llm.chat.return_value = json.dumps({
            "object_name": "Oven",
            "reason": "Observer suggested",
            "priority_score": 0.8,
            "skip_list": [],
        })
        mock_llm.extract_json.return_value = {
            "object_name": "Oven",
            "reason": "Observer suggested",
            "priority_score": 0.8,
            "skip_list": [],
        }

        scheduler = ObjectScheduler(
            llm=mock_llm,
            llm_config=AgentLLMConfig(enabled=True),
        )
        decision = scheduler.select_next(
            self._candidates(),
            processed=set(),
            scheduler_bias=["Oven"],
            failure_counts={"Knife": 2},
        )
        self.assertEqual(decision.object_name, "Oven")
        # Verify the prompt text included bias info
        call_args = mock_llm.chat.call_args
        prompt_text = call_args[0][0][1]["content"]  # user message
        self.assertIn("Observer priority", prompt_text)
        self.assertIn("Failure counts", prompt_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
