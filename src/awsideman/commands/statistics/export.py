"""Export statistics command for AWS Identity Center resources.

This module provides specialized export functionality for statistics data
with format-specific optimizations and batch export capabilities.
"""

import asyncio
import logging
from typing import List, Optional

import typer
from rich.console import Console

from ..common import cache_option, profile_option, region_option, verbose_option
from .helpers import (
    create_statistics_manager,
    handle_statistics_error,
    parse_filters,
    show_progress_info,
    validate_categories,
    validate_output_format,
)

# Setup logging and console
console = Console()
logger = logging.getLogger(__name__)


def export_statistics(
    format_type: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Export format: json, csv, text (default: json)",
    ),
    output_file: str = typer.Option(
        ...,
        "--output",
        "-o",
        help="Output file path (required for export command)",
    ),
    categories: Optional[List[str]] = typer.Option(
        None,
        "--category",
        "-c",
        help="Statistics categories to export (users, groups, permission-sets, accounts, assignments, governance, all). Can be specified multiple times.",
    ),
    filters: Optional[List[str]] = typer.Option(
        None,
        "--filter",
        help="Filter results (format: key=value). Can be specified multiple times.",
    ),
    include_historical: bool = typer.Option(
        False,
        "--include-historical",
        help="Include historical comparison using backup snapshots",
    ),
    backup_path: Optional[str] = typer.Option(
        None,
        "--backup-path",
        help="Path to backup snapshot for historical comparison",
    ),
    split_categories: bool = typer.Option(
        False,
        "--split-categories",
        help="Export each category to a separate file (for CSV format)",
    ),
    profile: Optional[str] = profile_option(),
    region: Optional[str] = region_option(),
    no_cache: bool = cache_option(),
    verbose: bool = verbose_option(),
) -> None:
    """Export statistics data to files in various formats.

    This command is optimized for exporting statistics data to files with
    format-specific optimizations and batch processing capabilities.

    Examples:
        # Export all statistics to JSON
        awsideman statistics export -f json -o report.json --profile floccus

        # Export specific categories to CSV with split files
        awsideman statistics export -f csv -o stats.csv -c users -c groups --split-categories --profile floccus

        # Export governance data with historical comparison
        awsideman statistics export -f json -o governance.json -c governance --include-historical --profile floccus

        # Export filtered data
        awsideman statistics export -f csv -o filtered.csv --filter account=123456789012 --profile floccus
    """
    try:
        # Validate parameters
        validated_categories = validate_categories(categories)
        validated_format = validate_output_format(format_type)
        parsed_filters = parse_filters(filters)

        if verbose:
            console.print(
                f"[blue]Exporting statistics for categories: {', '.join(validated_categories)}[/blue]"
            )
            console.print(f"[blue]Export format: {validated_format}[/blue]")
            console.print(f"[blue]Output file: {output_file}[/blue]")
            if parsed_filters:
                console.print(f"[blue]Filters: {parsed_filters}[/blue]")

        # Create statistics manager
        show_progress_info("Setting up AWS clients and validation...", verbose)
        stats_manager, instance_arn = create_statistics_manager(
            profile=profile,
            region=region,
            no_cache=no_cache,
            verbose=verbose,
        )

        # Generate statistics
        show_progress_info("Collecting data from AWS Identity Center...", verbose)

        report = asyncio.run(
            stats_manager.generate_statistics(
                categories=validated_categories,
                filters=parsed_filters,
                include_historical=include_historical,
                backup_path=backup_path,
            )
        )

        show_progress_info("Exporting data to file(s)...", verbose)

        # Handle split categories for CSV
        if split_categories and validated_format == "csv":
            # Export each category to a separate file
            base_name = output_file.rsplit(".", 1)[0] if "." in output_file else output_file
            extension = output_file.rsplit(".", 1)[1] if "." in output_file else "csv"

            for category in validated_categories:
                category_file = f"{base_name}_{category}.{extension}"
                category_content = stats_manager.exporter.export_to_csv(report, category=category)

                with open(category_file, "w", encoding="utf-8") as f:
                    f.write(category_content)

                console.print(f"[green]✓ Exported {category} to: {category_file}[/green]")
        else:
            # Export all data to single file
            if validated_format == "json":
                content = stats_manager.exporter.export_to_json(report)
            elif validated_format == "csv":
                content = stats_manager.exporter.export_to_csv(report)
            elif validated_format == "text":
                content = stats_manager.exporter.export_to_text(report)
            else:
                console.print(f"[red]Unsupported export format: {validated_format}[/red]")
                raise typer.Exit(1)

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(content)

            console.print(f"[green]✓ Statistics exported to: {output_file}[/green]")

        # Show summary
        if verbose:
            console.print("[blue]Export completed successfully[/blue]")

    except Exception as e:
        handle_statistics_error(e, "statistics export", verbose)
        raise typer.Exit(1)


def export_json(
    output_file: str = typer.Option(
        ...,
        "--output",
        "-o",
        help="JSON output file path (required)",
    ),
    categories: Optional[List[str]] = typer.Option(
        None,
        "--category",
        "-c",
        help="Statistics categories to export. Can be specified multiple times.",
    ),
    filters: Optional[List[str]] = typer.Option(
        None,
        "--filter",
        help="Filter results (format: key=value). Can be specified multiple times.",
    ),
    include_historical: bool = typer.Option(
        False,
        "--include-historical",
        help="Include historical comparison using backup snapshots",
    ),
    backup_path: Optional[str] = typer.Option(
        None,
        "--backup-path",
        help="Path to backup snapshot for historical comparison",
    ),
    pretty: bool = typer.Option(
        True,
        "--pretty/--compact",
        help="Pretty-print JSON output (default: pretty)",
    ),
    profile: Optional[str] = profile_option(),
    region: Optional[str] = region_option(),
    no_cache: bool = cache_option(),
    verbose: bool = verbose_option(),
) -> None:
    """Export statistics to JSON format with structured data.

    This command exports statistics in JSON format optimized for programmatic
    access and integration with other tools.

    Examples:
        # Export all statistics to pretty JSON
        awsideman statistics export-json -o report.json --profile floccus

        # Export compact JSON for specific categories
        awsideman statistics export-json -o users.json -c users --compact --profile floccus

        # Export with historical data
        awsideman statistics export-json -o trend.json --include-historical --profile floccus
    """
    # Delegate to main export command with JSON format
    export_statistics(
        format_type="json",
        output_file=output_file,
        categories=categories,
        filters=filters,
        include_historical=include_historical,
        backup_path=backup_path,
        split_categories=False,
        profile=profile,
        region=region,
        no_cache=no_cache,
        verbose=verbose,
    )


def export_csv(
    output_file: str = typer.Option(
        ...,
        "--output",
        "-o",
        help="CSV output file path (required)",
    ),
    categories: Optional[List[str]] = typer.Option(
        None,
        "--category",
        "-c",
        help="Statistics categories to export. Can be specified multiple times.",
    ),
    filters: Optional[List[str]] = typer.Option(
        None,
        "--filter",
        help="Filter results (format: key=value). Can be specified multiple times.",
    ),
    split_categories: bool = typer.Option(
        False,
        "--split-categories",
        help="Export each category to a separate CSV file",
    ),
    profile: Optional[str] = profile_option(),
    region: Optional[str] = region_option(),
    no_cache: bool = cache_option(),
    verbose: bool = verbose_option(),
) -> None:
    """Export statistics to CSV format for spreadsheet analysis.

    This command exports statistics in CSV format optimized for analysis
    in spreadsheet applications like Excel or Google Sheets.

    Examples:
        # Export all statistics to single CSV
        awsideman statistics export-csv -o report.csv --profile floccus

        # Export with split files for each category
        awsideman statistics export-csv -o stats.csv --split-categories --profile floccus

        # Export specific categories
        awsideman statistics export-csv -o users.csv -c users -c groups --profile floccus
    """
    # Delegate to main export command with CSV format
    export_statistics(
        format_type="csv",
        output_file=output_file,
        categories=categories,
        filters=filters,
        include_historical=False,  # CSV doesn't support historical data well
        backup_path=None,
        split_categories=split_categories,
        profile=profile,
        region=region,
        no_cache=no_cache,
        verbose=verbose,
    )


def export_text(
    output_file: str = typer.Option(
        ...,
        "--output",
        "-o",
        help="Text output file path (required)",
    ),
    categories: Optional[List[str]] = typer.Option(
        None,
        "--category",
        "-c",
        help="Statistics categories to export. Can be specified multiple times.",
    ),
    filters: Optional[List[str]] = typer.Option(
        None,
        "--filter",
        help="Filter results (format: key=value). Can be specified multiple times.",
    ),
    include_historical: bool = typer.Option(
        False,
        "--include-historical",
        help="Include historical comparison using backup snapshots",
    ),
    backup_path: Optional[str] = typer.Option(
        None,
        "--backup-path",
        help="Path to backup snapshot for historical comparison",
    ),
    profile: Optional[str] = profile_option(),
    region: Optional[str] = region_option(),
    no_cache: bool = cache_option(),
    verbose: bool = verbose_option(),
) -> None:
    """Export statistics to formatted text for human-readable reports.

    This command exports statistics in formatted text suitable for
    documentation, reports, and human review.

    Examples:
        # Export comprehensive text report
        awsideman statistics export-text -o report.txt --profile floccus

        # Export governance report with historical data
        awsideman statistics export-text -o governance.txt -c governance --include-historical --profile floccus

        # Export filtered report
        awsideman statistics export-text -o filtered.txt --filter account=123456789012 --profile floccus
    """
    # Delegate to main export command with text format
    export_statistics(
        format_type="text",
        output_file=output_file,
        categories=categories,
        filters=filters,
        include_historical=include_historical,
        backup_path=backup_path,
        split_categories=False,
        profile=profile,
        region=region,
        no_cache=no_cache,
        verbose=verbose,
    )
