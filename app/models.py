"""SQLAlchemy ORM models for BioInternshipRadar."""
from datetime import datetime

from sqlalchemy import String, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(100), default="")
    career_url: Mapped[str] = mapped_column(String(500), default="")
    internship_url: Mapped[str] = mapped_column(String(500), default="")
    platform: Mapped[str] = mapped_column(String(50), default="unknown")
    network_contact: Mapped[str] = mapped_column(String(255), default="")
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, default="")

    board_id: Mapped[str] = mapped_column(String(100), default="")

    scan_interval_minutes: Mapped[int] = mapped_column(Integer, default=15)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_scan_status: Mapped[str] = mapped_column(String(50), default="never_scanned")
    last_scan_error: Mapped[str] = mapped_column(Text, default="")

    opportunities: Mapped[list["Opportunity"]] = relationship(back_populates="company")


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    company_name: Mapped[str] = mapped_column(String(255))

    job_title: Mapped[str] = mapped_column(String(500))
    job_url: Mapped[str] = mapped_column(String(1000), default="")
    location: Mapped[str] = mapped_column(String(255), default="")
    remote_status: Mapped[str] = mapped_column(String(50), default="unknown")
    department: Mapped[str] = mapped_column(String(255), default="")
    job_type: Mapped[str] = mapped_column(String(100), default="")
    posted_date: Mapped[str] = mapped_column(String(50), default="")
    detected_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    description: Mapped[str] = mapped_column(Text, default="")
    source_platform: Mapped[str] = mapped_column(String(50), default="unknown")
    source_url: Mapped[str] = mapped_column(String(1000), default="")
    opportunity_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    fit_score: Mapped[int] = mapped_column(Integer, default=0)
    fit_score_explanation: Mapped[str] = mapped_column(Text, default="")
    matched_keywords: Mapped[str] = mapped_column(Text, default="")  # comma-separated
    ignored_keywords: Mapped[str] = mapped_column(Text, default="")  # comma-separated

    status: Mapped[str] = mapped_column(String(50), default="New")
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    notification_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resume_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    resume_path: Mapped[str] = mapped_column(String(1000), default="")
    cover_letter_path: Mapped[str] = mapped_column(String(1000), default="")
    notes: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company: Mapped["Company"] = relationship(back_populates="opportunities")


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="running")
    companies_scanned: Mapped[int] = mapped_column(Integer, default=0)
    opportunities_found: Mapped[int] = mapped_column(Integer, default=0)
    new_opportunities_found: Mapped[int] = mapped_column(Integer, default=0)
    errors_count: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")

    scan_logs: Mapped[list["ScanLog"]] = relationship(back_populates="scan_run")


class ScanLog(Base):
    __tablename__ = "scan_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_run_id: Mapped[int | None] = mapped_column(ForeignKey("scan_runs.id"), nullable=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    company_name: Mapped[str] = mapped_column(String(255), default="")

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scanner_used: Mapped[str] = mapped_column(String(50), default="")
    status: Mapped[str] = mapped_column(String(50), default="")
    jobs_found: Mapped[int] = mapped_column(Integer, default=0)
    new_jobs_found: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str] = mapped_column(String(1000), default="")

    scan_run: Mapped["ScanRun"] = relationship(back_populates="scan_logs")


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"), nullable=True)
    company_name: Mapped[str] = mapped_column(String(255), default="")
    job_title: Mapped[str] = mapped_column(String(500), default="")
    document_type: Mapped[str] = mapped_column(String(50), default="resume")  # resume | cover_letter | outreach
    file_path: Mapped[str] = mapped_column(String(1000), default="")
    metadata_path: Mapped[str] = mapped_column(String(1000), default="")
    base_resume_path: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[str] = mapped_column(Text, default="")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"), nullable=True)
    channel: Mapped[str] = mapped_column(String(50), default="email")
    recipient: Mapped[str] = mapped_column(String(255), default="")
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(50), default="sent")
    error_message: Mapped[str] = mapped_column(Text, default="")
    message_preview: Mapped[str] = mapped_column(Text, default="")
