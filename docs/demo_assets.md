# Demo Assets Checklist

Use this checklist to capture visual proof for the README, LinkedIn post, portfolio page, or bootcamp submission.

## Recommended Screenshots

Save screenshots under:

```text
docs/assets/
```

Suggested filenames:

```text
docs/assets/clara_loan_review_timeline.png
docs/assets/clara_judge_agreement_packet.png
docs/assets/clara_drift_probe.png
docs/assets/clara_docker_desktop.png
docs/assets/clara_pdf_packet.png
```

## Shot 1: Live Agent Timeline

Capture:

- Loan Review tab
- `ADV-001` or `ADV-007`
- Progress at or near 100%
- Live Agent Timeline visible
- Decision Packet visible

Why it matters:

Shows the LangGraph agents working step by step instead of only showing a final answer.

## Shot 2: Human Override + PDF Packet

Capture:

- Human Override Audit Log
- One completed audit entry
- Download PDF packet button

Why it matters:

Shows human-in-the-loop governance and auditability.

## Shot 3: Judge Agreement

Capture:

- Uploaded packet filename
- Primary Judge and Secondary Judge cards
- Exact agreement / within-one-point agreement
- Dimension deltas

Why it matters:

Shows evaluation rigor beyond a single LLM-as-judge score.

## Shot 4: Drift Probe

Capture:

- Drift tab
- Selected case dropdown
- Live LLM drift activity log with repeated runs
- Fingerprints or variance summary

Why it matters:

Shows that CLARA measures nondeterministic LLM behavior instead of pretending model outputs are fixed.

## Shot 5: Docker Desktop

Capture:

- Docker Desktop project `clara`
- `clara-api`
- `clara-web`
- Ports `8000:8000` and `3000:3000`

Why it matters:

Shows deployability and full-stack engineering polish.

## Optional GIF

Record a 20 to 30 second GIF:

1. Select `ADV-001`.
2. Click `Run review pipeline`.
3. Let the live timeline populate.
4. Stop when the decision packet appears.

Recommended filename:

```text
docs/assets/clara_live_pipeline.gif
```

## README Placement

Once screenshots are captured, add them near the top of `README.md` after the Portfolio Summary:

```md
![CLARA live agent timeline](docs/assets/clara_loan_review_timeline.png)
![CLARA judge agreement](docs/assets/clara_judge_agreement_packet.png)
```

Keep the README to two or three images. Put the rest in a portfolio post or slide deck.
