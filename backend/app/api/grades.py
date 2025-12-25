"""Grade and Salary Configuration API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Dict
from pydantic import BaseModel

from ..models.database import get_session
from ..models.models import GradeSalary

router = APIRouter(prefix="/api/v1/grades", tags=["grades"])


class GradeSalaryCreate(BaseModel):
    grade: str
    median_salary: float
    currency: str = "SGD"
    display_order: int = 99


class GradeSalaryUpdate(BaseModel):
    median_salary: float
    currency: str = "SGD"
    display_order: int = 99


class GradeSalaryResponse(BaseModel):
    id: str
    grade: str
    median_salary: float
    currency: str
    display_order: int

    class Config:
        from_attributes = True


class BulkImportData(BaseModel):
    grades: Dict[str, float]
    currency: str = "SGD"


@router.get("/", response_model=List[GradeSalaryResponse])
async def list_grades(db: AsyncSession = Depends(get_session)):
    """List all grade configurations ordered by display_order."""
    result = await db.execute(
        select(GradeSalary).order_by(GradeSalary.display_order)
    )
    return result.scalars().all()


@router.post("/", response_model=GradeSalaryResponse)
async def create_grade(
    data: GradeSalaryCreate,
    db: AsyncSession = Depends(get_session)
):
    """Create a new grade configuration."""
    # Check for duplicate
    result = await db.execute(
        select(GradeSalary).where(GradeSalary.grade == data.grade)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Grade '{data.grade}' already exists"
        )

    grade = GradeSalary(**data.model_dump())
    db.add(grade)
    await db.commit()
    await db.refresh(grade)
    return grade


@router.put("/{grade_id}", response_model=GradeSalaryResponse)
async def update_grade(
    grade_id: str,
    data: GradeSalaryUpdate,
    db: AsyncSession = Depends(get_session)
):
    """Update a grade configuration."""
    result = await db.execute(
        select(GradeSalary).where(GradeSalary.id == grade_id)
    )
    grade = result.scalar_one_or_none()
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")

    grade.median_salary = data.median_salary
    grade.currency = data.currency
    grade.display_order = data.display_order
    await db.commit()
    await db.refresh(grade)
    return grade


@router.delete("/{grade_id}")
async def delete_grade(grade_id: str, db: AsyncSession = Depends(get_session)):
    """Delete a grade configuration."""
    result = await db.execute(
        select(GradeSalary).where(GradeSalary.id == grade_id)
    )
    grade = result.scalar_one_or_none()
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")

    await db.delete(grade)
    await db.commit()
    return {"message": f"Grade '{grade.grade}' deleted"}


@router.post("/bulk-import")
async def bulk_import(
    data: BulkImportData,
    db: AsyncSession = Depends(get_session)
):
    """Bulk import grades from parsed CSV data."""
    imported = 0
    updated = 0

    for order, (grade, salary) in enumerate(data.grades.items(), 1):
        result = await db.execute(
            select(GradeSalary).where(GradeSalary.grade == grade)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.median_salary = salary
            existing.currency = data.currency
            existing.display_order = order
            updated += 1
        else:
            new_grade = GradeSalary(
                grade=grade,
                median_salary=salary,
                currency=data.currency,
                display_order=order
            )
            db.add(new_grade)
            imported += 1

    await db.commit()
    return {
        "message": f"Imported {imported} new grades, updated {updated} existing",
        "total": imported + updated
    }


@router.delete("/")
async def clear_all_grades(db: AsyncSession = Depends(get_session)):
    """Clear all grade configurations."""
    await db.execute(delete(GradeSalary))
    await db.commit()
    return {"message": "All grades cleared"}


@router.get("/order-map")
async def get_grade_order_map(db: AsyncSession = Depends(get_session)):
    """Get a map of grades to their display order (for gap calculations)."""
    result = await db.execute(
        select(GradeSalary).order_by(GradeSalary.display_order)
    )
    grades = result.scalars().all()
    return {g.grade: g.display_order for g in grades}
