"""Performance and scalability tests for statistics module.

These tests verify that the statistics module can handle large datasets
efficiently without excessive memory usage or long processing times.
"""

import asyncio
import time
from typing import Any, Dict
from unittest.mock import Mock

import pytest

from src.awsideman.statistics.manager import StatisticsManager
from src.awsideman.statistics.models import StatisticsReport


class TestStatisticsPerformance:
    """Performance tests for statistics module."""

    def create_large_mock_responses(
        self, user_count: int, group_count: int, ps_count: int, account_count: int
    ) -> Dict[str, Any]:
        """Create mock AWS responses with specified counts."""
        # Generate users
        users = []
        for i in range(user_count):
            users.append(
                {
                    "UserId": f"user{i}",
                    "UserName": f"user{i}",
                    "DisplayName": f"User {i}",
                    "Emails": [{"Value": f"user{i}@example.com", "Primary": True}],
                    "Active": True,
                }
            )

        # Generate groups
        groups = []
        for i in range(group_count):
            groups.append(
                {
                    "GroupId": f"group{i}",
                    "DisplayName": f"Group {i}",
                    "Description": f"Group {i} description",
                }
            )

        # Generate permission sets
        permission_sets = []
        for i in range(ps_count):
            permission_sets.append(f"arn:aws:sso:::permissionSet/ssoins-123/ps-{i}")

        # Generate accounts
        accounts = []
        for i in range(account_count):
            accounts.append(
                {
                    "Id": f"12345678901{i:01d}",
                    "Name": f"Account {i}",
                    "Email": f"account{i}@example.com",
                    "Status": "ACTIVE",
                }
            )

        # Generate assignments (distribute across accounts and users)
        assignments_by_account = {}
        assignment_count = 0
        for account_idx in range(account_count):
            account_id = f"12345678901{account_idx:01d}"
            assignments_by_account[account_id] = {
                "AccountAssignments": [],
                "NextToken": None,
            }

            # Add some assignments for this account
            for user_idx in range(min(10, user_count)):  # Max 10 assignments per account
                if assignment_count < user_count * 2:  # Limit total assignments
                    assignments_by_account[account_id]["AccountAssignments"].append(
                        {
                            "AccountId": account_id,
                            "PermissionSetArn": f"arn:aws:sso:::permissionSet/ssoins-123/ps-{user_idx % ps_count}",
                            "PrincipalType": "USER",
                            "PrincipalId": f"user{user_idx}",
                        }
                    )
                    assignment_count += 1

        # Generate group memberships (simple distribution)
        group_memberships_for_member = {}
        for user_idx in range(user_count):
            user_id = f"user{user_idx}"
            # Each user belongs to 1-3 groups
            user_groups = []
            for group_idx in range(min(3, group_count)):
                if (user_idx + group_idx) % 3 == 0:  # Distribute users across groups
                    user_groups.append({"GroupId": f"group{group_idx}"})

            group_memberships_for_member[user_id] = {
                "GroupMemberships": user_groups,
                "NextToken": None,
            }

        return {
            "list_instances": {
                "Instances": [
                    {
                        "InstanceArn": "arn:aws:sso:::instance/ssoins-1234567890abcdef",
                        "IdentityStoreId": "d-1234567890",
                        "Name": "Test SSO Instance",
                        "Status": "ACTIVE",
                    }
                ]
            },
            "list_users": {"Users": users, "NextToken": None},
            "list_groups": {"Groups": groups, "NextToken": None},
            "list_permission_sets": {"PermissionSets": permission_sets, "NextToken": None},
            "list_accounts": {"Accounts": accounts, "NextToken": None},
            "list_account_assignments": assignments_by_account,
            "list_group_memberships_for_member": group_memberships_for_member,
        }

    def create_mock_client_manager(self, mock_responses: Dict[str, Any]) -> Mock:
        """Create a mock client manager with the given responses."""
        client_manager = Mock()
        client_manager.is_caching_enabled.return_value = False
        client_manager.region = "us-east-1"

        # Identity Store client
        identity_store_client = Mock()
        identity_store_client.list_users.return_value = mock_responses["list_users"]
        identity_store_client.list_groups.return_value = mock_responses["list_groups"]

        def mock_group_memberships_for_member(**kwargs: Any) -> Dict[str, Any]:
            member_id = kwargs.get("MemberId", {}).get("UserId", "")
            return mock_responses["list_group_memberships_for_member"].get(
                member_id, {"GroupMemberships": [], "NextToken": None}
            )

        identity_store_client.list_group_memberships_for_member.side_effect = (
            mock_group_memberships_for_member
        )

        # Identity Center client
        identity_center_client = Mock()
        identity_center_client.list_instances.return_value = mock_responses["list_instances"]
        identity_center_client.list_permission_sets.return_value = mock_responses[
            "list_permission_sets"
        ]

        # Simple permission set details
        def mock_describe_permission_set(**kwargs: Any) -> Dict[str, Any]:
            ps_arn = kwargs.get("PermissionSetArn", "")
            ps_name = ps_arn.split("/")[-1] if "/" in ps_arn else "UnknownPS"
            return {
                "PermissionSet": {
                    "Name": ps_name,
                    "Description": f"Description for {ps_name}",
                    "PermissionSetArn": ps_arn,
                    "SessionDuration": "PT8H",
                }
            }

        identity_center_client.describe_permission_set.side_effect = mock_describe_permission_set
        identity_center_client.list_managed_policies_in_permission_set.return_value = {
            "AttachedManagedPolicies": []
        }

        def mock_list_account_assignments(**kwargs: Any) -> Dict[str, Any]:
            account_id = kwargs.get("AccountId", "")
            return mock_responses["list_account_assignments"].get(
                account_id, {"AccountAssignments": [], "NextToken": None}
            )

        identity_center_client.list_account_assignments.side_effect = mock_list_account_assignments

        # Organizations client
        organizations_client = Mock()
        organizations_client.list_accounts.return_value = mock_responses["list_accounts"]

        # Wire up clients
        client_manager.get_identity_store_client.return_value = identity_store_client
        client_manager.get_identity_center_client.return_value = identity_center_client
        client_manager.get_organizations_client.return_value = organizations_client

        return client_manager

    @pytest.mark.asyncio
    async def test_medium_dataset_performance(self) -> None:
        """Test performance with medium-sized dataset (100 users, 20 groups)."""
        mock_responses = self.create_large_mock_responses(
            user_count=100, group_count=20, ps_count=10, account_count=5
        )
        mock_client_manager = self.create_mock_client_manager(mock_responses)

        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        manager = StatisticsManager(mock_client_manager, instance_arn)

        start_time = time.time()
        result = await manager.generate_statistics()
        end_time = time.time()

        processing_time = end_time - start_time

        # Verify results
        assert isinstance(result, StatisticsReport)
        assert result.user_group_metrics.total_users == 100
        assert result.user_group_metrics.total_groups == 20
        assert result.permission_set_metrics.total_permission_sets == 10
        assert result.account_metrics.total_accounts == 5

        # Performance assertion - should complete within reasonable time
        assert processing_time < 10.0, f"Processing took {processing_time:.2f}s, expected < 10s"

    @pytest.mark.asyncio
    async def test_large_dataset_performance(self) -> None:
        """Test performance with large dataset (500 users, 50 groups)."""
        mock_responses = self.create_large_mock_responses(
            user_count=500, group_count=50, ps_count=25, account_count=10
        )
        mock_client_manager = self.create_mock_client_manager(mock_responses)

        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        manager = StatisticsManager(mock_client_manager, instance_arn)

        start_time = time.time()
        result = await manager.generate_statistics()
        end_time = time.time()

        processing_time = end_time - start_time

        # Verify results
        assert isinstance(result, StatisticsReport)
        assert result.user_group_metrics.total_users == 500
        assert result.user_group_metrics.total_groups == 50
        assert result.permission_set_metrics.total_permission_sets == 25
        assert result.account_metrics.total_accounts == 10

        # Performance assertion - should complete within reasonable time for large dataset
        assert processing_time < 30.0, f"Processing took {processing_time:.2f}s, expected < 30s"

    @pytest.mark.asyncio
    async def test_concurrent_statistics_generation(self) -> None:
        """Test concurrent statistics generation performance."""
        mock_responses = self.create_large_mock_responses(
            user_count=50, group_count=10, ps_count=5, account_count=3
        )
        mock_client_manager = self.create_mock_client_manager(mock_responses)

        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        manager = StatisticsManager(mock_client_manager, instance_arn)

        # Run multiple concurrent statistics generations
        start_time = time.time()
        tasks = [manager.generate_statistics() for _ in range(3)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        processing_time = end_time - start_time

        # Verify all results
        assert len(results) == 3
        for result in results:
            assert isinstance(result, StatisticsReport)
            assert result.user_group_metrics.total_users == 50

        # Concurrent processing should not take significantly longer than sequential
        # (allowing for some overhead)
        assert (
            processing_time < 15.0
        ), f"Concurrent processing took {processing_time:.2f}s, expected < 15s"

    @pytest.mark.asyncio
    async def test_memory_usage_large_dataset(self) -> None:
        """Test memory usage with large dataset."""
        import gc

        # Get initial memory usage
        gc.collect()
        initial_objects = len(gc.get_objects())

        mock_responses = self.create_large_mock_responses(
            user_count=200, group_count=30, ps_count=15, account_count=8
        )
        mock_client_manager = self.create_mock_client_manager(mock_responses)

        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        manager = StatisticsManager(mock_client_manager, instance_arn)

        result = await manager.generate_statistics()

        # Verify results
        assert isinstance(result, StatisticsReport)
        assert result.user_group_metrics.total_users == 200

        # Check memory usage after processing
        gc.collect()
        final_objects = len(gc.get_objects())
        object_increase = final_objects - initial_objects

        # Memory usage should be reasonable (allowing for test overhead)
        # This is a rough check - exact numbers will vary
        assert (
            object_increase < 10000
        ), f"Object count increased by {object_increase}, expected < 10000"

    @pytest.mark.asyncio
    async def test_export_performance(self) -> None:
        """Test export performance with large dataset."""
        mock_responses = self.create_large_mock_responses(
            user_count=100, group_count=20, ps_count=10, account_count=5
        )
        mock_client_manager = self.create_mock_client_manager(mock_responses)

        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        manager = StatisticsManager(mock_client_manager, instance_arn)

        result = await manager.generate_statistics()

        # Test JSON export performance
        start_time = time.time()
        json_output = manager.exporter.export_to_json(result)
        json_time = time.time() - start_time

        # Test CSV export performance
        start_time = time.time()
        csv_output = manager.exporter.export_to_csv(result)
        csv_time = time.time() - start_time

        # Test text export performance
        start_time = time.time()
        text_output = manager.exporter.export_to_text(result)
        text_time = time.time() - start_time

        # Verify exports completed
        assert len(json_output) > 0
        assert len(csv_output) > 0
        assert len(text_output) > 0

        # Performance assertions
        assert json_time < 5.0, f"JSON export took {json_time:.2f}s, expected < 5s"
        assert csv_time < 5.0, f"CSV export took {csv_time:.2f}s, expected < 5s"
        assert text_time < 5.0, f"Text export took {text_time:.2f}s, expected < 5s"

    @pytest.mark.asyncio
    async def test_scalability_with_assignments(self) -> None:
        """Test scalability with high number of assignments."""
        # Create dataset with many assignments
        user_count = 50
        account_count = 10
        ps_count = 5

        mock_responses = self.create_large_mock_responses(user_count, 10, ps_count, account_count)

        # Increase assignment density
        for account_idx in range(account_count):
            account_id = f"12345678901{account_idx:01d}"
            assignments = []

            # Create more assignments per account
            for user_idx in range(user_count):
                for ps_idx in range(ps_count):
                    assignments.append(
                        {
                            "AccountId": account_id,
                            "PermissionSetArn": f"arn:aws:sso:::permissionSet/ssoins-123/ps-{ps_idx}",
                            "PrincipalType": "USER",
                            "PrincipalId": f"user{user_idx}",
                        }
                    )

            mock_responses["list_account_assignments"][account_id] = {
                "AccountAssignments": assignments,
                "NextToken": None,
            }

        mock_client_manager = self.create_mock_client_manager(mock_responses)

        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        manager = StatisticsManager(mock_client_manager, instance_arn)

        start_time = time.time()
        result = await manager.generate_statistics()
        end_time = time.time()

        processing_time = end_time - start_time

        # Verify results with high assignment count
        assert isinstance(result, StatisticsReport)
        assert result.user_group_metrics.total_users == user_count

        # Should handle high assignment density efficiently
        assert (
            processing_time < 20.0
        ), f"High-assignment processing took {processing_time:.2f}s, expected < 20s"

    @pytest.mark.asyncio
    async def test_empty_dataset_performance(self) -> None:
        """Test performance with empty dataset."""
        mock_responses = self.create_large_mock_responses(0, 0, 0, 0)
        mock_client_manager = self.create_mock_client_manager(mock_responses)

        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        manager = StatisticsManager(mock_client_manager, instance_arn)

        start_time = time.time()
        result = await manager.generate_statistics()
        end_time = time.time()

        processing_time = end_time - start_time

        # Verify empty results
        assert isinstance(result, StatisticsReport)
        assert result.user_group_metrics.total_users == 0
        assert result.user_group_metrics.total_groups == 0

        # Empty dataset should process very quickly
        assert (
            processing_time < 2.0
        ), f"Empty dataset processing took {processing_time:.2f}s, expected < 2s"

    @pytest.mark.asyncio
    async def test_category_specific_performance(self) -> None:
        """Test performance of category-specific statistics generation."""
        mock_responses = self.create_large_mock_responses(
            user_count=100, group_count=20, ps_count=10, account_count=5
        )
        mock_client_manager = self.create_mock_client_manager(mock_responses)

        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        manager = StatisticsManager(mock_client_manager, instance_arn)

        # Test individual category performance
        start_time = time.time()
        user_metrics = await manager.generate_user_group_statistics()
        user_time = time.time() - start_time

        start_time = time.time()
        ps_metrics = await manager.generate_permission_set_statistics()
        ps_time = time.time() - start_time

        start_time = time.time()
        account_metrics = await manager.generate_account_statistics()
        account_time = time.time() - start_time

        # Verify results
        assert user_metrics.total_users == 100
        assert ps_metrics.total_permission_sets == 10
        assert account_metrics.total_accounts == 5

        # Individual categories should be faster than full generation
        assert user_time < 5.0, f"User metrics took {user_time:.2f}s, expected < 5s"
        assert ps_time < 5.0, f"Permission set metrics took {ps_time:.2f}s, expected < 5s"
        assert account_time < 5.0, f"Account metrics took {account_time:.2f}s, expected < 5s"
