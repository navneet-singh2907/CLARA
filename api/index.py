"""Vercel Python entrypoint for the FastAPI loan review API."""

from loan_pipeline.api.app import app

__all__ = ["app"]
