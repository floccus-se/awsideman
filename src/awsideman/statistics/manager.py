"""Main statistics manager for orchestrating data collection, analysis, and export."""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..aws_clients.manager import AWSClientManager
from .interfaces import StatisticsManagerInterface

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .analyzer import StatisticsAnalyzer
    from .collector import StatisticsCollector
    from .exporter import StatisticsExporter
    from .models import (
        AccountData,
        AccountMetrics,
        AssignmentPatterns,
        GovernanceView,
        PermissionSetMetrics,
        RawStatisticsData,
        StatisticsReport,
        UserGroupMetrics,
    )


class StatisticsManager(StatisticsManagerInterface):
    """Main manager for statistics operations."""

    def __init__(self, client_manager: AWSClientManager, instance_arn: str):
        """Initialize the statistics manager.

        Args:
            client_manager: AWS client manager for API access
            instance_arn: Identity Center instance ARN
        """
        self.client_manager = client_manager
        self.instance_arn = instance_arn
        # Components will be initialized when needed
        self._collector: Optional["StatisticsCollector"] = None
        self._analyzer: Optional["StatisticsAnalyzer"] = None
        self._exporter: Optional["StatisticsExporter"] = None

    @property
    def collector(self) -> "StatisticsCollector":
        """Lazy initialization of statistics collector."""
        if self._collector is None:
            from .collector import StatisticsCollector

            self._collector = StatisticsCollector(self.client_manager, self.instance_arn)
        return self._collector

    @property
    def analyzer(self) -> "StatisticsAnalyzer":
        """Lazy initialization of statistics analyzer."""
        if self._analyzer is None:
            from .analyzer import StatisticsAnalyzer

            self._analyzer = StatisticsAnalyzer()
        return self._analyzer

    @property
    def exporter(self) -> "StatisticsExporter":
        """Lazy initialization of statistics exporter."""
        if self._exporter is None:
            from .exporter import StatisticsExporter

            self._exporter = StatisticsExporter()
        return self._exporter

    async def generate_statistics(
        self,
        categories: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        include_historical: bool = False,
        backup_path: Optional[str] = None,
    ) -> "StatisticsReport":
        """Generate comprehensive statistics report.

        Args:
            categories: List of categories to include (users, groups, permission-sets, etc.)
            filters: Filters to apply to the data
            include_historical: Whether to include historical comparison
            backup_path: Specific backup path for historical comparison

        Returns:
            Complete statistics report
        """
        from datetime import datetime

        from .models import ReportMetadata, StatisticsReport

        start_time = datetime.now()

        # Default categories if none specified
        if categories is None:
            categories = [
                "users",
                "groups",
                "permission-sets",
                "accounts",
                "assignments",
                "governance",
            ]

        # Expand "all" category to individual categories
        if "all" in categories:
            categories = [
                "users",
                "groups",
                "permission-sets",
                "accounts",
                "assignments",
                "governance",
            ]

        # Default filters if none specified
        if filters is None:
            filters = {}

        logger.info("Generating statistics report")

        # Collect data
        raw_data = await self._collect_data_parallel()

        # Apply filters to raw data
        filtered_data = self._apply_filters(raw_data, filters)

        # Perform analysis - create default empty metrics if categories not requested
        from .models import (
            AccessMatrix,
            AccountMetrics,
            AssignmentPatterns,
            EmptyMappings,
            GovernanceView,
            PermissionSetMetrics,
            PrivilegedAccessReport,
            UserGroupMetrics,
        )

        if "users" in categories or "groups" in categories:
            user_group_metrics = self.analyzer.calculate_user_group_metrics(
                filtered_data.users, filtered_data.groups, filtered_data.assignments
            )
        else:
            user_group_metrics = UserGroupMetrics(
                total_users=0,
                total_groups=0,
                users_per_group={},
                groups_per_user={},
                groups_per_user_by_name={},
                largest_groups=[],
                orphaned_users=[],
                disabled_users=[],
                orphaned_groups=[],
            )

        if "permission-sets" in categories:
            permission_set_metrics = self.analyzer.calculate_permission_set_metrics(
                filtered_data.permission_sets.permission_sets, filtered_data.assignments.assignments
            )
        else:
            permission_set_metrics = PermissionSetMetrics(
                total_permission_sets=0,
                assignments_per_permission_set={},
                most_assigned_permission_sets=[],
                unused_permission_sets=[],
                average_assignments_per_permission_set=0.0,
                privileged_permission_sets=[],
            )

        if "accounts" in categories:
            account_metrics = self.analyzer.calculate_account_metrics(
                filtered_data.accounts.accounts,
                filtered_data.assignments.assignments,
                filtered_data.users.users,
            )
        else:
            account_metrics = AccountMetrics(
                total_accounts=0,
                assignments_per_account={},
                users_per_account={},
                groups_per_account={},
                accounts_with_no_assignments=[],
                cross_account_users=[],
                cross_account_groups=[],
            )

        if "assignments" in categories:
            assignment_patterns = self.analyzer.calculate_assignment_patterns(
                filtered_data.assignments.assignments
            )
        else:
            assignment_patterns = AssignmentPatterns(
                average_assignments_per_user=0.0,
                users_with_most_assignments=[],
                groups_with_most_assignments=[],
                assignment_growth_trend=None,
            )

        if "governance" in categories:
            governance_view = self.analyzer.calculate_governance_view(filtered_data)
        else:
            # Create empty governance view
            governance_view = GovernanceView(
                access_matrix=AccessMatrix(
                    user_to_accounts={},
                    user_to_permission_sets={},
                    group_to_accounts={},
                    group_to_permission_sets={},
                    account_to_users={},
                    account_to_groups={},
                ),
                privileged_access_report=PrivilegedAccessReport(
                    admin_permission_sets=[],
                    accounts_with_admin_access={},
                    users_with_admin_access=[],
                    high_privilege_patterns=[],
                ),
                empty_mappings=EmptyMappings(
                    groups_with_no_members=[],
                    permission_sets_with_no_assignments=[],
                    accounts_with_no_assignments=[],
                ),
                compliance_gaps=[],
            )

        # Create report
        from datetime import datetime

        generation_time = datetime.now()
        duration = (generation_time - start_time).total_seconds()

        historical_comparison = None
        if include_historical and backup_path:
            historical_data = self.collector.get_historical_data(backup_path)
            if historical_data is not None:
                historical_comparison = self.analyzer.compare_historical_data(
                    filtered_data, historical_data
                )

        report = StatisticsReport(
            metadata=ReportMetadata(
                generation_timestamp=start_time,
                instance_arn=self.instance_arn,
                region=self.client_manager.region or "us-east-1",
                profile=None,  # Will be set by CLI if needed
                categories_included=categories,
                filters_applied=filters,
                data_collection_duration=duration,
                analysis_duration=0.0,  # Will be calculated separately if needed
            ),
            user_group_metrics=user_group_metrics,
            permission_set_metrics=permission_set_metrics,
            account_metrics=account_metrics,
            assignment_patterns=assignment_patterns,
            governance_view=governance_view,
            historical_comparison=historical_comparison,
        )

        logger.info("Statistics report generated")
        return report

    def _apply_filters(
        self, raw_data: "RawStatisticsData", filters: Dict[str, Any]
    ) -> "RawStatisticsData":
        """Apply filters to raw statistics data.

        Args:
            raw_data: Raw statistics data to filter
            filters: Dictionary of filters to apply

        Returns:
            Filtered statistics data
        """
        if not filters:
            return raw_data

        # Extract tag filters
        tag_filters = {}
        for key, value in filters.items():
            if key.startswith("tag:"):
                tag_key = key[4:]  # Remove "tag:" prefix
                tag_filters[tag_key] = value
            elif key == "tag":
                # Handle format like tag=env:prod
                if ":" in value:
                    tag_key, tag_value = value.split(":", 1)
                    tag_filters[tag_key] = tag_value
                else:
                    logger.warning(
                        f"Invalid tag filter format: {value}. Expected 'key:value' or use 'tag:key=value'"
                    )

        # Apply account tag filtering
        if tag_filters:
            # Filter accounts based on tags
            filtered_accounts = []
            for account in raw_data.accounts.accounts:
                if self._account_matches_tag_filters(account, tag_filters):
                    filtered_accounts.append(account)

            # Create filtered account statistics
            from .models import AccountStatistics

            filtered_account_stats = AccountStatistics(
                accounts=filtered_accounts,
                collection_timestamp=raw_data.accounts.collection_timestamp,
            )

            # Get account IDs for filtering assignments
            filtered_account_ids = {account.account_id for account in filtered_accounts}

            # Filter assignments to only include those for filtered accounts
            filtered_assignments = []
            for assignment in raw_data.assignments.assignments:
                if assignment.account_id in filtered_account_ids:
                    filtered_assignments.append(assignment)

            # Create filtered assignment statistics
            from .models import AssignmentStatistics

            filtered_assignment_stats = AssignmentStatistics(
                assignments=filtered_assignments,
                collection_timestamp=raw_data.assignments.collection_timestamp,
            )

            # Create filtered raw data with updated accounts and assignments
            from .models import RawStatisticsData

            return RawStatisticsData(
                users=raw_data.users,
                groups=raw_data.groups,
                permission_sets=raw_data.permission_sets,
                accounts=filtered_account_stats,
                assignments=filtered_assignment_stats,
            )

        # TODO: Add support for other filter types (user, group, permission-set, assignment-type)
        return raw_data

    def _account_matches_tag_filters(
        self, account: "AccountData", tag_filters: Dict[str, str]
    ) -> bool:
        """Check if an account matches all specified tag filters.

        Args:
            account: Account to check
            tag_filters: Dictionary of tag key-value pairs to match

        Returns:
            True if account matches all tag filters, False otherwise
        """
        for tag_key, tag_value in tag_filters.items():
            if not account.matches_tag_filter(tag_key, tag_value):
                return False
        return True

    async def _collect_data_parallel(self) -> "RawStatisticsData":
        """Collect all data using parallel processing.

        Returns:
            Raw statistics data
        """
        import asyncio

        from .models import (
            AccountStatistics,
            AssignmentStatistics,
            GroupStatistics,
            PermissionSetStatistics,
            RawStatisticsData,
            UserStatistics,
        )

        # Create collection tasks
        tasks = [
            self.collector.collect_user_statistics(),
            self.collector.collect_group_statistics(),
            self.collector.collect_permission_set_statistics(),
            self.collector.collect_account_statistics(),
            self.collector.collect_assignment_statistics(),
        ]

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        users_data: Optional[UserStatistics] = results[0] if not isinstance(results[0], Exception) else None  # type: ignore
        groups_data: Optional[GroupStatistics] = results[1] if not isinstance(results[1], Exception) else None  # type: ignore
        permission_sets_data: Optional[PermissionSetStatistics] = results[2] if not isinstance(results[2], Exception) else None  # type: ignore
        accounts_data: Optional[AccountStatistics] = results[3] if not isinstance(results[3], Exception) else None  # type: ignore
        assignments_data: Optional[AssignmentStatistics] = results[4] if not isinstance(results[4], Exception) else None  # type: ignore

        # Create empty data for failed collections
        from datetime import datetime

        if users_data is None:
            users_data = UserStatistics(
                users=[], group_memberships={}, collection_timestamp=datetime.now()
            )

        if groups_data is None:
            groups_data = GroupStatistics(
                groups=[], memberships={}, collection_timestamp=datetime.now()
            )

        if permission_sets_data is None:
            permission_sets_data = PermissionSetStatistics(
                permission_sets=[], collection_timestamp=datetime.now()
            )

        if accounts_data is None:
            accounts_data = AccountStatistics(accounts=[], collection_timestamp=datetime.now())

        if assignments_data is None:
            assignments_data = AssignmentStatistics(
                assignments=[], collection_timestamp=datetime.now()
            )

        return RawStatisticsData(
            users=users_data,
            groups=groups_data,
            permission_sets=permission_sets_data,
            accounts=accounts_data,
            assignments=assignments_data,
        )

    async def generate_user_group_statistics(self) -> "UserGroupMetrics":
        """Generate user and group statistics.

        Returns:
            User and group metrics
        """
        data = await self._collect_data_parallel()
        return self.analyzer.calculate_user_group_metrics(data.users, data.groups, data.assignments)

    async def generate_permission_set_statistics(self) -> "PermissionSetMetrics":
        """Generate permission set statistics.

        Returns:
            Permission set metrics
        """
        data = await self._collect_data_parallel()
        return self.analyzer.calculate_permission_set_metrics(
            data.permission_sets.permission_sets, data.assignments.assignments
        )

    async def generate_account_statistics(self) -> "AccountMetrics":
        """Generate account statistics.

        Returns:
            Account metrics
        """
        data = await self._collect_data_parallel()
        return self.analyzer.calculate_account_metrics(
            data.accounts.accounts, data.assignments.assignments, data.users.users
        )

    async def generate_assignment_patterns(self) -> "AssignmentPatterns":
        """Generate assignment pattern analysis.

        Returns:
            Assignment patterns analysis
        """
        data = await self._collect_data_parallel()
        return self.analyzer.calculate_assignment_patterns(data.assignments.assignments)

    async def generate_governance_view(self) -> "GovernanceView":
        """Generate governance-oriented view.

        Returns:
            Governance view analysis
        """
        data = await self._collect_data_parallel()
        return self.analyzer.calculate_governance_view(data)
