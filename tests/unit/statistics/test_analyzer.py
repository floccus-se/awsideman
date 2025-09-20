"""Tests for StatisticsAnalyzer calculation and pattern detection functionality."""

from datetime import datetime

import pytest

from src.awsideman.statistics.analyzer import StatisticsAnalyzer
from src.awsideman.statistics.models import AccountData, AccountMetrics
from src.awsideman.statistics.models import AssignmentData as StatisticsAssignmentData
from src.awsideman.statistics.models import (
    AssignmentPatterns,
    GroupData,
    GroupStatistics,
    PermissionSetData,
    PermissionSetMetrics,
    UserData,
    UserGroupMetrics,
    UserStatistics,
)


def AssignmentData(*args: str, **kwargs: str) -> StatisticsAssignmentData:
    """Create assignments from either the API order or model keyword fields."""
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


class TestStatisticsAnalyzer:
    """Test the StatisticsAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create a StatisticsAnalyzer instance for testing."""
        return StatisticsAnalyzer()

    @pytest.fixture
    def sample_users_data(self):
        """Create sample user statistics data."""
        users = [
            UserData(
                user_id="user1",
                username="john.doe",
                display_name="John Doe",
                email="john.doe@example.com",
                active=True,
            ),
            UserData(
                user_id="user2",
                username="jane.smith",
                display_name="Jane Smith",
                email="jane.smith@example.com",
                active=True,
            ),
            UserData(
                user_id="user3",
                username="bob.wilson",
                display_name="Bob Wilson",
                email="bob.wilson@example.com",
                active=True,
            ),
            UserData(
                user_id="user4",
                username="alice.brown",
                display_name="Alice Brown",
                email="alice.brown@example.com",
                active=False,
            ),
        ]

        group_memberships = {
            "user1": ["group1", "group2"],
            "user2": ["group1"],
            "user3": [],  # Orphaned user
            "user4": ["group2"],
        }

        return UserStatistics(
            users=users,
            group_memberships=group_memberships,
            collection_timestamp=datetime.now(),
        )

    @pytest.fixture
    def sample_groups_data(self):
        """Create sample group statistics data."""
        groups = [
            GroupData(
                group_id="group1",
                display_name="Developers",
                description="Development team",
            ),
            GroupData(
                group_id="group2",
                display_name="Admins",
                description="Administrative team",
            ),
            GroupData(
                group_id="group3",
                display_name="Empty Group",
                description="Group with no members",
            ),
        ]

        memberships = {
            "group1": ["user1", "user2"],
            "group2": ["user1", "user4"],
            "group3": [],  # Orphaned group
        }

        return GroupStatistics(
            groups=groups,
            memberships=memberships,
            collection_timestamp=datetime.now(),
        )

    @pytest.fixture
    def sample_permission_sets(self):
        """Create sample permission set data."""
        return [
            PermissionSetData(
                permission_set_arn="arn:aws:sso:::permissionSet/ssoins-123/ps-dev",
                name="DeveloperAccess",
                description="Developer access permissions",
                session_duration="PT8H",
                managed_policies=["arn:aws:iam::aws:policy/PowerUserAccess"],
                inline_policy=None,
            ),
            PermissionSetData(
                permission_set_arn="arn:aws:sso:::permissionSet/ssoins-123/ps-admin",
                name="AdminAccess",
                description="Administrative access permissions",
                session_duration="PT4H",
                managed_policies=["arn:aws:iam::aws:policy/AdministratorAccess"],
                inline_policy=None,
            ),
            PermissionSetData(
                permission_set_arn="arn:aws:sso:::permissionSet/ssoins-123/ps-readonly",
                name="ReadOnlyAccess",
                description="Read-only access permissions",
                session_duration="PT12H",
                managed_policies=["arn:aws:iam::aws:policy/ReadOnlyAccess"],
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

    @pytest.fixture
    def sample_accounts(self):
        """Create sample account data."""
        return [
            AccountData(
                account_id="123456789012",
                account_name="Production Account",
                email="prod@example.com",
                status="ACTIVE",
            ),
            AccountData(
                account_id="123456789013",
                account_name="Development Account",
                email="dev@example.com",
                status="ACTIVE",
            ),
            AccountData(
                account_id="123456789014",
                account_name="Unused Account",
                email="unused@example.com",
                status="ACTIVE",
            ),
        ]

    @pytest.fixture
    def sample_assignments(self):
        """Create sample assignment data."""
        return [
            AssignmentData(
                account_id="123456789012",
                permission_set_arn="arn:aws:sso:::permissionSet/ssoins-123/ps-dev",
                principal_type="USER",
                principal_id="user1",
            ),
            AssignmentData(
                account_id="123456789013",
                permission_set_arn="arn:aws:sso:::permissionSet/ssoins-123/ps-admin",
                principal_type="USER",
                principal_id="user1",
            ),
            AssignmentData(
                account_id="123456789012",
                permission_set_arn="arn:aws:sso:::permissionSet/ssoins-123/ps-dev",
                principal_type="GROUP",
                principal_id="group1",
            ),
            AssignmentData(
                account_id="123456789012",
                permission_set_arn="arn:aws:sso:::permissionSet/ssoins-123/ps-readonly",
                principal_type="USER",
                principal_id="user2",
            ),
        ]

    def test_calculate_user_group_metrics(self, analyzer, sample_users_data, sample_groups_data):
        """Test user and group metrics calculation."""
        result = analyzer.calculate_user_group_metrics(sample_users_data, sample_groups_data)

        assert isinstance(result, UserGroupMetrics)
        assert result.total_users == 4
        assert result.total_groups == 3

        # Check users per group
        assert result.users_per_group["group1"] == 2
        assert result.users_per_group["group2"] == 2
        assert result.users_per_group["group3"] == 0

        # Check groups per user
        assert result.groups_per_user["user1"] == 2
        assert result.groups_per_user["user2"] == 1
        assert result.groups_per_user["user3"] == 0
        assert result.groups_per_user["user4"] == 1

        # Check largest groups
        assert len(result.largest_groups) == 3
        # Both group1 and group2 have 2 users, so order may vary
        group_names = [group[0] for group in result.largest_groups]
        assert "Developers" in group_names
        assert "Admins" in group_names
        assert "Empty Group" in group_names

        # Check orphaned users (user3 has no group membership)
        assert "bob.wilson" in result.orphaned_users
        assert len(result.orphaned_users) == 1

        # Check orphaned groups (group3 has no members)
        assert "Empty Group" in result.orphaned_groups
        assert len(result.orphaned_groups) == 1

    def test_calculate_permission_set_metrics(
        self, analyzer, sample_permission_sets, sample_assignments
    ):
        """Test permission set metrics calculation."""
        result = analyzer.calculate_permission_set_metrics(
            sample_permission_sets, sample_assignments
        )

        assert isinstance(result, PermissionSetMetrics)
        assert result.total_permission_sets == 4

        # Check assignments per permission set
        dev_ps_arn = "arn:aws:sso:::permissionSet/ssoins-123/ps-dev"
        admin_ps_arn = "arn:aws:sso:::permissionSet/ssoins-123/ps-admin"
        readonly_ps_arn = "arn:aws:sso:::permissionSet/ssoins-123/ps-readonly"
        unused_ps_arn = "arn:aws:sso:::permissionSet/ssoins-123/ps-unused"

        assert result.assignments_per_permission_set[dev_ps_arn] == 2
        assert result.assignments_per_permission_set[admin_ps_arn] == 1
        assert result.assignments_per_permission_set[readonly_ps_arn] == 1
        assert result.assignments_per_permission_set[unused_ps_arn] == 0

        # Check most assigned permission sets
        assert len(result.most_assigned_permission_sets) == 4
        most_assigned_names = [ps[0] for ps in result.most_assigned_permission_sets]
        assert "DeveloperAccess" in most_assigned_names
        assert "AdminAccess" in most_assigned_names

        # Check unused permission sets
        assert "UnusedAccess" in result.unused_permission_sets
        assert len(result.unused_permission_sets) == 1

        # Check average assignments
        assert (
            result.average_assignments_per_permission_set == 1.0
        )  # 4 assignments / 4 permission sets

        # Check privileged permission sets detection
        assert "DeveloperAccess" in result.privileged_permission_sets  # PowerUserAccess
        assert "AdminAccess" in result.privileged_permission_sets  # AdministratorAccess
        assert "ReadOnlyAccess" in result.privileged_permission_sets  # ReadOnlyAccess
        assert "UnusedAccess" not in result.privileged_permission_sets

    def test_calculate_account_metrics(self, analyzer, sample_accounts, sample_assignments):
        """Test account metrics calculation."""
        result = analyzer.calculate_account_metrics(sample_accounts, sample_assignments)

        assert isinstance(result, AccountMetrics)
        assert result.total_accounts == 3

        # Check assignments per account
        assert result.assignments_per_account["123456789012"] == 3
        assert result.assignments_per_account["123456789013"] == 1
        assert result.assignments_per_account["123456789014"] == 0

        # Check users per account
        assert result.users_per_account["123456789012"] == 2  # user1, user2
        assert result.users_per_account["123456789013"] == 1  # user1
        assert result.users_per_account["123456789014"] == 0

        # Check groups per account
        assert result.groups_per_account["123456789012"] == 1  # group1
        assert result.groups_per_account["123456789013"] == 0
        assert result.groups_per_account["123456789014"] == 0

        # Check accounts with no assignments
        assert "Unused Account" in result.accounts_with_no_assignments
        assert len(result.accounts_with_no_assignments) == 1

        # Check cross-account users (user1 has assignments in 2 accounts)
        assert len(result.cross_account_users) == 1
        assert result.cross_account_users[0] == ("user1", 2)

        # Check cross-account groups (none in this sample)
        assert len(result.cross_account_groups) == 0

    def test_calculate_assignment_patterns(self, analyzer, sample_assignments):
        """Test assignment patterns calculation."""
        result = analyzer.calculate_assignment_patterns(sample_assignments)

        assert isinstance(result, AssignmentPatterns)

        # Check average assignments per user
        # user1: 2 assignments, user2: 1 assignment = 3 total / 2 users = 1.5
        assert result.average_assignments_per_user == 1.5

        # Check users with most assignments
        assert len(result.users_with_most_assignments) == 2
        assert result.users_with_most_assignments[0] == ("user1", 2)
        assert result.users_with_most_assignments[1] == ("user2", 1)

        # Check groups with most assignments
        assert len(result.groups_with_most_assignments) == 1
        assert result.groups_with_most_assignments[0] == ("group1", 1)

        # Assignment growth trend should be None without historical data
        assert result.assignment_growth_trend is None

    def test_calculate_assignment_patterns_empty_assignments(self, analyzer):
        """Test assignment patterns calculation with empty assignments."""
        result = analyzer.calculate_assignment_patterns([])

        assert isinstance(result, AssignmentPatterns)
        assert result.average_assignments_per_user == 0.0
        assert len(result.users_with_most_assignments) == 0
        assert len(result.groups_with_most_assignments) == 0
        assert result.assignment_growth_trend is None

    def test_privileged_permission_set_detection_inline_policy(self, analyzer):
        """Test privileged permission set detection with inline policies."""
        permission_sets = [
            PermissionSetData(
                permission_set_arn="arn:aws:sso:::permissionSet/ssoins-123/ps-custom",
                name="CustomAdmin",
                description="Custom admin permissions",
                session_duration="PT4H",
                managed_policies=[],
                inline_policy='{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]}',
            ),
            PermissionSetData(
                permission_set_arn="arn:aws:sso:::permissionSet/ssoins-123/ps-limited",
                name="LimitedAccess",
                description="Limited permissions",
                session_duration="PT8H",
                managed_policies=[],
                inline_policy='{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "s3:GetObject", "Resource": "*"}]}',
            ),
        ]

        result = analyzer.calculate_permission_set_metrics(permission_sets, [])

        # CustomAdmin should be detected as privileged due to "*" in inline policy
        assert "CustomAdmin" in result.privileged_permission_sets
        assert "LimitedAccess" not in result.privileged_permission_sets

    def test_user_group_metrics_edge_cases(self, analyzer):
        """Test user and group metrics with edge cases."""
        # Empty data
        empty_users = UserStatistics(
            users=[], group_memberships={}, collection_timestamp=datetime.now()
        )
        empty_groups = GroupStatistics(
            groups=[], memberships={}, collection_timestamp=datetime.now()
        )

        result = analyzer.calculate_user_group_metrics(empty_users, empty_groups)

        assert result.total_users == 0
        assert result.total_groups == 0
        assert len(result.largest_groups) == 0
        assert len(result.orphaned_users) == 0
        assert len(result.orphaned_groups) == 0

    def test_permission_set_metrics_edge_cases(self, analyzer):
        """Test permission set metrics with edge cases."""
        # Empty permission sets
        result = analyzer.calculate_permission_set_metrics([], [])

        assert result.total_permission_sets == 0
        assert result.average_assignments_per_permission_set == 0.0
        assert len(result.most_assigned_permission_sets) == 0
        assert len(result.unused_permission_sets) == 0
        assert len(result.privileged_permission_sets) == 0

    def test_account_metrics_edge_cases(self, analyzer):
        """Test account metrics with edge cases."""
        # Empty accounts
        result = analyzer.calculate_account_metrics([], [])

        assert result.total_accounts == 0
        assert len(result.assignments_per_account) == 0
        assert len(result.accounts_with_no_assignments) == 0
        assert len(result.cross_account_users) == 0
        assert len(result.cross_account_groups) == 0

    def test_cross_account_analysis(self, analyzer):
        """Test cross-account user and group analysis."""
        accounts = [
            AccountData(
                account_id="acc1",
                account_name="Account 1",
                email="acc1@example.com",
                status="ACTIVE",
            ),
            AccountData(
                account_id="acc2",
                account_name="Account 2",
                email="acc2@example.com",
                status="ACTIVE",
            ),
            AccountData(
                account_id="acc3",
                account_name="Account 3",
                email="acc3@example.com",
                status="ACTIVE",
            ),
        ]

        assignments = [
            # user1 in 3 accounts
            AssignmentData(
                account_id="acc1",
                permission_set_arn="ps1",
                principal_type="USER",
                principal_id="user1",
            ),
            AssignmentData(
                account_id="acc2",
                permission_set_arn="ps2",
                principal_type="USER",
                principal_id="user1",
            ),
            AssignmentData(
                account_id="acc3",
                permission_set_arn="ps3",
                principal_type="USER",
                principal_id="user1",
            ),
            # user2 in 2 accounts
            AssignmentData(
                account_id="acc1",
                permission_set_arn="ps1",
                principal_type="USER",
                principal_id="user2",
            ),
            AssignmentData(
                account_id="acc2",
                permission_set_arn="ps2",
                principal_type="USER",
                principal_id="user2",
            ),
            # group1 in 2 accounts
            AssignmentData(
                account_id="acc1",
                permission_set_arn="ps1",
                principal_type="GROUP",
                principal_id="group1",
            ),
            AssignmentData(
                account_id="acc2",
                permission_set_arn="ps2",
                principal_type="GROUP",
                principal_id="group1",
            ),
        ]

        result = analyzer.calculate_account_metrics(accounts, assignments)

        # Check cross-account users (sorted by account count descending)
        assert len(result.cross_account_users) == 2
        assert result.cross_account_users[0] == ("user1", 3)
        assert result.cross_account_users[1] == ("user2", 2)

        # Check cross-account groups
        assert len(result.cross_account_groups) == 1
        assert result.cross_account_groups[0] == ("group1", 2)

    def test_largest_groups_sorting(self, analyzer):
        """Test that largest groups are sorted correctly."""
        users = [
            UserData(f"user{i}", f"user{i}", f"User {i}", f"user{i}@example.com", True)
            for i in range(1, 21)
        ]

        groups = [
            GroupData("group1", "Small Group", "5 members"),
            GroupData("group2", "Large Group", "10 members"),
            GroupData("group3", "Medium Group", "7 members"),
        ]

        # Create memberships with different sizes
        group_memberships = {}
        memberships = {
            "group1": [f"user{i}" for i in range(1, 6)],  # 5 members
            "group2": [f"user{i}" for i in range(6, 16)],  # 10 members
            "group3": [f"user{i}" for i in range(16, 21)]
            + [f"user{i}" for i in range(1, 4)],  # 7 members
        }

        # Build reverse mapping for group_memberships
        for group_id, user_list in memberships.items():
            for user_id in user_list:
                if user_id not in group_memberships:
                    group_memberships[user_id] = []
                group_memberships[user_id].append(group_id)

        users_data = UserStatistics(
            users=users, group_memberships=group_memberships, collection_timestamp=datetime.now()
        )
        groups_data = GroupStatistics(
            groups=groups, memberships=memberships, collection_timestamp=datetime.now()
        )

        result = analyzer.calculate_user_group_metrics(users_data, groups_data)

        # Should be sorted by size descending: Large Group (10), Medium Group (7), Small Group (5)
        assert result.largest_groups[0] == ("Large Group", 10)
        assert result.largest_groups[1] == ("Medium Group", 7)
        assert result.largest_groups[2] == ("Small Group", 5)

    def test_most_assigned_permission_sets_sorting(self, analyzer):
        """Test that most assigned permission sets are sorted correctly."""
        permission_sets = [
            PermissionSetData("ps1", "PS1", "Permission Set 1", "PT8H", [], None, None),
            PermissionSetData("ps2", "PS2", "Permission Set 2", "PT8H", [], None, None),
            PermissionSetData("ps3", "PS3", "Permission Set 3", "PT8H", [], None, None),
        ]

        assignments = [
            # ps2: 5 assignments
            AssignmentData(
                account_id="acc1",
                permission_set_arn="ps2",
                principal_type="USER",
                principal_id="user1",
            ),
            AssignmentData("USER", "user2", "ps2", "acc1", "AWS_ACCOUNT"),
            AssignmentData("USER", "user3", "ps2", "acc1", "AWS_ACCOUNT"),
            AssignmentData("GROUP", "group1", "ps2", "acc1", "AWS_ACCOUNT"),
            AssignmentData("GROUP", "group2", "ps2", "acc1", "AWS_ACCOUNT"),
            # ps1: 2 assignments
            AssignmentData("USER", "user1", "ps1", "acc1", "AWS_ACCOUNT"),
            AssignmentData("GROUP", "group1", "ps1", "acc1", "AWS_ACCOUNT"),
            # ps3: 1 assignment
            AssignmentData("USER", "user1", "ps3", "acc1", "AWS_ACCOUNT"),
        ]

        result = analyzer.calculate_permission_set_metrics(permission_sets, assignments)

        # Should be sorted by assignment count descending: PS2 (5), PS1 (2), PS3 (1)
        assert result.most_assigned_permission_sets[0] == ("PS2", 5)
        assert result.most_assigned_permission_sets[1] == ("PS1", 2)
        assert result.most_assigned_permission_sets[2] == ("PS3", 1)

    def test_assignment_patterns_with_many_users(self, analyzer):
        """Test assignment patterns with many users and groups."""
        assignments = []

        # Create assignments for multiple users with varying counts
        user_assignment_counts = {"user1": 5, "user2": 3, "user3": 8, "user4": 1, "user5": 2}
        group_assignment_counts = {"group1": 4, "group2": 6, "group3": 1}

        assignment_id = 1
        for user_id, count in user_assignment_counts.items():
            for _ in range(count):
                assignments.append(
                    AssignmentData(
                        "USER", user_id, f"ps{assignment_id}", f"acc{assignment_id}", "AWS_ACCOUNT"
                    )
                )
                assignment_id += 1

        for group_id, count in group_assignment_counts.items():
            for _ in range(count):
                assignments.append(
                    AssignmentData(
                        "GROUP",
                        group_id,
                        f"ps{assignment_id}",
                        f"acc{assignment_id}",
                        "AWS_ACCOUNT",
                    )
                )
                assignment_id += 1

        result = analyzer.calculate_assignment_patterns(assignments)

        # Check average (total user assignments / unique users)
        total_user_assignments = sum(user_assignment_counts.values())
        unique_users = len(user_assignment_counts)
        expected_average = total_user_assignments / unique_users
        assert result.average_assignments_per_user == expected_average

        # Check users with most assignments (should be sorted descending)
        assert result.users_with_most_assignments[0] == ("user3", 8)
        assert result.users_with_most_assignments[1] == ("user1", 5)
        assert result.users_with_most_assignments[2] == ("user2", 3)

        # Check groups with most assignments (should be sorted descending)
        assert result.groups_with_most_assignments[0] == ("group2", 6)
        assert result.groups_with_most_assignments[1] == ("group1", 4)
        assert result.groups_with_most_assignments[2] == ("group3", 1)
