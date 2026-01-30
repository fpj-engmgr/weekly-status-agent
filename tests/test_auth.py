"""Tests for authentication module."""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from auth import GoogleAuthManager, JiraAuthManager


class TestGoogleAuthManager(unittest.TestCase):
    """Test cases for GoogleAuthManager."""
    
    @patch.dict(os.environ, {}, clear=True)
    def test_initialization(self):
        """Test GoogleAuthManager initialization."""
        manager = GoogleAuthManager()
        self.assertIsNotNone(manager.creds_dir)
        self.assertEqual(manager.creds, None)
    
    @patch('auth.Path.exists')
    def test_credentials_path_check(self, mock_exists):
        """Test checking for credentials file."""
        mock_exists.return_value = False
        manager = GoogleAuthManager()
        
        with self.assertRaises(FileNotFoundError):
            manager.authenticate()


class TestJiraAuthManager(unittest.TestCase):
    """Test cases for JiraAuthManager."""
    
    @patch.dict(os.environ, {'JIRA_URL': 'https://test.atlassian.net', 
                              'JIRA_EMAIL': 'test@example.com',
                              'JIRA_API_TOKEN': 'test-token'})
    def test_initialization(self):
        """Test JiraAuthManager initialization."""
        manager = JiraAuthManager()
        self.assertEqual(manager.jira_url, 'https://test.atlassian.net')
        self.assertEqual(manager.jira_email, 'test@example.com')
    
    @patch.dict(os.environ, {'JIRA_URL': 'https://test.atlassian.net'}, clear=True)
    def test_missing_credentials(self):
        """Test error when credentials are missing."""
        with self.assertRaises(ValueError):
            JiraAuthManager()


if __name__ == '__main__':
    unittest.main()
