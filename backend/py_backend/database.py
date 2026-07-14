from urllib.parse import quote
import requests

from .config import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL


TABLE_MAP = {
    "textbooks": "textbooks",
    "lessons": "lesson_contents",
    "assessments": "assessments",
    "students": "student_profiles",
    "teachers": "teacher_profiles",
    "users": "profiles",
    "chunks": "textbook_chunks",
    "video_jobs": "video_jobs",
}


class SupabaseError(RuntimeError):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


def require_supabase():
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise SupabaseError("Supabase is not configured. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to backend/.env.")


def headers():
    require_supabase()
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def table_url(entity: str) -> str:
    table = TABLE_MAP.get(entity, entity)
    return f"{SUPABASE_URL}/rest/v1/{table}"


def parse_response(response: requests.Response):
    if response.status_code >= 400:
        try:
            data = response.json()
            message = data.get("message") or data.get("error") or str(data)
        except Exception:
            message = response.text
        raise SupabaseError(message, response.status_code)
    if not response.text:
        return None
    return response.json()


def list_records(entity: str, sort: str = "created_at", ascending: bool = False, limit: int | None = None):
    params = {"select": "*"}
    if sort:
        direction = "asc" if ascending else "desc"
        params["order"] = f"{sort}.{direction}"
    if limit:
        params["limit"] = str(limit)
    return parse_response(requests.get(table_url(entity), headers=headers(), params=params, timeout=30))


def filter_records(entity: str, filters: dict | None = None, limit: int | None = None, sort: str = "created_at", ascending: bool = False):
    params = {"select": "*"}
    for key, value in (filters or {}).items():
        if value not in (None, ""):
            params[key] = f"eq.{value}"
    if sort:
        direction = "asc" if ascending else "desc"
        params["order"] = f"{sort}.{direction}"
    if limit:
        params["limit"] = str(limit)
    return parse_response(requests.get(table_url(entity), headers=headers(), params=params, timeout=30))


def get_record(entity: str, record_id: str):
    data = filter_records(entity, {"id": record_id}, limit=1)
    if not data:
        raise SupabaseError(f"{entity} record not found", 404)
    return data[0]


def create_record(entity: str, payload: dict):
    data = parse_response(requests.post(table_url(entity), headers=headers(), json=payload, timeout=30))
    return data[0] if isinstance(data, list) else data


def update_record(entity: str, record_id: str, payload: dict):
    url = f"{table_url(entity)}?id=eq.{quote(str(record_id), safe='')}"
    data = parse_response(requests.patch(url, headers=headers(), json=payload, timeout=30))
    return data[0] if isinstance(data, list) and data else data


def delete_record(entity: str, record_id: str):
    url = f"{table_url(entity)}?id=eq.{quote(str(record_id), safe='')}"
    parse_response(requests.delete(url, headers=headers(), timeout=30))
    return {"ok": True}


def delete_where(entity: str, filters: dict):
    params = {key: f"eq.{value}" for key, value in filters.items() if value not in (None, "")}
    parse_response(requests.delete(table_url(entity), headers=headers(), params=params, timeout=30))
    return {"ok": True}
