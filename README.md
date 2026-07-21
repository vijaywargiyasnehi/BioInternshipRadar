# BioInternship Radar

Automated internship tracker for bioengineering, biomedical, pharma, medical devices, regulatory, consulting, and adjacent fields. Discovers opportunities automatically from Greenhouse, Lever, and Ashby job-board APIs, scores them for bioengineering relevance, and surfaces them in a private per-user Streamlit dashboard.

---

## What it does

- **Automatically discovers internships** from Greenhouse, Lever, and Ashby job-board APIs — no manual link entry required.
- **Scores each role** for relevance to a bioengineering student profile using keywords, company priority, and job type.
- **Deduplicates** across scans — re-scans never create duplicate rows.
- **Per-user application tracking** — saved jobs, status, notes, and applied dates are completely private per account.
- **Sends notifications** via email, Telegram, or Slack for high-fit new postings.
- **Tailors your resume** rule-based (or LLM-assisted) against a base .docx — never fabricates experience.
- Local **SQLite** for development; **PostgreSQL / Supabase** for production.

---

## Authentication

Uses Streamlit native OIDC — sign in with Google. No username/password system. Identity is sourced from the OIDC `sub` claim only, never from forms or URL parameters. Unauthenticated visitors see only the public landing page.

---

## Per-user data isolation

| Data | Visibility |
|---|---|
| Job listings (title, company, score, apply link) | All authenticated users |
| Application status, notes, saved flag | Your account only |
| Applied date, follow-up date, resume version | Your account only |
| Exports (CSV / Excel) | Your data only |
| Scan logs, source coverage | All authenticated users |

Isolation is enforced in the database layer (every read/write filters on `user_id`), not only in the UI.

---

## Supported providers

| Provider | How it works | Config needed |
|---|---|---|
| **Greenhouse** | `boards-api.greenhouse.io/v1/boards/{board_id}/jobs` | `platform: greenhouse` + `board_id: <token>` |
| **Lever** | `api.lever.co/v0/postings/{slug}?mode=json` | `platform: lever` + `board_id: <slug>` |
| **Ashby** | POST to `jobs.ashbyhq.com` non-user-facing API | `platform: ashby` + `board_id: <slug>` |
| **Workday** | No public API — manual monitoring reminder | `platform: workday` |

---

## Quick start (local)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  /  source .venv/bin/activate  (macOS/Linux)
pip install -r requirements.txt
copy .env.example .env
copy .streamlit\secrets.example.toml .streamlit\secrets.toml  # edit with your OAuth creds
streamlit run app/dashboard.py
```

Without OAuth configured, the app runs in local-dev mode with a warning banner.

---

## Configuring companies

Edit `data/companies.yaml`:

```yaml
companies:
  - name: Example Biotech
    category: Bio Companies
    platform: greenhouse
    board_id: examplebiotech
    priority: Medium
    active: true
```

Finding board IDs:
- Greenhouse: visit `https://boards.greenhouse.io/<slug>`
- Lever: visit `https://jobs.lever.co/<slug>`
- Ashby: visit `https://jobs.ashbyhq.com/<slug>`

If the page loads with job listings, that slug is your `board_id`.

---

## Running the scanner

```bash
python run_scanner.py --all     # scan all active companies now
python run_scanner.py           # scan companies due per interval
python scheduler.py             # continuous background scheduler
```

Or click **Refresh Jobs** in the dashboard.

---

## Google OAuth setup

1. [Google Cloud Console](https://console.cloud.google.com/apis/credentials) → Create OAuth 2.0 Client ID (Web application).
2. Authorized redirect URIs:
   - Local: `http://localhost:8501/oauth2callback`
   - Production: `https://biointernshipradar-sqtgcj2of9akzkknqfral3.streamlit.app/oauth2callback`
3. Copy `client_id` and `client_secret` into `.streamlit/secrets.toml`:

```toml
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "CHANGE_ME_32_CHARS"

[auth.google]
client_id = "YOUR_CLIENT_ID.apps.googleusercontent.com"
client_secret = "YOUR_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

---

## Supabase / PostgreSQL setup

1. Create a free project at [supabase.com](https://supabase.com).
2. Project Settings → Database → Connection string (URI).
3. Add to `.streamlit/secrets.toml` and Streamlit Cloud Secrets:

```toml
[database]
url = "postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres"
```

`init_db()` creates all tables on first run.

---

## Deploying to Streamlit Community Cloud

1. Push repo to GitHub (`.gitignore` excludes `.env`, `secrets.toml`, `database.sqlite`).
2. [share.streamlit.io](https://share.streamlit.io) → New app → repo `vijaywargiyasnehi/BioInternshipRadar`, branch `master`, main file `app/dashboard.py`.
3. Advanced settings → Secrets — paste contents of `.streamlit/secrets.toml`.
4. Deploy.

For continuous scanning, run `scheduler.py` on a VPS or GitHub Actions cron.

---

## Migrating existing data (one-time)

After the original owner logs in for the first time:

```bash
python scripts/migrate_owner_data.py --email you@gmail.com
```

Copies legacy `Opportunity.status` / `.notes` into `UserJob` records scoped to your account. New users are unaffected.

---

## Privacy and security

- Identity sourced from OIDC `sub` only — never from forms, query params, or session state.
- Every database query involving application tracking filters on `user_id`.
- Exports contain only the authenticated user's own tracking data.
- Secrets are in `.gitignore` and never committed.
- Resumes/uploads should use Supabase Storage in production (not the local filesystem).

---

## Known limitations

- Workday (most large pharma/med-device) has no public API — monitor career pages manually.
- Board IDs marked "(medium confidence)" may fail if a company changed ATS — check Scan Logs.
- Playwright for JS-heavy pages is not available on Streamlit Community Cloud.
- Streamlit Cloud local filesystem resets on redeploy — use PostgreSQL for production.

---

## Legal

All sources used are public, read-only APIs offered for job seekers. No authentication bypass or ToS violation is involved.
