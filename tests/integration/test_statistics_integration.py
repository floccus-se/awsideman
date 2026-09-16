"""Integration tests for statistics module with mock AWS data.

These tests use simple, realistic mock data to test the full statistics pipeline
without complex mocking that could break during refactoring.
"""

from typing import Any, Dict
from unittest.mock import Mock

import pytest

from src.awsideman.statistics.manager import StatisticsManager
from src.awsideman.statistics.models import StatisticsReport


class TestStatisticsIntegration:
    """Integration tests for the complete statistics pipeline."""

    @pytest.fixture
    def mock_aws_responses(self) -> Dict[str, Any]:
        """Create realistic AWS API response data."""
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
            "list_users": {
                "Users": [
                    {
                        "UserId": "user1",
                        "UserName": "john.doe",
                        "DisplayName": "John Doe",
                        "Emails": [{"Value": "john.doe@example.com", "Primary": True}],
                        "Active": True,
                    },
                    {
                        "UserId": "user2",
                        "UserName": "jane.smith",
                        "DisplayName": "Jane Smith",
                        "Emails": [{"Value": "jane.smith@example.com", "Primary": True}],
                        "Active": True,
                    },
                    {
                        "UserId": "user3",
                        "UserName": "orphaned.user",
                        "DisplayName": "Orphaned User",
                        "Emails": [{"Value": "orphaned@example.com", "Primary": True}],
                        "Active": True,
                    },
                ],
                "NextToken": None,
            },
            "list_groups": {
                "Groups": [
                    {
                        "GroupId": "group1",
                        "DisplayName": "Developers",
                        "Description": "Development team",
                    },
                    {
                        "GroupId": "group2",
                        "DisplayName": "Admins",
                        "Description": "Administrative team",
                    },
                    {
                        "GroupId": "group3",
                        "DisplayName": "Empty Group",
                        "Description": "Group with no members",
                    },
                ],
                "NextToken": None,
            },
            "list_permission_sets": {
                "PermissionSets": [
                    "arn:aws:sso:::permissionSet/ssoins-123/ps-admin",
                    "arn:aws:sso:::permissionSet/ssoins-123/ps-dev",
                    "arn:aws:sso:::permissionSet/ssoins-123/ps-readonly",
                ],
                "NextToken": None,
            },
            "describe_permission_set": {
                "admin": {
                    "PermissionSet": {
                        "Name": "AdminAccess",
                        "Description": "Administrative access",
                        "PermissionSetArn": "arn:aws:sso:::permissionSet/ssoins-123/ps-admin",
                        "SessionDuration": "PT4H",
                    }
                },
                "dev": {
                    "PermissionSet": {
                        "Name": "DeveloperAccess",
                        "Description": "Developer access",
                        "PermissionSetArn": "arn:aws:sso:::permissionSet/ssoins-123/ps-dev",
                        "SessionDuration": "PT8H",
                    }
                },
                "readonly": {
                    "PermissionSet": {
                        "Name": "ReadOnlyAccess",
                        "Description": "Read-only access",
                        "PermissionSetArn": "arn:aws:sso:::permissionSet/ssoins-123/ps-readonly",
                        "SessionDuration": "PT12H",
                    }
                },
            },
            "list_managed_policies_in_permission_set": {
                "admin": {
                    "AttachedManagedPolicies": [
                        {
                            "Name": "AdministratorAccess",
                            "Arn": "arn:aws:iam::aws:policy/AdministratorAccess",
                        }
                    ]
                },
                "dev": {
                    "AttachedManagedPolicies": [
                        {
                            "Name": "PowerUserAccess",
                            "Arn": "arn:aws:iam::aws:policy/PowerUserAccess",
                        }
                    ]
                },
                "readonly": {
                    "AttachedManagedPolicies": [
                        {"Name": "ReadOnlyAccess", "Arn": "arn:aws:iam::aws:policy/ReadOnlyAccess"}
                    ]
                },
            },
            "list_accounts": {
                "Accounts": [
                    {
                        "Id": "123456789012",
                        "Name": "Production Account",
                        "Email": "prod@example.com",
                        "Status": "ACTIVE",
                    },
                    {
                        "Id": "123456789013",
                        "Name": "Development Account",
                        "Email": "dev@example.com",
                        "Status": "ACTIVE",
                    },
                ],
                "NextToken": None,
            },
            "list_account_assignments": {
                "123456789012": {
                    "AccountAssignments": [
                        {
                            "AccountId": "123456789012",
                            "PermissionSetArn": "arn:aws:sso:::permissionSet/ssoins-123/ps-admin",
                            "PrincipalType": "USER",
                            "PrincipalId": "user1",
                        },
                        {
                            "AccountId": "123456789012",
                            "PermissionSetArn": "arn:aws:sso:::permissionSet/ssoins-123/ps-dev",
                            "PrincipalType": "GROUP",
                            "PrincipalId": "group1",
                        },
                    ],
                    "NextToken": None,
                },
                "123456789013": {
                    "AccountAssignments": [
                        {
                            "AccountId": "123456789013",
                            "PermissionSetArn": "arn:aws:sso:::permissionSet/ssoins-123/ps-dev",
                            "PrincipalType": "USER",
                            "PrincipalId": "user2",
                        },
                    ],
                    "NextToken": None,
                },
            },
            "list_group_memberships": {
                "group1": {
                    "GroupMemberships": [
                        {"MemberId": {"UserId": "user1"}},
                        {"MemberId": {"UserId": "user2"}},
                    ],
                    "NextToken": None,
                },
                "group2": {
                    "GroupMemberships": [
                        {"MemberId": {"UserId": "user1"}},
                    ],
                    "NextToken": None,
                },
                "group3": {
                    "GroupMemberships": [],
                    "NextToken": None,
                },
            },
            "list_group_memberships_for_member": {
                "user1": {
                    "GroupMemberships": [
                        {"GroupId": "group1"},
                        {"GroupId": "group2"},
                    ],
                    "NextToken": None,
                },
                "user2": {
                    "GroupMemberships": [
                        {"GroupId": "group1"},
                    ],
                    "NextToken": None,
                },
                "user3": {
                    "GroupMemberships": [],
                    "NextToken": None,
                },
            },
        }

    @pytest.fixture
    def mock_client_manager(self, mock_aws_responses: Dict[str, Any]) -> Mock:
        """Create a mock client manager with realistic AWS responses."""
        client_manager = Mock()
        client_manager.is_caching_enabled.return_value = (
            False  # Disable cache for integration tests
        )
        client_manager.region = "us-east-1"

        # Mock Identity Store client
        identity_store_client = Mock()
        identity_store_client.list_users.return_value = mock_aws_responses["list_users"]
        identity_store_client.list_groups.return_value = mock_aws_responses["list_groups"]

        # Mock group membership responses
        def mock_group_memberships_for_member(**kwargs: Any) -> Dict[str, Any]:
            member_id = kwargs.get("MemberId", {}).get("UserId", "")
            return mock_aws_responses["list_group_memberships_for_member"].get(
                member_id, {"GroupMemberships": [], "NextToken": None}
            )

        identity_store_client.list_group_memberships_for_member.side_effect = (
            mock_group_memberships_for_member
        )

        def mock_group_memberships(**kwargs: Any) -> Dict[str, Any]:
            group_id = kwargs.get("GroupId", "")
            return mock_aws_responses["list_group_memberships"].get(
                group_id, {"GroupMemberships": [], "NextToken": None}
            )

        identity_store_client.list_group_memberships.side_effect = mock_group_memberships

        # Mock Identity Center client
        identity_center_client = Mock()
        identity_center_client.list_instances.return_value = mock_aws_responses["list_instances"]
        identity_center_client.list_permission_sets.return_value = mock_aws_responses[
            "list_permission_sets"
        ]

        # Mock permission set details
        def mock_describe_permission_set(**kwargs: Any) -> Dict[str, Any]:
            ps_arn = kwargs.get("PermissionSetArn", "")
            if "ps-admin" in ps_arn:
                return mock_aws_responses["describe_permission_set"]["admin"]
            elif "ps-dev" in ps_arn:
                return mock_aws_responses["describe_permission_set"]["dev"]
            elif "ps-readonly" in ps_arn:
                return mock_aws_responses["describe_permission_set"]["readonly"]
            return {"PermissionSet": {}}

        identity_center_client.describe_permission_set.side_effect = mock_describe_permission_set

        # Mock managed policies
        def mock_list_managed_policies(**kwargs: Any) -> Dict[str, Any]:
            ps_arn = kwargs.get("PermissionSetArn", "")
            if "ps-admin" in ps_arn:
                return mock_aws_responses["list_managed_policies_in_permission_set"]["admin"]
            elif "ps-dev" in ps_arn:
                return mock_aws_responses["list_managed_policies_in_permission_set"]["dev"]
            elif "ps-readonly" in ps_arn:
                return mock_aws_responses["list_managed_policies_in_permission_set"]["readonly"]
            return {"AttachedManagedPolicies": []}

        identity_center_client.list_managed_policies_in_permission_set.side_effect = (
            mock_list_managed_policies
        )
        identity_center_client.list_customer_managed_policy_references_in_permission_set.return_value = {
            "CustomerManagedPolicyReferences": []
        }
        identity_center_client.get_inline_policy_for_permission_set.return_value = {
            "InlinePolicy": ""
        }

        def mock_accounts_for_permission_set(**kwargs: Any) -> Dict[str, Any]:
            permission_set_arn = kwargs.get("PermissionSetArn", "")
            if "ps-admin" in permission_set_arn:
                account_ids = ["123456789012"]
            elif "ps-dev" in permission_set_arn:
                account_ids = ["123456789012", "123456789013"]
            else:
                account_ids = []
            return {"AccountIds": account_ids, "NextToken": None}

        identity_center_client.list_accounts_for_provisioned_permission_set.side_effect = (
            mock_accounts_for_permission_set
        )

        # Mock account assignments
        def mock_list_account_assignments(**kwargs: Any) -> Dict[str, Any]:
            account_id = kwargs.get("AccountId", "")
            return mock_aws_responses["list_account_assignments"].get(
                account_id, {"AccountAssignments": [], "NextToken": None}
            )

        identity_center_client.list_account_assignments.side_effect = mock_list_account_assignments

        # Mock Organizations client
        organizations_client = Mock()
        organizations_client.list_accounts.return_value = mock_aws_responses["list_accounts"]
        organizations_client.list_tags_for_resource.return_value = {"Tags": []}

        # Wire up clients
        client_manager.get_identity_store_client.return_value = identity_store_client
        client_manager.get_identity_center_client.return_value = identity_center_client
        client_manager.get_organizations_client.return_value = organizations_client

        return client_manager

    @pytest.mark.asyncio
    async def test_full_statistics_pipeline(self, mock_client_manager: Mock) -> None:
        """Test the complete statistics generation pipeline."""
        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        manager = StatisticsManager(mock_client_manager, instance_arn)

        # Generate complete statistics
        result = await manager.generate_statistics()

        # Verify the complete report structure
        assert isinstance(result, StatisticsReport)
        assert result.metadata is not None
        assert result.user_group_metrics is not None
        assert result.permission_set_metrics is not None
        assert result.account_metrics is not None
        assert result.assignment_patterns is not None
        assert result.governance_view is not None

        # Verify specific metrics from our mock data
        assert result.user_group_metrics.total_users == 3
        assert result.user_group_metrics.total_groups == 3
        assert result.permission_set_metrics.total_permission_sets == 3
        assert result.account_metrics.total_accounts == 2

        # Verify orphaned resource detection
        assert "orphaned.user" in result.user_group_metrics.orphaned_users
        assert "Empty Group" in result.user_group_metrics.orphaned_groups

    @pytest.mark.asyncio
    async def test_cross_account_scenario(self, mock_client_manager: Mock) -> None:
        """Test statistics generation with cross-account assignments."""
        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        manager = StatisticsManager(mock_client_manager, instance_arn)

        result = await manager.generate_statistics()

        # Verify cross-account analysis
        assert result.account_metrics.total_accounts == 2

        # user1 should have assignments in production account
        prod_assignments = result.account_metrics.assignments_per_account.get("123456789012", 0)
        assert prod_assignments > 0

        # user2 should have assignments in development account
        dev_assignments = result.account_metrics.assignments_per_account.get("123456789013", 0)
        assert dev_assignments > 0

    @pytest.mark.asyncio
    async def test_privileged_access_detection(self, mock_client_manager: Mock) -> None:
        """Test privileged access detection in realistic scenario."""
        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        manager = StatisticsManager(mock_client_manager, instance_arn)

        result = await manager.generate_statistics()

        # Verify privileged permission sets are detected
        privileged_ps = result.permission_set_metrics.privileged_permission_sets
        assert "AdminAccess" in privileged_ps
        assert "DeveloperAccess" in privileged_ps  # PowerUserAccess is privileged
        assert "ReadOnlyAccess" not in privileged_ps

        # Verify governance view includes privileged access report
        assert result.governance_view.privileged_access_report is not None
        assert len(result.governance_view.privileged_access_report.admin_permission_sets) > 0

    @pytest.mark.asyncio
    async def test_assignment_patterns_analysis(self, mock_client_manager: Mock) -> None:
        """Test assignment patterns analysis with realistic data."""
        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        manager = StatisticsManager(mock_client_manager, instance_arn)

        result = await manager.generate_statistics()

        # Verify assignment patterns
        patterns = result.assignment_patterns
        assert patterns.average_assignments_per_user > 0
        assert len(patterns.users_with_most_assignments) > 0
        assert len(patterns.groups_with_most_assignments) > 0

    @pytest.mark.asyncio
    async def test_governance_analysis(self, mock_client_manager: Mock) -> None:
        """Test governance analysis with realistic scenarios."""
        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        manager = StatisticsManager(mock_client_manager, instance_arn)

        result = await manager.generate_statistics()

        # Verify governance view components
        governance = result.governance_view
        assert governance.access_matrix is not None
        assert governance.privileged_access_report is not None
        assert governance.empty_mappings is not None

        # Verify access matrix has realistic data
        access_matrix = governance.access_matrix
        assert len(access_matrix.user_to_accounts) > 0
        assert len(access_matrix.account_to_users) > 0

    @pytest.mark.asyncio
    async def test_export_integration(self, mock_client_manager: Mock) -> None:
        """Test export functionality integration."""
        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        manager = StatisticsManager(mock_client_manager, instance_arn)

        result = await manager.generate_statistics()

        # Test JSON export
        json_output = manager.exporter.export_to_json(result)
        assert json_output is not None
        assert len(json_output) > 0
        assert "statistics_report" in json_output

        # Test CSV export
        csv_output = manager.exporter.export_to_csv(result)
        assert csv_output is not None
        assert len(csv_output) > 0

        # Test text export
        text_output = manager.exporter.export_to_text(result)
        assert text_output is not None
        assert len(text_output) > 0

    @pytest.mark.asyncio
    async def test_filtered_statistics(self, mock_client_manager: Mock) -> None:
        """Test statistics generation with filters applied."""
        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        manager = StatisticsManager(mock_client_manager, instance_arn)

        # Generate statistics with account filter
        filters = {"account": "123456789012"}
        result = await manager.generate_statistics(filters=filters)

        # Verify filter is recorded in metadata
        assert result.metadata.filters_applied == filters

        # Result should still be complete (filtering affects analysis, not collection)
        assert result.user_group_metrics.total_users == 3
        assert result.account_metrics.total_accounts == 2

    @pytest.mark.asyncio
    async def test_category_specific_generation(self, mock_client_manager: Mock) -> None:
        """Test generation of specific statistic categories."""
        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        manager = StatisticsManager(mock_client_manager, instance_arn)

        # Test user-specific statistics
        user_metrics = await manager.generate_user_group_statistics()
        assert user_metrics.total_users == 3
        assert user_metrics.total_groups == 3

        # Test permission set statistics
        ps_metrics = await manager.generate_permission_set_statistics()
        assert ps_metrics.total_permission_sets == 3

        # Test account statistics
        account_metrics = await manager.generate_account_statistics()
        assert account_metrics.total_accounts == 2

    @pytest.mark.asyncio
    async def test_error_resilience(
        self, mock_client_manager: Mock, mock_aws_responses: Dict[str, Any]
    ) -> None:
        """Test system resilience to partial API failures."""
        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        manager = StatisticsManager(mock_client_manager, instance_arn)

        # Simulate partial failure in one API call
        identity_store_client = mock_client_manager.get_identity_store_client.return_value
        identity_store_client.list_groups.side_effect = [
            Exception("Temporary API failure"),
            mock_aws_responses["list_groups"],
        ]

        # The collector retries transient errors and returns a complete report.
        result = await manager.generate_statistics()
        assert isinstance(result, StatisticsReport)

    @pytest.mark.asyncio
    async def test_large_dataset_handling(self, mock_client_manager: Mock) -> None:
        """Test handling of larger datasets with pagination."""
        # Modify mock responses to simulate larger dataset
        large_users = []
        for i in range(50):
            large_users.append(
                {
                    "UserId": f"user{i}",
                    "UserName": f"user{i}",
                    "DisplayName": f"User {i}",
                    "Emails": [{"Value": f"user{i}@example.com", "Primary": True}],
                    "Active": True,
                }
            )

        # Update mock response
        identity_store_client = mock_client_manager.get_identity_store_client.return_value
        identity_store_client.list_users.return_value = {
            "Users": large_users,
            "NextToken": None,
        }

        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        manager = StatisticsManager(mock_client_manager, instance_arn)

        # Should handle larger dataset efficiently
        result = await manager.generate_statistics()

        assert result.user_group_metrics.total_users == 50
        assert isinstance(result, StatisticsReport)

    @pytest.mark.asyncio
    async def test_empty_environment(self, mock_client_manager: Mock) -> None:
        """Test statistics generation in empty AWS environment."""
        # Mock empty responses
        identity_store_client = mock_client_manager.get_identity_store_client.return_value
        identity_center_client = mock_client_manager.get_identity_center_client.return_value
        organizations_client = mock_client_manager.get_organizations_client.return_value

        identity_store_client.list_users.return_value = {"Users": [], "NextToken": None}
        identity_store_client.list_groups.return_value = {"Groups": [], "NextToken": None}
        identity_center_client.list_permission_sets.return_value = {
            "PermissionSets": [],
            "NextToken": None,
        }
        organizations_client.list_accounts.return_value = {"Accounts": [], "NextToken": None}

        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        manager = StatisticsManager(mock_client_manager, instance_arn)

        result = await manager.generate_statistics()

        # Should handle empty environment gracefully
        assert isinstance(result, StatisticsReport)
        assert result.user_group_metrics.total_users == 0
        assert result.user_group_metrics.total_groups == 0
        assert result.permission_set_metrics.total_permission_sets == 0
        assert result.account_metrics.total_accounts == 0
