"""Statistics CLI commands module."""

import typer

# Import all submodules
from . import export, generate, helpers

# Import command functions
from .export import export_csv, export_json, export_statistics, export_text
from .generate import (
    generate_account_statistics,
    generate_assignment_statistics,
    generate_governance_statistics,
    generate_group_statistics,
    generate_permission_set_statistics,
    generate_statistics,
    generate_user_statistics,
)

# Create the statistics CLI app
app = typer.Typer(
    help="Generate statistics and analytics for AWS Identity Center resources.",
    no_args_is_help=True,
)

# Register main commands
app.command("generate")(generate_statistics)

# Register category-specific commands
app.command("users")(generate_user_statistics)
app.command("groups")(generate_group_statistics)
app.command("permission-sets")(generate_permission_set_statistics)
app.command("accounts")(generate_account_statistics)
app.command("assignments")(generate_assignment_statistics)
app.command("governance")(generate_governance_statistics)

# Register export commands
app.command("export")(export_statistics)
app.command("export-json")(export_json)
app.command("export-csv")(export_csv)
app.command("export-text")(export_text)

# Export the app and submodules for backward compatibility
__all__ = ["app", "generate", "export", "helpers"]
