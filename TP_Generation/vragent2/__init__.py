"""
VRAgent 2.0 — Multi-Agent Closed-Loop Test Plan Generation

Architecture: RAG + Multi-Agent Pipeline (Plan → Verify → Execute → Observe)

Modules:
    contracts   – Agent I/O schema definitions
    retrieval   – Project Retrieval Layer (scene/script/UI/runtime indexing)
    agents      – Planner / Verifier / Executor / Observer
    graph       – Gate Graph & Failure-to-Condition reasoning
    exploration – Explore controller (Expand / Exploit / Recover)
    controller  – Top-level orchestrator
"""

__version__ = "2.0.0-alpha"
