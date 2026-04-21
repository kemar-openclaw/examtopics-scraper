"""Typer CLI for Exam Topics scraper."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .exporters import export_to_anki, export_to_csv, export_to_json
from .scraper import ExamTopicsScraper, GCP_EXAMS
from .settings import ExamTopicsSettings

console = Console()
app = typer.Typer(
    name="examtopics",
    help="Resilient scraper for Exam Topics certification exams",
    no_args_is_help=True,
)


def _get_settings() -> ExamTopicsSettings:
    """Get settings from environment or defaults."""
    return ExamTopicsSettings()


@app.callback()
def main() -> None:
    """Exam Topics Scraper — scrape certification exam questions."""


@app.command()
def list_exams() -> None:
    """List all available exams."""
    scraper = ExamTopicsScraper()
    exams = scraper.get_available_exams()

    table = Table(title="Available Exams")
    table.add_column("Code", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Provider", style="yellow")

    for code, info in exams.items():
        table.add_row(code, info["name"], info["provider"])

    console.print(table)


@app.command()
def scrape(
    exam_code: str = typer.Argument(help="Exam code (e.g., gcp-pca)"),
    max_pages: int = typer.Option(
        0,
        "--max-pages",
        "-p",
        help="Maximum pages to scrape (0 = unlimited)",
    ),
    output: Path = typer.Option(
        Path("./output/exam.json"),
        "--output",
        "-o",
        help="Output file path",
    ),
    format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: json, csv, anki",
    ),
    use_cache: bool = typer.Option(
        True,
        "--cache/--no-cache",
        help="Use cached data when available",
    ),
    headless: bool = typer.Option(
        True,
        "--headless/--no-headless",
        help="Run browser in headless mode",
    ),
) -> None:
    """Scrape an entire exam with all questions."""

    async def _run() -> None:
        settings = _get_settings()
        settings.headless = headless
        if max_pages > 0:
            settings.max_pages = max_pages

        scraper = ExamTopicsScraper(settings)

        # Validate exam code
        if exam_code not in GCP_EXAMS:
            console.print(f"[red]Error: Unknown exam code '{exam_code}'[/red]")
            console.print("Run 'examtopics list-exams' to see available exams.")
            raise typer.Exit(1)

        exam_info = GCP_EXAMS[exam_code]
        console.print(f"[blue]Scraping {exam_info['name']}...[/blue]")

        with console.status("[bold green]Scraping in progress..."):
            exam = await scraper.scrape_exam(
                exam_code,
                max_pages=max_pages or None,
                use_cache=use_cache,
            )

        # Display results
        table = Table(title=f"Scraping Results: {exam.code}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Total Questions", str(len(exam.questions)))
        table.add_row(
            "With Correct Answers",
            str(exam.correct_answer_count),
        )
        if scraper.session:
            table.add_row("Pages Scraped", str(scraper.session.pages_scraped))
            if scraper.session.duration_seconds:
                table.add_row(
                    "Duration",
                    f"{scraper.session.duration_seconds:.1f}s",
                )
        console.print(table)

        # Export based on format
        output.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            export_to_json(exam, output)
            console.print(f"[green]Saved to {output}[/green]")
        elif format == "csv":
            csv_path = output.with_suffix(".csv")
            export_to_csv(exam, csv_path)
            console.print(f"[green]Saved to {csv_path}[/green]")
        elif format == "anki":
            apkg_path = output.with_suffix(".apkg")
            export_to_anki(exam, apkg_path)
            console.print(f"[green]Saved to {apkg_path}[/green]")
        else:
            console.print(f"[red]Unknown format: {format}[/red]")
            raise typer.Exit(1)

    asyncio.run(_run())


@app.command()
def scrape_page(
    exam_code: str = typer.Argument(help="Exam code (e.g., gcp-pca)"),
    page_num: int = typer.Argument(help="Page number to scrape"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file (default: stdout)",
    ),
) -> None:
    """Scrape a single page of questions."""

    async def _run() -> None:
        settings = _get_settings()
        scraper = ExamTopicsScraper(settings)

        if exam_code not in GCP_EXAMS:
            console.print(f"[red]Error: Unknown exam code '{exam_code}'[/red]")
            raise typer.Exit(1)

        questions = await scraper.scrape_page(exam_code, page_num)

        if not questions:
            console.print("[yellow]No questions found on this page.[/yellow]")
            return

        # Display questions
        for q in questions:
            console.print(f"\n[bold cyan]Question {q.number}:[/bold cyan] {q.text[:100]}...")
            for ans in q.answers:
                mark = "[green]✓[/green]" if ans.is_correct else "[red]✗[/red]"
                console.print(f"  {mark} {ans.letter}. {ans.text[:50]}...")

        # Save if output specified
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            data = [q.model_dump() for q in questions]
            with open(output, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            console.print(f"\n[green]Saved to {output}[/green]")

    asyncio.run(_run())


@app.command()
def config() -> None:
    """Show current configuration."""
    settings = _get_settings()

    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Base URL", settings.base_url)
    table.add_row("Headless", str(settings.headless))
    table.add_row("Output Directory", str(settings.output_dir))
    table.add_row("Cache Directory", str(settings.cache_dir))
    table.add_row("Request Delay (min)", str(settings.request_delay_min))
    table.add_row("Request Delay (max)", str(settings.request_delay_max))
    table.add_row("Max Retries", str(settings.max_retries))
    table.add_row("Use Stealth", str(settings.use_stealth))
    table.add_row("Rotate User Agents", str(settings.rotate_user_agents))
    table.add_row("Use Proxy", str(settings.use_proxy))

    console.print(table)


@app.command()
def clear_cache() -> None:
    """Clear the cache directory."""
    settings = _get_settings()

    if not settings.cache_dir.exists():
        console.print("[yellow]Cache directory doesn't exist.[/yellow]")
        return

    import shutil

    file_count = len(list(settings.cache_dir.glob("*")))
    shutil.rmtree(settings.cache_dir)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[green]Cleared {file_count} cached files.[/green]")


if __name__ == "__main__":  # pragma: no cover
    app()
