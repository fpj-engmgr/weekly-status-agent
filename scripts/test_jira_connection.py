#!/usr/bin/env python3
"""
Test Jira connection and verify credentials are working.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env if present
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

try:
    from jira import JIRA
except ImportError:
    print("❌ Error: python-jira library not installed")
    print("\nInstall it with:")
    print("  pip install jira python-dotenv")
    sys.exit(1)


def test_connection():
    """Test Jira connection and display basic info."""

    print("="*80)
    print("JIRA CONNECTION TEST")
    print("="*80)
    print()

    # Get credentials
    jira_url = os.environ.get('JIRA_URL')
    jira_email = os.environ.get('JIRA_EMAIL')
    jira_token = os.environ.get('JIRA_API_TOKEN')

    # Validate credentials
    if not jira_url:
        print("❌ Error: JIRA_URL not set")
        print("Set it in .env file or environment")
        return False

    if not jira_email:
        print("❌ Error: JIRA_EMAIL not set")
        print("Set it in .env file or environment")
        return False

    if not jira_token:
        print("❌ Error: JIRA_API_TOKEN not set")
        print("Set it in .env file or environment")
        return False

    print(f"Connecting to: {jira_url}")
    print(f"Email: {jira_email}")
    print(f"Token: {'*' * 20}")
    print()

    # Try to connect
    try:
        jira = JIRA(server=jira_url, basic_auth=(jira_email, jira_token))
        print("✓ Successfully connected to Jira!")
        print()

        # Get current user info
        try:
            current_user = jira.current_user()
            print(f"Logged in as: {current_user}")
            print()
        except Exception as e:
            print(f"⚠️  Could not get current user: {e}")
            print()

        # Get accessible projects
        try:
            print("Fetching accessible projects...")
            projects = jira.projects()

            if projects:
                print(f"✓ Found {len(projects)} accessible project(s):")
                print()
                for proj in projects[:10]:  # Show first 10
                    print(f"  • {proj.key}: {proj.name}")

                if len(projects) > 10:
                    print(f"  ... and {len(projects) - 10} more")
                print()
            else:
                print("⚠️  No projects found. Check your permissions.")
                print()
        except Exception as e:
            print(f"❌ Error fetching projects: {e}")
            print()

        # Try a simple query
        try:
            print("Testing issue search...")

            # Search for recent issues (last 30 days)
            jql = f'updated >= -30d ORDER BY updated DESC'
            issues = jira.search_issues(jql, maxResults=5)

            if issues:
                print(f"✓ Found {len(issues)} recent issue(s):")
                print()
                for issue in issues:
                    print(f"  • {issue.key}: {issue.fields.summary[:60]}")
                    print(f"    Status: {issue.fields.status.name}")
                    print(f"    Updated: {issue.fields.updated}")
                    print()
            else:
                print("⚠️  No recent issues found.")
                print()
        except Exception as e:
            print(f"❌ Error searching issues: {e}")
            print()
            return False

        print("="*80)
        print("✓ CONNECTION TEST SUCCESSFUL!")
        print("="*80)
        print()
        print("You can now run:")
        print("  python scripts/extract_metrics.py")
        print()
        return True

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print()
        print("Common issues:")
        print("  1. Invalid API token - regenerate at:")
        print("     https://id.atlassian.com/manage-profile/security/api-tokens")
        print("  2. Wrong Jira URL - should be like:")
        print("     https://your-company.atlassian.net")
        print("  3. Wrong email - use the email associated with your Jira account")
        print()
        return False


if __name__ == '__main__':
    success = test_connection()
    sys.exit(0 if success else 1)
