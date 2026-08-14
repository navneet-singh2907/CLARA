from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_aws_fullstack_dockerfile_builds_and_runs_both_services() -> None:
    dockerfile = (ROOT / "Dockerfile.aws-fullstack").read_text(encoding="utf-8")

    assert "ARG NEXT_PUBLIC_API_BASE_URL=__SAME_ORIGIN__" in dockerfile
    assert "ARG CLARA_INTERNAL_API_URL=http://127.0.0.1:8001" in dockerfile
    assert "COPY --from=web-builder /build/web/.next/standalone ./web" in dockerfile
    assert 'CMD ["python", "scripts/start_aws_fullstack.py"]' in dockerfile
    assert "EXPOSE 8000" in dockerfile


def test_next_config_only_enables_internal_proxy_when_configured() -> None:
    next_config = (ROOT / "web" / "next.config.ts").read_text(encoding="utf-8")

    assert 'output: "standalone"' in next_config
    assert "if (!internalApiUrl)" in next_config
    assert '"/review"' in next_config
    assert '"/judge-agreement"' in next_config
    assert 'source: `${path}/:path*`' in next_config


def test_frontend_accepts_an_explicit_same_origin_api_base() -> None:
    page = (ROOT / "web" / "app" / "page.tsx").read_text(encoding="utf-8")

    assert 'configuredApiBase === "__SAME_ORIGIN__"' in page
    assert "configuredApiBase ??" in page
    assert "process.env.NEXT_PUBLIC_API_BASE_URL ||" not in page


def test_fullstack_bundle_keeps_secrets_and_generated_assets_out() -> None:
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    bundle_script = (ROOT / "scripts" / "build_aws_fullstack_bundle.ps1").read_text(
        encoding="utf-8"
    )

    assert ".env*" in dockerignore
    for generated_name in ("node_modules", ".next", "__pycache__", "out"):
        assert f'"{generated_name}"' in bundle_script
    assert 'Name -like ".env*"' in bundle_script
    assert '"scripts/start_aws_fullstack.py"' in bundle_script


def test_prebuilt_bundle_avoids_frontend_build_work_on_elastic_beanstalk() -> None:
    dockerfile = (ROOT / "Dockerfile.aws-fullstack-prebuilt").read_text(encoding="utf-8")
    bundle_script = (ROOT / "scripts" / "build_aws_prebuilt_bundle.ps1").read_text(
        encoding="utf-8"
    )

    assert "COPY web ./web" in dockerfile
    assert "npm ci" not in dockerfile
    assert "npm run build" not in dockerfile
    assert '$env:NEXT_PUBLIC_API_BASE_URL = "__SAME_ORIGIN__"' in bundle_script
    assert '"api/requirements.txt"' in bundle_script
    assert '"web/server.js"' in bundle_script
    assert '"web/.next/static/*"' in bundle_script
