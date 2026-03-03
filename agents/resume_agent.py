"""
Resume agent — generates cover letters and rewrites resumes using GPT-4o.
Tailored for international students on F-1/OPT visas.
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_cover_letter(
    resume: str,
    job_title: str,
    company: str,
    job_description: str,
    student_profile: dict = None,
) -> str:
    """
    Generate a tailored cover letter using GPT-4o.
    Handles visa mentions intelligently based on whether the job
    explicitly mentions sponsorship.
    """
    try:
        # Determine if job mentions sponsorship
        desc_lower = (job_description or "").lower()
        mentions_sponsorship = any(
            kw in desc_lower
            for kw in ["sponsor", "h1b", "h-1b", "visa", "work authorization"]
        )

        # Build profile context
        profile_context = ""
        if student_profile:
            profile_context = (
                f"\nStudent background: "
                f"University: {student_profile.get('university', 'N/A')}, "
                f"Major: {student_profile.get('major', 'N/A')}, "
                f"Degree: {student_profile.get('degree_level', 'N/A')}, "
                f"Graduation: {student_profile.get('graduation_date', 'N/A')}, "
                f"Visa: {student_profile.get('visa_type', 'N/A')}."
            )

        visa_instruction = ""
        if mentions_sponsorship and student_profile:
            visa_instruction = (
                "The job description mentions sponsorship/visa. "
                "You may naturally mention the student's visa status "
                "in one sentence to show awareness."
            )
        else:
            visa_instruction = (
                "The job does NOT mention sponsorship or visa. "
                "Do NOT mention visa status, immigration, or sponsorship "
                "at all in the cover letter."
            )

        system_prompt = f"""You write cover letters for international students applying to US jobs.

Rules:
- Under 350 words
- Naturally include keywords from the job description for ATS optimisation
- Reference the specific company name "{company}" and role "{job_title}"
- {visa_instruction}
- Never say "I am excited to apply" or any generic opener
- Sound human, specific, not AI-generated
- Strong opening sentence that is NOT "My name is..."
- End with a clear call to action
- Be concise and impactful{profile_context}"""

        user_prompt = f"""Write a cover letter for this application:

Job Title: {job_title}
Company: {company}
Job Description:
{job_description[:2500]}

Candidate's Resume:
{resume[:2500]}"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=1000,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"[generate_cover_letter] Error: {e}")
        raise


def rewrite_resume_for_job(
    resume: str,
    job_description: str,
    missing_keywords: list,
    student_profile: dict = None,
) -> str:
    """
    Rewrite/optimise a resume for a specific job using GPT-4o.
    Weaves in missing keywords while keeping all facts truthful.
    """
    try:
        profile_context = ""
        if student_profile:
            profile_context = (
                f"\nStudent background: "
                f"Degree: {student_profile.get('degree_level', 'N/A')} "
                f"in {student_profile.get('major', 'N/A')} "
                f"from {student_profile.get('university', 'N/A')}."
            )

        keywords_str = ", ".join(missing_keywords[:15]) if missing_keywords else "none"

        system_prompt = f"""You optimise resumes for ATS (Applicant Tracking Systems) and human readers.

Rules:
- Keep ALL facts truthful — only reword, reorder, and strengthen
- Weave these missing keywords naturally where they honestly apply: {keywords_str}
- Use strong action verbs (built, designed, led, reduced, improved, developed, implemented)
- Quantify achievements where possible (numbers, percentages, metrics)
- Return ONLY the rewritten resume text, no commentary or explanation
- Do NOT invent skills or experience that are not in the original
- Maintain professional formatting with clear sections{profile_context}"""

        user_prompt = f"""Optimise this resume for the following job:

Job Description:
{job_description[:2500]}

Original Resume:
{resume[:3000]}"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
            max_tokens=2000,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"[rewrite_resume_for_job] Error: {e}")
        raise

