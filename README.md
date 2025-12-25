# Org Design Analyzer

A lightweight organizational design analyzer that:
1. Parses CSV org data and calculates 6 core metrics
2. Provides AI-powered analysis with structured insights categorization
3. Runs on consultant laptops (SQLite, no Docker required)

## Features

### Core Metrics
- **Total Employees**: Count with manager/IC breakdown
- **Manager Ratio**: Percentage of managers vs individual contributors
- **Span of Control**: Average direct reports per manager
- **Total Cost**: Salary cost analysis by level and grade
- **Grade Gap**: Distance between manager and report grades
- **Organizational Layers**: Hierarchical depth analysis

### AI Analysis (Claude API)
- Industry trends & benchmarks
- Org structure health diagnosis
- Strategy alignment scoring
- Recommended organizational archetypes

### Visualizations
- Interactive org chart (React Flow)
- Metrics dashboards (Recharts)
- Health indicators and warnings

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Anthropic API key (for AI analysis)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## CSV Format

Required columns:
- `Name` - Employee name
- `Job Title` - Job title
- `Grade` - Grade level (e.g., SVP, H8, H6, TL, AO)
- `Level` - Hierarchical level (1, 2, 3...)
- `Line Manager` - Manager's name (use "Top of Org" for CEO)
- `Salary` - Annual salary

Optional columns:
- `Department` - Department name
- `Employee ID` - Unique identifier

Example:
```csv
Name,Job Title,Grade,Department,Level,Line Manager,Salary,Employee ID
John Smith,CEO,SVP,Executive,1,Top of Org,350000,E001
Jane Doe,VP Sales,H8,Sales,2,John Smith,250000,E002
```

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   ├── models/        # Database models
│   │   ├── parsers/       # CSV parser
│   │   └── services/      # Business logic
│   ├── alembic/           # Database migrations
│   └── tests/             # Test files
├── frontend/
│   └── src/
│       ├── components/    # React components
│       ├── pages/         # Page components
│       ├── services/      # API services
│       └── types/         # TypeScript types
└── PROGRESS.md            # Development progress
```

## API Endpoints

### Settings
- `GET /api/v1/settings/claude-api-key/status` - Check API key status
- `POST /api/v1/settings/claude-api-key` - Set API key
- `POST /api/v1/settings/claude-api-key/test` - Test connection

### Grades
- `GET /api/v1/grades/` - List grades
- `POST /api/v1/grades/` - Create grade
- `POST /api/v1/grades/bulk-import` - Bulk import grades

### Org Data
- `POST /api/v1/org-data/upload-csv` - Upload CSV
- `GET /api/v1/org-data/latest` - Get latest org data

### Metrics
- `POST /api/v1/metrics/calculate` - Calculate metrics
- `GET /api/v1/metrics/latest` - Get latest metrics
- `GET /api/v1/metrics/summary` - Get summary

### AI Analysis
- `POST /api/v1/ai-analysis/analyze` - Run AI analysis
- `GET /api/v1/ai-analysis/latest` - Get latest analysis
- `GET /api/v1/ai-analysis/quick-analysis` - Get quick insights

## Running Tests

```bash
cd backend
pytest tests/ -v
```

## Tech Stack

### Backend
- FastAPI 0.109.0
- SQLAlchemy (async) 2.0.25
- SQLite with aiosqlite
- Pandas 2.1.4
- NetworkX 3.2.1
- Anthropic SDK 0.17.0

### Frontend
- React 18
- TypeScript 5.3
- Vite 5.0
- React Flow 11.10
- Recharts 2.10
- Tailwind CSS 3.4

## License

MIT
