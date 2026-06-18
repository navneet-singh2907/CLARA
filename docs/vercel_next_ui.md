# Vercel Next.js UI

The Next.js UI in `web/` is now the primary browser demo surface for CLARA.

Use the full deployment guide here:

- [Deployment Guide](../DEPLOYMENT.md)

Current deployment shape:

```text
Next.js UI on Vercel
  -> NEXT_PUBLIC_API_BASE_URL
  -> FastAPI backend
  -> LangGraph/LangChain pipeline
```

The UI supports live agent timelines, document upload, PDF packet download, evaluation, ablation, live LLM drift probing, judge agreement, and PDF evaluation report generation.
