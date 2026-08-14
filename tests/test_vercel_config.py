import json
import tomllib
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_vercel_uses_explicit_fastapi_entrypoint_without_legacy_rewrite() -> None:
    vercel_config = json.loads((REPOSITORY_ROOT / "vercel.json").read_text(encoding="utf-8"))
    pyproject = tomllib.loads((REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "rewrites" not in vercel_config
    assert pyproject["tool"]["vercel"]["entrypoint"] == "loan_pipeline.api.app:app"


def test_vercel_bundle_preserves_frontend_source_but_excludes_generated_files() -> None:
    ignored_paths = set(
        (REPOSITORY_ROOT / ".vercelignore").read_text(encoding="utf-8").splitlines()
    )

    assert {
        ".env*",
        ".venv/",
        ".vercel/",
        "tests/",
        "web/node_modules/",
        "web/.next/",
        "web/out/",
    } <= ignored_paths
    assert "web/" not in ignored_paths
