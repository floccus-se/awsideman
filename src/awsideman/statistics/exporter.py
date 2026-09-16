"""Statistics exporter for output formatting and export to different formats."""

import csv
import io
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import StatisticsReport


class StatisticsJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for statistics data structures."""

    def default(self, obj: Any) -> Any:
        """Convert objects to JSON-serializable format."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif is_dataclass(obj) and not isinstance(obj, type):
            return asdict(obj)
        elif isinstance(obj, tuple):
            # Convert tuples to lists for JSON compatibility
            return list(obj)
        return super().default(obj)


class StatisticsExporter:
    """Exports statistics in various formats."""

    def export_to_json(self, report: StatisticsReport) -> str:
        """Export statistics as JSON format.

        Args:
            report: Statistics report to export

        Returns:
            JSON formatted string with proper indentation and metadata
        """
        try:
            # Convert the report to a dictionary structure
            report_dict = asdict(report)

            # Add export metadata
            export_metadata = {
                "export_timestamp": datetime.now().isoformat(),
                "export_format": "json",
                "export_version": "1.0",
            }

            # Create the final JSON structure with metadata
            json_output = {"export_metadata": export_metadata, "statistics_report": report_dict}

            # Serialize to JSON with proper formatting
            return json.dumps(
                json_output, cls=StatisticsJSONEncoder, indent=2, sort_keys=True, ensure_ascii=False
            )

        except Exception as e:
            raise ValueError(f"Failed to export statistics to JSON: {str(e)}") from e

    def export_to_csv(self, report: StatisticsReport, category: Optional[str] = None) -> str:
        """Export statistics as CSV format.

        Args:
            report: Statistics report to export
            category: Specific category to export (users, groups, permission_sets, accounts, assignments, governance)

        Returns:
            CSV formatted string with headers and data validation
        """
        try:
            if category:
                return self._export_category_to_csv(report, category)
            else:
                return self._export_all_to_csv(report)
        except Exception as e:
            raise ValueError(f"Failed to export statistics to CSV: {str(e)}") from e

    def _export_category_to_csv(self, report: StatisticsReport, category: str) -> str:
        """Export specific category to CSV format."""
        category_lower = category.lower()

        if category_lower == "users":
            return self._export_users_to_csv(report)
        elif category_lower == "groups":
            return self._export_groups_to_csv(report)
        elif category_lower == "permission_sets":
            return self._export_permission_sets_to_csv(report)
        elif category_lower == "accounts":
            return self._export_accounts_to_csv(report)
        elif category_lower == "assignments":
            return self._export_assignments_to_csv(report)
        elif category_lower == "governance":
            return self._export_governance_to_csv(report)
        else:
            raise ValueError(f"Unknown category: {category}")

    def _export_all_to_csv(self, report: StatisticsReport) -> str:
        """Export all statistics as a comprehensive CSV."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Write metadata header
        writer.writerow(["Statistics Report Summary"])
        writer.writerow(["Generated", report.metadata.generation_timestamp.isoformat()])
        writer.writerow(["Instance ARN", report.metadata.instance_arn])
        writer.writerow(["Region", report.metadata.region])
        writer.writerow(["Profile", report.metadata.profile or "N/A"])
        writer.writerow([])  # Empty row for separation

        # Summary statistics
        writer.writerow(["Summary Statistics"])
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total Users", report.user_group_metrics.total_users])
        writer.writerow(["Total Groups", report.user_group_metrics.total_groups])
        writer.writerow(
            ["Total Permission Sets", report.permission_set_metrics.total_permission_sets]
        )
        writer.writerow(["Total Accounts", report.account_metrics.total_accounts])
        writer.writerow(
            [
                "Average Assignments per User",
                f"{report.assignment_patterns.average_assignments_per_user:.2f}",
            ]
        )
        writer.writerow(
            [
                "Average Assignments per Permission Set",
                f"{report.permission_set_metrics.average_assignments_per_permission_set:.2f}",
            ]
        )
        writer.writerow([])  # Empty row for separation

        # Orphaned resources
        writer.writerow(["Orphaned Resources"])
        writer.writerow(["Resource Type", "Count", "Items"])
        writer.writerow(
            [
                "Orphaned Users",
                len(report.user_group_metrics.orphaned_users),
                "; ".join(report.user_group_metrics.orphaned_users),
            ]
        )
        writer.writerow(
            [
                "Orphaned Groups",
                len(report.user_group_metrics.orphaned_groups),
                "; ".join(report.user_group_metrics.orphaned_groups),
            ]
        )
        writer.writerow(
            [
                "Unused Permission Sets",
                len(report.permission_set_metrics.unused_permission_sets),
                "; ".join(report.permission_set_metrics.unused_permission_sets),
            ]
        )
        writer.writerow(
            [
                "Accounts with No Assignments",
                len(report.account_metrics.accounts_with_no_assignments),
                "; ".join(report.account_metrics.accounts_with_no_assignments),
            ]
        )

        return output.getvalue()

    def _export_users_to_csv(self, report: StatisticsReport) -> str:
        """Export user-related statistics to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["User Statistics"])
        writer.writerow(["Generated", report.metadata.generation_timestamp.isoformat()])
        writer.writerow([])

        # User metrics summary
        writer.writerow(["User Metrics Summary"])
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total Users", report.user_group_metrics.total_users])
        writer.writerow(["Orphaned Users", len(report.user_group_metrics.orphaned_users)])
        writer.writerow([])

        # Groups per user
        writer.writerow(["Groups per User"])
        writer.writerow(["User ID", "Group Count"])
        for user_id, group_count in sorted(report.user_group_metrics.groups_per_user.items()):
            writer.writerow([user_id, group_count])
        writer.writerow([])

        # Users with most assignments
        writer.writerow(["Users with Most Assignments"])
        writer.writerow(["User ID", "Assignment Count"])
        for user_id, assignment_count in report.assignment_patterns.users_with_most_assignments:
            writer.writerow([user_id, assignment_count])
        writer.writerow([])

        # Cross-account users
        writer.writerow(["Cross-Account Users"])
        writer.writerow(["User ID", "Account Count"])
        for user_id, account_count in report.account_metrics.cross_account_users:
            writer.writerow([user_id, account_count])
        writer.writerow([])

        # Orphaned users
        if report.user_group_metrics.orphaned_users:
            writer.writerow(["Orphaned Users"])
            writer.writerow(["User ID"])
            for user_id in report.user_group_metrics.orphaned_users:
                writer.writerow([user_id])

        return output.getvalue()

    def _export_groups_to_csv(self, report: StatisticsReport) -> str:
        """Export group-related statistics to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["Group Statistics"])
        writer.writerow(["Generated", report.metadata.generation_timestamp.isoformat()])
        writer.writerow([])

        # Group metrics summary
        writer.writerow(["Group Metrics Summary"])
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total Groups", report.user_group_metrics.total_groups])
        writer.writerow(["Orphaned Groups", len(report.user_group_metrics.orphaned_groups)])
        writer.writerow([])

        # Users per group
        writer.writerow(["Users per Group"])
        writer.writerow(["Group ID", "User Count"])
        for group_id, user_count in sorted(report.user_group_metrics.users_per_group.items()):
            writer.writerow([group_id, user_count])
        writer.writerow([])

        # Largest groups
        writer.writerow(["Largest Groups"])
        writer.writerow(["Group Name", "User Count"])
        for group_name, user_count in report.user_group_metrics.largest_groups:
            writer.writerow([group_name, user_count])
        writer.writerow([])

        # Groups with most assignments
        writer.writerow(["Groups with Most Assignments"])
        writer.writerow(["Group ID", "Assignment Count"])
        for group_id, assignment_count in report.assignment_patterns.groups_with_most_assignments:
            writer.writerow([group_id, assignment_count])
        writer.writerow([])

        # Cross-account groups
        writer.writerow(["Cross-Account Groups"])
        writer.writerow(["Group ID", "Account Count"])
        for group_id, account_count in report.account_metrics.cross_account_groups:
            writer.writerow([group_id, account_count])
        writer.writerow([])

        # Orphaned groups
        if report.user_group_metrics.orphaned_groups:
            writer.writerow(["Orphaned Groups"])
            writer.writerow(["Group ID"])
            for group_id in report.user_group_metrics.orphaned_groups:
                writer.writerow([group_id])

        return output.getvalue()

    def _export_permission_sets_to_csv(self, report: StatisticsReport) -> str:
        """Export permission set statistics to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["Permission Set Statistics"])
        writer.writerow(["Generated", report.metadata.generation_timestamp.isoformat()])
        writer.writerow([])

        # Permission set metrics summary
        writer.writerow(["Permission Set Metrics Summary"])
        writer.writerow(["Metric", "Value"])
        writer.writerow(
            ["Total Permission Sets", report.permission_set_metrics.total_permission_sets]
        )
        writer.writerow(
            ["Unused Permission Sets", len(report.permission_set_metrics.unused_permission_sets)]
        )
        writer.writerow(
            [
                "Privileged Permission Sets",
                len(report.permission_set_metrics.privileged_permission_sets),
            ]
        )
        writer.writerow(
            [
                "Average Assignments per Permission Set",
                f"{report.permission_set_metrics.average_assignments_per_permission_set:.2f}",
            ]
        )
        writer.writerow([])

        # Assignments per permission set
        writer.writerow(["Assignments per Permission Set"])
        writer.writerow(["Permission Set ARN", "Assignment Count"])
        for ps_arn, assignment_count in sorted(
            report.permission_set_metrics.assignments_per_permission_set.items()
        ):
            writer.writerow([ps_arn, assignment_count])
        writer.writerow([])

        # Most assigned permission sets
        writer.writerow(["Most Assigned Permission Sets"])
        writer.writerow(["Permission Set ARN", "Assignment Count"])
        for ps_arn, assignment_count in report.permission_set_metrics.most_assigned_permission_sets:
            writer.writerow([ps_arn, assignment_count])
        writer.writerow([])

        # Privileged permission sets
        if report.permission_set_metrics.privileged_permission_sets:
            writer.writerow(["Privileged Permission Sets"])
            writer.writerow(["Permission Set ARN"])
            for ps_arn in report.permission_set_metrics.privileged_permission_sets:
                writer.writerow([ps_arn])
            writer.writerow([])

        # Unused permission sets
        if report.permission_set_metrics.unused_permission_sets:
            writer.writerow(["Unused Permission Sets"])
            writer.writerow(["Permission Set ARN"])
            for ps_arn in report.permission_set_metrics.unused_permission_sets:
                writer.writerow([ps_arn])

        return output.getvalue()

    def _export_accounts_to_csv(self, report: StatisticsReport) -> str:
        """Export account statistics to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["Account Statistics"])
        writer.writerow(["Generated", report.metadata.generation_timestamp.isoformat()])
        writer.writerow([])

        # Account metrics summary
        writer.writerow(["Account Metrics Summary"])
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total Accounts", report.account_metrics.total_accounts])
        writer.writerow(
            [
                "Accounts with No Assignments",
                len(report.account_metrics.accounts_with_no_assignments),
            ]
        )
        writer.writerow([])

        # Assignments per account
        writer.writerow(["Assignments per Account"])
        writer.writerow(["Account ID", "Assignment Count"])
        for account_id, assignment_count in sorted(
            report.account_metrics.assignments_per_account.items()
        ):
            writer.writerow([account_id, assignment_count])
        writer.writerow([])

        # Users per account
        writer.writerow(["Users per Account"])
        writer.writerow(["Account ID", "User Count"])
        for account_id, user_count in sorted(report.account_metrics.users_per_account.items()):
            writer.writerow([account_id, user_count])
        writer.writerow([])

        # Groups per account
        writer.writerow(["Groups per Account"])
        writer.writerow(["Account ID", "Group Count"])
        for account_id, group_count in sorted(report.account_metrics.groups_per_account.items()):
            writer.writerow([account_id, group_count])
        writer.writerow([])

        # Accounts with no assignments
        if report.account_metrics.accounts_with_no_assignments:
            writer.writerow(["Accounts with No Assignments"])
            writer.writerow(["Account ID"])
            for account_id in report.account_metrics.accounts_with_no_assignments:
                writer.writerow([account_id])

        return output.getvalue()

    def _export_assignments_to_csv(self, report: StatisticsReport) -> str:
        """Export assignment pattern statistics to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["Assignment Pattern Statistics"])
        writer.writerow(["Generated", report.metadata.generation_timestamp.isoformat()])
        writer.writerow([])

        # Assignment pattern summary
        writer.writerow(["Assignment Pattern Summary"])
        writer.writerow(["Metric", "Value"])
        writer.writerow(
            [
                "Average Assignments per User",
                f"{report.assignment_patterns.average_assignments_per_user:.2f}",
            ]
        )
        writer.writerow([])

        # Users with most assignments
        writer.writerow(["Users with Most Assignments"])
        writer.writerow(["User ID", "Assignment Count"])
        for user_id, assignment_count in report.assignment_patterns.users_with_most_assignments:
            writer.writerow([user_id, assignment_count])
        writer.writerow([])

        # Groups with most assignments
        writer.writerow(["Groups with Most Assignments"])
        writer.writerow(["Group ID", "Assignment Count"])
        for group_id, assignment_count in report.assignment_patterns.groups_with_most_assignments:
            writer.writerow([group_id, assignment_count])
        writer.writerow([])

        # Historical trend data if available
        if report.assignment_patterns.assignment_growth_trend:
            trend = report.assignment_patterns.assignment_growth_trend
            writer.writerow(["Assignment Growth Trend"])
            writer.writerow(["Time Period", "Value"])
            for period, value in zip(trend.time_periods, trend.values):
                writer.writerow([period, value])
            writer.writerow([])
            writer.writerow(["Trend Direction", trend.trend_direction])

        return output.getvalue()

    def _export_governance_to_csv(self, report: StatisticsReport) -> str:
        """Export governance statistics to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["Governance Statistics"])
        writer.writerow(["Generated", report.metadata.generation_timestamp.isoformat()])
        writer.writerow([])

        # Privileged access summary
        writer.writerow(["Privileged Access Summary"])
        writer.writerow(["Metric", "Value"])
        writer.writerow(
            [
                "Admin Permission Sets",
                len(report.governance_view.privileged_access_report.admin_permission_sets),
            ]
        )
        writer.writerow(
            [
                "Users with Admin Access",
                len(report.governance_view.privileged_access_report.users_with_admin_access),
            ]
        )
        writer.writerow(
            [
                "Accounts with Admin Access",
                len(report.governance_view.privileged_access_report.accounts_with_admin_access),
            ]
        )
        writer.writerow([])

        # Admin permission sets
        if report.governance_view.privileged_access_report.admin_permission_sets:
            writer.writerow(["Admin Permission Sets"])
            writer.writerow(["Permission Set ARN"])
            for ps_arn in report.governance_view.privileged_access_report.admin_permission_sets:
                writer.writerow([ps_arn])
            writer.writerow([])

        # Users with admin access
        if report.governance_view.privileged_access_report.users_with_admin_access:
            writer.writerow(["Users with Admin Access"])
            writer.writerow(["User ID"])
            for user_id in report.governance_view.privileged_access_report.users_with_admin_access:
                writer.writerow([user_id])
            writer.writerow([])

        # Accounts with admin access
        writer.writerow(["Accounts with Admin Access"])
        writer.writerow(["Account ID", "Admin Entities"])
        for (
            account_id,
            entities,
        ) in report.governance_view.privileged_access_report.accounts_with_admin_access.items():
            writer.writerow([account_id, "; ".join(entities)])
        writer.writerow([])

        # Empty mappings
        writer.writerow(["Empty Mappings"])
        writer.writerow(["Resource Type", "Count", "Items"])
        writer.writerow(
            [
                "Groups with No Members",
                len(report.governance_view.empty_mappings.groups_with_no_members),
                "; ".join(report.governance_view.empty_mappings.groups_with_no_members),
            ]
        )
        writer.writerow(
            [
                "Permission Sets with No Assignments",
                len(report.governance_view.empty_mappings.permission_sets_with_no_assignments),
                "; ".join(
                    report.governance_view.empty_mappings.permission_sets_with_no_assignments
                ),
            ]
        )
        writer.writerow(
            [
                "Accounts with No Assignments",
                len(report.governance_view.empty_mappings.accounts_with_no_assignments),
                "; ".join(report.governance_view.empty_mappings.accounts_with_no_assignments),
            ]
        )
        writer.writerow([])

        # Compliance gaps
        if report.governance_view.compliance_gaps:
            writer.writerow(["Compliance Gaps"])
            writer.writerow(["Gap Type", "Description", "Severity", "Affected Resources"])
            for gap in report.governance_view.compliance_gaps:
                writer.writerow(
                    [gap.gap_type, gap.description, gap.severity, "; ".join(gap.affected_resources)]
                )

        return output.getvalue()

    def export_to_text(self, report: StatisticsReport) -> str:
        """Export statistics as formatted text.

        Args:
            report: Statistics report to export

        Returns:
            Human-readable formatted text string with tables and summaries
        """
        try:
            output = []

            # Header
            output.append("=" * 80)
            output.append("AWS Identity Center Statistics Report")
            output.append("=" * 80)
            output.append("")

            # Metadata
            output.append("Report Information:")
            output.append(
                f"  Generated: {report.metadata.generation_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
            output.append(f"  Instance ARN: {report.metadata.instance_arn}")
            output.append(f"  Region: {report.metadata.region}")
            output.append(f"  Profile: {report.metadata.profile or 'N/A'}")
            output.append(
                f"  Data Collection Duration: {report.metadata.data_collection_duration:.2f}s"
            )
            output.append(f"  Analysis Duration: {report.metadata.analysis_duration:.2f}s")
            output.append("")

            # Executive Summary
            output.append("Executive Summary:")
            output.append("-" * 40)
            output.append(f"  Total Users: {report.user_group_metrics.total_users:,}")
            output.append(f"  Total Groups: {report.user_group_metrics.total_groups:,}")
            output.append(
                f"  Total Permission Sets: {report.permission_set_metrics.total_permission_sets:,}"
            )
            output.append(f"  Total Accounts: {report.account_metrics.total_accounts:,}")
            output.append(
                f"  Average Assignments per User: {report.assignment_patterns.average_assignments_per_user:.2f}"
            )
            output.append(
                f"  Average Assignments per Permission Set: {report.permission_set_metrics.average_assignments_per_permission_set:.2f}"
            )
            output.append("")

            # Key Findings
            output.append("Key Findings:")
            output.append("-" * 40)

            # Orphaned resources
            orphaned_count = (
                len(report.user_group_metrics.orphaned_users)
                + len(report.user_group_metrics.orphaned_groups)
                + len(report.permission_set_metrics.unused_permission_sets)
                + len(report.account_metrics.accounts_with_no_assignments)
            )
            output.append(f"  • {orphaned_count} orphaned/unused resources detected")

            # Privileged access
            privileged_count = len(report.permission_set_metrics.privileged_permission_sets)
            admin_users_count = len(
                report.governance_view.privileged_access_report.users_with_admin_access
            )
            output.append(f"  • {privileged_count} privileged permission sets identified")
            output.append(f"  • {admin_users_count} users with administrative access")

            # Cross-account access
            cross_account_users = len(report.account_metrics.cross_account_users)
            cross_account_groups = len(report.account_metrics.cross_account_groups)
            output.append(f"  • {cross_account_users} users with cross-account access")
            output.append(f"  • {cross_account_groups} groups with cross-account access")

            output.append("")

            # Detailed sections
            output.extend(self._format_user_group_section(report))
            output.extend(self._format_permission_set_section(report))
            output.extend(self._format_account_section(report))
            output.extend(self._format_assignment_patterns_section(report))
            output.extend(self._format_governance_section(report))

            # Historical comparison if available
            if report.historical_comparison:
                output.extend(self._format_historical_section(report))

            # Footer
            output.append("=" * 80)
            output.append("End of Report")
            output.append("=" * 80)

            return "\n".join(output)

        except Exception as e:
            raise ValueError(f"Failed to export statistics to text: {str(e)}") from e

    def _format_user_group_section(self, report: StatisticsReport) -> List[str]:
        """Format user and group statistics section."""
        output = []
        metrics = report.user_group_metrics

        output.append("User and Group Statistics:")
        output.append("-" * 40)
        output.append("")

        # Summary table
        output.append("Summary:")
        output.append(
            self.format_summary_table(
                {
                    "Total Users": f"{metrics.total_users:,}",
                    "Total Groups": f"{metrics.total_groups:,}",
                    "Orphaned Users": f"{len(metrics.orphaned_users):,}",
                    "Orphaned Groups": f"{len(metrics.orphaned_groups):,}",
                }
            )
        )
        output.append("")

        # Largest groups
        if metrics.largest_groups:
            output.append("Largest Groups:")
            for group_name, user_count in metrics.largest_groups[:10]:  # Top 10
                output.append(f"  • {group_name}: {user_count:,} users")
            output.append("")

        # Orphaned resources
        if metrics.orphaned_users:
            output.append(f"Orphaned Users ({len(metrics.orphaned_users)}):")
            for user_id in metrics.orphaned_users[:10]:  # Show first 10
                output.append(f"  • {user_id}")
            if len(metrics.orphaned_users) > 10:
                output.append(f"  ... and {len(metrics.orphaned_users) - 10} more")
            output.append("")

        if metrics.orphaned_groups:
            output.append(f"Orphaned Groups ({len(metrics.orphaned_groups)}):")
            for group_id in metrics.orphaned_groups[:10]:  # Show first 10
                output.append(f"  • {group_id}")
            if len(metrics.orphaned_groups) > 10:
                output.append(f"  ... and {len(metrics.orphaned_groups) - 10} more")
            output.append("")

        return output

    def _format_permission_set_section(self, report: StatisticsReport) -> List[str]:
        """Format permission set statistics section."""
        output = []
        metrics = report.permission_set_metrics

        output.append("Permission Set Statistics:")
        output.append("-" * 40)
        output.append("")

        # Summary table
        output.append("Summary:")
        output.append(
            self.format_summary_table(
                {
                    "Total Permission Sets": f"{metrics.total_permission_sets:,}",
                    "Unused Permission Sets": f"{len(metrics.unused_permission_sets):,}",
                    "Privileged Permission Sets": f"{len(metrics.privileged_permission_sets):,}",
                    "Average Assignments": f"{metrics.average_assignments_per_permission_set:.2f}",
                }
            )
        )
        output.append("")

        # Most assigned permission sets
        if metrics.most_assigned_permission_sets:
            output.append("Most Assigned Permission Sets:")
            for ps_arn, assignment_count in metrics.most_assigned_permission_sets[:10]:
                ps_name = ps_arn.split("/")[-1] if "/" in ps_arn else ps_arn
                output.append(f"  • {ps_name}: {assignment_count:,} assignments")
            output.append("")

        # Privileged permission sets
        if metrics.privileged_permission_sets:
            output.append(
                f"Privileged Permission Sets ({len(metrics.privileged_permission_sets)}):"
            )
            for ps_arn in metrics.privileged_permission_sets[:10]:
                ps_name = ps_arn.split("/")[-1] if "/" in ps_arn else ps_arn
                output.append(f"  • {ps_name}")
            if len(metrics.privileged_permission_sets) > 10:
                output.append(f"  ... and {len(metrics.privileged_permission_sets) - 10} more")
            output.append("")

        # Unused permission sets
        if metrics.unused_permission_sets:
            output.append(f"Unused Permission Sets ({len(metrics.unused_permission_sets)}):")
            for ps_arn in metrics.unused_permission_sets[:10]:
                ps_name = ps_arn.split("/")[-1] if "/" in ps_arn else ps_arn
                output.append(f"  • {ps_name}")
            if len(metrics.unused_permission_sets) > 10:
                output.append(f"  ... and {len(metrics.unused_permission_sets) - 10} more")
            output.append("")

        return output

    def _format_account_section(self, report: StatisticsReport) -> List[str]:
        """Format account statistics section."""
        output = []
        metrics = report.account_metrics

        output.append("Account Statistics:")
        output.append("-" * 40)
        output.append("")

        # Summary table
        output.append("Summary:")
        output.append(
            self.format_summary_table(
                {
                    "Total Accounts": f"{metrics.total_accounts:,}",
                    "Accounts with No Assignments": f"{len(metrics.accounts_with_no_assignments):,}",
                    "Cross-Account Users": f"{len(metrics.cross_account_users):,}",
                    "Cross-Account Groups": f"{len(metrics.cross_account_groups):,}",
                }
            )
        )
        output.append("")

        # Top accounts by assignments
        if metrics.assignments_per_account:
            sorted_accounts = sorted(
                metrics.assignments_per_account.items(), key=lambda x: x[1], reverse=True
            )
            output.append("Accounts by Assignment Count:")
            for account_id, assignment_count in sorted_accounts[:10]:
                # Mask account ID for display
                masked_id = f"***{account_id[-4:]}"
                output.append(f"  • {masked_id}: {assignment_count:,} assignments")
            output.append("")

        # Cross-account access
        if metrics.cross_account_users:
            output.append("Users with Cross-Account Access:")
            for user_id, account_count in metrics.cross_account_users[:10]:
                output.append(f"  • {user_id}: {account_count:,} accounts")
            output.append("")

        if metrics.cross_account_groups:
            output.append("Groups with Cross-Account Access:")
            for group_id, account_count in metrics.cross_account_groups[:10]:
                output.append(f"  • {group_id}: {account_count:,} accounts")
            output.append("")

        return output

    def _format_assignment_patterns_section(self, report: StatisticsReport) -> List[str]:
        """Format assignment patterns section."""
        output = []
        patterns = report.assignment_patterns

        output.append("Assignment Patterns:")
        output.append("-" * 40)
        output.append("")

        # Summary
        output.append("Summary:")
        output.append(
            self.format_summary_table(
                {"Average Assignments per User": f"{patterns.average_assignments_per_user:.2f}"}
            )
        )
        output.append("")

        # Users with most assignments
        if patterns.users_with_most_assignments:
            output.append("Users with Most Assignments:")
            for user_id, assignment_count in patterns.users_with_most_assignments[:10]:
                output.append(f"  • {user_id}: {assignment_count:,} assignments")
            output.append("")

        # Groups with most assignments
        if patterns.groups_with_most_assignments:
            output.append("Groups with Most Assignments:")
            for group_id, assignment_count in patterns.groups_with_most_assignments[:10]:
                output.append(f"  • {group_id}: {assignment_count:,} assignments")
            output.append("")

        # Trend data
        if patterns.assignment_growth_trend:
            trend = patterns.assignment_growth_trend
            output.append("Assignment Growth Trend:")
            output.append(f"  Direction: {trend.trend_direction.title()}")
            if len(trend.time_periods) >= 2:
                start_value = trend.values[0]
                end_value = trend.values[-1]
                change = end_value - start_value
                change_pct = (change / start_value * 100) if start_value > 0 else 0
                output.append(f"  Change: {change:+,} assignments ({change_pct:+.1f}%)")
            output.append("")

        return output

    def _format_governance_section(self, report: StatisticsReport) -> List[str]:
        """Format governance statistics section."""
        output = []
        governance = report.governance_view

        output.append("Governance and Security:")
        output.append("-" * 40)
        output.append("")

        # Privileged access summary
        privileged = governance.privileged_access_report
        output.append("Privileged Access Summary:")
        output.append(
            self.format_summary_table(
                {
                    "Admin Permission Sets": f"{len(privileged.admin_permission_sets):,}",
                    "Users with Admin Access": f"{len(privileged.users_with_admin_access):,}",
                    "Accounts with Admin Access": f"{len(privileged.accounts_with_admin_access):,}",
                }
            )
        )
        output.append("")

        # Admin users
        if privileged.users_with_admin_access:
            output.append("Users with Administrative Access:")
            for user_id in privileged.users_with_admin_access[:10]:
                output.append(f"  • {user_id}")
            if len(privileged.users_with_admin_access) > 10:
                output.append(f"  ... and {len(privileged.users_with_admin_access) - 10} more")
            output.append("")

        # Empty mappings
        empty = governance.empty_mappings
        empty_count = (
            len(empty.groups_with_no_members)
            + len(empty.permission_sets_with_no_assignments)
            + len(empty.accounts_with_no_assignments)
        )

        if empty_count > 0:
            output.append("Empty Mappings:")
            if empty.groups_with_no_members:
                output.append(f"  • Groups with no members: {len(empty.groups_with_no_members):,}")
            if empty.permission_sets_with_no_assignments:
                output.append(
                    f"  • Permission sets with no assignments: {len(empty.permission_sets_with_no_assignments):,}"
                )
            if empty.accounts_with_no_assignments:
                output.append(
                    f"  • Accounts with no assignments: {len(empty.accounts_with_no_assignments):,}"
                )
            output.append("")

        # Compliance gaps
        if governance.compliance_gaps:
            output.append(f"Compliance Gaps ({len(governance.compliance_gaps)}):")
            for gap in governance.compliance_gaps[:5]:  # Show first 5
                output.append(
                    f"  • {gap.gap_type.title()}: {gap.description} (Severity: {gap.severity})"
                )
            if len(governance.compliance_gaps) > 5:
                output.append(f"  ... and {len(governance.compliance_gaps) - 5} more")
            output.append("")

        return output

    def _format_historical_section(self, report: StatisticsReport) -> List[str]:
        """Format historical comparison section."""
        output: List[str] = []
        historical = report.historical_comparison

        # This method should only be called when historical_comparison is not None
        if historical is None:
            return output

        output.append("Historical Comparison:")
        output.append("-" * 40)
        output.append("")

        # Growth metrics
        output.append("Growth Metrics:")
        growth_data = {
            "User Growth": f"{historical.user_growth.growth_rate:+.1%} ({historical.user_growth.absolute_change:+,})",
            "Group Growth": f"{historical.group_growth.growth_rate:+.1%} ({historical.group_growth.absolute_change:+,})",
            "Permission Set Growth": f"{historical.permission_set_growth.growth_rate:+.1%} ({historical.permission_set_growth.absolute_change:+,})",
            "Assignment Growth": f"{historical.assignment_growth.growth_rate:+.1%} ({historical.assignment_growth.absolute_change:+,})",
        }
        output.append(self.format_summary_table(growth_data))
        output.append("")

        # Significant changes
        if historical.significant_changes:
            output.append("Significant Changes:")
            for change in historical.significant_changes[:5]:
                output.append(f"  • {change.category.title()}: {change.description}")
                output.append(
                    f"    Impact: {change.impact.title()}, Magnitude: {change.change_magnitude:.1%}"
                )
            output.append("")

        return output

    def format_summary_table(self, metrics: Dict[str, Any]) -> str:
        """Format metrics as summary table.

        Args:
            metrics: Metrics to format as key-value pairs

        Returns:
            Formatted table string with aligned columns
        """
        if not metrics:
            return "  No data available"

        # Calculate column widths
        max_key_width = max(len(str(key)) for key in metrics.keys())
        max_value_width = max(len(str(value)) for value in metrics.values())

        # Ensure minimum widths
        key_width = max(max_key_width, 20)
        value_width = max(max_value_width, 10)

        # Format table
        lines = []
        for key, value in metrics.items():
            lines.append(f"  {str(key):<{key_width}} : {str(value):>{value_width}}")

        return "\n".join(lines)

    def format_detailed_report(self, report: StatisticsReport) -> str:
        """Format detailed report with comprehensive information.

        Args:
            report: Statistics report to format

        Returns:
            Formatted detailed report string with all sections and data
        """
        # The detailed report is the same as the main text export
        # but could be extended with additional detail levels in the future
        return self.export_to_text(report)

    def apply_filters(self, report: StatisticsReport, filters: Dict[str, Any]) -> StatisticsReport:
        """Apply filters to statistics report.

        Args:
            report: Statistics report to filter
            filters: Filters to apply with keys like:
                - account: Filter by specific account ID(s)
                - user: Filter by specific user ID(s)
                - group: Filter by specific group ID(s)
                - permission_set: Filter by specific permission set ARN(s)
                - categories: Include only specific categories
                - high_risk_only: Show only high-risk items
                - orphaned_only: Show only orphaned resources
                - privileged_only: Show only privileged access

        Returns:
            Filtered statistics report with applied filters
        """
        try:
            if not filters:
                return report

            # Create a copy of the report to avoid modifying the original
            import copy

            filtered_report = copy.deepcopy(report)

            # Update metadata to reflect applied filters
            filtered_report.metadata.filters_applied.update(filters)

            # Apply account filters
            if "account" in filters:
                filtered_report = self._filter_by_account(filtered_report, filters["account"])

            # Apply user filters
            if "user" in filters:
                filtered_report = self._filter_by_user(filtered_report, filters["user"])

            # Apply group filters
            if "group" in filters:
                filtered_report = self._filter_by_group(filtered_report, filters["group"])

            # Apply permission set filters
            if "permission_set" in filters:
                filtered_report = self._filter_by_permission_set(
                    filtered_report, filters["permission_set"]
                )

            # Apply preset filters
            if filters.get("high_risk_only", False):
                filtered_report = self._apply_high_risk_filter(filtered_report)

            if filters.get("orphaned_only", False):
                filtered_report = self._apply_orphaned_filter(filtered_report)

            if filters.get("privileged_only", False):
                filtered_report = self._apply_privileged_filter(filtered_report)

            return filtered_report

        except Exception as e:
            raise ValueError(f"Failed to apply filters to statistics report: {str(e)}") from e

    def _filter_by_account(self, report: StatisticsReport, account_filter: Any) -> StatisticsReport:
        """Filter report by account ID(s)."""
        # Normalize account filter to list
        if isinstance(account_filter, str):
            account_ids = [account_filter]
        elif isinstance(account_filter, list):
            account_ids = account_filter
        else:
            account_ids = [str(account_filter)]

        # Filter account metrics
        report.account_metrics.assignments_per_account = {
            k: v
            for k, v in report.account_metrics.assignments_per_account.items()
            if k in account_ids
        }
        report.account_metrics.users_per_account = {
            k: v for k, v in report.account_metrics.users_per_account.items() if k in account_ids
        }
        report.account_metrics.groups_per_account = {
            k: v for k, v in report.account_metrics.groups_per_account.items() if k in account_ids
        }
        report.account_metrics.accounts_with_no_assignments = [
            acc for acc in report.account_metrics.accounts_with_no_assignments if acc in account_ids
        ]

        # Update total accounts count
        report.account_metrics.total_accounts = len(
            set(
                list(report.account_metrics.assignments_per_account.keys())
                + list(report.account_metrics.users_per_account.keys())
                + list(report.account_metrics.groups_per_account.keys())
                + report.account_metrics.accounts_with_no_assignments
            )
        )

        # Filter access matrix
        report.governance_view.access_matrix.user_to_accounts = {
            k: [acc for acc in v if acc in account_ids]
            for k, v in report.governance_view.access_matrix.user_to_accounts.items()
        }
        report.governance_view.access_matrix.group_to_accounts = {
            k: [acc for acc in v if acc in account_ids]
            for k, v in report.governance_view.access_matrix.group_to_accounts.items()
        }
        report.governance_view.access_matrix.account_to_users = {
            k: v
            for k, v in report.governance_view.access_matrix.account_to_users.items()
            if k in account_ids
        }
        report.governance_view.access_matrix.account_to_groups = {
            k: v
            for k, v in report.governance_view.access_matrix.account_to_groups.items()
            if k in account_ids
        }

        # Filter privileged access report
        report.governance_view.privileged_access_report.accounts_with_admin_access = {
            k: v
            for k, v in report.governance_view.privileged_access_report.accounts_with_admin_access.items()
            if k in account_ids
        }

        # Filter empty mappings
        report.governance_view.empty_mappings.accounts_with_no_assignments = [
            acc
            for acc in report.governance_view.empty_mappings.accounts_with_no_assignments
            if acc in account_ids
        ]

        return report

    def _filter_by_user(self, report: StatisticsReport, user_filter: Any) -> StatisticsReport:
        """Filter report by user ID(s)."""
        # Normalize user filter to list
        if isinstance(user_filter, str):
            user_ids = [user_filter]
        elif isinstance(user_filter, list):
            user_ids = user_filter
        else:
            user_ids = [str(user_filter)]

        # Filter user group metrics
        report.user_group_metrics.groups_per_user = {
            k: v for k, v in report.user_group_metrics.groups_per_user.items() if k in user_ids
        }
        report.user_group_metrics.groups_per_user_by_name = {
            k: v
            for k, v in report.user_group_metrics.groups_per_user_by_name.items()
            if k in user_ids
        }
        report.user_group_metrics.orphaned_users = [
            user for user in report.user_group_metrics.orphaned_users if user in user_ids
        ]

        # Filter assignment patterns
        report.assignment_patterns.users_with_most_assignments = [
            (user, count)
            for user, count in report.assignment_patterns.users_with_most_assignments
            if user in user_ids
        ]

        # Filter account metrics
        report.account_metrics.cross_account_users = [
            (user, count)
            for user, count in report.account_metrics.cross_account_users
            if user in user_ids
        ]

        # Filter access matrix
        report.governance_view.access_matrix.user_to_accounts = {
            k: v
            for k, v in report.governance_view.access_matrix.user_to_accounts.items()
            if k in user_ids
        }
        report.governance_view.access_matrix.user_to_permission_sets = {
            k: v
            for k, v in report.governance_view.access_matrix.user_to_permission_sets.items()
            if k in user_ids
        }

        # Update account_to_users to only include filtered users
        for account_id in report.governance_view.access_matrix.account_to_users:
            report.governance_view.access_matrix.account_to_users[account_id] = [
                user
                for user in report.governance_view.access_matrix.account_to_users[account_id]
                if user in user_ids
            ]

        # Filter privileged access report
        report.governance_view.privileged_access_report.users_with_admin_access = [
            user
            for user in report.governance_view.privileged_access_report.users_with_admin_access
            if user in user_ids
        ]

        return report

    def _filter_by_group(self, report: StatisticsReport, group_filter: Any) -> StatisticsReport:
        """Filter report by group ID(s)."""
        # Normalize group filter to list
        if isinstance(group_filter, str):
            group_ids = [group_filter]
        elif isinstance(group_filter, list):
            group_ids = group_filter
        else:
            group_ids = [str(group_filter)]

        # Filter user group metrics
        report.user_group_metrics.users_per_group = {
            k: v for k, v in report.user_group_metrics.users_per_group.items() if k in group_ids
        }
        report.user_group_metrics.largest_groups = [
            (group, count)
            for group, count in report.user_group_metrics.largest_groups
            if group in group_ids
        ]
        report.user_group_metrics.orphaned_groups = [
            group for group in report.user_group_metrics.orphaned_groups if group in group_ids
        ]

        # Filter assignment patterns
        report.assignment_patterns.groups_with_most_assignments = [
            (group, count)
            for group, count in report.assignment_patterns.groups_with_most_assignments
            if group in group_ids
        ]

        # Filter account metrics
        report.account_metrics.cross_account_groups = [
            (group, count)
            for group, count in report.account_metrics.cross_account_groups
            if group in group_ids
        ]

        # Filter access matrix
        report.governance_view.access_matrix.group_to_accounts = {
            k: v
            for k, v in report.governance_view.access_matrix.group_to_accounts.items()
            if k in group_ids
        }
        report.governance_view.access_matrix.group_to_permission_sets = {
            k: v
            for k, v in report.governance_view.access_matrix.group_to_permission_sets.items()
            if k in group_ids
        }

        # Update account_to_groups to only include filtered groups
        for account_id in report.governance_view.access_matrix.account_to_groups:
            report.governance_view.access_matrix.account_to_groups[account_id] = [
                group
                for group in report.governance_view.access_matrix.account_to_groups[account_id]
                if group in group_ids
            ]

        # Filter empty mappings
        report.governance_view.empty_mappings.groups_with_no_members = [
            group
            for group in report.governance_view.empty_mappings.groups_with_no_members
            if group in group_ids
        ]

        return report

    def _filter_by_permission_set(
        self, report: StatisticsReport, ps_filter: Any
    ) -> StatisticsReport:
        """Filter report by permission set ARN(s)."""
        # Normalize permission set filter to list
        if isinstance(ps_filter, str):
            ps_arns = [ps_filter]
        elif isinstance(ps_filter, list):
            ps_arns = ps_filter
        else:
            ps_arns = [str(ps_filter)]

        # Filter permission set metrics
        report.permission_set_metrics.assignments_per_permission_set = {
            k: v
            for k, v in report.permission_set_metrics.assignments_per_permission_set.items()
            if k in ps_arns
        }
        report.permission_set_metrics.most_assigned_permission_sets = [
            (ps, count)
            for ps, count in report.permission_set_metrics.most_assigned_permission_sets
            if ps in ps_arns
        ]
        report.permission_set_metrics.unused_permission_sets = [
            ps for ps in report.permission_set_metrics.unused_permission_sets if ps in ps_arns
        ]
        report.permission_set_metrics.privileged_permission_sets = [
            ps for ps in report.permission_set_metrics.privileged_permission_sets if ps in ps_arns
        ]

        # Update total permission sets count
        report.permission_set_metrics.total_permission_sets = len(
            set(
                list(report.permission_set_metrics.assignments_per_permission_set.keys())
                + report.permission_set_metrics.unused_permission_sets
                + report.permission_set_metrics.privileged_permission_sets
            )
        )

        # Recalculate average including unused permission sets
        all_ps_count = len(
            set(
                list(report.permission_set_metrics.assignments_per_permission_set.keys())
                + report.permission_set_metrics.unused_permission_sets
                + report.permission_set_metrics.privileged_permission_sets
            )
        )

        if all_ps_count > 0:
            total_assignments = sum(
                report.permission_set_metrics.assignments_per_permission_set.values()
            )
            report.permission_set_metrics.average_assignments_per_permission_set = (
                total_assignments / all_ps_count
            )
        else:
            report.permission_set_metrics.average_assignments_per_permission_set = 0.0

        # Filter access matrix
        report.governance_view.access_matrix.user_to_permission_sets = {
            k: [ps for ps in v if ps in ps_arns]
            for k, v in report.governance_view.access_matrix.user_to_permission_sets.items()
        }
        report.governance_view.access_matrix.group_to_permission_sets = {
            k: [ps for ps in v if ps in ps_arns]
            for k, v in report.governance_view.access_matrix.group_to_permission_sets.items()
        }

        # Filter privileged access report
        report.governance_view.privileged_access_report.admin_permission_sets = [
            ps
            for ps in report.governance_view.privileged_access_report.admin_permission_sets
            if ps in ps_arns
        ]

        # Filter empty mappings
        report.governance_view.empty_mappings.permission_sets_with_no_assignments = [
            ps
            for ps in report.governance_view.empty_mappings.permission_sets_with_no_assignments
            if ps in ps_arns
        ]

        return report

    def _apply_high_risk_filter(self, report: StatisticsReport) -> StatisticsReport:
        """Apply high-risk filter to show only high-risk items."""
        # Keep only high-risk items in various sections

        # Keep only privileged permission sets
        report.permission_set_metrics.most_assigned_permission_sets = [
            (ps, count)
            for ps, count in report.permission_set_metrics.most_assigned_permission_sets
            if ps in report.permission_set_metrics.privileged_permission_sets
        ]

        # Keep only users with admin access
        admin_users = set(report.governance_view.privileged_access_report.users_with_admin_access)
        report.assignment_patterns.users_with_most_assignments = [
            (user, count)
            for user, count in report.assignment_patterns.users_with_most_assignments
            if user in admin_users
        ]

        # Keep only high-severity compliance gaps
        report.governance_view.compliance_gaps = [
            gap
            for gap in report.governance_view.compliance_gaps
            if gap.severity.lower() in ["high", "critical"]
        ]

        return report

    def _apply_orphaned_filter(self, report: StatisticsReport) -> StatisticsReport:
        """Apply orphaned filter to show only orphaned resources."""
        # Clear non-orphaned data and keep only orphaned resources

        # Keep only orphaned users and groups
        report.user_group_metrics.users_per_group = {}
        report.user_group_metrics.groups_per_user = {}
        report.user_group_metrics.largest_groups = []

        # Keep only unused permission sets
        report.permission_set_metrics.assignments_per_permission_set = {}
        report.permission_set_metrics.most_assigned_permission_sets = []
        report.permission_set_metrics.privileged_permission_sets = []

        # Keep only accounts with no assignments
        report.account_metrics.assignments_per_account = {}
        report.account_metrics.users_per_account = {}
        report.account_metrics.groups_per_account = {}

        # Clear assignment patterns (orphaned resources have no assignments)
        report.assignment_patterns.users_with_most_assignments = []
        report.assignment_patterns.groups_with_most_assignments = []
        report.assignment_patterns.average_assignments_per_user = 0.0

        # Clear access matrix (orphaned resources have no access)
        report.governance_view.access_matrix.user_to_accounts = {}
        report.governance_view.access_matrix.user_to_permission_sets = {}
        report.governance_view.access_matrix.group_to_accounts = {}
        report.governance_view.access_matrix.group_to_permission_sets = {}
        report.governance_view.access_matrix.account_to_users = {}
        report.governance_view.access_matrix.account_to_groups = {}

        return report

    def _apply_privileged_filter(self, report: StatisticsReport) -> StatisticsReport:
        """Apply privileged filter to show only privileged access."""
        # Keep only privileged-related data

        # Keep only privileged permission sets
        privileged_ps = set(report.permission_set_metrics.privileged_permission_sets)
        report.permission_set_metrics.assignments_per_permission_set = {
            k: v
            for k, v in report.permission_set_metrics.assignments_per_permission_set.items()
            if k in privileged_ps
        }
        report.permission_set_metrics.most_assigned_permission_sets = [
            (ps, count)
            for ps, count in report.permission_set_metrics.most_assigned_permission_sets
            if ps in privileged_ps
        ]
        report.permission_set_metrics.unused_permission_sets = [
            ps for ps in report.permission_set_metrics.unused_permission_sets if ps in privileged_ps
        ]

        # Keep only users with admin access
        admin_users = set(report.governance_view.privileged_access_report.users_with_admin_access)
        report.assignment_patterns.users_with_most_assignments = [
            (user, count)
            for user, count in report.assignment_patterns.users_with_most_assignments
            if user in admin_users
        ]

        # Filter user group metrics to admin users only
        report.user_group_metrics.groups_per_user = {
            k: v for k, v in report.user_group_metrics.groups_per_user.items() if k in admin_users
        }
        report.user_group_metrics.orphaned_users = [
            user for user in report.user_group_metrics.orphaned_users if user in admin_users
        ]

        # Filter access matrix to privileged access only
        report.governance_view.access_matrix.user_to_permission_sets = {
            k: [ps for ps in v if ps in privileged_ps]
            for k, v in report.governance_view.access_matrix.user_to_permission_sets.items()
            if k in admin_users
        }
        report.governance_view.access_matrix.group_to_permission_sets = {
            k: [ps for ps in v if ps in privileged_ps]
            for k, v in report.governance_view.access_matrix.group_to_permission_sets.items()
        }

        return report

    def get_preset_filters(self) -> Dict[str, Dict[str, Any]]:
        """Get available preset filters for common use cases.

        Returns:
            Dictionary of preset filter configurations
        """
        return {
            "high_risk": {
                "high_risk_only": True,
                "description": "Show only high-risk items (privileged access, high-severity gaps)",
            },
            "orphaned_resources": {
                "orphaned_only": True,
                "description": "Show only orphaned/unused resources",
            },
            "privileged_access": {
                "privileged_only": True,
                "description": "Show only privileged access patterns and admin users",
            },
            "cross_account": {
                "description": "Show only cross-account access patterns",
                # This would be implemented as a custom filter in the future
            },
            "governance_gaps": {
                "description": "Focus on governance and compliance gaps",
                # This would be implemented as a custom filter in the future
            },
        }

    def export_json(self, statistics: StatisticsReport) -> str:
        """Export statistics as JSON format.

        Args:
            statistics: Statistics report to export

        Returns:
            JSON formatted string
        """
        return self.export_to_json(statistics)

    def export_csv(self, statistics: StatisticsReport) -> str:
        """Export statistics as CSV format.

        Args:
            statistics: Statistics report to export

        Returns:
            CSV formatted string
        """
        return self.export_to_csv(statistics)

    def export_text(self, statistics: StatisticsReport) -> str:
        """Export statistics as formatted text.

        Args:
            statistics: Statistics report to export

        Returns:
            Formatted text string
        """
        return self.export_to_text(statistics)
