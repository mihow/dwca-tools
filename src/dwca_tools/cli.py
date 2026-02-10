"""
Command-line interface for dwca-tools.

This module provides the main entry point for the CLI with support for
Darwin Core Archive and iNaturalist open data operations.
"""

from __future__ import annotations

import argparse
import sys

from dwca_tools import __version__
from dwca_tools.config import get_settings
from dwca_tools.core import process_example


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="dwca-tools",
        description="Tools for working with Darwin Core Archive and iNaturalist open data",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Example: 'run' command
    run_parser = subparsers.add_parser("run", help="Run the main process")
    run_parser.add_argument(
        "--name",
        type=str,
        default="example",
        help="Name for the example (default: example)",
    )

    # Example: 'info' command
    subparsers.add_parser("info", help="Show application info")

    # iNaturalist commands
    inaturalist_parser = subparsers.add_parser(
        "inaturalist", help="iNaturalist open data commands"
    )
    inaturalist_subparsers = inaturalist_parser.add_subparsers(
        dest="inaturalist_command", help="Available iNaturalist commands"
    )

    # Download command
    download_parser = inaturalist_subparsers.add_parser(
        "download", help="Download iNaturalist data files"
    )
    download_parser.add_argument(
        "data_type",
        choices=["taxa", "observations", "photos", "all"],
        help="Type of data to download",
    )
    download_parser.add_argument(
        "--force", action="store_true", help="Force re-download even if cached"
    )

    # Extract command
    extract_parser = inaturalist_subparsers.add_parser(
        "extract", help="Extract and filter iNaturalist data"
    )
    extract_parser.add_argument(
        "data_type",
        choices=["taxa", "observations", "photos"],
        help="Type of data to extract",
    )
    extract_parser.add_argument(
        "--filter",
        action="append",
        metavar="KEY=VALUE",
        help="Filter by field (e.g., --filter rank=species)",
    )
    extract_parser.add_argument(
        "--output", type=str, help="Output file path (JSON format)"
    )

    return parser


def cmd_run(args: argparse.Namespace) -> int:
    """Handle the 'run' command."""
    settings = get_settings()
    if args.debug:
        print(f"Debug mode enabled. Settings: {settings}")

    result = process_example(args.name)
    if result.success:
        print(f"Success: {result.message}")
        return 0
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        return 1


def cmd_inaturalist(args: argparse.Namespace) -> int:
    """Handle the 'inaturalist' command."""
    if not args.inaturalist_command:
        print("Error: Please specify a subcommand (download or extract)", file=sys.stderr)
        return 1

    if args.inaturalist_command == "download":
        return cmd_inaturalist_download(args)
    elif args.inaturalist_command == "extract":
        return cmd_inaturalist_extract(args)

    return 1


def cmd_inaturalist_download(args: argparse.Namespace) -> int:
    """Handle the 'inaturalist download' command."""
    from dwca_tools.inaturalist.downloader import (
        download_observations,
        download_photos,
        download_taxa,
    )

    data_types = []
    if args.data_type == "all":
        data_types = ["taxa", "observations", "photos"]
    else:
        data_types = [args.data_type]

    for data_type in data_types:
        print(f"Downloading {data_type}...")
        try:
            if data_type == "taxa":
                path, downloaded = download_taxa(force=args.force)
            elif data_type == "observations":
                path, downloaded = download_observations(force=args.force)
            elif data_type == "photos":
                path, downloaded = download_photos(force=args.force)
            else:
                continue

            if downloaded:
                print(f"✓ Downloaded {data_type} to: {path}")
            else:
                print(f"✓ Using cached {data_type} file: {path}")

        except Exception as e:
            print(f"✗ Error downloading {data_type}: {e}", file=sys.stderr)
            return 1

    return 0


def cmd_inaturalist_extract(args: argparse.Namespace) -> int:
    """Handle the 'inaturalist extract' command."""
    import json

    from dwca_tools.inaturalist.extractor import (
        extract_observations,
        extract_photos,
        extract_taxa,
    )

    # Parse filters
    filters = {}
    if args.filter:
        for filter_str in args.filter:
            try:
                key, value = filter_str.split("=", 1)
                # Try to parse value as list if it contains commas
                if "," in value:
                    filters[key] = value.split(",")
                else:
                    filters[key] = value
            except ValueError:
                print(f"Warning: Invalid filter format: {filter_str}", file=sys.stderr)

    print(f"Extracting {args.data_type} with filters: {filters}")

    try:
        if args.data_type == "taxa":
            records, metadata = extract_taxa(filters=filters)
        elif args.data_type == "observations":
            records, metadata = extract_observations(filters=filters)
        elif args.data_type == "photos":
            records, metadata = extract_photos(filters=filters)
        else:
            print(f"Error: Unknown data type: {args.data_type}", file=sys.stderr)
            return 1

        print(f"✓ Extracted {metadata.total_records} records")

        # Output results
        if args.output:
            output_data = {
                "records": [r.model_dump() for r in records],
                "metadata": metadata.model_dump(mode="json"),
            }
            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2, default=str)
            print(f"✓ Saved results to: {args.output}")
        else:
            # Print summary
            print(f"\nSummary:")
            print(f"  Source: {metadata.source}")
            print(f"  Total records: {metadata.total_records}")
            print(f"  Filters: {metadata.filters}")

    except Exception as e:
        print(f"✗ Error extracting {args.data_type}: {e}", file=sys.stderr)
        if args.debug:
            raise
        return 1

    return 0


def cmd_info(_args: argparse.Namespace) -> int:
    """Handle the 'info' command."""
    settings = get_settings()
    print(f"Application: {settings.app_name}")
    print(f"Version: {__version__}")
    print(f"Environment: {settings.app_env}")
    print(f"Debug: {settings.debug}")
    return 0


def main() -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        "run": cmd_run,
        "info": cmd_info,
        "inaturalist": cmd_inaturalist,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
