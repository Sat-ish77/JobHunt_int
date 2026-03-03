"""
Career coach agent — persistent memory, profile extraction, GPT-4o.
Specifically designed for international students on F-1/OPT visas.
"""

import json
import os
from dotenv import load_dotenv
from openai import OpenAI

from database.supabase_client import (
    get_conversation_history,
    get_student_profile,
    save_message,
    update_student_profile,
)

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are a career coach specifically for international students \
on F-1/OPT visas studying in the United States.

You have full memory of all past conversations with this student.
You know their university, major, visa status, graduation date,
OPT timeline, target roles, courses, and career goals.

STRICT IMMIGRATION RULE — non-negotiable:
If the user asks anything about visa rules, OPT deadlines, \
cap-gap periods, H1B process, grace periods, CPT eligibility, \
or any immigration law — you must respond with:
"I'm not certain about the specifics of this — please verify \
with your DSO (Designated School Official) or check uscis.gov \
for accurate information."
Never guess on immigration topics. You are a coach, not a lawyer.

For everything else: be direct, practical, specific, encouraging.
Give real actionable advice based on what you know about the student."""


def extract_profile_from_message(user_message: str) -> dict:
    """
    Use GPT-4o-mini to extract any student profile fields
    explicitly mentioned in the user's message.
    Returns a dict of fields that were clearly stated.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract student profile fields explicitly stated in "
                        "this message. Return JSON with only fields that are "
                        "clearly mentioned.\n"
                        "Fields: university, major, degree_level, graduation_date, "
                        "gpa, visa_type, opt_start_date, opt_end_date, "
                        "stem_opt_eligible, country_of_origin, "
                        "target_roles (list), target_locations (list).\n"
                        "If nothing profile-related is mentioned return "
                        "empty dict {}.\n"
                        "Never infer or guess. Only extract explicitly stated "
                        "information."
                    ),
                },
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=500,
        )
        content = response.choices[0].message.content.strip()
        extracted = json.loads(content)
        # Remove empty values
        return {k: v for k, v in extracted.items() if v}
    except Exception as e:
        print(f"[extract_profile_from_message] Error: {e}")
        return {}


def chat_with_coach(user_message: str, resume_context: str = "") -> str:
    """
    Main career coach chat function.
    1. Loads student profile and conversation history.
    2. Extracts profile updates from the message.
    3. Builds context-rich message list.
    4. Calls GPT-4o at temperature=0.3.
    5. Saves both user and assistant messages.
    """
    try:
        # 1. Load profile and history
        profile = get_student_profile()
        history = get_conversation_history(limit=30)

        # 2. Extract and save any profile updates
        extracted = extract_profile_from_message(user_message)
        if extracted:
            try:
                update_student_profile(extracted)
            except Exception as e:
                print(f"[chat_with_coach] Profile update error: {e}")

        # 3. Build messages list
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

        # Add profile context
        if profile:
            profile_str = json.dumps(profile, default=str, indent=2)
            messages.append({
                "role": "system",
                "content": f"Student profile:\n{profile_str}",
            })

        # Add resume context if provided
        if resume_context:
            messages.append({
                "role": "system",
                "content": f"Student's resume:\n{resume_context[:2000]}",
            })

        # Add conversation history
        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message,
        })

        # 4. Call GPT-4o
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.3,
            max_tokens=1500,
        )
        assistant_reply = response.choices[0].message.content.strip()

        # 5. Save messages to conversation history
        save_message("user", user_message)
        save_message("assistant", assistant_reply)

        return assistant_reply

    except Exception as e:
        print(f"[chat_with_coach] Error: {e}")
        raise

