"""Gmail data collector."""

import base64
import logging
from datetime import datetime
from typing import List, Dict, Any
from email.utils import parsedate_to_datetime

from auth import GoogleAuthManager


class GmailCollector:
    """Collects email data from Gmail API."""
    
    def __init__(self, config: dict):
        """Initialize Gmail collector.
        
        Args:
            config: Gmail configuration from config.yaml
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.auth_manager = GoogleAuthManager()
        self.service = self.auth_manager.get_gmail_service()
        
        self.labels = config.get("labels", [])
        self.exclude_senders = config.get("exclude_senders", [])
        self.include_senders = config.get("include_senders", [])
        self.max_emails = config.get("max_emails", 100)
    
    def _build_query(self, start_date: datetime, end_date: datetime) -> str:
        """Build Gmail search query.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Gmail search query string
        """
        query_parts = []
        
        # Date range
        start_str = start_date.strftime("%Y/%m/%d")
        end_str = end_date.strftime("%Y/%m/%d")
        query_parts.append(f"after:{start_str} before:{end_str}")
        
        # Labels
        if self.labels:
            label_query = " OR ".join([f"label:{label}" for label in self.labels])
            query_parts.append(f"({label_query})")
        
        # Include specific senders
        if self.include_senders:
            sender_query = " OR ".join([f"from:{sender}" for sender in self.include_senders])
            query_parts.append(f"({sender_query})")
        
        # Exclude senders
        for sender in self.exclude_senders:
            query_parts.append(f"-from:{sender}")
        
        # Exclude spam and trash
        query_parts.append("-in:spam -in:trash")
        
        return " ".join(query_parts)
    
    def _get_message_details(self, msg_id: str) -> Dict[str, Any]:
        """Get detailed information about a message.
        
        Args:
            msg_id: Gmail message ID
            
        Returns:
            Dictionary with message details
        """
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()
            
            headers = {h['name']: h['value'] for h in message['payload']['headers']}
            
            # Extract body
            body = ""
            if 'parts' in message['payload']:
                for part in message['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        if 'data' in part['body']:
                            body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                            break
            elif 'body' in message['payload'] and 'data' in message['payload']['body']:
                body = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
            
            # Parse date
            date_str = headers.get('Date', '')
            try:
                date = parsedate_to_datetime(date_str)
            except:
                date = datetime.now()
            
            return {
                'id': msg_id,
                'thread_id': message.get('threadId'),
                'subject': headers.get('Subject', '(No Subject)'),
                'from': headers.get('From', ''),
                'to': headers.get('To', ''),
                'date': date,
                'snippet': message.get('snippet', ''),
                'body': body[:1000] if body else message.get('snippet', ''),  # Limit body length
                'labels': [label for label in message.get('labelIds', []) if not label.startswith('Label_')]
            }
        except Exception as e:
            self.logger.error(f"Error getting message {msg_id}: {str(e)}")
            return None
    
    def collect(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Collect Gmail messages for the date range.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            List of email dictionaries
        """
        self.logger.info("Starting Gmail collection")
        
        try:
            # Build search query
            query = self._build_query(start_date, end_date)
            self.logger.debug(f"Gmail query: {query}")
            
            # Search for messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=self.max_emails
            ).execute()
            
            messages = results.get('messages', [])
            self.logger.info(f"Found {len(messages)} messages")
            
            # Get detailed information for each message
            email_data = []
            for msg in messages:
                details = self._get_message_details(msg['id'])
                if details:
                    email_data.append(details)
            
            self.logger.info(f"Successfully collected {len(email_data)} emails")
            return email_data
            
        except Exception as e:
            self.logger.error(f"Error collecting Gmail data: {str(e)}")
            return []
