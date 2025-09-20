"""Tests for StatisticsExporter JSON export functionality."""

import json
from datetime import datetime

import pytest

from src.awsideman.statistics.exporter import StatisticsExporter, StatisticsJSONEncoder
from src.awsideman.statistics.models import (
    AccessMatrix,
    AccountMetrics,
    AssignmentPatterns,
    EmptyMappings,
    GovernanceView,
    GrowthMetric,
    PermissionSetMetrics,
    PrivilegedAccessReport,
    ReportMetadata,
    SignificantChange,
    StatisticsReport,
    TrendAnalysis,
    UserGroupMetrics,
)


class TestStatisticsJSONEncoder:
    """Test the custom JSON encoder."""

    def test_encode_datetime(self):
        """Test datetime encoding."""
        encoder = StatisticsJSONEncoder()
        dt = datetime(2023, 1, 1, 12, 0, 0)
        result = encoder.default(dt)
        assert result == "2023-01-01T12:00:00"

    def test_encode_tuple(self):
        """Test tuple encoding."""
        encoder = StatisticsJSONEncoder()
        test_tuple = ("user1", 5)
        result = encoder.default(test_tuple)
        assert result == ["user1", 5]

    def test_encode_dataclass(self):
        """Test dataclass encoding."""
        encoder = StatisticsJSONEncoder()
        growth_metric = GrowthMetric(
            current_count=100, previous_count=80, growth_rate=0.25, absolute_change=20
        )
        result = encoder.default(growth_metric)
        expected = {
            "current_count": 100,
            "previous_count": 80,
            "growth_rate": 0.25,
            "absolute_change": 20,
        }
        assert result == expected


class TestStatisticsExporter:
    """Test the StatisticsExporter class."""

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
            users_per_group={"group1": 10, "group2": 15},
            groups_per_user={"user1": 2, "user2": 1},
            groups_per_user_by_name={"user1": 2, "user2": 1},
            largest_groups=[("group2", 15), ("group1", 10)],
            orphaned_users=["user3", "user4"],
            disabled_users=["user5"],
            orphaned_groups=["group3"],
        )

        permission_set_metrics = PermissionSetMetrics(
            total_permission_sets=10,
            assignments_per_permission_set={"ps1": 5, "ps2": 3},
            most_assigned_permission_sets=[("ps1", 5), ("ps2", 3)],
            unused_permission_sets=["ps3"],
            average_assignments_per_permission_set=2.5,
            privileged_permission_sets=["ps1"],
        )

        account_metrics = AccountMetrics(
            total_accounts=5,
            assignments_per_account={"123456789012": 10, "123456789013": 5},
            users_per_account={"123456789012": 8, "123456789013": 3},
            groups_per_account={"123456789012": 2, "123456789013": 1},
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

        governance_view = GovernanceView(
            access_matrix=access_matrix,
            privileged_access_report=privileged_access_report,
            empty_mappings=empty_mappings,
            compliance_gaps=[],
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

    def test_export_to_json_success(self, sample_report):
        """Test successful JSON export."""
        exporter = StatisticsExporter()
        result = exporter.export_to_json(sample_report)

        # Verify it's valid JSON
        parsed = json.loads(result)

        # Verify structure
        assert "export_metadata" in parsed
        assert "statistics_report" in parsed

        # Verify export metadata
        export_meta = parsed["export_metadata"]
        assert export_meta["export_format"] == "json"
        assert export_meta["export_version"] == "1.0"
        assert "export_timestamp" in export_meta

        # Verify report data is present
        report_data = parsed["statistics_report"]
        assert "metadata" in report_data
        assert "user_group_metrics" in report_data
        assert "permission_set_metrics" in report_data
        assert "account_metrics" in report_data
        assert "assignment_patterns" in report_data
        assert "governance_view" in report_data

    def test_export_to_json_with_historical_data(self, sample_report):
        """Test JSON export with historical comparison data."""
        # Add historical comparison
        historical_comparison = TrendAnalysis(
            user_growth=GrowthMetric(100, 80, 0.25, 20),
            group_growth=GrowthMetric(20, 18, 0.11, 2),
            permission_set_growth=GrowthMetric(10, 10, 0.0, 0),
            assignment_growth=GrowthMetric(50, 45, 0.11, 5),
            significant_changes=[
                SignificantChange(
                    category="users",
                    description="Significant user growth",
                    impact="high",
                    change_magnitude=0.25,
                )
            ],
        )
        sample_report.historical_comparison = historical_comparison

        exporter = StatisticsExporter()
        result = exporter.export_to_json(sample_report)

        parsed = json.loads(result)
        report_data = parsed["statistics_report"]

        # Verify historical comparison is included
        assert report_data["historical_comparison"] is not None
        assert "user_growth" in report_data["historical_comparison"]
        assert "significant_changes" in report_data["historical_comparison"]

    def test_export_to_json_datetime_serialization(self, sample_report):
        """Test that datetime objects are properly serialized."""
        exporter = StatisticsExporter()
        result = exporter.export_to_json(sample_report)

        parsed = json.loads(result)
        report_data = parsed["statistics_report"]

        # Verify datetime is serialized as ISO string
        generation_timestamp = report_data["metadata"]["generation_timestamp"]
        assert generation_timestamp == "2023-01-01T12:00:00"

    def test_export_to_json_tuple_serialization(self, sample_report):
        """Test that tuples are properly serialized as lists."""
        exporter = StatisticsExporter()
        result = exporter.export_to_json(sample_report)

        parsed = json.loads(result)
        report_data = parsed["statistics_report"]

        # Verify tuples are converted to lists
        largest_groups = report_data["user_group_metrics"]["largest_groups"]
        assert isinstance(largest_groups, list)
        assert largest_groups[0] == ["group2", 15]
        assert largest_groups[1] == ["group1", 10]

    def test_export_to_json_formatting(self, sample_report):
        """Test JSON formatting and structure."""
        exporter = StatisticsExporter()
        result = exporter.export_to_json(sample_report)

        # Verify it's properly formatted (indented)
        assert "\n" in result
        assert "  " in result  # Should have indentation

        # Verify top-level structure
        parsed = json.loads(result)
        top_level_keys = list(parsed.keys())
        expected_keys = ["export_metadata", "statistics_report"]
        assert set(top_level_keys) == set(expected_keys)

    def test_export_to_json_error_handling(self):
        """Test error handling for invalid data."""
        exporter = StatisticsExporter()

        # Create an invalid report (None)
        with pytest.raises(ValueError, match="Failed to export statistics to JSON"):
            exporter.export_to_json(None)  # type: ignore

    def test_export_json_interface_method(self, sample_report):
        """Test the interface method export_json."""
        exporter = StatisticsExporter()
        result = exporter.export_json(sample_report)

        # Should produce valid JSON with same structure
        parsed_result = json.loads(result)
        assert "export_metadata" in parsed_result
        assert "statistics_report" in parsed_result
        assert parsed_result["export_metadata"]["export_format"] == "json"

    def test_json_output_structure_completeness(self, sample_report):
        """Test that all expected fields are present in JSON output."""
        exporter = StatisticsExporter()
        result = exporter.export_to_json(sample_report)

        parsed = json.loads(result)
        report_data = parsed["statistics_report"]

        # Verify all main sections are present
        expected_sections = [
            "metadata",
            "user_group_metrics",
            "permission_set_metrics",
            "account_metrics",
            "assignment_patterns",
            "governance_view",
            "historical_comparison",
        ]

        for section in expected_sections:
            assert section in report_data

        # Verify metadata fields
        metadata = report_data["metadata"]
        expected_metadata_fields = [
            "generation_timestamp",
            "instance_arn",
            "region",
            "profile",
            "categories_included",
            "filters_applied",
            "data_collection_duration",
            "analysis_duration",
        ]

        for field in expected_metadata_fields:
            assert field in metadata

    def test_json_sensitive_data_handling(self, sample_report):
        """Test that sensitive data is properly included (not masked in JSON export)."""
        exporter = StatisticsExporter()
        result = exporter.export_to_json(sample_report)

        # Verify JSON is valid
        json.loads(result)

        # JSON export should include actual ARNs and account IDs for programmatic access
        assert "arn:aws:sso:::instance/ssoins-1234567890abcdef" in result
        assert "123456789012" in result
        assert "123456789013" in result
