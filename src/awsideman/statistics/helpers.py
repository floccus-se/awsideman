"""Utility functions for the statistics module."""

from typing import Any, Dict, List


def calculate_percentage(part: int, total: int) -> float:
    """Calculate percentage with safe division.

    Args:
        part: Part value
        total: Total value

    Returns:
        Percentage as float
    """
    if total == 0:
        return 0.0
    return (part / total) * 100.0


def safe_divide(numerator: float, denominator: float) -> float:
    """Perform safe division avoiding division by zero.

    Args:
        numerator: Numerator value
        denominator: Denominator value

    Returns:
        Division result or 0.0 if denominator is zero
    """
    if denominator == 0:
        return 0.0
    return numerator / denominator


def get_top_n_items(data: Dict[str, int], n: int = 10) -> List[tuple]:
    """Get top N items from a dictionary sorted by value.

    Args:
        data: Dictionary with string keys and integer values
        n: Number of top items to return

    Returns:
        List of tuples (key, value) sorted by value descending
    """
    return sorted(data.items(), key=lambda x: x[1], reverse=True)[:n]


def filter_by_criteria(items: List[Any], criteria: Dict[str, Any]) -> List[Any]:
    """Filter items based on criteria.

    Args:
        items: List of items to filter
        criteria: Filter criteria

    Returns:
        Filtered list of items
    """
    # This will be implemented when filtering functionality is needed
    # For now, return all items
    return items


def mask_sensitive_data(data: str, mask_char: str = "*") -> str:
    """Mask sensitive data like account IDs and ARNs.

    Args:
        data: Data to mask
        mask_char: Character to use for masking

    Returns:
        Masked data string
    """
    if not data:
        return data

    # Mask account IDs (12 digits)
    if data.isdigit() and len(data) == 12:
        return f"{data[:3]}{mask_char * 6}{data[-3:]}"

    # Mask ARNs
    if data.startswith("arn:aws:"):
        parts = data.split(":")
        if len(parts) >= 5:
            # Mask account ID in ARN
            if parts[4].isdigit() and len(parts[4]) == 12:
                parts[4] = mask_sensitive_data(parts[4], mask_char)
            return ":".join(parts)

    return data


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def validate_instance_arn(instance_arn: str) -> bool:
    """Validate Identity Center instance ARN format.

    Args:
        instance_arn: Instance ARN to validate

    Returns:
        True if valid, False otherwise
    """
    if not instance_arn:
        return False

    # Basic ARN format validation
    if not instance_arn.startswith("arn:aws:sso:::instance/"):
        return False

    # Check if instance ID is present
    instance_id = instance_arn.split("/")[-1]
    if not instance_id or len(instance_id) < 10:
        return False

    return True


def get_category_filters() -> Dict[str, List[str]]:
    """Get available category filters for statistics.

    Returns:
        Dictionary of category filters
    """
    return {
        "users": ["active", "inactive", "orphaned"],
        "groups": ["with_members", "empty", "orphaned"],
        "permission_sets": ["assigned", "unassigned", "privileged"],
        "accounts": ["with_assignments", "without_assignments"],
        "assignments": ["user_assignments", "group_assignments"],
    }
