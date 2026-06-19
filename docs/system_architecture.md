# CLARA System Architecture

CLARA is split into a browser-facing product UI, a streaming API layer, a LangGraph orchestration layer, specialist agents, and an evaluation/governance layer.

## High-Level Runtime

```mermaid
flowchart LR
    U["Reviewer Browser"] --> W["Next.js UI\nweb/"]
    W -->|"HTTP fetch"| A["FastAPI Backend\nloan_pipeline/api/app.py"]
    W -->|"EventSource / SSE"| S["Streaming Endpoints\nloan_pipeline/api/streaming.py"]
    A --> G["LangGraph Runtime\nloan_pipeline/graph/orchestrator.py"]
    S --> G
    G --> L["LangChain Model Client\noptional live LLM mode"]
    G --> E["Evaluation Harness\nloan_pipeline/eval/"]
    G --> P["PDF Packet Export\nreview artifact"]
```

## Loan Review Graph

```mermaid
flowchart LR
    C["Loan Case or Uploaded Packet"] --> T["Term Extractor"]
    T --> V["Schema Validator"]
    V --> X{"Validated State"}
    X --> CO["Compliance Checker"]
    X --> R["Credit Risk Scorer"]
    CO --> J["Review Synthesizer"]
    R --> J
    J --> D["Contradiction Detection"]
    J --> CF["Counterfactual Explanations"]
    J --> H["Human Override Gate"]
    H --> PDF["PDF Review Packet"]
```

## Evaluation And Governance

```mermaid
flowchart TB
    GS["30-Case Gold Set\n10 clean / 10 ambiguous / 10 adversarial"] --> EV["Evaluation Runner"]
    GS --> AB["Ablation Study"]
    GS --> DR["Drift Probe"]
    GS --> JA["Judge Agreement"]
    EV --> REP["Markdown/PDF Evaluation Report"]
    AB --> REP
    DR --> REP
    JA --> REP
    PDF["Review Packet"] --> J1["Primary Judge"]
    PDF --> J2["Secondary Judge"]
    J1 --> DIFF["Dimension Deltas"]
    J2 --> DIFF
```

## Request Flow

1. The reviewer selects a seeded SBA-style case or uploads a loan document.
2. The Next.js UI calls the FastAPI backend.
3. For live review, the UI opens an SSE stream.
4. FastAPI sends the case into the compiled LangGraph workflow.
5. Term extraction and schema validation create structured shared state.
6. Compliance and credit risk agents evaluate the case as independent specialists.
7. The synthesizer joins outputs, detects contradictions, and creates counterfactuals.
8. The UI renders the live timeline and decision packet as events arrive.
9. The reviewer can add a human override with rationale.
10. The review packet can be exported as a PDF and independently judged.

## Why This Architecture Works

- **FastAPI SSE** makes long-running graph work visible instead of leaving the user on a frozen screen.
- **LangGraph state** keeps agent outputs structured and auditable.
- **Parallel specialist review** creates real division of responsibility between compliance and credit risk.
- **Human override logging** turns the system into decision support rather than autonomous lending.
- **Evaluation harness** makes performance measurable across clean, ambiguous, and adversarial cases.
- **Docker Compose** packages the API and UI as separate deployable services.

## Deployment Shape

```mermaid
flowchart LR
    subgraph Local["Local Docker Demo"]
        DW["clara-web\nNext.js :3000"] --> DA["clara-api\nFastAPI :8000"]
    end

    subgraph Cloud["Cloud Deployment"]
        VW["Vercel Web UI"] --> HA["Hosted FastAPI API\nRender/Railway/Fly/VM"]
        HA --> LS["LangSmith\noptional"]
        HA --> M["OpenAI-compatible LLM Provider\nNebius/OpenAI/etc."]
    end
```

For the bootcamp demo, the local Docker stack is the most reliable recording path. For public sharing, deploy the Next.js frontend and point `NEXT_PUBLIC_API_BASE_URL` to a hosted FastAPI backend.
