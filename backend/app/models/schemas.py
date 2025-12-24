"""
Pydantic schemas for API request/response validation.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# === Enums ===

class StatusEnum(str, Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"
    DRAFT = "draft"
    BASELINE = "baseline"
    ACTIVE = "active"
    ARCHIVED = "archived"


class SourceTypeEnum(str, Enum):
    PPTX = "pptx"
    CSV = "csv"
    EXCEL = "excel"
    HRIS_API = "hris_api"
    MANUAL = "manual"


# === Base Schemas ===

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# === Project Schemas ===

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    client_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    client_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    archived: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None


class ProjectResponse(BaseSchema):
    id: str
    name: str
    client_name: str
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    archived: bool
    settings: Optional[Dict[str, Any]]


class ProjectListResponse(BaseSchema):
    id: str
    name: str
    client_name: str
    created_at: datetime
    archived: bool
    dataset_count: Optional[int] = 0
    scenario_count: Optional[int] = 0


# === Dataset Schemas ===

class DatasetCreate(BaseModel):
    source_type: SourceTypeEnum
    source_filename: str


class DatasetResponse(BaseSchema):
    id: str
    project_id: str
    source_type: SourceTypeEnum
    source_filename: str
    uploaded_at: datetime
    validation_status: StatusEnum
    validation_errors: Optional[List[Dict[str, Any]]]
    parsed_employees: Optional[List[Dict[str, Any]]]
    parsed_relationships: Optional[List[List[str]]]


class DatasetPreview(BaseSchema):
    id: str
    source_filename: str
    total_employees: int
    total_relationships: int
    levels_detected: int
    outside_canvas_count: int
    validation_errors: List[Dict[str, Any]]
    sample_employees: List[Dict[str, Any]]


class ValidationError(BaseModel):
    error_type: str  # "cycle", "orphan", "duplicate", "missing_manager"
    severity: str  # "error", "warning", "info"
    message: str
    affected_nodes: List[str]
    suggested_fix: Optional[str] = None


class CorrectionRequest(BaseModel):
    corrections: List[Dict[str, Any]]


# === Scenario Schemas ===

class ScenarioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    parent_scenario_id: Optional[str] = None
    is_baseline: bool = False
    metadata: Optional[Dict[str, Any]] = None


class ScenarioUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[StatusEnum] = None
    metadata: Optional[Dict[str, Any]] = None


class ScenarioResponse(BaseSchema):
    id: str
    project_id: str
    name: str
    description: Optional[str]
    parent_scenario_id: Optional[str]
    status: StatusEnum
    created_at: datetime
    last_modified_at: datetime
    is_baseline: bool
    metadata: Optional[Dict[str, Any]] = Field(None, validation_alias="extra_data")
    employee_count: Optional[int] = 0


class ScenarioCloneRequest(BaseModel):
    new_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


# === Employee Schemas ===

class EmployeeCreate(BaseModel):
    employee_id: Optional[str] = None
    full_name: str = Field(..., min_length=1, max_length=255)
    job_title: str = Field(..., min_length=1, max_length=255)
    level: Optional[int] = None
    grade: Optional[str] = None
    manager_id: Optional[str] = None
    dotted_line_managers: Optional[List[str]] = None
    function: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    cost_center: Optional[str] = None
    fte: float = 1.0
    cost_base_salary: Optional[float] = None
    cost_variable: Optional[float] = None
    cost_benefits: Optional[float] = None
    cost_overhead_multiplier: float = 1.4
    currency: str = "USD"
    skills: Optional[List[Dict[str, Any]]] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    is_vacant: bool = False
    metadata: Optional[Dict[str, Any]] = None


class EmployeeUpdate(BaseModel):
    employee_id: Optional[str] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    job_title: Optional[str] = Field(None, min_length=1, max_length=255)
    level: Optional[int] = None
    grade: Optional[str] = None
    manager_id: Optional[str] = None
    dotted_line_managers: Optional[List[str]] = None
    function: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    cost_center: Optional[str] = None
    fte: Optional[float] = None
    cost_base_salary: Optional[float] = None
    cost_variable: Optional[float] = None
    cost_benefits: Optional[float] = None
    cost_overhead_multiplier: Optional[float] = None
    currency: Optional[str] = None
    skills: Optional[List[Dict[str, Any]]] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    is_vacant: Optional[bool] = None
    is_deleted: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class EmployeeResponse(BaseSchema):
    id: str
    scenario_id: str
    employee_id: Optional[str]
    full_name: str
    job_title: str
    level: Optional[int]
    grade: Optional[str]
    manager_id: Optional[str]
    dotted_line_managers: Optional[List[str]]
    function: Optional[str]
    department: Optional[str]
    location: Optional[str]
    cost_center: Optional[str]
    fte: float
    cost_base_salary: Optional[float]
    cost_variable: Optional[float]
    cost_benefits: Optional[float]
    cost_overhead_multiplier: float
    currency: str
    position_x: Optional[float]
    position_y: Optional[float]
    is_vacant: bool
    is_new: bool
    is_modified: bool
    is_deleted: bool
    direct_report_count: Optional[int] = 0


class EmployeeBulkUpdate(BaseModel):
    employee_ids: List[str]
    updates: EmployeeUpdate


# === Rate Card Schemas ===

class RateCardCreate(BaseModel):
    grade: str = Field(..., min_length=1, max_length=50)
    location: str = Field(..., min_length=1, max_length=100)
    function: Optional[str] = None
    base_salary_min: Optional[float] = None
    base_salary_mid: float = Field(..., gt=0)
    base_salary_max: Optional[float] = None
    variable_comp_target: float = 0
    benefits_value: float = 0
    overhead_multiplier: float = 1.4
    currency: str = "USD"
    source: Optional[str] = None
    notes: Optional[str] = None


class RateCardUpdate(BaseModel):
    base_salary_min: Optional[float] = None
    base_salary_mid: Optional[float] = Field(None, gt=0)
    base_salary_max: Optional[float] = None
    variable_comp_target: Optional[float] = None
    benefits_value: Optional[float] = None
    overhead_multiplier: Optional[float] = None
    source: Optional[str] = None
    notes: Optional[str] = None


class RateCardResponse(BaseSchema):
    id: str
    project_id: str
    grade: str
    location: str
    function: Optional[str]
    base_salary_min: Optional[float]
    base_salary_mid: float
    base_salary_max: Optional[float]
    variable_comp_target: float
    benefits_value: float
    overhead_multiplier: float
    currency: str
    effective_date: datetime
    source: Optional[str]


# === Metric Schemas ===

class MetricData(BaseModel):
    """Metric data without database fields - used for calculated results."""
    metric_type: str
    metric_category: Optional[str] = None
    value: float
    value_formatted: Optional[str] = None
    breakdown: Optional[Dict[str, Any]] = None
    benchmark_value: Optional[float] = None
    benchmark_source: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class MetricResponse(BaseSchema):
    id: str
    scenario_id: str
    metric_type: str
    metric_category: Optional[str]
    value: float
    value_formatted: Optional[str]
    breakdown: Optional[Dict[str, Any]]
    benchmark_value: Optional[float]
    benchmark_source: Optional[str]
    status: Optional[str]
    calculated_at: datetime


class MetricsSummary(BaseModel):
    total_headcount: int
    total_fte: float
    total_cost: float
    avg_span_of_control: float
    max_layers: int
    functions: List[str]
    locations: List[str]
    grade_distribution: Dict[str, int]
    metrics: List[MetricData]  # Use MetricData instead of MetricResponse


# === Analysis Schemas ===

class AnalysisRequest(BaseModel):
    scenario_id: str
    analysis_types: List[str] = ["structure", "pathology", "recommendations"]
    include_benchmarks: bool = True


class AnalysisResult(BaseModel):
    scenario_id: str
    analysis_type: str
    findings: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    generated_at: datetime


class ScenarioComparisonRequest(BaseModel):
    baseline_scenario_id: str
    target_scenario_id: str
    include_ai_narrative: bool = True


class ScenarioComparisonResult(BaseModel):
    baseline: Dict[str, Any]
    target: Dict[str, Any]
    delta: Dict[str, Any]
    node_changes: Dict[str, List[Dict[str, Any]]]  # added, removed, modified
    ai_narrative: Optional[str]
    generated_at: datetime


# === API Key Schemas ===

class APIKeyCreate(BaseModel):
    api_key: str = Field(..., min_length=10)
    provider: str = "anthropic"


class APIKeyResponse(BaseModel):
    id: str
    provider: str
    api_key_hint: str
    is_valid: bool
    last_validated_at: Optional[datetime]
    total_requests: int
    total_tokens_used: int


class APIKeyTestResult(BaseModel):
    is_valid: bool
    message: str
    model_available: Optional[str]


# === Pagination Schemas ===

class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: str = "desc"


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


# === Health Check ===

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    claude_api: str
