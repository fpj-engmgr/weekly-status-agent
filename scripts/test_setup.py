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
    
    required_vars = ['JIRA_URL', 'ANTHROPIC_API_KEY']
    missing = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✓ {var}: {'*' * 10} (set)")
        else:
            print(f"  ✗ {var}: Not set")
            missing.append(var)
    
    if missing:
        print(f"\n⚠ Missing variables: {', '.join(missing)}")
        print("Please set these in your .env file")
        return False
    
    print("✓ All required environment variables are set\n")
    return True


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
    """Test Jira authentication."""
    print("Testing Jira authentication...")
    
    try:
        from auth import JiraAuthManager
        
        auth_manager = JiraAuthManager()
        success = auth_manager.test_connection()
        
        if success:
            print("  ✓ Jira authentication successful\n")
            return True
        else:
            print("  ✗ Jira authentication failed\n")
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
    
    print(f"  ✓ Configuration file found\n")
    
    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check required sections
        required_sections = ['schedule', 'gmail', 'jira', 'gdrive', 'ai', 'output']
        missing_sections = [s for s in required_sections if s not in config]
        
        if missing_sections:
            print(f"  ⚠ Missing configuration sections: {', '.join(missing_sections)}")
        else:
            print("  ✓ All required configuration sections present")
        
        print()
        return len(missing_sections) == 0
        
    except Exception as e:
        print(f"  ✗ Error reading config: {str(e)}\n")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Weekly Status Agent - Setup Test")
    print("=" * 60)
    print()
    
    results = {
        'Environment': test_environment(),
        'Configuration': test_config(),
        'Google Auth': test_google_auth(),
        'Jira Auth': test_jira_auth()
    }
    
    print("=" * 60)
    print("Test Results:")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    print()
    
    if all(results.values()):
        print("✓ All tests passed! The agent is ready to use.")
        return 0
    else:
        print("⚠ Some tests failed. Please fix the issues above before running the agent.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
