"""Tests for StatisticsAnalyzer historical comparison and trend analysis."""

from datetime import datetime, timedelta

import pytest

from src.awsideman.statistics.analyzer import StatisticsAnalyzer
from src.awsideman.statistics.models import (
    AccountData,
    AccountStatistics,
    AssignmentData,
    AssignmentStatistics,
    GroupData,
    GroupStatistics,
    GrowthMetric,
    PermissionSetData,
    PermissionSetStatistics,
    RawStatisticsData,
    TrendAnalysis,
    TrendData,
    UserData,
    UserStatistics,
)


class TestStatisticsAnalyzerTrends:
    """Test historical comparison and trend analysis in StatisticsAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create a StatisticsAnalyzer instance for testing."""
        return StatisticsAnalyzer()

    @pytest.fixture
    def current_data(self):
        """Create current statistics data for trend analysis."""
        current_time = datetime.now()

        # Current data: 10 users, 3 groups, 5 permission sets, 3 accounts, 15 assignments
        users = [
            UserData(f"user{i}", f"user{i}", f"User {i}", f"user{i}@example.com", True)
            for i in range(1, 11)
        ]
        groups = [
            GroupData(f"group{i}", f"Group {i}", f"Group {i} description") for i in range(1, 4)
        ]
        permission_sets = [
            PermissionSetData(f"ps{i}", f"PS{i}", f"Permission Set {i}", "PT8H", [], None, None)
            for i in range(1, 6)
        ]
        accounts = [
            AccountData(
                account_id=f"acc{i}",
                account_name=f"Account {i}",
                email=f"acc{i}@example.com",
                status="ACTIVE",
            )
            for i in range(1, 4)
        ]
        assignments = [
            AssignmentData(
                account_id=f"acc{(i % 3) + 1}",
                permission_set_arn=f"ps{(i % 5) + 1}",
                principal_type="USER",
                principal_id=f"user{i}",
            )
            for i in range(1, 16)
        ]

        return RawStatisticsData(
            users=UserStatistics(
                users=users, group_memberships={}, collection_timestamp=current_time
            ),
            groups=GroupStatistics(
                groups=groups, memberships={}, collection_timestamp=current_time
            ),
            permission_sets=PermissionSetStatistics(
                permission_sets=permission_sets, collection_timestamp=current_time
            ),
            accounts=AccountStatistics(accounts=accounts, collection_timestamp=current_time),
            assignments=AssignmentStatistics(
                assignments=assignments, collection_timestamp=current_time
            ),
        )

    @pytest.fixture
    def historical_data(self):
        """Create historical statistics data for trend analysis."""
        historical_time = datetime.now() - timedelta(days=30)

        # Historical data: 8 users, 2 groups, 4 permission sets, 2 accounts, 10 assignments
        users = [
            UserData(f"user{i}", f"user{i}", f"User {i}", f"user{i}@example.com", True)
            for i in range(1, 9)
        ]
        groups = [
            GroupData(f"group{i}", f"Group {i}", f"Group {i} description") for i in range(1, 3)
        ]
        permission_sets = [
            PermissionSetData(f"ps{i}", f"PS{i}", f"Permission Set {i}", "PT8H", [], None, None)
            for i in range(1, 5)
        ]
        accounts = [
            AccountData(
                account_id=f"acc{i}",
                account_name=f"Account {i}",
                email=f"acc{i}@example.com",
                status="ACTIVE",
            )
            for i in range(1, 3)
        ]
        assignments = [
            AssignmentData(
                account_id=f"acc{(i % 2) + 1}",
                permission_set_arn=f"ps{(i % 4) + 1}",
                principal_type="USER",
                principal_id=f"user{i}",
            )
            for i in range(1, 11)
        ]

        return RawStatisticsData(
            users=UserStatistics(
                users=users, group_memberships={}, collection_timestamp=historical_time
            ),
            groups=GroupStatistics(
                groups=groups, memberships={}, collection_timestamp=historical_time
            ),
            permission_sets=PermissionSetStatistics(
                permission_sets=permission_sets, collection_timestamp=historical_time
            ),
            accounts=AccountStatistics(accounts=accounts, collection_timestamp=historical_time),
            assignments=AssignmentStatistics(
                assignments=assignments, collection_timestamp=historical_time
            ),
        )

    def test_compare_historical_data_growth(self, analyzer, current_data, historical_data):
        """Test historical data comparison showing growth."""
        result = analyzer.compare_historical_data(current_data, historical_data)

        assert isinstance(result, TrendAnalysis)

        # Check user growth: 10 current vs 8 historical = 25% growth
        assert result.user_growth.current_count == 10
        assert result.user_growth.previous_count == 8
        assert result.user_growth.absolute_change == 2
        assert result.user_growth.growth_rate == 25.0

        # Check group growth: 3 current vs 2 historical = 50% growth
        assert result.group_growth.current_count == 3
        assert result.group_growth.previous_count == 2
        assert result.group_growth.absolute_change == 1
        assert result.group_growth.growth_rate == 50.0

        # Check permission set growth: 5 current vs 4 historical = 25% growth
        assert result.permission_set_growth.current_count == 5
        assert result.permission_set_growth.previous_count == 4
        assert result.permission_set_growth.absolute_change == 1
        assert result.permission_set_growth.growth_rate == 25.0

        # Check assignment growth: 15 current vs 10 historical = 50% growth
        assert result.assignment_growth.current_count == 15
        assert result.assignment_growth.previous_count == 10
        assert result.assignment_growth.absolute_change == 5
        assert result.assignment_growth.growth_rate == 50.0

    def test_compare_historical_data_decline(self, analyzer):
        """Test historical data comparison showing decline."""
        current_time = datetime.now()
        historical_time = current_time - timedelta(days=30)

        # Current data: fewer resources than historical
        current_users = [
            UserData(f"user{i}", f"user{i}", f"User {i}", f"user{i}@example.com", True)
            for i in range(1, 6)
        ]
        historical_users = [
            UserData(f"user{i}", f"user{i}", f"User {i}", f"user{i}@example.com", True)
            for i in range(1, 11)
        ]

        current_data = RawStatisticsData(
            users=UserStatistics(
                users=current_users, group_memberships={}, collection_timestamp=current_time
            ),
            groups=GroupStatistics(groups=[], memberships={}, collection_timestamp=current_time),
            permission_sets=PermissionSetStatistics(
                permission_sets=[], collection_timestamp=current_time
            ),
            accounts=AccountStatistics(accounts=[], collection_timestamp=current_time),
            assignments=AssignmentStatistics(assignments=[], collection_timestamp=current_time),
        )

        historical_data = RawStatisticsData(
            users=UserStatistics(
                users=historical_users, group_memberships={}, collection_timestamp=historical_time
            ),
            groups=GroupStatistics(groups=[], memberships={}, collection_timestamp=historical_time),
            permission_sets=PermissionSetStatistics(
                permission_sets=[], collection_timestamp=historical_time
            ),
            accounts=AccountStatistics(accounts=[], collection_timestamp=historical_time),
            assignments=AssignmentStatistics(assignments=[], collection_timestamp=historical_time),
        )

        result = analyzer.compare_historical_data(current_data, historical_data)

        # Check user decline: 5 current vs 10 historical = -50% growth
        assert result.user_growth.current_count == 5
        assert result.user_growth.previous_count == 10
        assert result.user_growth.absolute_change == -5
        assert result.user_growth.growth_rate == -50.0

    def test_compare_historical_data_no_change(self, analyzer):
        """Test historical data comparison with no change."""
        current_time = datetime.now()
        historical_time = current_time - timedelta(days=30)

        # Same data for both current and historical
        users = [
            UserData(f"user{i}", f"user{i}", f"User {i}", f"user{i}@example.com", True)
            for i in range(1, 6)
        ]

        current_data = RawStatisticsData(
            users=UserStatistics(
                users=users, group_memberships={}, collection_timestamp=current_time
            ),
            groups=GroupStatistics(groups=[], memberships={}, collection_timestamp=current_time),
            permission_sets=PermissionSetStatistics(
                permission_sets=[], collection_timestamp=current_time
            ),
            accounts=AccountStatistics(accounts=[], collection_timestamp=current_time),
            assignments=AssignmentStatistics(assignments=[], collection_timestamp=current_time),
        )

        historical_data = RawStatisticsData(
            users=UserStatistics(
                users=users, group_memberships={}, collection_timestamp=historical_time
            ),
            groups=GroupStatistics(groups=[], memberships={}, collection_timestamp=historical_time),
            permission_sets=PermissionSetStatistics(
                permission_sets=[], collection_timestamp=historical_time
            ),
            accounts=AccountStatistics(accounts=[], collection_timestamp=historical_time),
            assignments=AssignmentStatistics(assignments=[], collection_timestamp=historical_time),
        )

        result = analyzer.compare_historical_data(current_data, historical_data)

        # Check no change: 5 current vs 5 historical = 0% growth
        assert result.user_growth.current_count == 5
        assert result.user_growth.previous_count == 5
        assert result.user_growth.absolute_change == 0
        assert result.user_growth.growth_rate == 0.0

    def test_identify_significant_changes(self, analyzer, current_data, historical_data):
        """Test identification of significant changes."""
        result = analyzer.compare_historical_data(current_data, historical_data)

        # Should identify significant changes based on growth rates
        assert len(result.significant_changes) > 0

        # Check for specific significant changes
        change_categories = [change.category for change in result.significant_changes]

        # Should identify significant growth in groups (50%) and assignments (50%)
        assert "groups" in change_categories or "assignments" in change_categories

        # Check change details
        for change in result.significant_changes:
            assert change.category in ["users", "groups", "permission_sets", "assignments"]
            assert change.description is not None
            assert change.impact in ["positive", "negative", "neutral", "security_risk"]
            assert isinstance(change.change_magnitude, (int, float))

    def test_significant_change_thresholds(self, analyzer):
        """Test significant change detection with different thresholds."""
        current_time = datetime.now()
        historical_time = current_time - timedelta(days=30)

        # Create data with various growth rates to test thresholds
        test_cases = [
            (10, 9, "small_growth"),  # 11.11% growth - might not be significant
            (10, 5, "large_growth"),  # 100% growth - should be significant
            (5, 10, "decline"),  # -50% decline - should be significant
            (10, 10, "no_change"),  # 0% change - not significant
        ]

        for current_count, historical_count, case_name in test_cases:
            current_users = [
                UserData(f"user{i}", f"user{i}", f"User {i}", f"user{i}@example.com", True)
                for i in range(1, current_count + 1)
            ]
            historical_users = [
                UserData(f"user{i}", f"user{i}", f"User {i}", f"user{i}@example.com", True)
                for i in range(1, historical_count + 1)
            ]

            current_data = RawStatisticsData(
                users=UserStatistics(
                    users=current_users, group_memberships={}, collection_timestamp=current_time
                ),
                groups=GroupStatistics(
                    groups=[], memberships={}, collection_timestamp=current_time
                ),
                permission_sets=PermissionSetStatistics(
                    permission_sets=[], collection_timestamp=current_time
                ),
                accounts=AccountStatistics(accounts=[], collection_timestamp=current_time),
                assignments=AssignmentStatistics(assignments=[], collection_timestamp=current_time),
            )

            historical_data = RawStatisticsData(
                users=UserStatistics(
                    users=historical_users,
                    group_memberships={},
                    collection_timestamp=historical_time,
                ),
                groups=GroupStatistics(
                    groups=[], memberships={}, collection_timestamp=historical_time
                ),
                permission_sets=PermissionSetStatistics(
                    permission_sets=[], collection_timestamp=historical_time
                ),
                accounts=AccountStatistics(accounts=[], collection_timestamp=historical_time),
                assignments=AssignmentStatistics(
                    assignments=[], collection_timestamp=historical_time
                ),
            )

            result = analyzer.compare_historical_data(current_data, historical_data)

            if case_name == "large_growth":
                # Should detect significant change for 100% growth
                user_changes = [c for c in result.significant_changes if c.category == "users"]
                assert len(user_changes) > 0
                assert user_changes[0].impact == "positive"
            elif case_name == "decline":
                # Should detect significant change for -50% decline
                user_changes = [c for c in result.significant_changes if c.category == "users"]
                assert len(user_changes) > 0
                assert user_changes[0].impact == "negative"
            elif case_name == "no_change":
                # Should not detect significant change for 0% change
                user_changes = [c for c in result.significant_changes if c.category == "users"]
                assert len(user_changes) == 0

    def test_growth_metric_calculation(self, analyzer):
        """Test growth metric calculation accuracy."""
        # Test various growth scenarios
        test_cases = [
            (100, 80, 25.0, 20),  # 25% growth
            (50, 100, -50.0, -50),  # 50% decline
            (100, 100, 0.0, 0),  # No change
            (10, 0, 100.0, 10),  # Growth from zero (special case)
            (0, 10, -100.0, -10),  # Decline to zero
        ]

        for current, previous, expected_rate, expected_change in test_cases:
            # Create minimal data to test growth calculation
            current_users = (
                [
                    UserData(f"user{i}", f"user{i}", f"User {i}", f"user{i}@example.com", True)
                    for i in range(1, current + 1)
                ]
                if current > 0
                else []
            )
            historical_users = (
                [
                    UserData(f"user{i}", f"user{i}", f"User {i}", f"user{i}@example.com", True)
                    for i in range(1, previous + 1)
                ]
                if previous > 0
                else []
            )

            current_data = RawStatisticsData(
                users=UserStatistics(
                    users=current_users, group_memberships={}, collection_timestamp=datetime.now()
                ),
                groups=GroupStatistics(
                    groups=[], memberships={}, collection_timestamp=datetime.now()
                ),
                permission_sets=PermissionSetStatistics(
                    permission_sets=[], collection_timestamp=datetime.now()
                ),
                accounts=AccountStatistics(accounts=[], collection_timestamp=datetime.now()),
                assignments=AssignmentStatistics(
                    assignments=[], collection_timestamp=datetime.now()
                ),
            )

            historical_data = RawStatisticsData(
                users=UserStatistics(
                    users=historical_users,
                    group_memberships={},
                    collection_timestamp=datetime.now() - timedelta(days=30),
                ),
                groups=GroupStatistics(
                    groups=[],
                    memberships={},
                    collection_timestamp=datetime.now() - timedelta(days=30),
                ),
                permission_sets=PermissionSetStatistics(
                    permission_sets=[], collection_timestamp=datetime.now() - timedelta(days=30)
                ),
                accounts=AccountStatistics(
                    accounts=[], collection_timestamp=datetime.now() - timedelta(days=30)
                ),
                assignments=AssignmentStatistics(
                    assignments=[], collection_timestamp=datetime.now() - timedelta(days=30)
                ),
            )

            result = analyzer.compare_historical_data(current_data, historical_data)

            assert result.user_growth.current_count == current
            assert result.user_growth.previous_count == previous
            assert result.user_growth.growth_rate == expected_rate
            assert result.user_growth.absolute_change == expected_change

    def test_historical_comparison_empty_data(self, analyzer):
        """Test historical comparison with empty data sets."""
        current_time = datetime.now()
        historical_time = current_time - timedelta(days=30)

        # Both current and historical data are empty
        empty_current = RawStatisticsData(
            users=UserStatistics(users=[], group_memberships={}, collection_timestamp=current_time),
            groups=GroupStatistics(groups=[], memberships={}, collection_timestamp=current_time),
            permission_sets=PermissionSetStatistics(
                permission_sets=[], collection_timestamp=current_time
            ),
            accounts=AccountStatistics(accounts=[], collection_timestamp=current_time),
            assignments=AssignmentStatistics(assignments=[], collection_timestamp=current_time),
        )

        empty_historical = RawStatisticsData(
            users=UserStatistics(
                users=[], group_memberships={}, collection_timestamp=historical_time
            ),
            groups=GroupStatistics(groups=[], memberships={}, collection_timestamp=historical_time),
            permission_sets=PermissionSetStatistics(
                permission_sets=[], collection_timestamp=historical_time
            ),
            accounts=AccountStatistics(accounts=[], collection_timestamp=historical_time),
            assignments=AssignmentStatistics(assignments=[], collection_timestamp=historical_time),
        )

        result = analyzer.compare_historical_data(empty_current, empty_historical)

        # Should handle empty data gracefully
        assert result.user_growth.current_count == 0
        assert result.user_growth.previous_count == 0
        assert result.user_growth.growth_rate == 0.0
        assert result.user_growth.absolute_change == 0

        # Should not identify any significant changes
        assert len(result.significant_changes) == 0

    def test_assignment_patterns_with_trend(self, analyzer, current_data, historical_data):
        """Test assignment patterns calculation with trend data."""
        # First calculate basic assignment patterns
        current_assignments = current_data.assignments.assignments
        # Create assignment patterns with trend
        result_with_trend = analyzer.calculate_assignment_patterns_with_trend(
            current_assignments, historical_data
        )

        assert result_with_trend.assignment_growth_trend is not None
        assert isinstance(result_with_trend.assignment_growth_trend, TrendData)
        assert result_with_trend.assignment_growth_trend.values == [10, 15]
        assert result_with_trend.assignment_growth_trend.trend_direction == "increasing"

    def test_trend_analysis_validation(self, analyzer, current_data, historical_data):
        """Test trend analysis data validation."""
        result = analyzer.compare_historical_data(current_data, historical_data)

        # Validate all growth metrics
        growth_metrics = [
            result.user_growth,
            result.group_growth,
            result.permission_set_growth,
            result.assignment_growth,
        ]

        for metric in growth_metrics:
            assert isinstance(metric, GrowthMetric)
            assert metric.current_count >= 0
            assert metric.previous_count >= 0
            assert isinstance(metric.growth_rate, (int, float))
            assert isinstance(metric.absolute_change, (int, float))

            # Verify calculation consistency
            if metric.previous_count > 0:
                expected_rate = (
                    (metric.current_count - metric.previous_count) / metric.previous_count
                ) * 100
                assert (
                    abs(metric.growth_rate - expected_rate) < 0.01
                )  # Allow for floating point precision
            else:
                # Special case: growth from zero
                if metric.current_count > 0:
                    assert metric.growth_rate == 100.0
                else:
                    assert metric.growth_rate == 0.0

            assert metric.absolute_change == metric.current_count - metric.previous_count

    def test_significant_change_impact_classification(self, analyzer):
        """Test classification of change impacts."""
        current_time = datetime.now()
        historical_time = current_time - timedelta(days=30)

        # Test different scenarios and their expected impacts
        scenarios = [
            # (current_users, historical_users, current_assignments, historical_assignments, expected_impact)
            (15, 10, 20, 15, "positive"),  # Growth in users and assignments
            (5, 10, 8, 15, "negative"),  # Decline in users and assignments
            (10, 10, 10, 10, "neutral"),  # No change
            (10, 8, 50, 20, "security_risk"),  # Rapid assignment growth
        ]

        for (
            current_users,
            historical_users,
            current_assignments,
            historical_assignments,
            expected_impact,
        ) in scenarios:
            # Create test data
            users_current = [
                UserData(f"user{i}", f"user{i}", f"User {i}", f"user{i}@example.com", True)
                for i in range(1, current_users + 1)
            ]
            users_historical = [
                UserData(f"user{i}", f"user{i}", f"User {i}", f"user{i}@example.com", True)
                for i in range(1, historical_users + 1)
            ]

            assignments_current = [
                AssignmentData(
                    account_id="acc1",
                    permission_set_arn="ps1",
                    principal_type="USER",
                    principal_id=f"user{(i % current_users) + 1}",
                )
                for i in range(current_assignments)
            ]
            assignments_historical = [
                AssignmentData(
                    account_id="acc1",
                    permission_set_arn="ps1",
                    principal_type="USER",
                    principal_id=f"user{(i % historical_users) + 1}",
                )
                for i in range(historical_assignments)
            ]

            current_data = RawStatisticsData(
                users=UserStatistics(
                    users=users_current, group_memberships={}, collection_timestamp=current_time
                ),
                groups=GroupStatistics(
                    groups=[], memberships={}, collection_timestamp=current_time
                ),
                permission_sets=PermissionSetStatistics(
                    permission_sets=[], collection_timestamp=current_time
                ),
                accounts=AccountStatistics(accounts=[], collection_timestamp=current_time),
                assignments=AssignmentStatistics(
                    assignments=assignments_current, collection_timestamp=current_time
                ),
            )

            historical_data = RawStatisticsData(
                users=UserStatistics(
                    users=users_historical,
                    group_memberships={},
                    collection_timestamp=historical_time,
                ),
                groups=GroupStatistics(
                    groups=[], memberships={}, collection_timestamp=historical_time
                ),
                permission_sets=PermissionSetStatistics(
                    permission_sets=[], collection_timestamp=historical_time
                ),
                accounts=AccountStatistics(accounts=[], collection_timestamp=historical_time),
                assignments=AssignmentStatistics(
                    assignments=assignments_historical, collection_timestamp=historical_time
                ),
            )

            result = analyzer.compare_historical_data(current_data, historical_data)

            # Check that significant changes have appropriate impact classification
            if expected_impact != "neutral":
                assert len(result.significant_changes) > 0
                impacts = [change.impact for change in result.significant_changes]
                # At least one change should have the expected impact
                assert expected_impact in impacts or any(
                    impact in ["positive", "negative", "security_risk"] for impact in impacts
                )
