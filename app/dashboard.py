"""Streamlit dashboard — the primary UI for BioInternshipRadar.

Run via `python run_dashboard.py` (preferred) or `streamlit run app/dashboard.py`.
Pages are implemented as plain functions for readability; each opens its own DB session.
"""
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
import yaml

from app.config import settings
from app.database import get_session, init_db
from app.models import Company, Opportunity, ScanLog
from app.schemas import CompanyIn
from app.services import export_service
from app.services.company_service import (
    companies_missing_career_url,
    create_company,
    list_companies,
    sync_companies_from_yaml,
    update_company,
)
from app.services.notification_service import send_test_notification
from app.services.opportunity_service import add_note, list_opportunities, update_status
from app.services.resume_service import load_student_profile, preview_tailoring, generate_resume_for_opportunity
from app.resume.cover_letter_generator import (
    generate_linkedin_message,
    generate_networking_message,
    generate_referral_request,
)
from app.services.scan_service import run_scan_all_active, run_scan_for_company_id

STATUS_OPTIONS = ["New", "Reviewing", "Interested", "Resume Generated", "Reached Out", "Applied", "Rejected", "Not Relevant", "Archived"]

st.set_page_config(page_title="BioInternship Radar", layout="wide")
init_db()


def main() -> None:
    st.sidebar.title("BioInternship Radar")
    page = st.sidebar.radio(
        "Navigate",
        [
            "Job Feed",
            "Overview",
            "Companies",
            "Opportunity Detail",
            "Resume Tailoring",
            "Notifications",
            "Scan Logs",
            "Settings",
        ],
    )

    with get_session() as session:
        sync_companies_from_yaml(session)

    if page == "Job Feed":
        render_job_feed()
    elif page == "Overview":
        render_overview()
    elif page == "Companies":
        render_companies()
    elif page == "Opportunity Detail":
        render_opportunity_detail()
    elif page == "Resume Tailoring":
        render_resume_tailoring()
    elif page == "Notifications":
        render_notifications()
    elif page == "Scan Logs":
        render_scan_logs()
    elif page == "Settings":
        render_settings()


# ---------------------------------------------------------------------------
# Page 1: Overview
# ---------------------------------------------------------------------------
def render_overview() -> None:
    st.header("Overview")

    with get_session() as session:
        companies = list_companies(session)
        opportunities = list_opportunities(session)
        missing_url = companies_missing_career_url(session)

    today = datetime.utcnow().date()
    new_today = [o for o in opportunities if o.detected_date.date() == today]
    high_fit = [o for o in opportunities if o.fit_score >= settings.min_notification_fit_score]
    last_scan = max((c.last_scanned_at for c in companies if c.last_scanned_at), default=None)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Companies Tracked", len(companies))
    col2.metric("Active Companies", len([c for c in companies if c.active]))
    col3.metric("Missing Career URL", len(missing_url))
    col4.metric("New Opportunities Today", len(new_today))

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Total Opportunities", len(opportunities))
    col6.metric("High-Fit Opportunities", len(high_fit))
    col7.metric("Last Scan", last_scan.strftime("%Y-%m-%d %H:%M") if last_scan else "Never")
    next_scan = (last_scan + timedelta(minutes=settings.scan_interval_minutes)) if last_scan else None
    col8.metric("Next Scan (est.)", next_scan.strftime("%H:%M") if next_scan else "N/A")

    notif_status = "Enabled" if (settings.email_enabled or settings.telegram_enabled or settings.slack_enabled) else "Disabled"
    st.caption(f"Notifications: {notif_status} | Min fit score for alerts: {settings.min_notification_fit_score}")

    if not opportunities:
        st.info("No opportunities yet. Click **Job Feed → Refresh Jobs** to start automatic discovery, or run `python run_scanner.py --all` from the terminal.")
        return

    df = pd.DataFrame([_opportunity_to_row(o) for o in opportunities])

    st.subheader("Opportunities by Category")
    company_to_category = {c.name: c.category for c in companies}
    df["category"] = df["company_name"].map(company_to_category).fillna("Uncategorized")
    st.bar_chart(df["category"].value_counts())

    st.subheader("Opportunities by Company")
    st.bar_chart(df["company_name"].value_counts().head(15))

    st.subheader("Opportunities by Fit Score")
    st.bar_chart(df["fit_score"])

    st.subheader("New Opportunities Over Time")
    df["detected_day"] = pd.to_datetime(df["detected_date"]).dt.date
    st.line_chart(df.groupby("detected_day").size())


# ---------------------------------------------------------------------------
# Page 2: Companies
# ---------------------------------------------------------------------------
def render_companies() -> None:
    st.header("Companies")

    with st.expander("Add a new company"):
        with st.form("add_company_form"):
            name = st.text_input("Name")
            category = st.selectbox("Category", ["Bio Companies", "Startups / Healthcare Tech", "Consulting Companies"])
            career_url = st.text_input("Career URL")
            internship_url = st.text_input("Internship URL")
            platform = st.selectbox("Platform", ["unknown", "greenhouse", "lever", "ashby", "usajobs", "workday", "icims", "company_static"])
            board_id = st.text_input("Board ID (Greenhouse token / Lever slug / Ashby slug)")
            network_contact = st.text_input("Network Contact")
            priority = st.selectbox("Priority", ["High", "Medium", "Low"], index=1)
            submitted = st.form_submit_button("Add Company")
            if submitted and name:
                with get_session() as session:
                    create_company(session, CompanyIn(
                        name=name, category=category, career_url=career_url, internship_url=internship_url,
                        platform=platform, board_id=board_id, network_contact=network_contact, priority=priority,
                    ))
                st.success(f"Added {name}")
                st.rerun()

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("Export companies to CSV"):
            with get_session() as session:
                path = export_service.export_companies_csv(session)
            st.success(f"Exported to {path}")
    with col_b:
        if st.button("Export companies to YAML"):
            with get_session() as session:
                path = export_service.export_companies_yaml(session)
            st.success(f"Exported to {path}")
    with col_c:
        if st.button("Run Scan Now (all active companies)"):
            with get_session() as session:
                scan_run = run_scan_all_active(session)
            st.success(f"Scan complete: {scan_run.new_opportunities_found} new opportunities found")

    with get_session() as session:
        companies = list_companies(session)
        rows = [_company_to_row(c, session) for c in companies]

    if not rows:
        st.info("No companies loaded yet.")
        return

    df = pd.DataFrame(rows)
    missing = df[(df["career_url"] == "") & (df["board_id"] == "") & (~df["platform"].isin(["usajobs"]))]
    if len(missing):
        st.warning(
            f"{len(missing)} companies have no scan config (no career_url, no board_id). "
            f"Edit each company to add platform + board_id, or set career_url. "
            f"Companies on Workday have no public API — monitor them manually."
        )

    st.dataframe(df, width="stretch", hide_index=True)

    st.subheader("Edit a company")
    with get_session() as session:
        companies = list_companies(session)
    selected_name = st.selectbox("Select company to edit", [c.name for c in companies])
    selected = next((c for c in companies if c.name == selected_name), None)
    if selected:
        with st.form("edit_company_form"):
            career_url = st.text_input("Career URL", value=selected.career_url)
            internship_url = st.text_input("Internship URL", value=selected.internship_url)
            _platforms = ["unknown", "greenhouse", "lever", "ashby", "usajobs", "workday", "icims", "company_static"]
            _plat_idx = _platforms.index(selected.platform) if selected.platform in _platforms else 0
            platform = st.selectbox("Platform", _platforms, index=_plat_idx)
            board_id = st.text_input("Board ID (Greenhouse token / Lever slug / Ashby slug)", value=getattr(selected, "board_id", "") or "")
            priority = st.selectbox("Priority", ["High", "Medium", "Low"], index=["High", "Medium", "Low"].index(selected.priority or "Medium"))
            active = st.checkbox("Active", value=selected.active)
            notes = st.text_area("Notes", value=selected.notes)
            col1, col2 = st.columns(2)
            save = col1.form_submit_button("Save")
            test_scan = col2.form_submit_button("Test Scan This Company")

            if save:
                with get_session() as session:
                    update_company(session, selected.id, {
                        "career_url": career_url, "internship_url": internship_url, "platform": platform,
                        "board_id": board_id, "priority": priority, "active": active, "notes": notes,
                    })
                st.success("Saved")
                st.rerun()

            if test_scan:
                with get_session() as session:
                    scan_run = run_scan_for_company_id(session, selected.id)
                st.success(f"Test scan complete: {scan_run.opportunities_found} jobs found, {scan_run.new_opportunities_found} new")


# ---------------------------------------------------------------------------
# Page 1: Job Feed  (primary discovery view)
# ---------------------------------------------------------------------------
def render_job_feed() -> None:
    st.header("Job Feed")

    with get_session() as session:
        companies = list_companies(session)
        opportunities = list_opportunities(session)

    last_scan = max((c.last_scanned_at for c in companies if c.last_scanned_at), default=None)

    # ---- Scan status + refresh ----
    hdr_col, btn_col = st.columns([5, 1])
    with hdr_col:
        if last_scan:
            mins = int((datetime.utcnow() - last_scan).total_seconds() / 60)
            st.caption(
                f"Last scan: {last_scan.strftime('%Y-%m-%d %H:%M UTC')} ({mins} min ago) "
                f"| {len(opportunities)} jobs in database"
            )
        else:
            st.info(
                "No scans have run yet. Click **Refresh Jobs** to discover internships automatically, "
                "or run `python run_scanner.py --all` from the terminal."
            )
    with btn_col:
        if st.button("Refresh Jobs", type="primary", use_container_width=True):
            with st.spinner("Scanning all active sources…"):
                with get_session() as session:
                    scan_run = run_scan_all_active(session)
            st.success(
                f"Done — {scan_run.new_opportunities_found} new jobs found "
                f"({scan_run.opportunities_found} total, {scan_run.errors_count} errors)"
            )
            st.rerun()

    # ---- Filters ----
    col1, col2, col3, col4, col5 = st.columns(5)
    company_filter = col1.selectbox("Company", ["All"] + sorted({o.company_name for o in opportunities}))
    status_filter = col2.selectbox("Status", ["All"] + STATUS_OPTIONS)
    source_filter = col3.selectbox(
        "Source",
        ["All"] + sorted({o.source_platform for o in opportunities if o.source_platform and o.source_platform != "unknown"}),
    )
    min_score = col4.slider("Min Fit Score", 0, 100, 0)
    new_only = col5.checkbox("New only")

    filtered = opportunities
    if company_filter != "All":
        filtered = [o for o in filtered if o.company_name == company_filter]
    if status_filter != "All":
        filtered = [o for o in filtered if o.status == status_filter]
    if source_filter != "All":
        filtered = [o for o in filtered if o.source_platform == source_filter]
    filtered = [o for o in filtered if o.fit_score >= min_score]
    if new_only:
        filtered = [o for o in filtered if o.status == "New"]

    st.caption(f"Showing {len(filtered)} of {len(opportunities)} opportunities")

    col_a, col_b = st.columns(2)
    if col_a.button("Export to CSV"):
        with get_session() as session:
            path = export_service.export_opportunities_csv(session)
        st.success(f"Exported to {path}")
    if col_b.button("Export to Excel"):
        with get_session() as session:
            path = export_service.export_opportunities_excel(session)
        st.success(f"Exported to {path}")

    # ---- Job cards ----
    for opp in filtered[:200]:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            with c1:
                score_icon = "🟢" if opp.fit_score >= 70 else ("🟡" if opp.fit_score >= 40 else "🔴")
                st.markdown(f"**{opp.job_title}** — {opp.company_name}")
                parts = []
                if opp.location:
                    parts.append(opp.location)
                if opp.posted_date:
                    parts.append(f"Posted {opp.posted_date[:10]}")
                parts.append(f"Detected {opp.detected_date.strftime('%Y-%m-%d')}")
                if opp.source_platform and opp.source_platform != "unknown":
                    parts.append(f"via {opp.source_platform}")
                st.caption(" · ".join(parts))
                st.caption(f"{score_icon} Fit score: {opp.fit_score}/100")
                if opp.matched_keywords:
                    st.caption(f"Matched keywords: {opp.matched_keywords}")
                if opp.fit_score_explanation:
                    with st.expander("Why this matched"):
                        st.text(opp.fit_score_explanation)
                if opp.job_url:
                    st.markdown(f"[Apply →]({opp.job_url})")
            with c2:
                new_status = st.selectbox(
                    "Status",
                    STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(opp.status) if opp.status in STATUS_OPTIONS else 0,
                    key=f"status_{opp.id}",
                )
                if new_status != opp.status:
                    with get_session() as session:
                        update_status(session, opp.id, new_status)
                    st.rerun()

    # ---- Add missing job manually (secondary feature) ----
    st.divider()
    with st.expander("Add a missing job manually"):
        with st.form("manual_opportunity_form"):
            company_name = st.text_input("Company")
            job_title = st.text_input("Role Title")
            job_url = st.text_input("Job URL")
            location = st.text_input("Location")
            posted_date = st.text_input("Posted Date (optional)")
            description = st.text_area("Description / paste job posting text")
            notes = st.text_area("Your notes")
            submitted = st.form_submit_button("Add")
            if submitted and company_name and job_title:
                from app.schemas import OpportunityCandidate
                from app.services.opportunity_service import upsert_opportunity
                with get_session() as session:
                    matching_company = next(
                        (c for c in list_companies(session) if c.name.lower() == company_name.lower()), None
                    )
                    candidate = OpportunityCandidate(
                        company_name=company_name, job_title=job_title, job_url=job_url,
                        location=location, posted_date=posted_date, description=description,
                        source_platform="manual",
                    )
                    opp, is_new = upsert_opportunity(session, candidate, matching_company)
                    if notes:
                        add_note(session, opp.id, notes)
                st.success(
                    f"{'Added' if is_new else 'Already existed (refreshed)'}: "
                    f"{job_title} at {company_name} — fit score {opp.fit_score}"
                )


# ---------------------------------------------------------------------------
# Page 4: Opportunity Detail
# ---------------------------------------------------------------------------
def render_opportunity_detail() -> None:
    st.header("Opportunity Detail")

    with get_session() as session:
        opportunities = list_opportunities(session)

    if not opportunities:
        st.info("No opportunities yet.")
        return

    labels = [f"{o.company_name} — {o.job_title} (id={o.id})" for o in opportunities]
    selected_idx = st.selectbox("Select opportunity", range(len(opportunities)), format_func=lambda i: labels[i])
    opp = opportunities[selected_idx]

    with get_session() as session:
        company = next((c for c in list_companies(session) if c.name == opp.company_name), None)

    st.subheader(f"{opp.job_title} at {opp.company_name}")
    st.write(f"**Location:** {opp.location or 'Not specified'}")
    st.write(f"**Fit Score:** {opp.fit_score}")
    st.write(f"**Status:** {opp.status}")
    if opp.job_url:
        st.markdown(f"[Open application link]({opp.job_url})")
    if company and company.network_contact:
        st.write(f"**Network Contact:** {company.network_contact}")

    st.subheader("Fit Score Explanation")
    st.text(opp.fit_score_explanation or "No explanation recorded.")

    st.subheader("Full Description")
    st.text_area("Description", opp.description, height=200, disabled=True)

    st.subheader("Notes")
    notes = st.text_area("Edit notes", opp.notes, key=f"notes_{opp.id}")
    if st.button("Save notes"):
        with get_session() as session:
            add_note(session, opp.id, notes)
        st.success("Notes saved")

    col1, col2, col3, col4 = st.columns(4)
    if col1.button("Generate Tailored Resume"):
        st.session_state["resume_target_opportunity_id"] = opp.id
        st.info("Go to the Resume Tailoring page to preview and generate.")
    if col2.button("Generate Networking Message"):
        profile = load_student_profile()
        plan, _ = preview_tailoring(opp)
        msg = generate_networking_message(profile.get("student_name", ""), opp.company_name, opp.job_title, company.network_contact if company else "", plan)
        st.text_area("Networking message draft", msg, height=150)
    if col3.button("Mark Applied"):
        with get_session() as session:
            update_status(session, opp.id, "Applied")
        st.success("Marked as Applied")
        st.rerun()
    if col4.button("Archive"):
        with get_session() as session:
            update_status(session, opp.id, "Archived")
        st.success("Archived")
        st.rerun()


# ---------------------------------------------------------------------------
# Page 5: Resume Tailoring
# ---------------------------------------------------------------------------
def render_resume_tailoring() -> None:
    st.header("Resume Tailoring")

    base_path = settings.resolved_path(settings.base_resume_path)
    if not base_path.exists():
        st.error(f"Base resume not found at {base_path}. Place a .docx file there first.")
        return

    with get_session() as session:
        opportunities = list_opportunities(session)
    if not opportunities:
        st.info("No opportunities to tailor a resume for yet.")
        return

    labels = [f"{o.company_name} — {o.job_title}" for o in opportunities]
    default_idx = 0
    target_id = st.session_state.get("resume_target_opportunity_id")
    if target_id:
        for i, o in enumerate(opportunities):
            if o.id == target_id:
                default_idx = i
    selected_idx = st.selectbox("Select opportunity", range(len(opportunities)), index=default_idx, format_func=lambda i: labels[i])
    opp = opportunities[selected_idx]

    use_llm = st.checkbox(
        f"Use LLM-assisted tailoring (provider: {settings.llm_provider})",
        value=False,
        disabled=(settings.llm_provider == "none"),
        help="LLM-assisted tailoring sends resume text and the job description to the configured provider.",
    )
    if use_llm and settings.llm_provider != "none":
        st.warning("LLM-assisted tailoring may send resume text and job descriptions to the configured LLM provider.")

    if st.button("Preview Tailoring Plan"):
        plan, llm_extra = preview_tailoring(opp, use_llm=use_llm)
        st.session_state["tailoring_plan"] = plan
        st.session_state["tailoring_opportunity_id"] = opp.id

    plan = st.session_state.get("tailoring_plan")
    if plan and st.session_state.get("tailoring_opportunity_id") == opp.id:
        st.subheader("Matched Keywords")
        st.write(", ".join(plan.matched_keywords) or "None found")

        st.subheader("Missing Keywords (do not fabricate — for awareness only)")
        st.write(", ".join(plan.missing_keywords) or "None")

        st.subheader("Suggested Summary")
        st.text_area("Summary", plan.suggested_summary, height=80, disabled=True)

        st.subheader("Relevant Existing Bullets")
        for bullet in plan.bullet_suggestions:
            st.write(f"- {bullet}")

        st.subheader("Changes That Will Be Made")
        for change in plan.changes_made:
            st.write(f"- {change}")

        if plan.warnings:
            st.subheader("Warnings")
            for warning in plan.warnings:
                st.warning(warning)

        if st.button("Generate and Save Tailored Resume"):
            with get_session() as session:
                fresh_opp = session.get(Opportunity, opp.id)
                resume_path, metadata_path = generate_resume_for_opportunity(session, fresh_opp, plan)
            st.success(f"Saved resume to {resume_path}")
            st.caption(f"Metadata saved to {metadata_path}")

    st.divider()
    st.subheader("Outreach Drafts")
    with get_session() as session:
        company = next((c for c in list_companies(session) if c.name == opp.company_name), None)
    profile = load_student_profile()
    if plan:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_area("LinkedIn message", generate_linkedin_message(profile.get("student_name", ""), opp.company_name, opp.job_title), height=120)
        with col2:
            st.text_area("Networking email", generate_networking_message(profile.get("student_name", ""), opp.company_name, opp.job_title, company.network_contact if company else "", plan), height=120)
        with col3:
            referral = generate_referral_request(profile.get("student_name", ""), opp.company_name, opp.job_title, company.network_contact if company else "")
            st.text_area("Referral request", referral or "No network contact on file for this company.", height=120)
    else:
        st.info("Click 'Preview Tailoring Plan' above to generate outreach drafts.")


# ---------------------------------------------------------------------------
# Page 6: Notifications
# ---------------------------------------------------------------------------
def render_notifications() -> None:
    st.header("Notifications")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Email")
        st.write(f"Enabled: {settings.email_enabled}")
        st.write(f"To: {settings.email_to or 'Not set'}")
        if st.button("Send test email"):
            success, error = send_test_notification("email")
            st.success("Sent") if success else st.error(error)
    with col2:
        st.subheader("Telegram")
        st.write(f"Enabled: {settings.telegram_enabled}")
        if st.button("Send test Telegram message"):
            success, error = send_test_notification("telegram")
            st.success("Sent") if success else st.error(error)
    with col3:
        st.subheader("Slack")
        st.write(f"Enabled: {settings.slack_enabled}")
        if st.button("Send test Slack message"):
            success, error = send_test_notification("slack")
            st.success("Sent") if success else st.error(error)

    st.divider()
    st.caption("Configure channels in your .env file (see .env.example). Restart the dashboard after changing .env.")

    from app.models import Notification
    with get_session() as session:
        recent = session.query(Notification).order_by(Notification.sent_at.desc()).limit(50).all()
    if recent:
        st.subheader("Recent Notification Attempts")
        st.dataframe(pd.DataFrame([{
            "sent_at": n.sent_at, "channel": n.channel, "status": n.status, "error": n.error_message,
        } for n in recent]), width="stretch", hide_index=True)


# ---------------------------------------------------------------------------
# Page 7: Scan Logs
# ---------------------------------------------------------------------------
def render_scan_logs() -> None:
    st.header("Scan Logs")

    with get_session() as session:
        logs = session.query(ScanLog).order_by(ScanLog.started_at.desc()).limit(300).all()

    if not logs:
        st.info("No scans have run yet.")
        return

    df = pd.DataFrame([{
        "started_at": l.started_at,
        "company": l.company_name,
        "scanner": l.scanner_used,
        "status": l.status,
        "jobs_found": l.jobs_found,
        "new_jobs": l.new_jobs_found,
        "error": l.error_message,
        "source_url": l.source_url,
    } for l in logs])
    st.dataframe(df, width="stretch", hide_index=True)

    if st.button("Export scan logs to CSV"):
        with get_session() as session:
            path = export_service.export_scan_logs_csv(session)
        st.success(f"Exported to {path}")


# ---------------------------------------------------------------------------
# Page 8: Settings
# ---------------------------------------------------------------------------
def render_settings() -> None:
    st.header("Settings")

    st.subheader("Scan Configuration (read from .env — edit the file then restart)")
    st.code(
        f"SCAN_INTERVAL_MINUTES={settings.scan_interval_minutes}\n"
        f"MAX_COMPANIES_PER_SCAN_BATCH={settings.max_companies_per_scan_batch}\n"
        f"ENABLE_PLAYWRIGHT={settings.enable_playwright}\n"
        f"HEADLESS_BROWSER={settings.headless_browser}\n"
        f"MIN_NOTIFICATION_FIT_SCORE={settings.min_notification_fit_score}\n"
        f"LLM_PROVIDER={settings.llm_provider}\n"
        f"BASE_RESUME_PATH={settings.base_resume_path}\n"
        f"GENERATED_RESUME_DIR={settings.generated_resume_dir}\n"
        f"EXPORT_DIR={settings.export_dir}\n"
    )

    st.subheader("Keyword Lists (data/keywords.yaml)")
    if settings.keywords_yaml_path.exists():
        with open(settings.keywords_yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
        edited = st.text_area("keywords.yaml", content, height=300)
        if st.button("Save keywords.yaml"):
            try:
                yaml.safe_load(edited)
            except yaml.YAMLError as exc:
                st.error(f"Invalid YAML: {exc}")
            else:
                with open(settings.keywords_yaml_path, "w", encoding="utf-8") as f:
                    f.write(edited)
                from app.services.keyword_service import clear_keyword_cache
                clear_keyword_cache()
                st.success("Saved. Cache cleared.")

    st.subheader("Ignored Keywords (data/ignored_keywords.yaml)")
    if settings.ignored_keywords_yaml_path.exists():
        with open(settings.ignored_keywords_yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
        edited = st.text_area("ignored_keywords.yaml", content, height=150)
        if st.button("Save ignored_keywords.yaml"):
            try:
                yaml.safe_load(edited)
            except yaml.YAMLError as exc:
                st.error(f"Invalid YAML: {exc}")
            else:
                with open(settings.ignored_keywords_yaml_path, "w", encoding="utf-8") as f:
                    f.write(edited)
                from app.services.keyword_service import clear_keyword_cache
                clear_keyword_cache()
                st.success("Saved. Cache cleared.")

    st.subheader("Student Profile (data/student_profile.yaml)")
    if settings.student_profile_yaml_path.exists():
        with open(settings.student_profile_yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
        edited = st.text_area("student_profile.yaml", content, height=300)
        if st.button("Save student_profile.yaml"):
            try:
                yaml.safe_load(edited)
            except yaml.YAMLError as exc:
                st.error(f"Invalid YAML: {exc}")
            else:
                with open(settings.student_profile_yaml_path, "w", encoding="utf-8") as f:
                    f.write(edited)
                st.success("Saved.")


# ---------------------------------------------------------------------------
# Row helpers
# ---------------------------------------------------------------------------
def _opportunity_to_row(o: Opportunity) -> dict:
    return {
        "id": o.id,
        "company_name": o.company_name,
        "job_title": o.job_title,
        "fit_score": o.fit_score,
        "status": o.status,
        "detected_date": o.detected_date,
        "location": o.location,
    }


def _company_to_row(c: Company, session) -> dict:
    opp_count = len([o for o in list_opportunities(session, company_name=c.name)])
    return {
        "name": c.name,
        "category": c.category,
        "platform": c.platform,
        "board_id": getattr(c, "board_id", "") or "",
        "career_url": c.career_url,
        "network_contact": c.network_contact,
        "priority": c.priority,
        "active": c.active,
        "last_scanned_at": c.last_scanned_at,
        "last_scan_status": c.last_scan_status,
        "opportunities_found": opp_count,
    }


if __name__ == "__main__":
    main()
else:
    main()
