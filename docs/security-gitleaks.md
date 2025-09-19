# Gitleaks Integration for Sensitive Data Detection

This document describes the Gitleaks integration in the awsideman project for detecting sensitive data and secrets in commits.

## Overview

[Gitleaks](https://github.com/gitleaks/gitleaks) is a comprehensive tool for detecting hardcoded secrets and sensitive data in git repositories. It's integrated as a pre-commit hook to prevent sensitive data from being committed to the repository.

## What Gitleaks Detects

### Default Detection
Gitleaks comes with built-in rules to detect:
- API keys and tokens
- Database credentials
- SSH keys
- AWS credentials
- GitHub tokens
- And many more common secret patterns

### Custom AWS-Specific Rules
Our custom configuration (`.gitleaks.toml`) adds detection for:

1. **Email Addresses** (`awsideman-email-addresses`)
   - Detects email addresses in code and documentation
   - Tags: `email`, `pii`

2. **Real AWS Profile Names** (`awsideman-real-profile-names`)
   - Detects AWS profile names that aren't test profiles
   - Tags: `aws`, `profile`, `sensitive`

3. **Real AWS Account IDs** (`awsideman-real-account-ids`)
   - Detects 12-digit AWS account IDs
   - Tags: `aws`, `account-id`, `sensitive`

4. **Real AWS ARNs** (`awsideman-real-arns`)
   - Detects AWS ARNs containing account IDs
   - Tags: `aws`, `arn`, `sensitive`

5. **Real AWS Instance IDs** (`awsideman-real-instance-ids`)
   - Detects AWS instance IDs
   - Tags: `aws`, `instance`, `sensitive`

6. **Real S3 Bucket Names** (`awsideman-real-bucket-names`)
   - Detects S3 bucket names
   - Tags: `aws`, `s3`, `bucket`, `sensitive`

7. **Real AWS Region Names** (`awsideman-real-region-names`)
   - Detects AWS region names
   - Tags: `aws`, `region`, `sensitive`

8. **Real Usernames** (`awsideman-real-user-names`)
   - Detects usernames that aren't test users
   - Tags: `username`, `pii`, `sensitive`

9. **Real Group Names** (`awsideman-real-group-names`)
   - Detects group names that aren't test groups
   - Tags: `group`, `pii`, `sensitive`

10. **Real Permission Set Names** (`awsideman-real-permission-set-names`)
    - Detects permission set names that aren't test permission sets
    - Tags: `permission-set`, `sensitive`

## Configuration Files

### `.gitleaks.toml`
Main configuration file containing:
- Custom detection rules
- Rule descriptions and tags
- Regex patterns for sensitive data

### `.gitleaksignore`
File for ignoring false positives by adding fingerprints of known safe detections.

## Usage

### Pre-commit Hook
Gitleaks runs automatically on every commit as part of the pre-commit hooks. If sensitive data is detected, the commit will be blocked.

### Manual Scanning
You can run Gitleaks manually:

```bash
# Scan all files
poetry run pre-commit run gitleaks --all-files

# Scan specific files
poetry run pre-commit run gitleaks --files file1.py file2.py
```

### Ignoring False Positives

If Gitleaks detects something that's actually safe (like test data), you can ignore it by adding the fingerprint to `.gitleaksignore`:

1. Run Gitleaks to get the fingerprint:
   ```bash
   poetry run pre-commit run gitleaks --all-files
   ```

2. Copy the fingerprint from the output
3. Add it to `.gitleaksignore`:
   ```
   # Example fingerprint
   7ef7dc00583b3fcf88916ab2567e4a43cac3ade8:src/awsideman/utils/example.py:awsideman-email-addresses:5
   ```

### Allowing Specific Secrets

For test secrets that you knowingly want to commit, you can add a `gitleaks:allow` comment:

```python
# This will be ignored by Gitleaks
test_api_key = "sk_test_1234567890abcdef"  # gitleaks:allow
```

## Best Practices

1. **Use Test Data**: Always use test data in examples and documentation:
   - Email: `test@example.com`
   - Profile: `sso-test-1`, `sso-test-2`
   - Account ID: `123456789012`
   - Username: `testuser`
   - Group: `testgroup`

2. **Environment Variables**: Use environment variables for sensitive data:
   ```python
   import os
   api_key = os.getenv('API_KEY')
   ```

3. **Configuration Files**: Store sensitive data in configuration files that are gitignored:
   ```python
   # config.py
   import json
   with open('secrets.json') as f:
       secrets = json.load(f)
   ```

4. **Regular Scanning**: Run Gitleaks regularly to catch any sensitive data that might have been missed.

## Troubleshooting

### Common Issues

1. **False Positives**: If Gitleaks detects something that's not actually sensitive, add it to `.gitleaksignore`.

2. **Regex Errors**: If you see regex compilation errors, check the regex patterns in `.gitleaks.toml` for syntax issues.

3. **Performance**: Gitleaks can be slow on large repositories. Consider excluding large files or directories in the configuration.

### Getting Help

- [Gitleaks Documentation](https://github.com/gitleaks/gitleaks)
- [Gitleaks Configuration Reference](https://github.com/gitleaks/gitleaks#configuration)
- [Pre-commit Hooks Documentation](https://pre-commit.com/)

## Security Benefits

This integration provides several security benefits:

1. **Prevents Accidental Exposure**: Stops sensitive data from being committed accidentally
2. **Compliance**: Helps meet security compliance requirements
3. **Early Detection**: Catches issues before they reach the remote repository
4. **Customizable**: Can be tailored to detect project-specific sensitive data
5. **Automated**: Runs automatically on every commit

## Maintenance

- Regularly update Gitleaks to get the latest detection rules
- Review and update custom rules as the project evolves
- Clean up `.gitleaksignore` periodically to remove outdated entries
- Test the configuration with new types of sensitive data
