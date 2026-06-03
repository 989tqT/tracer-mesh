# Contributing to Tracer Mesh

We welcome contributions from the cybersecurity and software engineering community! Please follow these guidelines when submitting pull requests.

## Development Setup

1. **Clone and Install Dependencies:**
   ```bash
   git clone https://github.com/your-org/tracer-mesh.git
   cd tracer-mesh
   pip install ruff pytest pytest-asyncio redis httpx chromadb jinja2 pyyaml pydantic-settings
   ```

2. **Run Tests locally:**
   Verify that your modifications do not break the test suite before submitting:
   ```bash
   $env:PYTHONPATH="src"; python -m pytest tests/
   ```

3. **Code Formatting & Linting:**
   We enforce formatting consistency using Ruff:
   ```bash
   ruff check .
   ```

## Development Guidelines

- **Keyword-Only Parameters:** All public APIs and critical methods handling sensitive system data must enforce keyword-only parameters (`*`) to prevent parameter injection.
- **Code Comments:** Code comments must conform to fast-typing developer style (all-lowercase, drop conjugations/articles, no trailing punctuation).
- **Unit Testing:** Write mock-based tests for new agents or core features under the `tests/` directory.
