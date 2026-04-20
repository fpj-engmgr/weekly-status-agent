#!/usr/bin/env python
"""Test script to verify setup and authentication."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils import load_env_vars, setup_logging
import logging


def test_environment():
    """Test environment variables."""
    print("Testing environment variables...")
    load_env_vars()

    # Always required
    jira_url = os.getenv('JIRA_URL')
    if jira_url:
        print(f"  ✓ JIRA_URL: {jira_url[:30]}...")
    else:
        print(f"  ✗ JIRA_URL: Not set")
        return False

    # Check Jira authentication
    jira_email = os.getenv('JIRA_EMAIL')
    jira_token = os.getenv('JIRA_API_TOKEN')
    jira_user = os.getenv('JIRA_USERNAME')
    jira_pass = os.getenv('JIRA_PASSWORD')

    if jira_token:
        print(f"  ✓ JIRA_API_TOKEN: {'*' * 10} (Cloud authentication)")
        if jira_email:
            print(f"  ✓ JIRA_EMAIL: {jira_email}")
        else:
            print(f"  ⚠ JIRA_EMAIL: Not set (recommended with API token)")
    elif jira_user and jira_pass:
        print(f"  ✓ JIRA_USERNAME/PASSWORD: Set (Server/DC authentication)")
    else:
        print(f"  ✗ Jira authentication: Missing credentials")
        print("    Set JIRA_EMAIL + JIRA_API_TOKEN (Cloud) or JIRA_USERNAME + JIRA_PASSWORD (Server)")
        return False

    print("✓ Jira configuration complete\n")
    return True


def test_ai_provider():
    """Test AI provider configuration."""
    print("Testing AI provider configuration...")

    # Load config to check provider
    import yaml
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        provider = config.get('ai', {}).get('provider', 'anthropic')
        print(f"  ℹ Provider configured: {provider}")

        if provider in ['vertex', 'vertex-ai']:
            # Check GCP environment
            gcp_project = os.getenv('GCP_PROJECT_ID')
            gcp_region = os.getenv('GCP_REGION', 'us-central1')

            if gcp_project:
                print(f"  ✓ GCP_PROJECT_ID: {gcp_project}")
                print(f"  ✓ GCP_REGION: {gcp_region}")
            else:
                print(f"  ✗ GCP_PROJECT_ID: Not set (required for Vertex AI)")
                return False

            # Check for gcloud authentication
            try:
                import subprocess
                result = subprocess.run(
                    ['gcloud', 'auth', 'application-default', 'print-access-token'],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    print(f"  ✓ GCP authentication: Active")
                else:
                    print(f"  ⚠ GCP authentication: Run 'gcloud auth application-default login'")
            except (FileNotFoundError, subprocess.TimeoutExpired):
                print(f"  ⚠ gcloud CLI not found or not responding")

        elif provider == 'anthropic':
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                print(f"  ✓ ANTHROPIC_API_KEY: {'*' * 10}")
            else:
                print(f"  ✗ ANTHROPIC_API_KEY: Not set (required for direct Anthropic)")
                return False

        elif provider == 'openai':
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                print(f"  ✓ OPENAI_API_KEY: {'*' * 10}")
            else:
                print(f"  ✗ OPENAI_API_KEY: Not set (required for OpenAI)")
                return False
        else:
            print(f"  ✗ Unknown provider: {provider}")
            return False

        print("✓ AI provider configuration complete\n")
        return True

    except Exception as e:
        print(f"  ✗ Error checking AI config: {str(e)}\n")
        return False


def test_google_auth():
    """Test Google authentication."""
    print("Testing Google authentication...")
    
    try:
        from auth import GoogleAuthManager
        
        auth_manager = GoogleAuthManager()
        
        # Check if credentials file exists
        if not auth_manager.credentials_path.exists():
            print(f"  ✗ Google OAuth credentials not found at {auth_manager.credentials_path}")
            print("    Please download credentials from Google Cloud Console")
            return False
        
        print("  ✓ Google OAuth credentials file found")
        
        # Try to authenticate (will use existing token or prompt for login)
        print("  Authenticating (this may open a browser window)...")
        creds = auth_manager.authenticate()
        
        if creds and creds.valid:
            print("  ✓ Google authentication successful\n")
            return True
        else:
            print("  ✗ Google authentication failed\n")
            return False
            
    except Exception as e:
        print(f"  ✗ Error: {str(e)}\n")
        return False


def test_jira_auth():
    """Test Jira authentication and API v3 configuration."""
    print("Testing Jira authentication...")

    try:
        from auth import JiraAuthManager

        auth_manager = JiraAuthManager()

        # Test basic connection
        print(f"  ℹ Connecting to: {auth_manager.jira_url}")
        success = auth_manager.test_connection()

        if success:
            print("  ✓ Jira authentication successful")

            # Test API v3 availability
            try:
                client = auth_manager.get_jira_client()
                # Try to get server info to verify API version
                server_info = client.server_info()
                print(f"  ✓ Jira Server: {server_info.get('serverTitle', 'Unknown')}")
                print(f"  ✓ Version: {server_info.get('version', 'Unknown')}")

                # Check if using API v3
                if hasattr(client, '_options') and client._options.get('rest_api_version') == '3':
                    print(f"  ✓ Using API v3 (required for Jira Cloud)")
                elif 'atlassian.net' in auth_manager.jira_url:
                    print(f"  ℹ Jira Cloud detected, API v3 is configured")

            except Exception as e:
                print(f"  ⚠ Could not verify API version: {str(e)}")

            print()
            return True
        else:
            print("  ✗ Jira authentication failed")
            print("    Check JIRA_URL, JIRA_EMAIL, and JIRA_API_TOKEN in .env\n")
            return False

    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        if "401" in str(e):
            print("    Authentication failed - check your credentials")
        elif "404" in str(e) or "API" in str(e):
            print("    API endpoint issue - ensure API v3 is enabled")
        print()
        return False


def test_ai_connection():
    """Test AI provider connection."""
    print("Testing AI provider connection...")

    # Load config to check provider
    import yaml
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        provider = config.get('ai', {}).get('provider', 'anthropic')
        model = config.get('ai', {}).get('model', 'claude-3-5-sonnet-20241022')

        print(f"  ℹ Testing {provider} connection...")

        if provider in ['vertex', 'vertex-ai']:
            from anthropic import AnthropicVertex
            gcp_project = os.getenv('GCP_PROJECT_ID')
            gcp_region = os.getenv('GCP_REGION', 'us-central1')

            if not gcp_project:
                print(f"  ✗ GCP_PROJECT_ID not set\n")
                return False

            try:
                client = AnthropicVertex(
                    project_id=gcp_project,
                    region=gcp_region
                )
                print(f"  ✓ Vertex AI client initialized")
                print(f"  ℹ Project: {gcp_project}, Region: {gcp_region}")
                print(f"  ℹ Note: Full connection test requires API call (skipped)\n")
                return True
            except Exception as e:
                print(f"  ✗ Vertex AI initialization failed: {str(e)}\n")
                return False

        elif provider == 'anthropic':
            import anthropic
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                print(f"  ✗ ANTHROPIC_API_KEY not set\n")
                return False

            try:
                client = anthropic.Anthropic(api_key=api_key)
                print(f"  ✓ Anthropic client initialized")
                print(f"  ℹ Note: Full connection test requires API call (skipped)\n")
                return True
            except Exception as e:
                print(f"  ✗ Anthropic initialization failed: {str(e)}\n")
                return False

        elif provider == 'openai':
            import openai
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                print(f"  ✗ OPENAI_API_KEY not set\n")
                return False

            try:
                client = openai.OpenAI(api_key=api_key)
                print(f"  ✓ OpenAI client initialized")
                print(f"  ℹ Note: Full connection test requires API call (skipped)\n")
                return True
            except Exception as e:
                print(f"  ✗ OpenAI initialization failed: {str(e)}\n")
                return False

    except Exception as e:
        print(f"  ✗ Error: {str(e)}\n")
        return False


def test_config():
    """Test configuration file."""
    print("Testing configuration...")

    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')

    if not os.path.exists(config_path):
        print(f"  ✗ Configuration file not found at {config_path}")
        print("    Please copy config/config.example.yaml to config/config.yaml")
        return False

    print(f"  ✓ Configuration file found")

    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Check required sections
        required_sections = ['schedule', 'gmail', 'jira', 'gdrive', 'ai', 'output']
        missing_sections = [s for s in required_sections if s not in config]

        if missing_sections:
            print(f"  ⚠ Missing configuration sections: {', '.join(missing_sections)}")
            return False
        else:
            print("  ✓ All required configuration sections present")

        # Validate Jira configuration
        jira_config = config.get('jira', {})
        if not jira_config.get('projects') and not jira_config.get('custom_jql') and not jira_config.get('board_ids'):
            print(f"  ⚠ Jira: No projects, custom_jql, or board_ids configured")
            print(f"    This may collect too many issues or none at all")
        else:
            print(f"  ✓ Jira: Data sources configured")

        # Check new configurable limits
        if 'max_comments_per_issue' in jira_config:
            print(f"  ✓ Jira: Configurable data limits set")
            print(f"    - max_comments_per_issue: {jira_config['max_comments_per_issue']}")
            print(f"    - max_comment_length: {jira_config.get('max_comment_length', 500)}")
            print(f"    - max_description_length: {jira_config.get('max_description_length', 1000)}")

        # Validate AI configuration
        ai_config = config.get('ai', {})
        provider = ai_config.get('provider', 'anthropic')
        model = ai_config.get('model', 'unknown')
        print(f"  ✓ AI: Provider={provider}, Model={model}")

        # Check for Vertex AI model format
        if provider in ['vertex', 'vertex-ai']:
            if '@' not in model:
                print(f"  ⚠ AI: Vertex AI models should use '@' format (e.g., claude-3-5-sonnet@20241022)")
        elif provider == 'anthropic':
            if '@' in model:
                print(f"  ⚠ AI: Direct Anthropic models should use '-' format (e.g., claude-3-5-sonnet-20241022)")

        print()
        return len(missing_sections) == 0

    except yaml.YAMLError as e:
        print(f"  ✗ YAML syntax error: {str(e)}\n")
        return False
    except Exception as e:
        print(f"  ✗ Error reading config: {str(e)}\n")
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("Weekly Status Agent - Setup Test")
    print("=" * 70)
    print()

    results = {
        'Environment Variables': test_environment(),
        'AI Provider Config': test_ai_provider(),
        'Configuration File': test_config(),
        'Google Authentication': test_google_auth(),
        'Jira Authentication': test_jira_auth(),
        'AI Provider Connection': test_ai_connection()
    }

    print("=" * 70)
    print("Test Results Summary:")
    print("=" * 70)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:.<50} {status}")

    print()

    if all(results.values()):
        print("✓ All tests passed! The agent is ready to use.")
        print("\nNext steps:")
        print("  1. Run the agent: python src/main.py")
        print("  2. Or dry-run: python src/main.py --dry-run")
        print("  3. Or schedule: python src/main.py --daemon")
        return 0
    else:
        failed = [name for name, result in results.items() if not result]
        print(f"⚠ {len(failed)} test(s) failed: {', '.join(failed)}")
        print("\nPlease fix the issues above before running the agent.")
        print("For help, see README.md or CLAUDE.md")
        return 1


if __name__ == "__main__":
    sys.exit(main())
