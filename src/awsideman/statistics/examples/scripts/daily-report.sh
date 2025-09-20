#!/bin/bash
# daily-report.sh - Daily statistics collection and monitoring script
#
# This script generates daily statistics reports, monitors for security issues,
# and sends alerts when thresholds are exceeded.
#
# Usage: ./daily-report.sh [--profile PROFILE] [--region REGION]
#
# Environment Variables:
#   REPORT_DIR - Directory for storing reports (default: /var/reports/identity-center)
#   ALERT_EMAIL - Email address for alerts (default: security@company.com)
#   ALERT_THRESHOLDS - JSON file with alert thresholds

set -euo pipefail

# Default configuration
DEFAULT_PROFILE="sso-test-1"
DEFAULT_REGION="eu-north-1"
DEFAULT_REPORT_DIR="/var/reports/identity-center"
DEFAULT_ALERT_EMAIL="security@company.com"

# Parse command line arguments
PROFILE="${DEFAULT_PROFILE}"
REGION="${DEFAULT_REGION}"
REPORT_DIR="${REPORT_DIR:-$DEFAULT_REPORT_DIR}"
ALERT_EMAIL="${ALERT_EMAIL:-$DEFAULT_ALERT_EMAIL}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--profile PROFILE] [--region REGION]"
            echo "Generate daily Identity Center statistics report"
            echo ""
            echo "Options:"
            echo "  --profile PROFILE    AWS profile to use (default: $DEFAULT_PROFILE)"
            echo "  --region REGION      AWS region (default: $DEFAULT_REGION)"
            echo "  --help              Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  REPORT_DIR          Report directory (default: $DEFAULT_REPORT_DIR)"
            echo "  ALERT_EMAIL         Alert email address (default: $DEFAULT_ALERT_EMAIL)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Configuration
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
LOG_FILE="${REPORT_DIR}/logs/daily-report-${DATE}.log"

# Alert thresholds
ORPHANED_USERS_THRESHOLD=5
ADMIN_USERS_THRESHOLD=10
HIGH_RISK_PATTERNS_THRESHOLD=0
UNUSED_PERMISSION_SETS_THRESHOLD=10

# Ensure directories exist
mkdir -p "${REPORT_DIR}/daily"
mkdir -p "${REPORT_DIR}/logs"
mkdir -p "${REPORT_DIR}/alerts"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Check dependencies
check_dependencies() {
    log "Checking dependencies..."

    if ! command -v awsideman &> /dev/null; then
        error_exit "awsideman command not found"
    fi

    if ! command -v jq &> /dev/null; then
        error_exit "jq command not found"
    fi

    if ! command -v mail &> /dev/null; then
        log "WARNING: mail command not found - alerts will not be sent"
    fi

    log "Dependencies check completed"
}

# Validate AWS access
validate_aws_access() {
    log "Validating AWS access..."

    if ! awsideman config show --profile "$PROFILE" &> /dev/null; then
        error_exit "Cannot access AWS with profile: $PROFILE"
    fi

    log "AWS access validated for profile: $PROFILE"
}

# Generate daily statistics
generate_statistics() {
    log "Generating daily statistics..."

    local daily_file="${REPORT_DIR}/daily/daily-stats-${DATE}.json"
    local governance_file="${REPORT_DIR}/daily/governance-${DATE}.json"
    local summary_file="${REPORT_DIR}/daily/summary-${DATE}.txt"

    # Generate comprehensive statistics
    if ! awsideman statistics generate -f json -o "$daily_file" --profile "$PROFILE" --region "$REGION"; then
        error_exit "Failed to generate daily statistics"
    fi

    # Generate governance-specific analysis
    if ! awsideman statistics governance -f json -o "$governance_file" --profile "$PROFILE" --region "$REGION"; then
        error_exit "Failed to generate governance statistics"
    fi

    # Create human-readable summary
    create_summary "$daily_file" "$governance_file" "$summary_file"

    log "Statistics generated successfully"
    echo "$daily_file"
}

# Create human-readable summary
create_summary() {
    local daily_file="$1"
    local governance_file="$2"
    local summary_file="$3"

    log "Creating daily summary..."

    cat > "$summary_file" << EOF
DAILY IDENTITY CENTER STATISTICS SUMMARY
Generated: $(date)
Profile: $PROFILE
Region: $REGION

OVERVIEW
========
$(jq -r '
"Total Users: " + (.user_group_metrics.total_users | tostring),
"Total Groups: " + (.user_group_metrics.total_groups | tostring),
"Total Permission Sets: " + (.permission_set_metrics.total_permission_sets | tostring),
"Total Accounts: " + (.account_metrics.total_accounts | tostring)
' "$daily_file")

SECURITY METRICS
===============
$(jq -r '
"Orphaned Users: " + (.user_group_metrics.orphaned_users | length | tostring),
"Orphaned Groups: " + (.user_group_metrics.orphaned_groups | length | tostring),
"Unused Permission Sets: " + (.permission_set_metrics.unused_permission_sets | length | tostring),
"Users with Admin Access: " + (.governance_view.privileged_access_report.users_with_admin_access | length | tostring),
"High Risk Patterns: " + (.governance_view.privileged_access_report.high_privilege_patterns | map(select(.risk_level == "high")) | length | tostring)
' "$governance_file")

UTILIZATION
===========
$(jq -r '
"Permission Set Utilization: " + (((.permission_set_metrics.total_permission_sets - (.permission_set_metrics.unused_permission_sets | length)) / .permission_set_metrics.total_permission_sets * 100) | floor | tostring) + "%",
"Account Coverage: " + (((.account_metrics.total_accounts - (.account_metrics.accounts_with_no_assignments | length)) / .account_metrics.total_accounts * 100) | floor | tostring) + "%",
"Group Efficiency: " + (((.user_group_metrics.total_groups - (.user_group_metrics.orphaned_groups | length)) / .user_group_metrics.total_groups * 100) | floor | tostring) + "%"
' "$daily_file")

GROWTH TRENDS
=============
$(if jq -e '.historical_comparison' "$daily_file" > /dev/null; then
    jq -r '
    "User Growth: " + (.historical_comparison.user_growth.growth_rate | tostring) + "% (" + (.historical_comparison.user_growth.absolute_change | tostring) + " users)",
    "Group Growth: " + (.historical_comparison.group_growth.growth_rate | tostring) + "% (" + (.historical_comparison.group_growth.absolute_change | tostring) + " groups)",
    "Assignment Growth: " + (.historical_comparison.assignment_growth.growth_rate | tostring) + "% (" + (.historical_comparison.assignment_growth.absolute_change | tostring) + " assignments)"
    ' "$daily_file"
else
    echo "Historical data not available - enable backup snapshots for trend analysis"
fi)

TOP USERS BY ASSIGNMENTS
========================
$(jq -r '.assignment_patterns.users_with_most_assignments[:5] | map("- " + .[0] + " (" + (.[1] | tostring) + " assignments)") | join("\n")' "$daily_file")

TOP GROUPS BY ASSIGNMENTS
=========================
$(jq -r '.assignment_patterns.groups_with_most_assignments[:5] | map("- " + .[0] + " (" + (.[1] | tostring) + " assignments)") | join("\n")' "$daily_file")

CLEANUP CANDIDATES
==================
$(jq -r '
if (.user_group_metrics.orphaned_users | length) > 0 then
"Orphaned Users: " + (.user_group_metrics.orphaned_users | join(", "))
else empty end,
if (.user_group_metrics.orphaned_groups | length) > 0 then
"Empty Groups: " + (.user_group_metrics.orphaned_groups | join(", "))
else empty end,
if (.permission_set_metrics.unused_permission_sets | length) > 0 then
"Unused Permission Sets: " + (.permission_set_metrics.unused_permission_sets | join(", "))
else empty end
' "$daily_file")

Report files:
- Detailed data: $daily_file
- Governance analysis: $governance_file
- Summary: $summary_file
EOF

    log "Summary created: $summary_file"
}

# Check security thresholds and generate alerts
check_thresholds() {
    local daily_file="$1"
    local governance_file="$2"

    log "Checking security thresholds..."

    local alert_file="${REPORT_DIR}/alerts/alert-${DATE}.txt"
    local alert_needed=false

    # Extract metrics
    local orphaned_users=$(jq '.user_group_metrics.orphaned_users | length' "$daily_file")
    local unused_permission_sets=$(jq '.permission_set_metrics.unused_permission_sets | length' "$daily_file")
    local admin_users=$(jq '.governance_view.privileged_access_report.users_with_admin_access | length' "$governance_file")
    local high_risk_patterns=$(jq '.governance_view.privileged_access_report.high_privilege_patterns | map(select(.risk_level == "high")) | length' "$governance_file")

    # Check thresholds
    if [ "$orphaned_users" -gt "$ORPHANED_USERS_THRESHOLD" ]; then
        echo "ALERT: Orphaned users ($orphaned_users) exceeds threshold ($ORPHANED_USERS_THRESHOLD)" >> "$alert_file"
        alert_needed=true
    fi

    if [ "$unused_permission_sets" -gt "$UNUSED_PERMISSION_SETS_THRESHOLD" ]; then
        echo "ALERT: Unused permission sets ($unused_permission_sets) exceeds threshold ($UNUSED_PERMISSION_SETS_THRESHOLD)" >> "$alert_file"
        alert_needed=true
    fi

    if [ "$admin_users" -gt "$ADMIN_USERS_THRESHOLD" ]; then
        echo "ALERT: Admin users ($admin_users) exceeds threshold ($ADMIN_USERS_THRESHOLD)" >> "$alert_file"
        alert_needed=true
    fi

    if [ "$high_risk_patterns" -gt "$HIGH_RISK_PATTERNS_THRESHOLD" ]; then
        echo "ALERT: High risk patterns ($high_risk_patterns) detected" >> "$alert_file"
        alert_needed=true
    fi

    if [ "$alert_needed" = true ]; then
        send_alert "$alert_file" "$daily_file" "$governance_file"
        log "Security alerts generated and sent"
    else
        log "All security thresholds within acceptable limits"
    fi
}

# Send security alert email
send_alert() {
    local alert_file="$1"
    local daily_file="$2"
    local governance_file="$3"

    if ! command -v mail &> /dev/null; then
        log "WARNING: Cannot send email alert - mail command not available"
        return
    fi

    local email_file="${REPORT_DIR}/alerts/alert-email-${DATE}.txt"

    cat > "$email_file" << EOF
IDENTITY CENTER SECURITY ALERT - $DATE

Security thresholds have been exceeded. Immediate attention required.

ALERTS:
$(cat "$alert_file")

CURRENT METRICS:
$(jq -r '
"Orphaned Users: " + (.user_group_metrics.orphaned_users | length | tostring),
"Unused Permission Sets: " + (.permission_set_metrics.unused_permission_sets | length | tostring)
' "$daily_file")

$(jq -r '
"Admin Users: " + (.governance_view.privileged_access_report.users_with_admin_access | length | tostring),
"High Risk Patterns: " + (.governance_view.privileged_access_report.high_privilege_patterns | map(select(.risk_level == "high")) | length | tostring)
' "$governance_file")

HIGH RISK PATTERNS DETECTED:
$(jq -r '.governance_view.privileged_access_report.high_privilege_patterns[] | select(.risk_level == "high") | "- " + .description + " (Risk: " + .risk_level + ")"' "$governance_file")

RECOMMENDED ACTIONS:
1. Review and address orphaned users
2. Clean up unused permission sets
3. Validate admin user access requirements
4. Investigate high-risk access patterns

Detailed reports available at:
- $daily_file
- $governance_file

Generated by: awsideman statistics daily report
Profile: $PROFILE
Region: $REGION
Timestamp: $(date)
EOF

    if mail -s "Identity Center Security Alert - $DATE" "$ALERT_EMAIL" < "$email_file"; then
        log "Alert email sent to: $ALERT_EMAIL"
    else
        log "ERROR: Failed to send alert email"
    fi
}

# Update trend data
update_trends() {
    local daily_file="$1"

    log "Updating trend data..."

    local trend_file="${REPORT_DIR}/trends.csv"

    # Create header if file doesn't exist
    if [ ! -f "$trend_file" ]; then
        echo "Date,Users,Groups,PermissionSets,Accounts,OrphanedUsers,UnusedPermissionSets,AdminUsers" > "$trend_file"
    fi

    # Extract metrics and append to trend file
    local users=$(jq '.user_group_metrics.total_users' "$daily_file")
    local groups=$(jq '.user_group_metrics.total_groups' "$daily_file")
    local permission_sets=$(jq '.permission_set_metrics.total_permission_sets' "$daily_file")
    local accounts=$(jq '.account_metrics.total_accounts' "$daily_file")
    local orphaned_users=$(jq '.user_group_metrics.orphaned_users | length' "$daily_file")
    local unused_permission_sets=$(jq '.permission_set_metrics.unused_permission_sets | length' "$daily_file")

    # Get admin users from governance file if it exists
    local governance_file="${REPORT_DIR}/daily/governance-${DATE}.json"
    local admin_users=0
    if [ -f "$governance_file" ]; then
        admin_users=$(jq '.governance_view.privileged_access_report.users_with_admin_access | length' "$governance_file")
    fi

    echo "$DATE,$users,$groups,$permission_sets,$accounts,$orphaned_users,$unused_permission_sets,$admin_users" >> "$trend_file"

    log "Trend data updated: $trend_file"
}

# Cleanup old reports
cleanup_old_reports() {
    log "Cleaning up old reports..."

    # Keep reports for 30 days
    find "${REPORT_DIR}/daily" -name "*.json" -mtime +30 -delete 2>/dev/null || true
    find "${REPORT_DIR}/daily" -name "*.txt" -mtime +30 -delete 2>/dev/null || true
    find "${REPORT_DIR}/alerts" -name "*.txt" -mtime +30 -delete 2>/dev/null || true
    find "${REPORT_DIR}/logs" -name "*.log" -mtime +30 -delete 2>/dev/null || true

    log "Old reports cleaned up"
}

# Generate performance metrics
generate_performance_metrics() {
    local daily_file="$1"

    log "Generating performance metrics..."

    local perf_file="${REPORT_DIR}/daily/performance-${DATE}.json"

    # Calculate performance indicators
    jq '{
        date: "'$DATE'",
        performance_metrics: {
            total_entities: (.user_group_metrics.total_users + .user_group_metrics.total_groups + .permission_set_metrics.total_permission_sets + .account_metrics.total_accounts),
            complexity_score: ((.user_group_metrics.total_users * .user_group_metrics.total_groups * .permission_set_metrics.total_permission_sets) / 1000000),
            cross_account_ratio: ((.account_metrics.cross_account_users | length) / .user_group_metrics.total_users * 100),
            utilization_score: (((.permission_set_metrics.total_permission_sets - (.permission_set_metrics.unused_permission_sets | length)) / .permission_set_metrics.total_permission_sets * 100) + ((.user_group_metrics.total_groups - (.user_group_metrics.orphaned_groups | length)) / .user_group_metrics.total_groups * 100)) / 2,
            efficiency_rating: (if .assignment_patterns.average_assignments_per_user < 3 then "Good" elif .assignment_patterns.average_assignments_per_user < 5 then "Fair" else "Needs Improvement" end)
        }
    }' "$daily_file" > "$perf_file"

    log "Performance metrics generated: $perf_file"
}

# Main execution
main() {
    log "Starting daily Identity Center statistics report"
    log "Profile: $PROFILE, Region: $REGION"

    # Check dependencies and access
    check_dependencies
    validate_aws_access

    # Generate statistics
    local daily_file
    daily_file=$(generate_statistics)

    # Check security thresholds
    local governance_file="${REPORT_DIR}/daily/governance-${DATE}.json"
    check_thresholds "$daily_file" "$governance_file"

    # Update trend data
    update_trends "$daily_file"

    # Generate performance metrics
    generate_performance_metrics "$daily_file"

    # Cleanup old reports
    cleanup_old_reports

    log "Daily report completed successfully"
    log "Summary available at: ${REPORT_DIR}/daily/summary-${DATE}.txt"
}

# Execute main function
main "$@"
