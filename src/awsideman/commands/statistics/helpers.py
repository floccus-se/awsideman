"""Helper functions for statistics CLI commands.

This module provides shared functionality for statistics commands including:
- Statistics manager creation with cache integration
- Common parameter validation
- Output formatting utilities
- Error handling specific to statistics operations
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import typer
from rich.console import Console
from rich.table import Table

from ...statistics.manager import StatisticsManager
from ..common import (
    extract_standard_params,
    get_aws_client_manager,
    handle_aws_error,
    show_cache_info,
)

# Shared instances
console = Console()
logger = logging.getLogger(__name__)


def create_statistics_manager(
    profile: Optional[str] = None,
    region: Optional[str] = None,
    no_cache: bool = False,
    verbose: bool = False,
) -> Tuple[StatisticsManager, str]:
    """
    Create a StatisticsManager with proper AWS client setup and validation.

    Args:
        profile: AWS profile name
        region: AWS region
        no_cache: Whether caching is disabled
        verbose: Whether to show verbose output

    Returns:
        Tuple of (StatisticsManager instance, instance_arn)

    Raises:
        typer.Exit: If setup fails
    """
    try:
        # Extract and process standard command parameters
        profile_param, region_param, enable_caching = extract_standard_params(
            profile, region, no_cache
        )

        # Get AWS client manager with cache integration
        aws_client = get_aws_client_manager(
            profile=profile_param,
            region=region_param,
            enable_caching=enable_caching,
            verbose=verbose,
        )

        # Get Identity Center instance ARN
        from ...utils.validators import validate_profile, validate_sso_instance

        # First validate the profile to get profile data
        profile_name, profile_data = validate_profile(profile_param)
        instance_arn, identity_store_id = validate_sso_instance(profile_data, profile_name)

        if verbose:
            console.print(f"[blue]Identity Center Instance: {instance_arn}[/blue]")
            console.print(f"[blue]Identity Store ID: {identity_store_id}[/blue]")

        # Show cache info if verbose
        show_cache_info(verbose=verbose, profile=profile)

        # Create statistics manager
        stats_manager = StatisticsManager(client_manager=aws_client, instance_arn=instance_arn)

        return stats_manager, instance_arn

    except Exception as e:
        handle_aws_error(e, "statistics manager setup", verbose=verbose)
        raise typer.Exit(1)


def validate_categories(categories: Optional[List[str]]) -> List[str]:
    """
    Validate and normalize statistics categories.

    Args:
        categories: List of category names to validate

    Returns:
        List of validated category names

    Raises:
        typer.Exit: If invalid categories are provided
    """
    valid_categories = {
        "users",
        "groups",
        "permission-sets",
        "accounts",
        "assignments",
        "governance",
        "all",
    }

    if not categories:
        return ["all"]

    # Normalize category names
    normalized_categories = []
    for category in categories:
        normalized = category.lower().replace("_", "-")
        if normalized not in valid_categories:
            console.print(f"[red]Error: Invalid category '{category}'[/red]")
            console.print(f"Valid categories: {', '.join(sorted(valid_categories))}")
            raise typer.Exit(1)
        normalized_categories.append(normalized)

    # If "all" is specified, return all categories except "all"
    if "all" in normalized_categories:
        return [cat for cat in valid_categories if cat != "all"]

    return normalized_categories


def validate_output_format(output_format: str) -> str:
    """
    Validate output format parameter.

    Args:
        output_format: Format string to validate

    Returns:
        Validated format string

    Raises:
        typer.Exit: If invalid format is provided
    """
    valid_formats = {"json", "csv", "text", "table"}
    normalized_format = output_format.lower()

    if normalized_format not in valid_formats:
        console.print(f"[red]Error: Invalid output format '{output_format}'[/red]")
        console.print(f"Valid formats: {', '.join(sorted(valid_formats))}")
        raise typer.Exit(1)

    return normalized_format


def parse_filters(filter_strings: Optional[List[str]]) -> Dict[str, Any]:
    """
    Parse filter strings into a filter dictionary.

    Args:
        filter_strings: List of filter strings in format "key=value"

    Returns:
        Dictionary of parsed filters

    Raises:
        typer.Exit: If filter format is invalid
    """
    filters: Dict[str, str] = {}

    if not filter_strings:
        return filters

    for filter_str in filter_strings:
        if "=" not in filter_str:
            console.print(f"[red]Error: Invalid filter format '{filter_str}'[/red]")
            console.print("Filters must be in format 'key=value'")
            console.print("Examples: account=123456789012, user=john.doe@example.com, tag:env=prod")
            raise typer.Exit(1)

        key, value = filter_str.split("=", 1)
        key = key.strip().lower()
        value = value.strip()

        # Handle tag:key=value format
        if key.startswith("tag:"):
            # For tag:key=value format, store as tag:key -> value
            # This will be processed in the manager's _apply_filters method
            filters[key] = value
        else:
            # Validate non-tag filter keys
            valid_filter_keys = {
                "account",
                "user",
                "group",
                "permission-set",
                "assignment-type",
                "tag",
            }

            if key not in valid_filter_keys:
                console.print(f"[red]Error: Invalid filter key '{key}'[/red]")
                console.print(f"Valid filter keys: {', '.join(sorted(valid_filter_keys))}")
                console.print("For tag filtering, use format: tag:key=value (e.g., tag:env=prod)")
                raise typer.Exit(1)

            filters[key] = value

    return filters


def format_statistics_summary(report: Any, categories: Optional[List[str]] = None) -> None:
    """
    Display a formatted summary of statistics report.

    Args:
        report: StatisticsReport object to summarize
        categories: Specific categories to show (if None, shows all)
    """
    console.print("\n[bold blue]Statistics Summary[/bold blue]")

    # Create summary table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Category", style="cyan")
    table.add_column("Key Metrics", style="white")

    # Show all categories if none specified or if "all" is in categories, otherwise show only requested ones
    show_all = categories is None or len(categories) == 0 or (categories and "all" in categories)

    # Add user/group metrics
    if (
        (show_all or (categories and ("users" in categories or "groups" in categories)))
        and hasattr(report, "user_group_metrics")
        and report.user_group_metrics
    ):
        metrics = report.user_group_metrics

        if show_all or (categories and "users" in categories):
            user_info = f"Total: {metrics.total_users}"
            if metrics.orphaned_users:
                user_info += f", Orphaned: {len(metrics.orphaned_users)}"
            if metrics.disabled_users:
                user_info += f", Disabled: {len(metrics.disabled_users)}"
            if metrics.largest_groups:
                user_info += f", Largest Group: {metrics.largest_groups[0][1]} users"
            table.add_row("Users", user_info)

        if show_all or (categories and "groups" in categories):
            group_info = f"Total: {metrics.total_groups}"
            if metrics.orphaned_groups:
                group_info += f", Orphaned: {len(metrics.orphaned_groups)}"
            if metrics.largest_groups:
                group_info += f", Largest: {metrics.largest_groups[0][0]} ({metrics.largest_groups[0][1]} users)"
            table.add_row("Groups", group_info)

    # Add permission set metrics
    if (
        (show_all or (categories and "permission-sets" in categories))
        and hasattr(report, "permission_set_metrics")
        and report.permission_set_metrics
    ):
        metrics = report.permission_set_metrics
        ps_info = f"Total: {metrics.total_permission_sets}"
        if metrics.unused_permission_sets:
            ps_info += f", Unused: {len(metrics.unused_permission_sets)}"
        if metrics.privileged_permission_sets:
            ps_info += f", Privileged: {len(metrics.privileged_permission_sets)}"
        if metrics.most_assigned_permission_sets:
            ps_info += f", Most Used: {metrics.most_assigned_permission_sets[0][0]}"
        table.add_row("Permission Sets", ps_info)

    # Add account metrics
    if (
        (show_all or (categories and "accounts" in categories))
        and hasattr(report, "account_metrics")
        and report.account_metrics
    ):
        metrics = report.account_metrics
        account_info = f"Total: {metrics.total_accounts}"
        if metrics.accounts_with_no_assignments:
            account_info += f", No Assignments: {len(metrics.accounts_with_no_assignments)}"
        if metrics.cross_account_users:
            account_info += f", Cross-Account Users: {len(metrics.cross_account_users)}"
        table.add_row("Accounts", account_info)

    # Add assignment patterns
    if (
        (show_all or (categories and "assignments" in categories))
        and hasattr(report, "assignment_patterns")
        and report.assignment_patterns
    ):
        patterns = report.assignment_patterns
        avg_assignments = f"Avg per User: {patterns.average_assignments_per_user:.1f}"
        if patterns.users_with_most_assignments:
            avg_assignments += f", Max: {patterns.users_with_most_assignments[0][1]}"
        table.add_row("Assignments", avg_assignments)

    # Add governance view
    if (
        (show_all or (categories and "governance" in categories))
        and hasattr(report, "governance_view")
        and report.governance_view
    ):
        governance = report.governance_view
        gov_info = f"Compliance Gaps: {len(governance.compliance_gaps)}"
        if governance.privileged_access_report.admin_permission_sets:
            gov_info += (
                f", Admin PS: {len(governance.privileged_access_report.admin_permission_sets)}"
            )
        if governance.empty_mappings.groups_with_no_members:
            gov_info += f", Empty Groups: {len(governance.empty_mappings.groups_with_no_members)}"
        table.add_row("Governance", gov_info)

    console.print(table)

    # Show detailed category-specific information
    if categories and len(categories) == 1:
        _show_detailed_category_view(report, categories[0])

    # Show governance highlights if available
    if hasattr(report, "governance_view") and report.governance_view:
        governance = report.governance_view
        if hasattr(governance, "privileged_access_report") and governance.privileged_access_report:
            priv_report = governance.privileged_access_report
            if priv_report.admin_permission_sets:
                console.print(
                    f"\n[yellow]⚠ Found {len(priv_report.admin_permission_sets)} privileged permission sets[/yellow]"
                )
            if priv_report.users_with_admin_access:
                console.print(
                    f"[yellow]⚠ Found {len(priv_report.users_with_admin_access)} users with admin access[/yellow]"
                )


def _show_detailed_category_view(report: Any, category: str) -> None:
    """Show detailed view for a specific category.

    Args:
        report: StatisticsReport object
        category: Category to show detailed view for
    """
    if category == "users" and hasattr(report, "user_group_metrics") and report.user_group_metrics:
        _show_users_detailed_view(report.user_group_metrics)
    elif (
        category == "groups" and hasattr(report, "user_group_metrics") and report.user_group_metrics
    ):
        _show_groups_detailed_view(report.user_group_metrics)
    elif (
        category == "permission-sets"
        and hasattr(report, "permission_set_metrics")
        and report.permission_set_metrics
    ):
        _show_permission_sets_detailed_view(report.permission_set_metrics)
    elif category == "accounts" and hasattr(report, "account_metrics") and report.account_metrics:
        _show_accounts_detailed_view(report.account_metrics)
    elif (
        category == "assignments"
        and hasattr(report, "assignment_patterns")
        and report.assignment_patterns
    ):
        _show_assignments_detailed_view(report.assignment_patterns)
    elif category == "governance" and hasattr(report, "governance_view") and report.governance_view:
        _show_governance_detailed_view(report.governance_view)


def _show_users_detailed_view(metrics: Any) -> None:
    """Show detailed users view."""
    console.print("\n[bold green]Users Detailed View[/bold green]")

    # Orphaned users
    if metrics.orphaned_users:
        console.print(f"\n[red]⚠ Orphaned Users ({len(metrics.orphaned_users)}):[/red]")
        for user_id in metrics.orphaned_users[:10]:  # Show first 10
            console.print(f"  • {user_id}")
        if len(metrics.orphaned_users) > 10:
            console.print(f"  ... and {len(metrics.orphaned_users) - 10} more")

    # Users with most group memberships
    if metrics.groups_per_user_by_name:
        top_users = sorted(
            metrics.groups_per_user_by_name.items(), key=lambda x: x[1], reverse=True
        )[:5]
        console.print("\n[blue]📊 Users with Most Group Memberships:[/blue]")
        for username, count in top_users:
            console.print(f"  • {username}: {count} groups")


def _show_groups_detailed_view(metrics: Any) -> None:
    """Show detailed groups view."""
    console.print("\n[bold green]Groups Detailed View[/bold green]")

    # Orphaned groups
    if metrics.orphaned_groups:
        console.print(f"\n[red]⚠ Orphaned Groups ({len(metrics.orphaned_groups)}):[/red]")
        for group_id in metrics.orphaned_groups[:10]:
            console.print(f"  • {group_id}")

    # Largest groups
    if metrics.largest_groups:
        console.print("\n[blue]📊 Largest Groups:[/blue]")
        for group_name, count in metrics.largest_groups[:5]:
            console.print(f"  • {group_name}: {count} users")


def _show_permission_sets_detailed_view(metrics: Any) -> None:
    """Show detailed permission sets view."""
    console.print("\n[bold green]Permission Sets Detailed View[/bold green]")

    # Unused permission sets
    if metrics.unused_permission_sets:
        console.print(
            f"\n[yellow]⚠ Unused Permission Sets ({len(metrics.unused_permission_sets)}):[/yellow]"
        )
        for ps_name in metrics.unused_permission_sets[:10]:
            console.print(f"  • {ps_name}")

    # Privileged permission sets
    if metrics.privileged_permission_sets:
        console.print(
            f"\n[red]⚠ Privileged Permission Sets ({len(metrics.privileged_permission_sets)}):[/red]"
        )
        for ps_name in metrics.privileged_permission_sets[:10]:
            console.print(f"  • {ps_name}")

    # Most assigned permission sets
    if metrics.most_assigned_permission_sets:
        console.print("\n[blue]📊 Most Assigned Permission Sets:[/blue]")
        for ps_name, count in metrics.most_assigned_permission_sets[:5]:
            console.print(f"  • {ps_name}: {count} assignments")


def _show_accounts_detailed_view(metrics: Any) -> None:
    """Show detailed accounts view."""
    console.print("\n[bold green]Accounts Detailed View[/bold green]")

    # Accounts with no assignments
    if metrics.accounts_with_no_assignments:
        console.print(
            f"\n[yellow]⚠ Accounts with No Assignments ({len(metrics.accounts_with_no_assignments)}):[/yellow]"
        )
        for account_id in metrics.accounts_with_no_assignments[:10]:
            console.print(f"  • {account_id}")

    # Cross-account users
    if metrics.cross_account_users:
        console.print(
            f"\n[blue]📊 Cross-Account Users ({len(metrics.cross_account_users)}):[/blue]"
        )
        for user_id in metrics.cross_account_users[:10]:
            console.print(f"  • {user_id}")


def _show_assignments_detailed_view(patterns: Any) -> None:
    """Show detailed assignments view."""
    console.print("\n[bold green]Assignments Detailed View[/bold green]")

    # Users with most assignments
    if patterns.users_with_most_assignments:
        console.print("\n[blue]📊 Users with Most Assignments:[/blue]")
        for user_id, count in patterns.users_with_most_assignments[:5]:
            console.print(f"  • {user_id}: {count} assignments")

    # Groups with most assignments
    if patterns.groups_with_most_assignments:
        console.print("\n[blue]📊 Groups with Most Assignments:[/blue]")
        for group_id, count in patterns.groups_with_most_assignments[:5]:
            console.print(f"  • {group_id}: {count} assignments")


def _show_governance_detailed_view(governance: Any) -> None:
    """Show detailed governance view."""
    console.print("\n[bold green]Governance Detailed View[/bold green]")

    # Compliance gaps
    if governance.compliance_gaps:
        console.print(f"\n[red]⚠ Compliance Gaps ({len(governance.compliance_gaps)}):[/red]")
        for gap in governance.compliance_gaps[:5]:
            console.print(f"  • {gap}")

    # Empty mappings
    if governance.empty_mappings:
        empty = governance.empty_mappings
        if empty.groups_with_no_members:
            console.print(
                f"\n[yellow]⚠ Empty Groups ({len(empty.groups_with_no_members)}):[/yellow]"
            )
            for group_id in empty.groups_with_no_members[:5]:
                console.print(f"  • {group_id}")

        if empty.permission_sets_with_no_assignments:
            console.print(
                f"\n[yellow]⚠ Unused Permission Sets ({len(empty.permission_sets_with_no_assignments)}):[/yellow]"
            )
            for ps_id in empty.permission_sets_with_no_assignments[:5]:
                console.print(f"  • {ps_id}")


def save_output_to_file(content: str, output_file: Optional[str], format_type: str) -> None:
    """
    Save output content to a file if specified.

    Args:
        content: Content to save
        output_file: Output file path (optional)
        format_type: Format type for default filename generation
    """
    if output_file:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(content)
            console.print(f"[green]✓ Output saved to: {output_file}[/green]")
        except Exception as e:
            console.print(f"[red]Error saving to file: {e}[/red]")
            raise typer.Exit(1)
    else:
        # Print to console
        console.print(content)


def handle_statistics_error(error: Exception, operation: str, verbose: bool = False) -> None:
    """
    Handle statistics-specific errors with appropriate messaging.

    Args:
        error: The error that occurred
        operation: Description of the operation that failed
        verbose: Whether to show detailed error information
    """
    from ...statistics.interfaces import StatisticsError

    if isinstance(error, StatisticsError):
        console.print(f"[red]Statistics Error in {operation}: {error}[/red]")
    else:
        handle_aws_error(error, operation, verbose)


def show_progress_info(message: str, verbose: bool = False) -> None:
    """
    Show progress information if verbose mode is enabled.

    Args:
        message: Progress message to display
        verbose: Whether to show the message
    """
    if verbose:
        console.print(f"[blue]{message}[/blue]")
