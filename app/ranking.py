import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Small, fast model. Good enough for short scientific abstracts and loads
# quickly, which matters for a service that is expected to start with a
# single command.
MODEL_NAME = "all-MiniLM-L6-v2"

# Weights for combining the two signals into a single relevance score.
EMBEDDING_WEIGHT = 0.85
KEYWORD_WEIGHT = 0.15


def _normalize_text(text: str) -> str:
    return text.lower().strip()


def _build_profile_embedding(profile: dict, model: SentenceTransformer):
    """Embed a journal profile in a way that is not biased by scope-list length.

    Concatenating aims + all scope items into a single string and embedding
    it as one blob would give journals with longer scope lists (e.g. 32
    items for Physics vs. 16 for AI) a more diverse, "generic" embedding
    that ends up with inflated similarity to many unrelated abstracts.
    Embedding aims and each scope item separately, then averaging, keeps
    every topic equally weighted regardless of how many topics a journal
    lists.
    """
    aims_embedding = model.encode([profile["aims"]])[0]
    scope = profile.get("scope", [])
    if scope:
        scope_embeddings = model.encode(scope)
        scope_embedding = scope_embeddings.mean(axis=0)
        return (aims_embedding + scope_embedding) / 2
    return aims_embedding


class RankingService:
    """Ranks journals against a manuscript abstract.

    Journal profiles do not change between requests, so their embeddings
    are computed once, at construction time, and reused for every call to
    `rank`. Only the abstract embedding is computed per request.
    """

    def __init__(self, profiles: list[dict], model_name: str = MODEL_NAME):
        self._profiles = profiles
        self._model = SentenceTransformer(model_name)
        self._profile_embeddings = np.array(
            [_build_profile_embedding(p, self._model) for p in profiles]
        )

    def _keyword_bonus(self, abstract: str, scope: list[str]) -> float:
        """Fraction of the journal's scope keywords that appear in the abstract."""
        if not scope:
            return 0.0
        abstract_norm = _normalize_text(abstract)
        matches = sum(1 for item in scope if _normalize_text(item) in abstract_norm)
        return matches / len(scope)

    def rank(self, abstract: str) -> list[dict]:
        abstract_embedding = self._model.encode([abstract])
        similarities = cosine_similarity(abstract_embedding, self._profile_embeddings)[0]

        results = []
        for profile, embedding_score in zip(self._profiles, similarities):
            keyword_bonus = self._keyword_bonus(abstract, profile.get("scope", []))
            relevance_score = (
                EMBEDDING_WEIGHT * embedding_score + KEYWORD_WEIGHT * keyword_bonus
            )

            relevance_score = max(0.0, relevance_score)
            results.append(
                {
                    "journal": profile["journal"],
                    "relevance_score": round(float(relevance_score), 4),
                }
            )

        return sorted(results, key=lambda r: r["relevance_score"], reverse=True)
