# Journal Finder API

A REST API that ranks 4 MDPI journals (Molecules, AI, Physics, Energies) by
how well a manuscript abstract fits each journal's scope.

## Running the service

### With Docker (recommended)

```bash
docker compose up --build
```

The first build takes a while, since it downloads the sentence-transformers
model at build time (see [Approach](#approach) for why). Subsequent builds
reuse the Docker layer cache and are fast. The API is then available at
`http://localhost:8000`.

### Without Docker

```bash
uv sync
uv run uvicorn app.main:app --reload
```

## Calling the endpoint

```bash
curl -X POST http://localhost:8000/find-journal \
  -H "Content-Type: application/json" \
  -d '{"abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks in an encoder-decoder configuration. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train. Our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over the existing best results, including ensembles by over 2 BLEU. On the WMT 2014 English-to-French translation task, our model establishes a new single-model state-of-the-art BLEU score of 41.8 after training for 3.5 days on eight GPUs, a small fraction of the training costs of the best models from the literature. We show that the Transformer generalizes well to other tasks by applying it successfully to English constituency parsing both with large and limited training data."}'
```

Example response:

```json
  {
  "ranked_journals": [
    { "journal": "AI", "relevance_score": 0.161 },
    { "journal": "Physics", "relevance_score": 0.0478 },
    { "journal": "Energies", "relevance_score": 0.0262 },
    { "journal": "Molecules", "relevance_score": 0.0 }
  ]
}
```

`relevance_score` is a similarity-based ranking signal, not a calibrated
probability, so scores across different abstracts are not directly
comparable to each other. It's clamped at 0 (raw cosine similarity can dip
slightly negative for genuinely unrelated content); this doesn't affect
the ranking order, only how the lowest scores are displayed.

There is also a `GET /health` endpoint for basic liveness checks.

## Running tests

```bash
uv run pytest
```

`tests/test_api.py` covers the HTTP layer (status codes, response shape,
validation). `tests/test_ranking.py` covers `RankingService` directly.

## Project structure

```
journal-finder/
├── app/
│   ├── main.py        # FastAPI app and the /find-journal endpoint
│   ├── schemas.py      # Pydantic request/response models
│   ├── profiles.py     # Loads journal profiles from JSON
│   ├── ranking.py       # RankingService: embedding + keyword scoring
│   └── data/
│       └── journals.json  # Manually prepared journal profiles (Aims + Scope)
├── tests/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── uv.lock
```

## Approach

The service is built around one core idea: journal
reference profiles, compared to the incoming abstract with embedding
similarity.

**1. Journal profiles** (`app/data/journals.json`): for each of the 4
journals, `app/data/journals.json` contains a manually prepared `aims`
text and a `scope` list of research areas, based on each journal's MDPI
"Aims & Scope" page.Only the Aims and Scope content was kept. This file is committed 
to the repository and have a structure:
```json
[
  {
    "journal": "...",
    "url": "https://www.mdpi.com/journal/.../about#Scope",
    "aims": "...",
    "scope": [
      "...",
      "..."
    	]
  },
]

```
**2. Online ranking** (`app/ranking.py`): `RankingService` is constructed
once, at application startup (`app/main.py`). At construction time it loads
the 4 journal profiles and computes their embeddings once, since profiles
don't change between requests. Each call to `rank(abstract)` then only
computes the embedding for that one abstract and reuses the cached profile
embeddings. Scoring combines two signals:

- **Semantic similarity** (weight 0.85): cosine similarity between the
  sentence-transformers embedding (`all-MiniLM-L6-v2`) of the abstract and
  each journal's profile embedding (the average of its `aims` embedding
  and its per-item `scope` embeddings).
- **Keyword overlap** (weight 0.15): the fraction of a journal's `scope`
  items that literally appear in the abstract, as a lightweight
  correction for cases where the abstract uses the exact same terminology
  as the journal's scope list.

### Why this approach

- Journal profiles are embedded per-item (aims + each scope item separately, 
  then averaged) instead of as one concatenated string, so a journal with a 
  longer scope list (e.g. Physics' 32 items vs. AI's 16) doesn't get an unfairly 
  "generic" embedding that scores high against everything.
- Embeddings capture meaning, not just exact words, so an abstract about 
  "transformer-based language models" still matches AI's scope without saying "AI."
- A small, fast sentence-transformers model keeps startup and inference quick, 
  which fits a service meant to run with one `docker compose up`.
- The keyword bonus is a simple, transparent nudge (weight 0.15) on top of the embedding score, 
  not a second model.
- With 4 journals, a vector database is overkill - profile embeddings are computed 
  once at startup and compared with cosine similarity. Same retrieval pattern 
  as RAG, just without the index.
- The model is downloaded at `docker build` time rather than at container startup, 
  so builds are slower but the running container doesn't need internet access.
- `uv.lock` is committed and installed with `--frozen`, so builds are reproducible.


### Trade-offs and simplifying assumptions

- No fine-tuning: there's no labeled abstract → journal dataset to train on.
- `relevance_score` is a similarity score, not a calibrated probability.
- Journal scopes overlap (e.g. "machine learning" appears in both AI and Physics), 
  so borderline abstracts can score close together - that's expected, not a bug.
- `journals.json` is maintained by hand - no scraping or freshness check, 
  though the format would work just as well if generated from a database or 
  scraper later.

## Known limitations / what I would improve next

- Add an LLM reranking/explanation step on top of the retrieval ranking - the task allows it, and `RankingService.rank()` is built so this could slot in without touching the API layer.
- Build a small evaluation set of real abstracts with known correct journals - right now I've only spot-checked obvious cases.
- Move keyword matching to stemmed/lemmatized comparison instead of plain substring matching.


## Environment variables

None required - no external LLM API is used. If reranking were added later, its API key would come from an environment variable, with a fallback to embedding-only ranking if it's not set.
