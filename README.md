# BioInternship Radar

Automated internship tracker for bioengineering, biomedical, pharma, medical devices, regulatory, consulting, and adjacent fields. Discovers opportunities automatically from multiple sources, scores them for relevance, and surfaces them in a searchable Streamlit dashboard.

---

## What it does

- **Automatically discovers internships** from Greenhouse, Lever, Ashby, and USAJobs job-board APIs — no manual link entry required.
- **Scores each role** for relevance to a bioengineering student profile (keywords, company priority, location, ignored terms).
- **Deduplicates** across scans using URL/content hashes so re-scans never create duplicate rows.
- **Tracks your applications** — save, apply, add notes, and track status per opportunity. Refreshes never erase your application history.
- **Sends notifications** via email, Telegram, or Slack for high-fit new postings.
- **Tailors your resume** rule-based (or LLM-assisted) against a base .docx file — never fabricates experience.
- Runs on **local SQLite**; all data stays on your machine.

---

## Supported providers

| Provider | How it works | Config needed |
|---|---|---|
| **Greenhouse** | `boards-api.greenhouse.io/v1/boards/{board_id}/jobs` | `platform: greenhouse` + `board_id: <token>` in companies.yaml |
| **Lever** | `api.lever.co/v0/postings/{slug}?mode=json` | `platform: lever` + `board_id: <slug>` in companies.yaml |
| **Ashby** | POST to `jobs.ashbyhq.com/api/non-user-facing/job-board/job-postings` | `platform: ashby` + `board_id: <slug>` in companies.yaml |
| **USAJobs** | Searches `data.usajobs.gov/api/search` for bioengineering internships at NIH, FDA, CDC, DoD, etc. | Free API key — set `USAJOBS_API_KEY` + `USAJOBS_EMAIL` in `.env` |
| **Workday** | No public API — monitor career pages manually | Set `platform: workday` as a reminder |
| **Static / Playwright** | HTML scraping fallback for any company with a `career_url` | Set `career_url` in companies.yaml |

---

## Quick start

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate         # Windows
# source .venv/bin/activate    # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
copy .env.example .env         # Windows
# cp .env.example .env         # macOS/Linux
# Edit .env — defaults work for a first run

# 4. Launch the dashboard
python run_dashboard.py        # opens http://localhost:8501

# 5. Click "Refresh Jobs" in the dashboard, or run from terminal:
python run_scanner.py --all
```

Double-click **BioInternship Radar** on your Desktop to launch (Windows shortcut).

---

## Automated discovery — how it works

1. **Refresh Jobs** (button in the dashboard) or `python run_scanner.py --all` iterates all active companies.
2. The scanner router dispatches each company to the right provider based on `platform` + `board_id`.
3. Each provider fetches current postings via a public API (no scraping, no auth bypass).
4. Results are **filtered** to internship/co-op/fellowship titles (`INTERNSHIP_ONLY=true` in .env).
5. Each job is **scored** against `data/keywords.yaml` (keywords, location, company priority).
6. New jobs are stored; existing jobs update `last_seen_at` without duplicating.
7. Jobs above `MIN_NOTIFICATION_FIT_SCORE` trigger notifications (if configured).

---

## Configuring companies

Edit `data/companies.yaml`:

```yaml
companies:
  - name: Example Biotech
    category: Bio Companies
    platform: greenhouse          # greenhouse | lever | ashby | usajobs | workday | unknown
    board_id: examplebiotech      # ATS token/slug — the scanner uses this directly
    career_url: ""                # optional if board_id is set
    priority: Medium              # High | Medium | Low
    active: true
    notes: ""
```

**Finding board IDs:**
- Greenhouse: go to `https://boards.greenhouse.io/<slug>` — if it shows a job board, that slug is your `board_id`.
- Lever: go to `https://jobs.lever.co/<slug>` — same pattern.
- Ashby: go to `https://jobs.ashbyhq.com/<slug>`.

The companies.yaml ships with verified and best-effort board IDs pre-filled. Board IDs marked "(medium confidence)" in the `notes` field may fail if the company changed ATS vendors — check the Scan Logs page for errors and correct them.

---

## USAJobs (federal internships — NIH, FDA, CDC, DoD)

Register at [developer.usajobs.gov](https://developer.usajobs.gov) (free, instant approval), then add to `.env`:

```
USAJOBS_API_KEY=your_key_here
USAJOBS_EMAIL=your@email.com
```

The "Federal Agencies (USAJobs)" entry in companies.yaml then automatically searches 14 bioengineering queries across all federal agencies — NIH, FDA, CDC, BARDA, DoD, and more. No per-agency config needed.

---

## Running locally

```bash
# Dashboard only
python run_dashboard.py

# One-shot scan (companies due per their interval)
python run_scanner.py

# One-shot scan of all active companies
python run_scanner.py --all

# Continuous scheduler (repeats every SCAN_INTERVAL_MINUTES)
python scheduler.py
```

---

## Configuration reference (`.env`)

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///data/database.sqlite` | SQLite path |
| `SCAN_INTERVAL_MINUTES` | `15` | Scheduler interval |
| `INTERNSHIP_ONLY` | `true` | Only store internship/co-op/fellowship-titled roles |
| `MIN_NOTIFICATION_FIT_SCORE` | `60` | Minimum score to trigger a notification |
| `USAJOBS_API_KEY` | *(blank)* | USAJobs API key (free registration) |
| `USAJOBS_EMAIL` | *(blank)* | Email registered with USAJobs API |
| `EMAIL_ENABLED` | `false` | Email notifications via SMTP |
| `TELEGRAM_ENABLED` | `false` | Telegram notifications |
| `SLACK_ENABLED` | `false` | Slack webhook notifications |
| `LLM_PROVIDER` | `none` | `openai` / `anthropic` / `local` / `none` |

---

## Application tracking

Every opportunity stores:

| Field | Description |
|---|---|
| Status | New → Reviewing → Interested → Resume Generated → Reached Out → Applied → Rejected / Archived |
| Notes | Free-text notes; editable in Opportunity Detail |
| Resume path | Set after generating a tailored resume |
| Notification sent | Timestamp of alert |

Application data is **never overwritten by refreshes** — only `last_seen_at` and `job_title` are updated on re-scan.

---

## Data files

| File | Purpose |
|---|---|
| `data/companies.yaml` | Company list with platform + board_id |
| `data/keywords.yaml` | Relevance keywords by category (expand to improve scoring) |
| `data/ignored_keywords.yaml` | Keywords that penalize the fit score |
| `data/locations.yaml` | Preferred locations for scoring |
| `data/student_profile.yaml` | Your profile (skills, target roles, experience) |
| `resumes/base/base_resume.docx` | Your base resume for tailoring |

---

## Deploying on Streamlit Community Cloud

1. Push repo to GitHub (`.gitignore` excludes `.env` and `data/database.sqlite`).
2. Add secrets in the Streamlit Cloud dashboard matching your `.env` variables.
3. Set main file to `app/dashboard.py`.
4. For continuous scanning, run `scheduler.py` separately (VPS or GitHub Actions cron).

---

## Known limitations

- **Workday** (most large pharma/med-device) has no public API — those companies appear in the list as reminders to check manually.
- **Board IDs marked "(medium confidence)"** are best-effort guesses. If a scan errors, check Scan Logs, visit `boards.greenhouse.io/<board_id>` to verify, then correct the YAML.
- **USAJobs** requires free registration. Some federal titles say "Student Trainee" instead of "Intern" — these still match the scanner's search terms.
- **Playwright** for JS-heavy pages requires `python -m playwright install chromium` after pip install.
- Rate limits: 1–3 second jitter between company requests; large boards (100+ jobs) may take several seconds.

---

## Legal

All data sources used are **public, read-only APIs** explicitly offered by each vendor for job seekers. No authentication bypass, credentials, or ToS violation is involved. Job postings are fetched and stored locally; they are not redistributed.
