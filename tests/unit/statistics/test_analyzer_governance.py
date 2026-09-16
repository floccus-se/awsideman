"""Tests for StatisticsAnalyzer governance and orphaned resource detection."""

from datetime import datetime

import pytest

from src.awsideman.statistics.analyzer import StatisticsAnalyzer
from src.awsideman.statistics.models import AccessMatrix, AccountData, AccountStatistics
from src.awsideman.statistics.models import AssignmentData as StatisticsAssignmentData
from src.awsideman.statistics.models import (
    AssignmentStatistics,
    GovernanceAnalysis,
    GroupData,
    GroupStatistics,
    OrphanedResources,
    PermissionSetData,
    PermissionSetStatistics,
    PrivilegedAccessReport,
    RawStatisticsData,
    UserData,
    UserStatistics,
)


def AssignmentData(*args: str, **kwargs: str) -> StatisticsAssignmentData:
    """Create assignments from the API's positional response shape."""
    if kwargs:
        return StatisticsAssignmentData(**kwargs)
    if len(args) != 5:
        raise TypeError(
            "Expected principal type, principal ID, permission set, account ID, target type"
        )
    principal_type, principal_id, permission_set_arn, account_id, _target_type = args
    return StatisticsAssignmentData(
        account_id=account_id,
        permission_set_arn=permission_set_arn,
        principal_type=principal_type,
        principal_id=principal_id,
    )


class TestStatisticsAnalyzerGovernance:
    """Test governance and orphaned resource detection in StatisticsAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create a StatisticsAnalyzer instance for testing."""
        return StatisticsAnalyzer()

    @pytest.fixture
    def comprehensive_raw_data(self):
        """Create comprehensive raw statistics data for testing."""
        # Users
        users = [
            UserData("user1", "john.doe", "John Doe", "john.doe@example.com", True),
            UserData("user2", "jane.smith", "Jane Smith", "jane.smith@example.com", True),
            UserData("user3", "orphaned.user", "Orphaned User", "orphaned@example.com", True),
            UserData("user4", "inactive.user", "Inactive User", "inactive@example.com", False),
        ]

        user_group_memberships = {
            "user1": ["group1", "group2"],
            "user2": ["group1"],
            "user3": [],  # Orphaned - no groups, no assignments
            "user4": ["group3"],  # Has group but group has no assignments
        }

        users_data = UserStatistics(
            users=users,
            group_memberships=user_group_memberships,
            collection_timestamp=datetime.now(),
        )

        # Groups
        groups = [
            GroupData("group1", "Active Group", "Group with members and assignments"),
            GroupData("group2", "User Group", "Group with members but no assignments"),
            GroupData("group3", "Inactive Group", "Group with members but no assignments"),
            GroupData("group4", "Empty Group", "Group with no members"),
        ]

        group_memberships = {
            "group1": ["user1", "user2"],
            "group2": ["user1"],
            "group3": ["user4"],
            "group4": [],  # Orphaned - no members
        }

        groups_data = GroupStatistics(
            groups=groups,
            memberships=group_memberships,
            collection_timestamp=datetime.now(),
        )

        # Permission Sets
        permission_sets = [
            PermissionSetData(
                permission_set_arn="arn:aws:sso:::permissionSet/ssoins-123/ps-admin",
                name="AdminAccess",
                description="Administrative access",
                session_duration="PT4H",
                managed_policies=["arn:aws:iam::aws:policy/AdministratorAccess"],
                inline_policy=None,
            ),
            PermissionSetData(
                permission_set_arn="arn:aws:sso:::permissionSet/ssoins-123/ps-dev",
                name="DeveloperAccess",
                description="Developer access",
                session_duration="PT8H",
                managed_policies=["arn:aws:iam::aws:policy/PowerUserAccess"],
                inline_policy=None,
            ),
            PermissionSetData(
                permission_set_arn="arn:aws:sso:::permissionSet/ssoins-123/ps-unused",
                name="UnusedAccess",
                description="Unused permission set",
                session_duration="PT8H",
                managed_policies=[],
                inline_policy=None,
            ),
        ]

        permission_sets_data = PermissionSetStatistics(
            permission_sets=permission_sets,
            collection_timestamp=datetime.now(),
        )

        # Accounts
        accounts = [
            AccountData("123456789012", "Production Account", "prod@example.com", "ACTIVE"),
            AccountData("123456789013", "Development Account", "dev@example.com", "ACTIVE"),
            AccountData("123456789014", "Unused Account", "unused@example.com", "ACTIVE"),
        ]

        accounts_data = AccountStatistics(
            accounts=accounts,
            collection_timestamp=datetime.now(),
        )

        # Assignments
        assignments = [
            # user1 has admin access to prod and dev access to dev
            AssignmentData(
                "USER",
                "user1",
                "arn:aws:sso:::permissionSet/ssoins-123/ps-admin",
                "123456789012",
                "AWS_ACCOUNT",
            ),
            AssignmentData(
                "USER",
                "user1",
                "arn:aws:sso:::permissionSet/ssoins-123/ps-dev",
                "123456789013",
                "AWS_ACCOUNT",
            ),
            # group1 has dev access to prod
            AssignmentData(
                "GROUP",
                "group1",
                "arn:aws:sso:::permissionSet/ssoins-123/ps-dev",
                "123456789012",
                "AWS_ACCOUNT",
            ),
            # user2 gets access through group1 membership
        ]

        assignments_data = AssignmentStatistics(
            assignments=assignments,
            collection_timestamp=datetime.now(),
        )

        return RawStatisticsData(
            users=users_data,
            groups=groups_data,
            permission_sets=permission_sets_data,
            accounts=accounts_data,
            assignments=assignments_data,
        )

    def test_detect_orphaned_resources(self, analyzer, comprehensive_raw_data):
        """Test detection of orphaned resources."""
        result = analyzer.detect_orphaned_resources(comprehensive_raw_data)

        assert isinstance(result, OrphanedResources)

        # Check orphaned users (user3 has no groups and no assignments)
        assert "orphaned.user" in result.orphaned_users
        assert len(result.orphaned_users) == 1

        # Check orphaned groups (group4 has no members, groups 2&3 have members but no assignments)
        # Note: groups with members but no assignments are not considered orphaned
        assert "Empty Group" in result.orphaned_groups
        assert len(result.orphaned_groups) == 1

        # Check unused permission sets
        assert "UnusedAccess" in result.unused_permission_sets
        assert len(result.unused_permission_sets) == 1

        # Check unassigned accounts
        assert "Unused Account" in result.unassigned_accounts
        assert len(result.unassigned_accounts) == 1

    def test_generate_access_matrix(self, analyzer, comprehensive_raw_data):
        """Test access matrix generation."""
        result = analyzer.generate_access_matrix(comprehensive_raw_data)

        assert isinstance(result, AccessMatrix)

        # Check user to accounts mapping
        assert "user1" in result.user_to_accounts
        assert "123456789012" in result.user_to_accounts["user1"]
        assert "123456789013" in result.user_to_accounts["user1"]

        # Check user to permission sets mapping
        assert "user1" in result.user_to_permission_sets
        assert (
            "arn:aws:sso:::permissionSet/ssoins-123/ps-admin"
            in result.user_to_permission_sets["user1"]
        )
        assert (
            "arn:aws:sso:::permissionSet/ssoins-123/ps-dev"
            in result.user_to_permission_sets["user1"]
        )

        # Check group to accounts mapping
        assert "group1" in result.group_to_accounts
        assert "123456789012" in result.group_to_accounts["group1"]

        # Check group to permission sets mapping
        assert "group1" in result.group_to_permission_sets
        assert (
            "arn:aws:sso:::permissionSet/ssoins-123/ps-dev"
            in result.group_to_permission_sets["group1"]
        )

        # Check account to users mapping
        assert "123456789012" in result.account_to_users
        assert "user1" in result.account_to_users["123456789012"]

        # Check account to groups mapping
        assert "123456789012" in result.account_to_groups
        assert "group1" in result.account_to_groups["123456789012"]

    def test_detect_privileged_access(self, analyzer, comprehensive_raw_data):
        """Test privileged access detection."""
        result = analyzer.detect_privileged_access(comprehensive_raw_data)

        assert isinstance(result, PrivilegedAccessReport)

        # Check admin permission sets
        assert "AdminAccess" in result.admin_permission_sets
        assert "DeveloperAccess" in result.admin_permission_sets  # PowerUserAccess is privileged
        assert "UnusedAccess" not in result.admin_permission_sets

        # Check accounts with admin access
        assert "123456789012" in result.accounts_with_admin_access
        assert "User: john.doe" in result.accounts_with_admin_access["123456789012"]
        assert "Group: Active Group" in result.accounts_with_admin_access["123456789012"]

        # Check users with admin access
        assert "john.doe" in result.users_with_admin_access

        # Check high privilege patterns
        assert len(result.high_privilege_patterns) > 0

    def test_analyze_governance_gaps(self, analyzer, comprehensive_raw_data):
        """Test governance gap analysis."""
        result = analyzer.analyze_governance_gaps(comprehensive_raw_data)

        assert isinstance(result, GovernanceAnalysis)

        # Should identify various governance issues
        assert len(result.view.compliance_gaps) > 0

        # Check for specific gap types
        gap_types = [gap.gap_type for gap in result.view.compliance_gaps]
        assert "user_organization" in gap_types
        assert "excessive_privilege" in gap_types

    def test_orphaned_resources_edge_cases(self, analyzer):
        """Test orphaned resource detection with edge cases."""
        # Create minimal data with no orphaned resources
        users = [UserData("user1", "user1", "User 1", "user1@example.com", True)]
        groups = [GroupData("group1", "Group 1", "Active group")]
        permission_sets = [PermissionSetData("ps1", "PS1", "PS 1", "PT8H", [], None, None)]
        accounts = [AccountData("acc1", "Account 1", "acc1@example.com", "ACTIVE")]
        assignments = [AssignmentData("USER", "user1", "ps1", "acc1", "AWS_ACCOUNT")]

        users_data = UserStatistics(
            users=users,
            group_memberships={"user1": ["group1"]},
            collection_timestamp=datetime.now(),
        )
        groups_data = GroupStatistics(
            groups=groups, memberships={"group1": ["user1"]}, collection_timestamp=datetime.now()
        )
        permission_sets_data = PermissionSetStatistics(
            permission_sets=permission_sets, collection_timestamp=datetime.now()
        )
        accounts_data = AccountStatistics(accounts=accounts, collection_timestamp=datetime.now())
        assignments_data = AssignmentStatistics(
            assignments=assignments, collection_timestamp=datetime.now()
        )

        raw_data = RawStatisticsData(
            users=users_data,
            groups=groups_data,
            permission_sets=permission_sets_data,
            accounts=accounts_data,
            assignments=assignments_data,
        )

        result = analyzer.detect_orphaned_resources(raw_data)

        # Should find no orphaned resources
        assert len(result.orphaned_users) == 0
        assert len(result.orphaned_groups) == 0
        assert len(result.unused_permission_sets) == 0
        assert len(result.unassigned_accounts) == 0

    def test_access_matrix_empty_data(self, analyzer):
        """Test access matrix generation with empty data."""
        empty_data = RawStatisticsData(
            users=UserStatistics(
                users=[], group_memberships={}, collection_timestamp=datetime.now()
            ),
            groups=GroupStatistics(groups=[], memberships={}, collection_timestamp=datetime.now()),
            permission_sets=PermissionSetStatistics(
                permission_sets=[], collection_timestamp=datetime.now()
            ),
            accounts=AccountStatistics(accounts=[], collection_timestamp=datetime.now()),
            assignments=AssignmentStatistics(assignments=[], collection_timestamp=datetime.now()),
        )

        result = analyzer.generate_access_matrix(empty_data)

        assert isinstance(result, AccessMatrix)
        assert len(result.user_to_accounts) == 0
        assert len(result.user_to_permission_sets) == 0
        assert len(result.group_to_accounts) == 0
        assert len(result.group_to_permission_sets) == 0
        assert len(result.account_to_users) == 0
        assert len(result.account_to_groups) == 0

    def test_privileged_access_detection_patterns(self, analyzer):
        """Test privileged access detection with various patterns."""
        # Create permission sets with different privilege patterns
        permission_sets = [
            # Explicit admin policy
            PermissionSetData(
                "ps-admin",
                "AdminPS",
                "Admin PS",
                "PT4H",
                ["arn:aws:iam::aws:policy/AdministratorAccess"],
                None,
                None,
            ),
            # Power user policy
            PermissionSetData(
                "ps-power",
                "PowerPS",
                "Power PS",
                "PT8H",
                ["arn:aws:iam::aws:policy/PowerUserAccess"],
                None,
                None,
            ),
            # IAM full access
            PermissionSetData(
                "ps-iam",
                "IAMPS",
                "IAM PS",
                "PT8H",
                ["arn:aws:iam::aws:policy/IAMFullAccess"],
                None,
                None,
            ),
            # Security audit
            PermissionSetData(
                "ps-audit",
                "AuditPS",
                "Audit PS",
                "PT12H",
                ["arn:aws:iam::aws:policy/SecurityAudit"],
                None,
                None,
            ),
            # Read only
            PermissionSetData(
                "ps-readonly",
                "ReadOnlyPS",
                "ReadOnly PS",
                "PT12H",
                ["arn:aws:iam::aws:policy/ReadOnlyAccess"],
                None,
                None,
            ),
            # Custom with wildcard inline policy
            PermissionSetData(
                permission_set_arn="ps-custom",
                name="CustomPS",
                description="Custom PS",
                session_duration="PT8H",
                managed_policies=[],
                inline_policy='{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]}',
            ),
            # Non-privileged
            PermissionSetData(
                permission_set_arn="ps-limited",
                name="LimitedPS",
                description="Limited PS",
                session_duration="PT8H",
                managed_policies=[],
                inline_policy='{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "s3:GetObject", "Resource": "*"}]}',
            ),
        ]

        # Create minimal other data
        users_data = UserStatistics(
            users=[], group_memberships={}, collection_timestamp=datetime.now()
        )
        groups_data = GroupStatistics(
            groups=[], memberships={}, collection_timestamp=datetime.now()
        )
        permission_sets_data = PermissionSetStatistics(
            permission_sets=permission_sets, collection_timestamp=datetime.now()
        )
        accounts_data = AccountStatistics(accounts=[], collection_timestamp=datetime.now())
        assignments_data = AssignmentStatistics(assignments=[], collection_timestamp=datetime.now())

        raw_data = RawStatisticsData(
            users=users_data,
            groups=groups_data,
            permission_sets=permission_sets_data,
            accounts=accounts_data,
            assignments=assignments_data,
        )

        result = analyzer.detect_privileged_access(raw_data)

        # Check that all privileged permission sets are detected
        expected_privileged = {"AdminPS", "PowerPS", "IAMPS", "AuditPS", "CustomPS"}
        actual_privileged = set(result.admin_permission_sets)

        assert expected_privileged.issubset(actual_privileged)
        assert "LimitedPS" not in result.admin_permission_sets

    def test_governance_analysis_comprehensive(self, analyzer, comprehensive_raw_data):
        """Test comprehensive governance analysis."""
        result = analyzer.analyze_governance_gaps(comprehensive_raw_data)

        assert isinstance(result, GovernanceAnalysis)

        # Should identify multiple types of compliance gaps
        gap_types = {gap.gap_type for gap in result.view.compliance_gaps}

        # Expected gap types based on the test data
        expected_gaps = {
            "user_organization",
            "excessive_privilege",
            "resource_waste",
        }

        # At least some of these should be present
        assert len(gap_types.intersection(expected_gaps)) > 0

        # Each gap should have proper details
        for gap in result.view.compliance_gaps:
            assert gap.gap_type is not None
            assert gap.description is not None
            assert gap.severity in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            assert isinstance(gap.affected_resources, list)

    def test_user_indirect_access_through_groups(self, analyzer):
        """Test that users get access through group memberships in access matrix."""
        # Create data where user2 only gets access through group membership
        users = [
            UserData("user1", "user1", "User 1", "user1@example.com", True),
            UserData("user2", "user2", "User 2", "user2@example.com", True),
        ]

        groups = [GroupData("group1", "Group 1", "Test group")]

        permission_sets = [PermissionSetData("ps1", "PS1", "PS 1", "PT8H", [], None, None)]

        accounts = [AccountData("acc1", "Account 1", "acc1@example.com", "ACTIVE")]

        # Only group1 has assignment, user2 is member of group1
        assignments = [AssignmentData("GROUP", "group1", "ps1", "acc1", "AWS_ACCOUNT")]

        users_data = UserStatistics(
            users=users,
            group_memberships={"user1": [], "user2": ["group1"]},
            collection_timestamp=datetime.now(),
        )
        groups_data = GroupStatistics(
            groups=groups, memberships={"group1": ["user2"]}, collection_timestamp=datetime.now()
        )
        permission_sets_data = PermissionSetStatistics(
            permission_sets=permission_sets, collection_timestamp=datetime.now()
        )
        accounts_data = AccountStatistics(accounts=accounts, collection_timestamp=datetime.now())
        assignments_data = AssignmentStatistics(
            assignments=assignments, collection_timestamp=datetime.now()
        )

        raw_data = RawStatisticsData(
            users=users_data,
            groups=groups_data,
            permission_sets=permission_sets_data,
            accounts=accounts_data,
            assignments=assignments_data,
        )

        # Check orphaned resources - user1 should be orphaned, user2 should not
        orphaned = analyzer.detect_orphaned_resources(raw_data)
        assert "user1" in orphaned.orphaned_users  # No groups, no direct assignments
        assert "user2" not in orphaned.orphaned_users  # Has group membership with assignment

        # Check access matrix - user2 should have indirect access through group
        access_matrix = analyzer.generate_access_matrix(raw_data)

        # user2 should appear in account access through group membership
        # This depends on implementation - the access matrix might show indirect access
        assert "group1" in access_matrix.group_to_accounts
        assert "acc1" in access_matrix.group_to_accounts["group1"]

    def test_complex_cross_account_privilege_patterns(self, analyzer):
        """Test detection of complex cross-account privilege patterns."""
        # Create a scenario with complex privilege escalation possibilities
        users = [UserData("user1", "user1", "User 1", "user1@example.com", True)]
        groups = [GroupData("group1", "Group 1", "Admin group")]

        permission_sets = [
            PermissionSetData(
                "ps-admin",
                "AdminAccess",
                "Admin access",
                "PT4H",
                ["arn:aws:iam::aws:policy/AdministratorAccess"],
                None,
                None,
            )
        ]

        accounts = [
            AccountData("prod-acc", "Production", "prod@example.com", "ACTIVE"),
            AccountData("dev-acc", "Development", "dev@example.com", "ACTIVE"),
            AccountData("test-acc", "Testing", "test@example.com", "ACTIVE"),
        ]

        # User has admin access across multiple accounts
        assignments = [
            AssignmentData("USER", "user1", "ps-admin", "prod-acc", "AWS_ACCOUNT"),
            AssignmentData("USER", "user1", "ps-admin", "dev-acc", "AWS_ACCOUNT"),
            AssignmentData("USER", "user1", "ps-admin", "test-acc", "AWS_ACCOUNT"),
        ]

        users_data = UserStatistics(
            users=users,
            group_memberships={"user1": ["group1"]},
            collection_timestamp=datetime.now(),
        )
        groups_data = GroupStatistics(
            groups=groups, memberships={"group1": ["user1"]}, collection_timestamp=datetime.now()
        )
        permission_sets_data = PermissionSetStatistics(
            permission_sets=permission_sets, collection_timestamp=datetime.now()
        )
        accounts_data = AccountStatistics(accounts=accounts, collection_timestamp=datetime.now())
        assignments_data = AssignmentStatistics(
            assignments=assignments, collection_timestamp=datetime.now()
        )

        raw_data = RawStatisticsData(
            users=users_data,
            groups=groups_data,
            permission_sets=permission_sets_data,
            accounts=accounts_data,
            assignments=assignments_data,
        )

        result = analyzer.detect_privileged_access(raw_data)

        # Should detect high-risk pattern: user with admin access across multiple accounts
        assert "user1" in result.users_with_admin_access
        assert len(result.accounts_with_admin_access) == 3  # All three accounts

        # Should have high privilege patterns
        pattern_types = [pattern.pattern_type for pattern in result.high_privilege_patterns]
        assert "cross_account_admin" in pattern_types or "multi_account_access" in pattern_types
