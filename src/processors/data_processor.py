"""Data processor for normalizing and deduplicating collected data."""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any


class DataProcessor:
    """Processes and normalizes data from multiple sources."""
    
    def __init__(self, config: dict):
        """Initialize data processor.
        
        Args:
            config: Database configuration from config.yaml
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Set up database
        db_path = config.get("path", "data/tracking.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for tracking processed items."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables for deduplication tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_emails (
                message_id TEXT PRIMARY KEY,
                processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_jira_issues (
                issue_key TEXT PRIMARY KEY,
                last_updated TIMESTAMP,
                processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_drive_files (
                file_id TEXT PRIMARY KEY,
                last_modified TIMESTAMP,
                processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_gitlab_mrs (
                project_id TEXT,
                mr_iid INTEGER,
                last_updated TIMESTAMP,
                processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (project_id, mr_iid)
            )
        ''')

        conn.commit()
        conn.close()
    
    def _is_email_processed(self, message_id: str) -> bool:
        """Check if email has been processed before.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            True if already processed, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT message_id FROM processed_emails WHERE message_id = ?',
            (message_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    
    def _mark_email_processed(self, message_id: str):
        """Mark email as processed.
        
        Args:
            message_id: Gmail message ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT OR IGNORE INTO processed_emails (message_id) VALUES (?)',
            (message_id,)
        )
        
        conn.commit()
        conn.close()

    def _is_gitlab_mr_processed(self, project_id: str, mr_iid: int, last_updated: str) -> bool:
        """Check if GitLab MR has been processed before or has been updated.

        Args:
            project_id: GitLab project ID
            mr_iid: MR number within project
            last_updated: MR last updated timestamp

        Returns:
            True if already processed and not updated, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            'SELECT last_updated FROM processed_gitlab_mrs WHERE project_id = ? AND mr_iid = ?',
            (str(project_id), mr_iid)
        )

        result = cursor.fetchone()
        conn.close()

        if result is None:
            return False

        # If MR was updated since last processing, treat as new
        return result[0] == last_updated

    def _mark_gitlab_mr_processed(self, project_id: str, mr_iid: int, last_updated: str):
        """Mark GitLab MR as processed.

        Args:
            project_id: GitLab project ID
            mr_iid: MR number within project
            last_updated: MR last updated timestamp
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            '''INSERT OR REPLACE INTO processed_gitlab_mrs
               (project_id, mr_iid, last_updated, processed_date)
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)''',
            (str(project_id), mr_iid, last_updated)
        )

        conn.commit()
        conn.close()

    def _normalize_email_data(self, emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Normalize and categorize email data.
        
        Args:
            emails: List of email dictionaries
            
        Returns:
            Normalized email data structure
        """
        # Filter out already processed emails
        new_emails = [
            email for email in emails
            if not self._is_email_processed(email['id'])
        ]
        
        # Mark as processed
        for email in new_emails:
            self._mark_email_processed(email['id'])
        
        # Categorize emails
        categorized = {
            'total_count': len(new_emails),
            'by_sender': {},
            'by_label': {},
            'important': [],
            'all_emails': new_emails
        }
        
        for email in new_emails:
            # Group by sender
            sender = email.get('from', 'Unknown')
            if sender not in categorized['by_sender']:
                categorized['by_sender'][sender] = []
            categorized['by_sender'][sender].append(email)
            
            # Group by label
            for label in email.get('labels', []):
                if label not in categorized['by_label']:
                    categorized['by_label'][label] = []
                categorized['by_label'][label].append(email)
            
            # Flag important emails (IMPORTANT label or in include_senders)
            if 'IMPORTANT' in email.get('labels', []):
                categorized['important'].append(email)
        
        return categorized
    
    def _normalize_jira_data(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Normalize and categorize Jira data.
        
        Args:
            issues: List of issue dictionaries
            
        Returns:
            Normalized Jira data structure
        """
        # Separate sprint metadata from issues
        sprint_info = []
        actual_issues = []
        
        for item in issues:
            if item.get('metadata_type') == 'sprints':
                sprint_info = item.get('sprints', [])
            else:
                actual_issues.append(item)
        
        # Categorize issues
        categorized = {
            'total_count': len(actual_issues),
            'by_status': {},
            'by_type': {},
            'by_priority': {},
            'by_epic': {},
            'status_changes': [],
            'completed': [],
            'in_progress': [],
            'sprints': sprint_info,
            'all_issues': actual_issues
        }
        
        for issue in actual_issues:
            # Group by status
            status = issue.get('status', 'Unknown')
            if status not in categorized['by_status']:
                categorized['by_status'][status] = []
            categorized['by_status'][status].append(issue)
            
            # Group by type
            issue_type = issue.get('issue_type', 'Unknown')
            if issue_type not in categorized['by_type']:
                categorized['by_type'][issue_type] = []
            categorized['by_type'][issue_type].append(issue)
            
            # Group by priority
            priority = issue.get('priority', 'None')
            if priority not in categorized['by_priority']:
                categorized['by_priority'][priority] = []
            categorized['by_priority'][priority].append(issue)
            
            # Group by epic
            epic_name = issue.get('epic_name')
            if epic_name:
                if epic_name not in categorized['by_epic']:
                    categorized['by_epic'][epic_name] = []
                categorized['by_epic'][epic_name].append(issue)
            
            # Track status changes
            if issue.get('status_changes'):
                categorized['status_changes'].extend([
                    {'issue': issue['key'], **change}
                    for change in issue['status_changes']
                ])
            
            # Flag completed and in-progress
            if issue.get('resolution'):
                categorized['completed'].append(issue)
            elif status.lower() in ['in progress', 'in development']:
                categorized['in_progress'].append(issue)
        
        return categorized
    
    def _normalize_gdrive_data(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Normalize and categorize Google Drive data.
        
        Args:
            files: List of file dictionaries
            
        Returns:
            Normalized Drive data structure
        """
        categorized = {
            'total_count': len(files),
            'by_folder': {},
            'by_type': {},
            'by_modifier': {},
            'newly_created': [],
            'recently_modified': [],
            'all_files': files
        }
        
        for file in files:
            # Group by folder
            folder = file.get('folder_name', 'Unknown')
            if folder not in categorized['by_folder']:
                categorized['by_folder'][folder] = []
            categorized['by_folder'][folder].append(file)
            
            # Group by MIME type
            mime_type = file.get('mime_type', 'Unknown')
            type_label = self._get_file_type_label(mime_type)
            if type_label not in categorized['by_type']:
                categorized['by_type'][type_label] = []
            categorized['by_type'][type_label].append(file)
            
            # Group by modifier
            modifier = file.get('last_modifying_user', 'Unknown')
            if modifier not in categorized['by_modifier']:
                categorized['by_modifier'][modifier] = []
            categorized['by_modifier'][modifier].append(file)
            
            # Check if newly created (created and modified times are close)
            created = file.get('created_time')
            modified = file.get('modified_time')
            if created and modified:
                created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                modified_dt = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                
                # If created within 1 hour of modified time, consider it new
                if (modified_dt - created_dt).total_seconds() < 3600:
                    categorized['newly_created'].append(file)
                else:
                    categorized['recently_modified'].append(file)
        
        return categorized

    def _normalize_gitlab_data(self, mrs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Normalize and categorize GitLab merge request data.

        Args:
            mrs: List of merge request dictionaries

        Returns:
            Normalized GitLab MR data structure
        """
        # Filter out already processed MRs (or those updated since last process)
        new_mrs = [
            mr for mr in mrs
            if not self._is_gitlab_mr_processed(
                mr['project_id'],
                mr['mr_iid'],
                mr['updated_at']
            )
        ]

        # Mark as processed
        for mr in new_mrs:
            self._mark_gitlab_mr_processed(
                mr['project_id'],
                mr['mr_iid'],
                mr['updated_at']
            )

        # Categorize MRs
        categorized = {
            'total_count': len(new_mrs),
            'by_state': {},
            'by_project': {},
            'by_author': {},
            'merged_this_period': [],
            'ready_for_review': [],
            'needs_approval': [],
            'stale_mrs': [],
            'all_mrs': new_mrs
        }

        for mr in new_mrs:
            # Group by state
            state = mr.get('state', 'unknown')
            if state not in categorized['by_state']:
                categorized['by_state'][state] = []
            categorized['by_state'][state].append(mr)

            # Group by project
            project = mr.get('project_name', 'Unknown')
            if project not in categorized['by_project']:
                categorized['by_project'][project] = []
            categorized['by_project'][project].append(mr)

            # Group by author
            author = mr.get('author', 'Unknown')
            if author not in categorized['by_author']:
                categorized['by_author'][author] = []
            categorized['by_author'][author].append(mr)

            # Merged this period
            if state == 'merged':
                categorized['merged_this_period'].append(mr)

            # Ready for review (open, not draft, has pipeline passing)
            if (state == 'opened' and
                not mr.get('draft', False) and
                mr.get('pipeline_status') in ['success', 'manual', None]):
                categorized['ready_for_review'].append(mr)

            # Needs approval (open, not approved)
            if state == 'opened' and not mr.get('approved', False):
                categorized['needs_approval'].append(mr)

            # Stale MRs (open for more than 14 days)
            age_days = mr.get('age_days')
            if age_days and age_days > 14:
                categorized['stale_mrs'].append(mr)

        return categorized

    def _get_file_type_label(self, mime_type: str) -> str:
        """Get human-readable label for MIME type.
        
        Args:
            mime_type: MIME type string
            
        Returns:
            Human-readable type label
        """
        type_map = {
            'application/vnd.google-apps.document': 'Google Doc',
            'application/vnd.google-apps.spreadsheet': 'Google Sheet',
            'application/vnd.google-apps.presentation': 'Google Slides',
            'application/pdf': 'PDF',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word Doc',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel Sheet',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'PowerPoint',
        }
        
        return type_map.get(mime_type, 'Other')
    
    def process(self, gmail_data: List[Dict[str, Any]],
                jira_data: List[Dict[str, Any]],
                gdrive_data: List[Dict[str, Any]],
                gitlab_data: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process and normalize all collected data.

        Args:
            gmail_data: Raw Gmail data
            jira_data: Raw Jira data
            gdrive_data: Raw Google Drive data
            gitlab_data: Raw GitLab MR data (optional)

        Returns:
            Normalized and structured data dictionary
        """
        self.logger.info("Processing collected data")

        # Handle optional GitLab data
        if gitlab_data is None:
            gitlab_data = []

        processed = {
            'gmail': self._normalize_email_data(gmail_data),
            'jira': self._normalize_jira_data(jira_data),
            'gdrive': self._normalize_gdrive_data(gdrive_data),
            'gitlab': self._normalize_gitlab_data(gitlab_data),
            'summary': {
                'total_emails': len(gmail_data),
                'total_jira_issues': len([i for i in jira_data if i.get('metadata_type') != 'sprints']),
                'total_drive_files': len(gdrive_data),
                'total_gitlab_mrs': len(gitlab_data)
            }
        }
        
        self.logger.info(f"Processing complete: {processed['summary']}")
        return processed
