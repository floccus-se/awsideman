"""Statistics analyzer for performing calculations and pattern analysis."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .models import (
        AccessMatrix,
        AccountData,
        AccountMetrics,
        AssignmentData,
        AssignmentPatterns,
        AssignmentStatistics,
        GovernanceAnalysis,
        GovernanceView,
        GroupStatistics,
        OrphanedResources,
        PermissionAnalysis,
        PermissionSetData,
        PermissionSetMetrics,
        PermissionSetStatistics,
        PrivilegedAccessReport,
        RawStatisticsData,
        TrendAnalysis,
        UserAnalysis,
        UserData,
        UserGroupMetrics,
        UserStatistics,
    )


class StatisticsAnalyzer:
    """Analyzes collected data to generate insights."""

    def calculate_user_group_metrics(
        self,
        users_data: "UserStatistics",
        groups_data: "GroupStatistics",
        assignments_data: Optional["AssignmentStatistics"] = None,
    ) -> "UserGroupMetrics":
        """Calculate user and group metrics.

        Args:
            users_data: User statistics data
            groups_data: Group statistics data

        Returns:
            User and group metrics
        """
        from .models import UserGroupMetrics

        total_users = len(users_data.users)
        total_groups = len(groups_data.groups)

        # Calculate users per group
        users_per_group = {}
        for group_id, user_ids in groups_data.memberships.items():
            users_per_group[group_id] = len(user_ids)

        # Calculate groups per user
        # Derive user group memberships from group memberships data
        groups_per_user: Dict[str, int] = {}
        user_group_memberships: Dict[str, List[str]] = {}

        # Create user ID to username mapping
        user_id_to_username = {user.user_id: user.username for user in users_data.users}

        # Initialize all users with empty group lists
        for user in users_data.users:
            user_group_memberships[user.user_id] = []
            groups_per_user[user.user_id] = 0

        # Build user group memberships from group memberships
        for group_id, user_ids in groups_data.memberships.items():
            for user_id in user_ids:
                if user_id in user_group_memberships:
                    user_group_memberships[user_id].append(group_id)
                    groups_per_user[user_id] = len(user_group_memberships[user_id])

        # Create username-based mapping for display purposes
        groups_per_user_by_name = {}
        for user_id, group_count in groups_per_user.items():
            username = user_id_to_username.get(
                user_id, user_id
            )  # fallback to user_id if username not found
            groups_per_user_by_name[username] = group_count

        # Find largest groups (top 10)
        largest_groups = []
        group_name_map = {g.group_id: g.display_name for g in groups_data.groups}
        for group_id, user_count in sorted(
            users_per_group.items(), key=lambda x: x[1], reverse=True
        )[:10]:
            group_name = group_name_map.get(group_id, group_id)
            largest_groups.append((group_name, user_count))

        # Find orphaned users (ACTIVE users with no group membership AND no assignments)
        orphaned_users = []
        disabled_users = []

        # Collect assignment data if available
        user_assignments = set()
        group_assignments = set()

        if assignments_data:
            for assignment in assignments_data.assignments:
                if assignment.principal_type == "USER":
                    user_assignments.add(assignment.principal_id)
                elif assignment.principal_type == "GROUP":
                    group_assignments.add(assignment.principal_id)

        for user in users_data.users:
            # Collect disabled users separately
            if not user.active:
                disabled_users.append(user.username)
                continue

            user_groups = user_group_memberships.get(user.user_id, [])
            has_direct_assignment = user.user_id in user_assignments
            has_group_assignment = any(group_id in group_assignments for group_id in user_groups)

            # User is orphaned if they are ACTIVE and have no group membership AND no assignments (direct or through groups)
            if not user_groups and not has_direct_assignment and not has_group_assignment:
                orphaned_users.append(user.username)

        # Find orphaned groups (groups with no members)
        orphaned_groups = []
        for group in groups_data.groups:
            group_members = groups_data.memberships.get(group.group_id, [])
            if not group_members:
                orphaned_groups.append(group.display_name)

        return UserGroupMetrics(
            total_users=total_users,
            total_groups=total_groups,
            users_per_group=users_per_group,
            groups_per_user=groups_per_user,
            groups_per_user_by_name=groups_per_user_by_name,
            largest_groups=largest_groups,
            orphaned_users=orphaned_users,
            disabled_users=disabled_users,
            orphaned_groups=orphaned_groups,
        )

    def calculate_permission_set_metrics(
        self, permission_sets: List["PermissionSetData"], assignments: List["AssignmentData"]
    ) -> "PermissionSetMetrics":
        """Calculate permission set metrics.

        Args:
            permission_sets: Permission set data
            assignments: Assignment data

        Returns:
            Permission set metrics
        """
        from .models import PermissionSetMetrics

        total_permission_sets = len(permission_sets)

        # Count assignments per permission set
        assignments_per_permission_set = {}
        for ps in permission_sets:
            assignments_per_permission_set[ps.permission_set_arn] = 0

        for assignment in assignments:
            if assignment.permission_set_arn in assignments_per_permission_set:
                assignments_per_permission_set[assignment.permission_set_arn] += 1

        # Find most assigned permission sets (top 10)
        ps_name_map = {ps.permission_set_arn: ps.name for ps in permission_sets}
        most_assigned = []
        for ps_arn, count in sorted(
            assignments_per_permission_set.items(), key=lambda x: x[1], reverse=True
        )[:10]:
            ps_name = ps_name_map.get(ps_arn, ps_arn)
            most_assigned.append((ps_name, count))

        # Find unused permission sets
        unused_permission_sets = []
        for ps in permission_sets:
            if assignments_per_permission_set[ps.permission_set_arn] == 0:
                unused_permission_sets.append(ps.name)

        # Calculate average assignments per permission set
        total_assignments = sum(assignments_per_permission_set.values())
        average_assignments = (
            total_assignments / total_permission_sets if total_permission_sets > 0 else 0.0
        )

        # Detect privileged permission sets based on managed policies
        privileged_permission_sets = []
        admin_policy_patterns = [
            "AdministratorAccess",
            "PowerUserAccess",
            "IAMFullAccess",
            "SecurityAudit",
            "ReadOnlyAccess",
        ]

        for ps in permission_sets:
            is_privileged = False

            # Check managed policies
            for policy_arn in ps.managed_policies:
                policy_name = policy_arn.split("/")[-1] if "/" in policy_arn else policy_arn
                if any(pattern in policy_name for pattern in admin_policy_patterns):
                    is_privileged = True
                    break

            # Check inline policy for admin-like permissions
            if not is_privileged and ps.inline_policy:
                inline_lower = ps.inline_policy.lower()
                if any(keyword in inline_lower for keyword in ["*", "admin", "full", "all"]):
                    is_privileged = True

            if is_privileged:
                privileged_permission_sets.append(ps.name)

        return PermissionSetMetrics(
            total_permission_sets=total_permission_sets,
            assignments_per_permission_set=assignments_per_permission_set,
            most_assigned_permission_sets=most_assigned,
            unused_permission_sets=unused_permission_sets,
            average_assignments_per_permission_set=average_assignments,
            privileged_permission_sets=privileged_permission_sets,
        )

    def calculate_account_metrics(
        self,
        accounts: List["AccountData"],
        assignments: List["AssignmentData"],
        users: Optional[List["UserData"]] = None,
    ) -> "AccountMetrics":
        """Calculate account metrics.

        Args:
            accounts: Account data
            assignments: Assignment data
            users: Optional user data for username mapping

        Returns:
            Account metrics
        """
        from collections import defaultdict

        from .models import AccountMetrics

        # Create user ID to username mapping
        user_id_to_username = {}
        if users:
            for user in users:
                user_id_to_username[user.user_id] = user.username

        total_accounts = len(accounts)

        # Count assignments per account
        assignments_per_account = {}
        users_per_account = defaultdict(set)
        groups_per_account = defaultdict(set)

        # Initialize all accounts with 0 assignments
        for account in accounts:
            assignments_per_account[account.account_id] = 0

        # Count assignments and track users/groups per account
        for assignment in assignments:
            if assignment.account_id in assignments_per_account:
                assignments_per_account[assignment.account_id] += 1

                if assignment.principal_type == "USER":
                    users_per_account[assignment.account_id].add(assignment.principal_id)
                elif assignment.principal_type == "GROUP":
                    groups_per_account[assignment.account_id].add(assignment.principal_id)

        # Convert sets to counts
        users_per_account_count = {
            account_id: len(users) for account_id, users in users_per_account.items()
        }
        groups_per_account_count = {
            account_id: len(groups) for account_id, groups in groups_per_account.items()
        }

        # Ensure all accounts are represented
        for account in accounts:
            if account.account_id not in users_per_account_count:
                users_per_account_count[account.account_id] = 0
            if account.account_id not in groups_per_account_count:
                groups_per_account_count[account.account_id] = 0

        # Find accounts with no assignments
        accounts_with_no_assignments = []
        account_name_map = {acc.account_id: acc.account_name for acc in accounts}
        for account_id, assignment_count in assignments_per_account.items():
            if assignment_count == 0:
                account_name = account_name_map.get(account_id, account_id)
                accounts_with_no_assignments.append(account_name)

        # Find cross-account users (users assigned to multiple accounts)
        user_account_count = defaultdict(set)
        for assignment in assignments:
            if assignment.principal_type == "USER":
                user_account_count[assignment.principal_id].add(assignment.account_id)

        cross_account_users = []
        for user_id, account_set in user_account_count.items():
            if len(account_set) > 1:
                # Use username if available, otherwise fall back to user_id
                display_name = user_id_to_username.get(user_id, user_id)
                cross_account_users.append((display_name, len(account_set)))

        # Sort by account count descending
        cross_account_users.sort(key=lambda x: x[1], reverse=True)

        # Find cross-account groups (groups assigned to multiple accounts)
        group_account_count = defaultdict(set)
        for assignment in assignments:
            if assignment.principal_type == "GROUP":
                group_account_count[assignment.principal_id].add(assignment.account_id)

        cross_account_groups = []
        for group_id, account_set in group_account_count.items():
            if len(account_set) > 1:
                cross_account_groups.append((group_id, len(account_set)))

        # Sort by account count descending
        cross_account_groups.sort(key=lambda x: x[1], reverse=True)

        return AccountMetrics(
            total_accounts=total_accounts,
            assignments_per_account=assignments_per_account,
            users_per_account=users_per_account_count,
            groups_per_account=groups_per_account_count,
            accounts_with_no_assignments=accounts_with_no_assignments,
            cross_account_users=cross_account_users,
            cross_account_groups=cross_account_groups,
        )

    def calculate_assignment_patterns(
        self, assignments: List["AssignmentData"]
    ) -> "AssignmentPatterns":
        """Calculate assignment patterns.

        Args:
            assignments: Assignment data

        Returns:
            Assignment patterns analysis
        """
        from collections import defaultdict

        from .models import AssignmentPatterns

        if not assignments:
            return AssignmentPatterns(
                average_assignments_per_user=0.0,
                users_with_most_assignments=[],
                groups_with_most_assignments=[],
                assignment_growth_trend=None,
            )

        # Count assignments per user and group
        user_assignment_count: Dict[str, int] = defaultdict(int)
        group_assignment_count: Dict[str, int] = defaultdict(int)

        for assignment in assignments:
            if assignment.principal_type == "USER":
                user_assignment_count[assignment.principal_id] += 1
            elif assignment.principal_type == "GROUP":
                group_assignment_count[assignment.principal_id] += 1

        # Calculate average assignments per user
        total_user_assignments = sum(user_assignment_count.values())
        unique_users = len(user_assignment_count)
        average_assignments_per_user = (
            total_user_assignments / unique_users if unique_users > 0 else 0.0
        )

        # Find users with most assignments (top 10)
        users_with_most_assignments = []
        for user_id, count in sorted(
            user_assignment_count.items(), key=lambda x: x[1], reverse=True
        )[:10]:
            users_with_most_assignments.append((user_id, count))

        # Find groups with most assignments (top 10)
        groups_with_most_assignments = []
        for group_id, count in sorted(
            group_assignment_count.items(), key=lambda x: x[1], reverse=True
        )[:10]:
            groups_with_most_assignments.append((group_id, count))

        # Assignment growth trend would require historical data
        # This can be populated by calling calculate_assignment_patterns_with_trend
        assignment_growth_trend = None

        return AssignmentPatterns(
            average_assignments_per_user=average_assignments_per_user,
            users_with_most_assignments=users_with_most_assignments,
            groups_with_most_assignments=groups_with_most_assignments,
            assignment_growth_trend=assignment_growth_trend,
        )

    def detect_orphaned_resources(self, data: "RawStatisticsData") -> "OrphanedResources":
        """Detect orphaned resources.

        Args:
            data: Raw statistics data

        Returns:
            Orphaned resources detection result
        """
        from .models import OrphanedResources

        # Find orphaned users (users with no group membership and no direct assignments)
        orphaned_users = []
        user_assignments = set()
        group_assignments = set()

        # Collect all users and groups that have assignments
        for assignment in data.assignments.assignments:
            if assignment.principal_type == "USER":
                user_assignments.add(assignment.principal_id)
            elif assignment.principal_type == "GROUP":
                group_assignments.add(assignment.principal_id)

        # Find users with no group membership and no direct assignments
        for user in data.users.users:
            user_groups = data.users.group_memberships.get(user.user_id, [])
            has_direct_assignment = user.user_id in user_assignments
            has_group_assignment = any(group_id in group_assignments for group_id in user_groups)

            if not user_groups and not has_direct_assignment and not has_group_assignment:
                orphaned_users.append(user.username)

        # Find orphaned groups (groups with no members and no assignments)
        orphaned_groups = []
        for group in data.groups.groups:
            group_members = data.groups.memberships.get(group.group_id, [])
            has_assignment = group.group_id in group_assignments

            if not group_members and not has_assignment:
                orphaned_groups.append(group.display_name)

        # Find unused permission sets (permission sets with no assignments)
        assigned_permission_sets = set()
        for assignment in data.assignments.assignments:
            assigned_permission_sets.add(assignment.permission_set_arn)

        unused_permission_sets = []
        for ps in data.permission_sets.permission_sets:
            if ps.permission_set_arn not in assigned_permission_sets:
                unused_permission_sets.append(ps.name)

        # Find unassigned accounts (accounts with no assignments)
        assigned_accounts = set()
        for assignment in data.assignments.assignments:
            assigned_accounts.add(assignment.account_id)

        unassigned_accounts = []
        for account in data.accounts.accounts:
            if account.account_id not in assigned_accounts:
                unassigned_accounts.append(account.account_name)

        return OrphanedResources(
            orphaned_users=orphaned_users,
            orphaned_groups=orphaned_groups,
            unused_permission_sets=unused_permission_sets,
            unassigned_accounts=unassigned_accounts,
        )

    def detect_privileged_access(
        self, permission_sets: List["PermissionSetData"]
    ) -> "PrivilegedAccessReport":
        """Detect privileged access patterns.

        Args:
            permission_sets: Permission set data

        Returns:
            Privileged access report
        """
        from .models import PrivilegedAccessReport, PrivilegePattern

        # Define patterns for admin/privileged policies
        admin_policy_patterns = [
            "AdministratorAccess",
            "PowerUserAccess",
            "IAMFullAccess",
            "SecurityAudit",
            "SystemAdministrator",
        ]

        high_privilege_patterns = ["FullAccess", "Admin", "Root", "Super", "Master"]

        admin_permission_sets = []
        high_privilege_patterns_found = []

        for ps in permission_sets:
            is_admin = False
            privilege_patterns = []

            # Check managed policies for admin access
            for policy_arn in ps.managed_policies:
                policy_name = policy_arn.split("/")[-1] if "/" in policy_arn else policy_arn

                # Check for exact admin policy matches
                if any(pattern in policy_name for pattern in admin_policy_patterns):
                    is_admin = True
                    privilege_patterns.append(f"Admin managed policy: {policy_name}")

                # Check for high privilege patterns
                elif any(
                    pattern.lower() in policy_name.lower() for pattern in high_privilege_patterns
                ):
                    privilege_patterns.append(f"High privilege managed policy: {policy_name}")

            # Check customer managed policies
            for policy_ref in ps.customer_managed_policies:
                policy_name = policy_ref.get("Name", "")
                if any(
                    pattern.lower() in policy_name.lower()
                    for pattern in admin_policy_patterns + high_privilege_patterns
                ):
                    privilege_patterns.append(f"High privilege customer policy: {policy_name}")

            # Check inline policy for admin-like permissions
            if ps.inline_policy:
                inline_lower = ps.inline_policy.lower()
                suspicious_patterns = ["*", '"*"', 'effect": "allow"', 'resource": "*"']

                if any(pattern in inline_lower for pattern in suspicious_patterns):
                    # Look for broad permissions
                    if '"action": "*"' in inline_lower or '"action":["*"]' in inline_lower:
                        is_admin = True
                        privilege_patterns.append("Inline policy with wildcard actions")
                    elif "admin" in inline_lower or "full" in inline_lower:
                        privilege_patterns.append("Inline policy with admin-like permissions")

            if is_admin:
                admin_permission_sets.append(ps.name)

            if privilege_patterns:
                pattern = PrivilegePattern(
                    pattern_type="permission_set_privilege",
                    description=f"Permission set '{ps.name}' contains privileged policies",
                    affected_entities=[ps.name],
                    risk_level="HIGH" if is_admin else "MEDIUM",
                )
                high_privilege_patterns_found.append(pattern)

        # For now, return empty dicts for accounts and users as we need assignment data
        # This will be enhanced when called with full context
        return PrivilegedAccessReport(
            admin_permission_sets=admin_permission_sets,
            accounts_with_admin_access={},
            users_with_admin_access=[],
            high_privilege_patterns=high_privilege_patterns_found,
        )

    def generate_access_matrix(self, data: "RawStatisticsData") -> "AccessMatrix":
        """Generate access matrix showing who has access to what.

        Args:
            data: Raw statistics data

        Returns:
            Access matrix
        """
        from collections import defaultdict

        from .models import AccessMatrix

        # Initialize matrices
        user_to_accounts: Dict[str, List[str]] = defaultdict(list)
        user_to_permission_sets: Dict[str, List[str]] = defaultdict(list)
        group_to_accounts: Dict[str, List[str]] = defaultdict(list)
        group_to_permission_sets: Dict[str, List[str]] = defaultdict(list)
        account_to_users: Dict[str, List[str]] = defaultdict(list)
        account_to_groups: Dict[str, List[str]] = defaultdict(list)

        # Build direct assignment relationships
        for assignment in data.assignments.assignments:
            account_id = assignment.account_id
            permission_set_arn = assignment.permission_set_arn
            principal_id = assignment.principal_id
            principal_type = assignment.principal_type

            if principal_type == "USER":
                # User direct assignments
                if account_id not in user_to_accounts[principal_id]:
                    user_to_accounts[principal_id].append(account_id)
                if permission_set_arn not in user_to_permission_sets[principal_id]:
                    user_to_permission_sets[principal_id].append(permission_set_arn)
                if principal_id not in account_to_users[account_id]:
                    account_to_users[account_id].append(principal_id)

            elif principal_type == "GROUP":
                # Group assignments
                if account_id not in group_to_accounts[principal_id]:
                    group_to_accounts[principal_id].append(account_id)
                if permission_set_arn not in group_to_permission_sets[principal_id]:
                    group_to_permission_sets[principal_id].append(permission_set_arn)
                if principal_id not in account_to_groups[account_id]:
                    account_to_groups[account_id].append(principal_id)

                # Add group members to user access (indirect access)
                group_members = data.groups.memberships.get(principal_id, [])
                for user_id in group_members:
                    if account_id not in user_to_accounts[user_id]:
                        user_to_accounts[user_id].append(account_id)
                    if permission_set_arn not in user_to_permission_sets[user_id]:
                        user_to_permission_sets[user_id].append(permission_set_arn)
                    if user_id not in account_to_users[account_id]:
                        account_to_users[account_id].append(user_id)

        # Convert defaultdicts to regular dicts
        return AccessMatrix(
            user_to_accounts=dict(user_to_accounts),
            user_to_permission_sets=dict(user_to_permission_sets),
            group_to_accounts=dict(group_to_accounts),
            group_to_permission_sets=dict(group_to_permission_sets),
            account_to_users=dict(account_to_users),
            account_to_groups=dict(account_to_groups),
        )

    def compare_with_historical(self, current: Any, historical: Any) -> "TrendAnalysis":
        """Compare current data with historical snapshots.

        Args:
            current: Current data
            historical: Historical data

        Returns:
            Trend analysis
        """
        from .models import GrowthMetric, SignificantChange, TrendAnalysis

        if not historical:
            # No historical data available
            return TrendAnalysis(
                user_growth=GrowthMetric(
                    current_count=0, previous_count=0, growth_rate=0.0, absolute_change=0
                ),
                group_growth=GrowthMetric(
                    current_count=0, previous_count=0, growth_rate=0.0, absolute_change=0
                ),
                permission_set_growth=GrowthMetric(
                    current_count=0, previous_count=0, growth_rate=0.0, absolute_change=0
                ),
                assignment_growth=GrowthMetric(
                    current_count=0, previous_count=0, growth_rate=0.0, absolute_change=0
                ),
                significant_changes=[],
            )

        # Extract counts from current and historical data
        current_users = (
            len(current.users.users)
            if hasattr(current, "users") and hasattr(current.users, "users")
            else 0
        )
        current_groups = (
            len(current.groups.groups)
            if hasattr(current, "groups") and hasattr(current.groups, "groups")
            else 0
        )
        current_permission_sets = (
            len(current.permission_sets.permission_sets)
            if hasattr(current, "permission_sets")
            and hasattr(current.permission_sets, "permission_sets")
            else 0
        )
        current_assignments = (
            len(current.assignments.assignments)
            if hasattr(current, "assignments") and hasattr(current.assignments, "assignments")
            else 0
        )

        historical_users = (
            len(historical.users.users)
            if hasattr(historical, "users") and hasattr(historical.users, "users")
            else 0
        )
        historical_groups = (
            len(historical.groups.groups)
            if hasattr(historical, "groups") and hasattr(historical.groups, "groups")
            else 0
        )
        historical_permission_sets = (
            len(historical.permission_sets.permission_sets)
            if hasattr(historical, "permission_sets")
            and hasattr(historical.permission_sets, "permission_sets")
            else 0
        )
        historical_assignments = (
            len(historical.assignments.assignments)
            if hasattr(historical, "assignments") and hasattr(historical.assignments, "assignments")
            else 0
        )

        # Calculate growth metrics
        def calculate_growth(current_count: int, previous_count: int) -> GrowthMetric:
            absolute_change = current_count - previous_count
            if previous_count > 0:
                growth_rate = (absolute_change / previous_count) * 100
            elif previous_count == 0 and current_count > 0:
                # Special case: growth from zero is 100%
                growth_rate = 100.0
            elif previous_count == 0 and current_count == 0:
                # No change from zero
                growth_rate = 0.0
            else:
                # current_count == 0 and previous_count > 0 (decline to zero)
                growth_rate = -100.0

            return GrowthMetric(
                current_count=current_count,
                previous_count=previous_count,
                growth_rate=growth_rate,
                absolute_change=absolute_change,
            )

        user_growth = calculate_growth(current_users, historical_users)
        group_growth = calculate_growth(current_groups, historical_groups)
        permission_set_growth = calculate_growth(
            current_permission_sets, historical_permission_sets
        )
        assignment_growth = calculate_growth(current_assignments, historical_assignments)

        # Identify significant changes (threshold: >20% change or >10 absolute change)
        significant_changes = []

        def check_significant_change(metric: GrowthMetric, category: str) -> None:
            if abs(metric.growth_rate) > 20 or abs(metric.absolute_change) > 10:
                direction = "increased" if metric.absolute_change > 0 else "decreased"
                impact = "HIGH" if abs(metric.growth_rate) > 50 else "MEDIUM"

                change = SignificantChange(
                    category=category,
                    description=f"{category.title()} count {direction} by {abs(metric.absolute_change)} ({abs(metric.growth_rate):.1f}%)",
                    impact=impact,
                    change_magnitude=abs(metric.growth_rate),
                )
                significant_changes.append(change)

        check_significant_change(user_growth, "users")
        check_significant_change(group_growth, "groups")
        check_significant_change(permission_set_growth, "permission_sets")
        check_significant_change(assignment_growth, "assignments")

        return TrendAnalysis(
            user_growth=user_growth,
            group_growth=group_growth,
            permission_set_growth=permission_set_growth,
            assignment_growth=assignment_growth,
            significant_changes=significant_changes,
        )

    def analyze_user_patterns(self, data: "UserStatistics") -> "UserAnalysis":
        """Analyze user patterns and identify insights.

        Args:
            data: User statistics data

        Returns:
            User analysis result
        """
        from .models import GroupStatistics, UserAnalysis

        # Create a mock GroupStatistics for metrics calculation
        # In real usage, this would be passed separately
        groups_data = GroupStatistics(
            groups=[], memberships={}, collection_timestamp=data.collection_timestamp
        )

        # Calculate metrics
        metrics = self.calculate_user_group_metrics(data, groups_data, None)

        # Generate insights
        insights = []
        recommendations = []

        # Analyze user distribution
        if metrics.total_users == 0:
            insights.append("No users found in the Identity Center instance")
            recommendations.append("Consider adding users to the Identity Center instance")
        else:
            insights.append(f"Total of {metrics.total_users} users in the system")

            # Analyze group membership patterns
            users_without_groups = len(metrics.orphaned_users)
            if users_without_groups > 0:
                percentage = (users_without_groups / metrics.total_users) * 100
                insights.append(
                    f"{users_without_groups} users ({percentage:.1f}%) have no group membership"
                )
                if percentage > 20:
                    recommendations.append(
                        "Consider organizing users into groups for better access management"
                    )

            # Analyze group membership distribution
            if metrics.groups_per_user:
                avg_groups = sum(metrics.groups_per_user.values()) / len(metrics.groups_per_user)
                insights.append(f"Average groups per user: {avg_groups:.1f}")

                # Find users with many groups
                high_group_users = [
                    (user_id, count)
                    for user_id, count in metrics.groups_per_user.items()
                    if count > 5
                ]
                if high_group_users:
                    insights.append(f"{len(high_group_users)} users belong to more than 5 groups")
                    recommendations.append(
                        "Review users with many group memberships for potential over-privilege"
                    )

        return UserAnalysis(metrics=metrics, insights=insights, recommendations=recommendations)

    def analyze_permission_usage(self, data: "PermissionSetStatistics") -> "PermissionAnalysis":
        """Analyze permission set usage patterns.

        Args:
            data: Permission set statistics data

        Returns:
            Permission analysis result
        """
        from .models import PermissionAnalysis

        # Calculate metrics (need assignments data, so create empty list for now)
        metrics = self.calculate_permission_set_metrics(data.permission_sets, [])

        # Generate insights
        insights = []
        recommendations = []

        if metrics.total_permission_sets == 0:
            insights.append("No permission sets found in the Identity Center instance")
            recommendations.append("Create permission sets to manage access to AWS accounts")
        else:
            insights.append(f"Total of {metrics.total_permission_sets} permission sets defined")

            # Analyze unused permission sets
            unused_count = len(metrics.unused_permission_sets)
            if unused_count > 0:
                percentage = (unused_count / metrics.total_permission_sets) * 100
                insights.append(
                    f"{unused_count} permission sets ({percentage:.1f}%) are not assigned to any accounts"
                )
                if percentage > 30:
                    recommendations.append(
                        "Consider removing unused permission sets to reduce complexity"
                    )

            # Analyze privileged permission sets
            privileged_count = len(metrics.privileged_permission_sets)
            if privileged_count > 0:
                percentage = (privileged_count / metrics.total_permission_sets) * 100
                insights.append(
                    f"{privileged_count} permission sets ({percentage:.1f}%) contain privileged policies"
                )
                recommendations.append(
                    "Review privileged permission sets for least privilege compliance"
                )

            # Analyze assignment distribution
            if metrics.most_assigned_permission_sets:
                top_ps_name, top_ps_count = metrics.most_assigned_permission_sets[0]
                insights.append(
                    f"Most assigned permission set: '{top_ps_name}' with {top_ps_count} assignments"
                )

                if top_ps_count > metrics.average_assignments_per_permission_set * 3:
                    recommendations.append(
                        "Consider splitting heavily used permission sets for better granularity"
                    )

        return PermissionAnalysis(
            metrics=metrics, insights=insights, recommendations=recommendations
        )

    def analyze_governance_gaps(self, data: Dict[str, Any]) -> "GovernanceAnalysis":
        """Analyze governance gaps and compliance issues.

        Args:
            data: Combined statistics data

        Returns:
            Governance analysis result
        """
        from .models import (
            AccessMatrix,
            ComplianceGap,
            EmptyMappings,
            GovernanceAnalysis,
            GovernanceView,
            PrivilegedAccessReport,
        )

        # Extract raw data if provided
        raw_data = data.get("raw_data")
        if not raw_data:
            # Create minimal governance view if no data provided
            empty_matrix = AccessMatrix(
                user_to_accounts={},
                user_to_permission_sets={},
                group_to_accounts={},
                group_to_permission_sets={},
                account_to_users={},
                account_to_groups={},
            )
            empty_privileged = PrivilegedAccessReport(
                admin_permission_sets=[],
                accounts_with_admin_access={},
                users_with_admin_access=[],
                high_privilege_patterns=[],
            )
            empty_mappings = EmptyMappings(
                groups_with_no_members=[],
                permission_sets_with_no_assignments=[],
                accounts_with_no_assignments=[],
            )

            view = GovernanceView(
                access_matrix=empty_matrix,
                privileged_access_report=empty_privileged,
                empty_mappings=empty_mappings,
                compliance_gaps=[],
            )

            return GovernanceAnalysis(
                view=view,
                insights=["No data available for governance analysis"],
                recommendations=["Collect statistics data to perform governance analysis"],
            )

        # Generate access matrix
        access_matrix = self.generate_access_matrix(raw_data)

        # Detect privileged access
        privileged_access = self.detect_privileged_access(raw_data.permission_sets.permission_sets)

        # Enhance privileged access report with assignment context
        admin_ps_arns = set()
        ps_name_to_arn = {
            ps.name: ps.permission_set_arn for ps in raw_data.permission_sets.permission_sets
        }

        for ps_name in privileged_access.admin_permission_sets:
            ps_arn = ps_name_to_arn.get(ps_name)
            if ps_arn:
                admin_ps_arns.add(ps_arn)

        # Find accounts with admin access
        accounts_with_admin_access: Dict[str, List[str]] = {}
        users_with_admin_access = set()

        for assignment in raw_data.assignments.assignments:
            if assignment.permission_set_arn in admin_ps_arns:
                account_id = assignment.account_id
                if account_id not in accounts_with_admin_access:
                    accounts_with_admin_access[account_id] = []

                if assignment.principal_type == "USER":
                    # Find user name
                    user_name = assignment.principal_id
                    for user in raw_data.users.users:
                        if user.user_id == assignment.principal_id:
                            user_name = user.username
                            break
                    accounts_with_admin_access[account_id].append(f"User: {user_name}")
                    users_with_admin_access.add(user_name)

                elif assignment.principal_type == "GROUP":
                    # Find group name
                    group_name = assignment.principal_id
                    for group in raw_data.groups.groups:
                        if group.group_id == assignment.principal_id:
                            group_name = group.display_name
                            break
                    accounts_with_admin_access[account_id].append(f"Group: {group_name}")

                    # Add group members to users with admin access
                    group_members = raw_data.groups.memberships.get(assignment.principal_id, [])
                    for user_id in group_members:
                        for user in raw_data.users.users:
                            if user.user_id == user_id:
                                users_with_admin_access.add(user.username)
                                break

        # Update privileged access report
        privileged_access.accounts_with_admin_access = accounts_with_admin_access
        privileged_access.users_with_admin_access = list(users_with_admin_access)

        # Detect empty mappings
        orphaned_resources = self.detect_orphaned_resources(raw_data)
        empty_mappings = EmptyMappings(
            groups_with_no_members=orphaned_resources.orphaned_groups,
            permission_sets_with_no_assignments=orphaned_resources.unused_permission_sets,
            accounts_with_no_assignments=orphaned_resources.unassigned_accounts,
        )

        # Identify compliance gaps
        compliance_gaps = []

        # Gap: Users with no group membership
        if orphaned_resources.orphaned_users:
            gap = ComplianceGap(
                gap_type="user_organization",
                description=f"{len(orphaned_resources.orphaned_users)} users have no group membership",
                affected_resources=orphaned_resources.orphaned_users,
                severity="MEDIUM",
            )
            compliance_gaps.append(gap)

        # Gap: Excessive admin access
        if (
            len(users_with_admin_access) > len(raw_data.users.users) * 0.1
        ):  # More than 10% have admin
            gap = ComplianceGap(
                gap_type="excessive_privilege",
                description=f"{len(users_with_admin_access)} users have administrative access",
                affected_resources=list(users_with_admin_access),
                severity="HIGH",
            )
            compliance_gaps.append(gap)

        # Gap: Unused resources
        if len(orphaned_resources.unused_permission_sets) > 0:
            gap = ComplianceGap(
                gap_type="resource_waste",
                description=f"{len(orphaned_resources.unused_permission_sets)} permission sets are unused",
                affected_resources=orphaned_resources.unused_permission_sets,
                severity="LOW",
            )
            compliance_gaps.append(gap)

        # Create governance view
        governance_view = GovernanceView(
            access_matrix=access_matrix,
            privileged_access_report=privileged_access,
            empty_mappings=empty_mappings,
            compliance_gaps=compliance_gaps,
        )

        # Generate insights and recommendations
        insights = []
        recommendations = []

        insights.append(
            f"Access matrix covers {len(access_matrix.user_to_accounts)} users and {len(access_matrix.account_to_users)} accounts"
        )

        if privileged_access.admin_permission_sets:
            insights.append(
                f"{len(privileged_access.admin_permission_sets)} permission sets contain administrative privileges"
            )
            recommendations.append(
                "Review administrative permission sets for least privilege compliance"
            )

        if compliance_gaps:
            insights.append(
                f"Identified {len(compliance_gaps)} compliance gaps requiring attention"
            )
            high_severity_gaps = [gap for gap in compliance_gaps if gap.severity == "HIGH"]
            if high_severity_gaps:
                recommendations.append("Address high-severity compliance gaps immediately")

        if empty_mappings.groups_with_no_members:
            insights.append(f"{len(empty_mappings.groups_with_no_members)} groups have no members")
            recommendations.append("Consider removing empty groups to reduce complexity")

        return GovernanceAnalysis(
            view=governance_view, insights=insights, recommendations=recommendations
        )

    def compare_historical_data(self, current: Any, historical: Any) -> "TrendAnalysis":
        """Compare current data with historical snapshots.

        Args:
            current: Current data
            historical: Historical data

        Returns:
            Trend analysis
        """
        # Delegate to the main comparison method
        return self.compare_with_historical(current, historical)

    def calculate_assignment_patterns_with_trend(
        self, current_assignments: List["AssignmentData"], historical_data: Any = None
    ) -> "AssignmentPatterns":
        """Calculate assignment patterns with historical trend analysis.

        Args:
            current_assignments: Current assignment data
            historical_data: Historical data for trend analysis

        Returns:
            Assignment patterns with trend data
        """
        from .models import TrendData

        # Get base assignment patterns
        patterns = self.calculate_assignment_patterns(current_assignments)

        if historical_data and hasattr(historical_data, "assignments"):
            # Calculate trend data
            current_count = len(current_assignments)
            historical_assignments = (
                historical_data.assignments.assignments
                if hasattr(historical_data.assignments, "assignments")
                else []
            )
            historical_count = len(historical_assignments)

            # Simple trend calculation (would be enhanced with multiple time periods)
            if historical_count > 0:
                growth_rate = ((current_count - historical_count) / historical_count) * 100

                if growth_rate > 10:
                    trend_direction = "increasing"
                elif growth_rate < -10:
                    trend_direction = "decreasing"
                else:
                    trend_direction = "stable"

                # Create simple trend data with two time periods
                patterns.assignment_growth_trend = TrendData(
                    time_periods=["Previous", "Current"],
                    values=[historical_count, current_count],
                    trend_direction=trend_direction,
                )

        return patterns

    def calculate_governance_view(self, data: "RawStatisticsData") -> "GovernanceView":
        """Calculate governance view for the raw statistics data.

        Args:
            data: Raw statistics data

        Returns:
            Governance view analysis
        """
        from .models import GovernanceView

        # Generate access matrix
        access_matrix = self.generate_access_matrix(data)

        # Detect privileged access
        privileged_access = self.detect_privileged_access(data.permission_sets.permission_sets)

        # Enhance privileged access report with assignment context
        admin_ps_arns = set()
        ps_name_to_arn = {
            ps.name: ps.permission_set_arn for ps in data.permission_sets.permission_sets
        }

        for ps_name in privileged_access.admin_permission_sets:
            ps_arn = ps_name_to_arn.get(ps_name)
            if ps_arn:
                admin_ps_arns.add(ps_arn)

        # Find accounts with admin access
        accounts_with_admin_access: Dict[str, List[str]] = {}
        users_with_admin_access = set()

        for assignment in data.assignments.assignments:
            if assignment.permission_set_arn in admin_ps_arns:
                account_id = assignment.account_id
                if account_id not in accounts_with_admin_access:
                    accounts_with_admin_access[account_id] = []

                if assignment.principal_type == "USER":
                    # Find user name
                    user_name = assignment.principal_id
                    for user in data.users.users:
                        if user.user_id == assignment.principal_id:
                            user_name = user.username
                            break
                    accounts_with_admin_access[account_id].append(f"User: {user_name}")
                    users_with_admin_access.add(user_name)

                elif assignment.principal_type == "GROUP":
                    # Find group name
                    group_name = assignment.principal_id
                    for group in data.groups.groups:
                        if group.group_id == assignment.principal_id:
                            group_name = group.display_name
                            break
                    accounts_with_admin_access[account_id].append(f"Group: {group_name}")

                    # Add group members to users with admin access
                    group_members = data.groups.memberships.get(assignment.principal_id, [])
                    for user_id in group_members:
                        for user in data.users.users:
                            if user.user_id == user_id:
                                users_with_admin_access.add(user.username)
                                break

        # Update privileged access report
        privileged_access.accounts_with_admin_access = accounts_with_admin_access
        privileged_access.users_with_admin_access = list(users_with_admin_access)

        # Detect empty mappings
        orphaned_resources = self.detect_orphaned_resources(data)

        from .models import EmptyMappings

        empty_mappings = EmptyMappings(
            groups_with_no_members=orphaned_resources.orphaned_groups,
            permission_sets_with_no_assignments=orphaned_resources.unused_permission_sets,
            accounts_with_no_assignments=orphaned_resources.unassigned_accounts,
        )

        # Identify compliance gaps
        from .models import ComplianceGap

        compliance_gaps = []

        # Gap: Users with no group membership
        if orphaned_resources.orphaned_users:
            gap = ComplianceGap(
                gap_type="user_organization",
                description=f"{len(orphaned_resources.orphaned_users)} users have no group membership",
                affected_resources=orphaned_resources.orphaned_users,
                severity="MEDIUM",
            )
            compliance_gaps.append(gap)

        # Gap: Excessive admin access
        if len(users_with_admin_access) > len(data.users.users) * 0.1:  # More than 10% have admin
            gap = ComplianceGap(
                gap_type="excessive_privilege",
                description=f"{len(users_with_admin_access)} users have administrative access",
                affected_resources=list(users_with_admin_access),
                severity="HIGH",
            )
            compliance_gaps.append(gap)

        # Gap: Unused resources
        if len(orphaned_resources.unused_permission_sets) > 0:
            gap = ComplianceGap(
                gap_type="resource_waste",
                description=f"{len(orphaned_resources.unused_permission_sets)} permission sets are unused",
                affected_resources=orphaned_resources.unused_permission_sets,
                severity="LOW",
            )
            compliance_gaps.append(gap)

        # Create governance view
        return GovernanceView(
            access_matrix=access_matrix,
            privileged_access_report=privileged_access,
            empty_mappings=empty_mappings,
            compliance_gaps=compliance_gaps,
        )
