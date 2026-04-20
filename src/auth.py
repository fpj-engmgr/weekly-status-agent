"""Authentication management for Google APIs and Jira."""

import os
import pickle
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from utils import ensure_credentials_dir, get_env_var


# Google API Scopes
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/documents'
]


class GoogleAuthManager:
    """Manages Google OAuth 2.0 authentication."""
    
    def __init__(self):
        """Initialize the Google Auth Manager."""
        self.creds_dir = ensure_credentials_dir()
        self.token_path = self.creds_dir / "google_token.pickle"
        self.credentials_path = self.creds_dir / "google_oauth.json"
        self.creds: Optional[Credentials] = None
    
    def authenticate(self) -> Credentials:
        """Authenticate with Google APIs using OAuth 2.0.
        
        Returns:
            Google OAuth2 credentials
            
        Raises:
            FileNotFoundError: If credentials file is missing
        """
        # Load existing token if available
        if self.token_path.exists():
            with open(self.token_path, 'rb') as token:
                self.creds = pickle.load(token)
        
        # If there are no (valid) credentials available, let the user log in
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                print("Refreshing Google OAuth token...")
                self.creds.refresh(Request())
            else:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"Google OAuth credentials not found at {self.credentials_path}\n"
                        "Please download OAuth 2.0 credentials from Google Cloud Console:\n"
                        "1. Go to https://console.cloud.google.com/\n"
                        "2. Enable Gmail, Drive, and Docs APIs\n"
                        "3. Create OAuth 2.0 credentials (Desktop app)\n"
                        "4. Download and save as config/credentials/google_oauth.json"
                    )
                
                print("Starting Google OAuth flow...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), GOOGLE_SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(self.token_path, 'wb') as token:
                pickle.dump(self.creds, token)
            print("Google authentication successful")
        
        return self.creds
    
    def get_gmail_service(self):
        """Get authenticated Gmail API service.
        
        Returns:
            Gmail API service instance
        """
        if not self.creds:
            self.authenticate()
        return build('gmail', 'v1', credentials=self.creds)
    
    def get_drive_service(self):
        """Get authenticated Google Drive API service.
        
        Returns:
            Drive API service instance
        """
        if not self.creds:
            self.authenticate()
        return build('drive', 'v3', credentials=self.creds)
    
    def get_docs_service(self):
        """Get authenticated Google Docs API service.
        
        Returns:
            Docs API service instance
        """
        if not self.creds:
            self.authenticate()
        return build('docs', 'v1', credentials=self.creds)


class JiraAuthManager:
    """Manages Jira API authentication."""
    
    def __init__(self):
        """Initialize the Jira Auth Manager."""
        self.jira_url = get_env_var("JIRA_URL", required=True)
        self.jira_email = get_env_var("JIRA_EMAIL", required=False)
        self.jira_api_token = get_env_var("JIRA_API_TOKEN", required=False)
        self.jira_username = get_env_var("JIRA_USERNAME", required=False)
        self.jira_password = get_env_var("JIRA_PASSWORD", required=False)
        
        # Validate authentication method
        if not (self.jira_api_token or (self.jira_username and self.jira_password)):
            raise ValueError(
                "Jira authentication requires either:\n"
                "1. JIRA_EMAIL and JIRA_API_TOKEN (for Jira Cloud), or\n"
                "2. JIRA_USERNAME and JIRA_PASSWORD (for Jira Server/DC)\n"
                "Please set these in your .env file"
            )
    
    def get_jira_client(self):
        """Get authenticated Jira client.

        Returns:
            Jira client instance
        """
        from jira import JIRA

        # Configure options to use API v3 (required for Jira Cloud)
        options = {
            'server': self.jira_url,
            'rest_api_version': '3'  # Use API v3 instead of deprecated v2
        }

        # Use API token (Jira Cloud)
        if self.jira_api_token:
            return JIRA(
                options=options,
                basic_auth=(self.jira_email, self.jira_api_token)
            )
        # Use username/password (Jira Server/DC)
        else:
            # Server/DC might still use v2, so use default for backward compatibility
            return JIRA(
                server=self.jira_url,
                basic_auth=(self.jira_username, self.jira_password)
            )
    
    def test_connection(self) -> bool:
        """Test Jira connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            client = self.get_jira_client()
            # Try to get current user
            _ = client.current_user()
            print("Jira authentication successful")
            return True
        except Exception as e:
            print(f"Jira authentication failed: {str(e)}")
            return False


def setup_authentication() -> tuple[GoogleAuthManager, JiraAuthManager]:
    """Set up all authentication managers.
    
    Returns:
        Tuple of (GoogleAuthManager, JiraAuthManager)
    """
    print("Setting up authentication...")
    
    # Google authentication
    google_auth = GoogleAuthManager()
    google_auth.authenticate()
    
    # Jira authentication
    jira_auth = JiraAuthManager()
    jira_auth.test_connection()
    
    print("All authentication setup complete")
    return google_auth, jira_auth


if __name__ == "__main__":
    """Test authentication setup."""
    from utils import load_env_vars
    
    load_env_vars()
    setup_authentication()
