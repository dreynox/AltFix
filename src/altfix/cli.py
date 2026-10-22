"""Command line interface for AltFix."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .classify import ImageClass
from .config import load_config
from .pipeline import run_fix
from .quality import NEEDS_REVIEW
from .scan import scan_path, summarize

app = typer.Typer(
    help="Generate alt text for documentation images with a local vision model.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _config(**overrides: object):
    return load_config(**overrides)


@app.command()
def scan(
    path: str = typer.Argument(".", help="File or directory to scan."),
    json_out: bool = typer.Option(False, "--json", help="Emit machine readable JSON."),
    show_all: bool = typer.Option(
        False, "--all", help="Include images whose alt text is already fine."
    ),
) -> None:
    """List images with missing or low quality alt text."""
    results = scan_path(path)
    if not results:
        console.print(f"[yellow]No documentation files found under {path}[/]")
        return

    counts = summarize(results)
    if json_out:
        payload = {
            "files": [
                {
                    "file": result.file_path,
                    "images": [
                        {
                            "line": image.line_start,
                            "src": image.src,
                            "alt": image.alt_text,
                            "class": image.classification.value,
                            "heading": image.context_heading,
                        }
                        for image in result.images
                        if show_all or image.needs_fix
                    ],
                }
                for result in results
                if any(show_all or image.needs_fix for image in result.images)
            ],
            "counts": counts,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    table = Table(title="AltFix scan", border_style="blue", show_lines=False)
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Line", justify="right", style="magenta")
    table.add_column("Current alt", style="yellow")
    table.add_column("Class", style="green")
    table.add_column("Source", style="dim", overflow="ellipsis")

    for result in results:
        for image in result.images:
            if not show_all and not image.needs_fix:
                continue
            name = str(Path(result.file_path).name)
            parent = str(Path(result.file_path).parent)
            table.add_row(
                f"{parent}/{name}" if parent not in ("", ".") else name,
                str(image.line_start),
                image.alt_text if image.alt_text else "[dim](empty)[/]",
                image.classification.value,
                image.src,
            )

    console.print(table)
    console.print(
        f"[bold]{counts['missing']}[/] missing, "
        f"[bold]{counts['low_quality']}[/] low quality, "
        f"[bold]{counts['ok']}[/] ok, "
        f"[bold]{counts['decorative']}[/] decorative"
    )


@app.command()
def fix(
    path: str = typer.Argument(".", help="File or directory to fix."),
    apply: bool = typer.Option(False, "--apply", help="Write the changes to disk."),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Preview only."),
    use_cache: bool = typer.Option(True, "--cache/--no-cache", help="Use the description cache."),
    model: Optional[str] = typer.Option(None, "--model", help="Model id to use."),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Model server base URL."),
    limit: Optional[int] = typer.Option(None, "--limit", help="Only describe N images."),
) -> None:
    """Describe images that need alt text and patch the documents."""
    config = _config(model=model, base_url=base_url)
    write = apply and not dry_run

    console.print(
        f"[cyan]Scanning {path} with model [bold]{config.model}[/] "
        f"at [bold]{config.base_url}[/][/]"
    )
    result = run_fix(
        path,
        config=config,
        use_cache=use_cache,
        dry_run=not write,
        limit=limit,
    )

    if not result.tasks:
        console.print("[green]Nothing to fix: every image already has usable alt text.[/]")
        return

    table = Table(title="Proposed alt text", border_style="blue")
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Line", justify="right", style="magenta")
    table.add_column("Old", style="yellow", max_width=24)
    table.add_column("New", style="green", max_width=60)

    for task in result.tasks:
        occurrence = task.occurrence
        new_alt = task.new_alt
        if new_alt == NEEDS_REVIEW:
            new_alt = f"[red]{NEEDS_REVIEW}[/] ({task.error or 'failed'})"
        table.add_row(
            f"{Path(occurrence.file_path).name}:{occurrence.line_start}",
            str(occurrence.line_start),
            occurrence.alt_text or "(empty)",
            new_alt,
        )
    console.print(table)

    if result.patches:
        console.print(Panel(result.patches[0].diff(), title="Unified diff", border_style="green"))
        for patch in result.patches[1:]:
            console.print(Panel(patch.diff(), title=str(patch.file_path), border_style="green"))

    review = len(result.needs_review)
    console.print(
        f"[bold]{result.applied}[/] file(s) changed, "
        f"[bold]{len(result.tasks) - review}[/] image(s) described, "
        f"[bold]{review}[/] need review, "
        f"cache {result.cache_hits}/{result.cache_requests} hits, "
        f"{result.elapsed_s:.1f}s"
    )
    if not write:
        console.print("[yellow]Dry run. Re-run with --apply to write the changes.[/]")


@app.command()
def pr(
    path: str = typer.Argument(".", help="File or directory to fix."),
    apply: bool = typer.Option(False, "--apply", help="Write the changes to disk."),
    branch: str = typer.Option("altfix/add-alt-text", help="Branch to create."),
    title: str = typer.Option("Add alt text to documentation images", help="PR title."),
    body: Optional[str] = typer.Option(None, "--body", help="PR body file."),
) -> None:
    """Create a pull request with the alt text fixes."""
    config = _config()
    write = apply
    console.print("[cyan]Describing images and building the patch...[/]")
    result = run_fix(path, config=config, dry_run=not write)

    if not result.patches:
        console.print("[yellow]No changes to propose.[/]")
        return

    diff = "".join(patch.diff() for patch in result.patches if patch.changed)
    if not write:
        console.print(
            "[yellow]Nothing was written. Re-run with --apply to create the branch and PR.[/]"
        )
        console.print(diff)
        return

    if not shutil.which("git"):
        console.print("[red]git is not installed; cannot create a branch.[/]")
        _print_manual_pr(path, branch, title)
        return

    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args], cwd=path if Path(path).is_dir() else Path(path).parent,
            capture_output=True, text=True,
        )

    git("checkout", "-b", branch)
    git("add", "-A")
    git("commit", "-m", "Add alt text to documentation images")
    pushed = git("push", "-u", "origin", branch)

    if not shutil.which("gh"):
        console.print("[yellow]gh CLI not found. Finish the PR manually:[/]")
        _print_manual_pr(path, branch, title)
        return
    if pushed.returncode != 0:
        console.print(f"[red]git push failed: {pushed.stderr.strip()}[/]")
        _print_manual_pr(path, branch, title)
        return

    args = ["gh", "pr", "create", "--title", title, "--body", body or _default_pr_body(result)]
    created = subprocess.run(args, cwd=path if Path(path).is_dir() else Path(path).parent,
                             capture_output=True, text=True)
    if created.returncode == 0:
        console.print(f"[green]{created.stdout.strip()}[/]")
    else:
        console.print(f"[red]gh pr create failed: {created.stderr.strip()}[/]")
        _print_manual_pr(path, branch, title)


def _default_pr_body(result) -> str:
    review = len(result.needs_review)
    return (
        "## Alt text added by AltFix\n\n"
        f"- Images described: {len(result.tasks) - review}\n"
        f"- Images needing review: {review}\n"
        f"- Model: {result.model} (prompt {result.prompt_version})\n"
        "\nAll inference ran locally against a local OpenAI-compatible server. "
        "Only alt text attributes were changed.\n"
    )


def _print_manual_pr(path: str, branch: str, title: str) -> None:
    console.print("Manual steps:")
    console.print(f"  cd {path}")
    console.print(f"  git checkout -b {branch}")
    console.print("  altfix fix . --apply")
    console.print("  git add -A")
    console.print("  git commit -m 'Add alt text to documentation images'")
    console.print("  git push -u origin " + branch)
    console.print(f"  gh pr create --title '{title}'")


@app.command()
def review(
    path: str = typer.Argument(".", help="File or directory to review."),
    apply: bool = typer.Option(False, "--apply", help="Write accepted changes to disk."),
    use_cache: bool = typer.Option(True, "--cache/--no-cache", help="Use the description cache."),
) -> None:
    """Interactively review each proposed alt text before applying it."""
    config = _config()
    result = run_fix(path, config=config, use_cache=use_cache, dry_run=not apply)

    if not result.tasks:
        console.print("[green]Nothing to review.[/]")
        return

    accepted: list = []
    for index, task in enumerate(result.tasks, start=1):
        occurrence = task.occurrence
        console.rule(f"[{index}/{len(result.tasks)}] {Path(occurrence.file_path).name}:{occurrence.line_start}")
        console.print(f"[dim]source:[/] {occurrence.src}")
        if occurrence.context_heading:
            console.print(f"[dim]section:[/] {occurrence.context_heading}")
        console.print(f"[dim]current alt:[/] {occurrence.alt_text or '(empty)'}")
        proposed = task.new_alt
        if proposed == NEEDS_REVIEW:
            console.print(f"[red]needs review[/] ({task.error or 'failed'})")
            continue
        console.print(f"[green]proposed alt:[/] {proposed}")

        if not sys.stdin.isatty():
            accepted.append(task)
            continue

        choice = typer.prompt(
            "  [a]ccept / [e]dit / [s]kip / [q]uit", default="a", show_default=False
        )
        choice = choice.strip().lower()
        if choice.startswith("q"):
            break
        if choice.startswith("s"):
            continue
        if choice.startswith("e"):
            edited = typer.prompt("  new alt text", default=proposed)
            if edited.strip():
                from .patch import plan_edit

                task.edit = plan_edit(occurrence, edited.strip())
                task.description.text = edited.strip()
                accepted.append(task)
            continue
        accepted.append(task)

    if not apply:
        console.print(f"[yellow]{len(accepted)} change(s) approved, nothing written.[/]")
        console.print("[yellow]Re-run with --apply to write them.[/]")
        return

    written = 0
    by_file: dict[str, list] = {}
    for task in accepted:
        if task.edit is not None:
            by_file.setdefault(task.occurrence.file_path, []).append(task.edit)
    for file_path, edits in by_file.items():
        from .patch import build_patch

        path_obj = Path(file_path)
        original = path_obj.read_bytes().decode("utf-8")
        patch = build_patch(path_obj, original, edits)
        if patch.changed:
            path_obj.write_bytes(patch.updated.encode("utf-8"))
            written += 1
    console.print(f"[green]{written} file(s) updated.[/]")


@app.command()
def demo(
    path: Optional[str] = typer.Argument(None, help="Sample repo to use (defaults to the bundled one)."),
    use_cache: bool = typer.Option(True, "--cache/--no-cache", help="Use pre-generated cached outputs."),
    model: Optional[str] = typer.Option(None, "--model", help="Model id to use."),
) -> None:
    """Run AltFix on the bundled sample repository and show before/after."""
    sample = Path(path) if path else Path(__file__).resolve().parents[2] / "demo" / "sample_repo"
    if not sample.exists():
        console.print(f"[red]Sample repository not found at {sample}[/]")
        raise typer.Exit(code=1)

    config = _config(model=model)
    console.print(
        f"[bold]AltFix demo[/] on {sample}\n"
        f"model: {config.model}\n"
        f"endpoint: {config.base_url}\n"
        f"cache: {'enabled (pre-generated outputs)' if use_cache else 'disabled (live inference)'}"
    )

    results = scan_path(sample)
    table = Table(title="Before", border_style="yellow")
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Line", justify="right")
    table.add_column("Current alt", style="yellow", max_width=30)
    table.add_column("Class", style="green")
    for result in results:
        for image in result.images:
            table.add_row(
                f"{Path(result.file_path).name}:{image.line_start}",
                str(image.line_start),
                image.alt_text or "(empty)",
                image.classification.value,
            )
    console.print(table)

    result = run_fix(sample, config=config, use_cache=use_cache, dry_run=True)
    after = Table(title="After", border_style="green")
    after.add_column("File", style="cyan", no_wrap=True)
    after.add_column("Line", justify="right")
    after.add_column("New alt", style="green", max_width=60)
    for task in result.tasks:
        after.add_row(
            f"{Path(task.occurrence.file_path).name}:{task.occurrence.line_start}",
            str(task.occurrence.line_start),
            task.new_alt,
        )
    console.print(after)

    diff = "".join(patch.diff() for patch in result.patches if patch.changed)
    if diff:
        console.print(Panel(diff, title="Unified diff", border_style="green"))
    console.print(
        f"[dim]{len(result.tasks)} image(s) processed in {result.elapsed_s:.1f}s, "
        f"cache {result.cache_hits}/{result.cache_requests} hits.[/]"
    )
    if not use_cache:
        console.print("[yellow]Live run: every description came from the local model.[/]")


@app.command()
def model_info() -> None:
    """Show the configured model backend and whether it is reachable."""
    config = _config()
    console.print(f"[bold]base url:[/] {config.base_url}")
    console.print(f"[bold]model:[/] {config.model}")
    console.print(f"[bold]quantization:[/] {config.quantization or '(not set)'}")
    console.print(f"[bold]prompt version:[/] {config.prompt_version}")
    console.print(f"[bold]temperature:[/] {config.temperature}")
    console.print(f"[bold]seed:[/] {config.seed}")
    console.print(f"[bold]cache dir:[/] {config.cache_dir}")

    from .client import LocalVisionClient

    client = LocalVisionClient(config)
    console.print(client.server_diagnostics())


if __name__ == "__main__":  # pragma: no cover
    app()
