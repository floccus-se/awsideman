# Statistics Module Troubleshooting Guide

This guide provides detailed troubleshooting information for common issues encountered when using the AWS Identity Center Statistics module.

## Quick Diagnostics

### Check System Status

Before troubleshooting specific issues, verify the basic system status:

```bash
# Check awsideman configuration
awsideman config show --profile sso-test-1

# Verify AWS credentials
aws sts get-caller-identity --profile sso-test-1

# Check Identity Center instance
aws sso-admin list-instances --profile sso-test-1 --region eu-north-1

# Test cache connectivity
awsideman cache status --profile sso-test-1
```

### Enable Debug Mode

For detailed troubleshooting information:

```bash
# Enable verbose output
awsideman statistics generate --verbose --profile sso-test-1

# Check logs
tail -f ~/.awsideman/logs/awsideman.log

# Force fresh data collection
awsideman statistics generate --no-cache --verbose --profile sso-test-1
```

## Common Error Messages

### Authentication and Authorization Errors

#### Error: "Unable to locate credentials"

**Symptoms:**
```
Error: Unable to locate credentials. You can configure credentials by running "aws configure".
```

**Causes:**
- AWS profile not configured
- Invalid or expired credentials
- Missing profile specification

**Solutions:**

1. **Configure AWS profile:**
   ```bash
   aws configure --profile sso-test-1
   ```

2. **Verify profile exists:**
   ```bash
   aws configure list --profile sso-test-1
   ```

3. **Always specify profile:**
   ```bash
   awsideman statistics generate --profile sso-test-1
   ```

4. **Check credential file:**
   ```bash
   cat ~/.aws/credentials
   cat ~/.aws/config
   ```

#### Error: "An error occurred (AccessDenied)"

**Symptoms:**
```
Error: An error occurred (AccessDenied) when calling the ListInstances operation:
User: arn:aws:iam::123456789012:user/username is not authorized to perform: sso:ListInstances
```

**Causes:**
- Insufficient IAM permissions
- Missing Identity Center permissions
- Wrong region or account

**Solutions:**

1. **Verify required permissions:**
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

2. **Check current permissions:**
   ```bash
   aws iam simulate-principal-policy \
     --policy-source-arn $(aws sts get-caller-identity --query Arn --output text --profile sso-test-1) \
     --action-names sso:ListInstances \
     --profile sso-test-1
   ```

3. **Verify region:**
   ```bash
   awsideman statistics generate --profile sso-test-1 --region eu-north-1
   ```

#### Error: "No Identity Center instance found"

**Symptoms:**
```
Error: No Identity Center instance found in region eu-north-1
```

**Causes:**
- Identity Center not enabled in the region
- Wrong region specified
- Account doesn't have Identity Center

**Solutions:**

1. **Check Identity Center status:**
   ```bash
   aws sso-admin list-instances --profile sso-test-1 --region eu-north-1
   ```

2. **Verify correct region:**
   ```bash
   # Check all regions for Identity Center
   for region in us-east-1 us-west-2 eu-west-1 eu-north-1; do
     echo "Checking $region..."
     aws sso-admin list-instances --region $region --profile sso-test-1 2>/dev/null || echo "No instance in $region"
   done
   ```

3. **Enable Identity Center:**
   - Go to AWS Console → Identity Center
   - Enable Identity Center in the correct region
   - Wait for setup to complete

### Data Collection Errors

#### Error: "Timeout waiting for response"

**Symptoms:**
```
Error: Timeout waiting for response from AWS API
```

**Causes:**
- Network connectivity issues
- Large dataset causing timeouts
- AWS service throttling
- Slow API responses

**Solutions:**

1. **Check network connectivity:**
   ```bash
   # Test AWS API connectivity
   curl -I https://sso.eu-north-1.amazonaws.com

   # Check DNS resolution
   nslookup sso.eu-north-1.amazonaws.com
   ```

2. **Use category filtering:**
   ```bash
   # Generate statistics in smaller chunks
   awsideman statistics users --profile sso-test-1
   awsideman statistics groups --profile sso-test-1
   awsideman statistics permission-sets --profile sso-test-1
   ```

3. **Enable caching:**
   ```bash
   # Use cached data to reduce API calls
   awsideman statistics generate --profile sso-test-1
   ```

4. **Retry with backoff:**
   ```bash
   # The module automatically retries, but you can manually retry
   sleep 30
   awsideman statistics generate --profile sso-test-1
   ```

#### Error: "Rate limit exceeded"

**Symptoms:**
```
Error: Rate limit exceeded. Please try again later.
```

**Causes:**
- Too many API calls in short time
- AWS service throttling
- Concurrent operations

**Solutions:**

1. **Wait and retry:**
   ```bash
   # Wait for rate limit to reset
   sleep 60
   awsideman statistics generate --profile sso-test-1
   ```

2. **Use caching:**
   ```bash
   # Enable caching to reduce API calls
   awsideman cache status --profile sso-test-1
   awsideman statistics generate --profile sso-test-1
   ```

3. **Reduce concurrent operations:**
   - Stop other AWS operations
   - Generate statistics during off-peak hours
   - Use category filtering to reduce load

#### Error: "Partial data collection failed"

**Symptoms:**
```
Warning: Some data could not be collected. Report may be incomplete.
```

**Causes:**
- Intermittent network issues
- Partial permission failures
- Service availability issues

**Solutions:**

1. **Check specific failures:**
   ```bash
   # Enable verbose logging
   awsideman statistics generate --verbose --profile sso-test-1
   ```

2. **Retry with fresh data:**
   ```bash
   # Clear cache and retry
   awsideman cache clear --profile sso-test-1
   awsideman statistics generate --no-cache --profile sso-test-1
   ```

3. **Generate specific categories:**
   ```bash
   # Test each category individually
   awsideman statistics users --verbose --profile sso-test-1
   awsideman statistics groups --verbose --profile sso-test-1
   ```

### Performance Issues

#### Issue: "Statistics generation is very slow"

**Symptoms:**
- Long wait times during data collection
- High CPU or memory usage
- Timeouts or incomplete results

**Causes:**
- Large number of users/groups/assignments
- Network latency
- Inefficient data processing
- Cache misses

**Solutions:**

1. **Enable caching:**
   ```bash
   # Check cache status
   awsideman cache status --profile sso-test-1

   # Use cached data
   awsideman statistics generate --profile sso-test-1
   ```

2. **Use category filtering:**
   ```bash
   # Generate specific categories only
   awsideman statistics generate -c users -c groups --profile sso-test-1
   ```

3. **Optimize system resources:**
   ```bash
   # Check system resources
   free -h
   top -p $(pgrep -f awsideman)

   # Close unnecessary applications
   # Ensure sufficient memory (>2GB recommended)
   ```

4. **Use export commands for large datasets:**
   ```bash
   # Export specific data types
   awsideman statistics export-json -o users.json -c users --profile sso-test-1
   awsideman statistics export-json -o groups.json -c groups --profile sso-test-1
   ```

#### Issue: "Out of memory errors"

**Symptoms:**
```
Error: MemoryError: Unable to allocate memory
```

**Causes:**
- Large datasets exceeding available memory
- Memory leaks in processing
- Insufficient system memory

**Solutions:**

1. **Check memory usage:**
   ```bash
   # Monitor memory during execution
   free -h
   ps aux | grep awsideman
   ```

2. **Use category filtering:**
   ```bash
   # Process data in smaller chunks
   awsideman statistics users --profile sso-test-1
   awsideman statistics permission-sets --profile sso-test-1
   awsideman statistics accounts --profile sso-test-1
   ```

3. **Increase system memory:**
   - Close other applications
   - Increase swap space
   - Use a machine with more RAM

4. **Use streaming export:**
   ```bash
   # Export directly to files
   awsideman statistics export-csv -o stats.csv --split-categories --profile sso-test-1
   ```

### Cache-Related Issues

#### Error: "Cache connection failed"

**Symptoms:**
```
Warning: Cache connection failed. Proceeding without cache.
```

**Causes:**
- Redis server not running
- Connection configuration issues
- Network connectivity problems

**Solutions:**

1. **Check cache status:**
   ```bash
   awsideman cache status --profile sso-test-1
   ```

2. **Use without cache:**
   ```bash
   # Bypass cache temporarily
   awsideman statistics generate --no-cache --profile sso-test-1
   ```

3. **Fix cache configuration:**
   ```bash
   # Check Redis status
   redis-cli ping

   # Restart Redis if needed
   sudo systemctl restart redis
   ```

4. **Clear corrupted cache:**
   ```bash
   awsideman cache clear --profile sso-test-1
   ```

#### Issue: "Stale cache data"

**Symptoms:**
- Statistics don't reflect recent changes
- Inconsistent data between runs
- Missing new resources

**Solutions:**

1. **Clear cache:**
   ```bash
   awsideman cache clear --profile sso-test-1
   ```

2. **Force fresh data:**
   ```bash
   awsideman statistics generate --no-cache --profile sso-test-1
   ```

3. **Check cache TTL:**
   ```bash
   awsideman cache status --profile sso-test-1
   ```

### Output and Export Issues

#### Error: "Permission denied writing to file"

**Symptoms:**
```
Error: Permission denied: '/path/to/output.json'
```

**Causes:**
- Insufficient file system permissions
- Directory doesn't exist
- File is locked or in use

**Solutions:**

1. **Check file permissions:**
   ```bash
   # Check directory permissions
   ls -la /path/to/

   # Create directory if needed
   mkdir -p /path/to/output/
   ```

2. **Use different output location:**
   ```bash
   # Write to home directory
   awsideman statistics generate -f json -o ~/report.json --profile sso-test-1

   # Write to current directory
   awsideman statistics generate -f json -o ./report.json --profile sso-test-1
   ```

3. **Check file locks:**
   ```bash
   # Check if file is open
   lsof /path/to/output.json
   ```

#### Error: "Invalid JSON output"

**Symptoms:**
- Malformed JSON in output files
- Parsing errors when reading exports
- Truncated output files

**Causes:**
- Interrupted generation process
- Disk space issues
- Character encoding problems

**Solutions:**

1. **Check disk space:**
   ```bash
   df -h
   ```

2. **Validate JSON:**
   ```bash
   # Check JSON validity
   python -m json.tool report.json
   jq . report.json
   ```

3. **Regenerate with verbose output:**
   ```bash
   awsideman statistics generate -f json -o report.json --verbose --profile sso-test-1
   ```

#### Issue: "CSV export formatting problems"

**Symptoms:**
- Malformed CSV files
- Encoding issues with special characters
- Missing or extra columns

**Solutions:**

1. **Use split categories:**
   ```bash
   # Export each category separately
   awsideman statistics export-csv -o stats.csv --split-categories --profile sso-test-1
   ```

2. **Check encoding:**
   ```bash
   # Verify file encoding
   file -i stats.csv

   # Convert if needed
   iconv -f UTF-8 -t ASCII//IGNORE stats.csv > stats_ascii.csv
   ```

3. **Validate CSV structure:**
   ```bash
   # Check CSV format
   head -5 stats.csv
   csvlint stats.csv
   ```

### Historical Data Issues

#### Error: "Historical data not found"

**Symptoms:**
```
Warning: No historical data found for comparison
```

**Causes:**
- No backup snapshots exist
- Incorrect backup path
- Backup data format issues

**Solutions:**

1. **Create backup first:**
   ```bash
   # Create initial backup
   awsideman backup create --profile sso-test-1

   # Wait and create another backup for comparison
   sleep 3600  # Wait 1 hour
   awsideman backup create --profile sso-test-1
   ```

2. **Check backup location:**
   ```bash
   # List available backups
   awsideman backup list --profile sso-test-1

   # Specify backup path
   awsideman statistics generate --include-historical --backup-path /path/to/backup --profile sso-test-1
   ```

3. **Verify backup format:**
   ```bash
   # Check backup file structure
   ls -la ~/.awsideman/backups/
   ```

#### Error: "Invalid historical data format"

**Symptoms:**
```
Error: Cannot parse historical data from backup
```

**Causes:**
- Corrupted backup files
- Incompatible backup format
- Missing backup components

**Solutions:**

1. **Validate backup:**
   ```bash
   # Check backup integrity
   awsideman backup validate --backup-path /path/to/backup --profile sso-test-1
   ```

2. **Use different backup:**
   ```bash
   # List all backups
   awsideman backup list --profile sso-test-1

   # Try different backup
   awsideman statistics generate --include-historical --backup-path /path/to/other/backup --profile sso-test-1
   ```

3. **Generate without historical data:**
   ```bash
   # Skip historical comparison
   awsideman statistics generate --profile sso-test-1
   ```

## Environment-Specific Issues

### Large Environments (1000+ Users)

**Common Issues:**
- Memory exhaustion
- Long processing times
- API rate limiting
- Timeout errors

**Optimization Strategies:**

1. **Use category filtering:**
   ```bash
   # Process in chunks
   awsideman statistics users --profile sso-test-1 > users_report.txt
   awsideman statistics groups --profile sso-test-1 > groups_report.txt
   awsideman statistics permission-sets --profile sso-test-1 > ps_report.txt
   ```

2. **Enable caching:**
   ```bash
   # Ensure cache is working
   awsideman cache status --profile sso-test-1
   ```

3. **Schedule during off-peak hours:**
   ```bash
   # Run during low-usage periods
   0 2 * * * /usr/local/bin/awsideman statistics generate -f json -o /var/reports/stats.json --profile sso-test-1
   ```

4. **Use export commands:**
   ```bash
   # Direct export to files
   awsideman statistics export-json -o stats.json --profile sso-test-1
   ```

### Multi-Region Environments

**Common Issues:**
- Wrong region specification
- Cross-region data inconsistencies
- Regional service availability

**Solutions:**

1. **Specify correct region:**
   ```bash
   # Always specify the Identity Center region
   awsideman statistics generate --profile sso-test-1 --region eu-north-1
   ```

2. **Check region configuration:**
   ```bash
   # Verify profile region
   aws configure get region --profile sso-test-1
   ```

3. **Test region connectivity:**
   ```bash
   # Test each region
   aws sso-admin list-instances --region eu-north-1 --profile sso-test-1
   ```

### Network-Restricted Environments

**Common Issues:**
- Proxy configuration
- Firewall restrictions
- VPN connectivity

**Solutions:**

1. **Configure proxy:**
   ```bash
   # Set proxy environment variables
   export HTTP_PROXY=http://proxy.company.com:8080
   export HTTPS_PROXY=http://proxy.company.com:8080

   awsideman statistics generate --profile sso-test-1
   ```

2. **Check firewall rules:**
   - Ensure access to AWS API endpoints
   - Verify HTTPS (443) connectivity
   - Check DNS resolution

3. **Test connectivity:**
   ```bash
   # Test AWS API access
   curl -I https://sso.eu-north-1.amazonaws.com
   curl -I https://identitystore.eu-north-1.amazonaws.com
   ```

## Debugging Techniques

### Enable Detailed Logging

```bash
# Set log level
export AWSIDEMAN_LOG_LEVEL=DEBUG

# Enable verbose output
awsideman statistics generate --verbose --profile sso-test-1

# Monitor logs in real-time
tail -f ~/.awsideman/logs/awsideman.log
```

### Isolate Issues

```bash
# Test individual components
awsideman statistics users --verbose --profile sso-test-1
awsideman statistics groups --verbose --profile sso-test-1
awsideman statistics permission-sets --verbose --profile sso-test-1

# Test without cache
awsideman statistics generate --no-cache --verbose --profile sso-test-1

# Test with minimal data
awsideman statistics generate -c users --filter user=test@company.com --profile sso-test-1
```

### Performance Profiling

```bash
# Monitor resource usage
top -p $(pgrep -f awsideman)
iostat -x 1
netstat -i

# Time operations
time awsideman statistics generate --profile sso-test-1

# Memory profiling
valgrind --tool=massif awsideman statistics generate --profile sso-test-1
```

## Getting Additional Help

### Log Analysis

When reporting issues, include relevant log information:

```bash
# Collect logs
awsideman statistics generate --verbose --profile sso-test-1 2>&1 | tee statistics_debug.log

# System information
uname -a
python --version
pip list | grep awsideman

# AWS configuration
aws configure list --profile sso-test-1
aws sts get-caller-identity --profile sso-test-1
```

### Minimal Reproduction

Create a minimal test case:

```bash
# Test with single user
awsideman statistics generate -c users --filter user=test@company.com --verbose --profile sso-test-1

# Test basic functionality
awsideman statistics users --no-cache --verbose --profile sso-test-1
```

### Environment Information

Collect environment details:

```bash
# System resources
free -h
df -h
ulimit -a

# Network configuration
ip route
cat /etc/resolv.conf

# AWS CLI version
aws --version
```

This troubleshooting guide covers the most common issues and their solutions. For additional help, ensure you have detailed logs and system information when seeking support.
