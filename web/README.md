# CLARA Next.js UI

Browser-native demo UI for CLARA.

The UI connects to the FastAPI backend through `NEXT_PUBLIC_API_BASE_URL` and displays live LangGraph timelines, document upload, PDF export, evaluation, ablation, live LLM drift, judge agreement, and report generation.

## Local Run

Start the Python API in one terminal:

```powershell
cd C:\Users\nsingh1\CLARA
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m uvicorn loan_pipeline.api.app:app --host 127.0.0.1 --port 8000 --reload
```

Start the Next.js app in another terminal:

```powershell
cd C:\Users\nsingh1\CLARA\web
npm.cmd install
$env:NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8000"
npm.cmd run dev
```

Open:

```text
http://localhost:3000
```

Deployment details live in [../DEPLOYMENT.md](../DEPLOYMENT.md).
