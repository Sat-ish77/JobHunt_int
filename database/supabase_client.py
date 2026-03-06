"""
Supabase client and all database operations for JobHunt Int.
Tables already exist in Supabase — this file only reads/writes data.
"""

import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv, dotenv_values
from supabase import create_client, Client
from typing import Optional

# Load .env from project root (where app.py and .env live)
_project_root = Path(__file__).resolve().parent.parent
_env_path = _project_root / ".env"

# 1) Try to load into process env (for all modules)
load_dotenv(_env_path)

# 2) Also read the file directly (handles Windows BOM / Streamlit cwd issues)
_file_env = {}
if _env_path.exists():
    try:
        raw = dotenv_values(_env_path)
        # Normalize: strip BOM from keys (Windows UTF-8 BOM breaks first key)
        for k, v in (raw or {}).items():
            key = k.lstrip("\ufeff").strip()
            if key and v is not None:
                _file_env[key] = v.strip() if isinstance(v, str) else v
    except Exception:
        _file_env = {}

SUPABASE_URL = (os.getenv("SUPABASE_URL") or _file_env.get("SUPABASE_URL") or "").strip()
SUPABASE_KEY = (os.getenv("SUPABASE_KEY") or _file_env.get("SUPABASE_KEY") or "").strip()

if not SUPABASE_URL or not SUPABASE_KEY:
    raise EnvironmentError(
        f"SUPABASE_URL and SUPABASE_KEY must be set in .env file at {_env_path}."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

USER_ID = "default_user"


def set_user(user_id: str):
    """Set the active USER_ID used by other helper functions."""
    global USER_ID
    USER_ID = user_id or "default_user"


def set_session(access_token: str, refresh_token: str):
    """
    Set the authenticated session on the Supabase client.
    Must be called after login so RLS auth.uid() returns the correct user.
    Without this, all RLS policies that check auth.uid() will fail.
    """
    try:
        supabase.auth.set_session(access_token, refresh_token)
    except Exception as e:
        print(f"[set_session] Error: {e}")


def auth_sign_up(email: str, password: str) -> dict:
    """Create a new user with email/password.

    Returns a dict: {user, session, error, needs_confirmation}
    """
    try:
        resp = supabase.auth.sign_up({"email": email, "password": password})
        print(f"[auth_sign_up] Response: {resp}")
        
        user = getattr(resp, "user", None) or (resp.get("data", {}).get("user") if isinstance(resp, dict) else None)
        session = getattr(resp, "session", None) or (resp.get("data", {}).get("session") if isinstance(resp, dict) else None)
        error = getattr(resp, "error", None) or (resp.get("error") if isinstance(resp, dict) else None)
        
        needs_confirmation = user is not None and session is None
        
        return {
            "user": user,
            "session": session,
            "error": error,
            "needs_confirmation": needs_confirmation,
        }
    except Exception as e:
        print(f"[auth_sign_up] Exception: {e}")
        return {
            "user": None,
            "session": None,
            "error": str(e),
            "needs_confirmation": False,
        }


def auth_sign_in(email: str, password: str) -> dict:
    """Sign in an existing user with email/password.

    Returns a dict: {user, session, error, needs_confirmation}
    """
    try:
        if hasattr(supabase.auth, "sign_in_with_password"):
            resp = supabase.auth.sign_in_with_password({"email": email, "password": password})
        else:
            resp = supabase.auth.sign_in({"email": email, "password": password})
        
        print(f"[auth_sign_in] Response: {resp}")
        
        user = getattr(resp, "user", None) or (resp.get("data", {}).get("user") if isinstance(resp, dict) else None)
        session = getattr(resp, "session", None) or (resp.get("data", {}).get("session") if isinstance(resp, dict) else None)
        error = getattr(resp, "error", None) or (resp.get("error") if isinstance(resp, dict) else None)
        
        needs_confirmation = user is not None and session is None and error is None
        
        return {
            "user": user,
            "session": session,
            "error": error,
            "needs_confirmation": needs_confirmation,
        }
    except Exception as e:
        print(f"[auth_sign_in] Exception: {e}")
        return {
            "user": None,
            "session": None,
            "error": str(e),
            "needs_confirmation": False,
        }


def auth_sign_out():
    """Sign out and clear the session."""
    try:
        supabase.auth.sign_out()
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
# STUDENT PROFILE
# ═══════════════════════════════════════════════════════════

def get_student_profile() -> Optional[dict]:
    try:
        response = (
            supabase.table("student_profile")
            .select("*")
            .eq("user_id", USER_ID)
            .limit(1)
            .execute()
        )
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"[get_student_profile] Error: {e}")
        return None


def save_student_profile(data: dict) -> dict:
    try:
        data["user_id"] = USER_ID
        data["updated_at"] = datetime.utcnow().isoformat()
        response = (
            supabase.table("student_profile")
            .upsert(data, on_conflict="user_id")
            .execute()
        )
        return response.data[0] if response.data else {}
    except Exception as e:
        print(f"[save_student_profile] Error: {e}")
        raise


def update_student_profile(updates: dict) -> dict:
    try:
        updates["updated_at"] = datetime.utcnow().isoformat()
        response = (
            supabase.table("student_profile")
            .update(updates)
            .eq("user_id", USER_ID)
            .execute()
        )
        return response.data[0] if response.data else {}
    except Exception as e:
        print(f"[update_student_profile] Error: {e}")
        raise


# ═══════════════════════════════════════════════════════════
# RESUMES
# ═══════════════════════════════════════════════════════════

def save_resume(name: str, content: str, embedding: list) -> dict:
    try:
        response = (
            supabase.table("resumes")
            .insert({
                "user_id": USER_ID,
                "name": name,
                "content": content,
                "embedding": embedding,
            })
            .execute()
        )
        return response.data[0] if response.data else {}
    except Exception as e:
        print(f"[save_resume] Error: {e}")
        raise


def get_all_resumes() -> list:
    try:
        response = (
            supabase.table("resumes")
            .select("*")
            .eq("user_id", USER_ID)
            .order("created_at", desc=True)
            .execute()
        )
        return response.data or []
    except Exception as e:
        print(f"[get_all_resumes] Error: {e}")
        return []


def get_resume_by_id(resume_id: str) -> Optional[dict]:
    try:
        response = (
            supabase.table("resumes")
            .select("*")
            .eq("id", resume_id)
            .limit(1)
            .execute()
        )
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"[get_resume_by_id] Error: {e}")
        return None


def update_resume_content(resume_id: str, content: str) -> dict:
    try:
        response = (
            supabase.table("resumes")
            .update({
                "content": content,
                "updated_at": datetime.utcnow().isoformat(),
            })
            .eq("id", resume_id)
            .execute()
        )
        return response.data[0] if response.data else {}
    except Exception as e:
        print(f"[update_resume_content] Error: {e}")
        raise


def delete_resume(resume_id: str):
    try:
        supabase.table("resumes").delete().eq("id", resume_id).execute()
    except Exception as e:
        print(f"[delete_resume] Error: {e}")
        raise


# ═══════════════════════════════════════════════════════════
# JOBS
# ═══════════════════════════════════════════════════════════

def save_jobs(jobs: list) -> list:
    try:
        if not jobs:
            return []
        response = (
            supabase.table("jobs")
            .upsert(jobs, on_conflict="url")
            .execute()
        )
        return response.data or []
    except Exception as e:
        print(f"[save_jobs] Error: {e}")
        return []


def get_all_jobs() -> list:
    try:
        response = (
            supabase.table("jobs")
            .select("*")
            .order("fetched_at", desc=True)
            .execute()
        )
        return response.data or []
    except Exception as e:
        print(f"[get_all_jobs] Error: {e}")
        return []


def get_sponsored_jobs() -> list:
    try:
        response = (
            supabase.table("jobs")
            .select("*")
            .eq("h1b_sponsor_history", True)
            .order("fetched_at", desc=True)
            .execute()
        )
        return response.data or []
    except Exception as e:
        print(f"[get_sponsored_jobs] Error: {e}")
        return []


# ═══════════════════════════════════════════════════════════
# APPLICATIONS
# ═══════════════════════════════════════════════════════════

def save_application(job_id: str, resume_id: str,
                     cover_letter: str, rewritten_resume: str) -> dict:
    try:
        response = (
            supabase.table("applications")
            .insert({
                "user_id": USER_ID,
                "job_id": job_id,
                "resume_id": resume_id,
                "cover_letter": cover_letter,
                "rewritten_resume": rewritten_resume,
                "status": "draft",
            })
            .execute()
        )
        return response.data[0] if response.data else {}
    except Exception as e:
        print(f"[save_application] Error: {e}")
        raise


def get_applications() -> list:
    try:
        response = (
            supabase.table("applications")
            .select("*, jobs(*), resumes(*)")
            .eq("user_id", USER_ID)
            .order("created_at", desc=True)
            .execute()
        )
        return response.data or []
    except Exception as e:
        print(f"[get_applications] Error: {e}")
        return []


def update_application_status(app_id: str, status: str):
    try:
        supabase.table("applications").update(
            {"status": status}
        ).eq("id", app_id).execute()
    except Exception as e:
        print(f"[update_application_status] Error: {e}")
        raise


def update_cover_letter(app_id: str, cover_letter: str):
    try:
        supabase.table("applications").update(
            {"cover_letter": cover_letter}
        ).eq("id", app_id).execute()
    except Exception as e:
        print(f"[update_cover_letter] Error: {e}")
        raise


# ═══════════════════════════════════════════════════════════
# CAREER COACH MEMORY (conversations)
# ═══════════════════════════════════════════════════════════

def save_message(role: str, content: str):
    try:
        supabase.table("conversations").insert({
            "user_id": USER_ID,
            "role": role,
            "content": content,
        }).execute()
    except Exception as e:
        print(f"[save_message] Error: {e}")
        raise


def get_conversation_history(limit: int = 30) -> list:
    try:
        response = (
            supabase.table("conversations")
            .select("*")
            .eq("user_id", USER_ID)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception as e:
        print(f"[get_conversation_history] Error: {e}")
        return []


def clear_conversation_history():
    try:
        supabase.table("conversations").delete().eq(
            "user_id", USER_ID
        ).execute()
    except Exception as e:
        print(f"[clear_conversation_history] Error: {e}")
        raise


# ═══════════════════════════════════════════════════════════
# IMMIGRATION NEWS
# ═══════════════════════════════════════════════════════════

def save_immigration_news(articles: list):
    try:
        if not articles:
            return
        supabase.table("immigration_news").upsert(
            articles, on_conflict="url"
        ).execute()
    except Exception as e:
        print(f"[save_immigration_news] Error: {e}")
        raise


def get_immigration_news(limit: int = 6) -> list:
    try:
        response = (
            supabase.table("immigration_news")
            .select("*")
            .order("published_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception as e:
        print(f"[get_immigration_news] Error: {e}")
        return []


def get_last_news_fetch_time() -> Optional[datetime]:
    try:
        response = (
            supabase.table("immigration_news")
            .select("fetched_at")
            .order("fetched_at", desc=True)
            .limit(1)
            .execute()
        )
        if response.data:
            fetched = response.data[0]["fetched_at"]
            if fetched:
                return datetime.fromisoformat(
                    fetched.replace("Z", "+00:00")
                )
        return None
    except Exception as e:
        print(f"[get_last_news_fetch_time] Error: {e}")
        return None