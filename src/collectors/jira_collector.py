"""Jira data collector."""

import logging
from datetime import datetime
from typing import List, Dict, Any

from auth import JiraAuthManager


class JiraCollector:
    """Collects issue data from Jira API."""
    
    def __init__(self, config: dict):
        """Initialize Jira collector.
        
        Args:
            config: Jira configuration from config.yaml
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.auth_manager = JiraAuthManager()
        self.jira = self.auth_manager.get_jira_client()
        
        self.projects = config.get("projects", [])
        self.include_epics = config.get("include_epics", True)
        self.track_sprints = config.get("track_sprints", True)
        self.custom_jql = config.get("custom_jql", "")
        self.issue_types = config.get("issue_types", ["Story", "Task", "Bug", "Epic"])
        self.include_comments = config.get("include_comments", True)
    
    def _build_jql(self, start_date: datetime, end_date: datetime) -> str:
        """Build JQL query for issues.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            JQL query string
        """
        jql_parts = []
        
        # Projects
        if self.projects:
            project_query = ", ".join(self.projects)
            jql_parts.append(f"project in ({project_query})")
        
        # Date range (issues updated in the period)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        jql_parts.append(f"updated >= '{start_str}' AND updated <= '{end_str}'")
        
        # Issue types
        if self.issue_types:
            types_query = ", ".join([f'"{t}"' for t in self.issue_types])
            jql_parts.append(f"issuetype in ({types_query})")
        
        # Custom JQL
        if self.custom_jql:
            jql_parts.append(f"({self.custom_jql})")
        
        # Order by updated date
        jql = " AND ".join(jql_parts) + " ORDER BY updated DESC"
        
        return jql
    
    def _extract_issue_data(self, issue) -> Dict[str, Any]:
        """Extract relevant data from a Jira issue.
        
        Args:
            issue: Jira issue object
            
        Returns:
            Dictionary with issue data
        """
        fields = issue.fields
        
        # Get status changes from changelog
        status_changes = []
        try:
            changelog = self.jira.issue(issue.key, expand='changelog').changelog
            for history in changelog.histories:
                for item in history.items:
                    if item.field == 'status':
                        status_changes.append({
                            'date': history.created,
                            'from': item.fromString,
                            'to': item.toString,
                            'author': history.author.displayName
                        })
        except Exception as e:
            self.logger.debug(f"Could not get changelog for {issue.key}: {str(e)}")
        
        # Get comments if configured
        comments = []
        if self.include_comments and hasattr(fields, 'comment'):
            for comment in fields.comment.comments[-5:]:  # Last 5 comments
                comments.append({
                    'author': comment.author.displayName,
                    'body': comment.body[:500],  # Limit comment length
                    'created': comment.created
                })
        
        # Get epic information
        epic_name = None
        epic_key = None
        try:
            if hasattr(fields, 'parent') and fields.parent:
                epic_key = fields.parent.key
                epic_name = fields.parent.fields.summary
        except:
            pass
        
        return {
            'key': issue.key,
            'summary': fields.summary,
            'description': fields.description[:1000] if fields.description else "",
            'status': fields.status.name,
            'issue_type': fields.issuetype.name,
            'priority': fields.priority.name if hasattr(fields, 'priority') and fields.priority else "None",
            'assignee': fields.assignee.displayName if fields.assignee else "Unassigned",
            'reporter': fields.reporter.displayName if fields.reporter else "Unknown",
            'created': fields.created,
            'updated': fields.updated,
            'resolution': fields.resolution.name if fields.resolution else None,
            'labels': fields.labels if hasattr(fields, 'labels') else [],
            'epic_key': epic_key,
            'epic_name': epic_name,
            'status_changes': status_changes,
            'comments': comments,
            'url': f"{self.auth_manager.jira_url}/browse/{issue.key}"
        }
    
    def _get_sprint_info(self) -> List[Dict[str, Any]]:
        """Get active sprint information.
        
        Returns:
            List of sprint data dictionaries
        """
        if not self.track_sprints:
            return []
        
        sprints = []
        try:
            # This requires Jira Software (Agile) API
            boards = self.jira.boards()
            for board in boards:
                try:
                    active_sprints = self.jira.sprints(board.id, state='active')
                    for sprint in active_sprints:
                        sprints.append({
                            'id': sprint.id,
                            'name': sprint.name,
                            'state': sprint.state,
                            'board': board.name
                        })
                except:
                    continue
        except Exception as e:
            self.logger.debug(f"Could not get sprint info: {str(e)}")
        
        return sprints
    
    def collect(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Collect Jira issues for the date range.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            List of issue dictionaries
        """
        self.logger.info("Starting Jira collection")
        
        try:
            # Build JQL query
            jql = self._build_jql(start_date, end_date)
            self.logger.debug(f"JQL query: {jql}")
            
            # Search for issues
            issues = self.jira.search_issues(
                jql,
                maxResults=200,  # Adjust as needed
                fields='summary,description,status,issuetype,priority,assignee,reporter,created,updated,resolution,labels,parent,comment'
            )
            
            self.logger.info(f"Found {len(issues)} issues")
            
            # Extract data from each issue
            issue_data = []
            for issue in issues:
                data = self._extract_issue_data(issue)
                if data:
                    issue_data.append(data)
            
            # Get sprint information
            if self.track_sprints:
                sprint_info = self._get_sprint_info()
                self.logger.info(f"Found {len(sprint_info)} active sprints")
                # Add sprint info as metadata
                if sprint_info:
                    issue_data.append({
                        'metadata_type': 'sprints',
                        'sprints': sprint_info
                    })
            
            self.logger.info(f"Successfully collected {len(issue_data)} Jira items")
            return issue_data
            
        except Exception as e:
            self.logger.error(f"Error collecting Jira data: {str(e)}")
            return []
