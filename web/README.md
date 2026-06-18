# Vercel Next.js UI

Experimental browser-native UI for the loan review pipeline.

## Local Run

Start the Python API in one terminal:

```powershell
cd C:\Users\nsingh1\CLARA
.\.venv\Scripts\Activate.ps1
uvicorn loan_pipeline.api.app:app --reload --port 8000
```

Start the Next.js app in another terminal:

```powershell
cd C:\Users\nsingh1\CLARA\web
npm.cmd install
npm.cmd run dev
```

Open:

```text
http://localhost:3000
```

The UI expects:

```text
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```
