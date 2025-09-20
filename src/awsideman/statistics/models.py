"""Data models for statistics module."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


class ValidationError(Exception):
    """Exception raised when data validation fails."""

    pass


# Raw data models for collection
@dataclass
class UserData:
    """Raw user data from Identity Center."""

    user_id: str
    username: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    active: bool = True


@dataclass
class GroupData:
    """Raw group data from Identity Center."""

    group_id: str
    display_name: str
    description: Optional[str] = None


@dataclass
class PermissionSetData:
    """Raw permission set data from Identity Center."""

    permission_set_arn: str
    name: str
    description: Optional[str] = None
    session_duration: Optional[str] = None
    managed_policies: List[str] = field(default_factory=list)
    customer_managed_policies: List[Dict[str, str]] = field(default_factory=list)
    inline_policy: Optional[str] = None


@dataclass
class AssignmentData:
    """Raw assignment data from Identity Center."""

    account_id: str
    permission_set_arn: str
    principal_type: str  # USER or GROUP
    principal_id: str


@dataclass
class AccountData:
    """Raw account data from Organizations."""

    account_id: str
    account_name: str
    email: str
    status: str
    tags: Dict[str, str] = field(default_factory=dict)

    def has_tag(self, key: str, value: Optional[str] = None) -> bool:
        """Check if account has a specific tag, optionally with a specific value.

        Args:
            key: Tag key to check
            value: Optional tag value to match

        Returns:
            True if account has the tag (and value if specified)
        """
        if key not in self.tags:
            return False
        if value is None:
            return True
        return self.tags[key] == value

    def matches_tag_filter(self, tag_key: str, tag_value: str) -> bool:
        """Check if account matches a specific tag filter.

        Args:
            tag_key: The tag key to match
            tag_value: The tag value to match

        Returns:
            True if account has the specified tag key-value pair
        """
        return self.tags.get(tag_key) == tag_value


# Collection result models
@dataclass
class UserStatistics:
    """User statistics collection result."""

    users: List[UserData]
    group_memberships: Dict[str, List[str]]  # user_id -> [group_ids]
    collection_timestamp: datetime


@dataclass
class GroupStatistics:
    """Group statistics collection result."""

    groups: List[GroupData]
    memberships: Dict[str, List[str]]  # group_id -> [user_ids]
    collection_timestamp: datetime


@dataclass
class PermissionSetStatistics:
    """Permission set statistics collection result."""

    permission_sets: List[PermissionSetData]
    collection_timestamp: datetime


@dataclass
class AccountStatistics:
    """Account statistics collection result."""

    accounts: List[AccountData]
    collection_timestamp: datetime


@dataclass
class AssignmentStatistics:
    """Assignment statistics collection result."""

    assignments: List[AssignmentData]
    collection_timestamp: datetime


# Analysis result models
@dataclass
class UserGroupMetrics:
    """Metrics for users and groups."""

    total_users: int
    total_groups: int
    users_per_group: Dict[str, int]  # group_id -> user_count
    groups_per_user: Dict[str, int]  # user_id -> group_count
    groups_per_user_by_name: Dict[str, int]  # username -> group_count (for display)
    largest_groups: List[Tuple[str, int]]  # (group_name, user_count)
    orphaned_users: List[str]  # active users with no group membership or assignments
    disabled_users: List[str]  # disabled users
    orphaned_groups: List[str]  # groups with no members or assignments


@dataclass
class PermissionSetMetrics:
    """Metrics for permission sets."""

    total_permission_sets: int
    assignments_per_permission_set: Dict[str, int]
    most_assigned_permission_sets: List[Tuple[str, int]]
    unused_permission_sets: List[str]
    average_assignments_per_permission_set: float
    privileged_permission_sets: List[str]


@dataclass
class AccountMetrics:
    """Metrics for AWS accounts."""

    total_accounts: int
    assignments_per_account: Dict[str, int]
    users_per_account: Dict[str, int]
    groups_per_account: Dict[str, int]
    accounts_with_no_assignments: List[str]
    cross_account_users: List[Tuple[str, int]]  # (user_id, account_count)
    cross_account_groups: List[Tuple[str, int]]  # (group_id, account_count)


@dataclass
class GrowthMetric:
    """Growth metric for trend analysis."""

    current_count: int
    previous_count: int
    growth_rate: float
    absolute_change: int


@dataclass
class SignificantChange:
    """Significant change detected in trend analysis."""

    category: str
    description: str
    impact: str
    change_magnitude: float


@dataclass
class TrendData:
    """Trend data for assignment patterns."""

    time_periods: List[str]
    values: List[int]
    trend_direction: str  # "increasing", "decreasing", "stable"


@dataclass
class AssignmentPatterns:
    """Assignment pattern analysis."""

    average_assignments_per_user: float
    users_with_most_assignments: List[Tuple[str, int]]
    groups_with_most_assignments: List[Tuple[str, int]]
    assignment_growth_trend: Optional[TrendData]


@dataclass
class AccessMatrix:
    """Who has access to what matrix."""

    user_to_accounts: Dict[str, List[str]]
    user_to_permission_sets: Dict[str, List[str]]
    group_to_accounts: Dict[str, List[str]]
    group_to_permission_sets: Dict[str, List[str]]
    account_to_users: Dict[str, List[str]]
    account_to_groups: Dict[str, List[str]]


@dataclass
class PrivilegePattern:
    """Privilege pattern detection."""

    pattern_type: str
    description: str
    affected_entities: List[str]
    risk_level: str


@dataclass
class PrivilegedAccessReport:
    """Report on privileged access patterns."""

    admin_permission_sets: List[str]
    accounts_with_admin_access: Dict[str, List[str]]  # account_id -> [user/group names]
    users_with_admin_access: List[str]
    high_privilege_patterns: List[PrivilegePattern]


@dataclass
class EmptyMappings:
    """Empty mappings detection."""

    groups_with_no_members: List[str]
    permission_sets_with_no_assignments: List[str]
    accounts_with_no_assignments: List[str]


@dataclass
class ComplianceGap:
    """Compliance gap identification."""

    gap_type: str
    description: str
    affected_resources: List[str]
    severity: str


@dataclass
class GovernanceView:
    """Governance-oriented analysis."""

    access_matrix: AccessMatrix
    privileged_access_report: PrivilegedAccessReport
    empty_mappings: EmptyMappings
    compliance_gaps: List[ComplianceGap]


@dataclass
class TrendAnalysis:
    """Historical trend analysis."""

    user_growth: GrowthMetric
    group_growth: GrowthMetric
    permission_set_growth: GrowthMetric
    assignment_growth: GrowthMetric
    significant_changes: List[SignificantChange]


@dataclass
class ReportMetadata:
    """Metadata for statistics report."""

    generation_timestamp: datetime
    instance_arn: str
    region: str
    profile: Optional[str]
    categories_included: List[str]
    filters_applied: Dict[str, Any]
    data_collection_duration: float
    analysis_duration: float


@dataclass
class StatisticsReport:
    """Complete statistics report."""

    metadata: ReportMetadata
    user_group_metrics: UserGroupMetrics
    permission_set_metrics: PermissionSetMetrics
    account_metrics: AccountMetrics
    assignment_patterns: AssignmentPatterns
    governance_view: GovernanceView
    historical_comparison: Optional[TrendAnalysis]


# Analysis interface models
@dataclass
class UserAnalysis:
    """User pattern analysis result."""

    metrics: UserGroupMetrics
    insights: List[str]
    recommendations: List[str]


@dataclass
class PermissionAnalysis:
    """Permission usage analysis result."""

    metrics: PermissionSetMetrics
    insights: List[str]
    recommendations: List[str]


@dataclass
class GovernanceAnalysis:
    """Governance analysis result."""

    view: GovernanceView
    insights: List[str]
    recommendations: List[str]


# Raw statistics data container
@dataclass
class RawStatisticsData:
    """Container for all raw collected data."""

    users: UserStatistics
    groups: GroupStatistics
    permission_sets: PermissionSetStatistics
    accounts: AccountStatistics
    assignments: AssignmentStatistics


# Orphaned resources detection
@dataclass
class OrphanedResources:
    """Orphaned resources detection result."""

    orphaned_users: List[str]
    orphaned_groups: List[str]
    unused_permission_sets: List[str]
    unassigned_accounts: List[str]


# Validation methods for data integrity
def validate_user_data(user: UserData) -> None:
    """Validate user data integrity."""
    if not user.user_id or not user.user_id.strip():
        raise ValidationError("User ID cannot be empty")

    if not user.username or not user.username.strip():
        raise ValidationError("Username cannot be empty")

    if user.email and not re.match(r"^[^@]+@[^@]+\.[^@]+$", user.email):
        raise ValidationError(f"Invalid email format: {user.email}")


def validate_group_data(group: GroupData) -> None:
    """Validate group data integrity."""
    if not group.group_id or not group.group_id.strip():
        raise ValidationError("Group ID cannot be empty")

    if not group.display_name or not group.display_name.strip():
        raise ValidationError("Group display name cannot be empty")


def validate_permission_set_data(permission_set: PermissionSetData) -> None:
    """Validate permission set data integrity."""
    if not permission_set.permission_set_arn or not permission_set.permission_set_arn.strip():
        raise ValidationError("Permission set ARN cannot be empty")

    if not permission_set.name or not permission_set.name.strip():
        raise ValidationError("Permission set name cannot be empty")

    # Validate ARN format
    arn_pattern = r"^arn:aws:sso:::permissionSet/[a-zA-Z0-9-]+/ps-[a-zA-Z0-9]+$"
    if not re.match(arn_pattern, permission_set.permission_set_arn):
        raise ValidationError(
            f"Invalid permission set ARN format: {permission_set.permission_set_arn}"
        )


def validate_assignment_data(assignment: AssignmentData) -> None:
    """Validate assignment data integrity."""
    if not assignment.account_id or not assignment.account_id.strip():
        raise ValidationError("Account ID cannot be empty")

    if not assignment.permission_set_arn or not assignment.permission_set_arn.strip():
        raise ValidationError("Permission set ARN cannot be empty")

    if not assignment.principal_id or not assignment.principal_id.strip():
        raise ValidationError("Principal ID cannot be empty")

    if assignment.principal_type not in ["USER", "GROUP"]:
        raise ValidationError(f"Invalid principal type: {assignment.principal_type}")

    # Validate account ID format (12 digits)
    if not re.match(r"^\d{12}$", assignment.account_id):
        raise ValidationError(f"Invalid account ID format: {assignment.account_id}")


def validate_account_data(account: AccountData) -> None:
    """Validate account data integrity."""
    if not account.account_id or not account.account_id.strip():
        raise ValidationError("Account ID cannot be empty")

    if not account.account_name or not account.account_name.strip():
        raise ValidationError("Account name cannot be empty")

    if not account.email or not account.email.strip():
        raise ValidationError("Account email cannot be empty")

    # Validate account ID format (12 digits)
    if not re.match(r"^\d{12}$", account.account_id):
        raise ValidationError(f"Invalid account ID format: {account.account_id}")

    # Validate email format
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", account.email):
        raise ValidationError(f"Invalid email format: {account.email}")


def validate_user_group_metrics(metrics: UserGroupMetrics) -> None:
    """Validate user group metrics data integrity."""
    if metrics.total_users < 0:
        raise ValidationError("Total users cannot be negative")

    if metrics.total_groups < 0:
        raise ValidationError("Total groups cannot be negative")

    # Validate that users_per_group counts are non-negative
    for group_id, count in metrics.users_per_group.items():
        if count < 0:
            raise ValidationError(f"User count for group {group_id} cannot be negative")

    # Validate that groups_per_user counts are non-negative
    for user_id, count in metrics.groups_per_user.items():
        if count < 0:
            raise ValidationError(f"Group count for user {user_id} cannot be negative")


def validate_permission_set_metrics(metrics: PermissionSetMetrics) -> None:
    """Validate permission set metrics data integrity."""
    if metrics.total_permission_sets < 0:
        raise ValidationError("Total permission sets cannot be negative")

    if metrics.average_assignments_per_permission_set < 0:
        raise ValidationError("Average assignments per permission set cannot be negative")

    # Validate that assignment counts are non-negative
    for ps_arn, count in metrics.assignments_per_permission_set.items():
        if count < 0:
            raise ValidationError(
                f"Assignment count for permission set {ps_arn} cannot be negative"
            )


def validate_account_metrics(metrics: AccountMetrics) -> None:
    """Validate account metrics data integrity."""
    if metrics.total_accounts < 0:
        raise ValidationError("Total accounts cannot be negative")

    # Validate that all counts are non-negative
    for account_id, count in metrics.assignments_per_account.items():
        if count < 0:
            raise ValidationError(f"Assignment count for account {account_id} cannot be negative")

    for account_id, count in metrics.users_per_account.items():
        if count < 0:
            raise ValidationError(f"User count for account {account_id} cannot be negative")

    for account_id, count in metrics.groups_per_account.items():
        if count < 0:
            raise ValidationError(f"Group count for account {account_id} cannot be negative")


def validate_assignment_patterns(patterns: AssignmentPatterns) -> None:
    """Validate assignment patterns data integrity."""
    if patterns.average_assignments_per_user < 0:
        raise ValidationError("Average assignments per user cannot be negative")

    # Validate that assignment counts in tuples are non-negative
    for user_id, count in patterns.users_with_most_assignments:
        if count < 0:
            raise ValidationError(f"Assignment count for user {user_id} cannot be negative")

    for group_id, count in patterns.groups_with_most_assignments:
        if count < 0:
            raise ValidationError(f"Assignment count for group {group_id} cannot be negative")


def validate_access_matrix(matrix: AccessMatrix) -> None:
    """Validate access matrix data integrity."""
    # Ensure all dictionary values are lists
    for user_id, accounts in matrix.user_to_accounts.items():
        if not isinstance(accounts, list):
            raise ValidationError(f"Accounts for user {user_id} must be a list")

    for user_id, permission_sets in matrix.user_to_permission_sets.items():
        if not isinstance(permission_sets, list):
            raise ValidationError(f"Permission sets for user {user_id} must be a list")

    for group_id, accounts in matrix.group_to_accounts.items():
        if not isinstance(accounts, list):
            raise ValidationError(f"Accounts for group {group_id} must be a list")

    for group_id, permission_sets in matrix.group_to_permission_sets.items():
        if not isinstance(permission_sets, list):
            raise ValidationError(f"Permission sets for group {group_id} must be a list")

    for account_id, users in matrix.account_to_users.items():
        if not isinstance(users, list):
            raise ValidationError(f"Users for account {account_id} must be a list")

    for account_id, groups in matrix.account_to_groups.items():
        if not isinstance(groups, list):
            raise ValidationError(f"Groups for account {account_id} must be a list")


def validate_privileged_access_report(report: PrivilegedAccessReport) -> None:
    """Validate privileged access report data integrity."""
    # Validate that all lists are actually lists
    if not isinstance(report.admin_permission_sets, list):
        raise ValidationError("Admin permission sets must be a list")

    if not isinstance(report.users_with_admin_access, list):
        raise ValidationError("Users with admin access must be a list")

    if not isinstance(report.high_privilege_patterns, list):
        raise ValidationError("High privilege patterns must be a list")

    # Validate accounts_with_admin_access structure
    for account_id, entities in report.accounts_with_admin_access.items():
        if not isinstance(entities, list):
            raise ValidationError(f"Admin access entities for account {account_id} must be a list")


def validate_trend_analysis(analysis: TrendAnalysis) -> None:
    """Validate trend analysis data integrity."""
    # Validate growth metrics
    if analysis.user_growth.current_count < 0:
        raise ValidationError("Current user count cannot be negative")

    if analysis.group_growth.current_count < 0:
        raise ValidationError("Current group count cannot be negative")

    if analysis.permission_set_growth.current_count < 0:
        raise ValidationError("Current permission set count cannot be negative")

    if analysis.assignment_growth.current_count < 0:
        raise ValidationError("Current assignment count cannot be negative")


def validate_statistics_report(report: StatisticsReport) -> None:
    """Validate complete statistics report data integrity."""
    # Validate metadata
    if not report.metadata.instance_arn or not report.metadata.instance_arn.strip():
        raise ValidationError("Instance ARN cannot be empty")

    if not report.metadata.region or not report.metadata.region.strip():
        raise ValidationError("Region cannot be empty")

    if report.metadata.data_collection_duration < 0:
        raise ValidationError("Data collection duration cannot be negative")

    if report.metadata.analysis_duration < 0:
        raise ValidationError("Analysis duration cannot be negative")

    # Validate individual components
    validate_user_group_metrics(report.user_group_metrics)
    validate_permission_set_metrics(report.permission_set_metrics)
    validate_account_metrics(report.account_metrics)
    validate_assignment_patterns(report.assignment_patterns)
    validate_access_matrix(report.governance_view.access_matrix)
    validate_privileged_access_report(report.governance_view.privileged_access_report)

    if report.historical_comparison:
        validate_trend_analysis(report.historical_comparison)
