"""Email notification sender using Gmail API."""

import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any

from auth import GoogleAuthManager
from utils import format_date_for_display


class EmailNotifier:
    """Sends email notifications using Gmail API."""

    def __init__(self):
        """Initialize email notifier."""
        self.logger = logging.getLogger(__name__)
        self.auth_manager = GoogleAuthManager()
        self.service = self.auth_manager.get_gmail_service()

    def send_report_notification(
        self,
        recipient: str,
        doc_url: str,
        analysis: Dict[str, Any],
        start_date: datetime,
        end_date: datetime
    ) -> bool:
        """Send email notification about generated report.

        Args:
            recipient: Email address to send to
            doc_url: URL of the generated Google Doc
            analysis: Analysis data from AI summarizer
            start_date: Report period start
            end_date: Report period end

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            subject = self._build_subject(start_date, end_date)
            body = self._build_body(doc_url, analysis, start_date, end_date)

            message = self._create_message(recipient, subject, body)
            self._send_message(message)

            self.logger.info(f"Email notification sent successfully to {recipient}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}", exc_info=True)
            return False

    def _build_subject(self, start_date: datetime, end_date: datetime) -> str:
        """Build email subject line.

        Args:
            start_date: Report period start
            end_date: Report period end

        Returns:
            Email subject string
        """
        start_str = format_date_for_display(start_date)
        end_str = format_date_for_display(end_date)
        return f"Weekly Status Report - {start_str} to {end_str}"

    def _build_body(
        self,
        doc_url: str,
        analysis: Dict[str, Any],
        start_date: datetime,
        end_date: datetime
    ) -> str:
        """Build HTML email body.

        Args:
            doc_url: URL of the generated report
            analysis: Analysis data from AI
            start_date: Report period start
            end_date: Report period end

        Returns:
            HTML email body
        """
        start_str = format_date_for_display(start_date)
        end_str = format_date_for_display(end_date)

        # Get summary data
        exec_summary = analysis.get('executive_summary', 'No summary available.')

        # Get metadata for counts
        metadata = analysis.get('metadata', {})
        data_summary = metadata.get('data_summary', {})

        email_count = data_summary.get('total_emails', 0)
        jira_count = data_summary.get('total_jira_issues', 0)
        gitlab_count = data_summary.get('total_gitlab_mrs', 0)
        drive_count = data_summary.get('total_drive_files', 0)

        # Get highlights
        email_highlights = analysis.get('email_highlights', {})
        action_items = email_highlights.get('action_items', [])

        project_progress = analysis.get('project_progress', {})
        completed = project_progress.get('completed', [])

        # Build HTML
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #4285f4;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        .header p {{
            margin: 5px 0 0 0;
            opacity: 0.9;
        }}
        .summary {{
            background-color: #f8f9fa;
            padding: 15px;
            border-left: 4px solid #4285f4;
            margin-bottom: 20px;
        }}
        .metrics {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 20px;
        }}
        .metric {{
            background-color: #e8f0fe;
            padding: 10px 15px;
            border-radius: 5px;
            flex: 1;
            min-width: 120px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #1967d2;
        }}
        .metric-label {{
            font-size: 12px;
            color: #5f6368;
            text-transform: uppercase;
        }}
        .section {{
            margin-bottom: 20px;
        }}
        .section h2 {{
            color: #1967d2;
            font-size: 18px;
            margin-bottom: 10px;
            border-bottom: 2px solid #e8f0fe;
            padding-bottom: 5px;
        }}
        .section ul {{
            margin: 0;
            padding-left: 20px;
        }}
        .section li {{
            margin-bottom: 5px;
        }}
        .cta {{
            background-color: #4285f4;
            color: white;
            padding: 15px 30px;
            text-decoration: none;
            border-radius: 5px;
            display: inline-block;
            margin: 20px 0;
            font-weight: bold;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e8eaed;
            font-size: 12px;
            color: #5f6368;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Weekly Status Report</h1>
        <p>{start_str} to {end_str}</p>
    </div>

    <div class="summary">
        <strong>Executive Summary:</strong><br>
        {exec_summary[:300]}{"..." if len(exec_summary) > 300 else ""}
    </div>

    <div class="metrics">
        <div class="metric">
            <div class="metric-value">{email_count}</div>
            <div class="metric-label">Emails</div>
        </div>
        <div class="metric">
            <div class="metric-value">{jira_count}</div>
            <div class="metric-label">Jira Issues</div>
        </div>
        <div class="metric">
            <div class="metric-value">{gitlab_count}</div>
            <div class="metric-label">GitLab MRs</div>
        </div>
        <div class="metric">
            <div class="metric-value">{drive_count}</div>
            <div class="metric-label">Drive Files</div>
        </div>
    </div>
"""

        # Add completed items if available
        if completed:
            html += """
    <div class="section">
        <h2>Key Completions</h2>
        <ul>
"""
            for item in completed[:5]:  # Top 5
                key = item.get('key', '')
                summary = item.get('summary', '')
                html += f"            <li><strong>{key}</strong>: {summary}</li>\n"

            html += """        </ul>
    </div>
"""

        # Add action items if available
        if action_items:
            html += """
    <div class="section">
        <h2>Action Items</h2>
        <ul>
"""
            for item in action_items[:5]:  # Top 5
                html += f"            <li>{item}</li>\n"

            html += """        </ul>
    </div>
"""

        # Add CTA and footer
        html += f"""
    <a href="{doc_url}" class="cta">View Full Report</a>

    <div class="footer">
        <p>This is an automated weekly status report generated by the Weekly Status Agent.</p>
        <p>Report generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
    </div>
</body>
</html>
"""

        return html

    def _create_message(self, to: str, subject: str, body: str) -> Dict:
        """Create email message in Gmail API format.

        Args:
            to: Recipient email address
            subject: Email subject
            body: HTML email body

        Returns:
            Message dictionary for Gmail API
        """
        message = MIMEMultipart('alternative')
        message['to'] = to
        message['subject'] = subject

        # Add HTML part
        html_part = MIMEText(body, 'html')
        message.attach(html_part)

        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

        return {'raw': raw_message}

    def _send_message(self, message: Dict) -> Dict:
        """Send email message using Gmail API.

        Args:
            message: Encoded message dictionary

        Returns:
            Sent message object from Gmail API
        """
        sent_message = self.service.users().messages().send(
            userId='me',
            body=message
        ).execute()

        self.logger.debug(f"Message sent, ID: {sent_message['id']}")
        return sent_message
