#!/usr/bin/env python3
import os
import sys
import time
import json
import httpx
import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

load_dotenv()
console = Console()

API_BASE = os.getenv("API_BASE", "http://localhost:8000/api/v1")

def wait_for_review(review_id: int):
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Running review...", total=None)
        while True:
            r = httpx.get(f"{API_BASE}/reviews/{review_id}/status")
            data = r.json()
            if data["status"] in ("completed", "failed"):
                progress.update(task, completed=True)
                return data
            progress.update(task, description=f"Running review... {data.get('current_agent', '')}")
            time.sleep(3)

@click.group()
def cli():
    """Agentic AI Code Review CLI"""
    pass

@cli.command()
@click.option("--repo", help="Repository URL")
@click.option("--pr", type=int, help="Pull request number")
@click.option("--commit", help="Commit SHA")
@click.option("--diff-file", type=click.Path(exists=True), help="Path to diff file")
@click.option("--local", type=click.Path(exists=True), help="Local repository path")
@click.option("--branch", default="HEAD", help="Branch or ref for local diff")
def start(repo, pr, commit, diff_file, local, branch):
    """Start a new code review."""
    payload = {}
    if diff_file:
        with open(diff_file, "r") as f:
            payload["diff_content"] = f.read()
    elif pr and repo:
        payload = {"repo_url": repo, "pr_number": pr}
    elif commit and repo:
        payload = {"repo_url": repo, "commit_sha": commit}
    elif local:
        payload = {"local_path": local, "branch": branch}
    else:
        console.print("[red]Provide --diff-file, --repo + --pr, --repo + --commit, or --local[/red]")
        sys.exit(1)

    r = httpx.post(f"{API_BASE}/reviews/start", json=payload)
    r.raise_for_status()
    data = r.json()
    review_id = data["review_id"]
    console.print(f"[green]Review started: ID {review_id}[/green]")

    status = wait_for_review(review_id)
    if status["status"] == "failed":
        console.print("[red]Review failed[/red]")
        sys.exit(1)

    r = httpx.get(f"{API_BASE}/reviews/{review_id}")
    review = r.json()
    show_report(review)

@cli.command()
@click.argument("review_id", type=int)
def show(review_id):
    """Show a completed review report."""
    r = httpx.get(f"{API_BASE}/reviews/{review_id}")
    r.raise_for_status()
    show_report(r.json())

@cli.command()
def list():
    """List recent reviews."""
    r = httpx.get(f"{API_BASE}/reviews?limit=20")
    r.raise_for_status()
    reviews = r.json()

    table = Table(title="Recent Reviews")
    table.add_column("ID", style="cyan")
    table.add_column("Target", style="white")
    table.add_column("Status", style="green")
    table.add_column("Recommendation", style="yellow")
    table.add_column("Findings", style="magenta")
    table.add_column("Created", style="dim")

    for rev in reviews:
        target = rev.get("repo_url") or rev.get("commit_sha") or "Raw diff"
        table.add_row(
            str(rev["id"]),
            target[:40],
            rev["status"],
            rev.get("overall_recommendation") or "-",
            str(len(rev.get("findings", []))),
            rev["created_at"][:19].replace("T", " ")
        )
    console.print(table)

def show_report(review):
    sev = review.get("severity_counts", {})
    rec = review.get("overall_recommendation", "N/A")

    color = "green"
    if rec == "BLOCK MERGE": color = "red"
    elif rec == "REQUEST CHANGES": color = "yellow"
    elif rec == "APPROVE WITH COMMENTS": color = "blue"

    console.print(Panel.fit(
        f"[bold]{rec}[/bold]
"
        f"Findings: {len(review.get('findings', []))}  |  "
        f"Critical: {sev.get('critical',0)}  High: {sev.get('high',0)}  "
        f"Medium: {sev.get('medium',0)}  Low: {sev.get('low',0)}",
        title=f"Review #{review['id']}", border_style=color
    ))

    if review.get("summary"):
        console.print(review["summary"])

    findings = review.get("findings", [])
    if not findings:
        console.print("[dim]No findings.[/dim]")
        return

    table = Table(title="Findings")
    table.add_column("Severity", style="bold")
    table.add_column("Category")
    table.add_column("File")
    table.add_column("Title", style="white")
    table.add_column("Agent")

    for f in findings:
        sev_color = {"critical":"red","high":"yellow","medium":"blue","low":"dim","optional":"dim"}.get(f["severity"], "white")
        table.add_row(
            f"[{sev_color}]{f['severity']}[/{sev_color}]",
            f["category"],
            f.get("file_path", "-")[:30],
            f["title"][:50],
            f["agent_name"]
        )
    console.print(table)

if __name__ == "__main__":
    cli()
