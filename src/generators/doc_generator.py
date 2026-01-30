"""Google Docs report generator."""

import logging
from datetime import datetime
from typing import Dict, Any, List

from auth import GoogleAuthManager
from utils import format_date_for_display


class DocGenerator:
    """Generates formatted Google Docs reports."""
    
    def __init__(self, config: dict):
        """Initialize document generator.
        
        Args:
            config: Output configuration from config.yaml
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.auth_manager = GoogleAuthManager()
        self.docs_service = self.auth_manager.get_docs_service()
        self.drive_service = self.auth_manager.get_drive_service()
        
        self.drive_folder_id = config.get("drive_folder_id")
        self.share_with = config.get("share_with", [])
        self.title_format = config.get("title_format", "Weekly Status Report - {start_date} to {end_date}")
    
    def _create_title(self, start_date: datetime, end_date: datetime) -> str:
        """Create document title.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            
        Returns:
            Formatted title string
        """
        return self.title_format.format(
            start_date=format_date_for_display(start_date),
            end_date=format_date_for_display(end_date)
        )
    
    def _create_document(self, title: str) -> str:
        """Create a new Google Doc.
        
        Args:
            title: Document title
            
        Returns:
            Document ID
        """
        doc = self.docs_service.documents().create(body={'title': title}).execute()
        doc_id = doc['documentId']
        
        # Move to specified folder if configured
        if self.drive_folder_id:
            file = self.drive_service.files().get(
                fileId=doc_id,
                fields='parents'
            ).execute()
            
            previous_parents = ",".join(file.get('parents', []))
            self.drive_service.files().update(
                fileId=doc_id,
                addParents=self.drive_folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
        
        return doc_id
    
    def _build_document_content(self, analysis: Dict[str, Any], 
                                start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Build document content requests.
        
        Args:
            analysis: AI analysis results
            start_date: Report start date
            end_date: Report end date
            
        Returns:
            List of Google Docs API requests
        """
        requests = []
        index = 1  # Start after title
        
        # Helper to add text
        def add_text(text: str, style: str = None) -> int:
            nonlocal index
            requests.append({
                'insertText': {
                    'location': {'index': index},
                    'text': text
                }
            })
            text_len = len(text)
            
            if style:
                if style == 'heading1':
                    requests.append({
                        'updateParagraphStyle': {
                            'range': {'startIndex': index, 'endIndex': index + text_len},
                            'paragraphStyle': {'namedStyleType': 'HEADING_1'},
                            'fields': 'namedStyleType'
                        }
                    })
                elif style == 'heading2':
                    requests.append({
                        'updateParagraphStyle': {
                            'range': {'startIndex': index, 'endIndex': index + text_len},
                            'paragraphStyle': {'namedStyleType': 'HEADING_2'},
                            'fields': 'namedStyleType'
                        }
                    })
                elif style == 'heading3':
                    requests.append({
                        'updateParagraphStyle': {
                            'range': {'startIndex': index, 'endIndex': index + text_len},
                            'paragraphStyle': {'namedStyleType': 'HEADING_3'},
                            'fields': 'namedStyleType'
                        }
                    })
                elif style == 'bold':
                    requests.append({
                        'updateTextStyle': {
                            'range': {'startIndex': index, 'endIndex': index + text_len - 1},
                            'textStyle': {'bold': True},
                            'fields': 'bold'
                        }
                    })
            
            index += text_len
            return text_len
        
        # Report header
        add_text(f"Report Period: {format_date_for_display(start_date)} to {format_date_for_display(end_date)}\n\n", 'bold')
        
        # Executive Summary
        add_text("Executive Summary\n", 'heading1')
        exec_summary = analysis.get('executive_summary', 'No summary available.')
        add_text(f"{exec_summary}\n\n")
        
        # Email Highlights
        add_text("Email Highlights\n", 'heading1')
        email_highlights = analysis.get('email_highlights', {})
        
        # Themes
        themes = email_highlights.get('themes', [])
        if themes:
            add_text("Key Communication Themes\n", 'heading2')
            for theme in themes:
                add_text(f"• {theme.get('theme', 'Unknown')}: ", 'bold')
                add_text(f"{theme.get('description', '')}\n")
            add_text("\n")
        
        # Action Items from emails
        action_items = email_highlights.get('action_items', [])
        if action_items:
            add_text("Action Items from Emails\n", 'heading2')
            for item in action_items:
                add_text(f"• {item}\n")
            add_text("\n")
        
        # Critical messages
        critical = email_highlights.get('critical_messages', [])
        if critical:
            add_text("Critical Messages\n", 'heading2')
            for msg in critical:
                add_text(f"• {msg.get('subject', 'No subject')}\n")
                add_text(f"  From: {msg.get('from', 'Unknown')}\n")
                add_text(f"  Why: {msg.get('why_important', '')}\n")
            add_text("\n")
        
        # Project Progress
        add_text("Project Progress\n", 'heading1')
        project_progress = analysis.get('project_progress', {})
        
        # Completed work
        completed = project_progress.get('completed', [])
        if completed:
            add_text("Completed This Week\n", 'heading2')
            for item in completed:
                add_text(f"• [{item.get('key', '')}] {item.get('summary', '')}\n")
                if item.get('impact'):
                    add_text(f"  Impact: {item.get('impact')}\n")
            add_text("\n")
        
        # In Progress
        in_progress = project_progress.get('in_progress', [])
        if in_progress:
            add_text("Currently In Progress\n", 'heading2')
            for item in in_progress:
                add_text(f"• [{item.get('key', '')}] {item.get('summary', '')}\n")
                add_text(f"  Status: {item.get('status', 'Unknown')}\n")
            add_text("\n")
        
        # Blockers
        blockers = project_progress.get('blockers', [])
        if blockers:
            add_text("Blockers & Concerns\n", 'heading2')
            for blocker in blockers:
                add_text(f"• {blocker}\n")
            add_text("\n")
        
        # Sprint summary
        sprint_summary = project_progress.get('sprint_summary')
        if sprint_summary:
            add_text("Sprint Summary\n", 'heading2')
            add_text(f"{sprint_summary}\n\n")
        
        # Document Activity
        add_text("Document Activity\n", 'heading1')
        doc_activity = analysis.get('document_activity', {})
        
        # New documents
        new_docs = doc_activity.get('new_documents', [])
        if new_docs:
            add_text("New Documents\n", 'heading2')
            for doc in new_docs:
                add_text(f"• {doc.get('name', 'Unnamed')}")
                if doc.get('folder'):
                    add_text(f" ({doc.get('folder')})")
                add_text("\n")
                if doc.get('significance'):
                    add_text(f"  {doc.get('significance')}\n")
            add_text("\n")
        
        # Major updates
        major_updates = doc_activity.get('major_updates', [])
        if major_updates:
            add_text("Major Updates\n", 'heading2')
            for doc in major_updates:
                add_text(f"• {doc.get('name', 'Unnamed')}")
                if doc.get('modifier'):
                    add_text(f" (by {doc.get('modifier')})")
                add_text("\n")
                if doc.get('changes_description'):
                    add_text(f"  {doc.get('changes_description')}\n")
            add_text("\n")
        
        # Action Items & Next Steps
        add_text("Action Items & Next Steps\n", 'heading1')
        all_action_items = analysis.get('action_items', [])
        
        # Group by priority
        high_priority = [item for item in all_action_items if item.get('priority') == 'high']
        medium_priority = [item for item in all_action_items if item.get('priority') == 'medium']
        low_priority = [item for item in all_action_items if item.get('priority') == 'low']
        
        if high_priority:
            add_text("High Priority\n", 'heading2')
            for item in high_priority:
                add_text(f"• {item.get('item', '')}")
                if item.get('source'):
                    add_text(f" (from {item.get('source')})")
                add_text("\n")
            add_text("\n")
        
        if medium_priority:
            add_text("Medium Priority\n", 'heading2')
            for item in medium_priority:
                add_text(f"• {item.get('item', '')}")
                if item.get('source'):
                    add_text(f" (from {item.get('source')})")
                add_text("\n")
            add_text("\n")
        
        if low_priority:
            add_text("Low Priority\n", 'heading2')
            for item in low_priority:
                add_text(f"• {item.get('item', '')}")
                if item.get('source'):
                    add_text(f" (from {item.get('source')})")
                add_text("\n")
            add_text("\n")
        
        # Recommendations
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            add_text("Recommendations\n", 'heading2')
            for rec in recommendations:
                add_text(f"• {rec}\n")
            add_text("\n")
        
        # Footer with metadata
        add_text("\n---\n")
        metadata = analysis.get('metadata', {})
        add_text(f"Generated: {metadata.get('generated_at', 'Unknown')}\n")
        add_text(f"Model: {metadata.get('model', 'Unknown')}\n")
        
        return requests
    
    def _apply_document_formatting(self, doc_id: str, requests: List[Dict[str, Any]]):
        """Apply formatting requests to document.
        
        Args:
            doc_id: Document ID
            requests: List of formatting requests
        """
        if requests:
            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
    
    def _share_document(self, doc_id: str):
        """Share document with configured users.
        
        Args:
            doc_id: Document ID
        """
        for email in self.share_with:
            try:
                self.drive_service.permissions().create(
                    fileId=doc_id,
                    body={
                        'type': 'user',
                        'role': 'reader',
                        'emailAddress': email
                    },
                    sendNotificationEmail=True
                ).execute()
                self.logger.info(f"Shared document with {email}")
            except Exception as e:
                self.logger.error(f"Failed to share with {email}: {str(e)}")
    
    def create_report(self, analysis: Dict[str, Any], 
                     start_date: datetime, end_date: datetime) -> str:
        """Create a formatted Google Doc report.
        
        Args:
            analysis: AI analysis results
            start_date: Report start date
            end_date: Report end date
            
        Returns:
            URL to the created document
        """
        self.logger.info("Creating Google Doc report")
        
        try:
            # Create title
            title = self._create_title(start_date, end_date)
            
            # Create document
            doc_id = self._create_document(title)
            self.logger.info(f"Created document: {doc_id}")
            
            # Build content
            requests = self._build_document_content(analysis, start_date, end_date)
            
            # Apply formatting
            self._apply_document_formatting(doc_id, requests)
            self.logger.info("Applied document formatting")
            
            # Share document
            if self.share_with:
                self._share_document(doc_id)
            
            # Get document URL
            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
            
            self.logger.info(f"Report created successfully: {doc_url}")
            return doc_url
            
        except Exception as e:
            self.logger.error(f"Error creating report: {str(e)}")
            raise
