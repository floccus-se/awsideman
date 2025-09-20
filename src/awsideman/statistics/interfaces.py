"""Core interfaces for the statistics module."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol


# Exception classes for statistics operations
class StatisticsError(Exception):
    """Base exception for statistics operations."""

    pass


class DataCollectionError(StatisticsError):
    """Error during data collection from AWS APIs."""

    pass


class AnalysisError(StatisticsError):
    """Error during statistical analysis."""

    pass


class ExportError(StatisticsError):
    """Error during report export."""

    pass


class HistoricalDataError(StatisticsError):
    """Error accessing historical backup data."""

    pass


if TYPE_CHECKING:
    from .models import (
        AccountMetrics,
        AccountStatistics,
        AssignmentPatterns,
        AssignmentStatistics,
        GovernanceAnalysis,
        GovernanceView,
        GroupStatistics,
        PermissionAnalysis,
        PermissionSetMetrics,
        PermissionSetStatistics,
        StatisticsReport,
        TrendAnalysis,
        UserAnalysis,
        UserGroupMetrics,
        UserStatistics,
    )


class StatisticsCollectorInterface(Protocol):
    """Interface for statistics data collection."""

    async def collect_user_statistics(self) -> "UserStatistics":
        """Collect user-related statistics from Identity Center."""
        ...

    async def collect_group_statistics(self) -> "GroupStatistics":
        """Collect group-related statistics from Identity Center."""
        ...

    async def collect_permission_set_statistics(self) -> "PermissionSetStatistics":
        """Collect permission set statistics from Identity Center."""
        ...

    async def collect_account_statistics(self) -> "AccountStatistics":
        """Collect account statistics from Organizations and Identity Center."""
        ...

    async def collect_assignment_statistics(self) -> "AssignmentStatistics":
        """Collect assignment statistics from Identity Center."""
        ...


class StatisticsAnalyzerInterface(Protocol):
    """Interface for statistical analysis."""

    def analyze_user_patterns(self, data: "UserStatistics") -> "UserAnalysis":
        """Analyze user patterns and identify insights."""
        ...

    def analyze_permission_usage(self, data: "PermissionSetStatistics") -> "PermissionAnalysis":
        """Analyze permission set usage patterns."""
        ...

    def analyze_governance_gaps(self, data: Dict[str, Any]) -> "GovernanceAnalysis":
        """Analyze governance gaps and compliance issues."""
        ...

    def compare_historical_data(self, current: Any, historical: Any) -> "TrendAnalysis":
        """Compare current data with historical snapshots."""
        ...


class StatisticsExporterInterface(Protocol):
    """Interface for statistics export."""

    def export_json(self, statistics: "StatisticsReport") -> str:
        """Export statistics as JSON format."""
        ...

    def export_csv(self, statistics: "StatisticsReport") -> str:
        """Export statistics as CSV format."""
        ...

    def export_text(self, statistics: "StatisticsReport") -> str:
        """Export statistics as formatted text."""
        ...


class StatisticsManagerInterface(ABC):
    """Abstract base class for statistics management."""

    @abstractmethod
    async def generate_statistics(
        self,
        categories: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        include_historical: bool = False,
    ) -> "StatisticsReport":
        """Generate comprehensive statistics report."""

    @abstractmethod
    async def generate_user_group_statistics(self) -> "UserGroupMetrics":
        """Generate user and group statistics."""

    @abstractmethod
    async def generate_permission_set_statistics(self) -> "PermissionSetMetrics":
        """Generate permission set statistics."""

    @abstractmethod
    async def generate_account_statistics(self) -> "AccountMetrics":
        """Generate account statistics."""

    @abstractmethod
    async def generate_assignment_patterns(self) -> "AssignmentPatterns":
        """Generate assignment pattern analysis."""

    @abstractmethod
    async def generate_governance_view(self) -> "GovernanceView":
        """Generate governance-oriented view."""
