"""The cyberrange CLI: content new|lint|solve|test|pack.

`preview`, `build`, and `publish` wire into the API's ingestion flow as
those phases land; until then they exit with a clear message instead of
pretending to work.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Any

import typer
from openrange.content.harness import solve_room
from openrange.content.linting import Finding, lint_path, lint_room
from openrange.content.loader import LoadError, load_bundle
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="OpenRange content toolchain", no_args_is_help=True)
console = Console()

BUNDLES_ROOT = Path("content")
ROOMS = BUNDLES_ROOT / "rooms"
MODULES = BUNDLES_ROOT / "modules"
PATHS = BUNDLES_ROOT / "paths"

TEMPLATE = """apiVersion: openrange.io/v1
kind: Room
metadata:
  slug: {slug}
  title: "{title}"
  version: 0.1.0
  difficulty: easy
  points: 100
  estimated_minutes: 30
  tags: []
spec:
  track: web-foundations
  type: challenge
  summary: >-
    Replace with a concrete one-paragraph scenario describing what the
    learner defends or attacks and why it matters.
  objectives:
    - "Identify the vulnerability class from observed behavior."
    - "Exploit it through the intended path and capture the flag."
  prerequisites: []
  scope:
    allowed_targets:
      - "http://target:{port}"
    forbidden: [control-plane, other-labs, internet, host]
  safety:
    simulated_only: true
    no_real_malware: true
  target:
    build_context: ./target
    ports: [{port}]
    healthcheck:
      http_path: /healthz
    flag_delivery: env
    flag_env: ROOM_FLAG
  workstation: terminal
  tasks:
    - id: task-1
      title: "Capture the flag"
      prompt: >-
        Describe the exact objective the learner must complete.
      points: 100
      hints:
        - cost: 0
          text: "A nudge that does not give anything away."
      solution: |
        Step-by-step intended path with commands. Minimum detail bar:
        a competent reviewer can reproduce every step end to end.
      validator:
        type: per_session_flag
"""


@app.command()
def new(kind: str, slug: str, title: str = "", port: int = 8000) -> None:
    """Scaffold a bundle (kind: room|module|path)."""
    if kind != "room":
        console.print("[red]only room scaffolding exists so far[/red]")
        raise typer.Exit(2)
    target = ROOMS / slug
    if target.exists():
        console.print(f"[red]{target} already exists[/red]")
        raise typer.Exit(1)
    (target / "solver").mkdir(parents=True)
    (target / "target").mkdir()
    (target / "lesson").mkdir()
    (target / "room.yaml").write_text(
        TEMPLATE.format(slug=slug, title=title or slug.replace("-", " ").title(), port=port)
    )
    (target / "solver" / "solver.py").write_text(
        '"""Intended-path solver for ' + slug + '."""\n\n'
        "from openrange.content.solver import SolveResult, TaskResult, find_flags\n"
        "import httpx\n\n\n"
        "def solve(ctx) -> SolveResult:\n"
        "    payload = {'username': chr(39) + ' OR 1=1--', 'password': 'x'}\n"
        "    res = httpx.post(f'{ctx.url()}/login', data=payload)\n"
        "    flags = find_flags(res.text)\n"
        "    captured = flags[0] if flags else None\n"
        "    return SolveResult(results=[\n"
        "        TaskResult(task_id='task-1', ok=bool(captured), captured=captured)\n"
        "    ])\n"
    )
    console.print(f"[green]scaffolded {target}[/green]")


def _print_findings(findings: list[Finding]) -> int:
    errors = [f for f in findings if f.severity == "error"]
    table = Table.grid(padding=(0, 2))
    for f in findings:
        color = "red" if f.severity == "error" else "yellow"
        table.add_row(f"[{color}]{f.severity}[/{color}]", f.rule, f.message)
    console.print(table)
    return 1 if errors else 0


def _lint_directory(target: Path) -> list[Finding]:
    findings: list[Finding] = []
    for child in sorted(target.glob("*")):
        if not child.is_dir():
            continue
        if (child / "room.yaml").exists():
            findings.extend(lint_room(child))
        elif (child / "path.yaml").exists():
            findings.extend(lint_path(child))
    return findings


@app.command()
def lint(target: Annotated[Path, typer.Argument()] = Path(".")) -> None:
    """Lint one bundle or a directory of bundles."""
    if (target / "room.yaml").exists():
        code = _print_findings(lint_room(target))
    elif (target / "path.yaml").exists():
        code = _print_findings(lint_path(target))
    elif target.is_dir():
        code = _print_findings(_lint_directory(target))
    else:
        console.print(f"[red]{target} is neither a bundle nor a directory[/red]")
        code = 1
    raise typer.Exit(code)


@app.command()
def solve(bundle: Path) -> None:
    """Build the room image and run its solver against a live container."""
    result = solve_room(bundle)
    status = "[green]PASS[/green]" if result.solved else "[red]FAIL[/red]"
    console.print(f"{status} {result.slug}: {result.detail}")
    raise typer.Exit(0 if result.solved else 1)


def _generated_schemas() -> dict[str, str]:
    from openrange.content import models as content_models

    schema_models: list[tuple[str, Any]] = [
        ("room.schema.json", content_models.RoomBundle),
        ("module.schema.json", content_models.ModuleBundle),
        ("path.schema.json", content_models.PathBundle),
    ]
    generated: dict[str, str] = {}
    for name, model in schema_models:
        schema = model.model_json_schema()
        schema["$id"] = f"https://openrange.local/schemas/{name}"
        generated[name] = json.dumps(schema, indent=2) + "\n"
    return generated


@app.command()
def schemas(
    out: Annotated[Path, typer.Option()] = Path("packages/content-sdk/schemas"),
    check_diff: Annotated[bool, typer.Option("--check-diff")] = False,
) -> None:
    """Generate JSON Schemas, or verify checked-in ones are current."""
    generated = _generated_schemas()
    if not check_diff:
        out.mkdir(parents=True, exist_ok=True)
        for name, text in generated.items():
            (out / name).write_text(text)
        console.print(f"[green]wrote schemas to {out}[/green]")
        return
    stale = [
        name
        for name, text in generated.items()
        if not (out / name).exists() or (out / name).read_text() != text
    ]
    if stale:
        console.print(f"[red]stale schemas: {', '.join(stale)}; run `cyberrange schemas`[/red]")
        raise typer.Exit(1)
    console.print("[green]schemas are up to date[/green]")


@app.command()
def show(manifest: Path) -> None:
    """Pretty-print a manifest after validation."""
    try:
        bundle = load_bundle(manifest)
    except LoadError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    console.print(json.dumps(json.loads(bundle.model_dump_json(by_alias=True)), indent=2))


@app.command()
def pack(bundle: Path, out: Annotated[Path, typer.Option()] = Path("dist")) -> None:
    """Package a validated bundle into a versioned tarball."""
    import tarfile

    try:
        load_bundle(bundle / "room.yaml") if (bundle / "room.yaml").exists() else load_bundle(
            bundle / ("module.yaml" if (bundle / "module.yaml").exists() else "path.yaml")
        )
    except LoadError as exc:
        console.print(f"[red]refusing to pack invalid bundle: {exc}[/red]")
        raise typer.Exit(1) from exc
    out.mkdir(parents=True, exist_ok=True)
    name = bundle.name
    dest = out / f"{name}.tgz"
    with tarfile.open(dest, "w:gz") as tar:
        tar.add(bundle, arcname=name)
    console.print(f"[green]packed {dest}[/green]")


@app.command()
def publish(bundle: Path) -> None:
    """Publishing requires a running control plane; not wired yet."""
    _ = bundle
    console.print(
        "[yellow]publish arrives with the Content Studio phase; "
        "use `pack` and the API ingestion endpoint once available[/yellow]"
    )
    raise typer.Exit(2)


def main() -> int:  # pragma: no cover - entry point
    try:
        app()
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
