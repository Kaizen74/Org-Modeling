"""SQLAlchemy models for the Org Design Analyzer."""

from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON, ForeignKey, UniqueConstraint
from datetime import datetime
import uuid

from .database import Base


def generate_uuid():
    return str(uuid.uuid4())


class GradeSalary(Base):
    """Grade and salary configuration model."""
    __tablename__ = "grade_salaries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    grade = Column(String(50), unique=True, nullable=False, index=True)
    median_salary = Column(Float, nullable=False)
    currency = Column(String(3), default="SGD")
    display_order = Column(Integer, default=99)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<GradeSalary(grade='{self.grade}', salary={self.median_salary})>"


class OrgAnalysis(Base):
    """Stored org analysis results."""
    __tablename__ = "org_analyses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Raw data
    employee_count = Column(Integer)
    raw_data = Column(JSON)  # Store parsed CSV data

    # Calculated metrics
    metrics = Column(JSON)  # Store calculated metrics

    # AI Analysis results
    ai_analysis = Column(JSON)  # Store structured AI analysis

    # Strategy documents (text extracted)
    strategy_context = Column(Text)
    design_criteria = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<OrgAnalysis(name='{self.name}', employees={self.employee_count})>"


class Scenario(Base):
    """A design option: the baseline organization plus an ordered list of design moves."""
    __tablename__ = "scenarios"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    analysis_id = Column(String(36), ForeignKey("org_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    source = Column(String(100), default="manual")  # e.g. "manual", "archetype:3_front_back_hybrid"
    moves = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Scenario(name='{self.name}', moves={len(self.moves or [])})>"


class Comparison(Base):
    """Weighted design criteria and judged scores for comparing options on one upload."""
    __tablename__ = "comparisons"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    analysis_id = Column(String(36), ForeignKey("org_analyses.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    criteria = Column(JSON, default=list)
    judgments = Column(JSON, default=dict)  # {option_id: {criterion_id: {score, rationale, source}}}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AIDisposition(Base):
    """Optional overlay: role of AI per job title for one upload."""
    __tablename__ = "ai_dispositions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    analysis_id = Column(String(36), ForeignKey("org_analyses.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    enabled = Column(Integer, default=1)  # 0 = hidden everywhere, tags kept
    roles = Column(JSON, default=dict)  # {job_title: {disposition, capacity_freed_pct, rationale, source, confidence}}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Engagement(Base):
    """
    Shared-workflow link between one upload and one Capability Compass workspace.

    One row per (upload, country). The row with country "" is the whole
    organization: it holds the strategy text waiting to be used, operating-model
    hypotheses, the grades and Compass links set on whole-organization findings,
    and the Compass-role to job-title matches. A country row holds that
    country's hand-off packet and the reasons recorded for its anchor roles.
    """
    __tablename__ = "engagements"
    __table_args__ = (UniqueConstraint("analysis_id", "country", name="uq_engagement_analysis_country"),)

    id = Column(String(36), primary_key=True, default=generate_uuid)
    analysis_id = Column(String(36), ForeignKey("org_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    country = Column(String(100), nullable=False, default="", server_default="")  # "" = whole organization
    key = Column(String(100))  # Compass engagement key, e.g. "MERIDIANBE"; None when no packet was imported
    packet = Column(JSON)  # the compass-handoff file as received
    imported_at = Column(DateTime)
    strategy_draft = Column(Text)  # pre-fills the strategy box on the archetype page
    hypotheses = Column(JSON, default=list)  # [{ref: "H1", statement, refuted_by, status, note}]
    hypothesis_seq = Column(Integer, default=0)  # last number used; never reused
    grades = Column(JSON, default=dict)  # {finding ref: confirmed|indicated|hypothesis} — the assessor's overrides
    relates = Column(JSON, default=dict)  # {finding ref: [Compass IDs]}
    role_matches = Column(JSON, default=dict)  # whole organization: {RL ref: [job titles]}, confirmed by the designer
    role_match_log = Column(JSON, default=list)  # whole organization: [{at, ref, before, after}]
    role_reasons = Column(JSON, default=dict)  # country: {RL ref: {reason_class, text, compared_with, grade}}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Setting(Base):
    """Application settings key-value store."""
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Setting(key='{self.key}')>"
