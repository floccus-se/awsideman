# Access Management Optimization Use Cases

This document provides comprehensive guidance for using the AWS Identity Center Statistics module to optimize access management, improve security posture, and streamline permission assignments. Access optimization helps organizations maintain efficient, secure, and well-governed access patterns.

## Overview

Access management optimization with the Statistics module focuses on:
- **Permission Consolidation**: Reducing complexity through permission set optimization
- **Access Pattern Analysis**: Understanding and improving access distribution
- **Resource Cleanup**: Removing unused and orphaned resources
- **Efficiency Improvements**: Streamlining access provisioning and management
- **Cost Optimization**: Reducing administrative overhead and complexity

## Permission Set Optimization

### 1. Permission Set Consolidation Analysis

**Objective**: Identify opportunities to consolidate similar permission sets and reduce complexity.

**Commands**:
```bash
# Analyze permission set usage patterns
awsideman statistics permission-sets --profile sso-test-1

# Export detailed permission set data
awsideman statistics permission-sets -f csv -o permission-set-analysis.csv --profile sso-test-1

# Focus on unused and underutilized permission sets
awsideman statistics permission-sets -f json --profile sso-test-1 | jq '.permission_set_metrics.unused_permission_sets'
```

**Consolidation Analysis Process**:
```bash
#!/bin/bash
# permission-consolidation-analysis.sh - Analyze permission set consolidation opportunities

ANALYSIS_DATE=$(date +%Y-%m-%d)
OUTPUT_DIR="/var/optimization/permission-sets"

mkdir -p "$OUTPUT_DIR"

# Generate permission set usage analysis
awsideman statistics permission-sets -f json -o "$OUTPUT_DIR/ps-usage-$ANALYSIS_DATE.json" --profile sso-test-1

# Create consolidation recommendations
cat > "$OUTPUT_DIR/consolidation-analysis-$ANALYSIS_DATE.txt" << EOF
PERMISSION SET CONSOLIDATION ANALYSIS - $ANALYSIS_DATE
=====================================================

Current State:
$(awsideman statistics permission-sets -f json --profile sso-test-1 | jq -r '
"Total Permission Sets: " + (.permission_set_metrics.total_permission_sets | tostring),
"Used Permission Sets: " + ((.permission_set_metrics.total_permission_sets - (.permission_set_metrics.unused_permission_sets | length)) | tostring),
"Unused Permission Sets: " + (.permission_set_metrics.unused_permission_sets | length | tostring),
"Average Assignments per PS: " + (.permission_set_metrics.average_assignments_per_permission_set | tostring)
')

Unused Permission Sets (Cleanup Candidates):
$(awsideman statistics permission-sets -f json --profile sso-test-1 | jq -r '.permission_set_metrics.unused_permission_sets[]' | while read ps; do echo "- $ps"; done)

Underutilized Permission Sets (< 5 assignments):
$(awsideman statistics permission-sets -f json --profile sso-test-1 | jq -r '.permission_set_metrics.assignments_per_permission_set | to_entries[] | select(.value < 5) | "- " + .key + " (" + (.value | tostring) + " assignments)"')

Most Used Permission Sets:
$(awsideman statistics permission-sets -f json --profile sso-test-1 | jq -r '.permission_set_metrics.most_assigned_permission_sets[] | "- " + .[0] + " (" + (.[1] | tostring) + " assignments)"' | head -5)

Consolidation Opportunities:
1. Remove unused permission sets to reduce complexity
2. Merge underutilized permission sets with similar purposes
3. Standardize naming conventions for better organization
4. Review and optimize most-used permission sets for efficiency

Recommended Actions:
[ ] Remove unused permission sets
[ ] Analyze similar permission sets for consolidation
[ ] Review permission set policies for optimization
[ ] Implement standardized naming conventions
[ ] Document permission set purposes and use cases
EOF

echo "Permission set consolidation analysis completed: $OUTPUT_DIR/consolidation-analysis-$ANALYSIS_DATE.txt"
```

### 2. Permission Set Optimization Recommendations

**Objective**: Generate specific recommendations for optimizing permission set portfolio.

**Optimization Script**:
```bash
#!/bin/bash
# permission-optimization.sh - Generate permission set optimization recommendations

OPT_DATE=$(date +%Y-%m-%d)
OPT_DIR="/var/optimization/recommendations"

mkdir -p "$OPT_DIR"

# Generate optimization recommendations
awsideman statistics permission-sets -f json --profile sso-test-1 | jq -r '
{
  optimization_date: "'$OPT_DATE'",
  current_metrics: {
    total_permission_sets: .permission_set_metrics.total_permission_sets,
    unused_count: (.permission_set_metrics.unused_permission_sets | length),
    utilization_rate: ((.permission_set_metrics.total_permission_sets - (.permission_set_metrics.unused_permission_sets | length)) / .permission_set_metrics.total_permission_sets * 100)
  },
  cleanup_candidates: {
    unused_permission_sets: .permission_set_metrics.unused_permission_sets,
    underutilized: [.permission_set_metrics.assignments_per_permission_set | to_entries[] | select(.value < 3) | .key]
  },
  optimization_targets: {
    most_used: .permission_set_metrics.most_assigned_permission_sets[:3],
    privileged_sets: .permission_set_metrics.privileged_permission_sets
  },
  recommendations: [
    "Remove " + (.permission_set_metrics.unused_permission_sets | length | tostring) + " unused permission sets",
    "Review underutilized permission sets for consolidation",
    "Optimize most-used permission sets for efficiency",
    "Implement consistent naming and tagging strategy"
  ]
}
' > "$OPT_DIR/permission-optimization-$OPT_DATE.json"

echo "Permission set optimization recommendations generated: $OPT_DIR/permission-optimization-$OPT_DATE.json"
```

## Access Pattern Optimization

### 1. User Access Pattern Analysis

**Objective**: Analyze user access patterns to identify optimization opportunities.

**Commands**:
```bash
# Analyze user access patterns
awsideman statistics users --profile sso-test-1

# Focus on users with excessive or insufficient access
awsideman statistics assignments --profile sso-test-1

# Export user access data for analysis
awsideman statistics users -f csv -o user-access-patterns.csv --profile sso-test-1
```

**Access Pattern Analysis**:
```bash
#!/bin/bash
# access-pattern-analysis.sh - Analyze user access patterns

PATTERN_DATE=$(date +%Y-%m-%d)
PATTERN_DIR="/var/optimization/access-patterns"

mkdir -p "$PATTERN_DIR"

# Generate access pattern analysis
cat > "$PATTERN_DIR/access-pattern-analysis-$PATTERN_DATE.txt" << EOF
USER ACCESS PATTERN ANALYSIS - $PATTERN_DATE
============================================

Access Distribution:
$(awsideman statistics users -f json --profile sso-test-1 | jq -r '
"Total Users: " + (.user_group_metrics.total_users | tostring),
"Users in Groups: " + ((.user_group_metrics.total_users - (.user_group_metrics.orphaned_users | length)) | tostring),
"Orphaned Users: " + (.user_group_metrics.orphaned_users | length | tostring)
')

Group Membership Patterns:
$(awsideman statistics users -f json --profile sso-test-1 | jq -r '
"Average Users per Group: " + ((.user_group_metrics.total_users / .user_group_metrics.total_groups) | tostring),
"Largest Groups: " + (.user_group_metrics.largest_groups[:3] | map(.[0] + " (" + (.[1] | tostring) + " users)") | join(", "))
')

Assignment Patterns:
$(awsideman statistics assignments -f json --profile sso-test-1 | jq -r '
"Average Assignments per User: " + (.assignment_patterns.average_assignments_per_user | tostring),
"Users with Most Assignments: " + (.assignment_patterns.users_with_most_assignments[:3] | map(.[0] + " (" + (.[1] | tostring) + " assignments)") | join(", "))
')

Optimization Opportunities:
1. Organize orphaned users into appropriate groups
2. Balance group sizes for better management
3. Review users with excessive assignments
4. Standardize access patterns by role/function

Recommended Actions:
[ ] Create role-based groups for orphaned users
[ ] Review and optimize large groups
[ ] Implement access templates by job function
[ ] Establish access request and approval processes
EOF

# Generate detailed user analysis
awsideman statistics users -f json --profile sso-test-1 | jq '{
  orphaned_users: .user_group_metrics.orphaned_users,
  group_distribution: .user_group_metrics.users_per_group,
  largest_groups: .user_group_metrics.largest_groups
}' > "$PATTERN_DIR/user-analysis-details-$PATTERN_DATE.json"

echo "Access pattern analysis completed: $PATTERN_DIR/access-pattern-analysis-$PATTERN_DATE.txt"
```

### 2. Group Structure Optimization

**Objective**: Optimize group structure for better access management and governance.

**Group Optimization Analysis**:
```bash
#!/bin/bash
# group-optimization.sh - Analyze and optimize group structure

GROUP_DATE=$(date +%Y-%m-%d)
GROUP_DIR="/var/optimization/groups"

mkdir -p "$GROUP_DIR"

# Generate group optimization analysis
cat > "$GROUP_DIR/group-optimization-$GROUP_DATE.txt" << EOF
GROUP STRUCTURE OPTIMIZATION ANALYSIS - $GROUP_DATE
===================================================

Current Group Metrics:
$(awsideman statistics groups -f json --profile sso-test-1 | jq -r '
"Total Groups: " + (.user_group_metrics.total_groups | tostring),
"Groups with Members: " + ((.user_group_metrics.total_groups - (.user_group_metrics.orphaned_groups | length)) | tostring),
"Empty Groups: " + (.user_group_metrics.orphaned_groups | length | tostring)
')

Group Size Distribution:
$(awsideman statistics groups -f json --profile sso-test-1 | jq -r '
.user_group_metrics.users_per_group | to_entries |
group_by(.value) |
map({size: .[0].value, count: length}) |
sort_by(.size) |
map("Groups with " + (.size | tostring) + " users: " + (.count | tostring)) |
join("\n")
')

Largest Groups (potential for subdivision):
$(awsideman statistics groups -f json --profile sso-test-1 | jq -r '.user_group_metrics.largest_groups[] | "- " + .[0] + " (" + (.[1] | tostring) + " users)"' | head -5)

Empty Groups (cleanup candidates):
$(awsideman statistics groups -f json --profile sso-test-1 | jq -r '.user_group_metrics.orphaned_groups[]' | while read group; do echo "- $group"; done)

Optimization Recommendations:
1. Remove empty groups that are no longer needed
2. Consider subdividing very large groups (>50 users)
3. Create functional groups based on job roles
4. Implement hierarchical group structure
5. Establish group naming conventions

Action Plan:
[ ] Review and remove empty groups
[ ] Analyze large groups for subdivision opportunities
[ ] Design role-based group structure
[ ] Implement group naming standards
[ ] Document group purposes and membership criteria
EOF

echo "Group optimization analysis completed: $GROUP_DIR/group-optimization-$GROUP_DATE.txt"
```

## Resource Cleanup Optimization

### 1. Comprehensive Cleanup Analysis

**Objective**: Identify all unused and orphaned resources for cleanup to reduce complexity and improve security.

**Commands**:
```bash
# Generate comprehensive cleanup report
awsideman statistics generate -c users -c groups -c permission-sets -c accounts -f text -o cleanup-analysis.txt --profile sso-test-1

# Focus on governance gaps and empty mappings
awsideman statistics governance -f json --profile sso-test-1 | jq '.governance_view.empty_mappings'

# Export cleanup data for tracking
awsideman statistics governance -f csv -o cleanup-tracking.csv --profile sso-test-1
```

**Cleanup Analysis Process**:
```bash
#!/bin/bash
# comprehensive-cleanup.sh - Comprehensive resource cleanup analysis

CLEANUP_DATE=$(date +%Y-%m-%d)
CLEANUP_DIR="/var/optimization/cleanup"

mkdir -p "$CLEANUP_DIR"

# Generate comprehensive cleanup analysis
cat > "$CLEANUP_DIR/cleanup-analysis-$CLEANUP_DATE.txt" << EOF
COMPREHENSIVE RESOURCE CLEANUP ANALYSIS - $CLEANUP_DATE
=======================================================

Orphaned Users:
$(awsideman statistics users -f json --profile sso-test-1 | jq -r '.user_group_metrics.orphaned_users[]' | while read user; do echo "- $user"; done)

Orphaned Groups:
$(awsideman statistics groups -f json --profile sso-test-1 | jq -r '.user_group_metrics.orphaned_groups[]' | while read group; do echo "- $group"; done)

Unused Permission Sets:
$(awsideman statistics permission-sets -f json --profile sso-test-1 | jq -r '.permission_set_metrics.unused_permission_sets[]' | while read ps; do echo "- $ps"; done)

Accounts Without Assignments:
$(awsideman statistics governance -f json --profile sso-test-1 | jq -r '.governance_view.empty_mappings.accounts_with_no_assignments[]' | while read account; do echo "- $account"; done)

Cleanup Impact Assessment:
$(awsideman statistics governance -f json --profile sso-test-1 | jq -r '
"Total Cleanup Items: " + ((.governance_view.empty_mappings.groups_with_no_members | length) + (.governance_view.empty_mappings.permission_sets_with_no_assignments | length) + (.governance_view.empty_mappings.accounts_with_no_assignments | length) | tostring),
"Security Risk Reduction: " + ((.governance_view.empty_mappings.groups_with_no_members | length) + (.governance_view.empty_mappings.permission_sets_with_no_assignments | length) | tostring) + " unused resources",
"Management Overhead Reduction: Significant reduction in administrative complexity"
')

Cleanup Priority:
1. HIGH: Remove unused permission sets (security risk)
2. MEDIUM: Clean up orphaned users (access management)
3. MEDIUM: Remove empty groups (organizational clarity)
4. LOW: Address unassigned accounts (resource optimization)

Cleanup Plan:
[ ] Phase 1: Remove unused permission sets
[ ] Phase 2: Handle orphaned users (disable/remove)
[ ] Phase 3: Clean up empty groups
[ ] Phase 4: Address unassigned accounts
[ ] Phase 5: Validate cleanup results
EOF

# Generate cleanup tracking spreadsheet
awsideman statistics governance -f json --profile sso-test-1 | jq -r '
["Resource Type", "Resource Name", "Status", "Priority", "Action Required", "Owner", "Completion Date"],
(.governance_view.empty_mappings.permission_sets_with_no_assignments[] | ["Permission Set", ., "Unused", "High", "Remove", "Security Team", ""]),
(.governance_view.empty_mappings.groups_with_no_members[] | ["Group", ., "Empty", "Medium", "Remove", "IT Team", ""]),
(.governance_view.empty_mappings.accounts_with_no_assignments[] | ["Account", ., "Unassigned", "Low", "Review", "Cloud Team", ""])
| @csv
' > "$CLEANUP_DIR/cleanup-tracking-$CLEANUP_DATE.csv"

echo "Comprehensive cleanup analysis completed: $CLEANUP_DIR/cleanup-analysis-$CLEANUP_DATE.txt"
```

### 2. Cleanup Validation and Tracking

**Objective**: Track cleanup progress and validate results.

**Cleanup Tracking Script**:
```bash
#!/bin/bash
# cleanup-tracking.sh - Track cleanup progress and validate results

TRACK_DATE=$(date +%Y-%m-%d)
TRACK_DIR="/var/optimization/cleanup-tracking"

mkdir -p "$TRACK_DIR"

# Generate before/after comparison
if [ -f "$TRACK_DIR/baseline-metrics.json" ]; then
    # Compare with baseline
    awsideman statistics governance -f json --profile sso-test-1 > "$TRACK_DIR/current-metrics-$TRACK_DATE.json"

    cat > "$TRACK_DIR/cleanup-progress-$TRACK_DATE.txt" << EOF
CLEANUP PROGRESS REPORT - $TRACK_DATE
====================================

Baseline vs Current Comparison:

Orphaned Users:
- Baseline: $(jq '.governance_view.empty_mappings.groups_with_no_members | length' "$TRACK_DIR/baseline-metrics.json")
- Current: $(jq '.governance_view.empty_mappings.groups_with_no_members | length' "$TRACK_DIR/current-metrics-$TRACK_DATE.json")
- Progress: $(echo "$(jq '.governance_view.empty_mappings.groups_with_no_members | length' "$TRACK_DIR/baseline-metrics.json") - $(jq '.governance_view.empty_mappings.groups_with_no_members | length' "$TRACK_DIR/current-metrics-$TRACK_DATE.json")" | bc) items cleaned

Unused Permission Sets:
- Baseline: $(jq '.governance_view.empty_mappings.permission_sets_with_no_assignments | length' "$TRACK_DIR/baseline-metrics.json")
- Current: $(jq '.governance_view.empty_mappings.permission_sets_with_no_assignments | length' "$TRACK_DIR/current-metrics-$TRACK_DATE.json")
- Progress: $(echo "$(jq '.governance_view.empty_mappings.permission_sets_with_no_assignments | length' "$TRACK_DIR/baseline-metrics.json") - $(jq '.governance_view.empty_mappings.permission_sets_with_no_assignments | length' "$TRACK_DIR/current-metrics-$TRACK_DATE.json")" | bc) items cleaned

Empty Groups:
- Baseline: $(jq '.governance_view.empty_mappings.groups_with_no_members | length' "$TRACK_DIR/baseline-metrics.json")
- Current: $(jq '.governance_view.empty_mappings.groups_with_no_members | length' "$TRACK_DIR/current-metrics-$TRACK_DATE.json")
- Progress: $(echo "$(jq '.governance_view.empty_mappings.groups_with_no_members | length' "$TRACK_DIR/baseline-metrics.json") - $(jq '.governance_view.empty_mappings.groups_with_no_members | length' "$TRACK_DIR/current-metrics-$TRACK_DATE.json")" | bc) items cleaned

Overall Cleanup Progress:
$(echo "scale=2; ($(jq '.governance_view.empty_mappings | (.groups_with_no_members | length) + (.permission_sets_with_no_assignments | length) + (.accounts_with_no_assignments | length)' "$TRACK_DIR/baseline-metrics.json") - $(jq '.governance_view.empty_mappings | (.groups_with_no_members | length) + (.permission_sets_with_no_assignments | length) + (.accounts_with_no_assignments | length)' "$TRACK_DIR/current-metrics-$TRACK_DATE.json")) / $(jq '.governance_view.empty_mappings | (.groups_with_no_members | length) + (.permission_sets_with_no_assignments | length) + (.accounts_with_no_assignments | length)' "$TRACK_DIR/baseline-metrics.json") * 100" | bc)% of cleanup items addressed
EOF
else
    # Create baseline
    awsideman statistics governance -f json --profile sso-test-1 > "$TRACK_DIR/baseline-metrics.json"
    echo "Baseline metrics established: $TRACK_DIR/baseline-metrics.json"
fi

echo "Cleanup tracking updated: $TRACK_DIR/cleanup-progress-$TRACK_DATE.txt"
```

## Access Efficiency Optimization

### 1. Assignment Pattern Optimization

**Objective**: Optimize assignment patterns to improve efficiency and reduce complexity.

**Assignment Optimization Analysis**:
```bash
#!/bin/bash
# assignment-optimization.sh - Optimize assignment patterns

ASSIGN_DATE=$(date +%Y-%m-%d)
ASSIGN_DIR="/var/optimization/assignments"

mkdir -p "$ASSIGN_DIR"

# Generate assignment optimization analysis
cat > "$ASSIGN_DIR/assignment-optimization-$ASSIGN_DATE.txt" << EOF
ASSIGNMENT PATTERN OPTIMIZATION ANALYSIS - $ASSIGN_DATE
=======================================================

Current Assignment Metrics:
$(awsideman statistics assignments -f json --profile sso-test-1 | jq -r '
"Average Assignments per User: " + (.assignment_patterns.average_assignments_per_user | tostring),
"Users with Most Assignments: " + (.assignment_patterns.users_with_most_assignments[:3] | map(.[0] + " (" + (.[1] | tostring) + ")") | join(", ")),
"Groups with Most Assignments: " + (.assignment_patterns.groups_with_most_assignments[:3] | map(.[0] + " (" + (.[1] | tostring) + ")") | join(", "))
')

Assignment Distribution Analysis:
$(awsideman statistics assignments -f json --profile sso-test-1 | jq -r '
.assignment_patterns.users_with_most_assignments |
map(.[1]) |
group_by(.) |
map({assignments: .[0], users: length}) |
sort_by(.assignments) |
reverse |
map("Users with " + (.assignments | tostring) + " assignments: " + (.users | tostring)) |
join("\n")
' | head -10)

Optimization Opportunities:
1. Review users with excessive assignments (>5)
2. Standardize assignment patterns by role
3. Implement group-based assignments where possible
4. Reduce individual user assignments through groups

Recommended Actions:
[ ] Analyze high-assignment users for role standardization
[ ] Create role-based groups to reduce individual assignments
[ ] Implement assignment templates by job function
[ ] Establish assignment approval workflows
[ ] Regular review of assignment patterns
EOF

# Generate assignment efficiency metrics
awsideman statistics assignments -f json --profile sso-test-1 | jq '{
  efficiency_metrics: {
    total_assignments: (.assignment_patterns.users_with_most_assignments | map(.[1]) | add),
    average_per_user: .assignment_patterns.average_assignments_per_user,
    high_assignment_users: (.assignment_patterns.users_with_most_assignments | map(select(.[1] > 5)) | length),
    group_assignments: (.assignment_patterns.groups_with_most_assignments | map(.[1]) | add)
  },
  optimization_potential: {
    individual_to_group_ratio: (.assignment_patterns.users_with_most_assignments | map(.[1]) | add) / (.assignment_patterns.groups_with_most_assignments | map(.[1]) | add),
    standardization_opportunity: (.assignment_patterns.users_with_most_assignments | map(select(.[1] > 3)) | length)
  }
}' > "$ASSIGN_DIR/assignment-efficiency-$ASSIGN_DATE.json"

echo "Assignment optimization analysis completed: $ASSIGN_DIR/assignment-optimization-$ASSIGN_DATE.txt"
```

### 2. Cross-Account Access Optimization

**Objective**: Optimize cross-account access patterns for better security and management.

**Cross-Account Optimization**:
```bash
#!/bin/bash
# cross-account-optimization.sh - Optimize cross-account access patterns

CROSS_DATE=$(date +%Y-%m-%d)
CROSS_DIR="/var/optimization/cross-account"

mkdir -p "$CROSS_DIR"

# Generate cross-account optimization analysis
cat > "$CROSS_DIR/cross-account-optimization-$CROSS_DATE.txt" << EOF
CROSS-ACCOUNT ACCESS OPTIMIZATION ANALYSIS - $CROSS_DATE
========================================================

Cross-Account Access Metrics:
$(awsideman statistics accounts -f json --profile sso-test-1 | jq -r '
"Total Accounts: " + (.account_metrics.total_accounts | tostring),
"Users with Multi-Account Access: " + (.account_metrics.cross_account_users | length | tostring),
"Groups with Multi-Account Access: " + (.account_metrics.cross_account_groups | length | tostring)
')

Top Cross-Account Users:
$(awsideman statistics accounts -f json --profile sso-test-1 | jq -r '.account_metrics.cross_account_users[:5] | map("- " + .[0] + " (" + (.[1] | tostring) + " accounts)") | join("\n")')

Top Cross-Account Groups:
$(awsideman statistics accounts -f json --profile sso-test-1 | jq -r '.account_metrics.cross_account_groups[:5] | map("- " + .[0] + " (" + (.[1] | tostring) + " accounts)") | join("\n")')

Account Coverage Analysis:
$(awsideman statistics accounts -f json --profile sso-test-1 | jq -r '
.account_metrics.assignments_per_account |
to_entries |
sort_by(.value) |
reverse |
map("- Account " + .key + ": " + (.value | tostring) + " assignments") |
join("\n")
' | head -5)

Optimization Recommendations:
1. Review business justification for extensive cross-account access
2. Implement account-specific roles where possible
3. Use cross-account roles instead of direct assignments
4. Establish clear policies for cross-account access
5. Regular review of cross-account access necessity

Security Considerations:
- Limit cross-account admin access
- Implement additional monitoring for cross-account activities
- Use temporary access for cross-account operations
- Document all cross-account access requirements

Action Plan:
[ ] Review users with access to >3 accounts
[ ] Implement cross-account role strategy
[ ] Establish cross-account access policies
[ ] Set up monitoring for cross-account activities
[ ] Regular review of cross-account access necessity
EOF

echo "Cross-account optimization analysis completed: $CROSS_DIR/cross-account-optimization-$CROSS_DATE.txt"
```

## Optimization Automation

### 1. Automated Optimization Recommendations

**Objective**: Generate automated optimization recommendations based on current statistics.

**Automated Recommendations Script**:
```bash
#!/bin/bash
# automated-optimization.sh - Generate automated optimization recommendations

AUTO_DATE=$(date +%Y-%m-%d)
AUTO_DIR="/var/optimization/automated"

mkdir -p "$AUTO_DIR"

# Generate automated recommendations
awsideman statistics generate -f json --profile sso-test-1 | jq -r '
{
  optimization_date: "'$AUTO_DATE'",
  recommendations: [
    (if (.user_group_metrics.orphaned_users | length) > 0 then
      "CLEANUP: Remove " + (.user_group_metrics.orphaned_users | length | tostring) + " orphaned users"
    else empty end),
    (if (.user_group_metrics.orphaned_groups | length) > 0 then
      "CLEANUP: Remove " + (.user_group_metrics.orphaned_groups | length | tostring) + " empty groups"
    else empty end),
    (if (.permission_set_metrics.unused_permission_sets | length) > 0 then
      "CLEANUP: Remove " + (.permission_set_metrics.unused_permission_sets | length | tostring) + " unused permission sets"
    else empty end),
    (if (.assignment_patterns.average_assignments_per_user) > 4 then
      "OPTIMIZATION: Review assignment patterns - average " + (.assignment_patterns.average_assignments_per_user | tostring) + " assignments per user"
    else empty end),
    (if (.governance_view.privileged_access_report.users_with_admin_access | length) > 5 then
      "SECURITY: Review admin access - " + (.governance_view.privileged_access_report.users_with_admin_access | length | tostring) + " users have admin access"
    else empty end),
    (if (.account_metrics.cross_account_users | length) > 20 then
      "GOVERNANCE: Review cross-account access - " + (.account_metrics.cross_account_users | length | tostring) + " users have multi-account access"
    else empty end)
  ],
  priority_actions: [
    (.governance_view.compliance_gaps[] | select(.severity == "high") | "HIGH: " + .description),
    (.governance_view.compliance_gaps[] | select(.severity == "medium") | "MEDIUM: " + .description)
  ],
  metrics_summary: {
    cleanup_items: ((.user_group_metrics.orphaned_users | length) + (.user_group_metrics.orphaned_groups | length) + (.permission_set_metrics.unused_permission_sets | length)),
    optimization_score: (100 - ((.governance_view.compliance_gaps | length) * 10)),
    efficiency_rating: (if .assignment_patterns.average_assignments_per_user < 3 then "Good" elif .assignment_patterns.average_assignments_per_user < 5 then "Fair" else "Needs Improvement" end)
  }
}
' > "$AUTO_DIR/automated-recommendations-$AUTO_DATE.json"

# Generate human-readable summary
jq -r '
"AUTOMATED OPTIMIZATION RECOMMENDATIONS - " + .optimization_date,
"=" * 50,
"",
"IMMEDIATE ACTIONS:",
(.recommendations[] | "• " + .),
"",
"PRIORITY ITEMS:",
(.priority_actions[] | "• " + .),
"",
"OPTIMIZATION METRICS:",
"• Cleanup Items: " + (.metrics_summary.cleanup_items | tostring),
"• Optimization Score: " + (.metrics_summary.optimization_score | tostring) + "/100",
"• Efficiency Rating: " + .metrics_summary.efficiency_rating,
"",
"Generated: " + .optimization_date
' "$AUTO_DIR/automated-recommendations-$AUTO_DATE.json" > "$AUTO_DIR/optimization-summary-$AUTO_DATE.txt"

echo "Automated optimization recommendations generated: $AUTO_DIR/optimization-summary-$AUTO_DATE.txt"
```

### 2. Optimization Progress Tracking

**Objective**: Track optimization progress over time and measure improvements.

**Progress Tracking Script**:
```bash
#!/bin/bash
# optimization-progress.sh - Track optimization progress over time

PROGRESS_DATE=$(date +%Y-%m-%d)
PROGRESS_DIR="/var/optimization/progress"

mkdir -p "$PROGRESS_DIR"

# Generate current optimization metrics
awsideman statistics generate -f json --profile sso-test-1 | jq '{
  date: "'$PROGRESS_DATE'",
  metrics: {
    total_users: .user_group_metrics.total_users,
    orphaned_users: (.user_group_metrics.orphaned_users | length),
    total_groups: .user_group_metrics.total_groups,
    empty_groups: (.user_group_metrics.orphaned_groups | length),
    total_permission_sets: .permission_set_metrics.total_permission_sets,
    unused_permission_sets: (.permission_set_metrics.unused_permission_sets | length),
    average_assignments_per_user: .assignment_patterns.average_assignments_per_user,
    compliance_gaps: (.governance_view.compliance_gaps | length),
    optimization_score: (100 - ((.governance_view.compliance_gaps | length) * 10))
  }
}' > "$PROGRESS_DIR/metrics-$PROGRESS_DATE.json"

# Append to historical tracking
echo "$PROGRESS_DATE,$(jq -r '.metrics.optimization_score' "$PROGRESS_DIR/metrics-$PROGRESS_DATE.json")" >> "$PROGRESS_DIR/optimization-trend.csv"

# Generate progress report if historical data exists
if [ $(ls "$PROGRESS_DIR"/metrics-*.json 2>/dev/null | wc -l) -gt 1 ]; then
    PREVIOUS_FILE=$(ls "$PROGRESS_DIR"/metrics-*.json | tail -2 | head -1)

    cat > "$PROGRESS_DIR/progress-report-$PROGRESS_DATE.txt" << EOF
OPTIMIZATION PROGRESS REPORT - $PROGRESS_DATE
============================================

Progress Since Last Measurement:

Cleanup Progress:
- Orphaned Users: $(jq '.metrics.orphaned_users' "$PREVIOUS_FILE") → $(jq '.metrics.orphaned_users' "$PROGRESS_DIR/metrics-$PROGRESS_DATE.json") ($(echo "$(jq '.metrics.orphaned_users' "$PREVIOUS_FILE") - $(jq '.metrics.orphaned_users' "$PROGRESS_DIR/metrics-$PROGRESS_DATE.json")" | bc) cleaned)
- Empty Groups: $(jq '.metrics.empty_groups' "$PREVIOUS_FILE") → $(jq '.metrics.empty_groups' "$PROGRESS_DIR/metrics-$PROGRESS_DATE.json") ($(echo "$(jq '.metrics.empty_groups' "$PREVIOUS_FILE") - $(jq '.metrics.empty_groups' "$PROGRESS_DIR/metrics-$PROGRESS_DATE.json")" | bc) cleaned)
- Unused Permission Sets: $(jq '.metrics.unused_permission_sets' "$PREVIOUS_FILE") → $(jq '.metrics.unused_permission_sets' "$PROGRESS_DIR/metrics-$PROGRESS_DATE.json") ($(echo "$(jq '.metrics.unused_permission_sets' "$PREVIOUS_FILE") - $(jq '.metrics.unused_permission_sets' "$PROGRESS_DIR/metrics-$PROGRESS_DATE.json")" | bc) cleaned)

Efficiency Improvements:
- Average Assignments per User: $(jq '.metrics.average_assignments_per_user' "$PREVIOUS_FILE") → $(jq '.metrics.average_assignments_per_user' "$PROGRESS_DIR/metrics-$PROGRESS_DATE.json")
- Compliance Gaps: $(jq '.metrics.compliance_gaps' "$PREVIOUS_FILE") → $(jq '.metrics.compliance_gaps' "$PROGRESS_DIR/metrics-$PROGRESS_DATE.json")
- Optimization Score: $(jq '.metrics.optimization_score' "$PREVIOUS_FILE") → $(jq '.metrics.optimization_score' "$PROGRESS_DIR/metrics-$PROGRESS_DATE.json")

Overall Progress: $(echo "scale=2; ($(jq '.metrics.optimization_score' "$PROGRESS_DIR/metrics-$PROGRESS_DATE.json") - $(jq '.metrics.optimization_score' "$PREVIOUS_FILE")) / $(jq '.metrics.optimization_score' "$PREVIOUS_FILE") * 100" | bc)% improvement
EOF
fi

echo "Optimization progress tracking updated: $PROGRESS_DIR/progress-report-$PROGRESS_DATE.txt"
```

This access optimization guide provides comprehensive coverage of optimization scenarios using the Statistics module. Regular implementation of these practices will help maintain an efficient, secure, and well-governed AWS Identity Center environment while reducing administrative overhead and complexity.
