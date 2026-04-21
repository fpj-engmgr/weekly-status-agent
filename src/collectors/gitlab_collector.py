"""GitLab merge request collector."""

import logging
import os
from datetime import datetime
from typing import List, Dict, Any

import gitlab
from gitlab.exceptions import GitlabError


class GitLabCollector:
    """Collects merge request data from GitLab projects."""

    def __init__(self, config: dict):
        """Initialize GitLab collector.

        Args:
            config: GitLab configuration from config.yaml

        Raises:
            ValueError: If config is invalid or GitLab token not found
        """
        if not config:
            raise ValueError("GitLab configuration is required")

        self.config = config
        self.logger = logging.getLogger(__name__)

        # Get GitLab URL and token
        self.gitlab_url = os.getenv("GITLAB_URL", config.get("url", "https://gitlab.com"))
        self.token = os.getenv("GITLAB_TOKEN")

        if not self.token:
            raise ValueError(
                "GITLAB_TOKEN environment variable not set. "
                "Create a personal access token with 'read_api' and 'read_repository' scopes."
            )

        # Configuration
        self.projects = config.get("projects", [])
        self.project_prefixes = config.get("project_prefixes", [])
        self.states = config.get("states", ["opened", "merged"])
        self.include_drafts = config.get("include_drafts", False)
        self.include_pipelines = config.get("include_pipelines", True)
        self.include_approvals = config.get("include_approvals", True)
        self.lookback_days = config.get("lookback_days", 7)
        self.max_mrs_per_project = config.get("max_mrs_per_project", 50)
        self.labels = config.get("labels", [])
        self.authors = config.get("authors", [])

        # Data limits
        self.max_comments_per_mr = config.get("max_comments_per_mr", 5)
        self.max_comment_length = config.get("max_comment_length", 500)
        self.max_description_length = config.get("max_description_length", 1000)

        # Initialize GitLab client
        try:
            self.gl = gitlab.Gitlab(self.gitlab_url, private_token=self.token)
            self.gl.auth()
            self.logger.info(f"Connected to GitLab at {self.gitlab_url}")
        except GitlabError as e:
            raise ValueError(f"Failed to authenticate with GitLab: {e}")

        # Validate configuration
        if not self.projects and not self.project_prefixes:
            self.logger.warning(
                "No projects or project_prefixes configured - GitLab collector will not fetch any MRs"
            )

        # Log configuration
        self.logger.debug(
            "GitLabCollector initialized: projects=%s, project_prefixes=%s, states=%s, "
            "max_mrs_per_project=%s, include_drafts=%s",
            self.projects,
            self.project_prefixes,
            self.states,
            self.max_mrs_per_project,
            self.include_drafts,
        )

    def _resolve_projects_from_prefixes(self) -> List[str]:
        """Resolve project prefixes to actual project paths.

        Fetches all accessible projects and filters by configured prefixes.

        Returns:
            List of project paths matching the prefixes
        """
        if not self.project_prefixes:
            return []

        self.logger.info(f"Resolving projects from prefixes: {self.project_prefixes}")
        matched_projects = []

        try:
            # Fetch all projects the user is a member of
            all_projects = self.gl.projects.list(membership=True, get_all=True)

            for project in all_projects:
                project_path = project.path_with_namespace

                # Check if project matches any prefix
                for prefix in self.project_prefixes:
                    if project_path.startswith(prefix):
                        matched_projects.append(project_path)
                        break

            self.logger.info(
                f"Found {len(matched_projects)} projects matching prefixes: {self.project_prefixes}"
            )

            if matched_projects and self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(f"Matched projects: {matched_projects[:10]}")  # Show first 10

        except GitlabError as e:
            self.logger.error(f"Error fetching projects for prefix matching: {e}")

        return matched_projects

    def collect(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Collect merge requests for the date range.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of normalized merge request dictionaries
        """
        self.logger.info("Starting GitLab MR collection")

        # Combine explicit projects and prefix-matched projects
        all_project_paths = list(self.projects)  # Start with explicit projects

        # Add projects matching prefixes
        if self.project_prefixes:
            prefix_projects = self._resolve_projects_from_prefixes()
            # Avoid duplicates
            for proj in prefix_projects:
                if proj not in all_project_paths:
                    all_project_paths.append(proj)

        if not all_project_paths:
            self.logger.warning("No projects to collect from")
            return []

        self.logger.info(f"Collecting from {len(all_project_paths)} projects")

        all_mrs = []

        for project_path in all_project_paths:
            try:
                mrs = self._collect_project_mrs(project_path, start_date, end_date)
                all_mrs.extend(mrs)
                if mrs:  # Only log if we found MRs
                    self.logger.info(
                        f"Collected {len(mrs)} MRs from project {project_path}"
                    )
            except Exception as e:
                self.logger.error(
                    f"Error collecting MRs from project {project_path}: {e}",
                    exc_info=True
                )

        self.logger.info(f"Successfully collected {len(all_mrs)} MRs total from {len(all_project_paths)} projects")
        return all_mrs

    def _collect_project_mrs(
        self,
        project_path: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Collect MRs for a single project.

        Args:
            project_path: Project ID or namespace/project path
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of MR dictionaries for this project
        """
        # Get project
        try:
            project = self.gl.projects.get(project_path)
        except GitlabError as e:
            self.logger.error(f"Failed to get project {project_path}: {e}")
            return []

        # Build query parameters
        mrs_params = {
            'state': 'all',  # We'll filter by states after
            'updated_after': start_date.isoformat(),
            'updated_before': end_date.isoformat(),
            'order_by': 'updated_at',
            'sort': 'desc',
            'per_page': 100,
        }

        # Add label filter if configured
        if self.labels:
            mrs_params['labels'] = ','.join(self.labels)

        # Add author filter if configured
        if self.authors:
            # Note: GitLab API doesn't support multiple authors in one query
            # We'll fetch all and filter client-side
            pass

        # Fetch MRs with pagination
        collected_mrs = []

        try:
            mrs = project.mergerequests.list(**mrs_params, get_all=False)

            for mr in mrs:
                # Skip if we've hit the limit
                if len(collected_mrs) >= self.max_mrs_per_project:
                    break

                # Filter by state
                if mr.state not in self.states:
                    continue

                # Filter drafts if not included
                if not self.include_drafts and mr.work_in_progress:
                    continue

                # Filter by author if configured
                if self.authors and mr.author['username'] not in self.authors:
                    continue

                # Extract MR data
                mr_data = self._extract_mr_data(project, mr)
                collected_mrs.append(mr_data)

        except GitlabError as e:
            self.logger.error(f"Error fetching MRs for {project_path}: {e}")

        return collected_mrs

    def _extract_mr_data(self, project, mr) -> Dict[str, Any]:
        """Extract and normalize data from a merge request.

        Args:
            project: GitLab project object
            mr: GitLab merge request object

        Returns:
            Normalized MR dictionary
        """
        # Basic MR info
        description = ""
        if mr.description:
            description = str(mr.description)[:self.max_description_length]

        mr_data = {
            'project_id': project.id,
            'project_name': project.path_with_namespace,
            'mr_iid': mr.iid,
            'mr_id': mr.id,
            'title': mr.title,
            'description': description,
            'state': mr.state,
            'draft': mr.work_in_progress,
            'author': mr.author['name'],
            'author_username': mr.author['username'],
            'created_at': mr.created_at,
            'updated_at': mr.updated_at,
            'merged_at': mr.merged_at if hasattr(mr, 'merged_at') else None,
            'closed_at': mr.closed_at if hasattr(mr, 'closed_at') else None,
            'target_branch': mr.target_branch,
            'source_branch': mr.source_branch,
            'labels': mr.labels,
            'web_url': mr.web_url,
            'upvotes': mr.upvotes,
            'downvotes': mr.downvotes,
            'user_notes_count': mr.user_notes_count,
        }

        # Add merged_by if available
        if mr.state == 'merged' and hasattr(mr, 'merged_by') and mr.merged_by:
            mr_data['merged_by'] = mr.merged_by['name']
            mr_data['merged_by_username'] = mr.merged_by['username']
        else:
            mr_data['merged_by'] = None
            mr_data['merged_by_username'] = None

        # Add assignees
        assignees = []
        if hasattr(mr, 'assignees') and mr.assignees:
            assignees = [a['name'] for a in mr.assignees]
        elif hasattr(mr, 'assignee') and mr.assignee:
            assignees = [mr.assignee['name']]
        mr_data['assignees'] = assignees

        # Add reviewers
        reviewers = []
        if hasattr(mr, 'reviewers') and mr.reviewers:
            reviewers = [r['name'] for r in mr.reviewers]
        mr_data['reviewers'] = reviewers

        # Pipeline status
        if self.include_pipelines:
            pipeline_status = None
            if hasattr(mr, 'head_pipeline') and mr.head_pipeline:
                pipeline_status = mr.head_pipeline.get('status')
            mr_data['pipeline_status'] = pipeline_status

        # Approvals
        if self.include_approvals:
            approvals = []
            try:
                mr_approvals = mr.approvals.get()
                if hasattr(mr_approvals, 'approved_by') and mr_approvals.approved_by:
                    approvals = [
                        {
                            'user': a['user']['name'],
                            'username': a['user']['username']
                        }
                        for a in mr_approvals.approved_by
                    ]
                mr_data['approved'] = mr_approvals.approved if hasattr(mr_approvals, 'approved') else False
            except Exception as e:
                self.logger.debug(f"Could not fetch approvals for MR !{mr.iid}: {e}")
                mr_data['approved'] = False

            mr_data['approvals'] = approvals

        # Comments (recent discussions)
        comments = []
        try:
            discussions = mr.discussions.list(per_page=self.max_comments_per_mr, get_all=False)
            for discussion in discussions[:self.max_comments_per_mr]:
                # Get the first note in each discussion thread
                notes = discussion.attributes.get('notes', [])
                if notes:
                    note = notes[0]
                    body = str(note.get('body', ''))[:self.max_comment_length]
                    comments.append({
                        'author': note.get('author', {}).get('name', 'Unknown'),
                        'body': body,
                        'created_at': note.get('created_at'),
                    })
        except Exception as e:
            self.logger.debug(f"Could not fetch comments for MR !{mr.iid}: {e}")

        mr_data['comments'] = comments

        # Calculate age if still open
        if mr.state == 'opened':
            created = datetime.fromisoformat(mr.created_at.replace('Z', '+00:00'))
            age_days = (datetime.now(created.tzinfo) - created).days
            mr_data['age_days'] = age_days
        else:
            mr_data['age_days'] = None

        # Calculate time to merge if merged
        if mr.state == 'merged' and mr.merged_at:
            created = datetime.fromisoformat(mr.created_at.replace('Z', '+00:00'))
            merged = datetime.fromisoformat(mr.merged_at.replace('Z', '+00:00'))
            time_to_merge_hours = (merged - created).total_seconds() / 3600
            mr_data['time_to_merge_hours'] = round(time_to_merge_hours, 1)
        else:
            mr_data['time_to_merge_hours'] = None

        return mr_data
