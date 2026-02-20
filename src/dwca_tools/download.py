"""GBIF occurrence download: request, poll, and fetch."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests
import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TransferSpeedColumn,
)

from .settings import get_gbif_settings, resolve_password

GBIF_API = "https://api.gbif.org/v1/occurrence/download"

console = Console()
app = typer.Typer(no_args_is_help=True)


# ---------------------------------------------------------------------------
# Predicate builders
# ---------------------------------------------------------------------------


def predicate_in(key: str, values: list[str]) -> dict[str, Any]:
    """Build an ``in`` predicate."""
    return {"type": "in", "key": key, "values": values}


def predicate_equals(key: str, value: str) -> dict[str, Any]:
    """Build an ``equals`` predicate."""
    return {"type": "equals", "key": key, "value": value}


def predicate_and(predicates: list[dict[str, Any]]) -> dict[str, Any]:
    """Combine predicates with ``and``. Returns the single predicate if only one."""
    if len(predicates) == 1:
        return predicates[0]
    return {"type": "and", "predicates": predicates}


def build_predicate(
    values: list[str],
    *,
    match_names: bool = False,
    has_images: bool = False,
    country: str | None = None,
    gadm_gid: str | None = None,
    dataset_key: str | None = None,
    extra_predicate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compose a GBIF download predicate from shorthand flags.

    Each flag appends one predicate; they are combined with ``and``.
    """
    key = "VERBATIM_SCIENTIFIC_NAME" if match_names else "TAXON_KEY"
    parts: list[dict[str, Any]] = [predicate_in(key, values)]

    if has_images:
        parts.append(predicate_equals("MEDIA_TYPE", "StillImage"))
    if country:
        parts.append(predicate_equals("COUNTRY", country))
    if gadm_gid:
        parts.append(predicate_equals("GADM_GID", gadm_gid))
    if dataset_key:
        parts.append(predicate_equals("DATASET_KEY", dataset_key))
    if extra_predicate:
        parts.append(extra_predicate)

    return predicate_and(parts)


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------


def load_values_from_file(path: Path) -> list[str]:
    """Read one value per line, skipping blanks."""
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def load_extra_predicate(path: Path) -> dict[str, Any]:
    """Load a JSON predicate from *path*."""
    return json.loads(path.read_text())  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# GBIF API helpers
# ---------------------------------------------------------------------------


def build_request_body(
    predicate: dict[str, Any],
    username: str,
    email: str,
    fmt: str = "DWCA",
) -> dict[str, Any]:
    """Build the JSON body for a GBIF download request."""
    return {
        "creator": username,
        "notificationAddresses": [email],
        "sendNotification": True,
        "format": fmt,
        "predicate": predicate,
    }


def submit_download_request(
    predicate: dict[str, Any],
    username: str,
    password: str,
    email: str,
    fmt: str = "DWCA",
) -> str:
    """Submit a download request to GBIF and return the download key."""
    url = f"{GBIF_API}/request"
    body = build_request_body(predicate, username, email, fmt)
    resp = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        data=json.dumps(body),
        auth=(username, password),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text.strip('"')


def get_download_status(key: str) -> dict[str, Any]:
    """Return status information for download *key*."""
    resp = requests.get(f"{GBIF_API}/{key}", timeout=30)
    resp.raise_for_status()
    return resp.json()  # type: ignore[no-any-return]


def stream_download_file(key: str, output_path: Path) -> None:
    """Stream the completed archive to *output_path* with a Rich progress bar."""
    url = f"{GBIF_API}/request/{key}.zip"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with requests.get(url, stream=True, timeout=30) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))

        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
        ) as progress:
            task = progress.add_task("Downloading", total=total or None)
            with output_path.open("wb") as fh:
                for chunk in resp.iter_content(chunk_size=8192):
                    fh.write(chunk)
                    progress.advance(task, len(chunk))


def poll_until_complete(
    key: str,
    poll_interval: int = 60,
    max_polls: int = 60,
) -> dict[str, Any]:
    """Poll GBIF until the download succeeds, fails, or we hit *max_polls*."""
    for i in range(max_polls):
        info = get_download_status(key)
        status = info.get("status", "UNKNOWN")
        console.print(f"  Status: [bold]{status}[/bold]")

        if status == "SUCCEEDED":
            return info
        if status in {"KILLED", "CANCELLED", "FAILED"}:
            reason = info.get("eraseReason", "unknown")
            console.print(f"[red]Download failed: {reason}[/red]")
            raise typer.Exit(code=1)

        if i < max_polls - 1:
            console.print(f"  Waiting {poll_interval}s before next check...")
            time.sleep(poll_interval)

    console.print("[yellow]Max polls reached. Download may still be processing.[/yellow]")
    console.print(f"  Check status: {GBIF_API}/{key}")
    raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Typer commands
# ---------------------------------------------------------------------------


@app.command()
def request(
    taxa_file: Path | None = typer.Argument(None, help="File with one taxon key/name per line"),
    taxon_keys: str | None = typer.Option(None, "--taxon-keys", help="Comma-separated taxon keys"),
    match_names: bool = typer.Option(
        False, "--match-names", help="Treat values as verbatim scientific names"
    ),
    has_images: bool = typer.Option(False, "--has-images", help="Filter: MEDIA_TYPE=StillImage"),
    country: str | None = typer.Option(None, "--country", help="Filter: COUNTRY (2-letter code)"),
    gadm_gid: str | None = typer.Option(None, "--gadm-gid", help="Filter: GADM_GID"),
    dataset_key: str | None = typer.Option(
        None, "--dataset-key", help="Filter: DATASET_KEY (UUID)"
    ),
    predicate_file: Path | None = typer.Option(
        None, "--predicate", help="JSON predicate file (AND-merged)"
    ),
    fmt: str = typer.Option("DWCA", "--format", help="DWCA, SIMPLE_CSV, or SPECIES_LIST"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file path"),
    no_wait: bool = typer.Option(False, "--no-wait", help="Submit and exit without polling"),
    poll_interval: int = typer.Option(60, "--poll-interval", help="Seconds between status checks"),
    max_polls: int = typer.Option(60, "--max-polls", help="Maximum number of status checks"),
    username: str | None = typer.Option(None, "--username", help="GBIF username (overrides env)"),
    email: str | None = typer.Option(None, "--email", help="Notification email (overrides env)"),
) -> None:
    """Submit a GBIF occurrence download request."""
    # -- resolve taxa values ---------------------------------------------------
    values: list[str] = []
    if taxa_file and taxon_keys:
        console.print("[red]Provide either TAXA_FILE or --taxon-keys, not both.[/red]")
        raise typer.Exit(code=1)
    if taxa_file:
        values = load_values_from_file(taxa_file)
    elif taxon_keys:
        values = [k.strip() for k in taxon_keys.split(",") if k.strip()]

    if not values:
        console.print("[red]No taxon keys or names provided.[/red]")
        raise typer.Exit(code=1)

    # -- resolve credentials ---------------------------------------------------
    settings = get_gbif_settings()
    user = username or settings.username
    mail = email or settings.email

    if not user:
        console.print("[red]Username required (--username or GBIF_USERNAME env var).[/red]")
        raise typer.Exit(code=1)
    if not mail:
        console.print("[red]Email required (--email or GBIF_EMAIL env var).[/red]")
        raise typer.Exit(code=1)

    password = resolve_password(settings, user)

    # -- build & submit --------------------------------------------------------
    extra = load_extra_predicate(predicate_file) if predicate_file else None
    pred = build_predicate(
        values,
        match_names=match_names,
        has_images=has_images,
        country=country,
        gadm_gid=gadm_gid,
        dataset_key=dataset_key,
        extra_predicate=extra,
    )

    console.print(
        f"Submitting download request for {len(values)} {'names' if match_names else 'taxon keys'} ({fmt})"
    )
    try:
        key = submit_download_request(pred, user, password, mail, fmt)
    except requests.HTTPError as exc:
        console.print(f"[red]GBIF API error: {exc}[/red]")
        raise typer.Exit(code=1) from exc

    console.print(f"Download key: [bold]{key}[/bold]")

    if no_wait:
        console.print(f"Status URL: {GBIF_API}/{key}")
        return

    # -- poll & fetch ----------------------------------------------------------
    console.print(f"Polling every {poll_interval}s (max {max_polls} checks)...")
    info = poll_until_complete(key, poll_interval, max_polls)

    doi = info.get("doi")
    if doi:
        console.print(f"DOI: {doi}")
    total_records = info.get("totalRecords")
    if total_records is not None:
        console.print(f"Records: {total_records:,}")

    out = output or Path(f"{key}.zip")
    stream_download_file(key, out)
    console.print(f"Saved to [bold]{out}[/bold]")


@app.command()
def status(
    download_key: str = typer.Argument(..., help="GBIF download key"),
) -> None:
    """Check the status of a GBIF download."""
    try:
        info = get_download_status(download_key)
    except requests.HTTPError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1) from exc

    console.print(f"Status: [bold]{info.get('status', 'UNKNOWN')}[/bold]")
    doi = info.get("doi")
    if doi:
        console.print(f"DOI:    {doi}")
    total_records = info.get("totalRecords")
    if total_records is not None:
        console.print(f"Records: {total_records:,}")
    download_link = info.get("downloadLink")
    if download_link:
        console.print(f"Link:   {download_link}")


@app.command()
def fetch(
    download_key: str = typer.Argument(..., help="GBIF download key"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file path"),
) -> None:
    """Download a completed GBIF archive."""
    # Check it's ready first
    try:
        info = get_download_status(download_key)
    except requests.HTTPError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1) from exc

    dl_status = info.get("status")
    if dl_status != "SUCCEEDED":
        console.print(f"[red]Download not ready (status: {dl_status}).[/red]")
        raise typer.Exit(code=1)

    out = output or Path(f"{download_key}.zip")
    stream_download_file(download_key, out)
    console.print(f"Saved to [bold]{out}[/bold]")
