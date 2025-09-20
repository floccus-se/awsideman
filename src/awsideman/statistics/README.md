# AWS Identity Center Statistics Module

The Statistics module provides comprehensive analytics and reporting capabilities for AWS Identity Center environments. It helps administrators understand user distributions, permission patterns, and governance gaps across their AWS organization.

## Overview

The Statistics module analyzes your AWS Identity Center configuration and generates actionable insights about:

- **User and Group Metrics**: Distribution patterns, membership analysis, and orphaned resources
- **Permission Set Usage**: Assignment patterns, unused resources, and privileged access detection
- **Account Coverage**: Access distribution, assignment gaps, and cross-account patterns
- **Assignment Patterns**: Usage trends, high-access entities, and growth analysis
- **Governance Views**: Access matrices, compliance gaps, and security insights

## Quick Start

### Basic Usage

Generate comprehensive statistics for your Identity Center environment:

```bash
# Generate all statistics with table output
awsideman statistics generate --profile sso-test-1

# Generate specific categories
awsideman statistics generate -c users -c groups --profile sso-test-1

# Export to JSON for programmatic access
awsideman statistics generate -f json -o report.json --profile sso-test-1
```

### Category-Specific Commands

Generate statistics for specific resource types:

```bash
# User and group analysis
awsideman statistics users --profile sso-test-1
awsideman statistics groups --profile sso-test-1

# Permission set usage analysis
awsideman statistics permission-sets --profile sso-test-1

# Account coverage analysis
awsideman statistics accounts --profile sso-test-1

# Assignment pattern analysis
awsideman statistics assignments --profile sso-test-1

# Governance and security analysis
awsideman statistics governance --profile sso-test-1
```

## Available Statistics

### User and Group Metrics

**What it analyzes:**
- Total number of users and groups
- User distribution across groups
- Group membership patterns
- Orphaned users (no group membership or assignments)
- Orphaned groups (no members or assignments)

**Key insights:**
- Identify users without proper group organization
- Find groups that are no longer used
- Understand group size distribution
- Detect potential access management issues

**Example output:**
```
User and Group Statistics:
├── Total Users: 245
├── Total Groups: 18
├── Average Users per Group: 13.6
├── Largest Groups:
│   ├── Developers (45 users)
│   ├── Operations (32 users)
│   └── Analysts (28 users)
├── Orphaned Users: 3
│   ├── john.doe@company.com (no group membership)
│   ├── temp.user@company.com (no assignments)
│   └── contractor@company.com (inactive)
└── Orphaned Groups: 1
    └── Legacy-Team (no members)
```

### Permission Set Metrics

**What it analyzes:**
- Total number of permission sets
- Assignment frequency per permission set
- Most and least used permission sets
- Unused permission sets
- Privileged permission sets (admin access)

**Key insights:**
- Identify unused permission sets for cleanup
- Find over-assigned or under-assigned permission sets
- Detect privileged access patterns
- Optimize permission set portfolio

**Example output:**
```
Permission Set Statistics:
├── Total Permission Sets: 24
├── Average Assignments per Permission Set: 8.3
├── Most Assigned Permission Sets:
│   ├── ReadOnlyAccess (89 assignments)
│   ├── DeveloperAccess (67 assignments)
│   └── DataAnalyst (45 assignments)
├── Unused Permission Sets: 3
│   ├── LegacyAdminAccess
│   ├── TempContractorAccess
│   └── TestPermissionSet
└── Privileged Permission Sets: 2
    ├── AdminAccess (12 assignments)
    └── SecurityAuditor (5 assignments)
```

### Account Metrics

**What it analyzes:**
- Total number of managed accounts
- Assignment distribution across accounts
- Accounts with no assignments
- Cross-account access patterns
- User and group coverage per account

**Key insights:**
- Identify accounts that may be misconfigured
- Find accounts with excessive or insufficient access
- Understand cross-account access breadth
- Detect potential security risks

**Example output:**
```
Account Statistics:
├── Total Accounts: 12
├── Average Assignments per Account: 15.7
├── Account Coverage:
│   ├── Production (45 assignments)
│   ├── Development (38 assignments)
│   ├── Staging (22 assignments)
│   └── Testing (18 assignments)
├── Accounts with No Assignments: 1
│   └── 123456789012 (Sandbox)
└── Cross-Account Access:
    ├── Users with Multi-Account Access: 23
    └── Groups with Multi-Account Access: 8
```

### Assignment Patterns

**What it analyzes:**
- Average assignments per user and group
- Users and groups with the most assignments
- Assignment growth trends (with historical data)
- Distribution patterns and outliers

**Key insights:**
- Identify potentially over-privileged users
- Find assignment distribution imbalances
- Track access growth over time
- Detect unusual assignment patterns

**Example output:**
```
Assignment Patterns:
├── Average Assignments per User: 2.3
├── Users with Most Assignments:
│   ├── admin@company.com (12 assignments)
│   ├── devops.lead@company.com (8 assignments)
│   └── security.admin@company.com (7 assignments)
├── Groups with Most Assignments:
│   ├── Infrastructure-Team (15 assignments)
│   ├── Security-Team (12 assignments)
│   └── Platform-Team (10 assignments)
└── Growth Trend (30 days):
    ├── Assignment Growth: +15% (23 new assignments)
    ├── User Growth: +5% (12 new users)
    └── Significant Changes: 2 detected
```

### Governance View

**What it analyzes:**
- Access matrices (who has access to what)
- Privileged access detection and reporting
- Empty mappings (unused resources)
- Compliance gaps and security risks

**Key insights:**
- Understand complete access relationships
- Identify privileged access patterns
- Find resources that need cleanup
- Detect potential compliance issues

**Example output:**
```
Governance Analysis:
├── Access Matrix:
│   ├── Users → Accounts: 245 → 12
│   ├── Users → Permission Sets: 245 → 24
│   ├── Groups → Accounts: 18 → 12
│   └── Groups → Permission Sets: 18 → 24
├── Privileged Access:
│   ├── Admin Permission Sets: 2
│   ├── Accounts with Admin Access: 8
│   ├── Users with Admin Access: 5
│   └── High-Risk Patterns: 3 detected
├── Empty Mappings:
│   ├── Groups with No Members: 1
│   ├── Permission Sets with No Assignments: 3
│   └── Accounts with No Assignments: 1
└── Compliance Gaps:
    ├── Orphaned Resources: 4 found
    ├── Over-Privileged Users: 2 detected
    └── Unused Resources: 4 identified
```

## Output Formats

### Table Format (Default)

Interactive, human-readable output displayed in the terminal with rich formatting:

```bash
awsideman statistics generate --profile sso-test-1
```

Features:
- Color-coded sections and highlights
- Hierarchical display with tree structure
- Summary tables and detailed breakdowns
- Progress indicators during generation

### JSON Format

Structured data output for programmatic access and integration:

```bash
awsideman statistics generate -f json -o report.json --profile sso-test-1
```

Features:
- Complete data structure with all metrics
- Metadata including generation timestamp and filters
- Nested objects for easy parsing
- Suitable for dashboards and monitoring systems

### CSV Format

Tabular data for spreadsheet analysis and reporting:

```bash
awsideman statistics generate -f csv -o report.csv --profile sso-test-1

# Export specific categories to separate files
awsideman statistics export-csv -o stats.csv --split-categories --profile sso-test-1
```

Features:
- Separate sheets/files for each category
- Headers with clear column names
- Flat structure for easy analysis
- Compatible with Excel, Google Sheets, and other tools

### Text Format

Formatted text reports for documentation and sharing:

```bash
awsideman statistics generate -f text -o report.txt --profile sso-test-1
```

Features:
- Human-readable formatted output
- Section headers and organized layout
- Suitable for reports and documentation
- Plain text for universal compatibility

## Filtering and Customization

### Category Selection

Choose specific statistics categories to generate:

```bash
# Single category
awsideman statistics generate -c users --profile sso-test-1

# Multiple categories
awsideman statistics generate -c users -c groups -c governance --profile sso-test-1

# All categories (default)
awsideman statistics generate -c all --profile sso-test-1
```

Available categories:
- `users` - User and group metrics
- `groups` - Group-specific analysis
- `permission-sets` - Permission set usage
- `accounts` - Account coverage analysis
- `assignments` - Assignment patterns
- `governance` - Governance and security view
- `all` - All categories (default)

### Filtering Options

Filter results by specific criteria:

```bash
# Filter by account
awsideman statistics generate --filter account=123456789012 --profile sso-test-1

# Filter by user
awsideman statistics generate --filter user=john.doe@company.com --profile sso-test-1

# Filter by group
awsideman statistics generate --filter group=Developers --profile sso-test-1

# Filter by permission set
awsideman statistics generate --filter permission-set=ReadOnlyAccess --profile sso-test-1

# Multiple filters
awsideman statistics generate --filter account=123456789012 --filter user=admin@company.com --profile sso-test-1
```

### Historical Comparison

Compare current statistics with historical backup data:

```bash
# Use automatic backup discovery
awsideman statistics generate --include-historical --profile sso-test-1

# Specify backup path
awsideman statistics generate --include-historical --backup-path /path/to/backup --profile sso-test-1

# Historical comparison for assignments
awsideman statistics assignments --include-historical --profile sso-test-1
```

Features:
- Growth rate calculations
- Trend analysis and direction
- Significant change detection
- Time-based comparisons

## Export Commands

### Specialized Export Commands

Use dedicated export commands for format-specific optimizations:

```bash
# JSON export with pretty formatting
awsideman statistics export-json -o report.json --pretty --profile sso-test-1

# CSV export with category splitting
awsideman statistics export-csv -o stats.csv --split-categories --profile sso-test-1

# Text export with historical data
awsideman statistics export-text -o report.txt --include-historical --profile sso-test-1
```

### Batch Export

Export multiple formats or categories at once:

```bash
# Export all categories to separate CSV files
awsideman statistics export-csv -o statistics.csv --split-categories --profile sso-test-1

# Export specific categories with filtering
awsideman statistics export-json -o governance.json -c governance --filter account=123456789012 --profile sso-test-1
```

## Performance and Caching

### Caching Behavior

The statistics module integrates with awsideman's caching system:

- **Automatic Caching**: Data is cached by default to improve performance
- **Cache Duration**: Configurable TTL based on data type
- **Cache Invalidation**: Smart invalidation when data changes
- **Disable Caching**: Use `--no-cache` to force fresh data collection

```bash
# Use cached data (default)
awsideman statistics generate --profile sso-test-1

# Force fresh data collection
awsideman statistics generate --no-cache --profile sso-test-1
```

### Performance Optimization

For large environments:

- **Parallel Processing**: Automatic parallel data collection
- **Pagination**: Efficient handling of large datasets
- **Memory Management**: Chunked processing for memory efficiency
- **Progress Reporting**: Real-time progress updates with `--verbose`

```bash
# Enable verbose output for progress tracking
awsideman statistics generate --verbose --profile sso-test-1
```

## Integration Examples

### Dashboard Integration

Export JSON data for dashboard consumption:

```bash
# Generate JSON for monitoring dashboard
awsideman statistics generate -f json -o /var/lib/monitoring/identity-center-stats.json --profile sso-test-1

# Schedule regular updates
0 6 * * * /usr/local/bin/awsideman statistics generate -f json -o /var/lib/monitoring/identity-center-stats.json --profile sso-test-1
```

### Compliance Reporting

Generate compliance reports:

```bash
# Monthly governance report
awsideman statistics governance -f text -o "governance-report-$(date +%Y-%m).txt" --profile sso-test-1

# Privileged access audit
awsideman statistics governance --filter account=production -f json -o privileged-access-audit.json --profile sso-test-1
```

### Spreadsheet Analysis

Export data for Excel/Google Sheets analysis:

```bash
# Export all data to separate CSV files
awsideman statistics export-csv -o identity-center-analysis.csv --split-categories --profile sso-test-1

# Export specific analysis
awsideman statistics users -f csv -o user-analysis.csv --profile sso-test-1
```

## Common Use Cases

### Security Auditing

Identify security risks and compliance gaps:

```bash
# Comprehensive security analysis
awsideman statistics governance --profile sso-test-1

# Find privileged access patterns
awsideman statistics governance --filter account=production --profile sso-test-1

# Identify orphaned resources
awsideman statistics generate -c users -c groups --profile sso-test-1
```

### Access Management Optimization

Optimize permission assignments and resource usage:

```bash
# Find unused permission sets
awsideman statistics permission-sets --profile sso-test-1

# Analyze assignment patterns
awsideman statistics assignments --include-historical --profile sso-test-1

# Review cross-account access
awsideman statistics accounts --profile sso-test-1
```

### Capacity Planning

Understand growth trends and plan for scaling:

```bash
# Track growth over time
awsideman statistics assignments --include-historical --profile sso-test-1

# Analyze user distribution
awsideman statistics users --profile sso-test-1

# Review account coverage
awsideman statistics accounts --profile sso-test-1
```

### Cleanup and Maintenance

Identify resources that need attention:

```bash
# Find orphaned resources
awsideman statistics generate -c users -c groups -c permission-sets --profile sso-test-1

# Identify unused resources
awsideman statistics governance --profile sso-test-1

# Review empty mappings
awsideman statistics governance -f json --profile sso-test-1 | jq '.governance_view.empty_mappings'
```

## Configuration

### Profile and Region Settings

The statistics module respects awsideman's profile and region configuration:

```bash
# Use specific profile (required)
awsideman statistics generate --profile sso-test-1

# Use specific region
awsideman statistics generate --profile sso-test-1 --region eu-north-1

# Check current configuration
awsideman config show --profile sso-test-1
```

### Cache Configuration

Configure caching behavior through awsideman settings:

```bash
# Check cache status
awsideman cache status --profile sso-test-1

# Clear cache if needed
awsideman cache clear --profile sso-test-1

# Disable caching for statistics
awsideman statistics generate --no-cache --profile sso-test-1
```

## Troubleshooting

### Common Issues

#### Permission Errors

**Problem**: Access denied errors when collecting data

**Solution**: Ensure your AWS profile has the required permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "sso:ListInstances",
                "sso:ListPermissionSets",
                "sso:ListAccountAssignments",
                "sso:DescribePermissionSet",
                "sso:ListManagedPoliciesInPermissionSet",
                "sso:ListCustomerManagedPolicyReferencesInPermissionSet",
                "identitystore:ListUsers",
                "identitystore:ListGroups",
                "identitystore:ListGroupMemberships",
                "identitystore:DescribeUser",
                "identitystore:DescribeGroup",
                "organizations:ListAccounts"
            ],
            "Resource": "*"
        }
    ]
}
```

#### Performance Issues

**Problem**: Statistics generation is slow or times out

**Solutions**:
1. Enable caching: Remove `--no-cache` flag
2. Use category filtering: Specify `-c` to limit scope
3. Check network connectivity to AWS APIs
4. Use `--verbose` to identify bottlenecks

```bash
# Optimize for large environments
awsideman statistics generate -c users --verbose --profile sso-test-1
```

#### Memory Issues

**Problem**: Out of memory errors with large datasets

**Solutions**:
1. Use category filtering to reduce data volume
2. Ensure sufficient system memory
3. Close other applications during generation
4. Use export commands for specific data

```bash
# Generate statistics in smaller chunks
awsideman statistics users --profile sso-test-1
awsideman statistics groups --profile sso-test-1
awsideman statistics permission-sets --profile sso-test-1
```

#### Data Inconsistencies

**Problem**: Unexpected or missing data in reports

**Solutions**:
1. Clear cache and regenerate: `--no-cache`
2. Check AWS service status
3. Verify Identity Center configuration
4. Use `--verbose` for detailed logging

```bash
# Force fresh data collection
awsideman statistics generate --no-cache --verbose --profile sso-test-1
```

### Error Messages

#### "No Identity Center instance found"

**Cause**: Identity Center is not enabled in the specified region

**Solution**:
1. Verify Identity Center is enabled
2. Check the correct region: `--region eu-north-1`
3. Ensure proper AWS profile configuration

#### "Insufficient permissions"

**Cause**: Missing required AWS permissions

**Solution**:
1. Review and update IAM permissions
2. Ensure the profile has access to Identity Center APIs
3. Check Organizations API access for account information

#### "Cache connection failed"

**Cause**: Redis cache is not available

**Solution**:
1. Use `--no-cache` to bypass caching
2. Check Redis configuration
3. Verify cache service is running

#### "Historical data not found"

**Cause**: No backup snapshots available for comparison

**Solution**:
1. Create backup snapshots first: `awsideman backup create`
2. Specify correct backup path: `--backup-path`
3. Use statistics without historical comparison

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# Enable verbose output
awsideman statistics generate --verbose --profile sso-test-1

# Check logs for detailed error information
tail -f ~/.awsideman/logs/awsideman.log
```

### Getting Help

If you encounter issues not covered here:

1. Check the main awsideman documentation
2. Review AWS service status
3. Verify your Identity Center configuration
4. Use `--verbose` for detailed error information
5. Check the awsideman logs for additional context

## Advanced Usage

### Custom Filtering

Combine multiple filters for targeted analysis:

```bash
# Analyze specific user's access across accounts
awsideman statistics generate --filter user=admin@company.com -c assignments -c governance --profile sso-test-1

# Review permission set usage in production accounts
awsideman statistics permission-sets --filter account=123456789012 --profile sso-test-1

# Governance analysis for specific group
awsideman statistics governance --filter group=Administrators --profile sso-test-1
```

### Automation and Scripting

Integrate statistics generation into automation workflows:

```bash
#!/bin/bash
# Daily statistics collection script

DATE=$(date +%Y-%m-%d)
OUTPUT_DIR="/var/reports/identity-center"

# Generate comprehensive report
awsideman statistics generate -f json -o "$OUTPUT_DIR/daily-report-$DATE.json" --profile sso-test-1

# Generate governance report
awsideman statistics governance -f text -o "$OUTPUT_DIR/governance-report-$DATE.txt" --profile sso-test-1

# Generate CSV exports for analysis
awsideman statistics export-csv -o "$OUTPUT_DIR/statistics-$DATE.csv" --split-categories --profile sso-test-1

echo "Statistics reports generated for $DATE"
```

### Monitoring Integration

Set up monitoring alerts based on statistics:

```bash
# Generate JSON for monitoring system
awsideman statistics generate -f json --profile sso-test-1 | jq '.governance_view.privileged_access_report.users_with_admin_access | length'

# Check for orphaned resources
awsideman statistics governance -f json --profile sso-test-1 | jq '.governance_view.empty_mappings'

# Monitor assignment growth
awsideman statistics assignments --include-historical -f json --profile sso-test-1 | jq '.assignment_patterns.assignment_growth_trend'
```

This comprehensive documentation covers all aspects of the Statistics module, from basic usage to advanced integration scenarios. The module provides powerful insights into your AWS Identity Center environment while maintaining security best practices and performance optimization.
