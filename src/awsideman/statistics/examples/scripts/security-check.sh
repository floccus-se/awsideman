#!/bin/bash
# security-check.sh - Security-focused Identity Center monitoring script
#
# This script performs comprehensive security checks on AWS Identity Center
# configuration, identifies potential risks, and generates security reports.
#
# Usage: ./security-check.sh [OPTIONS]
#
# Options:
#   --profile PROFILE    AWS profile to use (default: sso-test-1)
#   --region REGION      AWS region (default: eu-north-1)
#   --severity LEVEL     Minimum severity level (low|medium|high) (default: medium)
#   --output FORMAT      Output format (text|json|csv) (default: text)
#   --alert              Send alerts for high-severity findings
#   --help               Show help message

set -euo pipefail

# Default configuration
DEFAULT_PROFILE="sso-test-1"
DEFAULT_REGION="eu-north-1"
DEFAULT_SEVERITY="medium"
DEFAULT_OUTPUT="text"
DEFAULT_REPORT_DIR="/var/security/identity-center"
DEFAULT_ALERT_EMAIL="security@company.com"

# Parse command line arguments
PROFILE="${DEFAULT_PROFILE}"
REGION="${DEFAULT_REGION}"
SEVERITY="${DEFAULT_SEVERITY}"
OUTPUT_FORMAT="${DEFAULT_OUTPUT}"
SEND_ALERTS=false
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
        --severity)
            SEVERITY="$2"
            shift 2
            ;;
        --output)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        --alert)
            SEND_ALERTS=true
            shift
            ;;
        --help)
            cat << EOF
Usage: $0 [OPTIONS]

Perform comprehensive security checks on AWS Identity Center configuration.

Options:
  --profile PROFILE    AWS profile to use (default: $DEFAULT_PROFILE)
  --region REGION      AWS region (default: $DEFAULT_REGION)
  --severity LEVEL     Minimum severity level (low|medium|high) (default: $DEFAULT_SEVERITY)
  --output FORMAT      Output format (text|json|csv) (default: $DEFAULT_OUTPUT)
  --alert              Send alerts for high-severity findings
  --help               Show this help message

Environment Variables:
  REPORT_DIR          Security report directory (default: $DEFAULT_REPORT_DIR)
  ALERT_EMAIL         Alert email address (default: $DEFAULT_ALERT_EMAIL)

Examples:
  $0                                    # Basic security check
  $0 --severity high --alert            # Check high-severity issues and send alerts
  $0 --output json --profile prod       # Generate JSON report for production profile
EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Configuration
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
LOG_FILE="${REPORT_DIR}/logs/security-check-${DATE}.log"
FINDINGS_FILE="${REPORT_DIR}/findings/security-findings-${TIMESTAMP}.json"
REPORT_FILE="${REPORT_DIR}/reports/security-report-${TIMESTAMP}.${OUTPUT_FORMAT}"

# Ensure directories exist
mkdir -p "${REPORT_DIR}/logs"
mkdir -p "${REPORT_DIR}/findings"
mkdir -p "${REPORT_DIR}/reports"
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

# Security check functions
declare -a SECURITY_FINDINGS=()

# Add security finding
add_finding() {
    local severity="$1"
    local category="$2"
    local title="$3"
    local description="$4"
    local affected_resources="$5"
    local recommendation="$6"

    local finding=$(jq -n \
        --arg severity "$severity" \
        --arg category "$category" \
        --arg title "$title" \
        --arg description "$description" \
        --arg affected_resources "$affected_resources" \
        --arg recommendation "$recommendation" \
        --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        '{
            severity: $severity,
            category: $category,
            title: $title,
            description: $description,
            affected_resources: $affected_resources,
            recommendation: $recommendation,
            timestamp: $timestamp
        }')

    SECURITY_FINDINGS+=("$finding")
    log "FINDING [$severity]: $title"
}

# Check for orphaned users
check_orphaned_users() {
    log "Checking for orphaned users..."

    local orphaned_users
    orphaned_users=$(awsideman statistics users -f json --profile "$PROFILE" --region "$REGION" | jq -r '.user_group_metrics.orphaned_users[]' 2>/dev/null || echo "")

    if [ -n "$orphaned_users" ]; then
        local count=$(echo "$orphaned_users" | wc -l)
        local users_list=$(echo "$orphaned_users" | tr '\n' ',' | sed 's/,$//')

        add_finding "medium" "access_management" \
            "Orphaned Users Detected" \
            "$count users found without group membership or assignments" \
            "$users_list" \
            "Review orphaned users and either assign to appropriate groups or remove if no longer needed"
    fi
}

# Check for privileged access violations
check_privileged_access() {
    log "Checking privileged access patterns..."

    local governance_data
    governance_data=$(awsideman statistics governance -f json --profile "$PROFILE" --region "$REGION" 2>/dev/null || echo "{}")

    # Check for excessive admin access
    local admin_users
    admin_users=$(echo "$governance_data" | jq -r '.governance_view.privileged_access_report.users_with_admin_access[]?' 2>/dev/null || echo "")

    if [ -n "$admin_users" ]; then
        local admin_count=$(echo "$admin_users" | wc -l)
        if [ "$admin_count" -gt 5 ]; then
            add_finding "high" "privileged_access" \
                "Excessive Administrative Access" \
                "$admin_count users have administrative access, which may violate least privilege principle" \
                "$(echo "$admin_users" | tr '\n' ',' | sed 's/,$//')" \
                "Review administrative access requirements and implement just-in-time access where possible"
        fi
    fi

    # Check for cross-account admin access
    local high_risk_patterns
    high_risk_patterns=$(echo "$governance_data" | jq -r '.governance_view.privileged_access_report.high_privilege_patterns[]? | select(.risk_level == "high")' 2>/dev/null || echo "")

    if [ -n "$high_risk_patterns" ]; then
        while IFS= read -r pattern; do
            local description=$(echo "$pattern" | jq -r '.description')
            local affected=$(echo "$pattern" | jq -r '.affected_entities | join(",")')

            add_finding "high" "privileged_access" \
                "High-Risk Privilege Pattern" \
                "$description" \
                "$affected" \
                "Implement break-glass access model and additional monitoring for cross-account administrative access"
        done <<< "$high_risk_patterns"
    fi
}

# Check for unused resources
check_unused_resources() {
    log "Checking for unused resources..."

    # Check unused permission sets
    local unused_ps
    unused_ps=$(awsideman statistics permission-sets -f json --profile "$PROFILE" --region "$REGION" | jq -r '.permission_set_metrics.unused_permission_sets[]?' 2>/dev/null || echo "")

    if [ -n "$unused_ps" ]; then
        local count=$(echo "$unused_ps" | wc -l)
        local ps_list=$(echo "$unused_ps" | tr '\n' ',' | sed 's/,$//')

        local severity="low"
        if [ "$count" -gt 10 ]; then
            severity="medium"
        fi

        add_finding "$severity" "resource_management" \
            "Unused Permission Sets" \
            "$count permission sets are defined but never assigned" \
            "$ps_list" \
            "Review unused permission sets and remove those no longer needed to reduce attack surface"
    fi

    # Check empty groups
    local empty_groups
    empty_groups=$(awsideman statistics groups -f json --profile "$PROFILE" --region "$REGION" | jq -r '.user_group_metrics.orphaned_groups[]?' 2>/dev/null || echo "")

    if [ -n "$empty_groups" ]; then
        local count=$(echo "$empty_groups" | wc -l)
        local groups_list=$(echo "$empty_groups" | tr '\n' ',' | sed 's/,$//')

        add_finding "low" "resource_management" \
            "Empty Groups" \
            "$count groups have no members" \
            "$groups_list" \
            "Remove empty groups to reduce administrative overhead and potential confusion"
    fi
}

# Check cross-account access patterns
check_cross_account_access() {
    log "Checking cross-account access patterns..."

    local account_data
    account_data=$(awsideman statistics accounts -f json --profile "$PROFILE" --region "$REGION" 2>/dev/null || echo "{}")

    # Check for excessive cross-account access
    local cross_account_users
    cross_account_users=$(echo "$account_data" | jq -r '.account_metrics.cross_account_users[]?' 2>/dev/null || echo "")

    if [ -n "$cross_account_users" ]; then
        while IFS= read -r user_data; do
            local user=$(echo "$user_data" | jq -r '.[0]')
            local account_count=$(echo "$user_data" | jq -r '.[1]')

            if [ "$account_count" -gt 5 ]; then
                add_finding "medium" "cross_account_access" \
                    "Excessive Cross-Account Access" \
                    "User $user has access to $account_count accounts" \
                    "$user" \
                    "Review business justification for extensive cross-account access and consider account-specific roles"
            fi
        done <<< "$cross_account_users"
    fi

    # Check accounts without assignments
    local unassigned_accounts
    unassigned_accounts=$(echo "$account_data" | jq -r '.account_metrics.accounts_with_no_assignments[]?' 2>/dev/null || echo "")

    if [ -n "$unassigned_accounts" ]; then
        local count=$(echo "$unassigned_accounts" | wc -l)
        local accounts_list=$(echo "$unassigned_accounts" | tr '\n' ',' | sed 's/,$//')

        add_finding "medium" "account_management" \
            "Unassigned Accounts" \
            "$count accounts have no Identity Center assignments" \
            "$accounts_list" \
            "Review unassigned accounts and either configure access or remove from Identity Center management"
    fi
}

# Check assignment patterns
check_assignment_patterns() {
    log "Checking assignment patterns..."

    local assignment_data
    assignment_data=$(awsideman statistics assignments -f json --profile "$PROFILE" --region "$REGION" 2>/dev/null || echo "{}")

    # Check for users with excessive assignments
    local high_assignment_users
    high_assignment_users=$(echo "$assignment_data" | jq -r '.assignment_patterns.users_with_most_assignments[]? | select(.[1] > 10)' 2>/dev/null || echo "")

    if [ -n "$high_assignment_users" ]; then
        while IFS= read -r user_data; do
            local user=$(echo "$user_data" | jq -r '.[0]')
            local assignment_count=$(echo "$user_data" | jq -r '.[1]')

            add_finding "medium" "assignment_patterns" \
                "Excessive User Assignments" \
                "User $user has $assignment_count assignments, which may indicate over-privileged access" \
                "$user" \
                "Review user's role and responsibilities to ensure assignments align with least privilege principle"
        done <<< "$high_assignment_users"
    fi

    # Check average assignments per user
    local avg_assignments
    avg_assignments=$(echo "$assignment_data" | jq -r '.assignment_patterns.average_assignments_per_user' 2>/dev/null || echo "0")

    if [ "$(echo "$avg_assignments > 5" | bc -l 2>/dev/null || echo "0")" -eq 1 ]; then
        add_finding "medium" "assignment_patterns" \
            "High Average Assignments" \
            "Average assignments per user ($avg_assignments) is high, indicating potential over-provisioning" \
            "Organization-wide pattern" \
            "Review assignment patterns and consider role-based access consolidation"
    fi
}

# Check compliance gaps
check_compliance_gaps() {
    log "Checking compliance gaps..."

    local governance_data
    governance_data=$(awsideman statistics governance -f json --profile "$PROFILE" --region "$REGION" 2>/dev/null || echo "{}")

    local compliance_gaps
    compliance_gaps=$(echo "$governance_data" | jq -r '.governance_view.compliance_gaps[]?' 2>/dev/null || echo "")

    if [ -n "$compliance_gaps" ]; then
        while IFS= read -r gap; do
            local gap_type=$(echo "$gap" | jq -r '.gap_type')
            local description=$(echo "$gap" | jq -r '.description')
            local severity=$(echo "$gap" | jq -r '.severity')
            local affected=$(echo "$gap" | jq -r '.affected_resources | join(",")')

            add_finding "$severity" "compliance" \
                "Compliance Gap: $gap_type" \
                "$description" \
                "$affected" \
                "Address compliance gap to maintain security posture and regulatory compliance"
        done <<< "$compliance_gaps"
    fi
}

# Filter findings by severity
filter_findings_by_severity() {
    local min_severity="$1"
    local filtered_findings=()

    for finding in "${SECURITY_FINDINGS[@]}"; do
        local finding_severity=$(echo "$finding" | jq -r '.severity')

        case "$min_severity" in
            "low")
                filtered_findings+=("$finding")
                ;;
            "medium")
                if [[ "$finding_severity" == "medium" || "$finding_severity" == "high" ]]; then
                    filtered_findings+=("$finding")
                fi
                ;;
            "high")
                if [[ "$finding_severity" == "high" ]]; then
                    filtered_findings+=("$finding")
                fi
                ;;
        esac
    done

    SECURITY_FINDINGS=("${filtered_findings[@]}")
}

# Generate security report
generate_report() {
    log "Generating security report..."

    # Save findings to JSON file
    printf '%s\n' "${SECURITY_FINDINGS[@]}" | jq -s '{
        scan_timestamp: "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
        profile: "'$PROFILE'",
        region: "'$REGION'",
        severity_filter: "'$SEVERITY'",
        total_findings: length,
        findings: .
    }' > "$FINDINGS_FILE"

    case "$OUTPUT_FORMAT" in
        "json")
            cp "$FINDINGS_FILE" "$REPORT_FILE"
            ;;
        "csv")
            generate_csv_report
            ;;
        "text")
            generate_text_report
            ;;
    esac

    log "Security report generated: $REPORT_FILE"
}

# Generate CSV report
generate_csv_report() {
    {
        echo "Timestamp,Severity,Category,Title,Description,Affected Resources,Recommendation"
        jq -r '.findings[] | [.timestamp, .severity, .category, .title, .description, .affected_resources, .recommendation] | @csv' "$FINDINGS_FILE"
    } > "$REPORT_FILE"
}

# Generate text report
generate_text_report() {
    cat > "$REPORT_FILE" << EOF
AWS IDENTITY CENTER SECURITY REPORT
Generated: $(date)
Profile: $PROFILE
Region: $REGION
Severity Filter: $SEVERITY

EXECUTIVE SUMMARY
=================
$(jq -r '
"Total Findings: " + (.total_findings | tostring),
"High Severity: " + ([.findings[] | select(.severity == "high")] | length | tostring),
"Medium Severity: " + ([.findings[] | select(.severity == "medium")] | length | tostring),
"Low Severity: " + ([.findings[] | select(.severity == "low")] | length | tostring)
' "$FINDINGS_FILE")

FINDINGS BY CATEGORY
===================
$(jq -r '
.findings | group_by(.category) |
map({
    category: .[0].category,
    count: length,
    high: [.[] | select(.severity == "high")] | length,
    medium: [.[] | select(.severity == "medium")] | length,
    low: [.[] | select(.severity == "low")] | length
}) |
map("- " + .category + ": " + (.count | tostring) + " findings (H:" + (.high | tostring) + " M:" + (.medium | tostring) + " L:" + (.low | tostring) + ")") |
join("\n")
' "$FINDINGS_FILE")

DETAILED FINDINGS
================
$(jq -r '
.findings[] |
"
FINDING: " + .title + " [" + (.severity | ascii_upcase) + "]
Category: " + .category + "
Description: " + .description + "
Affected Resources: " + .affected_resources + "
Recommendation: " + .recommendation + "
Timestamp: " + .timestamp + "
" + ("-" * 80)
' "$FINDINGS_FILE")

SUMMARY STATISTICS
==================
$(awsideman statistics generate -f json --profile "$PROFILE" --region "$REGION" 2>/dev/null | jq -r '
"Total Users: " + (.user_group_metrics.total_users | tostring),
"Total Groups: " + (.user_group_metrics.total_groups | tostring),
"Total Permission Sets: " + (.permission_set_metrics.total_permission_sets | tostring),
"Total Accounts: " + (.account_metrics.total_accounts | tostring),
"Orphaned Users: " + (.user_group_metrics.orphaned_users | length | tostring),
"Unused Permission Sets: " + (.permission_set_metrics.unused_permission_sets | length | tostring)
' || echo "Statistics unavailable")

RECOMMENDATIONS
===============
1. Address all HIGH severity findings immediately
2. Plan remediation for MEDIUM severity findings within 30 days
3. Schedule cleanup for LOW severity findings within 90 days
4. Implement regular security scanning (weekly recommended)
5. Establish automated monitoring for critical security metrics

Report generated by: awsideman statistics security-check
For questions or support, refer to the Statistics module documentation.
EOF
}

# Send security alerts
send_alerts() {
    if [ "$SEND_ALERTS" != true ]; then
        return
    fi

    local high_severity_count
    high_severity_count=$(jq '[.findings[] | select(.severity == "high")] | length' "$FINDINGS_FILE")

    if [ "$high_severity_count" -eq 0 ]; then
        log "No high-severity findings - no alerts sent"
        return
    fi

    if ! command -v mail &> /dev/null; then
        log "WARNING: Cannot send email alert - mail command not available"
        return
    fi

    local alert_file="${REPORT_DIR}/alerts/security-alert-${TIMESTAMP}.txt"

    cat > "$alert_file" << EOF
IDENTITY CENTER SECURITY ALERT
==============================

High-severity security findings detected in AWS Identity Center configuration.

Profile: $PROFILE
Region: $REGION
Scan Time: $(date)

HIGH SEVERITY FINDINGS:
$(jq -r '.findings[] | select(.severity == "high") | "- " + .title + ": " + .description' "$FINDINGS_FILE")

IMMEDIATE ACTIONS REQUIRED:
$(jq -r '.findings[] | select(.severity == "high") | "- " + .recommendation' "$FINDINGS_FILE")

SUMMARY:
$(jq -r '
"Total Findings: " + (.total_findings | tostring),
"High Severity: " + ([.findings[] | select(.severity == "high")] | length | tostring),
"Medium Severity: " + ([.findings[] | select(.severity == "medium")] | length | tostring)
' "$FINDINGS_FILE")

Detailed report available at: $REPORT_FILE

This is an automated security alert from awsideman statistics security-check.
EOF

    if mail -s "URGENT: Identity Center Security Alert - $high_severity_count High Severity Findings" "$ALERT_EMAIL" < "$alert_file"; then
        log "Security alert sent to: $ALERT_EMAIL"
    else
        log "ERROR: Failed to send security alert"
    fi
}

# Main execution
main() {
    log "Starting Identity Center security check"
    log "Profile: $PROFILE, Region: $REGION, Severity: $SEVERITY, Output: $OUTPUT_FORMAT"

    # Check dependencies
    if ! command -v awsideman &> /dev/null; then
        error_exit "awsideman command not found"
    fi

    if ! command -v jq &> /dev/null; then
        error_exit "jq command not found"
    fi

    # Validate AWS access
    if ! awsideman config show --profile "$PROFILE" &> /dev/null; then
        error_exit "Cannot access AWS with profile: $PROFILE"
    fi

    # Perform security checks
    check_orphaned_users
    check_privileged_access
    check_unused_resources
    check_cross_account_access
    check_assignment_patterns
    check_compliance_gaps

    # Filter findings by severity
    filter_findings_by_severity "$SEVERITY"

    # Generate report
    generate_report

    # Send alerts if requested
    send_alerts

    local total_findings=${#SECURITY_FINDINGS[@]}
    log "Security check completed: $total_findings findings (severity >= $SEVERITY)"
    log "Report available at: $REPORT_FILE"

    # Exit with non-zero code if high-severity findings exist
    local high_severity_count
    high_severity_count=$(jq '[.findings[] | select(.severity == "high")] | length' "$FINDINGS_FILE" 2>/dev/null || echo "0")

    if [ "$high_severity_count" -gt 0 ]; then
        log "WARNING: $high_severity_count high-severity findings detected"
        exit 2
    fi
}

# Execute main function
main "$@"
