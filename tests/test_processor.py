"""Tests for data processor module."""

import unittest
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from processors.data_processor import DataProcessor


class TestDataProcessor(unittest.TestCase):
    """Test cases for DataProcessor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {'path': ':memory:'}  # Use in-memory SQLite for tests
        self.processor = DataProcessor(self.config)
    
    def test_initialization(self):
        """Test processor initialization."""
        self.assertIsNotNone(self.processor.db_path)
    
    def test_normalize_email_data(self):
        """Test email data normalization."""
        emails = [
            {
                'id': 'msg1',
                'from': 'test@example.com',
                'subject': 'Test',
                'labels': ['IMPORTANT']
            }
        ]
        
        result = self.processor._normalize_email_data(emails)
        
        self.assertEqual(result['total_count'], 1)
        self.assertIn('test@example.com', result['by_sender'])
        self.assertEqual(len(result['important']), 1)
    
    def test_normalize_jira_data(self):
        """Test Jira data normalization."""
        issues = [
            {
                'key': 'PROJ-123',
                'summary': 'Test issue',
                'status': 'Done',
                'issue_type': 'Task',
                'priority': 'High',
                'resolution': 'Fixed'
            }
        ]
        
        result = self.processor._normalize_jira_data(issues)
        
        self.assertEqual(result['total_count'], 1)
        self.assertIn('Done', result['by_status'])
        self.assertEqual(len(result['completed']), 1)
    
    def test_normalize_gdrive_data(self):
        """Test Google Drive data normalization."""
        files = [
            {
                'id': 'file1',
                'name': 'Test Doc',
                'mime_type': 'application/vnd.google-apps.document',
                'folder_name': 'Projects',
                'created_time': '2026-01-01T10:00:00Z',
                'modified_time': '2026-01-01T10:05:00Z'
            }
        ]
        
        result = self.processor._normalize_gdrive_data(files)
        
        self.assertEqual(result['total_count'], 1)
        self.assertIn('Projects', result['by_folder'])
        self.assertIn('Google Doc', result['by_type'])


if __name__ == '__main__':
    unittest.main()
