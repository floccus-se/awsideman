"""Filesystem backup layout and readable export tests."""

import asyncio
import gzip
import hashlib
import importlib
import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
import typer
from typer.testing import CliRunner

from src.awsideman.backup_restore.backends import FileSystemStorageBackend
from src.awsideman.backup_restore.encryption import ManagedAESEncryptionProvider
from src.awsideman.backup_restore.models import (
    BackupData,
    BackupMetadata,
    BackupType,
    EncryptionMetadata,
    RetentionPolicy,
    UserData,
)
from src.awsideman.backup_restore.storage import StorageEngine

export_command = importlib.import_module("src.awsideman.commands.backup.export")


def make_backup() -> BackupData:
    return BackupData(
        metadata=BackupMetadata(
            backup_id="full-20261001-112721-test",
            timestamp=datetime(2026, 10, 1, 11, 27, 21),
            instance_arn="arn:aws:sso:::instance/ssoins-test",
            backup_type=BackupType.FULL,
            version="1.0",
            source_account="123456789012",
            source_region="eu-west-1",
            retention_policy=RetentionPolicy(),
            encryption_info=EncryptionMetadata(),
        ),
        users=[UserData(user_id="user-1", user_name="alice", email="alice@example.com")],
    )


def test_default_binary_layout_and_export(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    backup = make_backup()
    engine = StorageEngine(FileSystemStorageBackend(str(tmp_path)))
    asyncio.run(engine.store_backup(backup))

    backup_dir = tmp_path / "123456789012" / "2026-10-01" / backup.metadata.backup_id
    assert (backup_dir / "data").read_bytes().startswith(b"\x1f\x8b")
    assert (backup_dir / "metadata.json").is_file()
    assert (
        asyncio.run(engine.retrieve_backup(backup.metadata.backup_id)).users[0].user_name == "alice"
    )
    assert [item.backup_id for item in asyncio.run(engine.list_backups())] == [
        backup.metadata.backup_id
    ]

    monkeypatch.setattr(
        export_command,
        "get_global_metadata_index",
        lambda: SimpleNamespace(
            get_storage_location=lambda _id: {"backend": "filesystem", "location": str(tmp_path)}
        ),
    )
    app = typer.Typer()
    app.command("export")(export_command.export_backup)
    runner = CliRunner()

    csv_dir = tmp_path / "backup-csv"
    result = runner.invoke(app, [backup.metadata.backup_id, "--format", "csv", "-o", str(csv_dir)])
    assert result.exit_code == 0, result.output
    assert "alice" in (csv_dir / "users.csv").read_text()
    assert (csv_dir / "metadata.csv").is_file()

    json_path = tmp_path / "backup.json"
    result = runner.invoke(
        app, [backup.metadata.backup_id, "--format", "json", "-o", str(json_path)]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(json_path.read_text())["users"][0]["user_name"] == "alice"

    yaml_path = tmp_path / "backup.yaml"
    result = runner.invoke(
        app, [backup.metadata.backup_id, "--format", "yaml", "-o", str(yaml_path)]
    )
    assert result.exit_code == 0, result.output
    assert "alice" in yaml_path.read_text()

    assert asyncio.run(engine.delete_backup(backup.metadata.backup_id))
    assert not backup_dir.exists()


def test_plain_json_and_legacy_backup_are_readable(tmp_path: Path) -> None:
    backup = make_backup()
    engine = StorageEngine(FileSystemStorageBackend(str(tmp_path)), storage_format="json")
    asyncio.run(engine.store_backup(backup))
    path = tmp_path / "123456789012" / "2026-10-01" / backup.metadata.backup_id / "data"
    assert path.read_bytes().startswith(b"{")

    legacy_dir = tmp_path / "profiles" / "ep-master" / "backups" / "legacy-backup"
    legacy_dir.mkdir(parents=True)
    backup.metadata.backup_id = "legacy-backup"
    old_engine = StorageEngine(FileSystemStorageBackend(str(tmp_path / "legacy-source")))
    asyncio.run(old_engine.store_backup(backup))
    source_dir = tmp_path / "legacy-source" / "123456789012" / "2026-10-01" / "legacy-backup"
    # Older backups compressed the serializer output and then compressed it again.
    legacy_data = gzip.compress((source_dir / "data").read_bytes())
    legacy_metadata = json.loads((source_dir / "metadata.json").read_text())
    legacy_metadata["final_checksum"] = hashlib.sha256(legacy_data).hexdigest()
    (legacy_dir / "data").write_bytes(legacy_data)
    (legacy_dir / "metadata.json").write_text(json.dumps(legacy_metadata))
    assert asyncio.run(engine.retrieve_backup("legacy-backup")).users[0].user_name == "alice"


def test_encrypted_backup_can_be_reopened_for_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    backup = make_backup()
    backup.metadata.encryption_info.encrypted = True
    backend = FileSystemStorageBackend(str(tmp_path / "backups"))
    writer = StorageEngine(backend, encryption_provider=ManagedAESEncryptionProvider())
    asyncio.run(writer.store_backup(backup))

    reader = StorageEngine(FileSystemStorageBackend(str(tmp_path / "backups")))
    reopened = asyncio.run(reader.retrieve_backup(backup.metadata.backup_id))
    assert reopened is not None
    assert reopened.users[0].user_name == "alice"
