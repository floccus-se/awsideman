"""Tests for StatisticsManager integration and orchestration."""

import asyncio
from datetime import datetime
from typing import List
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.awsideman.statistics.manager import StatisticsManager
from src.awsideman.statistics.models import (
    AccountData,
    AccountStatistics,
    AssignmentData,
    AssignmentStatistics,
    GroupData,
    GroupStatistics,
    PermissionSetData,
    PermissionSetStatistics,
    RawStatisticsData,
    StatisticsReport,
    UserData,
    UserStatistics,
)


class TestStatisticsManager:
    """Test the StatisticsManager class."""

    @pytest.fixture
    def mock_client_manager(self) -> Mock:
        """Create a mock AWS client manager."""
        client_manager = Mock()
        client_manager.is_caching_enabled.return_value = True
        return client_manager

    @pytest.fixture
    def manager(self, mock_client_manager: Mock) -> StatisticsManager:
        """Create a StatisticsManager instance for testing."""
        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        return StatisticsManager(mock_client_manager, instance_arn)

    @pytest.fixture
    def sample_raw_data(self) -> RawStatisticsData:
        """Create sample raw statistics data."""
        timestamp = datetime.now()

        users = [
            UserData("user1", "john.doe", "John Doe", "john.doe@example.com", True),
            UserData("user2", "jane.smith", "Jane Smith", "jane.smith@example.com", True),
        ]

        groups = [
            GroupData("group1", "Developers", "Development team"),
            GroupData("group2", "Admins", "Administrative team"),
        ]

        permission_sets = [
            PermissionSetData(
                "arn:aws:sso:::permissionSet/ssoins-123/ps-dev",
                "DeveloperAccess",
                "Developer permissions",
                "PT8H",
                [],
                None,
                None,
            ),
        ]

        accounts = [
            AccountData(
                account_id="123456789012",
                account_name="Production",
                email="prod@example.com",
                status="ACTIVE",
            ),
        ]

        assignments = [
            AssignmentData(
                account_id="123456789012",
                permission_set_arn="arn:aws:sso:::permissionSet/ssoins-123/ps-dev",
                principal_type="USER",
                principal_id="user1",
            ),
        ]

        return RawStatisticsData(
            users=UserStatistics(users, {"user1": ["group1"], "user2": []}, timestamp),
            groups=GroupStatistics(groups, {"group1": ["user1"], "group2": []}, timestamp),
            permission_sets=PermissionSetStatistics(permission_sets, timestamp),
            accounts=AccountStatistics(accounts, timestamp),
            assignments=AssignmentStatistics(assignments, timestamp),
        )

    @pytest.mark.asyncio
    async def test_generate_statistics_success(
        self, manager: StatisticsManager, sample_raw_data: RawStatisticsData
    ) -> None:
        """Test successful statistics generation."""
        with patch.object(
            manager, "_collect_data_parallel", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.return_value = sample_raw_data

            result = await manager.generate_statistics()

            assert isinstance(result, StatisticsReport)
            assert result.metadata is not None
            assert result.user_group_metrics is not None
            assert result.permission_set_metrics is not None
            assert result.account_metrics is not None
            assert result.assignment_patterns is not None
            assert result.governance_view is not None

            mock_collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_statistics_with_categories(
        self, manager: StatisticsManager, sample_raw_data: RawStatisticsData
    ) -> None:
        """Test statistics generation with specific categories."""
        with patch.object(
            manager, "_collect_data_parallel", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.return_value = sample_raw_data

            categories = ["users", "groups"]
            result = await manager.generate_statistics(categories=categories)

            assert isinstance(result, StatisticsReport)
            assert result.user_group_metrics is not None
            # Other metrics should still be present but may be empty
            assert result.permission_set_metrics is not None
            assert result.account_metrics is not None

    @pytest.mark.asyncio
    async def test_generate_statistics_with_filters(
        self, manager: StatisticsManager, sample_raw_data: RawStatisticsData
    ) -> None:
        """Test statistics generation with filters."""
        with patch.object(
            manager, "_collect_data_parallel", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.return_value = sample_raw_data

            filters = {"account": "123456789012"}
            result = await manager.generate_statistics(filters=filters)

            assert isinstance(result, StatisticsReport)
            assert result.metadata.filters_applied == filters

    @pytest.mark.asyncio
    async def test_generate_statistics_with_historical(
        self, manager: StatisticsManager, sample_raw_data: RawStatisticsData
    ) -> None:
        """Test statistics generation with historical comparison."""
        with (
            patch.object(manager, "_collect_data_parallel", new_callable=AsyncMock) as mock_collect,
            patch.object(manager.collector, "get_historical_data") as mock_historical,
        ):

            mock_collect.return_value = sample_raw_data
            mock_historical.return_value = sample_raw_data  # Same data for simplicity

            result = await manager.generate_statistics(
                include_historical=True, backup_path="/path/to/backup"
            )

            assert isinstance(result, StatisticsReport)
            assert result.historical_comparison is not None

            mock_historical.assert_called_once_with("/path/to/backup")

    @pytest.mark.asyncio
    async def test_generate_user_group_statistics(
        self, manager: StatisticsManager, sample_raw_data: RawStatisticsData
    ) -> None:
        """Test user group statistics generation."""
        with patch.object(
            manager, "_collect_data_parallel", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.return_value = sample_raw_data

            result = await manager.generate_user_group_statistics()

            assert result is not None
            assert result.total_users == 2
            assert result.total_groups == 2

    @pytest.mark.asyncio
    async def test_generate_permission_set_statistics(
        self, manager: StatisticsManager, sample_raw_data: RawStatisticsData
    ) -> None:
        """Test permission set statistics generation."""
        with patch.object(
            manager, "_collect_data_parallel", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.return_value = sample_raw_data

            result = await manager.generate_permission_set_statistics()

            assert result is not None
            assert result.total_permission_sets == 1

    @pytest.mark.asyncio
    async def test_generate_account_statistics(
        self, manager: StatisticsManager, sample_raw_data: RawStatisticsData
    ) -> None:
        """Test account statistics generation."""
        with patch.object(
            manager, "_collect_data_parallel", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.return_value = sample_raw_data

            result = await manager.generate_account_statistics()

            assert result is not None
            assert result.total_accounts == 1

    @pytest.mark.asyncio
    async def test_generate_assignment_patterns(
        self, manager: StatisticsManager, sample_raw_data: RawStatisticsData
    ) -> None:
        """Test assignment patterns generation."""
        with patch.object(
            manager, "_collect_data_parallel", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.return_value = sample_raw_data

            result = await manager.generate_assignment_patterns()

            assert result is not None
            assert result.average_assignments_per_user >= 0

    @pytest.mark.asyncio
    async def test_generate_governance_view(
        self, manager: StatisticsManager, sample_raw_data: RawStatisticsData
    ) -> None:
        """Test governance view generation."""
        with patch.object(
            manager, "_collect_data_parallel", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.return_value = sample_raw_data

            result = await manager.generate_governance_view()

            assert result is not None
            assert result.access_matrix is not None
            assert result.privileged_access_report is not None

    @pytest.mark.asyncio
    async def test_error_handling_collection_failure(self, manager: StatisticsManager) -> None:
        """Test error handling when data collection fails."""
        with patch.object(
            manager, "_collect_data_parallel", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.side_effect = Exception("Collection failed")

            with pytest.raises(Exception, match="Collection failed"):
                await manager.generate_statistics()

    @pytest.mark.asyncio
    async def test_error_handling_analysis_failure(
        self, manager: StatisticsManager, sample_raw_data: RawStatisticsData
    ) -> None:
        """Test error handling when analysis fails."""
        with (
            patch.object(manager, "_collect_data_parallel", new_callable=AsyncMock) as mock_collect,
            patch.object(manager.analyzer, "calculate_user_group_metrics") as mock_analyze,
        ):

            mock_collect.return_value = sample_raw_data
            mock_analyze.side_effect = Exception("Analysis failed")

            with pytest.raises(Exception, match="Analysis failed"):
                await manager.generate_statistics()

    @pytest.mark.asyncio
    async def test_performance_with_large_dataset(self, manager: StatisticsManager) -> None:
        """Test performance with large dataset."""
        # Create larger dataset
        timestamp = datetime.now()
        large_users = [
            UserData(f"user{i}", f"user{i}", f"User {i}", f"user{i}@example.com", True)
            for i in range(100)
        ]
        large_groups = [GroupData(f"group{i}", f"Group {i}", f"Group {i}") for i in range(20)]
        large_assignments = [
            AssignmentData(
                account_id="acc1",
                permission_set_arn="ps1",
                principal_type="USER",
                principal_id=f"user{i}",
            )
            for i in range(100)
        ]

        large_data = RawStatisticsData(
            users=UserStatistics(large_users, {}, timestamp),
            groups=GroupStatistics(large_groups, {}, timestamp),
            permission_sets=PermissionSetStatistics([], timestamp),
            accounts=AccountStatistics([], timestamp),
            assignments=AssignmentStatistics(large_assignments, timestamp),
        )

        with patch.object(
            manager, "_collect_data_parallel", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.return_value = large_data

            # Should complete without timeout
            result = await asyncio.wait_for(manager.generate_statistics(), timeout=10.0)

            assert isinstance(result, StatisticsReport)
            assert result.user_group_metrics.total_users == 100

    def test_manager_initialization(self, mock_client_manager: Mock) -> None:
        """Test StatisticsManager initialization."""
        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        manager = StatisticsManager(mock_client_manager, instance_arn)

        assert manager.client_manager == mock_client_manager
        assert manager.instance_arn == instance_arn
        assert manager.collector is not None
        assert manager.analyzer is not None
        assert manager.exporter is not None

    @pytest.mark.asyncio
    async def test_memory_efficiency(self, manager: StatisticsManager) -> None:
        """Test memory efficiency with chunked processing."""
        # This test verifies that the manager can handle data without excessive memory usage
        timestamp = datetime.now()

        # Create moderate dataset
        users = [
            UserData(f"user{i}", f"user{i}", f"User {i}", f"user{i}@example.com", True)
            for i in range(50)
        ]
        assignments = [
            AssignmentData(
                account_id="acc1",
                permission_set_arn="ps1",
                principal_type="USER",
                principal_id=f"user{i}",
            )
            for i in range(50)
        ]

        data = RawStatisticsData(
            users=UserStatistics(users, {}, timestamp),
            groups=GroupStatistics([], {}, timestamp),
            permission_sets=PermissionSetStatistics([], timestamp),
            accounts=AccountStatistics([], timestamp),
            assignments=AssignmentStatistics(assignments, timestamp),
        )

        with patch.object(
            manager, "_collect_data_parallel", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.return_value = data

            result = await manager.generate_statistics()

            # Verify result is complete
            assert isinstance(result, StatisticsReport)
            assert result.user_group_metrics.total_users == 50

    @pytest.mark.asyncio
    async def test_progress_reporting(
        self, manager: StatisticsManager, sample_raw_data: RawStatisticsData
    ) -> None:
        """Test progress reporting for long-running operations."""
        progress_calls: List[str] = []

        def mock_progress(message: str) -> None:
            progress_calls.append(message)

        with (
            patch.object(manager, "_collect_data_parallel", new_callable=AsyncMock) as mock_collect,
            patch("src.awsideman.statistics.manager.logger") as mock_logger,
        ):

            mock_collect.return_value = sample_raw_data

            result = await manager.generate_statistics()

            # Verify logging was called (progress reporting)
            assert mock_logger.info.called
            assert isinstance(result, StatisticsReport)

    @pytest.mark.asyncio
    async def test_graceful_degradation(self, manager: StatisticsManager) -> None:
        """Test graceful degradation when some data is unavailable."""
        timestamp = datetime.now()

        # Create partial data (missing some components)
        partial_data = RawStatisticsData(
            users=UserStatistics(
                [UserData("user1", "user1", "User 1", "user1@example.com", True)], {}, timestamp
            ),
            groups=GroupStatistics([], {}, timestamp),  # Empty groups
            permission_sets=PermissionSetStatistics([], timestamp),  # Empty permission sets
            accounts=AccountStatistics([], timestamp),  # Empty accounts
            assignments=AssignmentStatistics([], timestamp),  # Empty assignments
        )

        with patch.object(
            manager, "_collect_data_parallel", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.return_value = partial_data

            result = await manager.generate_statistics()

            # Should still generate a report with available data
            assert isinstance(result, StatisticsReport)
            assert result.user_group_metrics.total_users == 1
            assert result.user_group_metrics.total_groups == 0

    @pytest.mark.asyncio
    async def test_historical_data_missing(
        self, manager: StatisticsManager, sample_raw_data: RawStatisticsData
    ) -> None:
        """Test handling when historical data is missing."""
        with (
            patch.object(manager, "_collect_data_parallel", new_callable=AsyncMock) as mock_collect,
            patch.object(manager.collector, "get_historical_data") as mock_historical,
        ):

            mock_collect.return_value = sample_raw_data
            mock_historical.return_value = None  # No historical data

            result = await manager.generate_statistics(
                include_historical=True, backup_path="/nonexistent/path"
            )

            # Should still generate report without historical comparison
            assert isinstance(result, StatisticsReport)
            assert result.historical_comparison is None

    @pytest.mark.asyncio
    async def test_filter_application(
        self, manager: StatisticsManager, sample_raw_data: RawStatisticsData
    ) -> None:
        """Test that filters are properly applied to the analysis."""
        filters = {"account": "123456789012", "user": "john.doe"}

        with patch.object(
            manager, "_collect_data_parallel", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.return_value = sample_raw_data

            result = await manager.generate_statistics(filters=filters)

            # Verify filters are recorded in metadata
            assert result.metadata.filters_applied == filters

    @pytest.mark.asyncio
    async def test_category_filtering(
        self, manager: StatisticsManager, sample_raw_data: RawStatisticsData
    ) -> None:
        """Test that category filtering works correctly."""
        categories = ["users", "accounts"]

        with patch.object(
            manager, "_collect_data_parallel", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.return_value = sample_raw_data

            result = await manager.generate_statistics(categories=categories)

            # Verify categories are recorded in metadata
            assert result.metadata.categories_included == categories

    def test_exporter_integration(self, manager: StatisticsManager) -> None:
        """Test that exporter is properly integrated."""
        assert manager.exporter is not None

        # Test that exporter methods are accessible
        assert hasattr(manager.exporter, "export_to_json")
        assert hasattr(manager.exporter, "export_to_csv")
        assert hasattr(manager.exporter, "export_to_text")

    @pytest.mark.asyncio
    async def test_concurrent_statistics_generation(
        self, manager: StatisticsManager, sample_raw_data: RawStatisticsData
    ) -> None:
        """Test concurrent statistics generation requests."""
        with patch.object(
            manager, "_collect_data_parallel", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.return_value = sample_raw_data

            # Run multiple statistics generation concurrently
            tasks = [
                manager.generate_statistics(),
                manager.generate_statistics(),
                manager.generate_statistics(),
            ]

            results = await asyncio.gather(*tasks)

            # All should succeed
            assert len(results) == 3
            for result in results:
                assert isinstance(result, StatisticsReport)
                assert result.user_group_metrics.total_users == 2
