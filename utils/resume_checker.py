"""
Resume checker — formatting, structure, and content quality analysis.
Used in Tab 2 of app.py for the "Check My Resume" button.
Rule-based checks run instantly; GPT provides deeper content feedback.
"""

import os
import re
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ── Section detection ──────────────────────────────────────

EXPECTED_SECTIONS = {
    "contact":    ["email", "phone", "linkedin", "github", "@"],
    "education":  ["education", "university", "college", "degree", "gpa", "bachelor", "master"],
    "experience": ["experience", "work experience", "employment", "internship", "intern"],
    "projects":   ["project", "projects", "personal project"],
    "skills":     ["skills", "technical skills", "technologies", "tools", "languages"],
}

OPTIONAL_SECTIONS = {
    "summary":        ["summary", "objective", "profile", "about"],
    "certifications": ["certification", "certifications", "certificate", "license"],
    "awards":         ["award", "honor", "achievement", "scholarship"],
}

ATS_BREAKING_PATTERNS = [
    # Tables indicated by tab-heavy alignment
    (r"\t{3,}", "Possible table formatting detected — ATS parsers can't read tables."),
    # Graphics placeholder text
    (r"\[image\]|\[photo\]|\[logo\]", "Images or logos detected — ATS ignores them."),
    # Multiple columns (heuristic: very short lines alternating with long ones)
]

WEAK_OPENERS = [
    "responsible for", "helped with", "assisted in", "worked on",
    "duties included", "was involved", "participated in",
]

STRONG_VERBS = [
    "built", "designed", "led", "reduced", "improved", "developed",
    "implemented", "launched", "automated", "optimized", "deployed",
    "created", "managed", "delivered", "scaled", "migrated",
    "analyzed", "trained", "architected", "streamlined",
]


# ── Rule-based checks ──────────────────────────────────────

def check_resume_formatting(resume_text: str) -> dict:
    """
    Run all rule-based checks on resume text.
    Returns a structured report with issues and suggestions.
    """
    issues = []
    warnings = []
    suggestions = []
    score = 100  # start at 100, deduct for issues

    lines = resume_text.split("\n")
    text_lower = resume_text.lower()

    # ── Section checks ────────────────────────────────────
    found_sections = []
    missing_sections = []

    for section, keywords in EXPECTED_SECTIONS.items():
        if any(kw in text_lower for kw in keywords):
            found_sections.append(section)
        else:
            missing_sections.append(section)

    if missing_sections:
        for s in missing_sections:
            issues.append(f"❌ Missing section: **{s.title()}** — ATS and recruiters expect this section.")
            score -= 10

    # Optional but helpful sections
    for section, keywords in OPTIONAL_SECTIONS.items():
        if any(kw in text_lower for kw in keywords):
            found_sections.append(section)
        else:
            if section == "summary":
                suggestions.append(
                    "💡 Consider adding a 2-3 line **Professional Summary** "
                    "at the top targeting your desired role. It helps ATS classify your application."
                )

    # ── Contact info ───────────────────────────────────────
    has_email = bool(re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", resume_text))
    has_phone = bool(re.search(r"\(?\d{3}\)?[\s\-\.]\d{3}[\s\-\.]\d{4}", resume_text))
    has_linkedin = "linkedin" in text_lower
    has_github = "github" in text_lower

    if not has_email:
        issues.append("❌ No email address found.")
        score -= 15
    if not has_phone:
        warnings.append("⚠️ No phone number found.")
        score -= 5
    if not has_linkedin:
        suggestions.append("💡 Add your LinkedIn URL — recruiters check it.")
    if not has_github:
        suggestions.append("💡 Add your GitHub URL — important for CS/engineering roles.")

    # ── Quantification ─────────────────────────────────────
    number_matches = re.findall(r"\d+[%x+]?|\$\d+|\d{4,}", resume_text)
    # Filter out just years
    metrics = [n for n in number_matches if not re.match(r"^(19|20)\d{2}$", n)]
    if len(metrics) < 3:
        warnings.append(
            "⚠️ **Low quantification** — only found a few numbers/metrics. "
            "Add impact numbers: '40% faster', '10K+ users', '$2M pipeline'."
        )
        score -= 10
    else:
        suggestions.append(f"✅ Good use of metrics — found {len(metrics)} quantified achievements.")

    # ── Action verbs ───────────────────────────────────────
    strong_count = sum(1 for v in STRONG_VERBS if v in text_lower)
    weak_found = [w for w in WEAK_OPENERS if w in text_lower]

    if strong_count < 4:
        warnings.append(
            "⚠️ **Weak action verbs** — replace passive phrases with strong verbs: "
            f"{', '.join(STRONG_VERBS[:6])}."
        )
        score -= 8

    if weak_found:
        issues.append(
            f"❌ **Passive language** detected: '{weak_found[0]}'. "
            "Rewrite with action verbs — they make you sound more impactful."
        )
        score -= 7

    # ── Sponsorship/visa mention ───────────────────────────
    if re.search(r"\bvisa\b|\bsponsorship\b|\bwork authorization\b|\bf-1\b|\bopt\b", text_lower):
        issues.append(
            "❌ **Remove visa/sponsorship mentions** from your resume. "
            "Never include immigration status — it eliminates you before the interview."
        )
        score -= 15

    # ── Date consistency ───────────────────────────────────
    date_formats = {
        "month_year": bool(re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}", resume_text)),
        "mm_yyyy": bool(re.search(r"\d{2}/\d{4}", resume_text)),
        "yyyy_mm": bool(re.search(r"\d{4}-\d{2}", resume_text)),
    }
    formats_used = sum(date_formats.values())
    if formats_used > 1:
        warnings.append(
            "⚠️ **Inconsistent date formats** — pick one format and use it throughout "
            "(e.g. 'Jan 2024 – May 2025')."
        )
        score -= 5

    # ── Length check ──────────────────────────────────────
    word_count = len(resume_text.split())
    non_empty_lines = [l for l in lines if l.strip()]
    if word_count < 150:
        issues.append("❌ Resume is too short — add more detail to your experience and projects.")
        score -= 10
    elif word_count > 900:
        warnings.append(
            "⚠️ Resume may be too long for a student/new grad. "
            "Aim for one page (~400-700 words)."
        )
        score -= 5

    # ── Bullet point consistency ───────────────────────────
    bullet_types = set()
    for line in non_empty_lines:
        stripped = line.strip()
        if stripped.startswith("•"):
            bullet_types.add("•")
        elif stripped.startswith("●"):
            bullet_types.add("●")
        elif stripped.startswith("-"):
            bullet_types.add("-")
        elif stripped.startswith("*"):
            bullet_types.add("*")
    if len(bullet_types) > 1:
        warnings.append(
            f"⚠️ **Mixed bullet styles** ({', '.join(bullet_types)}) — "
            "standardize to one type throughout."
        )
        score -= 3

    # ── GPA ───────────────────────────────────────────────
    has_gpa = bool(re.search(r"gpa[\s:]*\d\.\d{1,2}", text_lower))
    if not has_gpa:
        suggestions.append(
            "💡 Include your GPA if it's 3.5+ — it's a positive signal for early-career candidates."
        )

    # Clamp score
    score = max(score, 0)

    return {
        "score": score,
        "issues": issues,          # must-fix (❌)
        "warnings": warnings,      # should-fix (⚠️)
        "suggestions": suggestions, # nice-to-have (💡)
        "found_sections": found_sections,
        "word_count": word_count,
    }


# ── GPT deep content review ────────────────────────────────

def gpt_resume_review(
    resume_text: str,
    target_role: str = "",
    target_company: str = "",
) -> str:
    """
    Use GPT-4o-mini to give a deeper content review of the resume.
    Focuses on: narrative, specificity, role alignment, and impact.
    Cost: ~$0.001-0.002 per call.
    """
    try:
        role_context = f"for a {target_role} role" if target_role else "for a tech/engineering role"
        company_context = f" at {target_company}" if target_company else ""

        prompt = f"""Review this resume {role_context}{company_context} and provide specific, actionable feedback.

Structure your response as:

**What's Working Well** (2-3 points)
**Must Fix** (2-3 critical issues with specific suggestions)
**Quick Wins** (2-3 easy improvements that will boost impact)

Rules:
- Be specific — reference actual content from the resume
- Suggest exact rewording where possible
- No generic advice
- Do NOT mention visa or immigration status
- Keep total response under 300 words

Resume:
{resume_text[:3000]}"""

        response = _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a concise expert resume coach for CS/engineering students. Give specific, actionable feedback only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=700,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[gpt_resume_review] Error: {e}")
        return "AI review temporarily unavailable. Check rule-based feedback above."


# ── Combined check ─────────────────────────────────────────

def full_resume_check(
    resume_text: str,
    target_role: str = "",
    use_gpt: bool = True,
) -> dict:
    """
    Run both rule-based formatting check and optional GPT content review.
    Returns everything needed to display in the UI.
    """
    formatting = check_resume_formatting(resume_text)
    gpt_review = ""
    if use_gpt:
        gpt_review = gpt_resume_review(resume_text, target_role)

    return {
        **formatting,
        "gpt_review": gpt_review,
        "target_role": target_role,
    }