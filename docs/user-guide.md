# Tracer Mesh User Guide

This guide walks you through setting up and running the Tracer Mesh threat hunting on your local machine or private VPS.

## Prerequisites

- **Python:** Version 3.11 or 3.12.
- **Docker:** Installed and running locally (for Redis).
- **Ollama:** Installed and running locally (for LLM and embeddings).

## Installation

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/your-org/tracer-mesh.git
   cd tracer-mesh
   ```

2. **Install Dependencies:**
   ```bash
   pip install ruff pytest pytest-asyncio redis httpx chromadb jinja2 pyyaml pydantic-settings psutil
   ```

3. **Configure Environment:**
   Copy the example environment file and configure parameters:
   ```bash
   cp .env.example .env
   ```

## Infrastructure Setup

1. **Launch Redis Broker:**
   Ensure a local Redis instance is running. You can run one in Docker:
   ```bash
   docker run -d --name redis-broker -p 6379:6379 redis:alpine
   ```

2. **Configure Ollama LLM and Embeddings:**
   Ensure Ollama is running, then pull the required models:
   ```bash
   # Pull the reasoning model
   ollama pull llama3
   # Pull the embedding model
   ollama pull nomic-embed-text
   ```

## Operations Workflow

### Step 1: Seed local CVE Databases
Populate your local database indexes with critical CVE definitions and compute vector representations:
```bash
$env:PYTHONPATH="src"; python scripts/seed_cve.py
```
This initializes the SQLite database and populates vector keys into ChromaDB using Ollama embeddings.

### Step 2: Launch the Agent CLI Orchestrator
Start the main runtime event loop. Run with the `--mock` flag to automatically trigger telemetry events for verification:
```bash
$env:PYTHONPATH="src"; python -m tracer_mesh.main --mock
```

You should see logs indicating that telemetry has been consumed and that the `VulnerabilityAnalysisAgent` has successfully queried the local LLM and output security reports to the finding stream.

### Running Real Host Telemetry Ingestion
To launch the orchestrator with the active local system discovery agent (polling installed libraries and open ports on 127.0.0.1 every 60s) instead of mock telemetry:
```bash
$env:PYTHONPATH="src"; python -m tracer_mesh.main --recon
```
This runs the `ReconAgent` in the background, periodically publishing host system states directly to the Redis Streams broker pipeline.

### Running Real Network Connection Telemetry Ingestion
To launch the orchestrator with the active local network connection monitoring agent (inspecting established connections against signature rules):
```bash
$env:PYTHONPATH="src"; python -m tracer_mesh.main --network
```

### Running Patch Proposer Agent
To activate the remediation patch generation worker listening to found vulnerability streams:
```bash
$env:PYTHONPATH="src"; python -m tracer_mesh.main --patch
```

You can combine active agents in the orchestrator run command:
```bash
$env:PYTHONPATH="src"; python -m tracer_mesh.main --recon --network --patch
```
