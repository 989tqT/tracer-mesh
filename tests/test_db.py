import pytest

from tracer_mesh.core.db import StateStore


@pytest.fixture
def temp_db_dir(tmp_path):
    # create temporary directories for test database
    db_dir = tmp_path / "data" / "cve_db"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_file = db_dir / "nvd_mirror.db"
    chroma_dir = db_dir / "chroma"
    yield str(db_file), str(chroma_dir)


@pytest.mark.asyncio
async def test_state_store_operations(temp_db_dir):
    db_path, chroma_path = temp_db_dir

    # init test state store database
    store = StateStore(db_path=db_path, chroma_path=chroma_path)
    store.init_db()

    # prepare mock input cve records
    mock_cves = [
        {
            "cve_id": "CVE-TEST-1",
            "product": "test-pkg",
            "version": "1.2.3",
            "severity": "MEDIUM",
            "description": "vulnerability vulnerability in test package component",
            "embedding": [0.1, 0.2, 0.3],
        }
    ]

    # perform insert operation
    await store.insert_cves(cves=mock_cves)

    # test query search by product name
    rows = await store.search_cve_by_product(product="test-pkg", version="1.2.3")
    assert len(rows) == 1
    assert rows[0]["cve_id"] == "CVE-TEST-1"
    assert rows[0]["severity"] == "MEDIUM"

    # test query search by vector search
    vector_results = await store.search_cve_by_vector(
        query_text="vulnerability", embedding=[0.1, 0.2, 0.3], limit=1
    )
    assert len(vector_results) == 1
    assert vector_results[0]["cve_id"] == "CVE-TEST-1"
