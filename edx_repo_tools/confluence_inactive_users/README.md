# Deactivate Inactive Confluence Users

This script identifies and suspends Confluence Cloud users who have been inactive for a specified period of time, helping to manage license costs, maintain security, and reduce spam.

## Overview

The script uses the [Atlassian Organizations REST API](https://developer.atlassian.com/cloud/admin/organization/rest/intro/) to:

1. Fetch the directory ID for your Atlassian organization
2. Retrieve all users from the organization directory
3. Check each user's last active date in Confluence
4. Optionally suspend users who haven't logged into Confluence for a specified number of days

**Important:** Suspended users:
- Retain their group memberships and can be easily restored
- Do not have their accounts deleted

## Prerequisites

### API Key Setup

1. Go to [https://admin.atlassian.com/](https://admin.atlassian.com/) and select your organization
2. Navigate to **Settings** > **API keys**
3. Click **Create API key**
5. **Important:** Choose a short lifetime since it has wide privileges
4. **Important:** Choose **"API keys without scopes"** - scoped keys will not work with this script
5. Copy and securely store your API key (you won't be able to see it again)
6. Copy your Organization ID from the Settings page

### Permissions

- You must be an **Organization Admin** to create API keys and suspend users
- The API key must have **no scopes** (organization-level access)

### Installation

First, set up the repo-tools project as described in the [root README](../../README.rst):

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies for this tool
uv sync --extra confluence_inactive_users
```

## Usage

### Basic Usage

Set your credentials as environment variables:

```bash
export ATLASSIAN_ORG_ID="your-org-id-here"
export ATLASSIAN_API_KEY="your-api-key-here"
```

Run the script in **dry-run mode** (default) to see which users would be suspended:

```bash
uv run deactivate_inactive_confluence_users
```

Or if you prefer to activate the virtual environment:

```bash
source .venv/bin/activate
deactivate_inactive_confluence_users
```

### Actually Suspend Users

To actually suspend users (not just preview), use the `--no-dry-run` flag:

```bash
uv run deactivate_inactive_confluence_users --no-dry-run
```

**⚠️ Warning:** This will actually suspend users! Make sure you've reviewed the dry-run output first.

### Common Options

```bash
# Check for users inactive for 90 days instead of the default 180
uv run deactivate_inactive_confluence_users --inactive-days 90

# Exclude specific users from suspension
uv run deactivate_inactive_confluence_users \
  --exclude-user admin@company.com \
  --exclude-user serviceaccount@company.com \
  --no-dry-run
```

### All Options

| Option | Environment Variable | Default | Description |
|--------|---------------------|---------|-------------|
| `--org-id` | `ATLASSIAN_ORG_ID` | (required) | Your Atlassian organization ID |
| `--api-key` | `ATLASSIAN_API_KEY` | (required) | Your API key from Admin console |
| `--inactive-days` | - | 180 | Number of days of inactivity before suspension |
| `--dry-run` | - | `true` | Preview mode (no actual changes) |
| `--no-dry-run` | - | `false` | Actually suspend users |
| `--exclude-user` | - | - | User to exclude (can be specified multiple times) |

## Example Output

### Dry Run

```
Organization ID: abc123-def456-ghi789
Directory ID: xyz789-uvw456-rst123
Product: confluence
Inactive threshold: 180 days (before 2024-06-01)
Mode: DRY RUN
Excluded users: admin@company.com

================================================================================

Fetching all users from Atlassian organization...
Found 150 total users

Processing users  [####################################]  100%

================================================================================
RESULTS
================================================================================

Total users processed: 150
Active users (within threshold): 120
Inactive users (beyond threshold): 15
Users with no confluence login data: 10
Already suspended/inactive: 3
Excluded users: 1
Errors: 1

INACTIVE USERS TO SUSPEND:
--------------------------------------------------------------------------------
  • John Doe (john@example.com) - Last active: 2023-08-15 (245 days ago)
  • Jane Smith (jane@example.com) - Last active: 2023-09-20 (209 days ago)
  • Bob Wilson (bob@example.com) - Last active: 2023-10-10 (189 days ago)

================================================================================
```

### Live Run

When you run with `--no-dry-run`, the script will prompt for confirmation and then suspend the users:

```
⚠️  You are about to suspend users. They can be restored later, but will temporarily lose access. Continue? [y/N]: y

================================================================================
SUSPENDING USERS...
================================================================================

Suspending John Doe (john@example.com)... ✓ SUCCESS
Suspending Jane Smith (jane@example.com)... ✓ SUCCESS
Suspending Bob Wilson (bob@example.com)... ✓ SUCCESS

Suspension complete: 3 succeeded, 0 failed
```

## Restoring Suspended Users

If you need to restore a user's access, you can:

1. **Via Admin Console:** Go to admin.atlassian.com > Directory > Users, find the user, and click "Restore access"
2. **Via API:** Use the [Restore user access in directory](https://developer.atlassian.com/cloud/admin/organization/rest/api-group-users/#api-orgs-orgid-directories-directoryid-users-accountid-restore-post) endpoint

## Limitations

- The script assumes your organization has exactly **one directory** (the typical case)
- Last active data may be delayed by up to 24 hours according to Atlassian's API
- The API is rate-limited (200 requests per minute for last-active-dates endpoint)
- Users with no login data (never logged in or service accounts) are not suspended

## Troubleshooting

### "Error: API key authentication failed"

- Ensure your API key is created with **no scopes**
- Verify you're an Organization Admin
- Check that your API key hasn't expired

### "Found more than 1 directory"

The script assumes a single directory. If you have multiple directories, you'll need to modify the `get_directory_id()` function to handle your specific case.

### Rate Limiting

If you have a very large organization (thousands of users), you may hit rate limits. The script will show errors for affected users. Wait a minute and re-run the script.

## Security Best Practices

- Store your API key securely (use environment variables or a secrets manager)
- Never commit your API key to version control
- Use short lived API keys as much as possible
- Always run in dry-run mode first to preview changes
- Keep an audit log of suspended users


## References

- [Atlassian Organizations REST API Documentation](https://developer.atlassian.com/cloud/admin/organization/rest/intro/)
- [Managing users in the Admin console](https://support.atlassian.com/organization-administration/docs/manage-users/)
- [API key creation guide](https://support.atlassian.com/organization-administration/docs/manage-an-organization-with-the-admin-apis/)
