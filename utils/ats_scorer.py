"""
ATS (Applicant Tracking System) scorer.
Extracts keywords and scores resume against job descriptions.
"""

import re
from collections import Counter

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "will",
    "you", "our", "are", "have", "has", "from", "your",
    "their", "about", "work", "team", "role", "position",
    "company", "experience", "they", "also", "who", "what",
    "when", "where", "which", "able", "been", "into", "more",
}


def extract_keywords(text: str) -> set:
    """
    Extract meaningful keywords from text.
    Strips HTML, extracts 3+ char words, removes stopwords.
    Returns a set of lowercase keywords.
    """
    try:
        # Strip HTML tags
        clean = re.sub(r"<[^>]+>", " ", text)
        # Extract all words 3+ chars
        words = re.findall(r"[a-zA-Z]{3,}", clean.lower())
        # Remove stopwords
        keywords = {w for w in words if w not in STOPWORDS}
        return keywords
    except Exception as e:
        print(f"[extract_keywords] Error: {e}")
        return set()


def score_resume_against_job(resume_text: str,
                              job_description: str) -> dict:
    """
    Score a resume against a job description.
    Returns score (0-100), matched keywords, and important missing keywords.
    """
    try:
        resume_keywords = extract_keywords(resume_text)
        job_keywords = extract_keywords(job_description)

        if not job_keywords:
            return {
                "score": 0,
                "matched_keywords": [],
                "important_missing": [],
            }

        matched = resume_keywords & job_keywords
        missing = job_keywords - resume_keywords

        # Count word frequency in job description to rank importance
        clean_desc = re.sub(r"<[^>]+>", " ", job_description.lower())
        all_words = re.findall(r"[a-zA-Z]{3,}", clean_desc)
        word_freq = Counter(all_words)

        # Sort missing by frequency in job description (most important first)
        missing_sorted = sorted(
            missing,
            key=lambda w: word_freq.get(w, 0),
            reverse=True,
        )
        important_missing = missing_sorted[:15]

        # Score
        score = round(len(matched) / len(job_keywords) * 100)
        score = min(score, 100)

        # Top matched keywords
        matched_sorted = sorted(
            matched,
            key=lambda w: word_freq.get(w, 0),
            reverse=True,
        )

        return {
            "score": score,
            "matched_keywords": matched_sorted[:20],
            "important_missing": important_missing,
        }

    except Exception as e:
        print(f"[score_resume_against_job] Error: {e}")
        return {
            "score": 0,
            "matched_keywords": [],
            "important_missing": [],
        }

