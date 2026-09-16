"""Statistics data collector for gathering data from AWS Identity Center APIs."""

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from botocore.exceptions import ClientError

from ..aws_clients.manager import AWSClientManager

if TYPE_CHECKING:
    from .models import (
        AccountData,
        AccountStatistics,
        AssignmentData,
        AssignmentStatistics,
        GroupData,
        GroupStatistics,
        PermissionSetData,
        PermissionSetStatistics,
        RawStatisticsData,
        UserData,
        UserStatistics,
    )

logger = logging.getLogger(__name__)


class StatisticsCollector:
    """Collects raw data from AWS Identity Center APIs."""

    def __init__(self, client_manager: AWSClientManager, instance_arn: str):
        """Initialize the statistics collector.

        Args:
            client_manager: AWS client manager for API access
            instance_arn: Identity Center instance ARN
        """
        self.client_manager = client_manager
        self.instance_arn = instance_arn
        self.cache_enabled = client_manager.is_caching_enabled()

    async def collect_all_data(self) -> "RawStatisticsData":
        """Collect all required data for statistics generation.

        Returns:
            Raw statistics data container
        """
        from .models import RawStatisticsData

        logger.info("Starting comprehensive data collection for statistics")
        collection_start = datetime.now()

        try:
            # Validate AWS permissions first
            await self._validate_aws_permissions()

            # Collect all data types concurrently for better performance
            tasks = [
                self.collect_user_statistics(),
                self.collect_group_statistics(),
                self.collect_permission_set_statistics(),
                self.collect_account_statistics(),
                self.collect_assignment_statistics(),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results and handle any exceptions
            from .models import (
                AccountStatistics,
                AssignmentStatistics,
                GroupStatistics,
                PermissionSetStatistics,
                UserStatistics,
            )

            (
                users_result,
                groups_result,
                permission_sets_result,
                accounts_result,
                assignments_result,
            ) = results

            # Check for exceptions and handle gracefully
            exceptions = [r for r in results if isinstance(r, Exception)]
            if exceptions:
                logger.warning(
                    f"Some data collection operations failed: {len(exceptions)} exceptions"
                )
                for exc in exceptions:
                    logger.error(f"Collection error: {exc}")

                # If too many operations failed, raise an exception
                if len(exceptions) >= 3:  # More than half failed
                    raise Exception(f"Too many collection operations failed: {len(exceptions)}/5")

            # Use empty data for failed collections
            if isinstance(users_result, Exception):
                logger.error("User collection failed, using empty data")
                users = UserStatistics(
                    users=[], group_memberships={}, collection_timestamp=collection_start
                )
            else:
                users = users_result  # type: ignore[assignment]

            if isinstance(groups_result, Exception):
                logger.error("Group collection failed, using empty data")
                groups = GroupStatistics(
                    groups=[], memberships={}, collection_timestamp=collection_start
                )
            else:
                groups = groups_result  # type: ignore[assignment]

            if isinstance(permission_sets_result, Exception):
                logger.error("Permission set collection failed, using empty data")
                permission_sets = PermissionSetStatistics(
                    permission_sets=[], collection_timestamp=collection_start
                )
            else:
                permission_sets = permission_sets_result  # type: ignore[assignment]

            if isinstance(accounts_result, Exception):
                logger.error("Account collection failed, using empty data")
                accounts = AccountStatistics(accounts=[], collection_timestamp=collection_start)
            else:
                accounts = accounts_result  # type: ignore[assignment]

            if isinstance(assignments_result, Exception):
                logger.error("Assignment collection failed, using empty data")
                assignments = AssignmentStatistics(
                    assignments=[], collection_timestamp=collection_start
                )
            else:
                assignments = assignments_result  # type: ignore[assignment]

            # Log collection metrics
            self._log_collection_metrics(
                "all_data",
                collection_start,
                len(users.users)
                + len(groups.groups)
                + len(permission_sets.permission_sets)
                + len(accounts.accounts)
                + len(assignments.assignments),
            )

            return RawStatisticsData(
                users=users,
                groups=groups,
                permission_sets=permission_sets,
                accounts=accounts,
                assignments=assignments,
            )

        except Exception as e:
            logger.error(f"Failed to collect all statistics data: {e}")
            raise

    async def collect_user_statistics(self) -> "UserStatistics":
        """Collect user-related statistics from Identity Center.

        Returns:
            User statistics data
        """
        from .models import UserStatistics

        logger.info("Starting user statistics collection")
        collection_start = datetime.now()

        try:
            # Get Identity Store client for user operations
            identity_store_client = self.client_manager.get_identity_store_client()

            # Extract identity store ID from instance ARN
            identity_store_id = self._extract_identity_store_id()

            # Collect users with pagination and caching
            users = await self._get_from_cache_or_execute(
                "users",
                lambda: self._collect_users_paginated(identity_store_client, identity_store_id),
                ttl_minutes=10,
                identity_store_id=identity_store_id,
            )

            # Collect group memberships for all users
            # Note: We'll derive this from group statistics instead of making separate API calls
            # to avoid API issues and improve performance
            group_memberships: Dict[str, List[str]] = {}  # Will be populated from group statistics

            logger.info(f"Collected {len(users)} users with group memberships")

            return UserStatistics(
                users=users,
                group_memberships=group_memberships,
                collection_timestamp=collection_start,
            )

        except Exception as e:
            logger.error(f"Failed to collect user statistics: {e}")
            raise

    async def collect_group_statistics(self) -> "GroupStatistics":
        """Collect group-related statistics from Identity Center.

        Returns:
            Group statistics data
        """
        from .models import GroupStatistics

        logger.info("Starting group statistics collection")
        collection_start = datetime.now()

        try:
            # Get Identity Store client for group operations
            identity_store_client = self.client_manager.get_identity_store_client()

            # Extract identity store ID from instance ARN
            identity_store_id = self._extract_identity_store_id()

            # Collect groups with pagination and caching
            groups = await self._get_from_cache_or_execute(
                "groups",
                lambda: self._collect_groups_paginated(identity_store_client, identity_store_id),
                ttl_minutes=10,
                identity_store_id=identity_store_id,
            )

            # Collect group memberships for all groups
            memberships = await self._collect_group_memberships(
                identity_store_client, identity_store_id, groups
            )

            logger.info(f"Collected {len(groups)} groups with memberships")

            return GroupStatistics(
                groups=groups, memberships=memberships, collection_timestamp=collection_start
            )

        except Exception as e:
            logger.error(f"Failed to collect group statistics: {e}")
            raise

    async def collect_permission_set_statistics(self) -> "PermissionSetStatistics":
        """Collect permission set statistics from Identity Center.

        Returns:
            Permission set statistics data
        """
        from .models import PermissionSetStatistics

        logger.info("Starting permission set statistics collection")
        collection_start = datetime.now()

        try:
            # Get Identity Center client for permission set operations
            identity_center_client = self.client_manager.get_identity_center_client()

            # Collect permission sets with pagination (temporarily disable caching)
            permission_sets = await self._collect_permission_sets_paginated(identity_center_client)

            # Collect detailed information for each permission set (temporarily disable caching)
            detailed_permission_sets = await self._collect_permission_set_details(
                identity_center_client, permission_sets
            )

            logger.info(f"Collected {len(detailed_permission_sets)} permission sets with details")

            return PermissionSetStatistics(
                permission_sets=detailed_permission_sets, collection_timestamp=collection_start
            )

        except Exception as e:
            logger.error(f"Failed to collect permission set statistics: {e}")
            raise

    async def collect_account_statistics(self) -> "AccountStatistics":
        """Collect account statistics from Organizations and Identity Center.

        Returns:
            Account statistics data
        """
        from .models import AccountStatistics

        logger.info("Starting account statistics collection")
        collection_start = datetime.now()

        try:
            # Get Organizations client for account operations
            organizations_client = self.client_manager.get_organizations_client()

            # Collect accounts with parallel processing and caching
            accounts = await self._get_from_cache_or_execute(
                "accounts",
                lambda: self._collect_accounts_parallel(organizations_client),
                ttl_minutes=30,  # Accounts change less frequently
            )

            logger.info(f"Collected {len(accounts)} accounts")

            return AccountStatistics(accounts=accounts, collection_timestamp=collection_start)

        except Exception as e:
            logger.error(f"Failed to collect account statistics: {e}")
            raise

    async def collect_assignment_statistics(self) -> "AssignmentStatistics":
        """Collect assignment statistics from Identity Center.

        Returns:
            Assignment statistics data
        """
        from .models import AssignmentStatistics

        logger.info("Starting assignment statistics collection")
        collection_start = datetime.now()

        try:
            # Get Identity Center client for assignment operations
            identity_center_client = self.client_manager.get_identity_center_client()

            # Collect assignments with caching
            assignments = await self._get_from_cache_or_execute(
                "assignments",
                lambda: self._collect_all_assignments(identity_center_client),
                ttl_minutes=10,  # Assignments change more frequently
            )

            logger.info(f"Collected {len(assignments)} assignments")

            return AssignmentStatistics(
                assignments=assignments, collection_timestamp=collection_start
            )

        except Exception as e:
            logger.error(f"Failed to collect assignment statistics: {e}")
            raise

    def get_historical_data(self, backup_path: str) -> Optional["RawStatisticsData"]:
        """Load historical data from backup snapshots.

        Args:
            backup_path: Path to backup data

        Returns:
            Historical raw statistics data if available
        """
        import json
        import os
        from datetime import datetime

        from .models import (
            AccountData,
            AccountStatistics,
            AssignmentData,
            AssignmentStatistics,
            GroupData,
            GroupStatistics,
            PermissionSetData,
            PermissionSetStatistics,
            RawStatisticsData,
            UserData,
            UserStatistics,
        )

        try:
            if not os.path.exists(backup_path):
                logger.warning(f"Backup path does not exist: {backup_path}")
                return None

            # Try to load as JSON file first
            if os.path.isfile(backup_path) and backup_path.endswith(".json"):
                with open(backup_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                # Assume it's a directory with backup files
                data = {}

                # Try to load individual component files
                individual_files = {
                    "users": "users.json",
                    "groups": "groups.json",
                    "permission_sets": "permission_sets.json",
                    "accounts": "accounts.json",
                    "assignments": "assignments.json",
                }

                found_files = False
                for key, filename in individual_files.items():
                    file_path = os.path.join(backup_path, filename)
                    if os.path.exists(file_path):
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                data[key] = json.load(f)
                            found_files = True
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse {filename}: {e}")
                            data[key] = {}
                    else:
                        data[key] = {}

                # If no individual files found, try statistics_backup.json
                if not found_files:
                    backup_file = os.path.join(backup_path, "statistics_backup.json")
                    if os.path.exists(backup_file):
                        with open(backup_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                    else:
                        logger.warning(f"No statistics backup found in: {backup_path}")
                        return None

            # Parse the backup data into our models
            # This assumes the backup has a specific structure
            users_data = data.get("users", {})
            groups_data = data.get("groups", {})
            permission_sets_data = data.get("permission_sets", {})
            accounts_data = data.get("accounts", {})
            assignments_data = data.get("assignments", {})

            # Convert to our data models
            users = [
                UserData(
                    user_id=user.get("user_id", ""),
                    username=user.get("username", ""),
                    display_name=user.get("display_name"),
                    email=user.get("email"),
                    active=user.get("active", True),
                )
                for user in users_data.get("users", [])
            ]

            groups = [
                GroupData(
                    group_id=group.get("group_id", ""),
                    display_name=group.get("display_name", ""),
                    description=group.get("description"),
                )
                for group in groups_data.get("groups", [])
            ]

            permission_sets = [
                PermissionSetData(
                    permission_set_arn=ps.get("permission_set_arn", ""),
                    name=ps.get("name", ""),
                    description=ps.get("description"),
                    session_duration=ps.get("session_duration"),
                    managed_policies=ps.get("managed_policies", []),
                    customer_managed_policies=ps.get("customer_managed_policies", []),
                    inline_policy=ps.get("inline_policy"),
                )
                for ps in permission_sets_data.get("permission_sets", [])
            ]

            accounts = [
                AccountData(
                    account_id=acc.get("account_id", ""),
                    account_name=acc.get("account_name", ""),
                    email=acc.get("email", ""),
                    status=acc.get("status", "UNKNOWN"),
                )
                for acc in accounts_data.get("accounts", [])
            ]

            assignments = [
                AssignmentData(
                    account_id=assign.get("account_id", ""),
                    permission_set_arn=assign.get("permission_set_arn", ""),
                    principal_type=assign.get("principal_type", ""),
                    principal_id=assign.get("principal_id", ""),
                )
                for assign in assignments_data.get("assignments", [])
            ]

            # Create statistics objects
            current_time = datetime.now()

            user_stats = UserStatistics(
                users=users,
                group_memberships=users_data.get("group_memberships", {}),
                collection_timestamp=current_time,
            )

            group_stats = GroupStatistics(
                groups=groups,
                memberships=groups_data.get("memberships", {}),
                collection_timestamp=current_time,
            )

            ps_stats = PermissionSetStatistics(
                permission_sets=permission_sets, collection_timestamp=current_time
            )

            account_stats = AccountStatistics(accounts=accounts, collection_timestamp=current_time)

            assignment_stats = AssignmentStatistics(
                assignments=assignments, collection_timestamp=current_time
            )

            return RawStatisticsData(
                users=user_stats,
                groups=group_stats,
                permission_sets=ps_stats,
                accounts=account_stats,
                assignments=assignment_stats,
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse backup JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load historical data from {backup_path}: {e}")
            return None

    def _extract_identity_store_id(self) -> str:
        """Extract Identity Store ID from the instance ARN.

        Returns:
            Identity Store ID

        Raises:
            ValueError: If instance ARN format is invalid
        """
        # Instance ARN format: arn:aws:sso:::instance/ssoins-xxxxxxxxxxxxxxxxx
        # Identity Store ID is typically the same as the instance ID
        try:
            # Extract the instance ID from the ARN
            arn_parts = self.instance_arn.split("/")
            if len(arn_parts) < 2:
                raise ValueError(f"Invalid instance ARN format: {self.instance_arn}")

            instance_id = arn_parts[-1]

            # For Identity Store operations, we need to get the actual Identity Store ID
            # This is typically done by calling list_instances and getting the IdentityStoreId
            identity_center_client = self.client_manager.get_identity_center_client()

            try:
                response = identity_center_client.list_instances()
                instances = response.get("Instances", [])

                for instance in instances:
                    if instance.get("InstanceArn") == self.instance_arn:
                        identity_store_id = instance.get("IdentityStoreId", instance_id)
                        return str(identity_store_id)

                # Fallback to instance ID if not found
                logger.warning(
                    f"Could not find Identity Store ID for instance {self.instance_arn}, using instance ID"
                )
                return instance_id

            except Exception as e:
                logger.warning(f"Failed to get Identity Store ID from API: {e}, using instance ID")
                return instance_id

        except Exception as e:
            logger.error(f"Failed to extract Identity Store ID from ARN {self.instance_arn}: {e}")
            raise ValueError(f"Invalid instance ARN format: {self.instance_arn}")

    async def _collect_users_paginated(
        self, identity_store_client: Any, identity_store_id: str
    ) -> List["UserData"]:
        """Collect all users using pagination.

        Args:
            identity_store_client: Identity Store client
            identity_store_id: Identity Store ID

        Returns:
            List of UserData objects
        """
        from .models import UserData, validate_user_data

        users = []
        next_token = None

        try:
            while True:
                # Prepare request parameters
                params = {"IdentityStoreId": identity_store_id}
                if next_token:
                    params["NextToken"] = next_token

                # Make API call with retry logic
                response = await self._retry_with_backoff(
                    lambda: identity_store_client.list_users(**params)
                )

                # Process users from response
                for user_data in response.get("Users", []):
                    try:
                        user = UserData(
                            user_id=user_data.get("UserId", ""),
                            username=user_data.get("UserName", ""),
                            display_name=user_data.get("DisplayName"),
                            email=self._extract_email_from_user(user_data),
                            active=user_data.get("Active", True),
                        )

                        # Validate user data
                        validate_user_data(user)
                        users.append(user)

                    except Exception as e:
                        logger.warning(f"Skipping invalid user data: {e}")
                        continue

                # Check for more pages
                next_token = response.get("NextToken")
                if not next_token:
                    break

                # Add small delay to avoid rate limiting
                await asyncio.sleep(0.1)

        except ClientError as e:
            logger.error(f"AWS API error collecting users: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error collecting users: {e}")
            raise

        return users

    async def _collect_groups_paginated(
        self, identity_store_client: Any, identity_store_id: str
    ) -> List["GroupData"]:
        """Collect all groups using pagination.

        Args:
            identity_store_client: Identity Store client
            identity_store_id: Identity Store ID

        Returns:
            List of GroupData objects
        """
        from .models import GroupData, validate_group_data

        groups = []
        next_token = None

        try:
            while True:
                # Prepare request parameters
                params = {"IdentityStoreId": identity_store_id}
                if next_token:
                    params["NextToken"] = next_token

                # Make API call with retry logic
                response = await self._retry_with_backoff(
                    lambda: identity_store_client.list_groups(**params)
                )

                # Process groups from response
                for group_data in response.get("Groups", []):
                    try:
                        group = GroupData(
                            group_id=group_data.get("GroupId", ""),
                            display_name=group_data.get("DisplayName", ""),
                            description=group_data.get("Description"),
                        )

                        # Validate group data
                        validate_group_data(group)
                        groups.append(group)

                    except Exception as e:
                        logger.warning(f"Skipping invalid group data: {e}")
                        continue

                # Check for more pages
                next_token = response.get("NextToken")
                if not next_token:
                    break

                # Add small delay to avoid rate limiting
                await asyncio.sleep(0.1)

        except ClientError as e:
            logger.error(f"AWS API error collecting groups: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error collecting groups: {e}")
            raise

        return groups

    async def _collect_permission_sets_paginated(self, identity_center_client: Any) -> List[str]:
        """Collect all permission set ARNs using pagination.

        Args:
            identity_center_client: Identity Center client

        Returns:
            List of permission set ARNs
        """
        permission_set_arns = []
        next_token = None

        try:
            while True:
                # Prepare request parameters
                params = {"InstanceArn": self.instance_arn}
                if next_token:
                    params["NextToken"] = next_token

                # Make API call with retry logic
                response = await self._retry_with_backoff(
                    lambda: identity_center_client.list_permission_sets(**params)
                )

                # Collect permission set ARNs
                arns = response.get("PermissionSets", [])
                permission_set_arns.extend(arns)

                # Check for more pages
                next_token = response.get("NextToken")
                if not next_token:
                    break

                # Add small delay to avoid rate limiting
                await asyncio.sleep(0.1)

        except ClientError as e:
            logger.error(f"AWS API error collecting permission sets: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error collecting permission sets: {e}")
            raise

        return permission_set_arns

    async def _collect_permission_set_details(
        self, identity_center_client: Any, permission_set_arns: List[str]
    ) -> List["PermissionSetData"]:
        """Collect detailed information for permission sets.

        Args:
            identity_center_client: Identity Center client
            permission_set_arns: List of permission set ARNs

        Returns:
            List of PermissionSetData objects
        """
        from .models import PermissionSetData, validate_permission_set_data

        permission_sets: List["PermissionSetData"] = []

        # Process permission sets in batches to avoid overwhelming the API
        batch_size = 10
        for i in range(0, len(permission_set_arns), batch_size):
            batch = permission_set_arns[i : i + batch_size]

            # Process batch concurrently
            tasks = [self._get_permission_set_details(identity_center_client, arn) for arn in batch]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    logger.warning(f"Failed to get permission set details: {result}")
                    continue

                if result is not None and not isinstance(result, Exception):
                    # Type guard to ensure result is PermissionSetData
                    if isinstance(result, PermissionSetData):
                        try:
                            validate_permission_set_data(result)
                            permission_sets.append(result)
                        except Exception as e:
                            logger.warning(f"Skipping invalid permission set data: {e}")
                            continue

            # Add delay between batches
            await asyncio.sleep(0.2)

        return permission_sets

    async def _get_permission_set_details(
        self, identity_center_client: Any, permission_set_arn: str
    ) -> Optional["PermissionSetData"]:
        """Get detailed information for a single permission set.

        Args:
            identity_center_client: Identity Center client
            permission_set_arn: Permission set ARN

        Returns:
            PermissionSetData object or None if failed
        """
        from .models import PermissionSetData

        try:
            # Get basic permission set information
            response = identity_center_client.describe_permission_set(
                InstanceArn=self.instance_arn, PermissionSetArn=permission_set_arn
            )

            permission_set_info = response.get("PermissionSet", {})

            # Get managed policies
            managed_policies = await self._get_managed_policies(
                identity_center_client, permission_set_arn
            )

            # Get customer managed policies
            customer_managed_policies = await self._get_customer_managed_policies(
                identity_center_client, permission_set_arn
            )

            # Get inline policy
            inline_policy = await self._get_inline_policy(
                identity_center_client, permission_set_arn
            )

            return PermissionSetData(
                permission_set_arn=permission_set_arn,
                name=permission_set_info.get("Name", ""),
                description=permission_set_info.get("Description"),
                session_duration=permission_set_info.get("SessionDuration"),
                managed_policies=managed_policies,
                customer_managed_policies=customer_managed_policies,
                inline_policy=inline_policy,
            )

        except Exception as e:
            logger.warning(f"Failed to get details for permission set {permission_set_arn}: {e}")
            return None

    async def _collect_user_group_memberships(
        self, identity_store_client: Any, identity_store_id: str, users: List["UserData"]
    ) -> Dict[str, List[str]]:
        """Collect group memberships for all users.

        Args:
            identity_store_client: Identity Store client
            identity_store_id: Identity Store ID
            users: List of users

        Returns:
            Dictionary mapping user_id to list of group_ids
        """
        group_memberships: Dict[str, List[str]] = {}

        # Process users in batches
        batch_size = 20
        for i in range(0, len(users), batch_size):
            batch = users[i : i + batch_size]

            # Process batch concurrently
            tasks = [
                self._get_user_group_memberships(
                    identity_store_client, identity_store_id, user.user_id
                )
                for user in batch
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for j, result in enumerate(batch_results):
                user = batch[j]
                if isinstance(result, Exception):
                    logger.warning(
                        f"Failed to get group memberships for user {user.user_id}: {result}"
                    )
                    group_memberships[user.user_id] = []
                elif (
                    result is not None
                    and not isinstance(result, Exception)
                    and isinstance(result, list)
                ):
                    group_memberships[user.user_id] = result
                else:
                    group_memberships[user.user_id] = []

            # Add delay between batches
            await asyncio.sleep(0.1)

        return group_memberships

    async def _collect_group_memberships(
        self, identity_store_client: Any, identity_store_id: str, groups: List["GroupData"]
    ) -> Dict[str, List[str]]:
        """Collect memberships for all groups.

        Args:
            identity_store_client: Identity Store client
            identity_store_id: Identity Store ID
            groups: List of groups

        Returns:
            Dictionary mapping group_id to list of user_ids
        """
        memberships: Dict[str, List[str]] = {}

        # Process groups in batches
        batch_size = 20
        for i in range(0, len(groups), batch_size):
            batch = groups[i : i + batch_size]

            # Process batch concurrently
            tasks = [
                self._get_group_memberships(
                    identity_store_client, identity_store_id, group.group_id
                )
                for group in batch
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for j, result in enumerate(batch_results):
                group = batch[j]
                if isinstance(result, Exception):
                    logger.warning(
                        f"Failed to get memberships for group {group.group_id}: {result}"
                    )
                    memberships[group.group_id] = []
                elif (
                    result is not None
                    and not isinstance(result, Exception)
                    and isinstance(result, list)
                ):
                    memberships[group.group_id] = result
                else:
                    memberships[group.group_id] = []

            # Add delay between batches
            await asyncio.sleep(0.1)

        return memberships

    def _extract_email_from_user(self, user_data: Dict[str, Any]) -> Optional[str]:
        """Extract email from user data.

        Args:
            user_data: User data from API response

        Returns:
            Email address or None
        """
        # Check for email in Emails array
        emails = user_data.get("Emails", [])
        if emails and isinstance(emails, list):
            for email_obj in emails:
                if isinstance(email_obj, dict):
                    email_value = email_obj.get("Value")
                    if email_value:
                        return str(email_value)

        # Check for email in UserName if it looks like an email
        username = user_data.get("UserName", "")
        if "@" in str(username):
            return str(username)

        return None

    async def _get_user_group_memberships(
        self, identity_store_client: Any, identity_store_id: str, user_id: str
    ) -> List[str]:
        """Get group memberships for a user.

        Args:
            identity_store_client: Identity Store client
            identity_store_id: Identity Store ID
            user_id: User ID

        Returns:
            List of group IDs
        """
        group_ids = []
        next_token = None

        try:
            while True:
                params = {"IdentityStoreId": identity_store_id, "MemberId": {"UserId": user_id}}
                if next_token:
                    params["NextToken"] = next_token

                response = identity_store_client.list_group_memberships_for_member(**params)

                for membership in response.get("GroupMemberships", []):
                    group_id = membership.get("GroupId")
                    if group_id:
                        group_ids.append(group_id)

                next_token = response.get("NextToken")
                if not next_token:
                    break

        except Exception as e:
            logger.warning(f"Failed to get group memberships for user {user_id}: {e}")

        return group_ids

    async def _get_group_memberships(
        self, identity_store_client: Any, identity_store_id: str, group_id: str
    ) -> List[str]:
        """Get memberships for a group.

        Args:
            identity_store_client: Identity Store client
            identity_store_id: Identity Store ID
            group_id: Group ID

        Returns:
            List of user IDs
        """
        user_ids = []
        next_token = None

        try:
            while True:
                params = {"IdentityStoreId": identity_store_id, "GroupId": group_id}
                if next_token:
                    params["NextToken"] = next_token

                response = identity_store_client.list_group_memberships(**params)

                for membership in response.get("GroupMemberships", []):
                    member_id = membership.get("MemberId", {})
                    user_id = member_id.get("UserId")
                    if user_id:
                        user_ids.append(user_id)

                next_token = response.get("NextToken")
                if not next_token:
                    break

        except Exception as e:
            logger.warning(f"Failed to get memberships for group {group_id}: {e}")

        return user_ids

    async def _get_managed_policies(
        self, identity_center_client: Any, permission_set_arn: str
    ) -> List[str]:
        """Get managed policies for a permission set.

        Args:
            identity_center_client: Identity Center client
            permission_set_arn: Permission set ARN

        Returns:
            List of managed policy ARNs
        """
        try:
            response = identity_center_client.list_managed_policies_in_permission_set(
                InstanceArn=self.instance_arn, PermissionSetArn=permission_set_arn
            )
            policies = response.get("AttachedManagedPolicies", [])
            return [str(policy) for policy in policies]
        except Exception as e:
            logger.warning(f"Failed to get managed policies for {permission_set_arn}: {e}")
            return []

    async def _get_customer_managed_policies(
        self, identity_center_client: Any, permission_set_arn: str
    ) -> List[Dict[str, str]]:
        """Get customer managed policies for a permission set.

        Args:
            identity_center_client: Identity Center client
            permission_set_arn: Permission set ARN

        Returns:
            List of customer managed policy references
        """
        try:
            response = (
                identity_center_client.list_customer_managed_policy_references_in_permission_set(
                    InstanceArn=self.instance_arn, PermissionSetArn=permission_set_arn
                )
            )
            policies = response.get("CustomerManagedPolicyReferences", [])
            return [dict(policy) for policy in policies if isinstance(policy, dict)]
        except Exception as e:
            logger.warning(f"Failed to get customer managed policies for {permission_set_arn}: {e}")
            return []

    async def _get_inline_policy(
        self, identity_center_client: Any, permission_set_arn: str
    ) -> Optional[str]:
        """Get inline policy for a permission set.

        Args:
            identity_center_client: Identity Center client
            permission_set_arn: Permission set ARN

        Returns:
            Inline policy document or None
        """
        try:
            response = identity_center_client.get_inline_policy_for_permission_set(
                InstanceArn=self.instance_arn, PermissionSetArn=permission_set_arn
            )
            policy = response.get("InlinePolicy")
            return str(policy) if policy is not None else None
        except Exception as e:
            # This is expected if no inline policy exists
            if "ResourceNotFoundException" in str(e):
                return None
            logger.warning(f"Failed to get inline policy for {permission_set_arn}: {e}")
            return None

    async def _collect_accounts_parallel(self, organizations_client: Any) -> List["AccountData"]:
        """Collect all accounts using parallel processing.

        Args:
            organizations_client: Organizations client

        Returns:
            List of AccountData objects
        """
        from .models import AccountData, validate_account_data

        try:
            # Get all accounts from Organizations
            response = organizations_client.list_accounts()
            account_list = response.get("Accounts", [])

            if not account_list:
                logger.warning("No accounts found in organization")
                return []

            # Process accounts in batches for parallel processing
            batch_size = 20
            all_accounts: List["AccountData"] = []

            for i in range(0, len(account_list), batch_size):
                batch = account_list[i : i + batch_size]

                # Process batch concurrently
                tasks = [self._process_account_data(account_data) for account_data in batch]

                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.warning(f"Failed to process account: {result}")
                        continue

                    if result is not None and not isinstance(result, Exception):
                        if isinstance(result, AccountData):
                            try:
                                validate_account_data(result)
                                all_accounts.append(result)
                            except Exception as e:
                                logger.warning(f"Skipping invalid account data: {e}")
                                continue

                # Add delay between batches
                await asyncio.sleep(0.1)

            return all_accounts

        except Exception as e:
            logger.error(f"Failed to collect accounts: {e}")
            raise

    async def _process_account_data(self, account_data: Dict[str, Any]) -> Optional["AccountData"]:
        """Process individual account data including tags.

        Args:
            account_data: Account data from Organizations API

        Returns:
            AccountData object with tags or None if processing failed
        """
        from .models import AccountData

        try:
            account_id = account_data.get("Id", "")

            # Get account tags
            tags = await self._get_account_tags(account_id)

            return AccountData(
                account_id=account_id,
                account_name=account_data.get("Name", ""),
                email=account_data.get("Email", ""),
                status=account_data.get("Status", "UNKNOWN"),
                tags=tags,
            )
        except Exception as e:
            logger.warning(
                f"Failed to process account data for {account_data.get('Id', 'unknown')}: {e}"
            )
            return None

    async def _get_account_tags(self, account_id: str) -> Dict[str, str]:
        """Get tags for a specific account.

        Args:
            account_id: Account ID to get tags for

        Returns:
            Dictionary of tag key-value pairs
        """
        try:
            organizations_client = self.client_manager.get_organizations_client()
            tags_data = organizations_client.list_tags_for_resource(account_id)

            # Handle different return types from cached vs non-cached clients
            tags_list = []
            if isinstance(tags_data, dict) and "Tags" in tags_data:
                # Cached client returns {"Tags": [...]}
                tags_list = tags_data["Tags"]
            elif isinstance(tags_data, list):
                # Non-cached client returns [...] directly
                tags_list = tags_data
            else:
                logger.warning(
                    f"Unexpected tags data format for account {account_id}: {type(tags_data)}"
                )
                return {}

            # Convert list of tag dictionaries to a simple key-value dict
            return {
                tag["Key"]: tag["Value"]
                for tag in tags_list
                if isinstance(tag, dict) and "Key" in tag and "Value" in tag
            }

        except Exception as e:
            logger.debug(f"Could not retrieve tags for account {account_id}: {e}")
            return {}

    async def _get_accounts_with_assignments(self, identity_center_client: Any) -> List[str]:
        """Get list of accounts that have assignments.

        Args:
            identity_center_client: Identity Center client

        Returns:
            List of account IDs with assignments
        """
        try:
            # Get all permission sets first (use cached version)
            permission_set_arns = await self._get_from_cache_or_execute(
                "permission_sets",
                lambda: self._collect_permission_sets_paginated(identity_center_client),
                ttl_minutes=15,
            )

            if not permission_set_arns:
                logger.warning("No permission sets found")
                return []

            # Get accounts for each permission set
            accounts_with_assignments: set[str] = set()

            # Process permission sets in batches
            batch_size = 10
            for i in range(0, len(permission_set_arns), batch_size):
                batch = permission_set_arns[i : i + batch_size]

                # Process batch concurrently
                tasks = [
                    self._get_accounts_for_permission_set(identity_center_client, ps_arn)
                    for ps_arn in batch
                ]

                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.warning(f"Failed to get accounts for permission set: {result}")
                        continue

                    if (
                        result is not None
                        and not isinstance(result, Exception)
                        and isinstance(result, list)
                    ):
                        accounts_with_assignments.update(result)

                # Add delay between batches
                await asyncio.sleep(0.1)

            return list(accounts_with_assignments)

        except Exception as e:
            logger.error(f"Failed to get accounts with assignments: {e}")
            return []

    async def _get_accounts_for_permission_set(
        self, identity_center_client: Any, permission_set_arn: str
    ) -> List[str]:
        """Get accounts that have assignments for a permission set.

        Args:
            identity_center_client: Identity Center client
            permission_set_arn: Permission set ARN

        Returns:
            List of account IDs
        """
        account_ids = []
        next_token = None

        try:
            while True:
                params = {"InstanceArn": self.instance_arn, "PermissionSetArn": permission_set_arn}
                if next_token:
                    params["NextToken"] = next_token

                response = identity_center_client.list_accounts_for_provisioned_permission_set(
                    **params
                )

                account_ids.extend(response.get("AccountIds", []))

                next_token = response.get("NextToken")
                if not next_token:
                    break

        except Exception as e:
            logger.warning(f"Failed to get accounts for permission set {permission_set_arn}: {e}")

        return account_ids

    async def _collect_assignments_parallel(
        self, identity_center_client: Any, account_ids: List[str]
    ) -> List["AssignmentData"]:
        """Collect assignments across multiple accounts in parallel.

        Args:
            identity_center_client: Identity Center client
            account_ids: List of account IDs to collect assignments for

        Returns:
            List of all AssignmentData objects across all accounts
        """
        all_assignments = []

        # Process accounts in batches to avoid overwhelming the API
        batch_size = 5
        for i in range(0, len(account_ids), batch_size):
            batch = account_ids[i : i + batch_size]

            # Process batch concurrently
            tasks = [
                self._collect_assignments_for_account(identity_center_client, account_id)
                for account_id in batch
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for j, result in enumerate(batch_results):
                account_id = batch[j]
                if isinstance(result, Exception):
                    logger.warning(
                        f"Failed to collect assignments for account {account_id}: {result}"
                    )
                elif isinstance(result, list):
                    all_assignments.extend(result)

            # Add delay between batches to avoid rate limiting
            await asyncio.sleep(0.1)

        return all_assignments

    async def _collect_all_assignments(self, identity_center_client: Any) -> List["AssignmentData"]:
        """Collect all assignments across all accounts.

        Args:
            identity_center_client: Identity Center client

        Returns:
            List of all AssignmentData objects
        """
        # First, get all accounts that have assignments
        accounts_with_assignments = await self._get_accounts_with_assignments(
            identity_center_client
        )

        # Collect assignments across all accounts with parallel processing
        assignments = await self._collect_assignments_parallel(
            identity_center_client, accounts_with_assignments
        )

        return assignments

    async def _collect_assignments_for_account(
        self, identity_center_client: Any, account_id: str
    ) -> List["AssignmentData"]:
        from .models import AssignmentData

        assignments = []
        try:
            # First, list all permission sets (use cached version)
            permission_set_arns = await self._get_from_cache_or_execute(
                "permission_sets",
                lambda: self._collect_permission_sets_paginated(identity_center_client),
                ttl_minutes=15,
            )

            for ps_arn in permission_set_arns:
                next_token = None
                while True:
                    params = {
                        "InstanceArn": self.instance_arn,
                        "AccountId": account_id,
                        "PermissionSetArn": ps_arn,
                    }
                    if next_token:
                        params["NextToken"] = next_token

                    response = identity_center_client.list_account_assignments(**params)

                    for assignment_data in response.get("AccountAssignments", []):
                        assignments.append(
                            AssignmentData(
                                account_id=account_id,
                                permission_set_arn=assignment_data.get("PermissionSetArn", ""),
                                principal_type=assignment_data.get("PrincipalType", ""),
                                principal_id=assignment_data.get("PrincipalId", ""),
                            )
                        )

                    next_token = response.get("NextToken")
                    if not next_token:
                        break
        except Exception as e:
            logger.warning(f"Failed to collect assignments for account {account_id}: {e}")

        return assignments

    async def _retry_with_backoff(
        self,
        operation: Callable[..., Any],
        *args: Any,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        **kwargs: Any,
    ) -> Any:
        """Execute an operation with exponential backoff retry logic.

        Args:
            operation: The operation to retry
            *args: Positional arguments for the operation
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            **kwargs: Keyword arguments for the operation

        Returns:
            Result of the operation

        Raises:
            Exception: The last exception if all retries fail
        """
        last_exception: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                return (
                    await operation(*args, **kwargs)
                    if asyncio.iscoroutinefunction(operation)
                    else operation(*args, **kwargs)
                )

            except ClientError as e:
                last_exception = e
                error_code = e.response.get("Error", {}).get("Code", "")

                # Don't retry on certain error types
                if error_code in ["AccessDenied", "UnauthorizedOperation", "InvalidParameterValue"]:
                    logger.error(f"Non-retryable error in {operation.__name__}: {e}")
                    raise

                # Don't retry on the last attempt
                if attempt == max_retries:
                    break

                # Calculate delay with exponential backoff
                delay = min(base_delay * (2**attempt), max_delay)

                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries + 1} failed for {getattr(operation, '__name__', 'unknown')}: {e}. "
                    f"Retrying in {delay:.1f} seconds..."
                )

                await asyncio.sleep(delay)

            except Exception as e:
                last_exception = e

                # Don't retry on the last attempt
                if attempt == max_retries:
                    break

                # Calculate delay with exponential backoff
                delay = min(base_delay * (2**attempt), max_delay)

                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries + 1} failed for {getattr(operation, '__name__', 'unknown')}: {e}. "
                    f"Retrying in {delay:.1f} seconds..."
                )

                await asyncio.sleep(delay)

        # If we get here, all retries failed
        if last_exception is not None:
            logger.error(
                f"All retry attempts failed for {getattr(operation, '__name__', 'unknown')}: {last_exception}"
            )
            raise last_exception
        else:
            raise RuntimeError("All retry attempts failed with unknown error")

    def _get_cache_key(self, operation: str, **params: Any) -> str:
        """Generate cache key for an operation.

        Args:
            operation: Operation name
            **params: Operation parameters

        Returns:
            Cache key string
        """
        import re

        # Create a deterministic cache key from operation and parameters
        key_parts = [f"statistics:{operation}"]

        # Add instance ARN to key (sanitize for cache compatibility)
        # Extract just the instance ID from the ARN to avoid special characters
        instance_id = (
            self.instance_arn.split("/")[-1] if "/" in self.instance_arn else self.instance_arn
        )
        key_parts.append(f"instance:{instance_id}")

        # Add sorted parameters to ensure consistent keys
        for key, value in sorted(params.items()):
            if value is not None:
                # Sanitize parameter values to only include allowed characters
                sanitized_value = re.sub(r"[^a-zA-Z0-9_\-\.:]", "_", str(value))
                key_parts.append(f"{key}:{sanitized_value}")

        return ":".join(key_parts)

    def _deserialize_cached_data(self, cached_data: Any, operation: str) -> Any:
        """Convert cached dictionary data back to dataclass objects.

        Args:
            cached_data: Cached data (could be dict, list, or already deserialized)
            operation: Operation name for context

        Returns:
            Deserialized data
        """
        logger.debug(
            f"Deserializing cached data for operation {operation}: type={type(cached_data)}, data={cached_data}"
        )

        # If it's already a dataclass object, return as-is
        if hasattr(cached_data, "__dataclass_fields__"):
            return cached_data

        # If it's a string (shouldn't happen but handle gracefully)
        if isinstance(cached_data, str):
            logger.warning(f"Unexpected string data in cache for operation {operation}")
            return cached_data

        # Handle list of dictionaries
        if isinstance(cached_data, list):
            if not cached_data:
                return cached_data

            # Check if items are already dataclass objects
            if hasattr(cached_data[0], "__dataclass_fields__"):
                return cached_data

            # Convert list of dictionaries to dataclass objects
            try:
                if operation == "users":
                    from .models import UserData

                    return [
                        UserData(**user_dict)
                        for user_dict in cached_data
                        if isinstance(user_dict, dict)
                    ]
                elif operation == "groups":
                    from .models import GroupData

                    return [
                        GroupData(**group_dict)
                        for group_dict in cached_data
                        if isinstance(group_dict, dict)
                    ]
                elif operation == "permission_sets":
                    # Permission sets are just ARN strings, not dataclass objects
                    logger.debug(
                        f"Returning permission sets cached data: {len(cached_data) if isinstance(cached_data, list) else 'not a list'} items"
                    )
                    return cached_data
                elif operation == "permission_set_details":
                    from .models import PermissionSetData

                    logger.debug(f"Deserializing permission_set_details: {len(cached_data)} items")
                    try:
                        result = [
                            PermissionSetData(**ps_dict)
                            for ps_dict in cached_data
                            if isinstance(ps_dict, dict)
                        ]
                        logger.debug(
                            f"Successfully deserialized {len(result)} permission set details"
                        )
                        return result
                    except Exception as e:
                        logger.error(f"Failed to deserialize permission set details: {e}")
                        logger.debug(
                            f"Cached data sample: {cached_data[:1] if cached_data else 'empty'}"
                        )
                        return cached_data
                elif operation == "accounts":
                    from .models import AccountData

                    return [
                        AccountData(**account_dict)
                        for account_dict in cached_data
                        if isinstance(account_dict, dict)
                    ]
                elif operation == "assignments":
                    from .models import AssignmentData

                    return [
                        AssignmentData(**assignment_dict)
                        for assignment_dict in cached_data
                        if isinstance(assignment_dict, dict)
                    ]
            except Exception as e:
                logger.warning(f"Failed to deserialize cached data for {operation}: {e}")
                return cached_data

        # Handle complex objects (statistics)
        if isinstance(cached_data, dict):
            try:
                if "users" in cached_data and "group_memberships" in cached_data:
                    # UserStatistics
                    from datetime import datetime

                    from .models import UserData, UserStatistics

                    users = [
                        UserData(**user_dict)
                        for user_dict in cached_data["users"]
                        if isinstance(user_dict, dict)
                    ]
                    return UserStatistics(
                        users=users,
                        group_memberships=cached_data["group_memberships"],
                        collection_timestamp=datetime.fromisoformat(
                            cached_data["collection_timestamp"]
                        ),
                    )
                elif "groups" in cached_data and "memberships" in cached_data:
                    # GroupStatistics
                    from datetime import datetime

                    from .models import GroupData, GroupStatistics

                    groups = [
                        GroupData(**group_dict)
                        for group_dict in cached_data["groups"]
                        if isinstance(group_dict, dict)
                    ]
                    return GroupStatistics(
                        groups=groups,
                        memberships=cached_data["memberships"],
                        collection_timestamp=datetime.fromisoformat(
                            cached_data["collection_timestamp"]
                        ),
                    )
                elif "permission_sets" in cached_data:
                    # PermissionSetStatistics
                    from datetime import datetime

                    from .models import PermissionSetData, PermissionSetStatistics

                    permission_sets = [
                        PermissionSetData(**ps_dict)
                        for ps_dict in cached_data["permission_sets"]
                        if isinstance(ps_dict, dict)
                    ]
                    return PermissionSetStatistics(
                        permission_sets=permission_sets,
                        collection_timestamp=datetime.fromisoformat(
                            cached_data["collection_timestamp"]
                        ),
                    )
                elif "accounts" in cached_data:
                    # AccountStatistics
                    from datetime import datetime

                    from .models import AccountData, AccountStatistics

                    accounts = [
                        AccountData(**account_dict)
                        for account_dict in cached_data["accounts"]
                        if isinstance(account_dict, dict)
                    ]
                    return AccountStatistics(
                        accounts=accounts,
                        collection_timestamp=datetime.fromisoformat(
                            cached_data["collection_timestamp"]
                        ),
                    )
                elif "assignments" in cached_data:
                    # AssignmentStatistics
                    from datetime import datetime

                    from .models import AssignmentData, AssignmentStatistics

                    assignments = [
                        AssignmentData(**assignment_dict)
                        for assignment_dict in cached_data["assignments"]
                        if isinstance(assignment_dict, dict)
                    ]
                    return AssignmentStatistics(
                        assignments=assignments,
                        collection_timestamp=datetime.fromisoformat(
                            cached_data["collection_timestamp"]
                        ),
                    )
            except Exception as e:
                logger.warning(f"Failed to deserialize cached statistics data for {operation}: {e}")
                return cached_data

        # Fallback: return as-is
        return cached_data

    async def _get_from_cache_or_execute(
        self, operation: str, execute_func: Callable[[], Any], ttl_minutes: int = 15, **params: Any
    ) -> Any:
        """Get data from cache or execute function if cache miss.

        Args:
            operation: Operation name for cache key
            execute_func: Function to execute if cache miss
            ttl_minutes: Cache TTL in minutes
            **params: Parameters for cache key generation

        Returns:
            Cached data or result from execute_func
        """
        if not self.cache_enabled:
            # If caching is disabled, execute directly
            func_result = execute_func()
            if asyncio.iscoroutine(func_result):
                return await func_result
            else:
                return await self._retry_with_backoff(execute_func)

        try:
            cache_manager = self.client_manager.get_cache_manager()
            if not cache_manager:
                logger.warning("Cache manager not available, executing without cache")
                func_result = execute_func()
                if asyncio.iscoroutine(func_result):
                    return await func_result
                else:
                    return await self._retry_with_backoff(execute_func)

            # Generate cache key
            cache_key = self._get_cache_key(operation, **params)

            # Try to get from cache
            try:
                cached_data = cache_manager.get(cache_key)
                if cached_data is not None:
                    logger.debug(f"Cache hit for {operation}")
                    # Convert cached dictionaries back to dataclass objects
                    return self._deserialize_cached_data(cached_data, operation)
            except Exception as e:
                logger.warning(f"Cache get failed for {operation}: {e}")

            # Cache miss - execute function with retry logic
            logger.debug(f"Cache miss for {operation}, executing function")
            # Check if execute_func returns a coroutine
            func_result = execute_func()
            if asyncio.iscoroutine(func_result):
                result = await func_result
            else:
                result = await self._retry_with_backoff(execute_func)

            # Store in cache
            try:
                from datetime import timedelta

                # Convert dataclass objects to dictionaries for JSON serialization
                serializable_result = self._make_serializable(result)

                cache_manager.set(
                    cache_key, serializable_result, timedelta(seconds=ttl_minutes * 60)
                )
                logger.debug(f"Cached result for {operation}")
            except Exception as e:
                logger.warning(f"Cache set failed for {operation}: {e}")

            return result

        except Exception as e:
            logger.warning(f"Cache operation failed for {operation}: {e}, executing without cache")
            func_result = execute_func()
            if asyncio.iscoroutine(func_result):
                return await func_result
            else:
                return await self._retry_with_backoff(execute_func)

    def _make_serializable(self, obj: Any) -> Any:
        """Convert dataclass objects to dictionaries for JSON serialization.

        Args:
            obj: Object to make serializable

        Returns:
            Serializable version of the object
        """
        from dataclasses import asdict, is_dataclass
        from datetime import datetime

        if is_dataclass(obj) and not isinstance(obj, type):
            return asdict(obj)
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._make_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj

    def _log_collection_metrics(self, operation: str, start_time: datetime, count: int) -> None:
        """Log collection metrics for monitoring.

        Args:
            operation: Operation name
            start_time: Operation start time
            count: Number of items collected
        """
        duration = (datetime.now() - start_time).total_seconds()
        rate = count / duration if duration > 0 else 0

        logger.info(
            f"Collection metrics - Operation: {operation}, "
            f"Count: {count}, Duration: {duration:.2f}s, Rate: {rate:.2f} items/sec"
        )

    async def _validate_aws_permissions(self) -> None:
        """Validate that required AWS permissions are available.

        Raises:
            Exception: If required permissions are not available
        """
        try:
            # Test basic Identity Center access
            identity_center_client = self.client_manager.get_identity_center_client()
            await self._retry_with_backoff(
                lambda: identity_center_client.list_instances(), max_retries=1
            )

            # Test Identity Store access
            identity_store_client = self.client_manager.get_identity_store_client()
            identity_store_id = self._extract_identity_store_id()

            # Try to list users (this will fail gracefully if no users exist)
            await self._retry_with_backoff(
                lambda: identity_store_client.list_users(
                    IdentityStoreId=identity_store_id, MaxResults=1
                ),
                max_retries=1,
            )

            # Test Organizations access
            organizations_client = self.client_manager.get_organizations_client()
            await self._retry_with_backoff(
                lambda: organizations_client.list_accounts(), max_retries=1
            )

            logger.info("AWS permissions validation successful")

        except Exception as e:
            logger.error(f"AWS permissions validation failed: {e}")
            raise Exception(
                f"Required AWS permissions are not available: {e}. "
                "Please ensure the AWS profile has the necessary Identity Center, "
                "Identity Store, and Organizations permissions."
            )
