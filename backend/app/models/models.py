"""
SQLAlchemy models for Organizational Design Workbench.

Core entities:
- Project: Top-level container for client engagements
- Dataset: Uploaded files (PPTX, CSV, Excel) with parsed data
- Scenario: Versioned org structures (As-Is, To-Be)
- Employee: Individual org chart nodes
- RateCard: Cost benchmarks by grade/location
- Metric: Calculated org health metrics
- AuditLog: Change tracking for compliance
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    Enum,
    Index,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from .database import Base


def generate_uuid():
    """Generate a new UUID as string for SQLite compatibility."""
    return str(uuid.uuid4())


class StatusEnum(str, enum.Enum):
    """Status for datasets and scenarios."""
    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"
    DRAFT = "draft"
    BASELINE = "baseline"
    ACTIVE = "active"
    ARCHIVED = "archived"


class SourceTypeEnum(str, enum.Enum):
    """Source file types for datasets."""
    PPTX = "pptx"
    CSV = "csv"
    EXCEL = "excel"
    HRIS_API = "hris_api"
    MANUAL = "manual"


# === Core Entities ===

class Project(Base):
    """
    Top-level container for organizational design engagements.
    Each project belongs to a client and contains datasets, scenarios, and rate cards.
    """
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, index=True)
    client_name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner_id = Column(String(36))  # FK to User (future auth implementation)
    archived = Column(Boolean, default=False, index=True)
    settings = Column(JSON, default=dict)  # Project-level configuration

    # Relationships
    datasets = relationship(
        "Dataset",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    scenarios = relationship(
        "Scenario",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    rate_cards = relationship(
        "RateCard",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}', client='{self.client_name}')>"


class Dataset(Base):
    """
    Uploaded source files with parsed organizational data.
    Supports staging workflow: upload → validate → correct → publish to scenario.
    """
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    source_type = Column(Enum(SourceTypeEnum), nullable=False)
    source_filename = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, index=True)
    raw_data = Column(JSON)  # Original parsed structure from parser
    parsed_employees = Column(JSON)  # Extracted employee nodes
    parsed_relationships = Column(JSON)  # Manager-employee edges
    validation_status = Column(Enum(StatusEnum), default=StatusEnum.PENDING, index=True)
    validation_errors = Column(JSON, default=list)  # List of validation issues
    user_corrections = Column(JSON, default=list)  # Manual fixes applied
    published_to_scenario_id = Column(String(36), ForeignKey("scenarios.id"))

    # Relationships
    project = relationship("Project", back_populates="datasets")

    __table_args__ = (
        Index("idx_dataset_project_status", "project_id", "validation_status"),
    )

    def __repr__(self):
        return f"<Dataset(id={self.id}, file='{self.source_filename}', status={self.validation_status})>"


class Scenario(Base):
    """
    Versioned organizational structure.
    Supports cloning for what-if analysis and parent-child relationships for version history.
    """
    __tablename__ = "scenarios"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    parent_scenario_id = Column(String(36), ForeignKey("scenarios.id"))  # For versioning
    created_from_dataset_id = Column(String(36), ForeignKey("datasets.id"))
    status = Column(Enum(StatusEnum), default=StatusEnum.DRAFT, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata = Column(JSON, default=dict)  # Tags, notes, assumptions
    is_baseline = Column(Boolean, default=False)  # Flag for "As-Is" scenarios

    # Relationships
    project = relationship("Project", back_populates="scenarios")
    employees = relationship(
        "Employee",
        back_populates="scenario",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    metrics = relationship(
        "Metric",
        back_populates="scenario",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    parent_scenario = relationship(
        "Scenario",
        remote_side=[id],
        backref="child_scenarios"
    )

    __table_args__ = (
        Index("idx_scenario_project_status", "project_id", "status"),
    )

    def __repr__(self):
        return f"<Scenario(id={self.id}, name='{self.name}', status={self.status})>"


class Employee(Base):
    """
    Individual organizational unit (person, role, or position).
    Supports hierarchical relationships, matrix reporting, and cost modeling.
    """
    __tablename__ = "employees"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    scenario_id = Column(String(36), ForeignKey("scenarios.id"), nullable=False, index=True)

    # Identity
    employee_id = Column(String(50), index=True)  # External ID (e.g., "EMP-12345")
    full_name = Column(String(255), nullable=False)
    job_title = Column(String(255), nullable=False)

    # Hierarchy
    level = Column(Integer, index=True)  # Hierarchy level (1=CEO)
    grade = Column(String(50), index=True)  # e.g., "L7", "Director", "VP"
    manager_id = Column(String(36), ForeignKey("employees.id"))  # Self-referencing
    dotted_line_managers = Column(JSON, default=list)  # Array of employee IDs for matrix reporting

    # Organization
    function = Column(String(100), index=True)  # e.g., "Engineering", "Sales", "HR"
    department = Column(String(100))  # Sub-function
    location = Column(String(100), index=True)  # e.g., "Singapore", "London"
    cost_center = Column(String(50))

    # Capacity
    fte = Column(Float, default=1.0)  # Full-time equivalent
    headcount = Column(Integer, default=1)  # For aggregate nodes

    # Costs (optional, can use RateCard lookup)
    cost_base_salary = Column(Float)
    cost_variable = Column(Float)
    cost_benefits = Column(Float)
    cost_overhead_multiplier = Column(Float, default=1.4)
    currency = Column(String(3), default="USD")

    # Skills & Competencies
    skills = Column(JSON, default=list)  # Array of skill objects

    # Visual positioning (for org chart rendering)
    position_x = Column(Float)  # Canvas X coordinate
    position_y = Column(Float)  # Canvas Y coordinate

    # Metadata
    metadata = Column(JSON, default=dict)  # Custom attributes
    source_shape_id = Column(String(100))  # Original PPTX shape reference

    # Flags
    is_vacant = Column(Boolean, default=False)  # Open position
    is_new = Column(Boolean, default=False)  # Added in transformation
    is_modified = Column(Boolean, default=False)  # Changed from baseline
    is_deleted = Column(Boolean, default=False)  # Soft delete for comparison

    # Relationships
    scenario = relationship("Scenario", back_populates="employees")
    direct_reports = relationship(
        "Employee",
        backref="manager",
        remote_side=[id],
        lazy="selectin"
    )

    __table_args__ = (
        Index("idx_employee_scenario_level", "scenario_id", "level"),
        Index("idx_employee_scenario_function", "scenario_id", "function"),
        Index("idx_employee_manager", "scenario_id", "manager_id"),
    )

    def __repr__(self):
        return f"<Employee(id={self.id}, name='{self.full_name}', title='{self.job_title}')>"

    @property
    def total_cost(self) -> float:
        """Calculate total loaded cost for this employee."""
        base = self.cost_base_salary or 0
        variable = self.cost_variable or 0
        benefits = self.cost_benefits or 0
        multiplier = self.cost_overhead_multiplier or 1.0
        return (base + variable + benefits) * multiplier * (self.fte or 1.0)


class RateCard(Base):
    """
    Cost benchmarks by grade and location.
    Used for costing new/modified positions and scenario comparison.
    """
    __tablename__ = "rate_cards"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)

    # Dimensions
    grade = Column(String(50), nullable=False, index=True)
    location = Column(String(100), nullable=False, index=True)
    function = Column(String(100))  # Optional function-specific rates

    # Compensation
    base_salary_min = Column(Float)
    base_salary_mid = Column(Float, nullable=False)  # Market rate
    base_salary_max = Column(Float)
    variable_comp_target = Column(Float, default=0)  # Target bonus %
    benefits_value = Column(Float, default=0)
    overhead_multiplier = Column(Float, default=1.4)

    # Currency & Validity
    currency = Column(String(3), default="USD")  # ISO 4217
    effective_date = Column(DateTime, default=datetime.utcnow)
    expiry_date = Column(DateTime)

    # Source
    source = Column(String(255))  # e.g., "Mercer 2024", "Internal Comp Team"
    notes = Column(Text)

    # Relationships
    project = relationship("Project", back_populates="rate_cards")

    __table_args__ = (
        Index("idx_ratecard_lookup", "project_id", "grade", "location"),
    )

    def __repr__(self):
        return f"<RateCard(grade='{self.grade}', location='{self.location}', mid={self.base_salary_mid})>"

    @property
    def total_cost_mid(self) -> float:
        """Calculate total loaded cost at market midpoint."""
        base = self.base_salary_mid or 0
        variable = base * (self.variable_comp_target or 0)
        benefits = self.benefits_value or 0
        return (base + variable + benefits) * (self.overhead_multiplier or 1.0)


class Metric(Base):
    """
    Calculated organizational health metrics for a scenario.
    Stores both aggregate values and detailed breakdowns.
    """
    __tablename__ = "metrics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    scenario_id = Column(String(36), ForeignKey("scenarios.id"), nullable=False, index=True)

    # Metric identification
    metric_type = Column(String(100), nullable=False, index=True)
    metric_category = Column(String(50))  # "structure", "cost", "complexity", "health"

    # Values
    value = Column(Float, nullable=False)
    value_formatted = Column(String(100))  # Human-readable (e.g., "4.2:1", "$1.2M")

    # Breakdown
    breakdown = Column(JSON, default=dict)  # Detailed calculations by segment

    # Benchmarks
    benchmark_value = Column(Float)
    benchmark_source = Column(String(255))
    status = Column(String(20))  # "healthy", "warning", "critical"

    # Timestamps
    calculated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    scenario = relationship("Scenario", back_populates="metrics")

    __table_args__ = (
        Index("idx_metric_scenario_type", "scenario_id", "metric_type"),
    )

    def __repr__(self):
        return f"<Metric(type='{self.metric_type}', value={self.value})>"


class AuditLog(Base):
    """
    Change tracking for compliance and undo functionality.
    Records all modifications to entities.
    """
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Entity reference
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(String(36), nullable=False, index=True)

    # Action details
    action = Column(String(50), nullable=False, index=True)  # "created", "updated", "deleted", "cloned"

    # User tracking
    user_id = Column(String(36))
    user_email = Column(String(255))

    # Change data
    changes = Column(JSON)  # Before/after snapshot
    reason = Column(Text)  # Optional explanation

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Context
    session_id = Column(String(36))  # Group related changes
    ip_address = Column(String(45))

    __table_args__ = (
        Index("idx_audit_entity", "entity_type", "entity_id"),
        Index("idx_audit_timestamp", "timestamp"),
    )

    def __repr__(self):
        return f"<AuditLog(entity={self.entity_type}, action={self.action}, time={self.timestamp})>"


class APIKeyConfig(Base):
    """
    Store user's Claude API key configuration.
    Encrypted storage for production use.
    """
    __tablename__ = "api_key_configs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), index=True)

    # API Configuration
    provider = Column(String(50), default="anthropic")  # Future: support other LLMs
    api_key_encrypted = Column(String(500))  # Encrypted API key
    api_key_hint = Column(String(20))  # Last 4 chars for display

    # Status
    is_valid = Column(Boolean, default=False)
    last_validated_at = Column(DateTime)
    last_error = Column(Text)

    # Usage tracking
    total_requests = Column(Integer, default=0)
    total_tokens_used = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<APIKeyConfig(provider='{self.provider}', hint='...{self.api_key_hint}')>"
