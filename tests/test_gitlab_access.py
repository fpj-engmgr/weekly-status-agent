#!/usr/bin/env python
"""Test GitLab API access and list available projects."""

import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from utils import load_env_vars

def test_gitlab_access():
    """Test basic GitLab API access."""

    print("=" * 70)
    print("GITLAB API ACCESS TEST")
    print("=" * 70)
    print()

    # Load environment
    load_env_vars()

    # Get GitLab config
    gitlab_url = os.getenv('GITLAB_URL', 'https://gitlab.com')
    gitlab_token = os.getenv('GITLAB_TOKEN')

    if not gitlab_token:
        print("❌ ERROR: GITLAB_TOKEN not found in .env file")
        print()
        print("To set up GitLab access:")
        print("1. Go to GitLab → Preferences → Access Tokens")
        print("   (or https://gitlab.com/-/profile/personal_access_tokens)")
        print("2. Click 'Add new token'")
        print("3. Token name: 'Weekly Status Agent'")
        print("4. Expiration: Choose a date (e.g., 1 year)")
        print("5. Select scopes:")
        print("   - read_api (to read project data)")
        print("   - read_repository (to read MR details)")
        print("6. Click 'Create personal access token'")
        print("7. Copy the token (starts with glpat-)")
        print("8. Add to .env file:")
        print("   GITLAB_TOKEN=glpat-your-token-here")
        print()
        return

    # Try to import python-gitlab
    try:
        import gitlab
        from gitlab.exceptions import GitlabError
    except ImportError:
        print("❌ ERROR: python-gitlab not installed")
        print()
        print("Install it with:")
        print("  pip install python-gitlab")
        print()
        return

    # Initialize client
    print("Step 1: Connecting to GitLab...")
    print("-" * 70)
    print(f"URL: {gitlab_url}")
    print()

    try:
        gl = gitlab.Gitlab(gitlab_url, private_token=gitlab_token)
        gl.auth()

        # Get current user info
        current_user = gl.user
        print(f"✓ Connected to GitLab!")
        print(f"  User: {current_user.name} (@{current_user.username})")
        print(f"  Email: {current_user.email}")
        print()
    except GitlabError as e:
        print(f"❌ Authentication failed: {e}")
        print()
        print("Possible issues:")
        print("  - Token is invalid or expired")
        print("  - Token doesn't have required scopes (read_api, read_repository)")
        print("  - Wrong GitLab URL (check GITLAB_URL in .env)")
        print()
        return

    # List accessible projects
    print("Step 2: Listing accessible projects...")
    print("-" * 70)

    try:
        # Get projects the user is a member of
        projects = gl.projects.list(membership=True, per_page=50, get_all=False)

        print(f"✓ Found {len(projects)} projects you're a member of")
        print()

        if projects:
            print("Your projects (showing first 20):")
            for i, project in enumerate(projects[:20], 1):
                # Show project info
                visibility = project.visibility
                namespace = project.namespace.get('name', 'N/A')
                print(f"\n  {i}. {project.path_with_namespace}")
                print(f"     ID: {project.id}")
                print(f"     Visibility: {visibility}")
                print(f"     Namespace: {namespace}")

                # Count open MRs
                try:
                    open_mrs = project.mergerequests.list(state='opened', per_page=1)
                    mr_count = len(list(open_mrs))
                    if mr_count > 0:
                        print(f"     Open MRs: {mr_count}")
                except:
                    pass

            print()
        else:
            print("⚠️  No projects found. You may not be a member of any projects.")
            print()

    except GitlabError as e:
        print(f"❌ Error listing projects: {e}")
        print()
        return

    # If we have projects, test fetching MRs
    if projects:
        print("Step 3: Testing MR retrieval...")
        print("-" * 70)

        # Try to find a project that's not a mirror
        test_project = None
        for proj in projects[:10]:
            # Skip mirror projects
            if '/mirrors/' not in proj.path_with_namespace:
                test_project = proj
                break

        if not test_project:
            test_project = projects[0]

        print(f"Testing with project: {test_project.path_with_namespace}")
        print()

        # Fetch MRs from last 7 days
        seven_days_ago = datetime.now() - timedelta(days=7)

        try:
            mrs = test_project.mergerequests.list(
                state='all',
                updated_after=seven_days_ago.isoformat(),
                order_by='updated_at',
                sort='desc',
                per_page=5
            )

            print(f"✓ Retrieved {len(mrs)} MRs updated in last 7 days")

            if mrs:
                print()
                print("Sample MRs:")
                for i, mr in enumerate(mrs[:3], 1):
                    print(f"\n  MR {i}: !{mr.iid}")
                    print(f"    Title: {mr.title}")
                    print(f"    Author: {mr.author['name']}")
                    print(f"    State: {mr.state}")
                    print(f"    Created: {mr.created_at}")
                    print(f"    Updated: {mr.updated_at}")

                    if mr.state == 'merged' and hasattr(mr, 'merged_at'):
                        print(f"    Merged: {mr.merged_at}")
                        if hasattr(mr, 'merged_by') and mr.merged_by:
                            print(f"    Merged by: {mr.merged_by['name']}")

                    # Pipeline status
                    if hasattr(mr, 'head_pipeline') and mr.head_pipeline:
                        pipeline_status = mr.head_pipeline.get('status', 'N/A')
                        print(f"    Pipeline: {pipeline_status}")

                    # Approvals
                    try:
                        approvals = mr.approvals.get()
                        if hasattr(approvals, 'approved') and approvals.approved:
                            print(f"    Approved: Yes")
                    except:
                        pass

                    print(f"    URL: {mr.web_url}")
            else:
                print("  (No MRs updated in the last 7 days)")

            print()

        except GitlabError as e:
            print(f"❌ Error fetching MRs: {e}")
            print()
            return

    # Summary
    print("=" * 70)
    print("✅ GITLAB ACCESS TEST COMPLETE")
    print("=" * 70)
    print()

    if projects:
        print("Next steps:")
        print("1. Choose which projects to monitor")
        print("2. Add them to config/config.yaml under 'gitlab.projects'")
        print("3. Test the full collector implementation")
        print()

        # Show config example
        print("Example config.yaml section:")
        print("-" * 70)
        print("gitlab:")
        print("  projects:")
        for proj in projects[:5]:
            print(f"    - \"{proj.path_with_namespace}\"  # ID: {proj.id}")
        print("  states:")
        print("    - \"opened\"")
        print("    - \"merged\"")
        print("  lookback_days: 7")
        print("  max_mrs_per_project: 50")
        print()
    else:
        print("Next steps:")
        print("1. Make sure you're a member of GitLab projects")
        print("2. Re-run this script to verify access")
        print()

if __name__ == "__main__":
    test_gitlab_access()
