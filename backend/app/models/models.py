"""SQLAlchemy models for the Org Design Analyzer."""

from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON
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


class Setting(Base):
    """Application settings key-value store."""
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Setting(key='{self.key}')>"
