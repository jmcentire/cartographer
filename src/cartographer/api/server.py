"""HTTP API server for Cartographer."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread
from typing import Any

from cartographer.config.loader import CartographerConfig, load_config
from cartographer.models import DiscoveryResult

# Jobs store (in-memory for simplicity)
_jobs: dict[str, dict[str, Any]] = {}


def create_app(config: CartographerConfig | None = None, base_dir: Path | None = None):
    """Create the Starlette ASGI application."""
    try:
        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.responses import JSONResponse
        from starlette.routing import Route
    except ImportError:
        raise ImportError(
            "Install API dependencies: pip install cartographer[api]"
        )

    if config is None:
        config = load_config()
    if base_dir is None:
        base_dir = Path.cwd()

    async def status(request: Request) -> JSONResponse:
        return JSONResponse({
            "status": "ok",
            "version": "0.1.0",
            "base_dir": str(base_dir),
            "output_dir": config.output_dir,
        })

    async def post_discover(request: Request) -> JSONResponse:
        body = await request.json() if request.headers.get("content-type") == "application/json" else {}
        job_id = str(uuid.uuid4())[:8]
        _jobs[job_id] = {
            "id": job_id,
            "type": "discover",
            "status": "running",
            "started": datetime.now(timezone.utc).isoformat(),
            "result": None,
        }

        only_tools = body.get("only", None)

        def _run():
            try:
                from cartographer.discovery.scanner import scan_source
                from cartographer.drafters.constrain_drafter import ConstrainDrafter
                from cartographer.drafters.pact_drafter import PactDrafter
                from cartographer.drafters.ledger_drafter import LedgerDrafter
                from cartographer.drafters.baton_drafter import BatonDrafter
                from cartographer.drafters.sentinel_drafter import SentinelDrafter

                result = scan_source(config, base_dir)
                output_dir = base_dir / config.output_dir
                output_dir.mkdir(parents=True, exist_ok=True)

                drafters_map = {
                    "constrain": ConstrainDrafter,
                    "pact": PactDrafter,
                    "ledger": LedgerDrafter,
                    "baton": BatonDrafter,
                    "sentinel": SentinelDrafter,
                }

                written: list[str] = []
                for name, cls in drafters_map.items():
                    if only_tools and name not in only_tools:
                        continue
                    paths = cls().draft(result, output_dir)
                    written.extend(str(p) for p in paths)

                _jobs[job_id]["status"] = "complete"
                _jobs[job_id]["result"] = {
                    "components": len(result.components),
                    "models": len(result.models),
                    "routes": len(result.routes),
                    "pact_keys": len(result.pact_keys),
                    "files_written": len(written),
                }
            except Exception as e:
                _jobs[job_id]["status"] = "failed"
                _jobs[job_id]["error"] = str(e)

        Thread(target=_run, daemon=True).start()
        return JSONResponse({"job_id": job_id, "status": "running"}, status_code=202)

    async def get_discover(request: Request) -> JSONResponse:
        job_id = request.path_params["job_id"]
        job = _jobs.get(job_id)
        if not job or job["type"] != "discover":
            return JSONResponse({"error": "not found"}, status_code=404)
        return JSONResponse(job)

    async def post_check(request: Request) -> JSONResponse:
        body = await request.json() if request.headers.get("content-type") == "application/json" else {}
        job_id = str(uuid.uuid4())[:8]
        _jobs[job_id] = {
            "id": job_id,
            "type": "check",
            "status": "running",
            "started": datetime.now(timezone.utc).isoformat(),
            "result": None,
        }

        tools = body.get("tools", None)

        def _run():
            try:
                from cartographer.compatibility.runner import run_checks
                from cartographer.report.generator import build_report

                checks = run_checks(config, base_dir, tools)
                report = build_report(checks)
                _jobs[job_id]["status"] = "complete"
                _jobs[job_id]["result"] = {
                    "pass": report.score_pass,
                    "warn": report.score_warn,
                    "fail": report.score_fail,
                    "total": report.total,
                    "percent": report.score_pct,
                    "recommendations": report.recommendations,
                }
            except Exception as e:
                _jobs[job_id]["status"] = "failed"
                _jobs[job_id]["error"] = str(e)

        Thread(target=_run, daemon=True).start()
        return JSONResponse({"job_id": job_id, "status": "running"}, status_code=202)

    async def get_check(request: Request) -> JSONResponse:
        job_id = request.path_params["job_id"]
        job = _jobs.get(job_id)
        if not job or job["type"] != "check":
            return JSONResponse({"error": "not found"}, status_code=404)
        return JSONResponse(job)

    async def get_drafts(request: Request) -> JSONResponse:
        output_dir = base_dir / config.output_dir
        if not output_dir.exists():
            return JSONResponse({"drafts": []})
        drafts: dict[str, list[str]] = {}
        for f in sorted(output_dir.rglob("*")):
            if f.is_file():
                rel = f.relative_to(output_dir)
                tool = rel.parts[0] if len(rel.parts) > 1 else "unknown"
                drafts.setdefault(tool, []).append(str(rel))
        return JSONResponse({"drafts": drafts})

    async def get_drafts_tool(request: Request) -> JSONResponse:
        tool = request.path_params["tool"]
        output_dir = base_dir / config.output_dir / tool
        if not output_dir.exists():
            return JSONResponse({"error": "not found"}, status_code=404)
        files = [str(f.relative_to(output_dir)) for f in sorted(output_dir.rglob("*")) if f.is_file()]
        return JSONResponse({"tool": tool, "artifacts": files})

    async def get_drafts_artifact(request: Request) -> JSONResponse:
        tool = request.path_params["tool"]
        artifact = request.path_params["artifact"]
        output_dir = base_dir / config.output_dir / tool
        for f in output_dir.rglob("*"):
            if f.is_file() and artifact in f.name:
                content = f.read_text()
                return JSONResponse({"tool": tool, "artifact": f.name, "content": content})
        return JSONResponse({"error": "not found"}, status_code=404)

    async def post_adopt(request: Request) -> JSONResponse:
        body = await request.json()
        tool = body.get("tool")
        artifact = body.get("artifact")
        confidence_floor = body.get("confidence_floor", "high")
        return JSONResponse({
            "status": "not_implemented",
            "message": "Adopt via API requires tool-specific registration commands. Use CLI.",
        }, status_code=501)

    async def get_report_latest(request: Request) -> JSONResponse:
        report_dir = base_dir / ".cartographer" / "reports"
        for name in ["report_latest.json", "report_latest.txt"]:
            path = report_dir / name
            if path.exists():
                content = path.read_text()
                if name.endswith(".json"):
                    return JSONResponse(json.loads(content))
                return JSONResponse({"format": "text", "content": content})
        return JSONResponse({"error": "no reports found"}, status_code=404)

    async def get_report_job(request: Request) -> JSONResponse:
        job_id = request.path_params["job_id"]
        job = _jobs.get(job_id)
        if not job:
            return JSONResponse({"error": "not found"}, status_code=404)
        return JSONResponse(job)

    routes = [
        Route("/status", status, methods=["GET"]),
        Route("/discover", post_discover, methods=["POST"]),
        Route("/discover/{job_id}", get_discover, methods=["GET"]),
        Route("/check", post_check, methods=["POST"]),
        Route("/check/{job_id}", get_check, methods=["GET"]),
        Route("/drafts", get_drafts, methods=["GET"]),
        Route("/drafts/{tool}", get_drafts_tool, methods=["GET"]),
        Route("/drafts/{tool}/{artifact}", get_drafts_artifact, methods=["GET"]),
        Route("/adopt", post_adopt, methods=["POST"]),
        Route("/report/latest", get_report_latest, methods=["GET"]),
        Route("/report/{job_id}", get_report_job, methods=["GET"]),
    ]

    return Starlette(routes=routes)
