"""Generate statistics command for AWS Identity Center resources.

This module provides the main statistics generation command with comprehensive
filtering, output format, and category selection options.
"""

import asyncio
import logging
from typing import List, Optional

import typer
from rich.console import Console

from ..common import cache_option, profile_option, region_option, verbose_option
from .helpers import (
    create_statistics_manager,
    format_statistics_summary,
    handle_statistics_error,
    parse_filters,
    save_output_to_file,
    show_progress_info,
    validate_categories,
    validate_output_format,
)

# Setup logging and console
console = Console()
logger = logging.getLogger(__name__)


def generate_statistics(
    categories: Optional[List[str]] = typer.Option(
        None,
        "--category",
        "-c",
        help="Statistics categories to generate (users, groups, permission-sets, accounts, assignments, governance, all). Can be specified multiple times.",
    ),
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: json, csv, text, table (default: table)",
    ),
    output_file: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (prints to console if not specified)",
    ),
    filters: Optional[List[str]] = typer.Option(
        None,
        "--filter",
        help="Filter results (format: key=value). Examples: account=123456789012, user=john.doe@example.com, tag:env=prod. Can be specified multiple times.",
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
    """Generate comprehensive statistics for AWS Identity Center resources.

    This command analyzes your AWS Identity Center environment and generates
    detailed statistics about users, groups, permission sets, accounts, and
    assignment patterns. It can help identify orphaned resources, over-privileged
    access, and governance gaps.

    Examples:
        # Generate all statistics with default table output
        awsideman statistics generate --profile sso-test-1

        # Generate user and group statistics in JSON format
        awsideman statistics generate -c users -c groups -f json --profile sso-test-1

        # Generate governance statistics with filtering
        awsideman statistics generate -c governance --filter account=123456789012 --profile sso-test-1

        # Generate statistics for production accounts using tag filtering
        awsideman statistics generate --filter tag:env=prod --profile sso-test-1

        # Generate statistics with historical comparison
        awsideman statistics generate --include-historical --backup-path /path/to/backup --profile sso-test-1

        # Save detailed report to file
        awsideman statistics generate -f json -o report.json --profile sso-test-1
    """
    try:
        # Validate parameters
        validated_categories = validate_categories(categories)
        validated_format = validate_output_format(output_format)
        parsed_filters = parse_filters(filters)

        if verbose:
            console.print(
                f"[blue]Generating statistics for categories: {', '.join(validated_categories)}[/blue]"
            )
            console.print(f"[blue]Output format: {validated_format}[/blue]")
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

        # Run the async statistics generation
        report = asyncio.run(
            stats_manager.generate_statistics(
                categories=validated_categories,
                filters=parsed_filters,
                include_historical=include_historical,
                backup_path=backup_path,
            )
        )

        show_progress_info("Processing and formatting results...", verbose)

        # Format output based on requested format
        if validated_format == "json":
            content = stats_manager.exporter.export_to_json(report)
        elif validated_format == "csv":
            content = stats_manager.exporter.export_to_csv(report)
        elif validated_format == "text":
            content = stats_manager.exporter.export_to_text(report)
        elif validated_format == "table":
            # For table format, show summary and detailed sections
            format_statistics_summary(report, validated_categories)
            if output_file:
                # If saving to file, use text format
                content = stats_manager.exporter.export_to_text(report)
                save_output_to_file(content, output_file, "text")
            return
        else:
            console.print(f"[red]Unsupported format: {validated_format}[/red]")
            raise typer.Exit(1)

        # Save or display output
        save_output_to_file(content, output_file, validated_format)

        # Show summary if not in table format and verbose
        if verbose and validated_format != "table":
            console.print("\n")
            format_statistics_summary(report)

    except Exception as e:
        handle_statistics_error(e, "statistics generation", verbose)
        raise typer.Exit(1)


def generate_user_statistics(
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: json, csv, text, table (default: table)",
    ),
    output_file: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (prints to console if not specified)",
    ),
    filters: Optional[List[str]] = typer.Option(
        None,
        "--filter",
        help="Filter results (format: key=value). Can be specified multiple times.",
    ),
    profile: Optional[str] = profile_option(),
    region: Optional[str] = region_option(),
    no_cache: bool = cache_option(),
    verbose: bool = verbose_option(),
) -> None:
    """Generate statistics specifically for users and groups.

    This command focuses on user and group metrics including distribution,
    membership patterns, and orphaned resources.

    Examples:
        # Generate user statistics in table format
        awsideman statistics users --profile sso-test-1

        # Export user statistics to CSV
        awsideman statistics users -f csv -o users.csv --profile sso-test-1

        # Filter user statistics by specific criteria
        awsideman statistics users --filter user=john.doe@example.com --profile sso-test-1
    """
    # Delegate to main generate command with users category
    generate_statistics(
        categories=["users"],
        output_format=output_format,
        output_file=output_file,
        filters=filters,
        include_historical=False,
        backup_path=None,
        profile=profile,
        region=region,
        no_cache=no_cache,
        verbose=verbose,
    )


def generate_group_statistics(
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: json, csv, text, table (default: table)",
    ),
    output_file: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (prints to console if not specified)",
    ),
    filters: Optional[List[str]] = typer.Option(
        None,
        "--filter",
        help="Filter results (format: key=value). Can be specified multiple times.",
    ),
    profile: Optional[str] = profile_option(),
    region: Optional[str] = region_option(),
    no_cache: bool = cache_option(),
    verbose: bool = verbose_option(),
) -> None:
    """Generate statistics specifically for groups.

    This command focuses on group metrics including membership distribution,
    assignment patterns, and orphaned groups.

    Examples:
        # Generate group statistics in table format
        awsideman statistics groups --profile sso-test-1

        # Export group statistics to JSON
        awsideman statistics groups -f json -o groups.json --profile sso-test-1
    """
    # Delegate to main generate command with groups category
    generate_statistics(
        categories=["groups"],
        output_format=output_format,
        output_file=output_file,
        filters=filters,
        include_historical=False,
        backup_path=None,
        profile=profile,
        region=region,
        no_cache=no_cache,
        verbose=verbose,
    )


def generate_permission_set_statistics(
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: json, csv, text, table (default: table)",
    ),
    output_file: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (prints to console if not specified)",
    ),
    filters: Optional[List[str]] = typer.Option(
        None,
        "--filter",
        help="Filter results (format: key=value). Can be specified multiple times.",
    ),
    profile: Optional[str] = profile_option(),
    region: Optional[str] = region_option(),
    no_cache: bool = cache_option(),
    verbose: bool = verbose_option(),
) -> None:
    """Generate statistics specifically for permission sets.

    This command focuses on permission set metrics including usage patterns,
    assignment distribution, and unused permission sets.

    Examples:
        # Generate permission set statistics
        awsideman statistics permission-sets --profile sso-test-1

        # Export to CSV with filtering
        awsideman statistics permission-sets -f csv --filter account=123456789012 --profile sso-test-1
    """
    # Delegate to main generate command with permission-sets category
    generate_statistics(
        categories=["permission-sets"],
        output_format=output_format,
        output_file=output_file,
        filters=filters,
        include_historical=False,
        backup_path=None,
        profile=profile,
        region=region,
        no_cache=no_cache,
        verbose=verbose,
    )


def generate_account_statistics(
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: json, csv, text, table (default: table)",
    ),
    output_file: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (prints to console if not specified)",
    ),
    filters: Optional[List[str]] = typer.Option(
        None,
        "--filter",
        help="Filter results (format: key=value). Can be specified multiple times.",
    ),
    profile: Optional[str] = profile_option(),
    region: Optional[str] = region_option(),
    no_cache: bool = cache_option(),
    verbose: bool = verbose_option(),
) -> None:
    """Generate statistics specifically for AWS accounts.

    This command focuses on account metrics including access distribution,
    assignment coverage, and accounts with no assignments.

    Examples:
        # Generate account statistics
        awsideman statistics accounts --profile sso-test-1

        # Export detailed account analysis
        awsideman statistics accounts -f json -o accounts.json --profile sso-test-1
    """
    # Delegate to main generate command with accounts category
    generate_statistics(
        categories=["accounts"],
        output_format=output_format,
        output_file=output_file,
        filters=filters,
        include_historical=False,
        backup_path=None,
        profile=profile,
        region=region,
        no_cache=no_cache,
        verbose=verbose,
    )


def generate_assignment_statistics(
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: json, csv, text, table (default: table)",
    ),
    output_file: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (prints to console if not specified)",
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
    """Generate statistics specifically for assignments.

    This command focuses on assignment patterns including distribution,
    growth trends, and high-access users or groups.

    Examples:
        # Generate assignment statistics
        awsideman statistics assignments --profile sso-test-1

        # Include historical trend analysis
        awsideman statistics assignments --include-historical --profile sso-test-1

        # Export with specific backup comparison
        awsideman statistics assignments --backup-path /path/to/backup -f json --profile sso-test-1
    """
    # Delegate to main generate command with assignments category
    generate_statistics(
        categories=["assignments"],
        output_format=output_format,
        output_file=output_file,
        filters=filters,
        include_historical=include_historical,
        backup_path=backup_path,
        profile=profile,
        region=region,
        no_cache=no_cache,
        verbose=verbose,
    )


def generate_governance_statistics(
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: json, csv, text, table (default: table)",
    ),
    output_file: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (prints to console if not specified)",
    ),
    filters: Optional[List[str]] = typer.Option(
        None,
        "--filter",
        help="Filter results (format: key=value). Can be specified multiple times.",
    ),
    profile: Optional[str] = profile_option(),
    region: Optional[str] = region_option(),
    no_cache: bool = cache_option(),
    verbose: bool = verbose_option(),
) -> None:
    """Generate governance-oriented statistics and analysis.

    This command focuses on governance metrics including access matrices,
    privileged access detection, and compliance gap identification.

    Examples:
        # Generate governance analysis
        awsideman statistics governance --profile sso-test-1

        # Export governance report for compliance review
        awsideman statistics governance -f json -o governance-report.json --profile sso-test-1

        # Focus on specific account governance
        awsideman statistics governance --filter account=123456789012 --profile sso-test-1
    """
    # Delegate to main generate command with governance category
    generate_statistics(
        categories=["governance"],
        output_format=output_format,
        output_file=output_file,
        filters=filters,
        include_historical=False,
        backup_path=None,
        profile=profile,
        region=region,
        no_cache=no_cache,
        verbose=verbose,
    )
