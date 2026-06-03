# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0-alpha] - 2026-06-04

### Added
- Developed `NetworkAgent` in `agents/network.py` monitoring active TCP connections via `psutil`.
- Integrated network signature rules verification from `configs/network_rules.yaml`.
- Added `--network` flag support in `main.py` CLI orchestrator.
- Created `tests/test_network_agent.py` unit test suite.

## [0.2.0-alpha] - 2026-06-04

### Added
- Developed `ReconAgent` in `agents/recon.py` executing async local package retrieval and port scanning.
- Added `--recon` flag support in `main.py` CLI orchestrator.
- Created `tests/test_recon_agent.py` unit test suite.

## [0.1.0-alpha] - 2026-06-04

### Added
- Created PEP 517 project structure with `src/tracer_mesh` layout.
- Implemented Redis Streams async broker client (`MessageBroker`) in `core/broker.py`.
- Developed HTTPX-based local Ollama client (`LLMClient`) in `core/llm.py` supporting JSON mode and embedding calculations.
- Integrated thread-safe SQLite and ChromaDB state store (`StateStore`) in `core/db.py`.
- Created Jinja2 templates loader and vulnerability analysis system prompt.
- Developed `BaseAgent` and `VulnerabilityAnalysisAgent` for stream telemetry correlation and automated reasoning.
- Implemented `scripts/seed_cve.py` to seed SQLite/ChromaDB databases.
- Implemented `scripts/mock_telemetry.py` to publish mock payloads to Redis Streams.
- Built CLI Orchestrator entry point in `main.py` supporting environment variable parsing and graceful shutdown.
- Configured Ruff code format guidelines and wrote comprehensive Pytest suites.
- Created GitHub Actions CI integration workflow.
- Wrote documentation folder containing `architecture.md` and `user-guide.md`.

