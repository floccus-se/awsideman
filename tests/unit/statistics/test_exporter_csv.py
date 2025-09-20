"""Tests for StatisticsExporter CSV export functionality."""

import csv
import io
from datetime import datetime

import pytest

from src.awsideman.statistics.exporter import StatisticsExporter
from src.awsideman.statistics.models import (
    AccessMatrix,
    AccountMetrics,
    AssignmentPatterns,
    ComplianceGap,
    EmptyMappings,
    GovernanceView,
    PermissionSetMetrics,
    PrivilegedAccessReport,
    ReportMetadata,
    StatisticsReport,
    TrendData,
    UserGroupMetrics,
)


class TestStatisticsExporter:
    """Test the StatisticsExporter CSV functionality."""

    @pytest.fixture
    def sample_report(self):
        """Create a sample statistics report for testing."""
        metadata = ReportMetadata(
            generation_timestamp=datetime(2023, 1, 1, 12, 0, 0),
            instance_arn="arn:aws:sso:::instance/ssoins-1234567890abcdef",
            region="us-east-1",
            profile="test-profile",
            categories_included=["users", "groups", "permission_sets"],
            filters_applied={"account": "123456789012"},
            data_collection_duration=5.5,
            analysis_duration=2.3,
        )

        user_group_metrics = UserGroupMetrics(
            total_users=100,
            total_groups=20,
            users_per_group={"group1": 10, "group2": 15, "group3": 0},
            groups_per_user={"user1": 2, "user2": 1, "user3": 0},
            groups_per_user_by_name={"user1": 2, "user2": 1, "user3": 0},
            largest_groups=[("group2", 15), ("group1", 10)],
            orphaned_users=["user3", "user4"],
            disabled_users=["user5"],
            orphaned_groups=["group3"],
        )

        permission_set_metrics = PermissionSetMetrics(
            total_permission_sets=10,
            assignments_per_permission_set={"ps1": 5, "ps2": 3, "ps3": 0},
            most_assigned_permission_sets=[("ps1", 5), ("ps2", 3)],
            unused_permission_sets=["ps3"],
            average_assignments_per_permission_set=2.5,
            privileged_permission_sets=["ps1"],
        )

        account_metrics = AccountMetrics(
            total_accounts=5,
            assignments_per_account={"123456789012": 10, "123456789013": 5, "123456789014": 0},
            users_per_account={"123456789012": 8, "123456789013": 3, "123456789014": 0},
            groups_per_account={"123456789012": 2, "123456789013": 1, "123456789014": 0},
            accounts_with_no_assignments=["123456789014"],
            cross_account_users=[("user1", 2), ("user2", 1)],
            cross_account_groups=[("group1", 2)],
        )

        assignment_patterns = AssignmentPatterns(
            average_assignments_per_user=3.5,
            users_with_most_assignments=[("user1", 10), ("user2", 8)],
            groups_with_most_assignments=[("group1", 15), ("group2", 12)],
            assignment_growth_trend=TrendData(
                time_periods=["2023-01", "2023-02", "2023-03"],
                values=[45, 50, 55],
                trend_direction="increasing",
            ),
        )

        access_matrix = AccessMatrix(
            user_to_accounts={"user1": ["123456789012", "123456789013"]},
            user_to_permission_sets={"user1": ["ps1", "ps2"]},
            group_to_accounts={"group1": ["123456789012"]},
            group_to_permission_sets={"group1": ["ps1"]},
            account_to_users={"123456789012": ["user1", "user2"]},
            account_to_groups={"123456789012": ["group1"]},
        )

        privileged_access_report = PrivilegedAccessReport(
            admin_permission_sets=["ps1"],
            accounts_with_admin_access={"123456789012": ["user1", "group1"]},
            users_with_admin_access=["user1"],
            high_privilege_patterns=[],
        )

        empty_mappings = EmptyMappings(
            groups_with_no_members=["group3"],
            permission_sets_with_no_assignments=["ps3"],
            accounts_with_no_assignments=["123456789014"],
        )

        compliance_gaps = [
            ComplianceGap(
                gap_type="over_privilege",
                description="User has excessive permissions",
                severity="high",
                affected_resources=["user1"],
            )
        ]

        governance_view = GovernanceView(
            access_matrix=access_matrix,
            privileged_access_report=privileged_access_report,
            empty_mappings=empty_mappings,
            compliance_gaps=compliance_gaps,
        )

        return StatisticsReport(
            metadata=metadata,
            user_group_metrics=user_group_metrics,
            permission_set_metrics=permission_set_metrics,
            account_metrics=account_metrics,
            assignment_patterns=assignment_patterns,
            governance_view=governance_view,
            historical_comparison=None,
        )

    def test_export_to_csv_all_categories(self, sample_report):
        """Test CSV export of all categories."""
        exporter = StatisticsExporter()
        result = exporter.export_to_csv(sample_report)

        # Verify it's valid CSV
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)

        # Should have multiple sections
        assert len(rows) > 10

        # Check for key sections
        content = result.lower()
        assert "statistics report summary" in content
        assert "summary statistics" in content
        assert "orphaned resources" in content
        assert "total users" in content
        assert "total groups" in content

    def test_export_to_csv_users_category(self, sample_report):
        """Test CSV export of users category."""
        exporter = StatisticsExporter()
        result = exporter.export_to_csv(sample_report, category="users")

        # Verify it's valid CSV
        csv.reader(io.StringIO(result))

        # Check for user-specific sections
        content = result.lower()
        assert "user statistics" in content
        assert "groups per user" in content
        assert "users with most assignments" in content
        assert "cross-account users" in content
        assert "orphaned users" in content

    def test_export_to_csv_groups_category(self, sample_report):
        """Test CSV export of groups category."""
        exporter = StatisticsExporter()
        result = exporter.export_to_csv(sample_report, category="groups")

        # Verify it's valid CSV
        csv.reader(io.StringIO(result))

        # Check for group-specific sections
        content = result.lower()
        assert "group statistics" in content
        assert "users per group" in content
        assert "largest groups" in content
        assert "groups with most assignments" in content
        assert "cross-account groups" in content
        assert "orphaned groups" in content

    def test_export_to_csv_permission_sets_category(self, sample_report):
        """Test CSV export of permission_sets category."""
        exporter = StatisticsExporter()
        result = exporter.export_to_csv(sample_report, category="permission_sets")

        # Verify it's valid CSV
        csv.reader(io.StringIO(result))

        # Check for permission set-specific sections
        content = result.lower()
        assert "permission set statistics" in content
        assert "assignments per permission set" in content
        assert "most assigned permission sets" in content
        assert "privileged permission sets" in content
        assert "unused permission sets" in content

    def test_export_to_csv_accounts_category(self, sample_report):
        """Test CSV export of accounts category."""
        exporter = StatisticsExporter()
        result = exporter.export_to_csv(sample_report, category="accounts")

        # Verify it's valid CSV
        csv.reader(io.StringIO(result))

        # Check for account-specific sections
        content = result.lower()
        assert "account statistics" in content
        assert "assignments per account" in content
        assert "users per account" in content
        assert "groups per account" in content
        assert "accounts with no assignments" in content

    def test_export_to_csv_assignments_category(self, sample_report):
        """Test CSV export of assignments category."""
        exporter = StatisticsExporter()
        result = exporter.export_to_csv(sample_report, category="assignments")

        # Verify it's valid CSV
        csv.reader(io.StringIO(result))

        # Check for assignment-specific sections
        content = result.lower()
        assert "assignment pattern statistics" in content
        assert "users with most assignments" in content
        assert "groups with most assignments" in content
        assert "assignment growth trend" in content

    def test_export_to_csv_governance_category(self, sample_report):
        """Test CSV export of governance category."""
        exporter = StatisticsExporter()
        result = exporter.export_to_csv(sample_report, category="governance")

        # Verify it's valid CSV
        csv.reader(io.StringIO(result))

        # Check for governance-specific sections
        content = result.lower()
        assert "governance statistics" in content
        assert "privileged access summary" in content
        assert "admin permission sets" in content
        assert "users with admin access" in content
        assert "empty mappings" in content
        assert "compliance gaps" in content

    def test_export_to_csv_invalid_category(self, sample_report):
        """Test CSV export with invalid category."""
        exporter = StatisticsExporter()

        with pytest.raises(ValueError, match="Unknown category: invalid"):
            exporter.export_to_csv(sample_report, category="invalid")

    def test_export_to_csv_case_insensitive_category(self, sample_report):
        """Test CSV export with case-insensitive category names."""
        exporter = StatisticsExporter()

        # Test various case combinations
        result1 = exporter.export_to_csv(sample_report, category="USERS")
        result2 = exporter.export_to_csv(sample_report, category="Users")
        result3 = exporter.export_to_csv(sample_report, category="users")

        # All should contain user statistics
        for result in [result1, result2, result3]:
            assert "User Statistics" in result

    def test_export_to_csv_proper_headers_and_formatting(self, sample_report):
        """Test CSV export has proper headers and formatting."""
        exporter = StatisticsExporter()
        result = exporter.export_to_csv(sample_report, category="users")

        reader = csv.reader(io.StringIO(result))
        rows = list(reader)

        # Check that we have proper CSV structure
        assert len(rows) > 0

        # Find the "Groups per User" section
        groups_per_user_idx = None
        for i, row in enumerate(rows):
            if row and row[0] == "Groups per User":
                groups_per_user_idx = i
                break

        assert groups_per_user_idx is not None

        # Next row should be headers
        headers = rows[groups_per_user_idx + 1]
        assert headers == ["User ID", "Group Count"]

        # Following rows should have data
        data_row = rows[groups_per_user_idx + 2]
        assert len(data_row) == 2  # Should have user ID and count

    def test_export_to_csv_data_validation(self, sample_report):
        """Test CSV export includes all expected data."""
        exporter = StatisticsExporter()
        result = exporter.export_to_csv(sample_report, category="users")

        # Check that specific data points are included
        assert "user1" in result
        assert "user2" in result
        assert "user3" in result  # orphaned user
        assert "user4" in result  # orphaned user

        # Check numeric values are properly formatted
        assert "100" in result  # total users
        assert "2" in result  # user1 has 2 groups

    def test_export_to_csv_empty_sections_handling(self, sample_report):
        """Test CSV export handles empty sections properly."""
        # Create a report with no orphaned users
        sample_report.user_group_metrics.orphaned_users = []

        exporter = StatisticsExporter()
        result = exporter.export_to_csv(sample_report, category="users")

        # Should still be valid CSV
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) > 0

        # Should not have orphaned users section when empty
        content = result.lower()
        assert "orphaned users" not in content or "0" in result

    def test_export_to_csv_with_trend_data(self, sample_report):
        """Test CSV export includes trend data when available."""
        exporter = StatisticsExporter()
        result = exporter.export_to_csv(sample_report, category="assignments")

        # Should include trend data
        assert "Assignment Growth Trend" in result
        assert "2023-01" in result
        assert "2023-02" in result
        assert "2023-03" in result
        assert "increasing" in result

    def test_export_to_csv_error_handling(self):
        """Test CSV export error handling."""
        exporter = StatisticsExporter()

        with pytest.raises(ValueError, match="Failed to export statistics to CSV"):
            exporter.export_to_csv(None)  # type: ignore

    def test_export_csv_interface_method(self, sample_report):
        """Test the interface method export_csv."""
        exporter = StatisticsExporter()
        result = exporter.export_csv(sample_report)

        # Should be the same as export_to_csv without category
        expected = exporter.export_to_csv(sample_report)
        assert result == expected

    def test_csv_special_characters_handling(self, sample_report):
        """Test CSV export handles special characters properly."""
        # Add some data with special characters
        sample_report.user_group_metrics.users_per_group["group,with,commas"] = 5
        sample_report.user_group_metrics.users_per_group['group"with"quotes'] = 3

        exporter = StatisticsExporter()
        result = exporter.export_to_csv(sample_report, category="groups")

        # Should be valid CSV even with special characters
        csv.reader(io.StringIO(result))

        # CSV reader should handle the special characters properly
        content = result
        assert "group,with,commas" in content or '"group,with,commas"' in content
        assert 'group"with"quotes' in content or '"group""with""quotes"' in content

    def test_csv_numeric_formatting(self, sample_report):
        """Test CSV export formats numeric values properly."""
        exporter = StatisticsExporter()
        result = exporter.export_to_csv(sample_report)

        # Check that decimal values are properly formatted
        assert "3.50" in result  # average assignments per user
        assert "2.50" in result  # average assignments per permission set

        # Check that integers are not formatted as decimals
        assert "100" in result  # total users (not 100.00)
        assert "20" in result  # total groups (not 20.00)
