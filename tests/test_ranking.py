from app.profiles import load_journal_profiles
from app.ranking import RankingService

_service = RankingService(load_journal_profiles())


def test_rank_returns_all_journals():
    ranked = _service.rank("A study of quantum physics and condensed matter.")
    assert len(ranked) == 4
    assert {r["journal"] for r in ranked} == {"Molecules", "AI", "Physics", "Energies"}


def test_rank_sorted_descending():
    ranked = _service.rank("A study of quantum physics and condensed matter.")
    scores = [r["relevance_score"] for r in ranked]
    assert scores == sorted(scores, reverse=True)


def test_rank_reuses_precomputed_profile_embeddings():
    # Calling rank() twice should not change the cached profile embeddings.
    embeddings_before = _service._profile_embeddings.copy()
    _service.rank("Some abstract about batteries and solar energy storage.")
    assert (embeddings_before == _service._profile_embeddings).all()
