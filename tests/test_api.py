from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SAMPLE_ABSTRACT = (
    "We propose a deep learning approach based on transformer neural "
    "networks for natural language understanding tasks, evaluated on "
    "several benchmark datasets."
)


def test_find_journal_returns_200():
    response = client.post("/find-journal", json={"abstract": SAMPLE_ABSTRACT})
    assert response.status_code == 200


def test_find_journal_response_shape():
    response = client.post("/find-journal", json={"abstract": SAMPLE_ABSTRACT})
    body = response.json()
    assert "ranked_journals" in body
    assert len(body["ranked_journals"]) == 4


def test_find_journal_results_sorted_descending():
    response = client.post("/find-journal", json={"abstract": SAMPLE_ABSTRACT})
    scores = [item["relevance_score"] for item in response.json()["ranked_journals"]]
    assert scores == sorted(scores, reverse=True)


def test_find_journal_ai_abstract_ranks_ai_journal_first():
    response = client.post("/find-journal", json={"abstract": SAMPLE_ABSTRACT})
    top_journal = response.json()["ranked_journals"][0]["journal"]
    assert top_journal == "AI"


def test_empty_abstract_returns_validation_error():
    response = client.post("/find-journal", json={"abstract": "   "})
    assert response.status_code == 422
