# TeaMate-Backend

## Run the backend

### 1. Create and activate a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure environment variables

Create or update `.env` with:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/teamate
ML_MODEL_URL=http://localhost:8000
APP_HOST=0.0.0.0
APP_PORT=8001
DEBUG=true
```

### 4. Run database migrations

Before starting the app, apply the existing migrations:

```powershell
alembic upgrade head
```

If you make changes to the SQLAlchemy models and need to create a new migration file, run:

```powershell
alembic revision --autogenerate -m "describe your change"
```

Then apply it:

### 5. Start the backend

You can also run it directly with Uvicorn:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```
