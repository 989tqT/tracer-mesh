# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0-alpha] - 2026-06-04 ~ 2026-06-07

### Added
- Developed `PatchAgent` in `agents/patch.py` proposing remediation patches for identified CVEs.
- Created `templates/patch_generation.j2` Jinja2 prompt template for structured LLM remediation suggestions.
- Integrated `--patch` flag in `main.py` CLI orchestrator.
- Created `tests/test_patch_agent.py` unit test suite.
- Created `scripts/setup_models.py` automatic environment configuration script to detect system RAM, pull reasoning models via local/docker CLI, and update `.env` settings.
- Added connection retry logic in `LLMClient.generate` and `get_embedding` API requests to handle temporary local model client disconnects.
- Implemented robust database fallback in `VulnerabilityAnalysisAgent` to handle local model query failure.
- Refactored `PatchAgent` fallback logic to support both exception recovery and missing/malformed JSON schema property fallbacks.
- Added socket timeout (`socket_timeout=10.0`, `socket_connect_timeout=5.0`), connection retry (`retry_on_timeout=True`), and connection keepalive (`health_check_interval=30`) parameters to `MessageBroker` Redis client.
- Renamed system settings environment properties to standard `REASONING_MODEL` and added `AliasChoices` validator to support fallback legacy `LLM_MODEL` mappings.

### Fixed
- Fixed CI pipeline dependencies configuration in `.github/workflows/ci.yml` by adding `psutil`.
- Fixed relative rules configuration file path resolution in `NetworkAgent`.
- Disabled default embedding functions in ChromaDB persistent collection creation to prevent vector dimension mismatch.
- Passed the configured `embedding_model` to `VulnerabilityAnalysisAgent` to align embeddings queries with `nomic-embed-text`.
- Added defensive check in `StateStore.search_cve_by_vector` to prevent query fallback errors if vector embedding calculation fails.
- Optimized `VulnerabilityAnalysisAgent._query_local_cve_db` to perform SQLite database queries and vector embeddings lookups concurrently using `asyncio.gather`, reducing host inventory scan times from 100+ seconds to under 5 seconds.
- Refactored `NetworkAgent` execution loop to run in a non-blocking background task, permitting the orchestrator to boot subsequent agents.
- Added operational log reporting found CVE counts for scanned system inventory components.
- Removed `format` parameter from local Ollama API payload in `LLMClient.generate` to support compatibility across all model environments.
- Hardened prompt templates (`vuln_analysis.j2` and `patch_generation.j2`) to strictly request JSON formatted response outputs.
- Implemented regex-based JSON substring extraction in `VulnerabilityAnalysisAgent` and `PatchAgent` to robustly parse LLM outputs.

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

