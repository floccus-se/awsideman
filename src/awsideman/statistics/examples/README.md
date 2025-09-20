# Statistics Module Examples

This directory contains example outputs and use cases for the AWS Identity Center Statistics module. These examples demonstrate the various output formats, filtering options, and practical applications of the statistics functionality.

## Directory Structure

```
examples/
├── README.md                    # This file
├── outputs/                     # Example output files
│   ├── json/                   # JSON format examples
│   ├── csv/                    # CSV format examples
│   └── text/                   # Text format examples
├── use-cases/                  # Practical use case scenarios
│   ├── security-audit.md       # Security auditing scenarios
│   ├── compliance-reporting.md # Compliance and governance
│   ├── access-optimization.md  # Access management optimization
│   └── capacity-planning.md    # Growth and capacity planning
└── scripts/                    # Example automation scripts
    ├── daily-report.sh         # Daily statistics collection
    ├── security-check.sh       # Security monitoring
    └── cleanup-analysis.sh     # Resource cleanup analysis
```

## Quick Examples

### Basic Statistics Generation

```bash
# Generate comprehensive statistics
awsideman statistics generate --profile sso-test-1

# Generate specific categories
awsideman statistics generate -c users -c governance --profile sso-test-1

# Export to JSON
awsideman statistics generate -f json -o report.json --profile sso-test-1
```

### Filtering Examples

```bash
# Filter by account
awsideman statistics generate --filter account=123456789012 --profile sso-test-1

# Filter by user
awsideman statistics users --filter user=admin@company.com --profile sso-test-1

# Multiple filters
awsideman statistics governance --filter account=123456789012 --filter group=Administrators --profile sso-test-1
```

### Export Examples

```bash
# Export all data to CSV with split files
awsideman statistics export-csv -o stats.csv --split-categories --profile sso-test-1

# Export governance data to JSON
awsideman statistics export-json -o governance.json -c governance --profile sso-test-1

# Export formatted text report
awsideman statistics export-text -o report.txt --include-historical --profile sso-test-1
```

## Output Format Examples

### JSON Output Structure

The JSON output provides a complete, structured representation of all statistics:

```json
{
  "metadata": {
    "generation_timestamp": "2024-01-15T10:30:00Z",
    "instance_arn": "arn:aws:sso:::instance/ssoins-xxxxxxxxxx",
    "region": "eu-north-1",
    "profile": "sso-test-1",
    "categories_included": ["users", "groups", "permission-sets", "accounts", "assignments", "governance"],
    "filters_applied": {},
    "data_collection_duration": 45.2,
    "analysis_duration": 12.8
  },
  "user_group_metrics": {
    "total_users": 245,
    "total_groups": 18,
    "users_per_group": {
      "group-id-1": 45,
      "group-id-2": 32
    },
    "largest_groups": [
      ["Developers", 45],
      ["Operations", 32],
      ["Analysts", 28]
    ],
    "orphaned_users": [
      "user-id-orphan-1",
      "user-id-orphan-2"
    ],
    "orphaned_groups": [
      "group-id-legacy"
    ]
  }
}
```

### CSV Output Structure

CSV output provides tabular data suitable for spreadsheet analysis:

```csv
Category,Metric,Value,Details
Users,Total Users,245,
Users,Orphaned Users,3,"user1@company.com,user2@company.com,user3@company.com"
Groups,Total Groups,18,
Groups,Largest Group,Developers,45 users
Groups,Orphaned Groups,1,Legacy-Team
Permission Sets,Total Permission Sets,24,
Permission Sets,Unused Permission Sets,3,"LegacyAdmin,TempAccess,TestPS"
Permission Sets,Most Assigned,ReadOnlyAccess,89 assignments
```

### Text Output Structure

Text output provides human-readable formatted reports:

```
AWS Identity Center Statistics Report
Generated: 2024-01-15 10:30:00 UTC
Instance: arn:aws:sso:::instance/ssoins-xxxxxxxxxx
Region: eu-north-1

═══════════════════════════════════════════════════════════════
EXECUTIVE SUMMARY
═══════════════════════════════════════════════════════════════

Total Users:           245
Total Groups:          18
Total Permission Sets: 24
Total Accounts:        12
Total Assignments:     456

Key Findings:
• 3 orphaned users detected (no group membership or assignments)
• 1 orphaned group found (no members)
• 3 unused permission sets identified
• 2 privileged permission sets with admin access
• 23 users have cross-account access

═══════════════════════════════════════════════════════════════
USER AND GROUP ANALYSIS
═══════════════════════════════════════════════════════════════

User Distribution:
┌─────────────────────────┬───────────┐
│ Group Name              │ Users     │
├─────────────────────────┼───────────┤
│ Developers              │ 45        │
│ Operations              │ 32        │
│ Analysts                │ 28        │
│ Security                │ 15        │
│ Management              │ 12        │
└─────────────────────────┴───────────┘

Orphaned Resources:
• Users without groups: 3
  - john.doe@company.com (no group membership)
  - temp.user@company.com (no assignments)
  - contractor@company.com (inactive)

• Groups without members: 1
  - Legacy-Team (created 2023-01-15, never used)
```

## Common Use Cases

### 1. Security Auditing

**Scenario**: Monthly security review to identify potential risks

**Commands**:
```bash
# Generate comprehensive governance report
awsideman statistics governance -f json -o security-audit.json --profile sso-test-1

# Focus on privileged access
awsideman statistics governance --filter account=production -f text -o privileged-access.txt --profile sso-test-1

# Identify orphaned resources
awsideman statistics generate -c users -c groups -c permission-sets --profile sso-test-1
```

**Key Metrics**:
- Privileged permission sets and their assignments
- Users with admin access across multiple accounts
- Orphaned users and groups
- Cross-account access patterns
- Unused permission sets

### 2. Compliance Reporting

**Scenario**: Quarterly compliance report for auditors

**Commands**:
```bash
# Generate comprehensive compliance report
awsideman statistics generate -f text -o "compliance-report-$(date +%Y-Q%q).txt" --profile sso-test-1

# Export detailed data for analysis
awsideman statistics export-csv -o compliance-data.csv --split-categories --profile sso-test-1

# Historical trend analysis
awsideman statistics assignments --include-historical -f json -o growth-trends.json --profile sso-test-1
```

**Key Metrics**:
- Access matrix showing who has access to what
- Assignment growth trends over time
- Compliance gaps and empty mappings
- Privileged access distribution
- Resource utilization patterns

### 3. Access Management Optimization

**Scenario**: Optimize permission assignments and clean up unused resources

**Commands**:
```bash
# Identify unused resources
awsideman statistics permission-sets --profile sso-test-1

# Analyze assignment patterns
awsideman statistics assignments --profile sso-test-1

# Review cross-account access
awsideman statistics accounts --profile sso-test-1
```

**Key Metrics**:
- Unused permission sets for cleanup
- Over-assigned or under-assigned resources
- Users with excessive permissions
- Groups with no members
- Assignment distribution imbalances

### 4. Capacity Planning

**Scenario**: Plan for organizational growth and scaling

**Commands**:
```bash
# Track growth trends
awsideman statistics assignments --include-historical --profile sso-test-1

# Analyze current distribution
awsideman statistics generate -c users -c accounts --profile sso-test-1

# Export data for forecasting
awsideman statistics export-json -o capacity-data.json --profile sso-test-1
```

**Key Metrics**:
- User and group growth rates
- Assignment growth trends
- Account coverage patterns
- Resource utilization trends
- Scaling bottlenecks

## Filtering and Customization Examples

### Account-Specific Analysis

```bash
# Production account security review
awsideman statistics governance --filter account=123456789012 --profile sso-test-1

# Development account usage analysis
awsideman statistics generate --filter account=987654321098 -c users -c assignments --profile sso-test-1

# Multi-account comparison
awsideman statistics accounts -f csv -o account-comparison.csv --profile sso-test-1
```

### User-Specific Analysis

```bash
# Analyze specific user's access
awsideman statistics generate --filter user=admin@company.com -c assignments -c governance --profile sso-test-1

# Review high-privilege users
awsideman statistics governance -f json --profile sso-test-1 | jq '.governance_view.privileged_access_report.users_with_admin_access'

# User access audit
awsideman statistics generate --filter user=john.doe@company.com --profile sso-test-1
```

### Group-Specific Analysis

```bash
# Analyze administrator group
awsideman statistics governance --filter group=Administrators --profile sso-test-1

# Review group membership patterns
awsideman statistics users --filter group=Developers --profile sso-test-1

# Group assignment analysis
awsideman statistics assignments --filter group=Operations --profile sso-test-1
```

### Permission Set Analysis

```bash
# Analyze specific permission set usage
awsideman statistics generate --filter permission-set=ReadOnlyAccess --profile sso-test-1

# Review admin permission sets
awsideman statistics governance -f json --profile sso-test-1 | jq '.governance_view.privileged_access_report.admin_permission_sets'

# Permission set optimization
awsideman statistics permission-sets -f csv -o permission-analysis.csv --profile sso-test-1
```

## Automation Examples

### Daily Monitoring Script

```bash
#!/bin/bash
# daily-statistics.sh - Daily statistics collection and monitoring

DATE=$(date +%Y-%m-%d)
REPORT_DIR="/var/reports/identity-center"
ALERT_EMAIL="security@company.com"

# Create report directory
mkdir -p "$REPORT_DIR"

# Generate daily statistics
awsideman statistics generate -f json -o "$REPORT_DIR/daily-stats-$DATE.json" --profile sso-test-1

# Generate governance report
awsideman statistics governance -f text -o "$REPORT_DIR/governance-$DATE.txt" --profile sso-test-1

# Check for security issues
ORPHANED_USERS=$(awsideman statistics users -f json --profile sso-test-1 | jq '.user_group_metrics.orphaned_users | length')
ADMIN_USERS=$(awsideman statistics governance -f json --profile sso-test-1 | jq '.governance_view.privileged_access_report.users_with_admin_access | length')

# Alert if thresholds exceeded
if [ "$ORPHANED_USERS" -gt 5 ] || [ "$ADMIN_USERS" -gt 10 ]; then
    echo "Security alert: $ORPHANED_USERS orphaned users, $ADMIN_USERS admin users" | \
    mail -s "Identity Center Security Alert - $DATE" "$ALERT_EMAIL"
fi

echo "Daily statistics generated for $DATE"
```

### Weekly Cleanup Analysis

```bash
#!/bin/bash
# weekly-cleanup.sh - Weekly resource cleanup analysis

WEEK=$(date +%Y-W%U)
OUTPUT_DIR="/var/reports/cleanup"

mkdir -p "$OUTPUT_DIR"

# Generate cleanup recommendations
awsideman statistics generate -c users -c groups -c permission-sets -f json -o "$OUTPUT_DIR/cleanup-analysis-$WEEK.json" --profile sso-test-1

# Extract cleanup candidates
echo "=== WEEKLY CLEANUP ANALYSIS - $WEEK ===" > "$OUTPUT_DIR/cleanup-report-$WEEK.txt"
echo "" >> "$OUTPUT_DIR/cleanup-report-$WEEK.txt"

# Orphaned users
echo "ORPHANED USERS:" >> "$OUTPUT_DIR/cleanup-report-$WEEK.txt"
awsideman statistics users -f json --profile sso-test-1 | jq -r '.user_group_metrics.orphaned_users[]' >> "$OUTPUT_DIR/cleanup-report-$WEEK.txt"
echo "" >> "$OUTPUT_DIR/cleanup-report-$WEEK.txt"

# Orphaned groups
echo "ORPHANED GROUPS:" >> "$OUTPUT_DIR/cleanup-report-$WEEK.txt"
awsideman statistics groups -f json --profile sso-test-1 | jq -r '.user_group_metrics.orphaned_groups[]' >> "$OUTPUT_DIR/cleanup-report-$WEEK.txt"
echo "" >> "$OUTPUT_DIR/cleanup-report-$WEEK.txt"

# Unused permission sets
echo "UNUSED PERMISSION SETS:" >> "$OUTPUT_DIR/cleanup-report-$WEEK.txt"
awsideman statistics permission-sets -f json --profile sso-test-1 | jq -r '.permission_set_metrics.unused_permission_sets[]' >> "$OUTPUT_DIR/cleanup-report-$WEEK.txt"

echo "Weekly cleanup analysis completed for $WEEK"
```

### Monthly Compliance Report

```bash
#!/bin/bash
# monthly-compliance.sh - Monthly compliance reporting

MONTH=$(date +%Y-%m)
REPORT_DIR="/var/reports/compliance"

mkdir -p "$REPORT_DIR"

# Generate comprehensive compliance report
awsideman statistics generate -f text -o "$REPORT_DIR/compliance-report-$MONTH.txt" --include-historical --profile sso-test-1

# Generate detailed CSV exports
awsideman statistics export-csv -o "$REPORT_DIR/compliance-data-$MONTH.csv" --split-categories --profile sso-test-1

# Generate governance analysis
awsideman statistics governance -f json -o "$REPORT_DIR/governance-analysis-$MONTH.json" --profile sso-test-1

# Create executive summary
cat > "$REPORT_DIR/executive-summary-$MONTH.txt" << EOF
IDENTITY CENTER COMPLIANCE REPORT - $MONTH
==========================================

Generated: $(date)
Report Period: $MONTH

Key Metrics:
- Total Users: $(awsideman statistics users -f json --profile sso-test-1 | jq '.user_group_metrics.total_users')
- Total Groups: $(awsideman statistics groups -f json --profile sso-test-1 | jq '.user_group_metrics.total_groups')
- Total Permission Sets: $(awsideman statistics permission-sets -f json --profile sso-test-1 | jq '.permission_set_metrics.total_permission_sets')
- Privileged Users: $(awsideman statistics governance -f json --profile sso-test-1 | jq '.governance_view.privileged_access_report.users_with_admin_access | length')

Security Findings:
- Orphaned Users: $(awsideman statistics users -f json --profile sso-test-1 | jq '.user_group_metrics.orphaned_users | length')
- Orphaned Groups: $(awsideman statistics groups -f json --profile sso-test-1 | jq '.user_group_metrics.orphaned_groups | length')
- Unused Permission Sets: $(awsideman statistics permission-sets -f json --profile sso-test-1 | jq '.permission_set_metrics.unused_permission_sets | length')

Detailed reports available in:
- $REPORT_DIR/compliance-report-$MONTH.txt
- $REPORT_DIR/compliance-data-$MONTH.csv
- $REPORT_DIR/governance-analysis-$MONTH.json
EOF

echo "Monthly compliance report generated for $MONTH"
```

## Integration Examples

### Dashboard Integration

```bash
# Generate JSON for Grafana dashboard
awsideman statistics generate -f json -o /var/lib/grafana/identity-center-stats.json --profile sso-test-1

# Extract metrics for Prometheus
awsideman statistics generate -f json --profile sso-test-1 | jq -r '
  "identity_center_users_total \(.user_group_metrics.total_users)",
  "identity_center_groups_total \(.user_group_metrics.total_groups)",
  "identity_center_permission_sets_total \(.permission_set_metrics.total_permission_sets)",
  "identity_center_orphaned_users_total \(.user_group_metrics.orphaned_users | length)",
  "identity_center_privileged_users_total \(.governance_view.privileged_access_report.users_with_admin_access | length)"
' > /var/lib/prometheus/identity-center-metrics.prom
```

### SIEM Integration

```bash
# Generate security events for SIEM
awsideman statistics governance -f json --profile sso-test-1 | jq -r '
  .governance_view.privileged_access_report.users_with_admin_access[] as $user |
  {
    timestamp: now | strftime("%Y-%m-%dT%H:%M:%SZ"),
    event_type: "privileged_access_detected",
    user: $user,
    severity: "high",
    source: "aws_identity_center_statistics"
  }
' > /var/log/siem/identity-center-events.json
```

### Spreadsheet Integration

```bash
# Generate Excel-compatible CSV
awsideman statistics export-csv -o identity-center-analysis.csv --split-categories --profile sso-test-1

# Create summary for Google Sheets
awsideman statistics generate -f json --profile sso-test-1 | jq -r '
  ["Metric", "Value"],
  ["Total Users", .user_group_metrics.total_users],
  ["Total Groups", .user_group_metrics.total_groups],
  ["Total Permission Sets", .permission_set_metrics.total_permission_sets],
  ["Orphaned Users", (.user_group_metrics.orphaned_users | length)],
  ["Orphaned Groups", (.user_group_metrics.orphaned_groups | length)],
  ["Unused Permission Sets", (.permission_set_metrics.unused_permission_sets | length)],
  ["Privileged Users", (.governance_view.privileged_access_report.users_with_admin_access | length)]
  | @csv
' > summary.csv
```

This examples directory provides comprehensive guidance for using the Statistics module in various scenarios, from basic reporting to advanced automation and integration use cases.
