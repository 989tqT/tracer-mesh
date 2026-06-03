# 📦 Tracer Mesh (TM)

[![CI Status](https://img.shields.io/github/actions/workflow/status/989tqT/tracer-mesh/ci.yml?branch=main&style=flat-square)](https://github.com/989tqT/tracer-mesh/actions)
[![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg?style=flat-square)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.11%20%7C%203.12-green?style=flat-square)](https://www.python.org/)
[![Local LLM](https://img.shields.io/badge/Local%20LLM-Ollama%20%7C%20vLLM-orange?style=flat-square)](https://ollama.com)

**Tracer Mesh** is a 100% open-source, local-first, AI Agent  designed to scan local system configurations, analyze network traffic streams, query local CVE repositories, threat hunt vulnerabilities, and generate automated code patches.

---

## 🚀 Key Features

* **Event-Driven Broker Architecture:** Employs async Redis Streams to handle telemetry ingestion and group consumer distribution.
* **Local RAG Integration:** Cross-references SQLite records and ChromaDB vector embeddings generated locally via Ollama.
* **Structured LLM Assessments:** Prompts local LLMs (e.g., Llama-3, Mistral) to return parsed JSON vulnerability evaluations.
* **Strict Security Enforcement:** Hardens internal APIs against parameter injections using Python's keyword-only arguments.

---

## 🗺️ System Architecture

```mermaid
graph TD
    %% Telemetry
    Sys[System State] -->|telemetry.system.inventory| Broker[(Redis Streams)]
    Net[Network Traffic] -->|telemetry.network.events| Broker

    %% Core Broker & Storage
    Broker -->|Consume Events| VulnAgent[Vulnerability Agent]
    VulnAgent -->|Query SQL / Vector| StateStore[(SQLite + ChromaDB)]
    VulnAgent -->|Structured Query| Ollama[Local Ollama / vLLM]
    Ollama -->|Return JSON| VulnAgent

    %% Remediation
    VulnAgent -->|analysis.vulnerability.found| Broker
    Broker -->|Consume Findings| PatchAgent[Patch Proposer Agent]
    PatchAgent -->|Generate Fix| Ollama
    PatchAgent -->|remediation.patch.proposed| Output[Admin Control Panel]
```

Detailed explanation of each module is documented in [docs/architecture.md](docs/architecture.md).

---

## ⚡ Quick Start

### 1. Boot up Local Redis Broker
Ensure a local Redis server is running:
```bash
docker run -d --name redis-broker -p 6379:6379 redis:alpine
```

### 2. Pull Local LLM & Embedding Models
Make sure Ollama is installed and running, then pull:
```bash
ollama pull llama3
ollama pull nomic-embed-text
```

### 3. Clone and Install Dependencies
```bash
git clone https://github.com/your-org/tracer-mesh.git
cd tracer-mesh
pip install ruff pytest pytest-asyncio redis httpx chromadb jinja2 pyyaml pydantic-settings
cp .env.example .env
```

### 4. Seed database and Execute CLI demo
```bash
# Seed SQLite and ChromaDB databases
$env:PYTHONPATH="src"; python scripts/seed_cve.py

# Launch CLI runner in mock telemetry ingestion mode
$env:PYTHONPATH="src"; python -m tracer_mesh.main --mock
```

---

## 📚 Technical Documentation

* **[Architecture Overview](docs/architecture.md):** Topology and component descriptions.
* **[User Guide](docs/user-guide.md):** Setup, configuration details, and custom rules mapping.
* **[Changelog](CHANGELOG.md):** Releases history and changes tracking.
* **[Contributing Guidelines](CONTRIBUTING.md):** Coding standards and PR instructions.
* **[Security Policy](SECURITY.md):** Guidelines for reporting security issues.

---

## 📄 License

Distributed under the Apache-2.0 License. See [LICENSE](LICENSE) for more information.
