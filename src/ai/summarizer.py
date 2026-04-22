"""AI-powered data analysis and summarization."""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from utils import get_env_var, format_date_for_display


class AISummarizer:
    """Uses LLM to analyze and summarize collected data."""
    
    def __init__(self, config: dict):
        """Initialize AI summarizer.
        
        Args:
            config: AI configuration from config.yaml
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.provider = config.get("provider", "anthropic")
        self.model = config.get("model", "claude-3-5-sonnet-20241022")
        self.temperature = config.get("temperature", 0.3)
        self.max_tokens = config.get("max_tokens", 4000)
        
        # Initialize LLM client
        if self.provider == "anthropic":
            import anthropic
            api_key = get_env_var("ANTHROPIC_API_KEY", required=True)
            # Support custom base URL for enterprise/proxy setups
            base_url = get_env_var("ANTHROPIC_API_BASE_URL", required=False)
            if base_url:
                self.logger.info(f"Using custom Anthropic endpoint: {base_url}")
                self.client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
            else:
                self.client = anthropic.Anthropic(api_key=api_key)
        elif self.provider == "openai":
            import openai
            api_key = get_env_var("OPENAI_API_KEY", required=True)
            self.client = openai.OpenAI(api_key=api_key)
        elif self.provider == "vertex" or self.provider == "vertex-ai":
            # GCP Vertex AI - access Claude through Google Cloud
            from anthropic import AnthropicVertex
            self.gcp_project_id = get_env_var("GCP_PROJECT_ID", required=True)
            self.gcp_region = get_env_var("GCP_REGION", required=False) or "us-central1"
            self.logger.info(f"Using Vertex AI - Project: {self.gcp_project_id}, Region: {self.gcp_region}")
            self.client = AnthropicVertex(
                project_id=self.gcp_project_id,
                region=self.gcp_region
            )
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")
    
    def _build_analysis_prompt(self, data: Dict[str, Any], 
                               start_date: datetime, end_date: datetime) -> str:
        """Build the analysis prompt for the LLM.
        
        Args:
            data: Processed data from all sources
            start_date: Report start date
            end_date: Report end date
            
        Returns:
            Formatted prompt string
        """
        start_str = format_date_for_display(start_date)
        end_str = format_date_for_display(end_date)
        
        # Build context from data
        gmail_summary = data['gmail']
        jira_summary = data['jira']
        gdrive_summary = data['gdrive']
        gitlab_summary = data.get('gitlab', {'total_count': 0, 'all_mrs': []})

        prompt = f"""You are an executive assistant analyzing weekly work activity for a status report.

Report Period: {start_str} to {end_str}

DATA SUMMARY:
- Emails: {gmail_summary['total_count']} new emails
- Jira Issues: {jira_summary['total_count']} issues with activity
- GitLab MRs: {gitlab_summary['total_count']} merge requests with activity
- Google Drive: {gdrive_summary['total_count']} files modified

GMAIL DATA:
Total Emails: {gmail_summary['total_count']}
Important Emails: {len(gmail_summary['important'])}
Top Senders: {list(gmail_summary['by_sender'].keys())[:10]}

Email Details:
{self._format_emails_for_prompt(gmail_summary['all_emails'][:20])}

JIRA DATA:
Total Issues: {jira_summary['total_count']}
Completed Issues: {len(jira_summary['completed'])}
In Progress: {len(jira_summary['in_progress'])}
By Status: {dict([(k, len(v)) for k, v in jira_summary['by_status'].items()])}
By Priority: {dict([(k, len(v)) for k, v in jira_summary['by_priority'].items()])}

Issue Details:
{self._format_jira_for_prompt(jira_summary['all_issues'][:30])}

GITLAB MERGE REQUEST DATA:
Total MRs: {gitlab_summary['total_count']}
Merged This Period: {len(gitlab_summary.get('merged_this_period', []))}
Currently Open: {len(gitlab_summary.get('by_state', {}).get('opened', []))}
Ready for Review: {len(gitlab_summary.get('ready_for_review', []))}
Stale MRs (>14 days): {len(gitlab_summary.get('stale_mrs', []))}
By Project: {dict([(k, len(v)) for k, v in gitlab_summary.get('by_project', {}).items()])}

MR Details:
{self._format_gitlab_for_prompt(gitlab_summary.get('all_mrs', [])[:30])}

GOOGLE DRIVE DATA:
Total Files: {gdrive_summary['total_count']}
Newly Created: {len(gdrive_summary['newly_created'])}
Recently Modified: {len(gdrive_summary['recently_modified'])}
By Folder: {dict([(k, len(v)) for k, v in gdrive_summary['by_folder'].items()])}

File Details:
{self._format_gdrive_for_prompt(gdrive_summary['all_files'][:30])}

TASK:
Analyze this weekly work activity and generate a comprehensive status report with the following structure:

1. EXECUTIVE SUMMARY (2-3 paragraphs)
   - High-level overview of the week
   - Key accomplishments and progress
   - Notable themes or patterns

2. EMAIL HIGHLIGHTS
   - Important communications grouped by theme
   - Action items identified from emails
   - Critical messages requiring attention

3. PROJECT PROGRESS (from Jira)
   - Completed work by epic/project
   - Current in-progress items
   - Blockers or concerns identified
   - Sprint progress if applicable

4. CODE REVIEW ACTIVITY (from GitLab)
   - Merge requests merged this period
   - Open MRs ready for review
   - Stale MRs needing attention
   - Notable contributions or reviews

5. DOCUMENT ACTIVITY (from Drive)
   - Important new documents
   - Significant updates to existing docs
   - Collaboration patterns observed

6. ACTION ITEMS & NEXT STEPS
   - Pending action items
   - Follow-ups required
   - Recommended priorities for next week

FORMAT YOUR RESPONSE AS JSON:
{{
  "executive_summary": "...",
  "email_highlights": {{
    "themes": [
      {{"theme": "...", "description": "...", "emails": ["subject1", "subject2"]}}
    ],
    "action_items": ["action1", "action2"],
    "critical_messages": [
      {{"subject": "...", "from": "...", "why_important": "..."}}
    ]
  }},
  "project_progress": {{
    "completed": [
      {{"key": "...", "summary": "...", "impact": "..."}}
    ],
    "in_progress": [
      {{"key": "...", "summary": "...", "status": "..."}}
    ],
    "blockers": ["..."],
    "sprint_summary": "..."
  }},
  "gitlab_activity": {{
    "merged_count": 0,
    "open_count": 0,
    "highlights": [
      {{"mr_id": "!123", "title": "...", "project": "...", "significance": "..."}}
    ],
    "ready_for_review": [
      {{"mr_id": "!456", "title": "...", "project": "...", "age_days": 0}}
    ],
    "stale_mrs": [
      {{"mr_id": "!789", "title": "...", "project": "...", "days_open": 0, "concern": "..."}}
    ]
  }},
  "document_activity": {{
    "new_documents": [
      {{"name": "...", "folder": "...", "significance": "..."}}
    ],
    "major_updates": [
      {{"name": "...", "modifier": "...", "changes_description": "..."}}
    ]
  }},
  "action_items": [
    {{"item": "...", "priority": "high|medium|low", "source": "gmail|jira|gitlab|gdrive"}}
  ],
  "recommendations": ["..."]
}}

Ensure the analysis is insightful, focuses on meaningful work, and helps understand weekly progress and priorities.
"""
        
        return prompt
    
    def _format_emails_for_prompt(self, emails: list) -> str:
        """Format emails for inclusion in prompt.
        
        Args:
            emails: List of email dictionaries
            
        Returns:
            Formatted string
        """
        formatted = []
        for email in emails[:15]:  # Limit to avoid token overflow
            formatted.append(
                f"- From: {email.get('from', 'Unknown')}\n"
                f"  Subject: {email.get('subject', 'No subject')}\n"
                f"  Snippet: {email.get('snippet', '')[:150]}"
            )
        return "\n".join(formatted)
    
    def _format_jira_for_prompt(self, issues: list) -> str:
        """Format Jira issues for inclusion in prompt.
        
        Args:
            issues: List of issue dictionaries
            
        Returns:
            Formatted string
        """
        formatted = []
        for issue in issues[:20]:  # Limit to avoid token overflow
            formatted.append(
                f"- {issue.get('key')}: {issue.get('summary')}\n"
                f"  Status: {issue.get('status')} | Priority: {issue.get('priority')}\n"
                f"  Assignee: {issue.get('assignee')}"
            )
            if issue.get('epic_name'):
                formatted[-1] += f" | Epic: {issue.get('epic_name')}"
        return "\n".join(formatted)

    def _format_gitlab_for_prompt(self, mrs: list) -> str:
        """Format GitLab merge requests for inclusion in prompt.

        Args:
            mrs: List of MR dictionaries

        Returns:
            Formatted string
        """
        if not mrs:
            return "(No merge request activity)"

        formatted = []
        for mr in mrs[:20]:  # Limit to avoid token overflow
            mr_id = f"!{mr.get('mr_iid')}"
            title = mr.get('title', 'No title')
            state = mr.get('state', 'unknown')
            project = mr.get('project_name', 'Unknown').split('/')[-1]  # Show just last part of path

            line = f"- {mr_id}: {title}\n"
            line += f"  Project: {project} | State: {state}"

            if state == 'merged':
                merged_by = mr.get('merged_by', 'Unknown')
                line += f" | Merged by: {merged_by}"
                time_to_merge = mr.get('time_to_merge_hours')
                if time_to_merge:
                    line += f" | Time to merge: {time_to_merge:.1f}h"
            elif state == 'opened':
                age_days = mr.get('age_days', 0)
                line += f" | Age: {age_days} days"
                if mr.get('approved'):
                    line += " | Approved ✓"
                pipeline = mr.get('pipeline_status')
                if pipeline:
                    line += f" | Pipeline: {pipeline}"

            author = mr.get('author', 'Unknown')
            line += f"\n  Author: {author}"

            formatted.append(line)

        return "\n".join(formatted)

    def _format_gdrive_for_prompt(self, files: list) -> str:
        """Format Drive files for inclusion in prompt.
        
        Args:
            files: List of file dictionaries
            
        Returns:
            Formatted string
        """
        formatted = []
        for file in files[:20]:  # Limit to avoid token overflow
            formatted.append(
                f"- {file.get('name')}\n"
                f"  Folder: {file.get('folder_name')} | Modified by: {file.get('last_modifying_user')}"
            )
        return "\n".join(formatted)
    
    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Claude API.
        
        Args:
            prompt: Analysis prompt
            
        Returns:
            LLM response text
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.content[0].text
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API.
        
        Args:
            prompt: Analysis prompt
            
        Returns:
            LLM response text
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an executive assistant analyzing weekly work activity."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        return response.choices[0].message.content
    
    def analyze(self, data: Dict[str, Any], 
                start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Analyze collected data using LLM.
        
        Args:
            data: Processed data from all sources
            start_date: Report start date
            end_date: Report end date
            
        Returns:
            Structured analysis dictionary
        """
        self.logger.info(f"Analyzing data with {self.provider} ({self.model})")
        
        try:
            # Build prompt
            prompt = self._build_analysis_prompt(data, start_date, end_date)
            
            # Call LLM
            if self.provider == "anthropic" or self.provider == "vertex" or self.provider == "vertex-ai":
                response_text = self._call_anthropic(prompt)
            elif self.provider == "openai":
                response_text = self._call_openai(prompt)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
            
            # Parse JSON response
            # Extract JSON from markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            analysis = json.loads(response_text)
            
            # Add metadata
            analysis['metadata'] = {
                'generated_at': datetime.now().isoformat(),
                'model': self.model,
                'provider': self.provider,
                'report_period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'data_summary': data['summary']
            }
            
            self.logger.info("Analysis complete")
            return analysis
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
            self.logger.debug(f"Raw response (first 1000 chars): {response_text[:1000]}")
            self.logger.debug(f"Raw response (last 500 chars): {response_text[-500:]}")
            # Return a structure with empty sections so doc generator can still render
            return {
                'executive_summary': response_text[:500] + "\n\n(Note: AI response parsing failed. Showing truncated response. Increase max_tokens or check logs for details.)",
                'email_highlights': {'themes': [], 'action_items': [], 'critical_messages': []},
                'project_progress': {'completed': [], 'in_progress': [], 'blockers': [], 'sprint_summary': ''},
                'gitlab_activity': {'merged_count': 0, 'open_count': 0, 'highlights': [], 'ready_for_review': [], 'stale_mrs': []},
                'document_activity': {'new_documents': [], 'major_updates': []},
                'action_items': {'high_priority': [], 'medium_priority': [], 'low_priority': []},
                'error': f'Failed to parse structured response: {str(e)}',
                'raw_response': response_text
            }
        except Exception as e:
            self.logger.error(f"Error during analysis: {str(e)}")
            raise
