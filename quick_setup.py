#!/usr/bin/env python3
"""
Quick interactive setup for Jira credentials.
"""

import os
import sys
from pathlib import Path

def quick_setup():
    """Interactive setup for Jira credentials."""

    print("="*80)
    print("JIRA QUICK SETUP")
    print("="*80)
    print()

    # Check if credentials already exist
    env_file = Path(__file__).parent / '.env'
    config_file = Path(__file__).parent / 'config' / 'config.yaml'

    # Get Jira URL
    print("Step 1: Jira URL")
    print("Examples:")
    print("  - https://issues.redhat.com")
    print("  - https://yourcompany.atlassian.net")
    print()

    jira_url = input("Enter your Jira URL: ").strip()
    if not jira_url:
        print("❌ Jira URL is required")
        return False

    # Ensure it starts with https://
    if not jira_url.startswith('http'):
        jira_url = 'https://' + jira_url

    print()

    # Get email
    print("Step 2: Jira Email")
    jira_email = input("Enter your Jira email: ").strip()
    if not jira_email:
        print("❌ Email is required")
        return False

    print()

    # Get API token
    print("Step 3: API Token")
    print("Get your token from: https://id.atlassian.com/manage-profile/security/api-tokens")
    print()
    jira_token = input("Paste your API token: ").strip()
    if not jira_token:
        print("❌ API token is required")
        return False

    print()

    # Get project key
    print("Step 4: Project Key")
    print("Example: AIPCC")
    print()
    project_key = input("Enter your Jira project key: ").strip().upper()
    if not project_key:
        print("⚠️  No project key provided, using 'PROJ' as default")
        project_key = "PROJ"

    print()

    # Create .env file
    print("Creating .env file...")
    with open(env_file, 'w') as f:
        f.write(f"""# Jira Configuration
JIRA_URL={jira_url}
JIRA_EMAIL={jira_email}
JIRA_API_TOKEN={jira_token}

# AI Provider (optional - for weekly report generation)
# ANTHROPIC_API_KEY=your-key-here
# OPENAI_API_KEY=your-key-here
""")

    os.chmod(env_file, 0o600)
    print(f"✓ Created .env at: {env_file}")
    print()

    # Create config.yaml
    print("Creating config.yaml...")
    example_config = Path(__file__).parent / 'config' / 'config.example.yaml'

    with open(example_config, 'r') as f:
        config_content = f.read()

    # Update projects line
    config_content = config_content.replace(
        'projects: ["PROJ", "DEV"]',
        f'projects: ["{project_key}"]'
    )

    with open(config_file, 'w') as f:
        f.write(config_content)

    print(f"✓ Created config.yaml at: {config_file}")
    print()

    print("="*80)
    print("✓ SETUP COMPLETE!")
    print("="*80)
    print()
    print("Next steps:")
    print("  1. Test connection:")
    print("     .venv/bin/python scripts/test_jira_connection.py")
    print()
    print("  2. Extract metrics:")
    print("     .venv/bin/python scripts/extract_metrics.py")
    print()

    return True


if __name__ == '__main__':
    try:
        success = quick_setup()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(1)
