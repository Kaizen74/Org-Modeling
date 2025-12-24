"""
API Routes for Organizational Design Workbench.

Includes all REST API endpoints organized by resource:
- /projects - Project management
- /datasets - Dataset upload and validation
- /scenarios - Scenario management
- /employees - Employee CRUD
- /analysis - AI-powered analysis
- /metrics - Metrics calculation
- /comparison - Scenario comparison
- /api-key - API key management
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import uuid
import io
import json
import logging

from ..models.database import get_session
from ..models.models import (
    Project, Dataset, Scenario, Employee, RateCard, Metric, AuditLog,
    APIKeyConfig, StatusEnum, SourceTypeEnum
)
from ..models.schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse,
    DatasetResponse, DatasetPreview,
    ScenarioCreate, ScenarioUpdate, ScenarioResponse, ScenarioCloneRequest,
    EmployeeCreate, EmployeeUpdate, EmployeeResponse,
    RateCardCreate, RateCardUpdate, RateCardResponse,
    MetricData, MetricResponse, MetricsSummary,
    AnalysisRequest, AnalysisResult, ScenarioComparisonRequest, ScenarioComparisonResult,
    APIKeyCreate, APIKeyResponse, APIKeyTestResult,
    PaginationParams, PaginatedResponse, HealthResponse,
    CorrectionRequest, ValidationError,
)
from ..parsers import OrgChartParser, CSVParser, ExcelParser
from ..services.validation import OrgValidator
from ..services.metrics import MetricsCalculator
from ..services.claude_integration import ClaudeAnalysisService, ANTHROPIC_AVAILABLE
from ..services.comparison import ScenarioComparator

logger = logging.getLogger(__name__)

router = APIRouter()


# === Health Check ===

@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Check system health status."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        database="connected",
        claude_api="available" if ANTHROPIC_AVAILABLE else "unavailable",
    )


# === Projects ===

@router.post("/projects", response_model=ProjectResponse, tags=["Projects"])
async def create_project(
    project: ProjectCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new project."""
    db_project = Project(
        name=project.name,
        client_name=project.client_name,
        description=project.description,
        settings=project.settings or {},
    )
    session.add(db_project)
    await session.commit()
    await session.refresh(db_project)

    return ProjectResponse.model_validate(db_project)


@router.get("/projects", response_model=List[ProjectListResponse], tags=["Projects"])
async def list_projects(
    archived: bool = False,
    search: Optional[str] = None,
    limit: int = Query(50, le=100),
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    """List all projects with optional filtering."""
    query = select(Project).where(Project.archived == archived)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            (Project.name.ilike(search_term)) |
            (Project.client_name.ilike(search_term))
        )

    query = query.order_by(Project.created_at.desc()).offset(offset).limit(limit)

    result = await session.execute(query)
    projects = result.scalars().all()

    response = []
    for project in projects:
        # Count datasets and scenarios
        dataset_count = await session.execute(
            select(func.count(Dataset.id)).where(Dataset.project_id == project.id)
        )
        scenario_count = await session.execute(
            select(func.count(Scenario.id)).where(Scenario.project_id == project.id)
        )

        response.append(ProjectListResponse(
            id=project.id,
            name=project.name,
            client_name=project.client_name,
            created_at=project.created_at,
            archived=project.archived,
            dataset_count=dataset_count.scalar() or 0,
            scenario_count=scenario_count.scalar() or 0,
        ))

    return response


@router.get("/projects/{project_id}", response_model=ProjectResponse, tags=["Projects"])
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a specific project by ID."""
    result = await session.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return ProjectResponse.model_validate(project)


@router.patch("/projects/{project_id}", response_model=ProjectResponse, tags=["Projects"])
async def update_project(
    project_id: str,
    updates: ProjectUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update a project."""
    result = await session.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)

    await session.commit()
    await session.refresh(project)

    return ProjectResponse.model_validate(project)


@router.delete("/projects/{project_id}", tags=["Projects"])
async def delete_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Delete a project (soft delete by archiving)."""
    result = await session.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.archived = True
    await session.commit()

    return {"message": "Project archived successfully"}


# === Datasets ===

@router.post("/projects/{project_id}/datasets", response_model=DatasetResponse, tags=["Datasets"])
async def upload_dataset(
    project_id: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    """Upload and parse a dataset file (PPTX, CSV, or Excel)."""
    # Verify project exists
    result = await session.execute(
        select(Project).where(Project.id == project_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    # Determine file type
    filename = file.filename or "unknown"
    extension = filename.lower().split(".")[-1]

    if extension == "pptx":
        source_type = SourceTypeEnum.PPTX
    elif extension == "csv":
        source_type = SourceTypeEnum.CSV
    elif extension in ["xlsx", "xls"]:
        source_type = SourceTypeEnum.EXCEL
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {extension}. Supported: pptx, csv, xlsx"
        )

    # Read file content
    content = await file.read()

    # Parse based on type
    try:
        if source_type == SourceTypeEnum.PPTX:
            # Save to temp file for pptx parsing
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            parser = OrgChartParser(tmp_path)
            parse_result = parser.parse()
            raw_data = parse_result.to_dict()

            # Cleanup temp file
            import os
            os.unlink(tmp_path)

        elif source_type == SourceTypeEnum.CSV:
            parser = CSVParser()
            parse_result = parser.parse(content.decode("utf-8"))
            raw_data = parse_result.to_dict()
            logger.info(f"CSV parsed: {len(raw_data.get('employees', []))} employees, {len(raw_data.get('relationships', []))} relationships")

        elif source_type == SourceTypeEnum.EXCEL:
            parser = ExcelParser()
            parse_result = parser.parse(content)
            raw_data = parse_result.to_dict()

    except Exception as e:
        logger.exception(f"Failed to parse file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    # Run validation
    validator = OrgValidator()
    validation_result = validator.validate(
        raw_data.get("employees", []),
        [(r[0], r[1]) for r in raw_data.get("relationships", [])]
    )

    # Create dataset record
    dataset = Dataset(
        project_id=project_id,
        source_type=source_type,
        source_filename=filename,
        raw_data=raw_data,
        parsed_employees=raw_data.get("employees", []),
        parsed_relationships=raw_data.get("relationships", []),
        validation_status=(
            StatusEnum.VALIDATED if validation_result.is_valid
            else StatusEnum.PENDING
        ),
        validation_errors=validation_result.to_dict().get("errors", []) +
                         validation_result.to_dict().get("warnings", []),
    )

    session.add(dataset)
    await session.commit()
    await session.refresh(dataset)

    return DatasetResponse.model_validate(dataset)


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse, tags=["Datasets"])
async def get_dataset(
    dataset_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a dataset by ID."""
    result = await session.execute(
        select(Dataset).where(Dataset.id == dataset_id)
    )
    dataset = result.scalar_one_or_none()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return DatasetResponse.model_validate(dataset)


@router.get("/datasets/{dataset_id}/preview", response_model=DatasetPreview, tags=["Datasets"])
async def preview_dataset(
    dataset_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a preview of parsed dataset with sample data."""
    result = await session.execute(
        select(Dataset).where(Dataset.id == dataset_id)
    )
    dataset = result.scalar_one_or_none()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    employees = dataset.parsed_employees or []
    relationships = dataset.parsed_relationships or []

    # Calculate preview stats
    levels = set(emp.get("level", 0) for emp in employees)
    outside_count = sum(
        1 for emp in employees
        if emp.get("position", {}).get("left", 0) < 0
    )

    return DatasetPreview(
        id=dataset.id,
        source_filename=dataset.source_filename,
        total_employees=len(employees),
        total_relationships=len(relationships),
        levels_detected=len(levels),
        outside_canvas_count=outside_count,
        validation_errors=dataset.validation_errors or [],
        sample_employees=employees[:20],
    )


@router.post("/datasets/{dataset_id}/validate", tags=["Datasets"])
async def validate_dataset(
    dataset_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Re-run validation on a dataset."""
    result = await session.execute(
        select(Dataset).where(Dataset.id == dataset_id)
    )
    dataset = result.scalar_one_or_none()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Run validation
    validator = OrgValidator()
    validation_result = validator.validate(
        dataset.parsed_employees or [],
        [(r[0], r[1]) for r in (dataset.parsed_relationships or [])]
    )

    # Update dataset
    dataset.validation_status = (
        StatusEnum.VALIDATED if validation_result.is_valid
        else StatusEnum.PENDING
    )
    dataset.validation_errors = (
        validation_result.to_dict().get("errors", []) +
        validation_result.to_dict().get("warnings", [])
    )

    await session.commit()

    return validation_result.to_dict()


@router.patch("/datasets/{dataset_id}/corrections", tags=["Datasets"])
async def apply_corrections(
    dataset_id: str,
    corrections: CorrectionRequest,
    session: AsyncSession = Depends(get_session),
):
    """Apply user corrections to parsed data."""
    result = await session.execute(
        select(Dataset).where(Dataset.id == dataset_id)
    )
    dataset = result.scalar_one_or_none()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Apply corrections to parsed data
    employees = dataset.parsed_employees or []
    relationships = list(dataset.parsed_relationships or [])

    for correction in corrections.corrections:
        action = correction.get("action")
        node_id = correction.get("node_id")

        if action == "update_employee":
            # Update employee fields
            for emp in employees:
                if emp.get("id") == node_id:
                    for key, value in correction.get("updates", {}).items():
                        emp[key] = value
                    break

        elif action == "set_manager":
            # Update manager relationship
            manager_id = correction.get("manager_id")
            # Remove existing relationship
            relationships = [r for r in relationships if r[1] != node_id]
            # Add new relationship if manager specified
            if manager_id:
                relationships.append([manager_id, node_id])

        elif action == "remove_employee":
            # Remove employee and their relationships
            employees = [e for e in employees if e.get("id") != node_id]
            relationships = [
                r for r in relationships
                if r[0] != node_id and r[1] != node_id
            ]

    # Store corrections
    dataset.parsed_employees = employees
    dataset.parsed_relationships = relationships
    dataset.user_corrections = dataset.user_corrections or []
    dataset.user_corrections.extend(corrections.corrections)

    # Re-validate
    validator = OrgValidator()
    validation_result = validator.validate(
        employees,
        [(r[0], r[1]) for r in relationships]
    )

    dataset.validation_status = (
        StatusEnum.VALIDATED if validation_result.is_valid
        else StatusEnum.PENDING
    )
    dataset.validation_errors = (
        validation_result.to_dict().get("errors", []) +
        validation_result.to_dict().get("warnings", [])
    )

    await session.commit()

    return {
        "message": "Corrections applied",
        "validation": validation_result.to_dict(),
    }


@router.post("/datasets/{dataset_id}/publish", response_model=ScenarioResponse, tags=["Datasets"])
async def publish_dataset(
    dataset_id: str,
    scenario_name: str = Form(...),
    scenario_description: Optional[str] = Form(None),
    is_baseline: bool = Form(False),
    session: AsyncSession = Depends(get_session),
):
    """Publish validated dataset as a new scenario."""
    result = await session.execute(
        select(Dataset).where(Dataset.id == dataset_id)
    )
    dataset = result.scalar_one_or_none()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.validation_status != StatusEnum.VALIDATED:
        raise HTTPException(
            status_code=400,
            detail="Dataset must be validated before publishing"
        )

    # Create scenario
    scenario = Scenario(
        project_id=dataset.project_id,
        name=scenario_name,
        description=scenario_description,
        created_from_dataset_id=dataset.id,
        is_baseline=is_baseline,
        status=StatusEnum.ACTIVE,
    )
    session.add(scenario)
    await session.flush()

    # Create employees from parsed data
    id_mapping = {}  # Map old IDs to new UUIDs
    employees_with_manager_id = []  # Track employees that have manager_id in parsed data

    logger.info(f"Publishing dataset with {len(dataset.parsed_employees or [])} employees")
    logger.info(f"Dataset has {len(dataset.parsed_relationships or [])} parsed relationships")

    for emp_data in dataset.parsed_employees or []:
        old_id = emp_data.get("id")
        employee = Employee(
            scenario_id=scenario.id,
            employee_id=emp_data.get("employee_id"),
            full_name=emp_data.get("full_name", emp_data.get("name", "Unknown")),
            job_title=emp_data.get("job_title", emp_data.get("title", "Unknown")),
            level=emp_data.get("level"),
            grade=emp_data.get("grade"),
            function=emp_data.get("function"),
            department=emp_data.get("department"),
            location=emp_data.get("location"),
            cost_center=emp_data.get("cost_center"),
            fte=emp_data.get("fte", 1.0),
            cost_base_salary=emp_data.get("cost_base_salary"),
            cost_variable=emp_data.get("cost_variable"),
            position_x=emp_data.get("position", {}).get("center_x"),
            position_y=emp_data.get("position", {}).get("center_y"),
            source_shape_id=old_id,
            extra_data=emp_data.get("metadata", {}),
        )
        session.add(employee)
        await session.flush()
        id_mapping[old_id] = employee.id

        # Track if employee has manager_id in parsed data (from CSV)
        if emp_data.get("manager_id"):
            employees_with_manager_id.append((employee.id, emp_data.get("manager_id")))
            logger.debug(f"Employee {emp_data.get('full_name')} has manager_id: {emp_data.get('manager_id')}")

    logger.info(f"Created id_mapping with {len(id_mapping)} entries")
    logger.info(f"Found {len(employees_with_manager_id)} employees with manager_id in parsed data")

    # Set manager relationships from parsed_relationships (PPTX spatial inference)
    relationships_set = 0
    for rel in dataset.parsed_relationships or []:
        manager_old_id, employee_old_id = rel[0], rel[1]
        manager_new_id = id_mapping.get(manager_old_id)
        employee_new_id = id_mapping.get(employee_old_id)

        if manager_new_id and employee_new_id:
            # Update the employee's manager_id
            emp_result = await session.execute(
                select(Employee).where(Employee.id == employee_new_id)
            )
            employee = emp_result.scalar_one_or_none()
            if employee:
                employee.manager_id = manager_new_id
                relationships_set += 1

    logger.info(f"Set {relationships_set} manager relationships from parsed_relationships")

    # Also set manager relationships from employee's manager_id field (CSV direct reference)
    csv_relationships_set = 0
    for new_employee_id, old_manager_id in employees_with_manager_id:
        manager_new_id = id_mapping.get(old_manager_id)
        if manager_new_id:
            emp_result = await session.execute(
                select(Employee).where(Employee.id == new_employee_id)
            )
            employee = emp_result.scalar_one_or_none()
            if employee and not employee.manager_id:  # Don't overwrite if already set
                employee.manager_id = manager_new_id
                csv_relationships_set += 1
        else:
            logger.warning(f"Could not find manager mapping for old_id: {old_manager_id}")

    logger.info(f"Set {csv_relationships_set} additional manager relationships from CSV manager_id")

    # Update dataset with scenario reference
    dataset.published_to_scenario_id = scenario.id

    await session.commit()
    await session.refresh(scenario)

    # Count employees
    emp_count = await session.execute(
        select(func.count(Employee.id)).where(Employee.scenario_id == scenario.id)
    )

    response = ScenarioResponse.model_validate(scenario)
    response.employee_count = emp_count.scalar() or 0

    return response


# === Scenarios ===

@router.get("/projects/{project_id}/scenarios", response_model=List[ScenarioResponse], tags=["Scenarios"])
async def list_scenarios(
    project_id: str,
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """List all scenarios for a project."""
    query = select(Scenario).where(Scenario.project_id == project_id)

    if status:
        query = query.where(Scenario.status == status)

    query = query.order_by(Scenario.created_at.desc())

    result = await session.execute(query)
    scenarios = result.scalars().all()

    response = []
    for scenario in scenarios:
        emp_count = await session.execute(
            select(func.count(Employee.id)).where(Employee.scenario_id == scenario.id)
        )
        resp = ScenarioResponse.model_validate(scenario)
        resp.employee_count = emp_count.scalar() or 0
        response.append(resp)

    return response


@router.post("/projects/{project_id}/scenarios", response_model=ScenarioResponse, tags=["Scenarios"])
async def create_scenario(
    project_id: str,
    scenario: ScenarioCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new empty scenario."""
    # Verify project exists
    result = await session.execute(
        select(Project).where(Project.id == project_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    db_scenario = Scenario(
        project_id=project_id,
        name=scenario.name,
        description=scenario.description,
        parent_scenario_id=scenario.parent_scenario_id,
        is_baseline=scenario.is_baseline,
        extra_data=scenario.metadata or {},
    )

    session.add(db_scenario)
    await session.commit()
    await session.refresh(db_scenario)

    resp = ScenarioResponse.model_validate(db_scenario)
    resp.employee_count = 0

    return resp


@router.get("/scenarios/{scenario_id}", response_model=ScenarioResponse, tags=["Scenarios"])
async def get_scenario(
    scenario_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a scenario by ID."""
    result = await session.execute(
        select(Scenario).where(Scenario.id == scenario_id)
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    emp_count = await session.execute(
        select(func.count(Employee.id)).where(Employee.scenario_id == scenario.id)
    )

    resp = ScenarioResponse.model_validate(scenario)
    resp.employee_count = emp_count.scalar() or 0

    return resp


@router.get("/scenarios/{scenario_id}/employees", response_model=List[EmployeeResponse], tags=["Scenarios"])
async def get_scenario_employees(
    scenario_id: str,
    include_deleted: bool = False,
    session: AsyncSession = Depends(get_session),
):
    """Get all employees in a scenario."""
    query = select(Employee).where(Employee.scenario_id == scenario_id)

    if not include_deleted:
        query = query.where(Employee.is_deleted == False)

    query = query.order_by(Employee.level, Employee.full_name)

    result = await session.execute(query)
    employees = result.scalars().all()

    response = []
    for emp in employees:
        # Count direct reports
        report_count = await session.execute(
            select(func.count(Employee.id)).where(
                Employee.manager_id == emp.id,
                Employee.is_deleted == False
            )
        )
        resp = EmployeeResponse.model_validate(emp)
        resp.direct_report_count = report_count.scalar() or 0
        response.append(resp)

    return response


@router.get("/scenarios/{scenario_id}/tree", tags=["Scenarios"])
async def get_scenario_tree(
    scenario_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get scenario as hierarchical tree structure for visualization."""
    result = await session.execute(
        select(Employee).where(
            Employee.scenario_id == scenario_id,
            Employee.is_deleted == False
        )
    )
    employees = result.scalars().all()

    logger.info(f"Building tree for scenario {scenario_id}: {len(employees)} employees")

    # Count employees with manager_id set
    employees_with_manager = sum(1 for emp in employees if emp.manager_id)
    logger.info(f"Employees with manager_id set: {employees_with_manager}")

    # Build employee lookup and check if positions exist
    emp_by_id = {str(emp.id): emp for emp in employees}
    has_positions = any(emp.position_x is not None and emp.position_y is not None for emp in employees)

    # If no positions exist, calculate auto-layout based on hierarchy
    positions = {}
    if not has_positions and employees:
        positions = _calculate_org_layout(employees)

    # Build tree structure
    nodes = []
    edges = []

    for emp in employees:
        emp_id_str = str(emp.id)

        # Use calculated position or stored position
        if emp.id in positions:
            pos_x, pos_y = positions[emp.id]
        else:
            pos_x = emp.position_x or 0
            pos_y = emp.position_y or 0

        nodes.append({
            "id": emp_id_str,  # Convert UUID to string for JSON
            "data": {
                "label": emp.full_name,
                "title": emp.job_title,
                "level": emp.level,
                "function": emp.function,
                "location": emp.location,
                "grade": emp.grade,
                "is_vacant": emp.is_vacant,
                "is_new": emp.is_new,
                "is_modified": emp.is_modified,
            },
            "position": {
                "x": pos_x,
                "y": pos_y,
            },
        })

        if emp.manager_id:
            manager_id_str = str(emp.manager_id)
            edges.append({
                "id": f"e-{manager_id_str}-{emp_id_str}",
                "source": manager_id_str,
                "target": emp_id_str,
                "type": "smoothstep",
            })

    return {"nodes": nodes, "edges": edges}


def _calculate_org_layout(employees: list) -> dict:
    """
    Calculate auto-layout positions for org chart nodes.

    Uses a top-down tree layout algorithm:
    - Root nodes at top
    - Children positioned below their manager
    - Siblings spread horizontally
    """
    import networkx as nx

    # Build graph
    G = nx.DiGraph()
    for emp in employees:
        G.add_node(emp.id, employee=emp)

    for emp in employees:
        if emp.manager_id and emp.manager_id in G:
            G.add_edge(emp.manager_id, emp.id)

    # Find roots (nodes with no incoming edges)
    roots = [n for n in G.nodes() if G.in_degree(n) == 0]

    if not roots:
        # If no clear root, use employee with level 1 or lowest level
        min_level = min((emp.level or 99 for emp in employees), default=1)
        roots = [emp.id for emp in employees if (emp.level or 99) == min_level]

    # Layout parameters
    NODE_WIDTH = 220
    NODE_HEIGHT = 120
    HORIZONTAL_SPACING = 40
    VERTICAL_SPACING = 80

    positions = {}
    level_widths = {}  # Track width needed at each level

    def get_subtree_width(node_id: str, level: int) -> int:
        """Calculate total width needed for a subtree."""
        children = list(G.successors(node_id))
        if not children:
            return NODE_WIDTH

        total_width = sum(get_subtree_width(c, level + 1) for c in children)
        total_width += HORIZONTAL_SPACING * (len(children) - 1)
        return max(NODE_WIDTH, total_width)

    def layout_subtree(node_id: str, x: float, y: float, level: int):
        """Recursively layout a subtree."""
        positions[node_id] = (x, y)

        children = list(G.successors(node_id))
        if not children:
            return

        # Calculate total width needed for children
        child_widths = [get_subtree_width(c, level + 1) for c in children]
        total_children_width = sum(child_widths) + HORIZONTAL_SPACING * (len(children) - 1)

        # Start position for first child (centered under parent)
        start_x = x - total_children_width / 2 + child_widths[0] / 2
        child_y = y + NODE_HEIGHT + VERTICAL_SPACING

        current_x = start_x
        for i, child_id in enumerate(children):
            layout_subtree(child_id, current_x, child_y, level + 1)
            if i < len(children) - 1:
                current_x += child_widths[i] / 2 + HORIZONTAL_SPACING + child_widths[i + 1] / 2

    # Layout each root tree
    total_width = sum(get_subtree_width(r, 0) for r in roots)
    total_width += HORIZONTAL_SPACING * (len(roots) - 1) if len(roots) > 1 else 0

    start_x = -total_width / 2
    for i, root in enumerate(roots):
        root_width = get_subtree_width(root, 0)
        layout_subtree(root, start_x + root_width / 2, 0, 0)
        start_x += root_width + HORIZONTAL_SPACING

    # Handle orphan nodes (not connected to any root)
    orphans = [emp.id for emp in employees if emp.id not in positions]
    if orphans:
        orphan_y = max(pos[1] for pos in positions.values()) + NODE_HEIGHT + VERTICAL_SPACING * 2 if positions else 0
        for i, orphan_id in enumerate(orphans):
            positions[orphan_id] = (i * (NODE_WIDTH + HORIZONTAL_SPACING), orphan_y)

    return positions


@router.post("/scenarios/{scenario_id}/clone", response_model=ScenarioResponse, tags=["Scenarios"])
async def clone_scenario(
    scenario_id: str,
    clone_request: ScenarioCloneRequest,
    session: AsyncSession = Depends(get_session),
):
    """Clone a scenario for transformation."""
    result = await session.execute(
        select(Scenario).where(Scenario.id == scenario_id)
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Create new scenario
    new_scenario = Scenario(
        project_id=source.project_id,
        name=clone_request.new_name,
        description=clone_request.description or f"Cloned from {source.name}",
        parent_scenario_id=source.id,
        status=StatusEnum.DRAFT,
        extra_data=source.extra_data,
    )
    session.add(new_scenario)
    await session.flush()

    # Clone employees
    emp_result = await session.execute(
        select(Employee).where(Employee.scenario_id == source.id)
    )
    source_employees = emp_result.scalars().all()

    id_mapping = {}
    for emp in source_employees:
        new_emp = Employee(
            scenario_id=new_scenario.id,
            employee_id=emp.employee_id,
            full_name=emp.full_name,
            job_title=emp.job_title,
            level=emp.level,
            grade=emp.grade,
            function=emp.function,
            department=emp.department,
            location=emp.location,
            cost_center=emp.cost_center,
            fte=emp.fte,
            cost_base_salary=emp.cost_base_salary,
            cost_variable=emp.cost_variable,
            cost_benefits=emp.cost_benefits,
            cost_overhead_multiplier=emp.cost_overhead_multiplier,
            currency=emp.currency,
            position_x=emp.position_x,
            position_y=emp.position_y,
            skills=emp.skills,
            extra_data=emp.extra_data,
            source_shape_id=emp.source_shape_id,
            is_vacant=emp.is_vacant,
        )
        session.add(new_emp)
        await session.flush()
        id_mapping[emp.id] = new_emp.id

    # Update manager references
    for old_id, new_id in id_mapping.items():
        old_emp = next(e for e in source_employees if e.id == old_id)
        if old_emp.manager_id and old_emp.manager_id in id_mapping:
            new_emp_result = await session.execute(
                select(Employee).where(Employee.id == new_id)
            )
            new_emp = new_emp_result.scalar_one()
            new_emp.manager_id = id_mapping[old_emp.manager_id]

    await session.commit()
    await session.refresh(new_scenario)

    resp = ScenarioResponse.model_validate(new_scenario)
    resp.employee_count = len(source_employees)

    return resp


# === Employees ===

@router.post("/scenarios/{scenario_id}/employees", response_model=EmployeeResponse, tags=["Employees"])
async def create_employee(
    scenario_id: str,
    employee: EmployeeCreate,
    session: AsyncSession = Depends(get_session),
):
    """Add a new employee to a scenario."""
    # Verify scenario exists
    result = await session.execute(
        select(Scenario).where(Scenario.id == scenario_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Scenario not found")

    employee_data = employee.model_dump(exclude_unset=True)
    # Map metadata -> extra_data for SQLAlchemy model
    if "metadata" in employee_data:
        employee_data["extra_data"] = employee_data.pop("metadata")

    db_employee = Employee(
        scenario_id=scenario_id,
        is_new=True,
        **employee_data
    )

    session.add(db_employee)
    await session.commit()
    await session.refresh(db_employee)

    resp = EmployeeResponse.model_validate(db_employee)
    resp.direct_report_count = 0

    return resp


@router.patch("/scenarios/{scenario_id}/employees/{employee_id}", response_model=EmployeeResponse, tags=["Employees"])
async def update_employee(
    scenario_id: str,
    employee_id: str,
    updates: EmployeeUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update an employee."""
    result = await session.execute(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.scenario_id == scenario_id
        )
    )
    employee = result.scalar_one_or_none()

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    update_data = updates.model_dump(exclude_unset=True)
    # Map metadata -> extra_data for SQLAlchemy model
    if "metadata" in update_data:
        update_data["extra_data"] = update_data.pop("metadata")

    for key, value in update_data.items():
        setattr(employee, key, value)

    employee.is_modified = True

    await session.commit()
    await session.refresh(employee)

    # Count direct reports
    report_count = await session.execute(
        select(func.count(Employee.id)).where(Employee.manager_id == employee.id)
    )

    resp = EmployeeResponse.model_validate(employee)
    resp.direct_report_count = report_count.scalar() or 0

    return resp


@router.delete("/scenarios/{scenario_id}/employees/{employee_id}", tags=["Employees"])
async def delete_employee(
    scenario_id: str,
    employee_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Delete an employee (soft delete for comparison tracking)."""
    result = await session.execute(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.scenario_id == scenario_id
        )
    )
    employee = result.scalar_one_or_none()

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    employee.is_deleted = True
    await session.commit()

    return {"message": "Employee deleted"}


# === Metrics ===

@router.post("/scenarios/{scenario_id}/calculate-metrics", response_model=MetricsSummary, tags=["Metrics"])
async def calculate_scenario_metrics(
    scenario_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Calculate and store metrics for a scenario."""
    # Get scenario
    result = await session.execute(
        select(Scenario).where(Scenario.id == scenario_id)
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Get employees
    emp_result = await session.execute(
        select(Employee).where(
            Employee.scenario_id == scenario_id,
            Employee.is_deleted == False
        )
    )
    employees = emp_result.scalars().all()

    # Build relationships from manager_id
    employee_dicts = [
        {
            "id": emp.id,
            "employee_id": emp.employee_id,
            "full_name": emp.full_name,
            "job_title": emp.job_title,
            "level": emp.level,
            "grade": emp.grade,
            "function": emp.function,
            "location": emp.location,
            "fte": emp.fte,
            "cost_base_salary": emp.cost_base_salary,
            "cost_variable": emp.cost_variable,
            "cost_benefits": emp.cost_benefits,
            "cost_overhead_multiplier": emp.cost_overhead_multiplier,
            "manager_id": emp.manager_id,
        }
        for emp in employees
    ]

    relationships = [
        (emp["manager_id"], emp["id"])
        for emp in employee_dicts
        if emp.get("manager_id")
    ]

    # Calculate metrics
    calculator = MetricsCalculator()
    report = calculator.calculate_all(employee_dicts, relationships)

    # Store metrics in database
    # First delete existing metrics
    await session.execute(
        select(Metric).where(Metric.scenario_id == scenario_id)
    )

    for metric_data in report.metrics:
        metric = Metric(
            scenario_id=scenario_id,
            metric_type=metric_data.metric_type,
            metric_category=metric_data.metric_category,
            value=metric_data.value,
            value_formatted=metric_data.value_formatted,
            breakdown=metric_data.breakdown,
            benchmark_value=metric_data.benchmark_value,
            benchmark_source=metric_data.benchmark_source,
            status=metric_data.status,
        )
        session.add(metric)

    await session.commit()

    return MetricsSummary(
        total_headcount=report.summary.get("total_headcount", 0),
        total_fte=report.summary.get("total_fte", 0),
        total_cost=report.summary.get("total_cost", 0),
        avg_span_of_control=report.summary.get("span_of_control_avg", 0),
        max_layers=report.summary.get("hierarchy_depth", 0),
        functions=list(set(e.function or "Unknown" for e in employees)),
        locations=list(set(e.location or "Unknown" for e in employees)),
        grade_distribution={},
        metrics=[MetricData.model_validate(m) for m in report.metrics],
    )


@router.get("/scenarios/{scenario_id}/metrics", response_model=List[MetricResponse], tags=["Metrics"])
async def get_scenario_metrics(
    scenario_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get stored metrics for a scenario."""
    result = await session.execute(
        select(Metric).where(Metric.scenario_id == scenario_id)
    )
    metrics = result.scalars().all()

    return [MetricResponse.model_validate(m) for m in metrics]


# === Analysis ===

@router.post("/scenarios/{scenario_id}/analyze", tags=["Analysis"])
async def analyze_scenario(
    scenario_id: str,
    api_key: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """Run AI-powered analysis on a scenario."""
    if not ANTHROPIC_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="AI analysis unavailable: anthropic package not installed"
        )

    # Get scenario and employees
    result = await session.execute(
        select(Scenario).where(Scenario.id == scenario_id)
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    emp_result = await session.execute(
        select(Employee).where(
            Employee.scenario_id == scenario_id,
            Employee.is_deleted == False
        )
    )
    employees = emp_result.scalars().all()

    # Build org data
    employee_dicts = [
        {
            "id": emp.id,
            "full_name": emp.full_name,
            "job_title": emp.job_title,
            "level": emp.level,
            "grade": emp.grade,
            "function": emp.function,
            "location": emp.location,
            "manager_id": emp.manager_id,
        }
        for emp in employees
    ]

    relationships = [
        (emp["manager_id"], emp["id"])
        for emp in employee_dicts
        if emp.get("manager_id")
    ]

    org_data = {
        "employees": employee_dicts,
        "relationships": relationships,
    }

    # Get metrics
    metrics_result = await session.execute(
        select(Metric).where(Metric.scenario_id == scenario_id)
    )
    metrics = metrics_result.scalars().all()
    metrics_data = {
        "metrics": [
            {
                "metric_type": m.metric_type,
                "value": m.value,
                "status": m.status,
            }
            for m in metrics
        ]
    }

    # Run analysis
    try:
        service = ClaudeAnalysisService(api_key=api_key)
        results = service.run_comprehensive_analysis(org_data, metrics_data)

        return {
            "success": True,
            "analyses": {
                key: result.to_dict()
                for key, result in results.items()
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# === Comparison ===

@router.post("/scenarios/compare", tags=["Comparison"])
async def compare_scenarios(
    request: ScenarioComparisonRequest,
    api_key: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """Compare two scenarios and generate delta analysis."""
    # Get both scenarios
    baseline_result = await session.execute(
        select(Scenario).where(Scenario.id == request.baseline_scenario_id)
    )
    baseline = baseline_result.scalar_one_or_none()

    target_result = await session.execute(
        select(Scenario).where(Scenario.id == request.target_scenario_id)
    )
    target = target_result.scalar_one_or_none()

    if not baseline or not target:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Get employees for both
    async def get_employees(scenario_id: str):
        result = await session.execute(
            select(Employee).where(
                Employee.scenario_id == scenario_id,
                Employee.is_deleted == False
            )
        )
        employees = result.scalars().all()
        return [
            {
                "id": emp.id,
                "employee_id": emp.employee_id,
                "full_name": emp.full_name,
                "job_title": emp.job_title,
                "level": emp.level,
                "grade": emp.grade,
                "function": emp.function,
                "location": emp.location,
                "manager_id": emp.manager_id,
                "fte": emp.fte,
                "cost_base_salary": emp.cost_base_salary,
                "cost_variable": emp.cost_variable,
                "cost_benefits": emp.cost_benefits,
                "cost_overhead_multiplier": emp.cost_overhead_multiplier,
            }
            for emp in employees
        ]

    baseline_employees = await get_employees(baseline.id)
    target_employees = await get_employees(target.id)

    # Get metrics for both
    async def get_metrics(scenario_id: str):
        result = await session.execute(
            select(Metric).where(Metric.scenario_id == scenario_id)
        )
        return {
            "metrics": [
                {"metric_type": m.metric_type, "value": m.value}
                for m in result.scalars().all()
            ]
        }

    baseline_metrics = await get_metrics(baseline.id)
    target_metrics = await get_metrics(target.id)

    # Run comparison
    comparator = ScenarioComparator()
    comparison = comparator.compare(
        {"id": baseline.id, "name": baseline.name, "employees": baseline_employees},
        {"id": target.id, "name": target.name, "employees": target_employees},
        baseline_metrics,
        target_metrics,
    )

    # Generate AI narrative if requested
    if request.include_ai_narrative and ANTHROPIC_AVAILABLE and api_key:
        try:
            service = ClaudeAnalysisService(api_key=api_key)
            narrative_result = service.generate_comparison_narrative(
                {"name": baseline.name, "employees": baseline_employees, "metrics": baseline_metrics},
                {"name": target.name, "employees": target_employees, "metrics": target_metrics},
                comparison.summary,
            )
            comparison.ai_narrative = narrative_result.narrative
        except Exception as e:
            logger.warning(f"Failed to generate narrative: {e}")

    return comparison.to_dict()


# === Rate Cards (Job Grades & Salaries) ===

@router.get("/projects/{project_id}/rate-cards", response_model=List[RateCardResponse], tags=["Rate Cards"])
async def list_rate_cards(
    project_id: str,
    session: AsyncSession = Depends(get_session),
):
    """List all rate cards (job grades and salaries) for a project."""
    result = await session.execute(
        select(RateCard).where(RateCard.project_id == project_id).order_by(RateCard.grade)
    )
    rate_cards = result.scalars().all()

    return [RateCardResponse.model_validate(rc) for rc in rate_cards]


@router.post("/projects/{project_id}/rate-cards", response_model=RateCardResponse, tags=["Rate Cards"])
async def create_rate_card(
    project_id: str,
    rate_card: RateCardCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new rate card (job grade with salary information)."""
    # Verify project exists
    result = await session.execute(
        select(Project).where(Project.id == project_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    db_rate_card = RateCard(
        project_id=project_id,
        **rate_card.model_dump(exclude_unset=True)
    )

    session.add(db_rate_card)
    await session.commit()
    await session.refresh(db_rate_card)

    return RateCardResponse.model_validate(db_rate_card)


@router.post("/projects/{project_id}/rate-cards/bulk", response_model=List[RateCardResponse], tags=["Rate Cards"])
async def bulk_create_rate_cards(
    project_id: str,
    rate_cards: List[RateCardCreate],
    session: AsyncSession = Depends(get_session),
):
    """Bulk create/update rate cards for efficient entry."""
    # Verify project exists
    result = await session.execute(
        select(Project).where(Project.id == project_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    created = []
    for rc_data in rate_cards:
        # Check if rate card with same grade/location exists
        existing = await session.execute(
            select(RateCard).where(
                RateCard.project_id == project_id,
                RateCard.grade == rc_data.grade,
                RateCard.location == rc_data.location,
            )
        )
        existing_rc = existing.scalar_one_or_none()

        if existing_rc:
            # Update existing
            for key, value in rc_data.model_dump(exclude_unset=True).items():
                setattr(existing_rc, key, value)
            await session.flush()
            await session.refresh(existing_rc)
            created.append(existing_rc)
        else:
            # Create new
            db_rate_card = RateCard(
                project_id=project_id,
                **rc_data.model_dump(exclude_unset=True)
            )
            session.add(db_rate_card)
            await session.flush()
            await session.refresh(db_rate_card)
            created.append(db_rate_card)

    await session.commit()

    return [RateCardResponse.model_validate(rc) for rc in created]


@router.patch("/rate-cards/{rate_card_id}", response_model=RateCardResponse, tags=["Rate Cards"])
async def update_rate_card(
    rate_card_id: str,
    updates: RateCardUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update a rate card."""
    result = await session.execute(
        select(RateCard).where(RateCard.id == rate_card_id)
    )
    rate_card = result.scalar_one_or_none()

    if not rate_card:
        raise HTTPException(status_code=404, detail="Rate card not found")

    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rate_card, key, value)

    await session.commit()
    await session.refresh(rate_card)

    return RateCardResponse.model_validate(rate_card)


@router.delete("/rate-cards/{rate_card_id}", tags=["Rate Cards"])
async def delete_rate_card(
    rate_card_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Delete a rate card."""
    result = await session.execute(
        select(RateCard).where(RateCard.id == rate_card_id)
    )
    rate_card = result.scalar_one_or_none()

    if not rate_card:
        raise HTTPException(status_code=404, detail="Rate card not found")

    await session.delete(rate_card)
    await session.commit()

    return {"message": "Rate card deleted"}


# === API Key Management ===

@router.post("/api-key/test", response_model=APIKeyTestResult, tags=["Settings"])
async def test_api_key(
    api_key: APIKeyCreate,
):
    """Test if a Claude API key is valid."""
    if not ANTHROPIC_AVAILABLE:
        return APIKeyTestResult(
            is_valid=False,
            message="anthropic package not installed",
            model_available=None,
        )

    service = ClaudeAnalysisService()
    result = service.validate_api_key(api_key.api_key)

    return APIKeyTestResult(**result)


@router.post("/api-key/save", response_model=APIKeyResponse, tags=["Settings"])
async def save_api_key(
    api_key: APIKeyCreate,
    project_id: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """Save an API key configuration."""
    # Validate key first
    if ANTHROPIC_AVAILABLE:
        service = ClaudeAnalysisService()
        validation = service.validate_api_key(api_key.api_key)
        is_valid = validation.get("is_valid", False)
    else:
        is_valid = False

    # Create or update config
    config = APIKeyConfig(
        project_id=project_id,
        provider=api_key.provider,
        api_key_encrypted=api_key.api_key,  # TODO: Encrypt in production
        api_key_hint=api_key.api_key[-4:] if len(api_key.api_key) >= 4 else "****",
        is_valid=is_valid,
    )

    session.add(config)
    await session.commit()
    await session.refresh(config)

    return APIKeyResponse(
        id=config.id,
        provider=config.provider,
        api_key_hint=config.api_key_hint,
        is_valid=config.is_valid,
        last_validated_at=config.last_validated_at,
        total_requests=config.total_requests,
        total_tokens_used=config.total_tokens_used,
    )


@router.get("/api-key", response_model=Optional[APIKeyResponse], tags=["Settings"])
async def get_api_key(
    project_id: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """Get current API key configuration."""
    query = select(APIKeyConfig)
    if project_id:
        query = query.where(APIKeyConfig.project_id == project_id)

    result = await session.execute(query.order_by(APIKeyConfig.created_at.desc()).limit(1))
    config = result.scalar_one_or_none()

    if not config:
        return None

    return APIKeyResponse(
        id=config.id,
        provider=config.provider,
        api_key_hint=config.api_key_hint,
        is_valid=config.is_valid,
        last_validated_at=config.last_validated_at,
        total_requests=config.total_requests,
        total_tokens_used=config.total_tokens_used,
    )
