"""Tests for grades API."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_grades_empty(client: AsyncClient):
    """Test listing grades when empty."""
    response = await client.get("/api/v1/grades/")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_grade(client: AsyncClient):
    """Test creating a grade."""
    response = await client.post(
        "/api/v1/grades/",
        json={
            "grade": "SVP",
            "median_salary": 350000,
            "currency": "SGD",
            "display_order": 1
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["grade"] == "SVP"
    assert data["median_salary"] == 350000


@pytest.mark.asyncio
async def test_create_duplicate_grade(client: AsyncClient):
    """Test creating duplicate grade fails."""
    # Create first
    await client.post(
        "/api/v1/grades/",
        json={"grade": "H8", "median_salary": 250000}
    )

    # Try duplicate
    response = await client.post(
        "/api/v1/grades/",
        json={"grade": "H8", "median_salary": 260000}
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_bulk_import_grades(client: AsyncClient):
    """Test bulk import of grades."""
    response = await client.post(
        "/api/v1/grades/bulk-import",
        json={
            "grades": {
                "SVP": 350000,
                "H8": 250000,
                "H6": 180000,
                "H5": 130000,
                "TL": 90000,
                "AO": 60000
            },
            "currency": "SGD"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 6


@pytest.mark.asyncio
async def test_get_grade_order_map(client: AsyncClient):
    """Test getting grade order map."""
    # First import some grades
    await client.post(
        "/api/v1/grades/bulk-import",
        json={
            "grades": {"SVP": 350000, "H8": 250000, "H6": 180000}
        }
    )

    response = await client.get("/api/v1/grades/order-map")
    assert response.status_code == 200
    data = response.json()
    assert "SVP" in data
    assert "H8" in data
