"""Google Drive data collector."""

import logging
from datetime import datetime
from typing import List, Dict, Any

from auth import GoogleAuthManager


class GDriveCollector:
    """Collects file activity data from Google Drive API."""
    
    def __init__(self, config: dict):
        """Initialize Google Drive collector.
        
        Args:
            config: Google Drive configuration from config.yaml
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.auth_manager = GoogleAuthManager()
        self.service = self.auth_manager.get_drive_service()
        
        self.folders = config.get("folders", [])
        self.file_types = config.get("file_types", [])
        self.include_shared_with_me = config.get("include_shared_with_me", True)
    
    def _build_query(self, start_date: datetime, end_date: datetime, folder_id: str = None) -> str:
        """Build Drive API search query.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            folder_id: Optional folder ID to search in
            
        Returns:
            Drive API query string
        """
        query_parts = []
        
        # Date range
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%S")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%S")
        query_parts.append(f"modifiedTime >= '{start_str}' and modifiedTime <= '{end_str}'")
        
        # Folder filter
        if folder_id:
            query_parts.append(f"'{folder_id}' in parents")
        
        # File types
        if self.file_types:
            type_queries = [f"mimeType = '{ft}'" for ft in self.file_types]
            query_parts.append(f"({' or '.join(type_queries)})")
        
        # Exclude trashed files
        query_parts.append("trashed = false")
        
        return " and ".join(query_parts)
    
    def _get_file_details(self, file_data: dict) -> Dict[str, Any]:
        """Extract relevant details from a Drive file.
        
        Args:
            file_data: Raw file data from Drive API
            
        Returns:
            Dictionary with file details
        """
        return {
            'id': file_data['id'],
            'name': file_data['name'],
            'mime_type': file_data['mimeType'],
            'web_view_link': file_data.get('webViewLink', ''),
            'created_time': file_data.get('createdTime'),
            'modified_time': file_data.get('modifiedTime'),
            'owners': [owner.get('displayName', '') for owner in file_data.get('owners', [])],
            'last_modifying_user': file_data.get('lastModifyingUser', {}).get('displayName', ''),
            'shared': file_data.get('shared', False),
            'size': int(file_data.get('size', 0)) if 'size' in file_data else 0,
            'version': file_data.get('version', ''),
            'folder_name': None  # Will be set by caller
        }
    
    def _collect_from_folder(self, folder_id: str, folder_name: str, 
                            start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Collect files from a specific folder.
        
        Args:
            folder_id: Google Drive folder ID
            folder_name: Human-readable folder name
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            List of file dictionaries
        """
        try:
            query = self._build_query(start_date, end_date, folder_id)
            
            files_data = []
            page_token = None
            
            while True:
                response = self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name, mimeType, webViewLink, createdTime, modifiedTime, owners, lastModifyingUser, shared, size, version)',
                    pageToken=page_token,
                    pageSize=100
                ).execute()
                
                files = response.get('files', [])
                for file in files:
                    file_details = self._get_file_details(file)
                    file_details['folder_name'] = folder_name
                    files_data.append(file_details)
                
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
            
            return files_data
            
        except Exception as e:
            self.logger.error(f"Error collecting from folder {folder_name}: {str(e)}")
            return []
    
    def _collect_shared_with_me(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Collect files shared with me.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            List of file dictionaries
        """
        try:
            query = self._build_query(start_date, end_date)
            query += " and sharedWithMe = true"
            
            files_data = []
            page_token = None
            
            while True:
                response = self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name, mimeType, webViewLink, createdTime, modifiedTime, owners, lastModifyingUser, shared, size, version)',
                    pageToken=page_token,
                    pageSize=100
                ).execute()
                
                files = response.get('files', [])
                for file in files:
                    file_details = self._get_file_details(file)
                    file_details['folder_name'] = 'Shared with me'
                    files_data.append(file_details)
                
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
            
            return files_data
            
        except Exception as e:
            self.logger.error(f"Error collecting shared files: {str(e)}")
            return []
    
    def collect(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Collect Google Drive file activity for the date range.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            List of file dictionaries
        """
        self.logger.info("Starting Google Drive collection")
        
        all_files = []
        
        # Collect from specified folders
        for folder in self.folders:
            folder_id = folder.get('id')
            folder_name = folder.get('name', 'Unknown')
            
            self.logger.info(f"Collecting from folder: {folder_name}")
            files = self._collect_from_folder(folder_id, folder_name, start_date, end_date)
            all_files.extend(files)
            self.logger.info(f"Found {len(files)} files in {folder_name}")
        
        # Collect shared files
        if self.include_shared_with_me:
            self.logger.info("Collecting shared files")
            shared_files = self._collect_shared_with_me(start_date, end_date)
            all_files.extend(shared_files)
            self.logger.info(f"Found {len(shared_files)} shared files")
        
        # Remove duplicates (same file in multiple collections)
        unique_files = {}
        for file in all_files:
            if file['id'] not in unique_files:
                unique_files[file['id']] = file
        
        result = list(unique_files.values())
        self.logger.info(f"Successfully collected {len(result)} unique files")
        
        return result
