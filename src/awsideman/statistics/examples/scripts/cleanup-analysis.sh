#!/bin/bash
# cleanup-analysis.sh - Identity Center resource cleanup analysis script
#
# This script analyzes AWS Identity Center configuration to identify cleanup
# opportunities, generates cleanup recommendations, and tracks cleanup progress.
#
# Usage: ./cleanup-analysis.sh [OPTIONS]
#
# Options:
#   --profile PROFILE    AWS profile to use (default: sso-test-1)
#   --region REGION      AWS region (default: eu-north-1)
#   --output FORMAT      Output format (text|json|csv) (default: text)
#   --track              Track cleanup progress against baseline
#   --baseline           Establish new baseline for tracking
#   --dry-run            Show what would be cleaned up without making changes
#   --help               Show help message

set -euo pipefail

# Default configuration
DEFAULT_PROFILE="sso-test-1"
DEFAULT_REGION="eu-north-1"
DEFAULT_OUTPUT="text"
DEFAULT_REPORT_DIR="/var/cleanup/identity-center"

# Parse command line arguments
PROFILE="${DEFAULT_PROFILE}"
REGION="${DEFAULT_REGION}"
OUTPUT_FORMAT="${DEFAULT_OUTPUT}"
TRACK_PROGRESS=false
ESTABLISH_BASELINE=false
DRY_RUN=false
REPORT_DIR="${REPORT_DIR:-$DEFAULT_REPORT_DIR}"

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
        --output)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        --track)
            TRACK_PROGRESS=true
            shift
            ;;
        --baseline)
            ESTABLISH_BASELINE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            cat << EOF
Usage: $0 [OPTIONS]

Analyze AWS Identity Center configuration for cleanup opportunities.

Options:
  --profile PROFILE    AWS profile to use (default: $DEFAULT_PROFILE)
  --region REGION      AWS region (default: $DEFAULT_REGION)
  --output FORMAT      Output format (text|json|csv) (default: $DEFAULT_OUTPUT)
  --track              Track cleanup progress against baseline
  --baseline           Establish new baseline for tracking
  --dry-run            Show what would be cleaned up without making changes
  --help               Show this help message

Environment Variables:
  REPORT_DIR          Cleanup report directory (default: $DEFAULT_REPORT_DIR)

Examples:
  $0                                    # Basic cleanup analysis
  $0 --baseline                         # Establish cleanup baseline
  $0 --track --output json              # Track progress in JSON format
  $0 --dry-run --profile prod           # Dry run for production profile
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
LOG_FILE="${REPORT_DIR}/logs/cleanup-analysis-${DATE}.log"
ANALYSIS_FILE="${REPORT_DIR}/analysis/cleanup-analysis-${TIMESTAMP}.json"
REPORT_FILE="${REPORT_DIR}/reports/cleanup-report-${TIMESTAMP}.${OUTPUT_FORMAT}"
BASELINE_FILE="${REPORT_DIR}/baseline/cleanup-baseline.json"

# Ensure directories exist
mkdir -p "${REPORT_DIR}/logs"
mkdir -p "${REPORT_DIR}/analysis"
mkdir -p "${REPORT_DIR}/reports"
mkdir -p "${REPORT_DIR}/baseline"
mkdir -p "${REPORT_DIR}/tracking"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Cleanup analysis data structure
declare -A CLEANUP_ITEMS

# Add cleanup item
add_cleanup_item() {
    local category="$1"
    local item_type="$2"
    local item_name="$3"
    local priority="$4"
    local impact="$5"
    local recommendation="$6"

    local key="${category}_${item_type}_$(echo "$item_name" | tr ' ' '_')"
    CLEANUP_ITEMS["$key"]=$(jq -n \
        --arg category "$category" \
        --arg item_type "$item_type" \
        --arg item_name "$item_name" \
        --arg priority "$priority" \
        --arg impact "$impact" \
        --arg recommendation "$recommendation" \
        --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        '{
            category: $category,
            item_type: $item_type,
            item_name: $item_name,
            priority: $priority,
            impact: $impact,
            recommendation: $recommendation,
            timestamp: $timestamp
        }')

    log "CLEANUP ITEM [$priority]: $category - $item_name"
}

# Analyze orphaned users
analyze_orphaned_users() {
    log "Analyzing orphaned users..."

    local user_data
    user_data=$(awsideman statistics users -f json --profile "$PROFILE" --region "$REGION" 2>/dev/null || echo "{}")

    local orphaned_users
    orphaned_users=$(echo "$user_data" | jq -r '.user_group_metrics.orphaned_users[]?' 2>/dev/null || echo "")

    if [ -n "$orphaned_users" ]; then
        while IFS= read -r user; do
            add_cleanup_item "users" "orphaned_user" "$user" "medium" \
                "Security gap - user without proper group assignment" \
                "Review user status and either assign to appropriate group or deactivate account"
        done <<< "$orphaned_users"
    fi

    log "Found $(echo "$orphaned_users" | wc -l) orphaned users"
}

# Analyze empty groups
analyze_empty_groups() {
    log "Analyzing empty groups..."

    local group_data
    group_data=$(awsideman statistics groups -f json --profile "$PROFILE" --region "$REGION" 2>/dev/null || echo "{}")

    local empty_groups
    empty_groups=$(echo "$group_data" | jq -r '.user_group_metrics.orphaned_groups[]?' 2>/dev/null || echo "")

    if [ -n "$empty_groups" ]; then
        while IFS= read -r group; do
            add_cleanup_item "groups" "empty_group" "$group" "low" \
                "Administrative overhead - unused group consuming resources" \
                "Remove empty group if no longer needed or populate with appropriate users"
        done <<< "$empty_groups"
    fi

    log "Found $(echo "$empty_groups" | wc -l) empty groups"
}

# Analyze unused permission sets
analyze_unused_permission_sets() {
    log "Analyzing unused permission sets..."

    local ps_data
    ps_data=$(awsideman statistics permission-sets -f json --profile "$PROFILE" --region "$REGION" 2>/dev/null || echo "{}")

    local unused_ps
    unused_ps=$(echo "$ps_data" | jq -r '.permission_set_metrics.unused_permission_sets[]?' 2>/dev/null || echo "")

    if [ -n "$unused_ps" ]; then
        while IFS= read -r ps; do
            local priority="medium"
            # Higher priority for admin-related permission sets
            if [[ "$ps" == *"Admin"* ]] || [[ "$ps" == *"admin"* ]]; then
                priority="high"
            fi

            add_cleanup_item "permission_sets" "unused_permission_set" "$ps" "$priority" \
                "Security risk - unused permission set increases attack surface" \
                "Remove unused permission set if no longer needed or document retention reason"
        done <<< "$unused_ps"
    fi

    log "Found $(echo "$unused_ps" | wc -l) unused permission sets"
}

# Analyze underutilized permission sets
analyze_underutilized_permission_sets() {
    log "Analyzing underutilized permission sets..."

    local ps_data
    ps_data=$(awsideman statistics permission-sets -f json --profile "$PROFILE" --region "$REGION" 2>/dev/null || echo "{}")

    local underutilized_ps
    underutilized_ps=$(echo "$ps_data" | jq -r '.permission_set_metrics.assignments_per_permission_set | to_entries[] | select(.value > 0 and .value < 3) | .key' 2>/dev/null || echo "")

    if [ -n "$underutilized_ps" ]; then
        while IFS= read -r ps; do
            local assignment_count
            assignment_count=$(echo "$ps_data" | jq -r ".permission_set_metrics.assignments_per_permission_set[\"$ps\"]" 2>/dev/null || echo "0")

            add_cleanup_item "permission_sets" "underutilized_permission_set" "$ps" "low" \
                "Efficiency - permission set with only $assignment_count assignments may be consolidatable" \
                "Review if this permission set can be consolidated with similar ones or if usage will increase"
        done <<< "$underutilized_ps"
    fi

    log "Found $(echo "$underutilized_ps" | wc -l) underutilized permission sets"
}

# Analyze unassigned accounts
analyze_unassigned_accounts() {
    log "Analyzing unassigned accounts..."

    local governance_data
    governance_data=$(awsideman statistics governance -f json --profile "$PROFILE" --region "$REGION" 2>/dev/null || echo "{}")

    local unassigned_accounts
    unassigned_accounts=$(echo "$governance_data" | jq -r '.governance_view.empty_mappings.accounts_with_no_assignments[]?' 2>/dev/null || echo "")

    if [ -n "$unassigned_accounts" ]; then
        while IFS= read -r account; do
            add_cleanup_item "accounts" "unassigned_account" "$account" "medium" \
                "Resource waste - account managed by Identity Center but has no assignments" \
                "Either configure appropriate access for this account or remove from Identity Center management"
        done <<< "$unassigned_accounts"
    fi

    log "Found $(echo "$unassigned_accounts" | wc -l) unassigned accounts"
}

# Analyze duplicate or similar groups
analyze_duplicate_groups() {
    log "Analyzing potential duplicate groups..."

    local group_data
    group_data=$(awsideman statistics groups -f json --profile "$PROFILE" --region "$REGION" 2>/dev/null || echo "{}")

    # This is a simplified analysis - in practice, you'd want more sophisticated similarity detection
    local group_names
    group_names=$(echo "$group_data" | jq -r '.user_group_metrics.users_per_group | keys[]' 2>/dev/null || echo "")

    # Look for groups with similar names (basic pattern matching)
    local processed_groups=()
    while IFS= read -r group1; do
        if [[ " ${processed_groups[*]} " =~ " ${group1} " ]]; then
            continue
        fi

        while IFS= read -r group2; do
            if [ "$group1" != "$group2" ] && [[ ! " ${processed_groups[*]} " =~ " ${group2} " ]]; then
                # Simple similarity check (same prefix or suffix)
                local group1_base=$(echo "$group1" | sed 's/[_-].*//')
                local group2_base=$(echo "$group2" | sed 's/[_-].*//')

                if [ "$group1_base" = "$group2_base" ] && [ ${#group1_base} -gt 3 ]; then
                    add_cleanup_item "groups" "similar_group" "$group1 / $group2" "low" \
                        "Potential consolidation opportunity - similar group names detected" \
                        "Review if groups $group1 and $group2 can be consolidated"
                    processed_groups+=("$group1" "$group2")
                    break
                fi
            fi
        done <<< "$group_names"
    done <<< "$group_names"
}

# Calculate cleanup impact
calculate_cleanup_impact() {
    log "Calculating cleanup impact..."

    local total_items=0
    local high_priority=0
    local medium_priority=0
    local low_priority=0

    for key in "${!CLEANUP_ITEMS[@]}"; do
        local item="${CLEANUP_ITEMS[$key]}"
        local priority=$(echo "$item" | jq -r '.priority')

        ((total_items++))
        case "$priority" in
            "high") ((high_priority++)) ;;
            "medium") ((medium_priority++)) ;;
            "low") ((low_priority++)) ;;
        esac
    done

    # Calculate potential impact scores
    local security_impact=$((high_priority * 3 + medium_priority * 2 + low_priority * 1))
    local efficiency_impact=$((total_items * 2))
    local maintenance_reduction=$((total_items * 5)) # 5% reduction per item (estimated)

    cat > "${REPORT_DIR}/analysis/impact-calculation-${TIMESTAMP}.json" << EOF
{
    "analysis_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "profile": "$PROFILE",
    "region": "$REGION",
    "cleanup_summary": {
        "total_items": $total_items,
        "high_priority": $high_priority,
        "medium_priority": $medium_priority,
        "low_priority": $low_priority
    },
    "impact_scores": {
        "security_impact": $security_impact,
        "efficiency_impact": $efficiency_impact,
        "maintenance_reduction_percent": $maintenance_reduction
    },
    "estimated_benefits": {
        "reduced_attack_surface": "$([ $high_priority -gt 0 ] && echo "High" || echo "Medium")",
        "administrative_overhead_reduction": "${maintenance_reduction}%",
        "improved_governance": "$([ $total_items -gt 10 ] && echo "Significant" || echo "Moderate")"
    }
}
EOF

    log "Cleanup impact calculated: $total_items items (H:$high_priority M:$medium_priority L:$low_priority)"
}

# Generate cleanup analysis
generate_analysis() {
    log "Generating cleanup analysis..."

    # Convert cleanup items to JSON array
    local items_json="["
    local first=true
    for key in "${!CLEANUP_ITEMS[@]}"; do
        if [ "$first" = true ]; then
            first=false
        else
            items_json+=","
        fi
        items_json+="${CLEANUP_ITEMS[$key]}"
    done
    items_json+="]"

    # Create comprehensive analysis
    jq -n \
        --argjson items "$items_json" \
        --arg profile "$PROFILE" \
        --arg region "$REGION" \
        --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        '{
            analysis_timestamp: $timestamp,
            profile: $profile,
            region: $region,
            cleanup_items: $items,
            summary: {
                total_items: ($items | length),
                by_category: ($items | group_by(.category) | map({category: .[0].category, count: length}) | from_entries),
                by_priority: ($items | group_by(.priority) | map({priority: .[0].priority, count: length}) | from_entries),
                by_type: ($items | group_by(.item_type) | map({type: .[0].item_type, count: length}) | from_entries)
            }
        }' > "$ANALYSIS_FILE"

    log "Analysis saved to: $ANALYSIS_FILE"
}

# Track cleanup progress
track_progress() {
    if [ ! -f "$BASELINE_FILE" ]; then
        log "No baseline found - use --baseline to establish one"
        return
    fi

    log "Tracking cleanup progress against baseline..."

    local baseline_items
    baseline_items=$(jq '.cleanup_items | length' "$BASELINE_FILE")

    local current_items=${#CLEANUP_ITEMS[@]}
    local items_cleaned=$((baseline_items - current_items))
    local progress_percent=0

    if [ "$baseline_items" -gt 0 ]; then
        progress_percent=$(echo "scale=2; $items_cleaned * 100 / $baseline_items" | bc -l)
    fi

    # Generate progress report
    cat > "${REPORT_DIR}/tracking/progress-${TIMESTAMP}.json" << EOF
{
    "tracking_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "baseline": {
        "timestamp": $(jq '.analysis_timestamp' "$BASELINE_FILE"),
        "total_items": $baseline_items
    },
    "current": {
        "total_items": $current_items
    },
    "progress": {
        "items_cleaned": $items_cleaned,
        "progress_percent": $progress_percent,
        "remaining_items": $current_items
    }
}
EOF

    log "Progress: $items_cleaned items cleaned ($progress_percent% complete)"
}

# Establish baseline
establish_baseline() {
    log "Establishing cleanup baseline..."

    cp "$ANALYSIS_FILE" "$BASELINE_FILE"
    log "Baseline established with ${#CLEANUP_ITEMS[@]} items"
}

# Generate cleanup report
generate_report() {
    log "Generating cleanup report..."

    case "$OUTPUT_FORMAT" in
        "json")
            cp "$ANALYSIS_FILE" "$REPORT_FILE"
            ;;
        "csv")
            generate_csv_report
            ;;
        "text")
            generate_text_report
            ;;
    esac

    log "Cleanup report generated: $REPORT_FILE"
}

# Generate CSV report
generate_csv_report() {
    {
        echo "Category,Type,Name,Priority,Impact,Recommendation,Timestamp"
        jq -r '.cleanup_items[] | [.category, .item_type, .item_name, .priority, .impact, .recommendation, .timestamp] | @csv' "$ANALYSIS_FILE"
    } > "$REPORT_FILE"
}

# Generate text report
generate_text_report() {
    cat > "$REPORT_FILE" << EOF
AWS IDENTITY CENTER CLEANUP ANALYSIS
Generated: $(date)
Profile: $PROFILE
Region: $REGION

EXECUTIVE SUMMARY
=================
$(jq -r '
"Total Cleanup Items: " + (.summary.total_items | tostring),
"High Priority: " + ((.summary.by_priority.high // 0) | tostring),
"Medium Priority: " + ((.summary.by_priority.medium // 0) | tostring),
"Low Priority: " + ((.summary.by_priority.low // 0) | tostring)
' "$ANALYSIS_FILE")

CLEANUP ITEMS BY CATEGORY
=========================
$(jq -r '
.summary.by_category | to_entries |
map("- " + .key + ": " + (.value | tostring) + " items") |
join("\n")
' "$ANALYSIS_FILE")

CLEANUP ITEMS BY TYPE
====================
$(jq -r '
.summary.by_type | to_entries |
map("- " + .key + ": " + (.value | tostring) + " items") |
join("\n")
' "$ANALYSIS_FILE")

HIGH PRIORITY ITEMS
==================
$(jq -r '
.cleanup_items[] | select(.priority == "high") |
"
ITEM: " + .item_name + "
Category: " + .category + " (" + .item_type + ")
Impact: " + .impact + "
Recommendation: " + .recommendation + "
" + ("-" * 60)
' "$ANALYSIS_FILE")

MEDIUM PRIORITY ITEMS
====================
$(jq -r '
.cleanup_items[] | select(.priority == "medium") |
"
ITEM: " + .item_name + "
Category: " + .category + " (" + .item_type + ")
Impact: " + .impact + "
Recommendation: " + .recommendation + "
" + ("-" * 60)
' "$ANALYSIS_FILE")

LOW PRIORITY ITEMS
=================
$(jq -r '
.cleanup_items[] | select(.priority == "low") |
"- " + .item_name + " (" + .category + "): " + .impact
' "$ANALYSIS_FILE")

CLEANUP RECOMMENDATIONS
======================
1. Address HIGH priority items immediately (security impact)
2. Plan MEDIUM priority items for next maintenance window
3. Schedule LOW priority items for quarterly cleanup
4. Establish regular cleanup schedule (monthly recommended)
5. Implement automated monitoring for cleanup opportunities

IMPLEMENTATION PLAN
==================
Phase 1 (Immediate - 0-7 days):
$(jq -r '.cleanup_items[] | select(.priority == "high") | "- " + .recommendation' "$ANALYSIS_FILE")

Phase 2 (Short-term - 1-4 weeks):
$(jq -r '.cleanup_items[] | select(.priority == "medium") | "- " + .recommendation' "$ANALYSIS_FILE")

Phase 3 (Long-term - 1-3 months):
$(jq -r '.cleanup_items[] | select(.priority == "low") | "- " + .recommendation' "$ANALYSIS_FILE")

ESTIMATED IMPACT
===============
$(if [ -f "${REPORT_DIR}/analysis/impact-calculation-${TIMESTAMP}.json" ]; then
    jq -r '
    "Security Impact Score: " + (.impact_scores.security_impact | tostring),
    "Efficiency Improvement: " + (.impact_scores.efficiency_impact | tostring) + " points",
    "Maintenance Reduction: " + (.impact_scores.maintenance_reduction_percent | tostring) + "%",
    "Attack Surface Reduction: " + .estimated_benefits.reduced_attack_surface,
    "Governance Improvement: " + .estimated_benefits.improved_governance
    ' "${REPORT_DIR}/analysis/impact-calculation-${TIMESTAMP}.json"
else
    echo "Impact calculation not available"
fi)

$(if [ "$TRACK_PROGRESS" = true ] && [ -f "${REPORT_DIR}/tracking/progress-${TIMESTAMP}.json" ]; then
    echo "
CLEANUP PROGRESS
==============="
    jq -r '
    "Items Cleaned Since Baseline: " + (.progress.items_cleaned | tostring),
    "Progress: " + (.progress.progress_percent | tostring) + "%",
    "Remaining Items: " + (.progress.remaining_items | tostring)
    ' "${REPORT_DIR}/tracking/progress-${TIMESTAMP}.json"
fi)

Report generated by: awsideman statistics cleanup-analysis
For questions or support, refer to the Statistics module documentation.
EOF
}

# Main execution
main() {
    log "Starting Identity Center cleanup analysis"
    log "Profile: $PROFILE, Region: $REGION, Output: $OUTPUT_FORMAT"

    if [ "$DRY_RUN" = true ]; then
        log "DRY RUN MODE - No changes will be made"
    fi

    # Check dependencies
    if ! command -v awsideman &> /dev/null; then
        error_exit "awsideman command not found"
    fi

    if ! command -v jq &> /dev/null; then
        error_exit "jq command not found"
    fi

    if ! command -v bc &> /dev/null; then
        error_exit "bc command not found"
    fi

    # Validate AWS access
    if ! awsideman config show --profile "$PROFILE" &> /dev/null; then
        error_exit "Cannot access AWS with profile: $PROFILE"
    fi

    # Perform cleanup analysis
    analyze_orphaned_users
    analyze_empty_groups
    analyze_unused_permission_sets
    analyze_underutilized_permission_sets
    analyze_unassigned_accounts
    analyze_duplicate_groups

    # Calculate impact and generate analysis
    calculate_cleanup_impact
    generate_analysis

    # Track progress if requested
    if [ "$TRACK_PROGRESS" = true ]; then
        track_progress
    fi

    # Establish baseline if requested
    if [ "$ESTABLISH_BASELINE" = true ]; then
        establish_baseline
    fi

    # Generate report
    generate_report

    local total_items=${#CLEANUP_ITEMS[@]}
    log "Cleanup analysis completed: $total_items items identified"
    log "Report available at: $REPORT_FILE"

    # Summary output
    if [ "$total_items" -gt 0 ]; then
        echo ""
        echo "CLEANUP SUMMARY:"
        jq -r '
        "Total Items: " + (.summary.total_items | tostring),
        "High Priority: " + ((.summary.by_priority.high // 0) | tostring),
        "Medium Priority: " + ((.summary.by_priority.medium // 0) | tostring),
        "Low Priority: " + ((.summary.by_priority.low // 0) | tostring)
        ' "$ANALYSIS_FILE"

        if [ "$DRY_RUN" = false ]; then
            echo ""
            echo "Next steps:"
            echo "1. Review the detailed report: $REPORT_FILE"
            echo "2. Plan cleanup activities based on priority"
            echo "3. Use --baseline to establish tracking baseline"
            echo "4. Use --track to monitor cleanup progress"
        fi
    else
        echo ""
        echo "No cleanup items identified - Identity Center configuration is clean!"
    fi
}

# Execute main function
main "$@"
