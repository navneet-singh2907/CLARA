"""Regression checks for the browser's SSE event contract."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_review_timeline_subscribes_to_and_renders_agent_failures() -> None:
    page = (ROOT / "web" / "app" / "page.tsx").read_text(encoding="utf-8")
    styles = (ROOT / "web" / "app" / "globals.css").read_text(encoding="utf-8")

    assert '"agent_failed",' in page
    assert 'item.event === "agent_completed" || item.event === "agent_failed"' in page
    assert 'item.event === "agent_failed" ? `${node} failed` : node' in page
    assert ".dot.agent_failed" in styles
