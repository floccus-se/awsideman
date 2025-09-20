"""Unit tests for supporting data models in statistics module."""

import pytest

from src.awsideman.statistics.models import (
    AccessMatrix,
    GrowthMetric,
    PrivilegedAccessReport,
    PrivilegePattern,
    SignificantChange,
    TrendAnalysis,
    ValidationError,
    validate_access_matrix,
    validate_privileged_access_report,
    validate_trend_analysis,
)


class TestAccessMatrix:
    """Test AccessMatrix model and validation."""

    def test_access_matrix_creation(self):
        """Test creating an AccessMatrix instance."""
        matrix = AccessMatrix(
            user_to_accounts={"user1": ["account1", "account2"]},
            user_to_permission_sets={"user1": ["ps1", "ps2"]},
            group_to_accounts={"group1": ["account1"]},
            group_to_permission_sets={"group1": ["ps1"]},
            account_to_users={"account1": ["user1"]},
            account_to_groups={"account1": ["group1"]},
        )

        assert matrix.user_to_accounts["user1"] == ["account1", "account2"]
        assert matrix.user_to_permission_sets["user1"] == ["ps1", "ps2"]
        assert matrix.group_to_accounts["group1"] == ["account1"]
        assert matrix.group_to_permission_sets["group1"] == ["ps1"]
        assert matrix.account_to_users["account1"] == ["user1"]
        assert matrix.account_to_groups["account1"] == ["group1"]

    def test_access_matrix_validation_success(self):
        """Test successful validation of AccessMatrix."""
        matrix = AccessMatrix(
            user_to_accounts={"user1": ["account1"]},
            user_to_permission_sets={"user1": ["ps1"]},
            group_to_accounts={"group1": ["account1"]},
            group_to_permission_sets={"group1": ["ps1"]},
            account_to_users={"account1": ["user1"]},
            account_to_groups={"account1": ["group1"]},
        )

        # Should not raise any exception
        validate_access_matrix(matrix)

    def test_access_matrix_validation_invalid_user_accounts(self):
        """Test validation failure when user_to_accounts contains non-list."""
        # Create matrix with invalid data (bypassing type checking for testing)
        matrix = AccessMatrix(
            user_to_accounts={},
            user_to_permission_sets={"user1": ["ps1"]},
            group_to_accounts={"group1": ["account1"]},
            group_to_permission_sets={"group1": ["ps1"]},
            account_to_users={"account1": ["user1"]},
            account_to_groups={"account1": ["group1"]},
        )
        # Manually set invalid data for testing
        matrix.user_to_accounts["user1"] = "account1"  # type: ignore

        with pytest.raises(ValidationError, match="Accounts for user user1 must be a list"):
            validate_access_matrix(matrix)

    def test_access_matrix_validation_invalid_group_permission_sets(self):
        """Test validation failure when group_to_permission_sets contains non-list."""
        matrix = AccessMatrix(
            user_to_accounts={"user1": ["account1"]},
            user_to_permission_sets={"user1": ["ps1"]},
            group_to_accounts={"group1": ["account1"]},
            group_to_permission_sets={},
            account_to_users={"account1": ["user1"]},
            account_to_groups={"account1": ["group1"]},
        )
        # Manually set invalid data for testing
        matrix.group_to_permission_sets["group1"] = "ps1"  # type: ignore

        with pytest.raises(
            ValidationError, match="Permission sets for group group1 must be a list"
        ):
            validate_access_matrix(matrix)


class TestPrivilegedAccessReport:
    """Test PrivilegedAccessReport model and validation."""

    def test_privileged_access_report_creation(self):
        """Test creating a PrivilegedAccessReport instance."""
        privilege_pattern = PrivilegePattern(
            pattern_type="admin_access",
            description="Administrative access pattern",
            affected_entities=["user1", "group1"],
            risk_level="high",
        )

        report = PrivilegedAccessReport(
            admin_permission_sets=["AdminAccess", "PowerUserAccess"],
            accounts_with_admin_access={"account1": ["user1", "group1"]},
            users_with_admin_access=["user1"],
            high_privilege_patterns=[privilege_pattern],
        )

        assert report.admin_permission_sets == ["AdminAccess", "PowerUserAccess"]
        assert report.accounts_with_admin_access["account1"] == ["user1", "group1"]
        assert report.users_with_admin_access == ["user1"]
        assert len(report.high_privilege_patterns) == 1
        assert report.high_privilege_patterns[0].pattern_type == "admin_access"

    def test_privileged_access_report_validation_success(self):
        """Test successful validation of PrivilegedAccessReport."""
        report = PrivilegedAccessReport(
            admin_permission_sets=["AdminAccess"],
            accounts_with_admin_access={"account1": ["user1"]},
            users_with_admin_access=["user1"],
            high_privilege_patterns=[],
        )

        # Should not raise any exception
        validate_privileged_access_report(report)

    def test_privileged_access_report_validation_invalid_admin_permission_sets(self):
        """Test validation failure when admin_permission_sets is not a list."""
        report = PrivilegedAccessReport(
            admin_permission_sets=[],
            accounts_with_admin_access={"account1": ["user1"]},
            users_with_admin_access=["user1"],
            high_privilege_patterns=[],
        )
        # Manually set invalid data for testing
        report.admin_permission_sets = "AdminAccess"  # type: ignore

        with pytest.raises(ValidationError, match="Admin permission sets must be a list"):
            validate_privileged_access_report(report)

    def test_privileged_access_report_validation_invalid_accounts_structure(self):
        """Test validation failure when accounts_with_admin_access has invalid structure."""
        report = PrivilegedAccessReport(
            admin_permission_sets=["AdminAccess"],
            accounts_with_admin_access={},
            users_with_admin_access=["user1"],
            high_privilege_patterns=[],
        )
        # Manually set invalid data for testing
        report.accounts_with_admin_access["account1"] = "user1"  # type: ignore

        with pytest.raises(
            ValidationError, match="Admin access entities for account account1 must be a list"
        ):
            validate_privileged_access_report(report)


class TestTrendAnalysis:
    """Test TrendAnalysis model and validation."""

    def test_trend_analysis_creation(self):
        """Test creating a TrendAnalysis instance."""
        user_growth = GrowthMetric(
            current_count=100, previous_count=90, growth_rate=11.11, absolute_change=10
        )

        group_growth = GrowthMetric(
            current_count=20, previous_count=18, growth_rate=11.11, absolute_change=2
        )

        permission_set_growth = GrowthMetric(
            current_count=15, previous_count=15, growth_rate=0.0, absolute_change=0
        )

        assignment_growth = GrowthMetric(
            current_count=500, previous_count=450, growth_rate=11.11, absolute_change=50
        )

        significant_change = SignificantChange(
            category="users",
            description="Significant increase in user count",
            impact="positive",
            change_magnitude=11.11,
        )

        analysis = TrendAnalysis(
            user_growth=user_growth,
            group_growth=group_growth,
            permission_set_growth=permission_set_growth,
            assignment_growth=assignment_growth,
            significant_changes=[significant_change],
        )

        assert analysis.user_growth.current_count == 100
        assert analysis.group_growth.current_count == 20
        assert analysis.permission_set_growth.current_count == 15
        assert analysis.assignment_growth.current_count == 500
        assert len(analysis.significant_changes) == 1
        assert analysis.significant_changes[0].category == "users"

    def test_trend_analysis_validation_success(self):
        """Test successful validation of TrendAnalysis."""
        user_growth = GrowthMetric(
            current_count=100, previous_count=90, growth_rate=11.11, absolute_change=10
        )
        group_growth = GrowthMetric(
            current_count=20, previous_count=18, growth_rate=11.11, absolute_change=2
        )
        permission_set_growth = GrowthMetric(
            current_count=15, previous_count=15, growth_rate=0.0, absolute_change=0
        )
        assignment_growth = GrowthMetric(
            current_count=500, previous_count=450, growth_rate=11.11, absolute_change=50
        )

        analysis = TrendAnalysis(
            user_growth=user_growth,
            group_growth=group_growth,
            permission_set_growth=permission_set_growth,
            assignment_growth=assignment_growth,
            significant_changes=[],
        )

        # Should not raise any exception
        validate_trend_analysis(analysis)

    def test_trend_analysis_validation_negative_user_count(self):
        """Test validation failure when user count is negative."""
        user_growth = GrowthMetric(
            current_count=-1, previous_count=90, growth_rate=-101.11, absolute_change=-91
        )
        group_growth = GrowthMetric(
            current_count=20, previous_count=18, growth_rate=11.11, absolute_change=2
        )
        permission_set_growth = GrowthMetric(
            current_count=15, previous_count=15, growth_rate=0.0, absolute_change=0
        )
        assignment_growth = GrowthMetric(
            current_count=500, previous_count=450, growth_rate=11.11, absolute_change=50
        )

        analysis = TrendAnalysis(
            user_growth=user_growth,
            group_growth=group_growth,
            permission_set_growth=permission_set_growth,
            assignment_growth=assignment_growth,
            significant_changes=[],
        )

        with pytest.raises(ValidationError, match="Current user count cannot be negative"):
            validate_trend_analysis(analysis)

    def test_trend_analysis_validation_negative_assignment_count(self):
        """Test validation failure when assignment count is negative."""
        user_growth = GrowthMetric(
            current_count=100, previous_count=90, growth_rate=11.11, absolute_change=10
        )
        group_growth = GrowthMetric(
            current_count=20, previous_count=18, growth_rate=11.11, absolute_change=2
        )
        permission_set_growth = GrowthMetric(
            current_count=15, previous_count=15, growth_rate=0.0, absolute_change=0
        )
        assignment_growth = GrowthMetric(
            current_count=-1, previous_count=450, growth_rate=-100.22, absolute_change=-451
        )

        analysis = TrendAnalysis(
            user_growth=user_growth,
            group_growth=group_growth,
            permission_set_growth=permission_set_growth,
            assignment_growth=assignment_growth,
            significant_changes=[],
        )

        with pytest.raises(ValidationError, match="Current assignment count cannot be negative"):
            validate_trend_analysis(analysis)


class TestPrivilegePattern:
    """Test PrivilegePattern model."""

    def test_privilege_pattern_creation(self):
        """Test creating a PrivilegePattern instance."""
        pattern = PrivilegePattern(
            pattern_type="cross_account_admin",
            description="User has admin access across multiple accounts",
            affected_entities=["user123", "account456", "account789"],
            risk_level="critical",
        )

        assert pattern.pattern_type == "cross_account_admin"
        assert pattern.description == "User has admin access across multiple accounts"
        assert pattern.affected_entities == ["user123", "account456", "account789"]
        assert pattern.risk_level == "critical"


class TestGrowthMetric:
    """Test GrowthMetric model."""

    def test_growth_metric_creation(self):
        """Test creating a GrowthMetric instance."""
        metric = GrowthMetric(
            current_count=150, previous_count=120, growth_rate=25.0, absolute_change=30
        )

        assert metric.current_count == 150
        assert metric.previous_count == 120
        assert metric.growth_rate == 25.0
        assert metric.absolute_change == 30

    def test_growth_metric_negative_growth(self):
        """Test GrowthMetric with negative growth."""
        metric = GrowthMetric(
            current_count=80, previous_count=100, growth_rate=-20.0, absolute_change=-20
        )

        assert metric.current_count == 80
        assert metric.previous_count == 100
        assert metric.growth_rate == -20.0
        assert metric.absolute_change == -20


class TestSignificantChange:
    """Test SignificantChange model."""

    def test_significant_change_creation(self):
        """Test creating a SignificantChange instance."""
        change = SignificantChange(
            category="permission_sets",
            description="New permission set with admin privileges added",
            impact="security_risk",
            change_magnitude=100.0,
        )

        assert change.category == "permission_sets"
        assert change.description == "New permission set with admin privileges added"
        assert change.impact == "security_risk"
        assert change.change_magnitude == 100.0
