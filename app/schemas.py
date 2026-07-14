from pydantic import BaseModel, Field, field_validator


class FindJournalRequest(BaseModel):
    abstract: str = Field(..., description="Abstract of the manuscript")

    @field_validator("abstract")
    @classmethod
    def abstract_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("abstract must not be empty")
        return value


class JournalResult(BaseModel):
    journal: str
    relevance_score: float


class FindJournalResponse(BaseModel):
    ranked_journals: list[JournalResult]
