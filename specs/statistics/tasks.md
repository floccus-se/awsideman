# Implementation Plan

- [x] 1. Set up statistics module structure and core interfaces
  - Create directory structure for statistics module under src/awsideman/statistics/
  - Define core interfaces (StatisticsCollectorInterface, StatisticsAnalyzerInterface, StatisticsExporterInterface)
  - Create base data models for statistics (UserGroupMetrics, PermissionSetMetrics, AccountMetrics, etc.)
  - _Requirements: 1.1, 1.2, 2.1, 3.1, 4.1, 5.1_

- [-] 2. Implement data models and validation
  - [x] 2.1 Create core statistics data models
    - Write dataclasses for UserGroupMetrics, PermissionSetMetrics, AccountMetrics
    - Implement AssignmentPatterns and GovernanceView models
    - Create StatisticsReport wrapper model with metadata
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 5.1_

  - [x] 2.2 Implement supporting data models
    - Create AccessMatrix model for "who has access to what" relationships
    - Implement PrivilegedAccessReport and TrendAnalysis models
    - Add validation methods for data integrity
    - _Requirements: 5.1, 5.2, 4.4, 4.5_

- [x] 3. Create StatisticsCollector for data gathering
  - [x] 3.1 Implement base collector with AWS client integration
    - Create StatisticsCollector class with AWSClientManager integration
    - Implement methods for collecting users, groups, permission sets from Identity Center APIs
    - Add pagination handling for large datasets
    - _Requirements: 1.1, 1.2, 2.1, 3.1, 8.1, 8.2_

  - [x] 3.2 Add assignment and account data collection
    - Implement assignment collection across all accounts
    - Add Organizations client integration for account information
    - Create parallel collection methods for performance
    - _Requirements: 3.1, 3.2, 3.4, 3.5, 4.1, 4.2, 8.1, 8.2_

  - [x] 3.3 Integrate caching and error handling
    - Add cache integration using existing awsideman cache system
    - Implement retry logic with exponential backoff for AWS API errors
    - Add graceful degradation for partial data collection failures
    - _Requirements: 8.1, 8.4, 8.5_

- [x] 4. Implement StatisticsAnalyzer for calculations and pattern detection
  - [x] 4.1 Create user and group analysis methods
    - Implement calculate_user_group_metrics method
    - Add orphaned user and group detection logic
    - Create group membership distribution calculations
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [x] 4.2 Add permission set usage analysis
    - Implement permission set assignment counting and distribution
    - Create unused permission set detection
    - Add most frequently assigned permission set identification
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 4.3 Implement account and assignment pattern analysis
    - Create account access distribution calculations
    - Add cross-account access breadth analysis
    - Implement assignment pattern detection (average assignments, high-access users)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 4.2, 4.3_

  - [x] 4.4 Add governance and privileged access detection
    - Implement access matrix generation for "who has access to what"
    - Create privileged permission set detection based on policy analysis
    - Add empty mapping detection (groups with no members, permission sets with no assignments)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 4.5 Implement historical comparison and trend analysis
    - Create methods to compare current statistics with backup snapshots
    - Add assignment growth calculation over time
    - Implement significant change detection between time periods
    - _Requirements: 4.4, 4.5_

- [x] 5. Create StatisticsExporter for output formatting
  - [x] 5.1 Implement JSON export functionality
    - Create JSON serialization for all statistics models
    - Add structured data output for programmatic access
    - Implement proper JSON formatting with metadata
    - _Requirements: 6.1, 6.4_

  - [x] 5.2 Add CSV export with category support
    - Implement CSV export for spreadsheet analysis
    - Create category-specific CSV outputs (users, groups, permission sets, etc.)
    - Add proper CSV formatting with headers and data validation
    - _Requirements: 6.2_

  - [x] 5.3 Create formatted text output
    - Implement human-readable text reports with tables and summaries
    - Add executive summary formatting
    - Create detailed report formatting with sections
    - _Requirements: 6.3_

  - [x] 5.4 Add filtering and customization support
    - Implement filtering by account, user, group, or permission set
    - Add category selection for specific statistic types
    - Create preset filters for high-risk scenarios
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 6. Implement StatisticsManager as main orchestrator
  - [x] 6.1 Create main StatisticsManager class
    - Implement StatisticsManager with collector, analyzer, and exporter integration
    - Add generate_statistics method with category and filter support
    - Create specific generation methods for each statistic category
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 6.2 Add historical data integration
    - Implement backup snapshot loading for historical comparison
    - Add trend analysis coordination between current and historical data
    - Create error handling for missing or invalid historical data
    - _Requirements: 4.4, 4.5_

  - [x] 6.3 Implement performance optimization
    - Add parallel processing coordination for large datasets
    - Implement memory-efficient data processing in chunks
    - Add progress reporting for long-running operations
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 7. Create CLI commands for statistics functionality
  - [x] 7.1 Set up CLI command structure
    - Create statistics command module under src/awsideman/commands/statistics/
    - Implement main statistics app with typer integration
    - Add command registration following awsideman CLI patterns
    - _Requirements: 6.1, 6.2, 6.3, 7.1, 7.2_

  - [x] 7.2 Implement generate command with options
    - Create main generate_statistics command with category selection
    - Add filtering options (account, user, group, permission set filters)
    - Implement output format options (JSON, CSV, text)
    - Add profile and region options following awsideman patterns
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 7.3 Add category-specific commands
    - Implement specific commands for users, groups, permission-sets, accounts, assignments
    - Create governance command for governance-oriented views
    - Add export command for format-specific exports
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 2.2, 2.3, 2.4, 2.5, 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 7.4 Integrate with existing awsideman infrastructure
    - Add cache integration using common.py patterns
    - Implement profile validation with validate_profile_with_cache
    - Add error handling using handle_aws_error patterns
    - _Requirements: 8.1, 8.4_

- [x] 8. Write comprehensive unit tests
  - [x] 8.1 Create tests for StatisticsCollector
    - Write unit tests for data collection methods (users, groups, permission sets)
    - Test pagination handling and parallel collection
    - Add tests for cache integration and error handling
    - _Requirements: 1.1, 1.2, 2.1, 3.1, 8.1, 8.2_

  - [x] 8.2 Add tests for StatisticsAnalyzer
    - Test user and group metrics calculations
    - Write tests for orphaned resource detection
    - Add tests for privileged access detection and access matrix generation
    - Test historical comparison and trend analysis
    - _Requirements: 1.3, 1.4, 1.5, 1.6, 2.2, 2.3, 2.4, 2.5, 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 8.3 Create tests for StatisticsExporter
    - Test JSON, CSV, and text export functionality
    - Write tests for filtering and category selection
    - Add tests for output formatting and data validation
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 8.4 Add tests for StatisticsManager integration
    - Test end-to-end statistics generation workflow
    - Write tests for error handling and graceful degradation
    - Add performance tests for large dataset handling
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 9. Create integration tests with AWS services
  - [x] 9.1 Implement integration tests with mock AWS data
    - Create integration tests using existing awsideman test fixtures
    - Test with realistic Identity Center data structures
    - Add tests for cross-account scenarios
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 9.2 Add performance and scalability tests
    - Test performance with large user bases (1000+ users)
    - Add memory usage tests for large datasets
    - Test cache effectiveness and parallel processing efficiency
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 10. Add CLI integration to main awsideman app
  - Register statistics command in main CLI app (src/awsideman/cli.py)
  - Update commands/__init__.py to include statistics module
  - Add statistics to help documentation and command discovery
  - _Requirements: 6.1, 6.2, 6.3, 7.1, 7.2_

- [x] 11. Create documentation and examples
  - [x] 11.1 Write user documentation
    - Create README for statistics module with usage examples
    - Document all available statistics and their meanings
    - Add troubleshooting guide for common issues
    - _Requirements: 6.1, 6.2, 6.3, 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 11.2 Add example outputs and use cases
    - Create example JSON, CSV, and text outputs
    - Document filtering and customization options
    - Add governance and security use case examples
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 7.1, 7.2, 7.3, 7.4, 7.5_
