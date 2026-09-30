"""Tests for assignment revoke command."""

from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from src.awsideman.commands.assignment.revoke import (
    _delete_account_assignment_with_conflict_retry,
    revoke_single_account,
)


def _client_error(code: str) -> ClientError:
    return ClientError(
        {"Error": {"Code": code, "Message": "test error"}},
        "DeleteAccountAssignment",
    )


def test_delete_account_assignment_retries_conflict_then_succeeds():
    """Propagation conflicts should be retried with exponential backoff."""
    client = Mock()
    expected_response = {
        "AccountAssignmentDeletionStatus": {
            "Status": "IN_PROGRESS",
            "RequestId": "request-123",
        }
    }
    client.delete_account_assignment.side_effect = [
        _client_error("ConflictException"),
        expected_response,
    ]

    with patch("src.awsideman.commands.assignment.revoke.time.sleep") as sleep:
        response = _delete_account_assignment_with_conflict_retry(
            client, {"TargetId": "123456789012"}
        )

    assert response == expected_response
    assert client.delete_account_assignment.call_count == 2
    sleep.assert_called_once_with(1.0)


def test_delete_account_assignment_does_not_retry_non_conflict():
    """Non-conflict API errors should be returned to normal error handling."""
    client = Mock()
    client.delete_account_assignment.side_effect = _client_error("AccessDeniedException")

    with pytest.raises(ClientError):
        _delete_account_assignment_with_conflict_retry(client, {"TargetId": "123456789012"})

    client.delete_account_assignment.assert_called_once()


def test_verified_single_account_revoke_calls_delete_once():
    """Verification must not execute an early duplicate revocation."""
    sso_client = Mock()
    sso_client.list_account_assignments.return_value = {
        "AccountAssignments": [{"PrincipalId": "group-123", "PrincipalType": "GROUP"}]
    }
    sso_client.delete_account_assignment.return_value = {
        "AccountAssignmentDeletionStatus": {
            "Status": "IN_PROGRESS",
            "RequestId": "request-123",
        }
    }

    aws_client = Mock()
    aws_client.get_sso_admin_client.return_value = sso_client
    aws_client.get_identity_store_client.return_value = Mock()
    aws_client.is_caching_enabled.return_value = False

    resolver = Mock()
    resolver.resolve_principal_name.side_effect = [
        Mock(success=False),
        Mock(success=True, resolved_value="group-123"),
    ]

    with (
        patch(
            "src.awsideman.commands.assignment.revoke.validate_profile",
            return_value=("default", {}),
        ),
        patch(
            "src.awsideman.commands.assignment.revoke.validate_sso_instance",
            return_value=("instance-arn", "identity-store-id"),
        ),
        patch(
            "src.awsideman.commands.assignment.revoke.AWSClientManager",
            return_value=aws_client,
        ),
        patch(
            "src.awsideman.commands.assignment.revoke.resolve_permission_set_identifier",
            return_value="permission-set-arn",
        ),
        patch(
            "src.awsideman.commands.assignment.revoke.ResourceResolver",
            return_value=resolver,
        ),
        patch(
            "src.awsideman.commands.assignment.revoke.resolve_permission_set_info",
            return_value={"Name": "Audit"},
        ),
        patch(
            "src.awsideman.commands.assignment.revoke.resolve_principal_info",
            return_value={"DisplayName": "CADMINS"},
        ),
        patch("src.awsideman.commands.assignment.revoke.log_individual_operation"),
    ):
        revoke_single_account(
            permission_set_name="Audit",
            principal_name="CADMINS",
            account_id="123456789012",
            force=True,
        )

    sso_client.delete_account_assignment.assert_called_once()


def test_revoke_permission_set_module_import():
    """Test that the revoke_permission_set module can be imported."""
    try:
        from src.awsideman.commands.assignment.revoke import revoke_permission_set

        assert revoke_permission_set is not None
        assert callable(revoke_permission_set)
    except ImportError as e:
        pytest.fail(f"Failed to import revoke_permission_set: {e}")


def test_revoke_permission_set_function_signature():
    """Test that the revoke_permission_set function has the expected signature."""
    import inspect

    from src.awsideman.commands.assignment.revoke import revoke_permission_set

    # Check that the function exists and is callable
    assert callable(revoke_permission_set)

    # Check that it has the expected parameters
    sig = inspect.signature(revoke_permission_set)
    expected_params = {
        "permission_set_name",
        "principal_name",
        "account_id",
        "force",
        "profile",
    }

    actual_params = set(sig.parameters.keys())
    assert expected_params.issubset(
        actual_params
    ), f"Missing parameters: {expected_params - actual_params}"


def test_revoke_permission_set_help_text():
    """Test that the revoke_permission_set function has help text."""
    from src.awsideman.commands.assignment.revoke import revoke_permission_set

    # Check that the function has a docstring
    assert revoke_permission_set.__doc__ is not None
    assert len(revoke_permission_set.__doc__.strip()) > 0

    # Check that the docstring contains expected content
    doc = revoke_permission_set.__doc__.lower()
    assert "revoke" in doc
    assert "permission set" in doc
    assert "principal" in doc


def test_revoke_permission_set_typer_integration():
    """Test that the revoke_permission_set function is properly integrated with Typer."""
    from src.awsideman.commands.assignment.revoke import revoke_permission_set

    # Check that the function has the expected type hints
    assert hasattr(revoke_permission_set, "__annotations__")

    annotations = revoke_permission_set.__annotations__
    assert "permission_set_name" in annotations
    assert "principal_name" in annotations
    assert "account_id" in annotations
    assert "force" in annotations
    assert "profile" in annotations


def test_revoke_permission_set_parameter_types():
    """Test that the revoke_permission_set function has correct parameter types."""
    import inspect

    from src.awsideman.commands.assignment.revoke import revoke_permission_set

    sig = inspect.signature(revoke_permission_set)

    # Check that permission_set_name is a string
    assert sig.parameters["permission_set_name"].annotation == str

    # Check that principal_name is a string
    assert sig.parameters["principal_name"].annotation == str

    # Check that account_id is a string (or Optional[str])
    account_id_param = sig.parameters["account_id"]
    assert account_id_param.annotation == str or "Optional" in str(account_id_param.annotation)

    # principal_type parameter has been removed - auto-detection is now used

    # Check that force is a boolean
    assert sig.parameters["force"].annotation == bool

    # Check that profile is optional string
    profile_param = sig.parameters["profile"]
    assert profile_param.annotation == str or "Optional" in str(profile_param.annotation)
