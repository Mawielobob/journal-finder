import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "data" / "journals.json"


def load_journal_profiles() -> list[dict]:
    """Load the preprocessed journal profiles."""
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)
