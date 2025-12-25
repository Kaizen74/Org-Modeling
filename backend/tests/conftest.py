"""Pytest configuration and fixtures."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.models.database import Base, get_session


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_orgdesign.db"

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)

# Test session factory
test_async_session = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a fresh database for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_async_session() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """Create test client with database override."""

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_csv_path():
    """Path to sample CSV fixture."""
    return Path(__file__).parent / "fixtures" / "org_structure_PAX.csv"


@pytest.fixture
def sample_employees():
    """Sample employee data for testing."""
    return [
        {"name": "CEO", "job_title": "CEO", "grade": "SVP", "level": 1, "manager_name": "Top of Org", "salary": 350000, "department": "Executive"},
        {"name": "VP1", "job_title": "VP Sales", "grade": "H8", "level": 2, "manager_name": "CEO", "salary": 250000, "department": "Sales"},
        {"name": "VP2", "job_title": "VP Ops", "grade": "H8", "level": 2, "manager_name": "CEO", "salary": 250000, "department": "Operations"},
        {"name": "Mgr1", "job_title": "Sales Manager", "grade": "H6", "level": 3, "manager_name": "VP1", "salary": 180000, "department": "Sales"},
        {"name": "Mgr2", "job_title": "Ops Manager", "grade": "H6", "level": 3, "manager_name": "VP2", "salary": 180000, "department": "Operations"},
        {"name": "Lead1", "job_title": "Team Lead", "grade": "TL", "level": 4, "manager_name": "Mgr1", "salary": 90000, "department": "Sales"},
        {"name": "IC1", "job_title": "Associate", "grade": "AO", "level": 5, "manager_name": "Lead1", "salary": 60000, "department": "Sales"},
        {"name": "IC2", "job_title": "Associate", "grade": "AO", "level": 5, "manager_name": "Lead1", "salary": 60000, "department": "Sales"},
    ]


@pytest.fixture
def sample_grade_order():
    """Sample grade order for testing."""
    return {
        "SVP": 1,
        "H8": 2,
        "H6": 3,
        "H5": 4,
        "TL": 5,
        "AO": 6
    }


# Expected metrics for PAX CSV validation
EXPECTED_PAX_METRICS = {
    'total_employees': 64,
    'total_managers': 16,
    'manager_ratio_pct': 25.0,
    'total_cost': 5770000,
    'organizational_layers': 6
}
