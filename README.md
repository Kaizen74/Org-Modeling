# Organizational Design Workbench (OrgDesign Pro)

A production-grade organizational design application for management consultants. Parse PowerPoint org charts (including shapes outside the visible canvas), perform structural analysis using established frameworks (Kates-Kesler, McKinsey), simulate transformation scenarios, and generate AI-powered recommendations via Claude API.

## Features

- **PowerPoint Parsing**: Parse org charts from PPTX files, including shapes positioned outside the visible canvas
- **CSV/Excel Import**: Import employee data from spreadsheets
- **Structural Validation**: Detect cycles, orphans, and hierarchy issues
- **Metrics Calculation**: Span of control, hierarchy depth, cost analysis
- **AI-Powered Analysis**: Claude-powered insights and recommendations
- **Scenario Comparison**: Compare As-Is vs To-Be organizational structures
- **Interactive Org Chart**: Visual editing with React Flow

## Technology Stack

- **Backend**: FastAPI + SQLAlchemy (async) + NetworkX + python-pptx
- **Frontend**: React 18 + TypeScript + React Flow + Recharts + Tailwind CSS
- **Database**: SQLite (local) or PostgreSQL (production)
- **AI**: Anthropic Claude API (Sonnet)

## Quick Start Guide

### Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- Git

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd Org-Modeling
```

### Step 2: Set Up the Backend

```bash
# Navigate to backend directory
cd backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env

# Edit .env and add your Anthropic API key (optional, for AI features)
# ANTHROPIC_API_KEY=your_api_key_here

# Initialize the database
python -c "import asyncio; from app.models.database import init_db; asyncio.run(init_db())"

# Start the backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend API will be available at:
- API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Alternative Docs: http://localhost:8000/redoc

### Step 3: Set Up the Frontend

Open a new terminal window:

```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Start the development server
npm run dev
```

The frontend will be available at: http://localhost:3000

### Step 4: Configure Claude API Key (Optional)

To enable AI-powered analysis:

1. Get an API key from [Anthropic Console](https://console.anthropic.com/)
2. In the app, go to Settings
3. Enter your API key and click "Test Key"
4. Once validated, click "Save Key"

## Usage Guide

### Creating a Project

1. Navigate to Projects page
2. Click "New Project"
3. Enter project name and client name
4. Click "Create Project"

### Uploading an Org Chart

1. Open your project
2. Drag and drop a PPTX, CSV, or Excel file into the upload area
3. Review the parsed data and validation results
4. Fix any validation errors if needed
5. Click "Publish as Scenario" to create a scenario

### Analyzing a Scenario

1. Open a scenario
2. Click "Calculate Metrics" to see organizational KPIs
3. Click "AI Analysis" to get Claude-powered insights
4. View findings and recommendations in the Analysis tab

### Comparing Scenarios

1. Go to the Compare page
2. Select a project
3. Choose baseline (As-Is) and target (To-Be) scenarios
4. Click "Compare Scenarios"
5. Review metric deltas and node changes

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=app

# Frontend tests
cd frontend
npm test
```

### Code Quality

```bash
# Backend
cd backend
black app/
flake8 app/
mypy app/

# Frontend
cd frontend
npm run lint
```

## Project Structure

```
Org-Modeling/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routes
│   │   ├── models/       # SQLAlchemy models & Pydantic schemas
│   │   ├── parsers/      # PPTX, CSV, Excel parsers
│   │   ├── services/     # Business logic (validation, metrics, AI)
│   │   └── main.py       # Application entry point
│   ├── tests/            # Backend tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/          # API client & types
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   └── stores/       # Zustand state management
│   └── package.json
└── README.md
```

## API Endpoints

### Projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects` - List projects
- `GET /api/v1/projects/{id}` - Get project
- `PATCH /api/v1/projects/{id}` - Update project

### Datasets
- `POST /api/v1/projects/{id}/datasets` - Upload file
- `GET /api/v1/datasets/{id}/preview` - Preview parsed data
- `POST /api/v1/datasets/{id}/validate` - Run validation
- `POST /api/v1/datasets/{id}/publish` - Publish to scenario

### Scenarios
- `GET /api/v1/projects/{id}/scenarios` - List scenarios
- `GET /api/v1/scenarios/{id}` - Get scenario
- `GET /api/v1/scenarios/{id}/tree` - Get org chart tree
- `POST /api/v1/scenarios/{id}/clone` - Clone scenario
- `POST /api/v1/scenarios/{id}/calculate-metrics` - Calculate metrics
- `POST /api/v1/scenarios/{id}/analyze` - AI analysis

### Comparison
- `POST /api/v1/scenarios/compare` - Compare scenarios

## Troubleshooting

### Backend won't start
- Ensure Python 3.11+ is installed: `python --version`
- Ensure virtual environment is activated
- Check if all dependencies installed: `pip install -r requirements.txt`

### Frontend won't start
- Ensure Node.js 18+ is installed: `node --version`
- Delete `node_modules` and reinstall: `rm -rf node_modules && npm install`

### Database errors
- Delete `orgdesign.db` and restart the backend to recreate

### API key errors
- Verify your API key at https://console.anthropic.com/
- Ensure the key starts with `sk-ant-`

## License

MIT License - see LICENSE file for details.

## Support

For issues and feature requests, please open a GitHub issue.
