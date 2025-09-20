"""Tests for StatisticsExporter text export functionality."""

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
    GrowthMetric,
    PermissionSetMetrics,
    PrivilegedAccessReport,
    ReportMetadata,
    SignificantChange,
    StatisticsReport,
    TrendAnalysis,
    TrendData,
    UserGroupMetrics,
)


class TestStatisticsExporter:
    """Test the StatisticsExporter text functionality."""

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
            largest_groups=[("group2", 15), ("group1", 10), ("group4", 8)],
            orphaned_users=["user3", "user4", "user5"],
            disabled_users=["user6"],
            orphaned_groups=["group3", "group5"],
        )

        permission_set_metrics = PermissionSetMetrics(
            total_permission_sets=10,
            assignments_per_permission_set={"ps1": 5, "ps2": 3, "ps3": 0},
            most_assigned_permission_sets=[("ps1", 5), ("ps2", 3), ("ps4", 2)],
            unused_permission_sets=["ps3", "ps5"],
            average_assignments_per_permission_set=2.5,
            privileged_permission_sets=["ps1", "ps6"],
        )

        account_metrics = AccountMetrics(
            total_accounts=5,
            assignments_per_account={"123456789012": 10, "123456789013": 5, "123456789014": 0},
            users_per_account={"123456789012": 8, "123456789013": 3, "123456789014": 0},
            groups_per_account={"123456789012": 2, "123456789013": 1, "123456789014": 0},
            accounts_with_no_assignments=["123456789014", "123456789015"],
            cross_account_users=[("user1", 2), ("user2", 1), ("user6", 3)],
            cross_account_groups=[("group1", 2), ("group2", 1)],
        )

        assignment_patterns = AssignmentPatterns(
            average_assignments_per_user=3.5,
            users_with_most_assignments=[("user1", 10), ("user2", 8), ("user7", 6)],
            groups_with_most_assignments=[("group1", 15), ("group2", 12), ("group8", 9)],
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
            admin_permission_sets=["ps1", "ps6"],
            accounts_with_admin_access={
                "123456789012": ["user1", "group1"],
                "123456789013": ["user2"],
            },
            users_with_admin_access=["user1", "user2"],
            high_privilege_patterns=[],
        )

        empty_mappings = EmptyMappings(
            groups_with_no_members=["group3", "group5"],
            permission_sets_with_no_assignments=["ps3", "ps5"],
            accounts_with_no_assignments=["123456789014", "123456789015"],
        )

        compliance_gaps = [
            ComplianceGap(
                gap_type="over_privilege",
                description="User has excessive permissions",
                severity="high",
                affected_resources=["user1"],
            ),
            ComplianceGap(
                gap_type="unused_resource",
                description="Permission set is not assigned",
                severity="medium",
                affected_resources=["ps3"],
            ),
        ]

        governance_view = GovernanceView(
            access_matrix=access_matrix,
            privileged_access_report=privileged_access_report,
            empty_mappings=empty_mappings,
            compliance_gaps=compliance_gaps,
        )

        historical_comparison = TrendAnalysis(
            user_growth=GrowthMetric(100, 80, 0.25, 20),
            group_growth=GrowthMetric(20, 18, 0.11, 2),
            permission_set_growth=GrowthMetric(10, 10, 0.0, 0),
            assignment_growth=GrowthMetric(50, 45, 0.11, 5),
            significant_changes=[
                SignificantChange(
                    category="users",
                    description="Significant user growth detected",
                    impact="high",
                    change_magnitude=0.25,
                )
            ],
        )

        return StatisticsReport(
            metadata=metadata,
            user_group_metrics=user_group_metrics,
            permission_set_metrics=permission_set_metrics,
            account_metrics=account_metrics,
            assignment_patterns=assignment_patterns,
            governance_view=governance_view,
            historical_comparison=historical_comparison,
        )

    def test_export_to_text_basic_structure(self, sample_report):
        """Test basic text export structure."""
        exporter = StatisticsExporter()
        result = exporter.export_to_text(sample_report)

        # Check for main sections
        assert "AWS Identity Center Statistics Report" in result
        assert "Report Information:" in result
        assert "Executive Summary:" in result
        assert "Key Findings:" in result
        assert "User and Group Statistics:" in result
        assert "Permission Set Statistics:" in result
        assert "Account Statistics:" in result
        assert "Assignment Patterns:" in result
        assert "Governance and Security:" in result
        assert "Historical Comparison:" in result
        assert "End of Report" in result

    def test_export_to_text_metadata_section(self, sample_report):
        """Test metadata section formatting."""
        exporter = StatisticsExporter()
        result = exporter.export_to_text(sample_report)

        # Check metadata content
        assert "Generated: 2023-01-01 12:00:00 UTC" in result
        assert "Instance ARN: arn:aws:sso:::instance/ssoins-1234567890abcdef" in result
        assert "Region: us-east-1" in result
        assert "Profile: test-profile" in result
        assert "Data Collection Duration: 5.50s" in result
        assert "Analysis Duration: 2.30s" in result

    def test_export_to_text_executive_summary(self, sample_report):
        """Test executive summary section."""
        exporter = StatisticsExporter()
        result = exporter.export_to_text(sample_report)

        # Check summary metrics
        assert "Total Users: 100" in result
        assert "Total Groups: 20" in result
        assert "Total Permission Sets: 10" in result
        assert "Total Accounts: 5" in result
        assert "Average Assignments per User: 3.50" in result
        assert "Average Assignments per Permission Set: 2.50" in result

    def test_export_to_text_key_findings(self, sample_report):
        """Test key findings section."""
        exporter = StatisticsExporter()
        result = exporter.export_to_text(sample_report)

        # Check key findings
        assert "orphaned/unused resources detected" in result
        assert "privileged permission sets identified" in result
        assert "users with administrative access" in result
        assert "users with cross-account access" in result
        assert "groups with cross-account access" in result

    def test_export_to_text_user_group_section(self, sample_report):
        """Test user and group statistics section."""
        exporter = StatisticsExporter()
        result = exporter.export_to_text(sample_report)

        # Check user/group content
        assert "User and Group Statistics:" in result
        assert "Largest Groups:" in result
        assert "group2: 15 users" in result
        assert "group1: 10 users" in result
        assert "Orphaned Users" in result
        assert "user3" in result
        assert "user4" in result
        assert "Orphaned Groups" in result
        assert "group3" in result

    def test_export_to_text_permission_set_section(self, sample_report):
        """Test permission set statistics section."""
        exporter = StatisticsExporter()
        result = exporter.export_to_text(sample_report)

        # Check permission set content
        assert "Permission Set Statistics:" in result
        assert "Most Assigned Permission Sets:" in result
        assert "Privileged Permission Sets" in result
        assert "Unused Permission Sets" in result
        assert "ps1" in result
        assert "ps3" in result

    def test_export_to_text_account_section(self, sample_report):
        """Test account statistics section."""
        exporter = StatisticsExporter()
        result = exporter.export_to_text(sample_report)

        # Check account content
        assert "Account Statistics:" in result
        assert "Accounts by Assignment Count:" in result
        assert "Users with Cross-Account Access:" in result
        assert "Groups with Cross-Account Access:" in result

        # Check account ID masking
        assert "***9012" in result  # Masked account ID
        assert "123456789012" not in result  # Full account ID should not appear

    def test_export_to_text_assignment_patterns_section(self, sample_report):
        """Test assignment patterns section."""
        exporter = StatisticsExporter()
        result = exporter.export_to_text(sample_report)

        # Check assignment patterns content
        assert "Assignment Patterns:" in result
        assert "Users with Most Assignments:" in result
        assert "Groups with Most Assignments:" in result
        assert "Assignment Growth Trend:" in result
        assert "Direction: Increasing" in result
        assert "+10 assignments" in result  # 55 - 45 = 10

    def test_export_to_text_governance_section(self, sample_report):
        """Test governance and security section."""
        exporter = StatisticsExporter()
        result = exporter.export_to_text(sample_report)

        # Check governance content
        assert "Governance and Security:" in result
        assert "Privileged Access Summary:" in result
        assert "Users with Administrative Access:" in result
        assert "Empty Mappings:" in result
        assert "Compliance Gaps" in result
        assert "over_privilege" in result.lower()
        assert "unused_resource" in result.lower()

    def test_export_to_text_historical_section(self, sample_report):
        """Test historical comparison section."""
        exporter = StatisticsExporter()
        result = exporter.export_to_text(sample_report)

        # Check historical content
        assert "Historical Comparison:" in result
        assert "Growth Metrics:" in result
        assert "User Growth" in result
        assert "+25.0%" in result  # 0.25 as percentage
        assert "Significant Changes:" in result
        assert "Significant user growth detected" in result

    def test_export_to_text_without_historical_data(self, sample_report):
        """Test text export without historical data."""
        sample_report.historical_comparison = None

        exporter = StatisticsExporter()
        result = exporter.export_to_text(sample_report)

        # Should not have historical section
        assert "Historical Comparison:" not in result
        assert "Growth Metrics:" not in result

    def test_format_summary_table(self):
        """Test summary table formatting."""
        exporter = StatisticsExporter()

        metrics = {"Total Users": "100", "Total Groups": "20", "Very Long Metric Name": "12,345"}

        result = exporter.format_summary_table(metrics)

        # Check formatting
        lines = result.split("\n")
        assert len(lines) == 3

        # Check alignment
        for line in lines:
            assert " : " in line
            assert line.startswith("  ")

    def test_format_summary_table_empty(self):
        """Test summary table with empty data."""
        exporter = StatisticsExporter()
        result = exporter.format_summary_table({})
        assert result == "  No data available"

    def test_format_detailed_report(self, sample_report):
        """Test detailed report formatting."""
        exporter = StatisticsExporter()
        detailed = exporter.format_detailed_report(sample_report)
        regular = exporter.export_to_text(sample_report)

        # Currently they should be the same
        assert detailed == regular

    def test_export_to_text_large_lists_truncation(self, sample_report):
        """Test that large lists are properly truncated."""
        # Add many orphaned users
        sample_report.user_group_metrics.orphaned_users = [f"user{i}" for i in range(15)]

        exporter = StatisticsExporter()
        result = exporter.export_to_text(sample_report)

        # Should show first 10 and indicate more
        assert "... and 5 more" in result

    def test_export_to_text_empty_sections(self, sample_report):
        """Test handling of empty sections."""
        # Clear some data
        sample_report.user_group_metrics.orphaned_users = []
        sample_report.user_group_metrics.orphaned_groups = []
        sample_report.governance_view.compliance_gaps = []

        exporter = StatisticsExporter()
        result = exporter.export_to_text(sample_report)

        # Should still be valid text
        assert "AWS Identity Center Statistics Report" in result
        assert "End of Report" in result

    def test_export_to_text_formatting_consistency(self, sample_report):
        """Test consistent formatting throughout the report."""
        exporter = StatisticsExporter()
        result = exporter.export_to_text(sample_report)

        # Check for consistent section separators
        assert result.count("=" * 80) >= 2  # Header and footer
        assert result.count("-" * 40) >= 5  # Section separators

        # Check for consistent indentation
        lines = result.split("\n")
        for line in lines:
            if line.startswith("  •"):  # Bullet points should be consistently indented
                assert line.startswith("  • ")

    def test_export_to_text_error_handling(self):
        """Test error handling for invalid data."""
        exporter = StatisticsExporter()

        with pytest.raises(ValueError, match="Failed to export statistics to text"):
            exporter.export_to_text(None)  # type: ignore

    def test_export_text_interface_method(self, sample_report):
        """Test the interface method export_text."""
        exporter = StatisticsExporter()
        result = exporter.export_text(sample_report)

        # Should be the same as export_to_text
        expected = exporter.export_to_text(sample_report)
        assert result == expected

    def test_text_output_readability(self, sample_report):
        """Test that text output is human-readable."""
        exporter = StatisticsExporter()
        result = exporter.export_to_text(sample_report)

        # Check for proper spacing and structure
        lines = result.split("\n")

        # Should have empty lines for separation
        empty_lines = [i for i, line in enumerate(lines) if line.strip() == ""]
        assert len(empty_lines) > 5  # Should have multiple empty lines for separation

        # Should not have excessively long lines
        for line in lines:
            assert len(line) <= 120  # Reasonable line length limit

    def test_text_numeric_formatting(self, sample_report):
        """Test numeric formatting in text output."""
        exporter = StatisticsExporter()
        result = exporter.export_to_text(sample_report)

        # Check that large numbers use comma separators
        # (Note: our sample data doesn't have numbers > 1000, so this tests the format)
        assert "100" in result  # Total users
        assert "3.50" in result  # Average assignments (decimal formatting)
        assert "25.0%" in result  # Growth percentage
