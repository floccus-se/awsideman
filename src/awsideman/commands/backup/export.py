"""Export stored backups to readable files."""

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

import typer
from rich.console import Console

from ...backup_restore.backends import FileSystemStorageBackend, S3StorageBackend
from ...backup_restore.export_import import ExportImportManager
from ...backup_restore.local_metadata_index import get_global_metadata_index
from ...backup_restore.models import ExportFormat
from ...backup_restore.storage import StorageEngine
from ...utils.config import Config
from ...utils.validators import validate_profile

console = Console()
config = Config()


def export_backup(
    backup_id: str = typer.Argument(..., help="Backup ID to export", show_default=False),
    format: str = typer.Option("json", "--format", "-f", help="Export format: json, yaml, csv"),
    target: str = typer.Option(
        "filesystem", "--target", "-t", help="Export target: filesystem or s3"
    ),
    output_path: Optional[str] = typer.Option(
        None,
        "--output-path",
        "-o",
        help="New output file, CSV directory, or S3 bucket/prefix",
        show_default=False,
    ),
    profile: Optional[str] = typer.Option(
        None, "--profile", help="AWS profile for S3 or legacy backups", show_default=False
    ),
) -> None:
    """Export a stored backup as readable JSON, YAML, or resource CSV files."""
    export_format = format.lower()
    if export_format not in {"json", "yaml", "csv"}:
        raise typer.BadParameter("Choose json, yaml, or csv", param_hint="--format")
    if target not in {"filesystem", "s3"}:
        raise typer.BadParameter("Choose filesystem or s3", param_hint="--target")
    if not backup_id or "/" in backup_id or ".." in backup_id:
        raise typer.BadParameter("Invalid backup ID", param_hint="backup_id")

    index = get_global_metadata_index()
    storage_info = index.get_storage_location(backup_id) or {}
    source_type = storage_info.get("backend", "filesystem")
    source_location = storage_info.get("location")

    try:
        if source_type == "filesystem":
            base_path = source_location or config.get(
                "backup.storage.filesystem.path", "~/.awsideman/backups"
            )
            source_backend = FileSystemStorageBackend(base_path=base_path, profile=profile)
        elif source_type == "s3":
            if not source_location:
                raise ValueError("S3 source location is missing from the backup index")
            profile_name, profile_data = validate_profile(profile)
            bucket, _, prefix = source_location.partition("/")
            source_backend = S3StorageBackend(
                bucket_name=bucket,
                prefix=prefix,
                profile=profile_name,
                profile_name=profile_name,
                region_name=profile_data.get("region"),
            )
        else:
            raise ValueError(f"Unsupported backup storage: {source_type}")

        manager = ExportImportManager(StorageEngine(source_backend))
        destination = output_path or (
            f"{backup_id}-csv" if export_format == "csv" else f"{backup_id}.{export_format}"
        )
        console.print(f"[blue]Exporting backup {backup_id} in {export_format} format...[/blue]")

        if target == "filesystem":
            path = Path(destination).expanduser()
            if path.exists():
                raise ValueError(f"Output already exists: {path}")
            success = asyncio.run(
                manager.export_backup(backup_id, ExportFormat(export_format), str(path))
            )
            if not success:
                raise ValueError(
                    f"Could not export backup {backup_id}; check the ID and storage access"
                )
            console.print(f"[green]Exported to {path.resolve()}[/green]")
            return

        if not output_path:
            raise ValueError("S3 export requires --output-path bucket/prefix")
        profile_name, profile_data = validate_profile(profile)
        bucket, _, prefix = output_path.partition("/")
        if not bucket:
            raise ValueError("S3 output path must be bucket/prefix")
        with TemporaryDirectory() as temporary_directory:
            staged_path = Path(temporary_directory) / (
                "export-csv" if export_format == "csv" else f"export.{export_format}"
            )
            success = asyncio.run(
                manager.export_backup(backup_id, ExportFormat(export_format), str(staged_path))
            )
            if not success:
                raise ValueError(
                    f"Could not export backup {backup_id}; check the ID and storage access"
                )
            s3_backend = S3StorageBackend(
                bucket_name=bucket,
                prefix=prefix,
                profile=profile_name,
                profile_name=profile_name,
                region_name=profile_data.get("region"),
            )
            files = sorted(staged_path.glob("*.csv")) if export_format == "csv" else [staged_path]
            for file_path in files:
                if not asyncio.run(s3_backend.write_data(file_path.name, file_path.read_bytes())):
                    raise ValueError(f"Could not upload {file_path.name} to S3")
        console.print(f"[green]Exported to s3://{bucket}/{s3_backend.prefix}[/green]")
    except Exception as error:
        console.print(f"[red]Export failed: {error}[/red]")
        raise typer.Exit(1) from error
