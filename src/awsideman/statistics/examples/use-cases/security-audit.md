# Security Audit Use Cases

This document provides comprehensive guidance for using the AWS Identity Center Statistics module for security auditing purposes. Security audits help identify potential risks, compliance gaps, and areas for improvement in your Identity Center configuration.

## Overview

Security auditing with the Statistics module focuses on:
- **Privileged Access Analysis**: Identifying admin and high-privilege access patterns
- **Orphaned Resource Detection**: Finding unused or improperly configured resources
- **Cross-Account Access Review**: Analyzing access patterns across AWS accounts
- **Compliance Gap Identification**: Detecting violations of security policies
- **Risk Pattern Recognition**: Identifying potential security vulnerabilities

## Common Security Audit Scenarios

### 1. Monthly Security Review

**Objective**: Conduct regular security assessments to identify new risks and validate existing controls.

**Commands**:
```bash
# Generate comprehensive governance report
awsideman statistics governance -f text -o "security-review-$(date +%Y-%m).txt" --profile sso-test-1

# Export detailed data for analysis
awsideman statistics governance -f json -o "security-data-$(date +%Y-%m).json" --profile sso-test-1

# Generate CSV for spreadsheet analysis
awsideman statistics export-csv -o "security-analysis-$(date +%Y-%m).csv" -c governance --profile sso-test-1
```

**Key Metrics to Review**:
- Number of users with admin access
- Cross-account access patterns
- Orphaned users and groups
- Unused permission sets
- High-risk access patterns

**Example Analysis**:
```bash
# Check for users with excessive privileges
awsideman statistics governance -f json --profile sso-test-1 | \
jq '.governance_view.privileged_access_report.users_with_admin_access | length'

# Identify cross-account admin access
awsideman statistics governance -f json --profile sso-test-1 | \
jq '.governance_view.privileged_access_report.high_privilege_patterns[] | select(.pattern_type == "cross_account_admin")'

# Count orphaned resources
awsideman statistics generate -c users -c groups -f json --profile sso-test-1 | \
jq '{orphaned_users: .user_group_metrics.orphaned_users | length, orphaned_groups: .user_group_metrics.orphaned_groups | length}'
```

### 2. Privileged Access Audit

**Objective**: Review all administrative and privileged access to ensure compliance with least privilege principles.

**Commands**:
```bash
# Focus on privileged access patterns
awsideman statistics governance --profile sso-test-1

# Filter by accounts with sensitive data
awsideman statistics governance --filter account=123456789012 --profile sso-test-1

# Export privileged access data
awsideman statistics governance -f json -o privileged-access-audit.json --profile sso-test-1
```

**Analysis Checklist**:
- [ ] Review all users with AdminAccess permission set
- [ ] Validate business justification for cross-account admin access
- [ ] Check for groups with administrative privileges
- [ ] Verify MFA enforcement for privileged users
- [ ] Review session duration for admin access

**Example Queries**:
```bash
# List all admin users
awsideman statistics governance -f json --profile sso-test-1 | \
jq -r '.governance_view.privileged_access_report.users_with_admin_access[]'

# Find accounts with admin access
awsideman statistics governance -f json --profile sso-test-1 | \
jq -r '.governance_view.privileged_access_report.accounts_with_admin_access | keys[]'

# Identify high-risk patterns
awsideman statistics governance -f json --profile sso-test-1 | \
jq '.governance_view.privileged_access_report.high_privilege_patterns[] | select(.risk_level == "high")'
```

### 3. Orphaned Resource Cleanup Audit

**Objective**: Identify and plan cleanup of unused or orphaned resources to reduce security surface area.

**Commands**:
```bash
# Generate comprehensive cleanup report
awsideman statistics generate -c users -c groups -c permission-sets -f text -o cleanup-audit.txt --profile sso-test-1

# Export orphaned resources data
awsideman statistics generate -c users -c groups -c permission-sets -f json -o orphaned-resources.json --profile sso-test-1

# Focus on governance gaps
awsideman statistics governance -f json --profile sso-test-1 | jq '.governance_view.empty_mappings'
```

**Cleanup Checklist**:
- [ ] Identify users without group membership
- [ ] Find users without any assignments
- [ ] Locate groups without members
- [ ] Discover unused permission sets
- [ ] Find accounts without assignments

**Example Analysis**:
```bash
# Create cleanup report
cat > cleanup-analysis.sh << 'EOF'
#!/bin/bash
echo "=== ORPHANED RESOURCES CLEANUP ANALYSIS ==="
echo "Date: $(date)"
echo ""

echo "ORPHANED USERS:"
awsideman statistics users -f json --profile sso-test-1 | \
jq -r '.user_group_metrics.orphaned_users[]' | \
while read user; do
    echo "  - $user"
done

echo ""
echo "ORPHANED GROUPS:"
awsideman statistics groups -f json --profile sso-test-1 | \
jq -r '.user_group_metrics.orphaned_groups[]' | \
while read group; do
    echo "  - $group"
done

echo ""
echo "UNUSED PERMISSION SETS:"
awsideman statistics permission-sets -f json --profile sso-test-1 | \
jq -r '.permission_set_metrics.unused_permission_sets[]' | \
while read ps; do
    echo "  - $ps"
done

echo ""
echo "ACCOUNTS WITHOUT ASSIGNMENTS:"
awsideman statistics governance -f json --profile sso-test-1 | \
jq -r '.governance_view.empty_mappings.accounts_with_no_assignments[]' | \
while read account; do
    echo "  - $account"
done
EOF

chmod +x cleanup-analysis.sh
./cleanup-analysis.sh
```

### 4. Cross-Account Access Review

**Objective**: Analyze and validate cross-account access patterns to ensure they align with business requirements.

**Commands**:
```bash
# Analyze cross-account patterns
awsideman statistics accounts --profile sso-test-1

# Focus on users with multi-account access
awsideman statistics generate -c accounts -c assignments -f json -o cross-account-analysis.json --profile sso-test-1

# Generate account-specific reports
for account in 123456789012 234567890123 345678901234; do
    awsideman statistics generate --filter account=$account -f text -o "account-$account-audit.txt" --profile sso-test-1
done
```

**Analysis Points**:
- Users with access to multiple accounts
- Groups spanning multiple accounts
- Business justification for cross-account access
- Potential for lateral movement
- Account isolation effectiveness

**Example Analysis**:
```bash
# Identify users with most cross-account access
awsideman statistics accounts -f json --profile sso-test-1 | \
jq -r '.account_metrics.cross_account_users[] | "\(.[1]) accounts: \(.[0])"' | \
sort -nr | head -10

# Find groups with cross-account access
awsideman statistics accounts -f json --profile sso-test-1 | \
jq -r '.account_metrics.cross_account_groups[] | "\(.[1]) accounts: \(.[0])"' | \
sort -nr

# Analyze account coverage
awsideman statistics accounts -f json --profile sso-test-1 | \
jq '.account_metrics | {total_accounts, accounts_with_assignments: (.assignments_per_account | keys | length), accounts_without_assignments: .accounts_with_no_assignments | length}'
```

### 5. Permission Set Security Review

**Objective**: Review permission sets for security best practices and identify overly permissive configurations.

**Commands**:
```bash
# Analyze permission set usage
awsideman statistics permission-sets --profile sso-test-1

# Focus on privileged permission sets
awsideman statistics governance --profile sso-test-1 | grep -A 20 "Privileged Access"

# Export permission set data for detailed analysis
awsideman statistics permission-sets -f json -o permission-sets-security-review.json --profile sso-test-1
```

**Security Review Checklist**:
- [ ] Review all permission sets with administrative privileges
- [ ] Validate managed policies attached to permission sets
- [ ] Check for overly broad permission sets
- [ ] Identify permission sets with inline policies
- [ ] Review session duration settings

**Example Analysis**:
```bash
# Find most assigned permission sets
awsideman statistics permission-sets -f json --profile sso-test-1 | \
jq -r '.permission_set_metrics.most_assigned_permission_sets[] | "\(.[1]) assignments: \(.[0])"' | \
head -10

# Identify privileged permission sets
awsideman statistics permission-sets -f json --profile sso-test-1 | \
jq -r '.permission_set_metrics.privileged_permission_sets[]'

# Check permission set utilization
awsideman statistics permission-sets -f json --profile sso-test-1 | \
jq '{total: .permission_set_metrics.total_permission_sets, unused: (.permission_set_metrics.unused_permission_sets | length), utilization_rate: ((.permission_set_metrics.total_permission_sets - (.permission_set_metrics.unused_permission_sets | length)) / .permission_set_metrics.total_permission_sets * 100)}'
```

## Security Audit Automation

### Daily Security Monitoring

```bash
#!/bin/bash
# daily-security-monitor.sh - Daily security monitoring script

DATE=$(date +%Y-%m-%d)
ALERT_THRESHOLD_ORPHANED=5
ALERT_THRESHOLD_ADMIN=10
REPORT_DIR="/var/security/identity-center"
ALERT_EMAIL="security@company.com"

mkdir -p "$REPORT_DIR"

# Generate daily security metrics
awsideman statistics governance -f json -o "$REPORT_DIR/daily-security-$DATE.json" --profile sso-test-1

# Extract key metrics
ORPHANED_USERS=$(jq '.governance_view.empty_mappings.groups_with_no_members | length' "$REPORT_DIR/daily-security-$DATE.json")
ADMIN_USERS=$(jq '.governance_view.privileged_access_report.users_with_admin_access | length' "$REPORT_DIR/daily-security-$DATE.json")
HIGH_RISK_PATTERNS=$(jq '.governance_view.privileged_access_report.high_privilege_patterns | map(select(.risk_level == "high")) | length' "$REPORT_DIR/daily-security-$DATE.json")

# Check thresholds and alert
if [ "$ORPHANED_USERS" -gt "$ALERT_THRESHOLD_ORPHANED" ] || [ "$ADMIN_USERS" -gt "$ALERT_THRESHOLD_ADMIN" ] || [ "$HIGH_RISK_PATTERNS" -gt 0 ]; then
    cat > "$REPORT_DIR/security-alert-$DATE.txt" << EOF
SECURITY ALERT - $DATE

Metrics exceeding thresholds:
- Orphaned Users: $ORPHANED_USERS (threshold: $ALERT_THRESHOLD_ORPHANED)
- Admin Users: $ADMIN_USERS (threshold: $ALERT_THRESHOLD_ADMIN)
- High Risk Patterns: $HIGH_RISK_PATTERNS (threshold: 0)

Please review the detailed report: $REPORT_DIR/daily-security-$DATE.json
EOF

    # Send alert email
    mail -s "Identity Center Security Alert - $DATE" "$ALERT_EMAIL" < "$REPORT_DIR/security-alert-$DATE.txt"
fi

echo "Daily security monitoring completed for $DATE"
```

### Weekly Security Audit Report

```bash
#!/bin/bash
# weekly-security-audit.sh - Weekly comprehensive security audit

WEEK=$(date +%Y-W%U)
REPORT_DIR="/var/security/weekly-audits"

mkdir -p "$REPORT_DIR"

# Generate comprehensive security report
awsideman statistics generate -f text -o "$REPORT_DIR/security-audit-$WEEK.txt" --profile sso-test-1

# Generate governance-specific analysis
awsideman statistics governance -f json -o "$REPORT_DIR/governance-analysis-$WEEK.json" --profile sso-test-1

# Create executive summary
cat > "$REPORT_DIR/executive-summary-$WEEK.txt" << EOF
WEEKLY SECURITY AUDIT SUMMARY - $WEEK
=====================================

Generated: $(date)

Key Security Metrics:
$(awsideman statistics governance -f json --profile sso-test-1 | jq -r '
"- Total Users: " + (.governance_view.access_matrix.user_to_accounts | keys | length | tostring),
"- Users with Admin Access: " + (.governance_view.privileged_access_report.users_with_admin_access | length | tostring),
"- Privileged Permission Sets: " + (.governance_view.privileged_access_report.admin_permission_sets | length | tostring),
"- High Risk Patterns: " + (.governance_view.privileged_access_report.high_privilege_patterns | map(select(.risk_level == "high")) | length | tostring),
"- Orphaned Users: " + (.governance_view.empty_mappings.groups_with_no_members | length | tostring),
"- Unused Permission Sets: " + (.governance_view.empty_mappings.permission_sets_with_no_assignments | length | tostring)
')

Security Findings:
$(awsideman statistics governance -f json --profile sso-test-1 | jq -r '
.governance_view.compliance_gaps[] |
"- " + .gap_type + " (" + .severity + "): " + .description
')

Recommendations:
- Review all high-risk patterns identified
- Clean up orphaned and unused resources
- Validate business justification for privileged access
- Implement additional monitoring for cross-account access

Detailed reports available in:
- $REPORT_DIR/security-audit-$WEEK.txt
- $REPORT_DIR/governance-analysis-$WEEK.json
EOF

echo "Weekly security audit completed for $WEEK"
```

### Monthly Compliance Report

```bash
#!/bin/bash
# monthly-compliance-report.sh - Monthly compliance and security report

MONTH=$(date +%Y-%m)
REPORT_DIR="/var/compliance/monthly-reports"

mkdir -p "$REPORT_DIR"

# Generate comprehensive compliance report
awsideman statistics generate -f text -o "$REPORT_DIR/compliance-report-$MONTH.txt" --include-historical --profile sso-test-1

# Generate detailed CSV exports for analysis
awsideman statistics export-csv -o "$REPORT_DIR/compliance-data-$MONTH.csv" --split-categories --profile sso-test-1

# Create compliance metrics summary
awsideman statistics governance -f json --profile sso-test-1 | jq -r '
{
  "report_date": "'$MONTH'",
  "total_users": (.governance_view.access_matrix.user_to_accounts | keys | length),
  "total_groups": (.governance_view.access_matrix.group_to_accounts | keys | length),
  "admin_users": (.governance_view.privileged_access_report.users_with_admin_access | length),
  "privileged_permission_sets": (.governance_view.privileged_access_report.admin_permission_sets | length),
  "high_risk_patterns": (.governance_view.privileged_access_report.high_privilege_patterns | map(select(.risk_level == "high")) | length),
  "medium_risk_patterns": (.governance_view.privileged_access_report.high_privilege_patterns | map(select(.risk_level == "medium")) | length),
  "orphaned_users": (.governance_view.empty_mappings.groups_with_no_members | length),
  "unused_permission_sets": (.governance_view.empty_mappings.permission_sets_with_no_assignments | length),
  "compliance_gaps": (.governance_view.compliance_gaps | length)
}
' > "$REPORT_DIR/compliance-metrics-$MONTH.json"

echo "Monthly compliance report generated for $MONTH"
```

## Security Audit Best Practices

### 1. Regular Review Schedule

- **Daily**: Monitor for new high-risk patterns and threshold breaches
- **Weekly**: Comprehensive security audit and trend analysis
- **Monthly**: Compliance reporting and historical comparison
- **Quarterly**: Deep-dive security assessment and policy review

### 2. Key Security Indicators (KSIs)

Monitor these critical metrics:
- Number of users with admin access
- Cross-account access breadth
- Orphaned resource count
- High-risk pattern detection
- Permission set utilization rate

### 3. Alerting Thresholds

Establish thresholds for automated alerting:
- Orphaned users > 5
- Admin users > 10
- High-risk patterns > 0
- Unused permission sets > 10
- Accounts without assignments > 2

### 4. Documentation Requirements

Maintain documentation for:
- Business justification for privileged access
- Cross-account access requirements
- Exception approvals and time limits
- Remediation plans for identified gaps
- Regular review and approval records

### 5. Integration with Security Tools

Integrate statistics with:
- SIEM systems for security event correlation
- Vulnerability management tools
- Compliance management platforms
- Identity governance solutions
- Security orchestration tools

## Common Security Findings and Remediation

### Finding: Excessive Cross-Account Admin Access

**Risk**: High blast radius if account is compromised
**Detection**: User with AdminAccess to multiple accounts
**Remediation**:
1. Implement break-glass access model
2. Create account-specific admin roles
3. Enable additional monitoring and alerting
4. Require business justification documentation

### Finding: Orphaned Users and Groups

**Risk**: Potential security gaps and access confusion
**Detection**: Users without group membership or assignments
**Remediation**:
1. Review employment status of orphaned users
2. Remove inactive user accounts
3. Clean up unused groups
4. Implement automated lifecycle management

### Finding: Unused Permission Sets

**Risk**: Attack surface expansion and maintenance overhead
**Detection**: Permission sets with zero assignments
**Remediation**:
1. Review business need for unused permission sets
2. Remove obsolete permission sets
3. Consolidate similar permission sets
4. Implement approval process for new permission sets

### Finding: Privileged Access Concentration

**Risk**: Single points of failure and limited redundancy
**Detection**: Very few users with admin access
**Remediation**:
1. Identify additional admin users for redundancy
2. Implement emergency access procedures
3. Cross-train administrative personnel
4. Document administrative procedures

This security audit guide provides comprehensive coverage of security assessment scenarios using the Statistics module. Regular implementation of these practices will help maintain a secure and compliant AWS Identity Center environment.
