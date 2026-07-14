from fastapi import FastAPI

from app.profiles import load_journal_profiles
from app.ranking import RankingService
from app.schemas import FindJournalRequest, FindJournalResponse

app = FastAPI(
    title="Journal Finder API",
    description="Ranks MDPI journals by relevance to a manuscript abstract.",
)

# Built once at startup: loads the 4 journal profiles and precomputes their
# embeddings, since profiles do not change between requests.
ranking_service = RankingService(load_journal_profiles())


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/find-journal", response_model=FindJournalResponse)
def find_journal(request: FindJournalRequest) -> FindJournalResponse:
    ranked = ranking_service.rank(request.abstract)
    return FindJournalResponse(ranked_journals=ranked)
