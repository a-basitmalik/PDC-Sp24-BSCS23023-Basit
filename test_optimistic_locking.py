from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app import STUDENT_ID, app


client = TestClient(app)


def test_student_id_header_is_added_to_every_response():
    response = client.get("/documents/shared-notes")

    assert response.status_code == 200
    assert response.headers["X-Student-ID"] == STUDENT_ID


def test_naive_update_loses_first_writer_change():
    client.post("/reset")

    snapshot_for_alice = client.get("/documents/shared-notes").json()
    snapshot_for_bob = client.get("/documents/shared-notes").json()

    alice_response = client.put(
        "/naive/documents/shared-notes",
        json={"content": "Alice adds CAP theorem notes"},
    )
    bob_response = client.put(
        "/naive/documents/shared-notes",
        json={"content": "Bob adds circuit breaker notes"},
    )
    final_document = client.get("/documents/shared-notes").json()

    assert snapshot_for_alice["version"] == snapshot_for_bob["version"] == 1
    assert alice_response.status_code == 200
    assert bob_response.status_code == 200
    assert final_document["content"] == "Bob adds circuit breaker notes"
    assert "Alice" not in final_document["content"]


def test_optimistic_locking_rejects_stale_concurrent_update():
    client.post("/reset")

    original = client.get("/documents/shared-notes").json()

    def submit_edit(content: str):
        return client.put(
            "/documents/shared-notes",
            headers={"If-Match": str(original["version"])},
            json={"content": content},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(
                submit_edit,
                [
                    "Alice adds CAP theorem notes",
                    "Bob adds circuit breaker notes",
                ],
            )
        )

    status_codes = sorted(response.status_code for response in responses)
    final_document = client.get("/documents/shared-notes").json()

    assert status_codes == [200, 409]
    assert final_document["version"] == 2
    assert final_document["content"] in {
        "Alice adds CAP theorem notes",
        "Bob adds circuit breaker notes",
    }
