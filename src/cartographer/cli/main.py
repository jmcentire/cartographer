"""Cartographer CLI — stack adoption and compatibility tool."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from cartographer.config.loader import (
    CartographerConfig,
    DEFAULT_CONFIG_NAME,
    load_config,
    write_default_config,
)


@click.group()
@click.pass_context
def main(ctx: click.Context) -> None:
    """Cartographer: stack adoption and compatibility tool."""
    ctx.ensure_object(dict)
    ctx.obj["base_dir"] = Path.cwd()
    ctx.obj["config"] = load_config()


@main.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize cartographer.yaml with defaults."""
    base = ctx.obj["base_dir"]
    path = base / DEFAULT_CONFIG_NAME
    if path.exists():
        click.echo(f"{DEFAULT_CONFIG_NAME} already exists.")
        return
    write_default_config(path)
    click.echo(f"Created {DEFAULT_CONFIG_NAME}")


@main.command()
@click.option("--only", "only_tools", default=None, help="Comma-separated list of tools to draft for.")
@click.option("--no-live", is_flag=True, help="Skip live backend and service probing.")
@click.option("--service", "service_urls", multiple=True, help="Additional service URL to probe.")
@click.option("--openapi", "openapi_files", multiple=True, help="Additional OpenAPI spec file to parse.")
@click.pass_context
def discover(
    ctx: click.Context,
    only_tools: str | None,
    no_live: bool,
    service_urls: tuple[str, ...],
    openapi_files: tuple[str, ...],
) -> None:
    """Run discovery and produce draft artifacts."""
    config: CartographerConfig = ctx.obj["config"]
    base_dir: Path = ctx.obj["base_dir"]
    output_dir = base_dir / config.output_dir

    tools = [t.strip() for t in only_tools.split(",")] if only_tools else None

    # Source scan
    click.echo("Scanning source code...")
    from cartographer.discovery.scanner import scan_source

    result = scan_source(config, base_dir)
    click.echo(
        f"  Found {len(result.components)} components, "
        f"{len(result.models)} models, "
        f"{len(result.routes)} routes, "
        f"{len(result.pact_keys)} PACT keys, "
        f"{len(result.env_vars)} env vars, "
        f"{len(result.sensitive_fields)} sensitive fields"
    )

    # Live backend introspection
    if not no_live and config.targets.infrastructure.backends:
        click.echo("Introspecting live backends...")
        from cartographer.discovery.live.introspector import introspect_backends

        live_models = introspect_backends(config.targets.infrastructure.backends)
        result.models.extend(live_models)
        click.echo(f"  Found {len(live_models)} models from live backends")

    # Service probing
    all_service_urls = list(config.targets.services.base_urls) + list(service_urls)
    all_openapi_paths = list(config.targets.services.openapi_paths) + list(openapi_files)

    if not no_live and (all_service_urls or all_openapi_paths):
        click.echo("Probing services...")
        from cartographer.discovery.service_prober import probe_services

        service_result = probe_services(all_service_urls, all_openapi_paths)
        result.routes.extend(service_result.routes)
        result.components.extend(service_result.components)
        click.echo(
            f"  Found {len(service_result.routes)} routes, "
            f"{len(service_result.components)} components from services"
        )

    # Run drafters
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    from cartographer.drafters.constrain_drafter import ConstrainDrafter
    from cartographer.drafters.pact_drafter import PactDrafter
    from cartographer.drafters.ledger_drafter import LedgerDrafter
    from cartographer.drafters.baton_drafter import BatonDrafter
    from cartographer.drafters.sentinel_drafter import SentinelDrafter

    drafters = {
        "constrain": ConstrainDrafter,
        "pact": PactDrafter,
        "ledger": LedgerDrafter,
        "baton": BatonDrafter,
        "sentinel": SentinelDrafter,
    }

    for name, drafter_cls in drafters.items():
        if tools and name not in tools:
            continue
        click.echo(f"Drafting {name} artifacts...")
        drafter = drafter_cls()
        paths = drafter.draft(result, output_dir)
        written.extend(paths)
        click.echo(f"  Wrote {len(paths)} file(s)")

    click.echo(f"\nDraft artifacts written to {output_dir}")
    click.echo(f"Total files: {len(written)}")


@main.command()
@click.option("--tool", "tool_name", default=None, help="Check only this tool.")
@click.option("--strict", is_flag=True, help="Exit non-zero on any WARN or FAIL.")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text", help="Output format.")
@click.pass_context
def check(ctx: click.Context, tool_name: str | None, strict: bool, fmt: str) -> None:
    """Run compatibility checks against existing stack."""
    config: CartographerConfig = ctx.obj["config"]
    base_dir: Path = ctx.obj["base_dir"]

    tools = [tool_name] if tool_name else None

    from cartographer.compatibility.runner import run_checks
    from cartographer.report.generator import build_report, format_text, format_json, save_report

    click.echo("Running compatibility checks...")
    checks = run_checks(config, base_dir, tools)
    report = build_report(checks)

    if fmt == "json":
        click.echo(format_json(report))
    else:
        click.echo(format_text(report))

    # Save report
    report_dir = base_dir / ".cartographer" / "reports"
    save_report(report, report_dir, fmt)

    # Exit code
    if report.has_failures:
        sys.exit(1)
    if strict and report.score_warn > 0:
        sys.exit(1)


@main.command()
@click.pass_context
def report(ctx: click.Context) -> None:
    """Show the most recent compatibility report."""
    base_dir: Path = ctx.obj["base_dir"]
    report_dir = base_dir / ".cartographer" / "reports"

    for name in ["report_latest.txt", "report_latest.json"]:
        path = report_dir / name
        if path.exists():
            click.echo(path.read_text())
            return

    click.echo("No reports found. Run 'cartographer check' first.")


@main.command()
@click.option("--confidence", type=click.Choice(["high", "medium", "low"]), default="high",
              help="Minimum confidence level for adoption.")
@click.option("--tool", "tool_name", default=None, help="Adopt only this tool's artifacts.")
@click.option("--dry-run", is_flag=True, help="Show what would be registered without doing it.")
@click.option("--confirm-classification", is_flag=True,
              help="Required to adopt classification fields.")
@click.pass_context
def adopt(
    ctx: click.Context,
    confidence: str,
    tool_name: str | None,
    dry_run: bool,
    confirm_classification: bool,
) -> None:
    """Register draft artifacts with their target tools."""
    config: CartographerConfig = ctx.obj["config"]
    base_dir: Path = ctx.obj["base_dir"]
    output_dir = base_dir / config.output_dir

    if not output_dir.exists():
        click.echo("No drafts found. Run 'cartographer discover' first.")
        return

    from cartographer.models import Confidence

    confidence_map = {"high": Confidence.HIGH, "medium": Confidence.MEDIUM, "low": Confidence.LOW}
    min_confidence = confidence_map[confidence]
    confidence_order = [Confidence.HIGH, Confidence.MEDIUM, Confidence.LOW]
    min_idx = confidence_order.index(min_confidence)

    import yaml

    adopted = 0
    skipped = 0

    for yaml_file in sorted(output_dir.rglob("*.yaml")):
        try:
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
        except Exception:
            continue

        if not isinstance(data, dict):
            continue
        if not data.get("_draft"):
            continue

        # Check tool filter
        tool = _infer_tool(yaml_file, output_dir)
        if tool_name and tool != tool_name:
            continue

        # Check confidence
        item_confidence = data.get("_confidence", "low")
        try:
            item_conf = Confidence(item_confidence)
        except ValueError:
            item_conf = Confidence.LOW

        item_idx = confidence_order.index(item_conf)
        if item_idx > min_idx:
            skipped += 1
            continue

        # Check classification fields
        has_classification = _has_classification_fields(data)
        if has_classification and not confirm_classification:
            click.echo(f"  SKIP {yaml_file.name} — has classification fields (use --confirm-classification)")
            skipped += 1
            continue

        if dry_run:
            click.echo(f"  WOULD ADOPT {yaml_file.name} ({tool}, confidence: {item_confidence})")
        else:
            click.echo(f"  ADOPTED {yaml_file.name} ({tool}, confidence: {item_confidence})")
        adopted += 1

    click.echo(f"\n{'Would adopt' if dry_run else 'Adopted'}: {adopted}, Skipped: {skipped}")


@main.group()
def drafts() -> None:
    """Manage draft artifacts."""


@drafts.command("list")
@click.option("--tool", "tool_name", default=None, help="Filter by tool.")
@click.pass_context
def drafts_list(ctx: click.Context, tool_name: str | None) -> None:
    """List all draft artifacts."""
    config: CartographerConfig = ctx.obj["config"]
    base_dir: Path = ctx.obj["base_dir"]
    output_dir = base_dir / config.output_dir

    if not output_dir.exists():
        click.echo("No drafts found.")
        return

    for f in sorted(output_dir.rglob("*")):
        if f.is_file():
            rel = f.relative_to(output_dir)
            tool = rel.parts[0] if len(rel.parts) > 1 else "unknown"
            if tool_name and tool != tool_name:
                continue
            click.echo(f"  {rel}")


@drafts.command("show")
@click.argument("tool")
@click.argument("artifact")
@click.pass_context
def drafts_show(ctx: click.Context, tool: str, artifact: str) -> None:
    """Show a specific draft artifact."""
    config: CartographerConfig = ctx.obj["config"]
    base_dir: Path = ctx.obj["base_dir"]
    output_dir = base_dir / config.output_dir

    # Find the artifact
    for f in output_dir.rglob("*"):
        if f.is_file() and tool in str(f) and artifact in f.name:
            click.echo(f.read_text())
            return

    click.echo(f"Artifact not found: {tool}/{artifact}")


@main.command()
@click.option("--host", default="0.0.0.0", help="Bind host.")
@click.option("--port", default=8090, type=int, help="Bind port.")
@click.pass_context
def serve(ctx: click.Context, host: str, port: int) -> None:
    """Start the HTTP API server."""
    try:
        import uvicorn
    except ImportError:
        click.echo("Install API dependencies: pip install cartographer[api]")
        raise SystemExit(1)

    config: CartographerConfig = ctx.obj["config"]
    base_dir: Path = ctx.obj["base_dir"]

    from cartographer.api.server import create_app

    app = create_app(config, base_dir)
    click.echo(f"Starting Cartographer API on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


def _infer_tool(path: Path, output_dir: Path) -> str:
    """Infer the target tool from the artifact path."""
    try:
        rel = path.relative_to(output_dir)
        return rel.parts[0] if len(rel.parts) > 1 else "unknown"
    except ValueError:
        return "unknown"


def _has_classification_fields(data: dict) -> bool:
    """Check if the artifact contains classification fields."""
    if "classification" in data or "_classification_confidence" in data:
        return True
    for v in data.values():
        if isinstance(v, dict) and _has_classification_fields(v):
            return True
        if isinstance(v, list):
            for item in v:
                if isinstance(item, dict) and _has_classification_fields(item):
                    return True
    return False


if __name__ == "__main__":
    main()
