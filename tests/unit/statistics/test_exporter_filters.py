"""Tests for StatisticsExporter filtering functionality."""

from datetime import datetime
from typing import Any, Dict

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
    UserGroupMetrics,
)


class TestStatisticsExporter:
    """Test the StatisticsExporter filtering functionality."""

    @pytest.fixture
    def sample_report(self):
        """Create a sample statistics report for testing."""
        metadata = ReportMetadata(
            generation_timestamp=datetime(2023, 1, 1, 12, 0, 0),
            instance_arn="arn:aws:sso:::instance/ssoins-1234567890abcdef",
            region="us-east-1",
            profile="test-profile",
            categories_included=["users", "groups", "permission_sets"],
            filters_applied={},
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
            assignment_growth_trend=None,
        )

        access_matrix = AccessMatrix(
            user_to_accounts={"user1": ["123456789012", "123456789013"], "user2": ["123456789012"]},
            user_to_permission_sets={"user1": ["ps1", "ps2"], "user2": ["ps1"]},
            group_to_accounts={"group1": ["123456789012"], "group2": ["123456789013"]},
            group_to_permission_sets={"group1": ["ps1"], "group2": ["ps2"]},
            account_to_users={"123456789012": ["user1", "user2"], "123456789013": ["user1"]},
            account_to_groups={"123456789012": ["group1"], "123456789013": ["group2"]},
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

        return StatisticsReport(
            metadata=metadata,
            user_group_metrics=user_group_metrics,
            permission_set_metrics=permission_set_metrics,
            account_metrics=account_metrics,
            assignment_patterns=assignment_patterns,
            governance_view=governance_view,
            historical_comparison=None,
        )

    def test_apply_filters_no_filters(self, sample_report):
        """Test apply_filters with no filters returns original report."""
        exporter = StatisticsExporter()
        result = exporter.apply_filters(sample_report, {})

        # Should be essentially the same (deep copy creates new object)
        assert result.user_group_metrics.total_users == sample_report.user_group_metrics.total_users
        assert (
            result.permission_set_metrics.total_permission_sets
            == sample_report.permission_set_metrics.total_permission_sets
        )

    def test_apply_filters_account_filter_string(self, sample_report):
        """Test filtering by single account ID as string."""
        exporter = StatisticsExporter()
        filters = {"account": "123456789012"}
        result = exporter.apply_filters(sample_report, filters)

        # Should only have data for the filtered account
        assert "123456789012" in result.account_metrics.assignments_per_account
        assert "123456789013" not in result.account_metrics.assignments_per_account
        assert "123456789014" not in result.account_metrics.assignments_per_account

        # Check access matrix filtering
        assert "123456789012" in result.governance_view.access_matrix.account_to_users
        assert "123456789013" not in result.governance_view.access_matrix.account_to_users

        # Check metadata updated
        assert result.metadata.filters_applied["account"] == "123456789012"

    def test_apply_filters_account_filter_list(self, sample_report):
        """Test filtering by multiple account IDs as list."""
        exporter = StatisticsExporter()
        filters = {"account": ["123456789012", "123456789014"]}
        result = exporter.apply_filters(sample_report, filters)

        # Should have data for both filtered accounts
        assert "123456789012" in result.account_metrics.assignments_per_account
        assert "123456789014" in result.account_metrics.accounts_with_no_assignments
        assert "123456789013" not in result.account_metrics.assignments_per_account

    def test_apply_filters_user_filter(self, sample_report):
        """Test filtering by user ID."""
        exporter = StatisticsExporter()
        filters = {"user": "user1"}
        result = exporter.apply_filters(sample_report, filters)

        # Should only have data for user1
        assert "user1" in result.user_group_metrics.groups_per_user
        assert "user2" not in result.user_group_metrics.groups_per_user

        # Check assignment patterns
        user_assignments = [
            user for user, count in result.assignment_patterns.users_with_most_assignments
        ]
        assert "user1" in user_assignments
        assert "user2" not in user_assignments

        # Check access matrix
        assert "user1" in result.governance_view.access_matrix.user_to_accounts
        assert "user2" not in result.governance_view.access_matrix.user_to_accounts

    def test_apply_filters_group_filter(self, sample_report):
        """Test filtering by group ID."""
        exporter = StatisticsExporter()
        filters = {"group": ["group1", "group3"]}
        result = exporter.apply_filters(sample_report, filters)

        # Should only have data for group1 and group3
        assert "group1" in result.user_group_metrics.users_per_group
        assert "group3" in result.user_group_metrics.orphaned_groups
        assert "group2" not in result.user_group_metrics.users_per_group

        # Check largest groups
        group_names = [group for group, count in result.user_group_metrics.largest_groups]
        assert "group1" in group_names
        assert "group2" not in group_names

    def test_apply_filters_permission_set_filter(self, sample_report):
        """Test filtering by permission set ARN."""
        exporter = StatisticsExporter()
        filters = {"permission_set": ["ps1", "ps3"]}
        result = exporter.apply_filters(sample_report, filters)

        # Should only have data for ps1 and ps3
        assert "ps1" in result.permission_set_metrics.assignments_per_permission_set
        assert "ps3" in result.permission_set_metrics.unused_permission_sets
        assert "ps2" not in result.permission_set_metrics.assignments_per_permission_set

        # Check total count updated
        assert result.permission_set_metrics.total_permission_sets == 2

        # Check average recalculated (ps1: 5 assignments, ps3: 0 assignments = 2.5 average)
        assert result.permission_set_metrics.average_assignments_per_permission_set == 2.5

    def test_apply_filters_high_risk_only(self, sample_report):
        """Test high-risk only filter."""
        exporter = StatisticsExporter()
        filters = {"high_risk_only": True}
        result = exporter.apply_filters(sample_report, filters)

        # Should only show privileged permission sets
        ps_names = [ps for ps, count in result.permission_set_metrics.most_assigned_permission_sets]
        assert "ps1" in ps_names  # ps1 is privileged
        assert "ps2" not in ps_names  # ps2 is not privileged

        # Should only show admin users
        user_names = [
            user for user, count in result.assignment_patterns.users_with_most_assignments
        ]
        assert "user1" in user_names  # user1 has admin access
        assert "user2" not in user_names  # user2 doesn't have admin access

        # Should only show high-severity compliance gaps
        severities = [gap.severity for gap in result.governance_view.compliance_gaps]
        assert "high" in severities
        assert "medium" not in severities

    def test_apply_filters_orphaned_only(self, sample_report):
        """Test orphaned resources only filter."""
        exporter = StatisticsExporter()
        filters = {"orphaned_only": True}
        result = exporter.apply_filters(sample_report, filters)

        # Should clear non-orphaned data
        assert len(result.user_group_metrics.users_per_group) == 0
        assert len(result.permission_set_metrics.assignments_per_permission_set) == 0
        assert len(result.account_metrics.assignments_per_account) == 0

        # Should keep orphaned data
        assert len(result.user_group_metrics.orphaned_users) > 0
        assert len(result.user_group_metrics.orphaned_groups) > 0
        assert len(result.permission_set_metrics.unused_permission_sets) > 0

        # Should clear access matrix (orphaned resources have no access)
        assert len(result.governance_view.access_matrix.user_to_accounts) == 0

    def test_apply_filters_privileged_only(self, sample_report):
        """Test privileged access only filter."""
        exporter = StatisticsExporter()
        filters = {"privileged_only": True}
        result = exporter.apply_filters(sample_report, filters)

        # Should only show privileged permission sets
        assert "ps1" in result.permission_set_metrics.assignments_per_permission_set
        assert "ps2" not in result.permission_set_metrics.assignments_per_permission_set

        # Should only show admin users
        assert "user1" in result.user_group_metrics.groups_per_user
        assert "user2" not in result.user_group_metrics.groups_per_user

        # Should filter access matrix to privileged access only
        assert "user1" in result.governance_view.access_matrix.user_to_permission_sets
        assert "ps1" in result.governance_view.access_matrix.user_to_permission_sets["user1"]
        assert "ps2" not in result.governance_view.access_matrix.user_to_permission_sets.get(
            "user1", []
        )

    def test_apply_filters_multiple_filters(self, sample_report):
        """Test applying multiple filters together."""
        exporter = StatisticsExporter()
        filters = {"account": "123456789012", "user": "user1", "high_risk_only": True}
        result = exporter.apply_filters(sample_report, filters)

        # Should apply all filters
        assert "123456789012" in result.account_metrics.assignments_per_account
        assert "123456789013" not in result.account_metrics.assignments_per_account

        assert "user1" in result.user_group_metrics.groups_per_user
        assert "user2" not in result.user_group_metrics.groups_per_user

        # High-risk filter should also be applied
        severities = [gap.severity for gap in result.governance_view.compliance_gaps]
        assert all(severity in ["high", "critical"] for severity in severities)

    def test_apply_filters_preserves_original(self, sample_report):
        """Test that filtering doesn't modify the original report."""
        exporter = StatisticsExporter()
        original_user_count = sample_report.user_group_metrics.total_users
        original_accounts = len(sample_report.account_metrics.assignments_per_account)

        filters = {"account": "123456789012"}
        result = exporter.apply_filters(sample_report, filters)

        # Original should be unchanged
        assert sample_report.user_group_metrics.total_users == original_user_count
        assert len(sample_report.account_metrics.assignments_per_account) == original_accounts

        # Result should be different
        assert len(result.account_metrics.assignments_per_account) < original_accounts

    def test_apply_filters_updates_metadata(self, sample_report):
        """Test that filters are recorded in metadata."""
        exporter = StatisticsExporter()
        filters = {"account": "123456789012", "high_risk_only": True}
        result = exporter.apply_filters(sample_report, filters)

        # Metadata should include applied filters
        assert result.metadata.filters_applied["account"] == "123456789012"
        assert result.metadata.filters_applied["high_risk_only"] is True

    def test_get_preset_filters(self):
        """Test getting preset filter configurations."""
        exporter = StatisticsExporter()
        presets = exporter.get_preset_filters()

        # Should have expected presets
        assert "high_risk" in presets
        assert "orphaned_resources" in presets
        assert "privileged_access" in presets

        # Each preset should have description
        for preset_name, preset_config in presets.items():
            assert "description" in preset_config
            assert isinstance(preset_config["description"], str)

        # Check specific preset configurations
        assert presets["high_risk"]["high_risk_only"] is True
        assert presets["orphaned_resources"]["orphaned_only"] is True
        assert presets["privileged_access"]["privileged_only"] is True

    def test_apply_filters_edge_cases(self, sample_report):
        """Test edge cases in filtering."""
        exporter = StatisticsExporter()

        # Test with non-existent account
        filters1 = {"account": "999999999999"}
        result = exporter.apply_filters(sample_report, filters1)
        assert len(result.account_metrics.assignments_per_account) == 0

        # Test with non-existent user
        filters2 = {"user": "nonexistent_user"}
        result = exporter.apply_filters(sample_report, filters2)
        assert len(result.user_group_metrics.groups_per_user) == 0

        # Test with empty filter values
        filters3: Dict[str, Any] = {"account": []}
        result = exporter.apply_filters(sample_report, filters3)
        assert len(result.account_metrics.assignments_per_account) == 0

    def test_apply_filters_type_conversion(self, sample_report):
        """Test that filters handle type conversion properly."""
        exporter = StatisticsExporter()

        # Test integer account ID
        filters = {"account": 123456789012}
        result = exporter.apply_filters(sample_report, filters)
        assert "123456789012" in result.account_metrics.assignments_per_account

    def test_apply_filters_error_handling(self):
        """Test error handling in apply_filters."""
        exporter = StatisticsExporter()

        with pytest.raises(ValueError, match="Failed to apply filters"):
            exporter.apply_filters(None, {"account": "123456789012"})  # type: ignore

    def test_filter_integration_with_export(self, sample_report):
        """Test that filtering works with export methods."""
        exporter = StatisticsExporter()

        # Apply filters
        filters = {"user": "user1", "high_risk_only": True}
        filtered_report = exporter.apply_filters(sample_report, filters)

        # Export filtered report
        json_result = exporter.export_to_json(filtered_report)
        csv_result = exporter.export_to_csv(
            filtered_report, category="users"
        )  # Use users category to see user data
        text_result = exporter.export_to_text(filtered_report)

        # All exports should work and contain filtered data
        assert "user1" in json_result
        assert "user2" not in json_result

        assert "user1" in csv_result
        assert "user2" not in csv_result

        assert "user1" in text_result
        assert "user2" not in text_result
