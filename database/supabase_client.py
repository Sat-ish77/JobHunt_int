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


def auth_reset_password(email: str) -> dict:
    """Trigger Supabase to send a password-reset email to the given address.

    If the repository sets the environment variable
    ``SUPABASE_PASSWORD_RESET_URL`` this value will be passed to the API as
    ``redirect_to`` so that the email link brings the user back into our
    Streamlit app instead of a generic Supabase page.

    Supabase will silently succeed even if the address is not registered, so the
    return value mostly exists to surface unexpected errors.

    Returns a dict: {data, error}
    """
    try:
        options = {}
        redirect = os.getenv("SUPABASE_PASSWORD_RESET_URL")
        if redirect:
            options["redirect_to"] = redirect
        resp = supabase.auth.reset_password_for_email(email, options)
        error = getattr(resp, "error", None) or (resp.get("error") if isinstance(resp, dict) else None)
        return {"data": resp, "error": error}
    except Exception as e:
        print(f"[auth_reset_password] Exception: {e}")
        return {"data": None, "error": str(e)}


def reset_password_with_token(access_token: str, new_password: str) -> dict:
    """Given a recovery token from the email link, set a new password.

    This function performs a direct HTTP request against the Supabase
    ``/auth/v1/user`` endpoint using the provided token as a bearer token.  It
    does **not** require the user to already have an active session in our
    client.

    Returns a dict: {data, error}.  ``data`` will contain the updated user
    object on success; ``error`` will be a string message on failure.
    """
    try:
        import httpx

        url = f"{SUPABASE_URL}/auth/v1/user"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        resp = httpx.put(url, json={"password": new_password}, headers=headers, timeout=10)
        try:
            body = resp.json()
        except Exception:
            body = None
        if resp.status_code >= 400:
            return {"data": body, "error": resp.text}
        return {"data": body, "error": None}
    except Exception as e:
        print(f"[reset_password_with_token] Exception: {e}")
        return {"data": None, "error": str(e)}


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
    """Upsert jobs on the url column, ignoring conflicts.

    The list coming from ``search_all_jobs`` may contain transient fields such as
    ``tier_label`` and ``tier`` that are not columns in the database.  Postgres
    would raise an error if unknown columns are provided, so we strip them here.
    """
    try:
        if not jobs:
            return []
        # drop any keys not present in the jobs table schema
        sanitized = []
        for job in jobs:
            if isinstance(job, dict):
                sanitized.append({
                    k: v
                    for k, v in job.items()
                    if k not in ("tier_label", "tier")
                })
            else:
                sanitized.append(job)
        response = (
            supabase.table("jobs")
            .upsert(sanitized, on_conflict="url")
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