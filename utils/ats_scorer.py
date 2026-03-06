"""
ATS Scorer — fully GPT-powered, works for any role and any industry.

GPT-4o-mini acts as an expert ATS analyst:
  - Understands any role (tech, non-tech, construction, finance, healthcare, etc.)
  - Scores resume against job description with industry-specific weighting
  - Identifies matched and missing skills with context
  - Provides specific improvement tips per resume + job combo

Cost: ~$0.003–0.005 per full score call (gpt-4o-mini)
"""

import os
import re
import json
from collections import Counter
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ══════════════════════════════════════════════════════════
# SYSTEM PROMPT — tells GPT exactly how to score
# ══════════════════════════════════════════════════════════

_SCORING_SYSTEM_PROMPT = """You are an expert ATS (Applicant Tracking System) analyst
and resume coach with deep knowledge across ALL industries — tech, construction,
finance, healthcare, education, business, engineering, and more.

Your job is to score a resume against a job description and provide actionable feedback.

SCORING RULES — follow these exactly:
1. First identify the industry and role from the job description
2. Score based on what ACTUALLY MATTERS for that specific role — not generic criteria
   - Tech role: weight programming languages, frameworks, tools heavily
   - Construction: weight certifications (PMP, OSHA), software (AutoCAD, Procore), field experience
   - Finance: weight certifications (CFA, CPA), Excel, financial modeling, regulations
   - Healthcare: weight licenses, clinical skills, EHR systems, compliance
   - Business/Management: weight leadership, stakeholder management, domain expertise
3. Weight: technical/hard skills 60%, experience relevance 25%, soft skills 15%
4. Required skills that are completely missing = heavy penalty
5. Partial matches (similar tool, related experience) = 50% credit
6. Be honest — do not inflate scores
   - 80-100: Strong match, should pass ATS
   - 60-79:  Decent match, some gaps
   - 40-59:  Moderate match, significant gaps
   - 0-39:   Weak match, major gaps

TIPS RULES — each tip must:
- Reference actual content from THIS resume (not generic advice)
- Be actionable — exactly what to add, reword, or remove
- Be industry-aware
- Start with: 🔴 (must-fix), 🟡 (should-fix), or 💡 (quick-win)
- Never mention visa status, immigration, or sponsorship

OUTPUT: Return ONLY valid JSON with no markdown, no explanation outside the JSON:
{
  "score": <int 0-100>,
  "role_detected": "<job title/role>",
  "industry": "<industry>",
  "score_breakdown": {
    "technical_skills": <int 0-60>,
    "experience_relevance": <int 0-25>,
    "soft_skills": <int 0-15>
  },
  "matched_keywords": [<up to 15 matching skills/keywords>],
  "missing_required": [<must-have skills completely missing>],
  "missing_preferred": [<nice-to-have skills missing>],
  "important_missing": [<top 10 most impactful missing — required first>],
  "rule_tips": [
    "<tip 1 — specific to this resume and job>",
    "<tip 2>",
    "<tip 3>",
    "<tip 4>",
    "<tip 5>"
  ],
  "strengths": [<2-3 specific things the resume does well for this role>],
  "summary": "<2 honest sentences summarizing the match>"
}"""


# ══════════════════════════════════════════════════════════
# MAIN SCORER
# ══════════════════════════════════════════════════════════

def score_resume_against_job(
    resume_text: str,
    job_description: str,
    job_title: str = "",
    use_gpt: bool = True,
) -> dict:
    """
    Score a resume against a job description.
    Works for ANY role and industry — tech, construction, finance, healthcare, etc.

    Args:
        resume_text:     Plain text of the resume
        job_description: Full job description text
        job_title:       Optional — helps GPT detect role faster
        use_gpt:         False = instant keyword fallback (no API call)

    Returns:
        score             int 0-100
        role_detected     str
        industry          str
        score_breakdown   dict {technical_skills, experience_relevance, soft_skills}
        matched_keywords  list
        missing_required  list
        missing_preferred list
        important_missing list  ← backward compat with existing app.py
        rule_tips         list of actionable improvement tips
        strengths         list
        summary           str
        gpt_tips          str (empty — tips already in rule_tips)
    """
    if not job_description or not resume_text:
        return _empty_result()

    if not use_gpt:
        return _basic_keyword_score(resume_text, job_description)

    try:
        user_prompt = f"""Score this resume against the job description.

JOB TITLE: {job_title or "See job description"}

JOB DESCRIPTION:
{job_description[:3000]}

---

RESUME:
{resume_text[:3000]}"""

        response = _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SCORING_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=1200,
        )

        raw = response.choices[0].message.content.strip()
        result = json.loads(raw)

        return {
            "score":             int(result.get("score", 0)),
            "role_detected":     result.get("role_detected", "Unknown"),
            "industry":          result.get("industry", "Unknown"),
            "score_breakdown":   result.get("score_breakdown", {}),
            "matched_keywords":  result.get("matched_keywords", []),
            "missing_required":  result.get("missing_required", []),
            "missing_preferred": result.get("missing_preferred", []),
            "important_missing": result.get("important_missing", []),
            "rule_tips":         result.get("rule_tips", []),
            "strengths":         result.get("strengths", []),
            "summary":           result.get("summary", ""),
            "gpt_tips":          "",
        }

    except json.JSONDecodeError as e:
        print(f"[score_resume_against_job] JSON parse error: {e}")
        return _basic_keyword_score(resume_text, job_description)
    except Exception as e:
        print(f"[score_resume_against_job] Error: {e}")
        return _basic_keyword_score(resume_text, job_description)


# ══════════════════════════════════════════════════════════
# DEEP IMPROVEMENT TIPS — separate call, on-demand only
# ══════════════════════════════════════════════════════════

def get_gpt_improvement_tips(
    resume_text: str,
    job_description: str,
    score: int,
    missing_required: list,
    role_detected: str = "",
    industry: str = "",
) -> str:
    """
    Deeper narrative improvement advice — called only when user
    explicitly requests it (e.g. 'Analyze My Resume' button).
    Separate from scoring to keep bulk job scoring fast.
    Cost: ~$0.002 per call.
    """
    try:
        missing_str = ", ".join(missing_required[:8]) if missing_required else "none"
        role_ctx = f"{role_detected} in the {industry} industry" if role_detected else "this role"

        prompt = f"""You are an expert resume coach for {role_ctx}.

ATS Score: {score}/100
Top missing required skills: {missing_str}

Give a structured improvement plan:

**What's Working** (2 specific strengths from the actual resume)

**Must Fix Now** (2-3 critical gaps — suggest exact wording or changes)

**Quick Wins** (2-3 small changes that immediately boost the score)

Rules:
- Reference specific sections or lines from the resume
- Be industry-aware for {industry or "this field"}
- Never mention visa, immigration, or sponsorship
- Under 250 words total

Job Description:
{job_description[:1200]}

Resume:
{resume_text[:2000]}"""

        response = _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"You are a concise expert resume coach. Specific and actionable advice only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[get_gpt_improvement_tips] Error: {e}")
        return ""


# ══════════════════════════════════════════════════════════
# FALLBACK — basic keyword scorer (no API, used if GPT fails)
# ══════════════════════════════════════════════════════════

_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "will", "you", "our",
    "are", "have", "has", "from", "your", "their", "about", "work",
    "team", "role", "position", "company", "experience", "they", "also",
    "who", "what", "when", "where", "which", "able", "been", "into",
    "more", "must", "well", "use", "using", "used", "good", "strong",
}


def _extract_keywords(text: str) -> set:
    clean = re.sub(r"<[^>]+>", " ", text)
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#\-\.]{2,}", clean.lower())
    return {w for w in words if w not in _STOPWORDS}


def _basic_keyword_score(resume_text: str, job_description: str) -> dict:
    """Pure keyword fallback — used when GPT is unavailable."""
    resume_kw = _extract_keywords(resume_text)
    job_kw = _extract_keywords(job_description)

    if not job_kw:
        return _empty_result()

    matched = resume_kw & job_kw
    missing = job_kw - resume_kw

    word_freq = Counter(re.findall(r"[a-zA-Z]{3,}", job_description.lower()))
    missing_sorted = sorted(missing, key=lambda w: word_freq.get(w, 0), reverse=True)
    matched_sorted = sorted(matched, key=lambda w: word_freq.get(w, 0), reverse=True)
    score = round(min(len(matched) / len(job_kw) * 100, 100))

    return {
        "score":             score,
        "role_detected":     "Unknown (fallback mode)",
        "industry":          "Unknown",
        "score_breakdown":   {},
        "matched_keywords":  matched_sorted[:20],
        "missing_required":  missing_sorted[:10],
        "missing_preferred": [],
        "important_missing": missing_sorted[:15],
        "rule_tips": [
            "⚠️ AI scoring unavailable — showing basic keyword match only.",
            "💡 Try again for full industry-specific scoring and tips.",
        ],
        "strengths":  [],
        "summary":    f"Basic keyword match: {score}%. AI analysis unavailable.",
        "gpt_tips":   "",
    }


def _empty_result() -> dict:
    return {
        "score":             0,
        "role_detected":     "Unknown",
        "industry":          "Unknown",
        "score_breakdown":   {},
        "matched_keywords":  [],
        "missing_required":  [],
        "missing_preferred": [],
        "important_missing": [],
        "rule_tips":         [],
        "strengths":         [],
        "summary":           "",
        "gpt_tips":          "",
    }