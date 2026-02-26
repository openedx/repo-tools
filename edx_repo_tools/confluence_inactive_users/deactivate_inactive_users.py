"""
Deactivate inactive Confluence Cloud users based on their last login activity.

This script uses the Atlassian Organizations REST API to:
1. Fetch the directory id for an Atlassian organization
2. Fetch all active users from the directory
3. Check their last login date for Confluence
4. Optionally suspend users who have been inactive for a specified period

Authentication uses an API key from the Atlassian Admin console.
*Important*: The API Key must have no scopes, scoped keys will not work!
See: https://developer.atlassian.com/cloud/admin/organization/rest/intro/
"""

import sys
from datetime import datetime, timedelta, timezone

import click
import requests


def get_all_users(org_id, api_key, directory_id, limit=100):
    """
    Fetch all active users from the Atlassian organization.

    Uses the Organizations REST API v2.

    Args:
        org_id: Atlassian organization ID
        api_key: API key for authentication
        directory_id: Directory ID to filter users, we only have 1
        limit: Number of users to fetch per page

    Returns:
        List of user dictionaries
    """
    users = []
    cursor = None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    while True:
        url = f"https://api.atlassian.com/admin/v2/orgs/{org_id}/directories/{directory_id}/users"

        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor

        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        results = data.get("data", [])

        if not results:
            break

        users.extend(results)
        print(f"{len(users)} users fetched")

        # Check for next page
        next_link = data.get("links", {}).get("next")
        if not next_link:
            break

        cursor = next_link

    return users


def get_user_last_active(org_id, api_key, account_id):
    """
    Get the last active dates for a user across all products.

    Args:
        org_id: Atlassian organization ID
        api_key: API key for authentication
        account_id: Atlassian account ID of the user

    Returns:
        Dictionary with product access information or None if error
    """
    url = f"https://api.atlassian.com/admin/v1/orgs/{org_id}/directory/users/{account_id}/last-active-dates"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        click.echo(
            f"Error fetching last active data for user {account_id}: {e}", err=True
        )
        return None


def get_directory_id(org_id, api_key):
    """
    Fetch the directory ID for the organization.

    This assumes the organization has exactly one directory, which is the typical case.

    Args:
        org_id: Atlassian organization ID
        api_key: API key for authentication

    Returns:
        Directory ID string or None if error

    Raises:
        click.ClickException: If more than one directory is found
    """
    url = f"https://api.atlassian.com/admin/v2/orgs/{org_id}/directories"

    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        directories = data["data"]

        if len(directories) != 1:
            raise click.ClickException(
                "Found more than 1 directory, don't know which one to suspend users from!"
            )

        return directories[0]["directoryId"]
    except requests.exceptions.RequestException as e:
        click.echo(f"Error fetching directory IDs: {e}", err=True)
        return None


def suspend_user(org_id, api_key, directory_id, account_id):
    """
    Suspend a user's access in the organization directory.

    This removes their access to apps temporarily without deleting the account.
    You're not billed for a user when their access is suspended.

    Args:
        org_id: Atlassian organization ID
        api_key: API key for authentication
        directory_id: Directory ID where the user exists
        account_id: Atlassian account ID of the user to suspend

    Returns:
        True if successful, False otherwise
    """
    url = f"https://api.atlassian.com/admin/v2/orgs/{org_id}/directories/{directory_id}/users/{account_id}/suspend"

    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    try:
        response = requests.post(url, headers=headers, timeout=30)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        click.echo(f"Error suspending user {account_id}: {e}", err=True)
        return False


def parse_timestamp(timestamp_str):
    """
    Parse an ISO format timestamp string.

    Args:
        timestamp_str: ISO format timestamp string (or None/empty string)

    Returns:
        datetime object with timezone info, or None if input is None/empty or parsing fails
    """
    if not timestamp_str:
        return None

    return datetime.fromisoformat(timestamp_str)


@click.command()
@click.option(
    "--org-id",
    envvar="ATLASSIAN_ORG_ID",
    required=True,
    help="Atlassian organization ID (from Admin console)",
)
@click.option(
    "--api-key",
    envvar="ATLASSIAN_API_KEY",
    required=True,
    help="Atlassian API key (create from Admin > Settings > API keys)",
)
@click.option(
    "--inactive-days",
    default=180,
    type=int,
    help="Number of days of inactivity after which to suspend users (default: 180)",
)
@click.option(
    "--product-key",
    default="confluence",
    help="Product key to check for activity (default: confluence)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=True,
    help="Perform a dry run without actually suspending users (default: enabled)",
)
@click.option(
    "--no-dry-run",
    is_flag=True,
    default=False,
    help="Actually suspend users (disables dry run mode)",
)
@click.option(
    "--exclude-user",
    multiple=True,
    help="Account IDs or emails to exclude from suspension (can be specified multiple times)",
)
def main(
    org_id,
    api_key,
    inactive_days,
    product_key,
    dry_run,
    no_dry_run,
    exclude_user,
):
    """
    Suspend inactive Confluence Cloud users in an Atlassian organization.

    This script identifies users who haven't logged into Confluence for the specified
    number of days and suspends their access. By default, it runs in dry-run mode to
    show which users would be suspended without actually suspending them.

    SETUP:
    1. Go to https://admin.atlassian.com/ and select your organization
    2. Navigate to Settings > API keys
    3. Create an API key (requires Organization Admin permissions)
        3.1 Choose "API keys without scopes", scoped keys will not work
    4. Copy the Organization ID from the Settings page

    Examples:

        # Dry run (default) - see which users would be suspended
        export ATLASSIAN_ORG_ID="your-org-id"
        export ATLASSIAN_API_KEY="your-api-key"
        uv run deactivate_inactive_confluence_users

        # Actually suspend users inactive for 180 days
        uv run deactivate_inactive_confluence_users --no-dry-run

        # Suspend users inactive for 90 days, excluding specific users
        uv run deactivate_inactive_confluence_users --inactive-days 90 --no-dry-run \\
            --exclude-user user1@example.com --exclude-user user2@example.com
    """
    # Handle dry-run flag logic
    if no_dry_run:
        dry_run = False

    # Calculate the cutoff date
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=inactive_days)

    click.echo(f"Organization ID: {org_id}")
    directory_id = get_directory_id(org_id, api_key)
    click.echo(f"Directory ID: {directory_id}")

    click.echo(f"Product: {product_key}")
    click.echo(
        f"Inactive threshold: {inactive_days} days (before {cutoff_date.strftime('%Y-%m-%d')})"
    )
    click.echo(f"Mode: {'DRY RUN' if dry_run else 'LIVE - WILL SUSPEND USERS'}")
    click.echo(f"Excluded users: {', '.join(exclude_user) if exclude_user else 'None'}")
    click.echo("\n" + "=" * 80 + "\n")

    if not dry_run:
        click.confirm(
            "⚠️  You are about to suspend users. They can be restored later, but will temporarily lose access. Continue?",
            abort=True,
        )

    try:
        # Fetch all users
        click.echo("Fetching all users from Atlassian organization...")
        users = get_all_users(org_id, api_key, directory_id)
        click.echo(f"Found {len(users)} total users\n")

        # Track statistics
        inactive_users = []
        active_users = []
        no_login_data = []
        excluded_count = 0
        suspended_already = 0
        errors = 0

        # Process each user
        with click.progressbar(users, label="Processing users") as bar:
            for user in bar:
                # Handle both v1 and v2 API response formats
                account_id = user.get("accountId") or user.get("account_id")
                display_name = user.get("name") or user.get("displayName", "Unknown")
                email = user.get("email", "N/A")

                # Check account status
                account_status = user.get("accountStatus") or user.get("account_status")
                membership_status = user.get("membershipStatus") or user.get("status")

                # Skip if already inactive/suspended
                if (
                    account_status in ["inactive", "closed"]
                    or membership_status == "suspended"
                ):
                    suspended_already += 1
                    continue

                # Skip excluded users
                if (
                    account_id in exclude_user
                    or email in exclude_user
                    or display_name in exclude_user
                ):
                    excluded_count += 1
                    continue

                # Get last active information for this user
                last_active_data = get_user_last_active(org_id, api_key, account_id)

                if not last_active_data or not last_active_data.get("data"):
                    errors += 1
                    continue

                # Find the product we're interested in
                product_access = last_active_data.get("data", {}).get(
                    "product_access", []
                )

                confluence_last_active = None
                for product in product_access:
                    if product.get("key") == product_key:
                        # Use timestamp if available, otherwise fall back to date string
                        last_active_str = product.get(
                            "last_active_timestamp"
                        ) or product.get("last_active")
                        confluence_last_active = parse_timestamp(last_active_str)
                        break

                if not confluence_last_active:
                    # User has never logged into Confluence
                    no_login_data.append(
                        {
                            "accountId": account_id,
                            "displayName": display_name,
                            "email": email,
                        }
                    )
                    continue

                # Check if user is inactive
                if confluence_last_active < cutoff_date:
                    days_inactive = (
                        datetime.now(timezone.utc) - confluence_last_active
                    ).days
                    inactive_users.append(
                        {
                            "accountId": account_id,
                            "displayName": display_name,
                            "email": email,
                            "lastActive": confluence_last_active.strftime("%Y-%m-%d"),
                            "daysInactive": days_inactive,
                        }
                    )
                else:
                    active_users.append(
                        {
                            "accountId": account_id,
                            "displayName": display_name,
                            "email": email,
                            "lastActive": confluence_last_active.strftime("%Y-%m-%d"),
                        }
                    )

        # Display results
        click.echo("\n" + "=" * 80)
        click.echo("RESULTS")
        click.echo("=" * 80 + "\n")

        click.echo(f"Total users processed: {len(users)}")
        click.echo(f"Active users (within threshold): {len(active_users)}")
        click.echo(f"Inactive users (beyond threshold): {len(inactive_users)}")
        click.echo(f"Users with no {product_key} login data: {len(no_login_data)}")
        click.echo(f"Already suspended/inactive: {suspended_already}")
        click.echo(f"Excluded users: {excluded_count}")
        click.echo(f"Errors: {errors}")
        click.echo("\n")

        if inactive_users:
            click.echo("INACTIVE USERS TO SUSPEND:")
            click.echo("-" * 80)
            for user in sorted(
                inactive_users, key=lambda x: x["daysInactive"], reverse=True
            ):
                click.echo(
                    f"  • {user['displayName']} ({user['email']}) - "
                    f"Last active: {user['lastActive']} ({user['daysInactive']} days ago)"
                )

            if not dry_run:
                click.echo("\n" + "=" * 80)
                click.echo("SUSPENDING USERS...")
                click.echo("=" * 80 + "\n")

                suspended = 0
                failed = 0

                for user in inactive_users:
                    click.echo(
                        f"Suspending {user['displayName']} ({user['email']})...",
                        nl=False,
                    )

                    if suspend_user(org_id, api_key, directory_id, user["accountId"]):
                        click.echo(" ✓ SUCCESS")
                        suspended += 1
                    else:
                        click.echo(" ✗ FAILED")
                        failed += 1

                click.echo(
                    f"\nSuspension complete: {suspended} succeeded, {failed} failed"
                )
        else:
            click.echo("No inactive users found to suspend.")

        if no_login_data:
            click.echo("\n" + "-" * 80)
            click.echo(
                f"USERS WITH NO {product_key.upper()} LOGIN DATA (may be service accounts or never logged in):"
            )
            click.echo("-" * 80)
            for user in no_login_data[:10]:  # Show first 10
                click.echo(f"  • {user['displayName']} ({user['email']})")
            if len(no_login_data) > 10:
                click.echo(f"  ... and {len(no_login_data) - 10} more")

        click.echo("\n" + "=" * 80)

    except requests.exceptions.RequestException as e:
        click.echo(f"\n✗ Error communicating with Atlassian API: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"\n✗ Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
