# 🌐 JobHunt Int

> The job search platform built exclusively for international students in the United States.

---

## Setup

Set the following variables in a `.env` file at the project root (or export them in your shell):

```
SUPABASE_URL=<your supabase project url>
SUPABASE_KEY=<anon or service key>
SUPABASE_PASSWORD_RESET_URL=<full URL where users should end up after clicking the reset link>
RAPIDAPI_KEY=<optional; JSearch via RapidAPI>
TAVILY_API_KEY=<optional; Tavily AI search>
```

`SUPABASE_PASSWORD_RESET_URL` should typically be your app's base URL (e.g. `http://localhost:8501`) so that the recovery email brings users back into the Streamlit login page where they can set a new password.  

To verify the flow locally:

1. Start the app with that environment variable exported.
2. Click "Forgot Password?" and request a reset link.
3. Open the link from your inbox; you should land back on the login screen with
a message and a form to choose a new password.
4. After submitting the new password the query parameters are cleared and you
   can sign in normally.

The first two keys are required for authentication and data storage.  The
other two enable additional job sources and can be left blank if you prefer a
smaller, fully verified dataset.

## The Problem Nobody Is Solving

Every year, hundreds of thousands of international students graduate from US universities and face a job search that is fundamentally broken.

They apply to hundreds of companies. Most will never sponsor a visa. They miss OPT deadlines because nobody told them the rules. They walk into interviews not knowing how to handle the visa question. They watch their peers get offers while their clock runs out.

No job board filters by visa sponsorship. No career coach understands immigration. No platform was built with them in mind.

**JobHunt Int is built for them.**

---

## What We're Building

A platform that combines job search, AI career tools, and community — specifically designed for international students navigating the US job market on F-1 and OPT visas.

### 🔍 Smart Job Search
Find jobs at companies with verified H1B sponsorship history — backed by real US Department of Labor data. Results are now ranked using a tiered quality system:

* **✅ Verified** – listings fetched directly from public Greenhouse/Lever APIs.
* **⚪ H1B Verified Company** – scraped jobs where the employer exists in the H1B CSV.
* **⚠️ Unverified** – everything else, clearly flagged so you can make quality-over-quantity decisions.

Stop wasting time applying to companies that will never sponsor you.

### 🤖 AI Career Tools
- Resume optimization tailored to each job
- Cover letters that sound human, not AI-generated
- ATS scoring so you know where you stand before you apply
- Persistent career coach that remembers your profile, goals, and history

### 📊 Visa Intelligence
Real-time immigration news from official sources. OPT timeline tracking. Sponsorship verification from half a million government records.

### 🎓 JobHunt Learn *(coming soon)*
One-on-one mentorship sessions with industry professionals actively working in tech. Project guidance, skill building, and career coaching — specifically for international CS, Data Science, ML, AI, Cybersecurity, and Software Engineering students.

Mentors are people who have been where you are — international professionals now working at top US companies who understand the visa journey firsthand.

---

## Who This Is For

- F-1 students approaching graduation
- Students on OPT searching for their first US job
- STEM OPT students looking to extend
- Anyone who has heard "we don't sponsor visas" one too many times

---

## Current Status

🟢 **Live** — Core platform is running with job search, AI resume tools, career coaching, and immigration news.  
✉️ **Authentication now supports password reset; use the "Forgot Password" link on the login page if you ever get locked out.**  
When a reset email is generated, the link will return you to the app (set
`SUPABASE_PASSWORD_RESET_URL` accordingly).  The login screen will detect the
recovery token and present a form so you can choose a new password directly in
our UI.

🟡 **In Progress** — Authentication, multi-user support, full web app conversion.

🔴 **Planned** — Mentorship marketplace, mobile app, ML-powered sponsor predictions, voice and vision features.

---

## Roadmap

### Near Term
- User authentication and accounts
- Full React web application
- Mobile app

### Growth
- **JobHunt Learn** — mentorship marketplace connecting international students with industry professionals
- One-on-one sessions, project guidance, mock interviews
- Focus areas: Software Engineering, Data Science, ML/AI, Cybersecurity, Applied AI

### Long Term
- ML model predicting which companies are likely to sponsor based on role, location, and timing
- Voice interface for career coach
- University and DSO portal
- Payment integration for mentorship sessions
- Expansion beyond tech into other fields

---

## The Bigger Vision

JobHunt Int starts as a job search tool. It grows into the complete support system that every international student needs but never had — from finding the right companies, to getting the skills, to landing the offer, to navigating the visa process.

The international student community is one of the most talented, hardworking, and underserved communities in the US job market. We're building for them.

---

## Contributing

We are a small team actively building. If you are an international student, a developer, or someone who believes in this mission — reach out.

---

## Disclaimer

JobHunt Int is not a legal service. Sponsorship history data is sourced from public government records and does not guarantee future sponsorship decisions. For immigration decisions always consult your DSO or a licensed immigration attorney.

---

*Built by international students, for international students.*
