"""
JobHunt Int — Main Streamlit application.
A job hunting web app for international students on F-1/OPT visas.
"""

import re
import streamlit as st
<<<<<<< HEAD
import pycountry
=======
from datetime import datetime, date
>>>>>>> c46c5cad312b5692a09c8cef61201a82c6bf3cb1

st.set_page_config(
    page_title="JobHunt Int",
    page_icon="🌐",
    layout="wide",
)

# ── Imports ────────────────────────────────────────────────
from database.supabase_client import (
    auth_sign_in,
    auth_sign_up,
    auth_sign_out,
    set_user,
    set_session,
    clear_conversation_history,
    get_all_jobs,
    get_all_resumes,
    get_applications,
    get_conversation_history,
    get_resume_by_id,
    get_student_profile,
    save_application,
    save_jobs,
    save_resume,
    save_student_profile,
    update_application_status,
    update_cover_letter,
    update_resume_content,
    delete_resume,
)
from tools.embeddings import get_embedding
from tools.immigration_news import get_all_immigration_news
from tools.job_fetcher import search_all_jobs
from tools.resume_parser import parse_resume
from agents.career_coach import chat_with_coach
from agents.resume_agent import generate_cover_letter, rewrite_resume_for_job
from utils.ats_scorer import score_resume_against_job

# ── Helpers ────────────────────────────────────────────────
def _strip_html(text: str) -> str:
    """Remove HTML tags from text (some RSS feeds return raw HTML)."""
    return re.sub(r"<[^>]+>", "", text or "").strip()

<<<<<<< HEAD
COUNTRIES = sorted([country.name for country in pycountry.countries])
def _safe_date(value, default=None):

    """Convert saved string/ISO date into a Python date for Streamlit date_input."""
    if default is None:
        default = date.today()
    if not value:
        return default
    if isinstance(value, date):
        return value
=======

def _parse_date(date_str: str) -> date:
    """Parse date string to date object. Returns None if invalid."""
    if not date_str:
        return None
>>>>>>> c46c5cad312b5692a09c8cef61201a82c6bf3cb1
    try:
        for fmt in ["%Y-%m-%d", "%B %Y", "%B %d, %Y", "%m/%d/%Y"]:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None
    except Exception:
<<<<<<< HEAD
        return default
    

    """Remove HTML tags from text (some RSS feeds return raw HTML)."""
    return re.sub(r"<[^>]+>", "", text or "").strip()
=======
        return None


def _format_date(d) -> str:
    """Convert date object to string format."""
    if d is None:
        return ""
    if isinstance(d, str):
        return d
    return d.strftime("%Y-%m-%d")

>>>>>>> c46c5cad312b5692a09c8cef61201a82c6bf3cb1

# ── Session state init ─────────────────────────────────────
if "user" not in st.session_state:
    st.session_state["user"] = None
if "session" not in st.session_state:
    st.session_state["session"] = None
if "user_email" not in st.session_state:
    st.session_state["user_email"] = None
if "active_resume_id" not in st.session_state:
    st.session_state["active_resume_id"] = None
if "uploaded_files_processed" not in st.session_state:
    st.session_state["uploaded_files_processed"] = set()


# ── Authentication Page ────────────────────────────────────
def show_login_page():
    """Display login/signup page for unauthenticated users."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("https://cdn-icons-png.flaticon.com/512/163/163801.png", width=80)
        st.title("🌐 JobHunt Int")
        st.caption("Job Search Assistant for International Students")
        
        tab_login, tab_signup = st.tabs(["Login", "Sign Up"])
        
        # ── LOGIN TAB ──
        with tab_login:
            st.subheader("Welcome Back!")
            login_email = st.text_input(
                "Email", 
                placeholder="your@email.com",
                key="login_email"
            )
            login_password = st.text_input(
                "Password",
                type="password",
                key="login_password"
            )
            
            if st.button("🔓 Sign In", use_container_width=True):
                if not login_email or not login_password:
                    st.error("Please enter email and password.")
                else:
                    with st.spinner("Signing in..."):
                        result = auth_sign_in(login_email, login_password)
                        if result.get("needs_confirmation"):
                            st.warning(
                                f"📧 Your email ({login_email}) hasn't been confirmed yet. "
                                f"Check your inbox for a confirmation link and verify your email, then try logging in again."
                            )
                        elif result["error"]:
                            st.error(f"Login failed: {result['error']}")
                        elif result["user"] and result["session"]:
                            st.session_state["user"] = result["user"]
                            st.session_state["session"] = result["session"]
                            st.session_state["user_email"] = login_email
                            user_id = result["user"].id if hasattr(result["user"], "id") else login_email
                            set_user(user_id)
                            # ── SET SESSION so RLS auth.uid() works ──
                            set_session(
                                result["session"].access_token,
                                result["session"].refresh_token,
                            )
                            st.success("✅ Signed in! Refreshing...")
                            st.rerun()
                        else:
                            st.error("Sign in failed. Please check your email and password.")
        
        # ── SIGNUP TAB ──
        with tab_signup:
            st.subheader("Create Your Account")
            signup_email = st.text_input(
                "Email",
                placeholder="your@email.com",
                key="signup_email"
            )
            signup_password = st.text_input(
                "Password (min 6 characters)",
                type="password",
                key="signup_password"
            )
            signup_password_confirm = st.text_input(
                "Confirm Password",
                type="password",
                key="signup_password_confirm"
            )
            
            if st.button("✍️ Create Account", use_container_width=True):
                if not signup_email:
                    st.error("Please enter an email.")
                elif signup_password != signup_password_confirm:
                    st.error("Passwords do not match.")
                elif len(signup_password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    with st.spinner("Creating account..."):
                        result = auth_sign_up(signup_email, signup_password)
                        if result.get("needs_confirmation"):
                            st.success(
                                f"✅ Account created! Check your email ({signup_email}) for a confirmation link. "
                                f"Click the link to verify your email, then you can log in."
                            )
                        elif result["error"]:
                            st.error(f"Sign up failed: {result['error']}")
                        elif result["user"]:
                            if result["session"]:
                                st.success("✅ Account created and signed in! Redirecting...")
                                st.session_state["user"] = result["user"]
                                st.session_state["session"] = result["session"]
                                st.session_state["user_email"] = signup_email
                                user_id = result["user"].id if hasattr(result["user"], "id") else signup_email
                                set_user(user_id)
                                # ── SET SESSION so RLS auth.uid() works ──
                                set_session(
                                    result["session"].access_token,
                                    result["session"].refresh_token,
                                )
                                st.rerun()
                            else:
                                st.success(
                                    f"✅ Account created! Check your email ({signup_email}) for a confirmation link, "
                                    f"then log in on the Login tab."
                                )
                        else:
                            st.error("Sign up failed. Please try again.")
        
        st.divider()
        st.caption(
            "🔒 All data is secured with Supabase authentication. "
            "For immigration decisions, consult your DSO or a licensed immigration attorney."
        )


if st.session_state["user"] is None:
    show_login_page()
    st.stop()

# ════════════════════════════════════════════════════════════
# USER LOGGED IN — Show main app below
# ════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════
# SIDEBAR — visible on every tab
# ════════════════════════════════════════════════════════════

st.sidebar.title("🌐 JobHunt Int")
st.sidebar.caption("Built for International Students")

if st.sidebar.button("🚪 Sign Out", use_container_width=True):
    auth_sign_out()
    st.session_state["user"] = None
    st.session_state["session"] = None
    st.session_state["user_email"] = None
    st.session_state["active_resume_id"] = None
    st.success("Signed out! Redirecting...")
    st.rerun()

st.sidebar.divider()
st.sidebar.caption(f"👤 Logged in as: {st.session_state.get('user_email', 'Unknown')}")
st.sidebar.divider()

st.sidebar.warning(
    "⚠️ For immigration decisions, always consult your DSO "
    "or a licensed immigration attorney. This is not legal advice."
)

st.sidebar.subheader("📰 Immigration News")
st.sidebar.caption("Official sources only")

with st.sidebar:
    with st.spinner("Loading news..."):
        news = get_all_immigration_news()

    SOURCE_COLORS = {
        "USCIS": "🔵",
        "DHS": "🔴",
        "NAFSA": "🟢",
        "Federal Register": "🟠",
    }

    for article in news[:6]:
        icon = SOURCE_COLORS.get(article.get("source", ""), "⚪")
        st.markdown(f"**{icon} {article.get('source', 'Unknown')}**")
        title = _strip_html(article.get("title", ""))
        if not title:
            continue
        if len(title) > 80:
            title = title[:80] + "..."
        st.markdown(f"_{title}_")
        summary = _strip_html(article.get("summary", ""))
        if summary:
            st.caption(summary[:120])
        url = article.get("url", "")
        if url:
            st.link_button("Read →", url)
        st.divider()

# ════════════════════════════════════════════════════════════
# MAIN TABS
# ════════════════════════════════════════════════════════════

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "👤 Profile",
    "📄 Resumes",
    "🔍 Job Search",
    "📬 Applications",
    "🤖 Career Coach",
])

# ════════════════════════════════════════════════════════════
# TAB 1 — Profile
# ════════════════════════════════════════════════════════════

with tab1:
    profile = get_student_profile()

<<<<<<< HEAD
    # ✅ Step 1: Put all inputs inside a form (smoother UX)
    with st.form("profile_form"):

        # ── Personal Information ───────────────────────────────
        st.subheader("Personal Information")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            name = st.text_input(
                "Full Name",
                value=profile.get("name", ""),
                placeholder="Sat Adhikari",
            )
        with col_p2:
            email = st.text_input(
                "Email",
                value=profile.get("email", ""),
                placeholder="sat@gmail.com",
            )

        # ── Academic Information ───────────────────────────────
        st.subheader("Academic Information")
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            university = st.text_input(
                "University",
                value=profile.get("university", ""),
            )
        with col_a2:
            major = st.text_input(
                "Major",
                value=profile.get("major", ""),
            )

        col_a3, col_a4, col_a5 = st.columns(3)
        with col_a3:
            degree_level = st.selectbox(
                "Degree Level",
                ["BS", "MS", "PhD", "Other"],
                index=(
                    ["BS", "MS", "PhD", "Other"].index(profile.get("degree_level"))
                    if profile.get("degree_level") in ["BS", "MS", "PhD", "Other"]
                    else 0
                ),
            )
        with col_a4:
            graduation_date = st.date_input(
                "Graduation Date",
                value=_safe_date(profile.get("graduation_date", "")),
            )
        with col_a5:
            gpa = st.text_input(
                "GPA",
                value=profile.get("gpa", ""),
            )

        # ── Visa & Immigration ─────────────────────────────────
        st.subheader("Visa & Immigration")
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            visa_options = ["F-1", "J-1", "OPT", "STEM OPT", "Other"]
            visa_type = st.selectbox(
                "Visa Type",
                visa_options,
                index=(
                    visa_options.index(profile.get("visa_type"))
                    if profile.get("visa_type") in visa_options
                    else 0
                ),
            )
        with col_v2:
            saved_country = profile.get("country_of_origin", "United States")

            country_of_origin = st.selectbox(
            "Country of Origin",
        COUNTRIES,
        index=COUNTRIES.index(saved_country) if saved_country in COUNTRIES else COUNTRIES.index("United States"),
        )
            

        col_v3, col_v4 = st.columns(2)
        with col_v3:
            opt_start_date = st.date_input(
                "OPT Start Date",
                value=_safe_date(profile.get("opt_start_date", "")),
            )
        with col_v4:
            opt_end_date = st.date_input(
                "OPT End Date",
                value=_safe_date(profile.get("opt_end_date", "")),
            )

        stem_opt_eligible = st.checkbox(
            "STEM OPT Eligible",
            value=bool(profile.get("stem_opt_eligible", False)),
=======
    st.subheader("Personal Information")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        name = st.text_input(
            "Full Name",
            value=profile.get("name", "") if profile else "",
            placeholder="Sat Adhikari",
        )
    with col_p2:
        email = st.text_input(
            "Email",
            value=profile.get("email", "") if profile else "",
            placeholder="sat@gmail.com",
>>>>>>> c46c5cad312b5692a09c8cef61201a82c6bf3cb1
        )

    st.subheader("Academic Information")
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        university = st.text_input(
            "University",
            value=profile.get("university", "") if profile else "",
        )
    with col_a2:
        major = st.text_input(
            "Major",
            value=profile.get("major", "") if profile else "",
        )

    col_a3, col_a4, col_a5 = st.columns(3)
    with col_a3:
        degree_level = st.selectbox(
            "Degree Level",
            ["BS", "MS", "PhD", "Other"],
            index=(
                ["BS", "MS", "PhD", "Other"].index(profile["degree_level"])
                if profile and profile.get("degree_level") in ["BS", "MS", "PhD", "Other"]
                else 0
            ),
        )
    with col_a4:
        grad_date_val = profile.get("graduation_date", "") if profile else ""
        grad_date_parsed = _parse_date(grad_date_val) if grad_date_val else None
        graduation_date_obj = st.date_input(
            "Graduation Date",
            value=grad_date_parsed,
            format="YYYY-MM-DD",
        )
        graduation_date = _format_date(graduation_date_obj)
    with col_a5:
        gpa = st.text_input(
            "GPA",
            value=profile.get("gpa", "") if profile else "",
        )

    st.subheader("Visa & Immigration")
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        visa_options = ["F-1", "J-1", "OPT", "STEM OPT", "Other"]
        visa_type = st.selectbox(
            "Visa Type",
            visa_options,
            index=(
                visa_options.index(profile["visa_type"])
                if profile and profile.get("visa_type") in visa_options
                else 0
            ),
        )
    with col_v2:
        country_of_origin = st.text_input(
            "Country of Origin",
            value=profile.get("country_of_origin", "") if profile else "",
        )

    col_v3, col_v4 = st.columns(2)
    with col_v3:
        opt_start_val = profile.get("opt_start_date", "") if profile else ""
        opt_start_parsed = _parse_date(opt_start_val) if opt_start_val else None
        opt_start_obj = st.date_input(
            "OPT Start Date",
            value=opt_start_parsed,
            format="YYYY-MM-DD",
        )
        opt_start_date = _format_date(opt_start_obj)
    with col_v4:
        opt_end_val = profile.get("opt_end_date", "") if profile else ""
        opt_end_parsed = _parse_date(opt_end_val) if opt_end_val else None
        opt_end_obj = st.date_input(
            "OPT End Date",
            value=opt_end_parsed,
            format="YYYY-MM-DD",
        )
        opt_end_date = _format_date(opt_end_obj)

    stem_opt_eligible = st.checkbox(
        "STEM OPT Eligible",
        value=profile.get("stem_opt_eligible", False) if profile else False,
    )
    stem_opt_end_date = ""
    if stem_opt_eligible:
        stem_opt_end_val = profile.get("stem_opt_end_date", "") if profile else ""
        stem_opt_end_parsed = _parse_date(stem_opt_end_val) if stem_opt_end_val else None
        stem_opt_end_obj = st.date_input(
            "STEM OPT End Date",
            value=stem_opt_end_parsed,
            format="YYYY-MM-DD",
        )
        stem_opt_end_date = _format_date(stem_opt_end_obj)

    st.subheader("Career Preferences")
    target_roles_str = st.text_input(
        "Target Roles",
        value=(
            ", ".join(profile.get("target_roles", []))
            if profile and profile.get("target_roles")
            else ""
        ),
        placeholder="Data Engineer, ML Engineer",
    )
    st.caption("Comma separated")

    target_locations_str = st.text_input(
        "Target Locations",
        value=(
            ", ".join(profile.get("target_locations", []))
            if profile and profile.get("target_locations")
            else ""
        ),
        placeholder="Dallas TX, Austin TX, Remote",
    )
    st.caption("Comma separated")

    open_to_remote = st.checkbox(
        "Open to Remote",
        value=profile.get("open_to_remote", True) if profile else True,
    )
    requires_sponsorship = st.checkbox(
        "Requires Sponsorship",
        value=profile.get("requires_sponsorship", True) if profile else True,
    )

    if st.button("💾 Save Profile"):
        with st.spinner("Saving profile..."):
            target_roles = [r.strip() for r in target_roles_str.split(",") if r.strip()]
            target_locations = [l.strip() for l in target_locations_str.split(",") if l.strip()]
            profile_data = {
                "name": name,
                "email": email,
                "university": university,
                "major": major,
                "degree_level": degree_level,
                "graduation_date": graduation_date,
                "gpa": gpa,
                "visa_type": visa_type,
                "opt_start_date": opt_start_date,
                "opt_end_date": opt_end_date,
                "stem_opt_eligible": stem_opt_eligible,
                "stem_opt_end_date": stem_opt_end_date,
                "country_of_origin": country_of_origin,
                "target_roles": target_roles,
                "target_locations": target_locations,
                "open_to_remote": open_to_remote,
                "requires_sponsorship": requires_sponsorship,
            }
            try:
                save_student_profile(profile_data)
                st.success("✅ Profile saved!")
            except Exception as e:
                st.error(f"Error saving profile: {e}")

    if profile:
        st.caption(f"Last updated: {profile.get('updated_at', 'N/A')}")

# ════════════════════════════════════════════════════════════
# TAB 2 — Resumes
# ════════════════════════════════════════════════════════════

with tab2:
    st.subheader("Your Resumes")

    uploaded_files = st.file_uploader(
        "Upload PDF or DOCX",
        type=["pdf", "docx"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        for file in uploaded_files:
            if file.name not in st.session_state["uploaded_files_processed"]:
                with st.spinner(f"Processing {file.name}..."):
                    try:
                        content = parse_resume(file)
                        embedding = get_embedding(content)
                        save_resume(file.name, content, embedding)
                        st.session_state["uploaded_files_processed"].add(file.name)
                        st.success(f"✅ Saved: {file.name}")
                    except ValueError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Error processing {file.name}: {e}")

    resumes = get_all_resumes()

    if not resumes:
        st.info("Upload a resume above to get started.")
    else:
        st.subheader("Select Active Resume")
        resume_names = [r["name"] for r in resumes]
        resume_ids = [r["id"] for r in resumes]

        active_index = 0
        if st.session_state.get("active_resume_id") in resume_ids:
            active_index = resume_ids.index(st.session_state["active_resume_id"])

        selected = st.radio(
            "Active resume for job matching and applications:",
            resume_names,
            index=active_index,
        )
        st.session_state["active_resume_id"] = resume_ids[resume_names.index(selected)]

        st.divider()
        st.subheader("Manage Resumes")

        for resume in resumes:
            with st.expander(f"📋 {resume['name']}"):
                edited = st.text_area(
                    "Content",
                    value=resume["content"],
                    height=300,
                    key=f"edit_{resume['id']}",
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Save Changes", key=f"save_{resume['id']}"):
                        with st.spinner("Saving..."):
                            try:
                                update_resume_content(resume["id"], edited)
                                st.success("Saved!")
                            except Exception as e:
                                st.error(f"Error: {e}")
                with col2:
                    if st.button("🗑️ Delete", key=f"del_{resume['id']}"):
                        try:
                            delete_resume(resume["id"])
                            if st.session_state.get("active_resume_id") == resume["id"]:
                                st.session_state["active_resume_id"] = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

        # ── Resume Health Check ────────────────────────────
        st.divider()
        st.subheader("🔍 Resume Health Check")
        st.caption("Formatting analysis + AI content review")

        from utils.resume_checker import full_resume_check

        checker_resume = st.selectbox(
            "Select resume to check",
            [r["name"] for r in resumes],
            key="checker_resume_select",
        )
        checker_matched = next((r for r in resumes if r["name"] == checker_resume), None)

        target_role_input = st.text_input(
            "Target role (optional)",
            placeholder="Data Engineer, ML Engineer, Construction Manager...",
            key="checker_target_role",
        )

        col_check1, col_check2 = st.columns(2)
        with col_check1:
            run_check = st.button("🔍 Run Check", key="run_resume_check")

        if run_check and checker_matched:
            with st.spinner("Analyzing resume..."):
                result = full_resume_check(
                    resume_text=checker_matched["content"],
                    target_role=target_role_input,
                    use_gpt=True,
                )

            score = result["score"]
            badge = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"

            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.metric("Resume Health Score", f"{badge} {score}/100")
            with col_s2:
                st.metric("Word Count", result["word_count"])
            with col_s3:
                st.metric("Issues Found", len(result["issues"]))

            st.divider()

            if result["issues"]:
                st.subheader("❌ Must Fix")
                for issue in result["issues"]:
                    st.markdown(issue)

            if result["warnings"]:
                st.subheader("⚠️ Should Fix")
                for warning in result["warnings"]:
                    st.markdown(warning)

            if result["suggestions"]:
                st.subheader("💡 Quick Wins")
                for suggestion in result["suggestions"]:
                    st.markdown(suggestion)

            if result.get("gpt_review"):
                st.divider()
                st.subheader("🤖 AI Deep Review")
                st.markdown(result["gpt_review"])

# ════════════════════════════════════════════════════════════
# TAB 3 — Job Search
# ════════════════════════════════════════════════════════════

with tab3:
    st.subheader("Search Jobs")

    col1, col2, col3 = st.columns(3)
    with col1:
        role = st.text_input(
            "Job Role",
            placeholder="Data Engineer, SWE, ML Engineer",
        )
    with col2:
        city = st.text_input("City", placeholder="Dallas")
    with col3:
        state = st.selectbox(
            "State",
            [
                "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
                "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
                "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
                "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
                "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
                "Remote",
            ],
        )

    location = f"{city}, {state}" if city else state

    col4, col5 = st.columns(2)
    with col4:
        h1b_only = st.toggle("H1B Verified Sponsors Only", value=True)
    with col5:
        include_remote = st.toggle("Include Remote Jobs", value=True)

    if st.button("🔍 Search All Jobs", disabled=not role):
        with st.spinner(f"Searching all job boards for {role} in {location}..."):
            jobs = search_all_jobs(role, location)

            if h1b_only:
                jobs = [j for j in jobs if j.get("h1b_sponsor_history")]
            if not include_remote:
                jobs = [j for j in jobs if "remote" not in j.get("location", "").lower()]

            if jobs:
                try:
                    save_jobs(jobs)
                except Exception:
                    pass
                st.success(f"Found {len(jobs)} jobs in {location}")
            else:
                st.warning("No jobs found. Try broader role or location.")

    jobs = get_all_jobs()

    active_resume = None
    if st.session_state.get("active_resume_id"):
        active_resume = get_resume_by_id(st.session_state["active_resume_id"])

    if jobs:
        if active_resume:
            for job in jobs:
                if job.get("description"):
                    ats = score_resume_against_job(
                        active_resume["content"],
                        job["description"],
                        job_title=job.get("title", ""),
                        use_gpt=False,  # fast mode for bulk scoring
                    )
                    job["ats_score"] = ats["score"]
                    job["missing_keywords"] = ats["important_missing"]
                    job["rule_tips"] = ats.get("rule_tips", [])
                    job["ats_summary"] = ats.get("summary", "")
                else:
                    job["ats_score"] = 0
                    job["missing_keywords"] = []
                    job["rule_tips"] = []
                    job["ats_summary"] = ""
            jobs.sort(key=lambda x: x.get("ats_score", 0), reverse=True)

        st.metric("Jobs Found", len(jobs))

        for job in jobs:
            header = (
                f"{job.get('title', '?')} — "
                f"{job.get('company', '?')} | "
                f"{job.get('location', '?')} | "
                f"[{job.get('source', '?')}]"
            )

            with st.expander(header):
                col1, col2 = st.columns(2)

                with col1:
                    score = job.get("ats_score", 0)
                    color = "🟢" if score > 70 else "🟡" if score >= 40 else "🔴"
                    st.metric("ATS Match", f"{color} {score}%")

                with col2:
                    if job.get("h1b_sponsor_history"):
                        st.success(f"✅ H1B Verified ({job.get('h1b_approvals_count', 0)} approvals)")
                    else:
                        st.caption("⚪ No H1B history found")

                if job.get("explicitly_sponsors"):
                    st.info("🎯 Mentions sponsorship in job description")

                if job.get("description"):
                    st.markdown(job["description"][:400] + "...")

                missing = job.get("missing_keywords", [])
                if missing:
                    st.caption(f"Resume missing: {', '.join(missing[:8])}")

                # ATS improvement tips
                tips = job.get("rule_tips", [])
                if tips:
                    st.markdown("**💡 How to improve your match**")
                    for tip in tips:
                        st.markdown(tip)

                col3, col4 = st.columns(2)
                with col3:
                    if job.get("url"):
                        st.link_button("🔗 View Job", job["url"])
                with col4:
                    if st.button("✍️ Generate Application", key=f"gen_{job['id']}"):
                        if not active_resume:
                            st.error("Go to Resumes tab and select an active resume first.")
                        else:
                            with st.spinner("Writing cover letter and optimizing resume..."):
                                try:
                                    profile = get_student_profile()
                                    ats = score_resume_against_job(
                                        active_resume["content"],
                                        job.get("description", ""),
                                        job_title=job.get("title", ""),
                                        use_gpt=True,  # full analysis for application generation
                                    )
                                    cover_letter = generate_cover_letter(
                                        resume=active_resume["content"],
                                        job_title=job.get("title", ""),
                                        company=job.get("company", ""),
                                        job_description=job.get("description", ""),
                                        student_profile=profile,
                                    )
                                    rewritten = rewrite_resume_for_job(
                                        resume=active_resume["content"],
                                        job_description=job.get("description", ""),
                                        missing_keywords=ats["important_missing"],
                                        student_profile=profile,
                                    )
                                    save_application(
                                        job["id"],
                                        active_resume["id"],
                                        cover_letter,
                                        rewritten,
                                    )
                                    st.success("✅ Application saved! Check Applications tab.")
                                except Exception as e:
                                    st.error(f"Error generating application: {e}")

# ════════════════════════════════════════════════════════════
# TAB 4 — Applications
# ════════════════════════════════════════════════════════════

with tab4:
    st.subheader("Your Applications")

    applications = get_applications()
    STATUS_OPTIONS = ["draft", "submitted", "interview", "offer", "rejected"]

    if not applications:
        st.info("Generate applications from the Job Search tab.")
    else:
        for app in applications:
            job = app.get("jobs") or {}
            title = job.get("title", "Unknown Job")
            company = job.get("company", "")
            status = app.get("status", "draft")

            STATUS_ICON = {
                "draft": "📝",
                "submitted": "📤",
                "interview": "🎯",
                "offer": "🎉",
                "rejected": "❌",
            }
            icon = STATUS_ICON.get(status, "📝")

            with st.expander(f"{icon} {title} — {company} | {status.upper()}"):
                new_status = st.selectbox(
                    "Status",
                    STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(status) if status in STATUS_OPTIONS else 0,
                    key=f"status_{app['id']}",
                )
                if new_status != status:
                    try:
                        update_application_status(app["id"], new_status)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error updating status: {e}")

                if job.get("url"):
                    st.link_button("🔗 Apply Now", job["url"])

                st.subheader("Cover Letter")
                edited_cl = st.text_area(
                    "",
                    value=app.get("cover_letter", ""),
                    height=250,
                    key=f"cl_{app['id']}",
                )
                if st.button("💾 Save Cover Letter", key=f"savecl_{app['id']}"):
                    try:
                        update_cover_letter(app["id"], edited_cl)
                        st.success("Saved!")
                    except Exception as e:
                        st.error(f"Error: {e}")

                with st.expander("📄 View Rewritten Resume"):
                    st.text_area(
                        "",
                        value=app.get("rewritten_resume", ""),
                        height=350,
                        key=f"rr_{app['id']}",
                    )

                st.caption(f"Created: {app.get('created_at', '')[:10]}")

# ════════════════════════════════════════════════════════════
# TAB 5 — Career Coach
# ════════════════════════════════════════════════════════════

with tab5:
    st.subheader("🤖 Career Coach")
    st.caption(
        "Your coach remembers everything across all sessions. "
        "Share your university, visa status, goals — it will remember."
    )

    resumes = get_all_resumes()
    coach_resume_context = ""

    if resumes:
        selected_resume = st.selectbox(
            "Give coach your resume context (optional)",
            ["None"] + [r["name"] for r in resumes],
            key="coach_resume_select",
        )
        if selected_resume != "None":
            matched = next((r for r in resumes if r["name"] == selected_resume), None)
            if matched:
                coach_resume_context = matched["content"]

    history = get_conversation_history(limit=50)
    for msg in history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input("Ask your career coach anything...")

    if user_input:
        with st.chat_message("user"):
            st.write(user_input)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = chat_with_coach(user_input, coach_resume_context)
                    st.write(response)
                except Exception as e:
                    st.error(f"Error: {e}")
        st.rerun()

    if st.button("🗑️ Clear Conversation History"):
        try:
            clear_conversation_history()
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")