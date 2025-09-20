"""Regression tests for control-flow defects found during the repository audit."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import boto3
import pytest
from botocore.client import BaseClient
from botocore.stub import Stubber

from src.awsideman.backup_restore.models import ConflictStrategy, UserData
from src.awsideman.backup_restore.restore_manager import ConflictResolver, RestoreProcessor
from src.awsideman.permission_cloning.assignment_copier import AssignmentCopier
from src.awsideman.permission_cloning.rollback_integration import (
    PermissionCloningRollbackIntegration,
)
from src.awsideman.rollback.logger import OperationLogger
from src.awsideman.rollback.models import (
    AssignmentState,
    OperationRecord,
    OperationResult,
    OperationType,
    PermissionCloningOperationRecord,
    PrincipalType,
    RollbackAction,
    RollbackActionType,
    RollbackPlan,
)
from src.awsideman.rollback.processor import RollbackProcessor
from src.awsideman.rollback.storage import OperationStore
from src.awsideman.statistics.collector import StatisticsCollector

INSTANCE_ARN = "arn:aws:sso:::instance/ssoins-1234567890abcdef"
PERMISSION_SET_ARN = "arn:aws:sso:::permissionSet/ssoins-1234567890abcdef/ps-1234567890abcdef"
ACCOUNT_ID = "123456789012"
PRINCIPAL_ID = "12345678-1234-1234-1234-123456789012"


@pytest.fixture
def copy_record() -> PermissionCloningOperationRecord:
    return PermissionCloningOperationRecord.create(
        operation_type=OperationType.COPY_ASSIGNMENTS,
        source_entity_id="source-user",
        source_entity_type=PrincipalType.USER,
        source_entity_name="Source",
        target_entity_id=PRINCIPAL_ID,
        target_entity_type=PrincipalType.GROUP,
        target_entity_name="Target",
        assignments_copied=[f"{PERMISSION_SET_ARN}:{ACCOUNT_ID}:{PRINCIPAL_ID}"],
        permission_sets_involved=[PERMISSION_SET_ARN],
        accounts_affected=[ACCOUNT_ID],
    )


@pytest.fixture
def sso_client() -> BaseClient:
    return boto3.client(
        "sso-admin",
        region_name="eu-west-1",
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
    )


def test_store_updates_operation_instead_of_returning_stale_record(
    tmp_path: Path, copy_record: PermissionCloningOperationRecord
) -> None:
    store = OperationStore(str(tmp_path))
    store.store_operation(copy_record)
    copy_record.rolled_back = True
    copy_record.rollback_operation_id = "rollback-id"
    store.store_operation(copy_record)

    assert store.get_operation(copy_record.operation_id).rolled_back is True
    assert len(store.get_operations()) == 1


def test_copy_rollback_preserves_arn_and_persists_completion(
    tmp_path: Path, copy_record: PermissionCloningOperationRecord
) -> None:
    processor = Mock(store=OperationStore(str(tmp_path)))
    processor.store.store_operation(copy_record)
    integration = PermissionCloningRollbackIntegration(Mock(), processor, Mock())
    integration._revoke_assignment = Mock()

    result = integration.rollback_assignment_copy_operation(copy_record.operation_id)

    assert result["success"] is True
    integration._revoke_assignment.assert_called_once_with(
        PRINCIPAL_ID, PERMISSION_SET_ARN, ACCOUNT_ID, PrincipalType.GROUP
    )
    with pytest.raises(ValueError, match="already been rolled back"):
        integration.rollback_assignment_copy_operation(copy_record.operation_id)


def test_failed_copy_rollback_remains_retryable(
    tmp_path: Path, copy_record: PermissionCloningOperationRecord
) -> None:
    processor = Mock(store=OperationStore(str(tmp_path)))
    processor.store.store_operation(copy_record)
    integration = PermissionCloningRollbackIntegration(Mock(), processor, Mock())
    integration._revoke_assignment = Mock(side_effect=RuntimeError("Access denied"))

    result = integration.rollback_assignment_copy_operation(copy_record.operation_id)

    assert result["success"] is False
    assert processor.store.get_operation(copy_record.operation_id).rolled_back is False
    assert all(not op.rolled_back for op in processor.store.get_operations())
    integration._revoke_assignment.side_effect = None
    assert integration.rollback_assignment_copy_operation(copy_record.operation_id)["success"]


@pytest.mark.parametrize("principal_type", ["USER", "GROUP"])
def test_copy_assignment_matches_aws_request_schema(
    sso_client: BaseClient, principal_type: str
) -> None:
    retriever = Mock(sso_admin_client=sso_client, instance_arn=INSTANCE_ARN)
    copier = AssignmentCopier(Mock(), retriever, Mock(), Mock())
    expected = {
        "InstanceArn": INSTANCE_ARN,
        "TargetId": ACCOUNT_ID,
        "TargetType": "AWS_ACCOUNT",
        "PermissionSetArn": PERMISSION_SET_ARN,
        "PrincipalType": principal_type,
        "PrincipalId": PRINCIPAL_ID,
    }
    with Stubber(sso_client) as stubber:
        stubber.add_response("create_account_assignment", {}, expected)
        method = getattr(copier, f"_create_{principal_type.lower()}_assignment")
        method(PRINCIPAL_ID, PERMISSION_SET_ARN, ACCOUNT_ID)
        stubber.assert_no_pending_responses()


@pytest.mark.parametrize("principal_type", [PrincipalType.USER, PrincipalType.GROUP])
def test_copy_rollback_matches_aws_request_schema(
    sso_client: BaseClient, principal_type: PrincipalType
) -> None:
    manager = Mock()
    manager.get_sso_admin_client.return_value = sso_client
    integration = PermissionCloningRollbackIntegration(manager, Mock(), Mock())
    integration._get_instance_arn = Mock(return_value=INSTANCE_ARN)
    expected = {
        "InstanceArn": INSTANCE_ARN,
        "TargetId": ACCOUNT_ID,
        "TargetType": "AWS_ACCOUNT",
        "PermissionSetArn": PERMISSION_SET_ARN,
        "PrincipalType": principal_type.value,
        "PrincipalId": PRINCIPAL_ID,
    }
    with Stubber(sso_client) as stubber:
        stubber.add_response("delete_account_assignment", {}, expected)
        integration._revoke_assignment(PRINCIPAL_ID, PERMISSION_SET_ARN, ACCOUNT_ID, principal_type)
        stubber.assert_no_pending_responses()


@pytest.mark.asyncio
async def test_restore_returns_cached_identity_store_id() -> None:
    client = AsyncMock()
    client.list_instances.return_value = {
        "Instances": [{"InstanceArn": INSTANCE_ARN, "IdentityStoreId": "d-1234567890"}]
    }
    processor = RestoreProcessor(client, AsyncMock(), ConflictResolver(ConflictStrategy.SKIP))

    assert await processor._get_identity_store_id(INSTANCE_ARN) == "d-1234567890"
    assert await processor._get_identity_store_id(INSTANCE_ARN) == "d-1234567890"
    client.list_instances.assert_awaited_once()


def test_statistics_missing_instance_reaches_fallback(caplog: pytest.LogCaptureFixture) -> None:
    manager = Mock()
    manager.get_identity_center_client.return_value.list_instances.return_value = {"Instances": []}
    collector = StatisticsCollector(manager, INSTANCE_ARN)

    assert collector._extract_identity_store_id() == "ssoins-1234567890abcdef"
    assert "Could not find Identity Store ID" in caplog.text
    assert "Failed to get Identity Store ID from API" not in caplog.text


def test_copy_plan_uses_each_recorded_permission_set_and_account(
    tmp_path: Path, copy_record: PermissionCloningOperationRecord
) -> None:
    second_arn = PERMISSION_SET_ARN.replace("ps-1234567890abcdef", "ps-abcdef1234567890")
    copy_record.assignments_copied.append(f"{second_arn}:{ACCOUNT_ID}:{PRINCIPAL_ID}")
    copy_record.permission_sets_involved.append(second_arn)
    processor = RollbackProcessor(str(tmp_path))
    processor.store.store_operation(copy_record)

    plan = processor.generate_plan(copy_record.operation_id)

    assert plan is not None
    assert {(a.permission_set_arn, a.account_id, a.principal_id) for a in plan.actions} == {
        (PERMISSION_SET_ARN, ACCOUNT_ID, PRINCIPAL_ID),
        (second_arn, ACCOUNT_ID, PRINCIPAL_ID),
    }


def test_rollback_state_check_follows_assignment_pagination(tmp_path: Path) -> None:
    manager = Mock()
    client = manager.get_identity_center_client.return_value
    client.list_account_assignments.side_effect = [
        {"AccountAssignments": [], "NextToken": "next-page"},
        {"AccountAssignments": [{"PrincipalId": PRINCIPAL_ID, "PrincipalType": "USER"}]},
    ]
    processor = RollbackProcessor(str(tmp_path), manager)
    operation = OperationRecord.create(
        operation_type=OperationType.ASSIGN,
        principal_id=PRINCIPAL_ID,
        principal_type=PrincipalType.USER,
        principal_name="Target",
        permission_set_arn=PERMISSION_SET_ARN,
        permission_set_name="PermissionSet",
        account_ids=[ACCOUNT_ID],
        account_names=["Account"],
        results=[OperationResult(account_id=ACCOUNT_ID, success=True)],
    )

    assert (
        processor._get_current_assignment_state(operation, ACCOUNT_ID) == AssignmentState.ASSIGNED
    )
    assert client.list_account_assignments.call_args.kwargs["NextToken"] == "next-page"


def test_malformed_copy_assignment_does_not_report_success(
    tmp_path: Path, copy_record: PermissionCloningOperationRecord
) -> None:
    copy_record.assignments_copied = ["malformed"]
    processor = Mock(store=OperationStore(str(tmp_path)))
    processor.store.store_operation(copy_record)
    integration = PermissionCloningRollbackIntegration(Mock(), processor, Mock())
    integration._revoke_assignment = Mock()

    with pytest.raises(ValueError, match="Invalid copied assignment"):
        integration.rollback_assignment_copy_operation(copy_record.operation_id)
    integration._revoke_assignment.assert_not_called()
    assert processor.store.get_operation(copy_record.operation_id).rolled_back is False


@pytest.mark.parametrize("explicit_path", [True, False])
def test_logger_honors_explicit_storage_directory(tmp_path: Path, explicit_path: bool) -> None:
    configured = tmp_path / "configured"
    requested = tmp_path / "requested"
    with patch("src.awsideman.utils.config.Config") as config:
        config.return_value.get_rollback_config.return_value = {
            "enabled": True,
            "storage_directory": str(configured),
        }
        logger = OperationLogger(str(requested) if explicit_path else None)

    assert logger.store.storage_dir == (requested if explicit_path else configured)


def test_rollback_execution_deletes_assignment_found_on_later_page(tmp_path: Path) -> None:
    manager = Mock()
    client = manager.get_identity_center_client.return_value
    client.list_account_assignments.side_effect = [
        {"AccountAssignments": [], "NextToken": "next-page"},
        {"AccountAssignments": [{"PrincipalId": PRINCIPAL_ID, "PrincipalType": "GROUP"}]},
    ]
    client.delete_account_assignment.return_value = {
        "AccountAssignmentDeletionStatus": {"Status": "SUCCEEDED", "RequestId": "request-id"}
    }
    processor = RollbackProcessor(str(tmp_path), manager)
    plan = RollbackPlan(
        operation_id="test-operation",
        rollback_type=RollbackActionType.REVOKE,
        actions=[
            RollbackAction(
                principal_id=PRINCIPAL_ID,
                permission_set_arn=PERMISSION_SET_ARN,
                account_id=ACCOUNT_ID,
                action_type=RollbackActionType.REVOKE,
                current_state=AssignmentState.ASSIGNED,
                principal_type=PrincipalType.GROUP,
            )
        ],
        estimated_duration=0,
    )

    result = processor.execute_rollback(plan, verify_post_rollback=False)

    assert result.success is True
    client.delete_account_assignment.assert_called_once_with(
        InstanceArn=INSTANCE_ARN,
        TargetId=ACCOUNT_ID,
        TargetType="AWS_ACCOUNT",
        PermissionSetArn=PERMISSION_SET_ARN,
        PrincipalType="GROUP",
        PrincipalId=PRINCIPAL_ID,
    )


@pytest.mark.asyncio
async def test_restore_creates_multiple_users_with_synchronous_aws_clients(
    sso_client: BaseClient,
) -> None:
    identity_client = boto3.client(
        "identitystore",
        region_name="eu-west-1",
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
    )
    processor = RestoreProcessor(
        sso_client, identity_client, ConflictResolver(ConflictStrategy.SKIP)
    )
    with Stubber(sso_client) as sso_stubber, Stubber(identity_client) as identity_stubber:
        sso_stubber.add_response(
            "list_instances",
            {"Instances": [{"InstanceArn": INSTANCE_ARN, "IdentityStoreId": "d-1234567890"}]},
            {},
        )
        for username in ["first-user", "second-user"]:
            identity_stubber.add_response(
                "create_user",
                {"UserId": PRINCIPAL_ID, "IdentityStoreId": "d-1234567890"},
                {
                    "IdentityStoreId": "d-1234567890",
                    "UserName": username,
                    "DisplayName": username,
                },
            )
            user = UserData(user_id=PRINCIPAL_ID, user_name=username)
            assert await processor._create_user(user, INSTANCE_ARN) == PRINCIPAL_ID
        sso_stubber.assert_no_pending_responses()
        identity_stubber.assert_no_pending_responses()
