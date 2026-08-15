import json
import os
from pathlib import Path
from typing import Any

# Use environment variables if available, otherwise fallback to the provided values
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://wttssbxoptowkxdjtuky.supabase.co")
# Note: we use the service_role key to bypass RLS for now so the backend can freely insert/select rows without user auth setup in Supabase.
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind0dHNzYnhvcHRvd2t4ZGp0dWt5Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc1NTg4NiwiZXhwIjoyMDg5MzMxODg2fQ.rGnrPaL3alNpMLsTjji5RKumpEYD5MJtb-fkbu78tOg")
LOCAL_DATA_PATH = Path(__file__).resolve().parent / "local_data.json"

supabase: Any = None


def _get_supabase_client():
    global supabase
    if supabase is None:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return supabase

# Dependency mock for FastAPI routes (to maintain compatibility with existing route signature)
def get_db():
    yield _get_supabase_client()


def load_local_data() -> dict[str, Any]:
    if not LOCAL_DATA_PATH.exists():
        return {"users": [], "health_records": []}

    with LOCAL_DATA_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    data.setdefault("users", [])
    data.setdefault("health_records", [])
    return data


def save_local_data(data: dict[str, Any]) -> None:
    with LOCAL_DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=True, indent=2)


def next_local_id(items: list[dict[str, Any]]) -> int:
    if not items:
        return 1
    return max(int(item.get("id", 0)) for item in items) + 1
