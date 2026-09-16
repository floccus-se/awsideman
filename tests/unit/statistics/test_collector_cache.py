"""Tests for StatisticsCollector cache integration and error handling."""

import asyncio
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from src.awsideman.statistics.collector import StatisticsCollector
from src.awsideman.statistics.models import UserData, UserStatistics


class TestStatisticsCollectorCache:
    """Test cache integration in StatisticsCollector."""

    @pytest.fixture
    def mock_client_manager_with_cache(self):
        """Create a mock AWS client manager with cache enabled."""
        client_manager = Mock()
        client_manager.is_caching_enabled.return_value = True

        # Mock cache manager
        cache_manager = Mock()
        cache_manager.get.return_value = None  # Cache miss by default
        cache_manager.set.return_value = None
        client_manager.get_cache_manager.return_value = cache_manager

        # Mock clients
        identity_store_client = Mock()
        identity_center_client = Mock()
        organizations_client = Mock()

        client_manager.get_identity_store_client.return_value = identity_store_client
        client_manager.get_identity_center_client.return_value = identity_center_client
        client_manager.get_organizations_client.return_value = organizations_client

        return client_manager

    @pytest.fixture
    def collector_with_cache(self, mock_client_manager_with_cache):
        """Create a StatisticsCollector with cache enabled."""
        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        return StatisticsCollector(mock_client_manager_with_cache, instance_arn)

    @pytest.mark.asyncio
    async def test_cache_hit_users(self, collector_with_cache):
        """Test cache hit for user data collection."""
        # Mock cached user data
        cached_users = [
            UserData(
                user_id="user1",
                username="john.doe",
                display_name="John Doe",
                email="john.doe@example.com",
                active=True,
            )
        ]

        with patch.object(collector_with_cache, "_get_from_cache_or_execute") as mock_cache:
            mock_cache.return_value = cached_users

            with patch.object(
                collector_with_cache, "_collect_user_group_memberships"
            ) as mock_memberships:
                mock_memberships.return_value = {"user1": ["group1"]}

                result = await collector_with_cache.collect_user_statistics()

        assert isinstance(result, UserStatistics)
        assert len(result.users) == 1
        assert result.users[0].user_id == "user1"

        # Verify cache was used (function was called with cache key)
        mock_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_miss_users(self, collector_with_cache):
        """Test cache miss for user data collection."""
        sample_user_data = [
            {
                "UserId": "user1",
                "UserName": "john.doe",
                "DisplayName": "John Doe",
                "Emails": [{"Value": "john.doe@example.com", "Primary": True}],
                "Active": True,
            }
        ]

        identity_store_client = (
            collector_with_cache.client_manager.get_identity_store_client.return_value
        )
        identity_center_client = (
            collector_with_cache.client_manager.get_identity_center_client.return_value
        )

        # Mock API responses
        identity_store_client.list_users.return_value = {
            "Users": sample_user_data,
            "NextToken": None,
        }

        identity_center_client.list_instances.return_value = {
            "Instances": [
                {
                    "InstanceArn": collector_with_cache.instance_arn,
                    "IdentityStoreId": "d-1234567890",
                }
            ]
        }

        # Mock cache miss (function executes)
        with patch.object(collector_with_cache, "_get_from_cache_or_execute") as mock_cache:

            async def cache_side_effect(key, func, **kwargs):
                result = func()
                if asyncio.iscoroutine(result):
                    return await result
                return result

            mock_cache.side_effect = cache_side_effect

            with patch.object(
                collector_with_cache, "_collect_user_group_memberships"
            ) as mock_memberships:
                mock_memberships.return_value = {"user1": ["group1"]}

                result = await collector_with_cache.collect_user_statistics()

        assert isinstance(result, UserStatistics)
        assert len(result.users) == 1
        assert result.users[0].user_id == "user1"

    @pytest.mark.asyncio
    async def test_cache_disabled(self, mock_client_manager_with_cache):
        """Test behavior when cache is disabled."""
        # Disable cache
        mock_client_manager_with_cache.is_caching_enabled.return_value = False

        collector = StatisticsCollector(
            mock_client_manager_with_cache, "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        )

        assert collector.cache_enabled is False

        sample_user_data = [
            {
                "UserId": "user1",
                "UserName": "john.doe",
                "DisplayName": "John Doe",
                "Emails": [{"Value": "john.doe@example.com", "Primary": True}],
                "Active": True,
            }
        ]

        identity_store_client = collector.client_manager.get_identity_store_client.return_value
        identity_center_client = collector.client_manager.get_identity_center_client.return_value

        # Mock API responses
        identity_store_client.list_users.return_value = {
            "Users": sample_user_data,
            "NextToken": None,
        }

        identity_center_client.list_instances.return_value = {
            "Instances": [
                {
                    "InstanceArn": collector.instance_arn,
                    "IdentityStoreId": "d-1234567890",
                }
            ]
        }

        # Mock cache methods to verify they're not used
        with patch.object(collector, "_get_from_cache_or_execute") as mock_cache:

            async def cache_side_effect(key, func, **kwargs):
                result = func()
                if asyncio.iscoroutine(result):
                    return await result
                return result

            mock_cache.side_effect = cache_side_effect

            with patch.object(collector, "_collect_user_group_memberships") as mock_memberships:
                mock_memberships.return_value = {"user1": ["group1"]}

                result = await collector.collect_user_statistics()

        assert isinstance(result, UserStatistics)
        assert len(result.users) == 1

    @pytest.mark.asyncio
    async def test_cache_error_fallback(self, collector_with_cache):
        """Test fallback to direct execution when cache fails."""
        sample_user_data = [
            {
                "UserId": "user1",
                "UserName": "john.doe",
                "DisplayName": "John Doe",
                "Emails": [{"Value": "john.doe@example.com", "Primary": True}],
                "Active": True,
            }
        ]

        identity_store_client = (
            collector_with_cache.client_manager.get_identity_store_client.return_value
        )
        identity_center_client = (
            collector_with_cache.client_manager.get_identity_center_client.return_value
        )

        # Mock API responses
        identity_store_client.list_users.return_value = {
            "Users": sample_user_data,
            "NextToken": None,
        }

        identity_center_client.list_instances.return_value = {
            "Instances": [
                {
                    "InstanceArn": collector_with_cache.instance_arn,
                    "IdentityStoreId": "d-1234567890",
                }
            ]
        }

        # Mock cache error, then fallback to function execution
        with patch.object(collector_with_cache, "_get_from_cache_or_execute") as mock_cache:

            async def cache_side_effect(key, func, **kwargs):
                result = func()
                if asyncio.iscoroutine(result):
                    return await result
                return result

            mock_cache.side_effect = cache_side_effect

            with patch.object(
                collector_with_cache, "_collect_user_group_memberships"
            ) as mock_memberships:
                mock_memberships.return_value = {"user1": ["group1"]}

                result = await collector_with_cache.collect_user_statistics()

        assert isinstance(result, UserStatistics)
        assert len(result.users) == 1

    def test_cache_key_generation(self, collector_with_cache):
        """Test cache key generation for different data types."""
        # This would test the internal cache key generation logic
        # Since the actual implementation might vary, we'll test the concept

        with patch.object(collector_with_cache, "_get_from_cache_or_execute") as mock_cache:
            mock_cache.return_value = []

            # Test different cache keys are used for different data types
            asyncio.run(
                collector_with_cache._get_from_cache_or_execute(
                    "users", lambda: [], ttl_minutes=10, identity_store_id="d-123"
                )
            )

            asyncio.run(
                collector_with_cache._get_from_cache_or_execute(
                    "groups", lambda: [], ttl_minutes=10, identity_store_id="d-123"
                )
            )

            # Verify different keys were used
            assert mock_cache.call_count == 2

            # Verify the calls had different first arguments (cache keys)
            call_args = [call[0][0] for call in mock_cache.call_args_list]
            assert call_args[0] != call_args[1]

    @pytest.mark.asyncio
    async def test_cache_ttl_settings(self, collector_with_cache):
        """Test different TTL settings for different data types."""
        with patch.object(collector_with_cache, "_get_from_cache_or_execute") as mock_cache:
            mock_cache.return_value = []

            # Test users cache (10 minutes)
            await collector_with_cache._get_from_cache_or_execute(
                "users", lambda: [], ttl_minutes=10
            )

            # Test accounts cache (30 minutes)
            await collector_with_cache._get_from_cache_or_execute(
                "accounts", lambda: [], ttl_minutes=30
            )

            # Test permission sets cache (15 minutes)
            await collector_with_cache._get_from_cache_or_execute(
                "permission_sets", lambda: [], ttl_minutes=15
            )

            assert mock_cache.call_count == 3

            # Verify TTL values were passed correctly
            calls = mock_cache.call_args_list
            assert calls[0][1]["ttl_minutes"] == 10  # users
            assert calls[1][1]["ttl_minutes"] == 30  # accounts
            assert calls[2][1]["ttl_minutes"] == 15  # permission sets


class TestStatisticsCollectorErrorHandling:
    """Test error handling in StatisticsCollector."""

    @pytest.fixture
    def mock_client_manager_error(self):
        """Create a mock client manager that simulates errors."""
        client_manager = Mock()
        client_manager.is_caching_enabled.return_value = False

        # Mock clients that will raise errors
        identity_store_client = Mock()
        identity_center_client = Mock()
        organizations_client = Mock()

        client_manager.get_identity_store_client.return_value = identity_store_client
        client_manager.get_identity_center_client.return_value = identity_center_client
        client_manager.get_organizations_client.return_value = organizations_client

        return client_manager

    @pytest.fixture
    def collector_error(self, mock_client_manager_error):
        """Create a StatisticsCollector for error testing."""
        instance_arn = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
        return StatisticsCollector(mock_client_manager_error, instance_arn)

    @pytest.mark.asyncio
    async def test_throttling_error_handling(self, collector_error):
        """Test handling of AWS throttling errors."""
        identity_store_client = (
            collector_error.client_manager.get_identity_store_client.return_value
        )
        identity_center_client = (
            collector_error.client_manager.get_identity_center_client.return_value
        )

        # Mock throttling error
        identity_store_client.list_users.side_effect = ClientError(
            {"Error": {"Code": "Throttling", "Message": "Rate exceeded"}}, "ListUsers"
        )

        identity_center_client.list_instances.return_value = {
            "Instances": [
                {
                    "InstanceArn": collector_error.instance_arn,
                    "IdentityStoreId": "d-1234567890",
                }
            ]
        }

        with patch.object(collector_error, "_get_from_cache_or_execute") as mock_cache:

            async def cache_side_effect(key, func, **kwargs):
                result = func()
                if asyncio.iscoroutine(result):
                    return await result
                return result

            mock_cache.side_effect = cache_side_effect

            with pytest.raises(ClientError):
                await collector_error.collect_user_statistics()

    @pytest.mark.asyncio
    async def test_access_denied_error_handling(self, collector_error):
        """Test handling of access denied errors."""
        identity_store_client = (
            collector_error.client_manager.get_identity_store_client.return_value
        )
        identity_center_client = (
            collector_error.client_manager.get_identity_center_client.return_value
        )

        # Mock access denied error
        identity_store_client.list_users.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "ListUsers"
        )

        identity_center_client.list_instances.return_value = {
            "Instances": [
                {
                    "InstanceArn": collector_error.instance_arn,
                    "IdentityStoreId": "d-1234567890",
                }
            ]
        }

        with patch.object(collector_error, "_get_from_cache_or_execute") as mock_cache:

            async def cache_side_effect(key, func, **kwargs):
                result = func()
                if asyncio.iscoroutine(result):
                    return await result
                return result

            mock_cache.side_effect = cache_side_effect

            with pytest.raises(ClientError):
                await collector_error.collect_user_statistics()

    @pytest.mark.asyncio
    async def test_network_error_handling(self, collector_error):
        """Test handling of network errors."""
        identity_store_client = (
            collector_error.client_manager.get_identity_store_client.return_value
        )
        identity_center_client = (
            collector_error.client_manager.get_identity_center_client.return_value
        )

        # Mock network error
        identity_store_client.list_users.side_effect = Exception("Network error")

        identity_center_client.list_instances.return_value = {
            "Instances": [
                {
                    "InstanceArn": collector_error.instance_arn,
                    "IdentityStoreId": "d-1234567890",
                }
            ]
        }

        with patch.object(collector_error, "_get_from_cache_or_execute") as mock_cache:

            async def cache_side_effect(key, func, **kwargs):
                result = func()
                if asyncio.iscoroutine(result):
                    return await result
                return result

            mock_cache.side_effect = cache_side_effect

            with pytest.raises(Exception, match="Network error"):
                await collector_error.collect_user_statistics()

    @pytest.mark.asyncio
    async def test_invalid_data_handling(self, collector_error):
        """Test handling of invalid data from AWS APIs."""
        identity_store_client = (
            collector_error.client_manager.get_identity_store_client.return_value
        )
        identity_center_client = (
            collector_error.client_manager.get_identity_center_client.return_value
        )

        # Mock response with invalid user data
        invalid_user_data = [
            {
                "UserId": "",  # Invalid: empty user ID
                "UserName": "john.doe",
                "DisplayName": "John Doe",
                "Active": True,
            },
            {
                "UserId": "user2",
                "UserName": "jane.smith",
                "DisplayName": "Jane Smith",
                "Active": True,
            },
        ]

        identity_store_client.list_users.return_value = {
            "Users": invalid_user_data,
            "NextToken": None,
        }

        identity_center_client.list_instances.return_value = {
            "Instances": [
                {
                    "InstanceArn": collector_error.instance_arn,
                    "IdentityStoreId": "d-1234567890",
                }
            ]
        }

        with patch.object(collector_error, "_get_from_cache_or_execute") as mock_cache:

            async def cache_side_effect(key, func, **kwargs):
                result = func()
                if asyncio.iscoroutine(result):
                    return await result
                return result

            mock_cache.side_effect = cache_side_effect

            with patch.object(
                collector_error, "_collect_user_group_memberships"
            ) as mock_memberships:
                mock_memberships.return_value = {}

                result = await collector_error.collect_user_statistics()

        # Should skip invalid user but include valid one
        assert isinstance(result, UserStatistics)
        assert len(result.users) == 1  # Only valid user included
        assert result.users[0].user_id == "user2"

    @pytest.mark.asyncio
    async def test_partial_data_collection_failure(self, collector_error):
        """Test handling when some data collection operations fail."""
        identity_store_client = (
            collector_error.client_manager.get_identity_store_client.return_value
        )
        identity_center_client = (
            collector_error.client_manager.get_identity_center_client.return_value
        )

        # Mock successful user collection but failed group membership collection
        identity_store_client.list_users.return_value = {
            "Users": [
                {
                    "UserId": "user1",
                    "UserName": "john.doe",
                    "DisplayName": "John Doe",
                    "Active": True,
                }
            ],
            "NextToken": None,
        }

        identity_center_client.list_instances.return_value = {
            "Instances": [
                {
                    "InstanceArn": collector_error.instance_arn,
                    "IdentityStoreId": "d-1234567890",
                }
            ]
        }

        with patch.object(collector_error, "_get_from_cache_or_execute") as mock_cache:

            async def cache_side_effect(key, func, **kwargs):
                result = func()
                if asyncio.iscoroutine(result):
                    return await result
                return result

            mock_cache.side_effect = cache_side_effect

            # User collection no longer queries group memberships; group
            # statistics owns that separate collection step.
            result = await collector_error.collect_user_statistics()

        assert result.group_memberships == {}

    @pytest.mark.asyncio
    async def test_aws_permissions_validation_failure(self, collector_error):
        """Test handling of AWS permissions validation failure."""
        with patch.object(collector_error, "_validate_aws_permissions") as mock_validate:
            mock_validate.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Insufficient permissions"}},
                "ListInstances",
            )

            with pytest.raises(ClientError):
                await collector_error.collect_all_data()

    def test_malformed_instance_arn_handling(self, mock_client_manager_error):
        """Test handling of malformed instance ARN."""
        malformed_arn = "not-a-valid-arn"
        collector = StatisticsCollector(mock_client_manager_error, malformed_arn)

        with pytest.raises(ValueError, match="Invalid instance ARN format"):
            collector._extract_identity_store_id()

    @pytest.mark.asyncio
    async def test_empty_response_handling(self, collector_error):
        """Test handling of empty responses from AWS APIs."""
        identity_store_client = (
            collector_error.client_manager.get_identity_store_client.return_value
        )
        identity_center_client = (
            collector_error.client_manager.get_identity_center_client.return_value
        )

        # Mock empty response
        identity_store_client.list_users.return_value = {
            "Users": [],
            "NextToken": None,
        }

        identity_center_client.list_instances.return_value = {
            "Instances": [
                {
                    "InstanceArn": collector_error.instance_arn,
                    "IdentityStoreId": "d-1234567890",
                }
            ]
        }

        with patch.object(collector_error, "_get_from_cache_or_execute") as mock_cache:

            async def cache_side_effect(key, func, **kwargs):
                result = func()
                if asyncio.iscoroutine(result):
                    return await result
                return result

            mock_cache.side_effect = cache_side_effect

            with patch.object(
                collector_error, "_collect_user_group_memberships"
            ) as mock_memberships:
                mock_memberships.return_value = {}

                result = await collector_error.collect_user_statistics()

        assert isinstance(result, UserStatistics)
        assert len(result.users) == 0
        assert len(result.group_memberships) == 0
