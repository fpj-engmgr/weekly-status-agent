"""Jira data collector."""

import json
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from auth import JiraAuthManager

# Fields returned by issue search (changelog is loaded per issue in _extract_issue_data).
_SEARCH_FIELDS = (
    "summary,description,status,issuetype,priority,assignee,reporter,"
    "created,updated,resolution,labels,parent,comment"
)

# Jira Cloud/Server search API caps maxResults per request (typically 100).
_MAX_PAGE_SIZE = 100

# Jira Cloud bulk changelog API (POST /rest/api/3/changelog/bulkfetch).
_BULK_CHANGELOG_MAX_ISSUES_PER_REQUEST = 1000
_BULK_CHANGELOG_PAGE_MAX = 10000


class JiraCollector:
    """Collects issue data from Jira API."""
    
    def __init__(self, config: dict):
        """Initialize Jira collector.

        Args:
            config: Jira configuration from config.yaml

        Raises:
            ValueError: If config is None or empty
        """
        if not config:
            raise ValueError("Jira configuration is required")

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
        raw_page = config.get("search_page_size", _MAX_PAGE_SIZE)
        self.search_page_size = max(1, min(int(raw_page), _MAX_PAGE_SIZE))
        max_issues = config.get("max_issues")
        self.max_issues = int(max_issues) if max_issues is not None else None
        self.board_ids = self._parse_board_ids(config.get("board_ids"))
        self.bulk_changelog = config.get("bulk_changelog", True)
        raw_chunk = config.get("bulk_changelog_chunk_size", _BULK_CHANGELOG_MAX_ISSUES_PER_REQUEST)
        self.bulk_changelog_chunk_size = max(
            1,
            min(int(raw_chunk), _BULK_CHANGELOG_MAX_ISSUES_PER_REQUEST),
        )

        # Configurable limits for data extraction
        self.max_comments_per_issue = config.get("max_comments_per_issue", 5)
        self.max_comment_length = config.get("max_comment_length", 500)
        self.max_description_length = config.get("max_description_length", 1000)

        # Board name cache to avoid repeated API calls
        self._board_name_cache: Dict[int, str] = {}

        # Validate at least one data source is configured
        if not self.projects and not self.custom_jql and not self.board_ids:
            self.logger.warning(
                "No projects, custom_jql, or board_ids configured - "
                "may collect too many issues or fail to collect any"
            )

        # Log configuration summary for troubleshooting
        self.logger.debug(
            "JiraCollector initialized: projects=%s, issue_types=%s, "
            "board_ids=%s, max_issues=%s, bulk_changelog=%s, "
            "max_comments=%s, max_comment_length=%s, max_description_length=%s",
            self.projects,
            self.issue_types,
            self.board_ids,
            self.max_issues,
            self.bulk_changelog,
            self.max_comments_per_issue,
            self.max_comment_length,
            self.max_description_length,
        )
    
    def _parse_board_ids(self, raw: Any) -> List[int]:
        """Coerce config board_ids to a list of unique int IDs (order preserved)."""
        if not raw:
            return []
        out: List[int] = []
        seen: set[int] = set()
        for x in raw:
            try:
                bid = int(x)
            except (TypeError, ValueError):
                self.logger.warning("Ignoring invalid jira.board_ids entry: %r", x)
                continue
            if bid not in seen:
                seen.add(bid)
                out.append(bid)
        return out
    
    def _resolve_board_name(self, board_id: int, board: Any = None) -> str:
        """Human-readable board name; used for sprint metadata in reports."""
        # Check cache first
        if board_id in self._board_name_cache:
            return self._board_name_cache[board_id]

        # Try to get name from provided board object
        if board is not None and getattr(board, "name", None):
            name = board.name
            self._board_name_cache[board_id] = name
            return name

        # Fetch from API if not in cache
        try:
            # Use the official Jira client API to get board info
            board_obj = self.jira.board(board_id)
            name = getattr(board_obj, 'name', f"Board {board_id}")
            self._board_name_cache[board_id] = name
            return name
        except Exception as e:
            self.logger.debug("Could not resolve board name for board_id=%s: %s", board_id, e)
            name = f"Board {board_id}"
            self._board_name_cache[board_id] = name
            return name
    
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

        # Basic validation
        if len(jql) > 2000:
            self.logger.warning(
                "JQL query is very long (%d chars), may fail or be rejected by Jira server",
                len(jql)
            )

        return jql
    
    def _status_changes_from_expand_changelog(self, issue) -> List[Dict[str, Any]]:
        """Load status transitions via GET issue expand=changelog (legacy / Server)."""
        status_changes: List[Dict[str, Any]] = []
        try:
            changelog = self.jira.issue(issue.key, expand="changelog").changelog
            for history in changelog.histories:
                for item in history.items:
                    if item.field == "status":
                        status_changes.append(
                            {
                                "date": history.created,
                                "from": item.fromString,
                                "to": item.toString,
                                "author": history.author.displayName,
                            }
                        )
        except Exception as e:
            issue_type = getattr(getattr(issue, 'fields', None), 'issuetype', None)
            issue_type_name = getattr(issue_type, 'name', 'unknown') if issue_type else 'unknown'
            self.logger.debug(
                "Could not get changelog for issue %s (type: %s): %s",
                issue.key,
                issue_type_name,
                e,
                exc_info=True
            )
        return status_changes
    
    def _bulk_changelog_url(self) -> str:
        server = self.jira._options["server"].rstrip("/")
        return f"{server}/rest/api/3/changelog/bulkfetch"
    
    def _fetch_status_changes_bulk(
        self, issues: List[Any]
    ) -> Optional[Dict[str, List[Dict[str, Any]]]]:
        """Jira Cloud: fetch status changelog entries for many issues in few API calls."""
        if not issues:
            return {}
        
        id_to_key: Dict[str, str] = {}
        for issue in issues:
            iid = getattr(issue, "id", None)
            if iid is not None:
                id_to_key[str(iid)] = issue.key
        
        key_to_changes: Dict[str, List[Dict[str, Any]]] = {i.key: [] for i in issues}
        keys = [i.key for i in issues]
        url = self._bulk_changelog_url()
        chunk_size = self.bulk_changelog_chunk_size
        
        try:
            for start in range(0, len(keys), chunk_size):
                chunk = keys[start : start + chunk_size]
                next_token: Optional[str] = None
                while True:
                    payload: Dict[str, Any] = {
                        "issueIdsOrKeys": chunk,
                        "fieldIds": ["status"],
                        "maxResults": _BULK_CHANGELOG_PAGE_MAX,
                    }
                    if next_token:
                        payload["nextPageToken"] = next_token
                    r = self.jira._session.post(url, data=json.dumps(payload))
                    if r.status_code == 404:
                        return None
                    r.raise_for_status()
                    data = r.json()
                    for icl in data.get("issueChangeLogs") or []:
                        kid = icl.get("issueId")
                        key = id_to_key.get(str(kid)) if kid is not None else None
                        if not key:
                            continue
                        for hist in icl.get("changeHistories") or []:
                            author = (hist.get("author") or {}).get("displayName") or "Unknown"
                            created = hist.get("created")
                            for item in hist.get("items") or []:
                                if item.get("field") != "status" and item.get("fieldId") != "status":
                                    continue
                                key_to_changes[key].append(
                                    {
                                        "date": created,
                                        "from": item.get("fromString"),
                                        "to": item.get("toString"),
                                        "author": author,
                                    }
                                )
                    next_token = data.get("nextPageToken")
                    if not next_token:
                        break
            return key_to_changes
        except Exception as e:
            self.logger.debug(
                "Bulk changelog fetch failed, will fall back to per-issue fetching: %s",
                e,
                exc_info=True
            )
            return None
    
    def _extract_issue_data(
        self,
        issue,
        status_changes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Extract relevant data from a Jira issue.
        
        Args:
            issue: Jira issue object
            status_changes: If provided (e.g. from bulk changelog), skip per-issue fetch.
            
        Returns:
            Dictionary with issue data
        """
        fields = issue.fields
        
        if status_changes is None:
            status_changes = self._status_changes_from_expand_changelog(issue)
        
        # Get comments if configured
        comments = []
        if self.include_comments and hasattr(fields, 'comment'):
            for comment in fields.comment.comments[-self.max_comments_per_issue:]:
                comments.append({
                    'author': comment.author.displayName,
                    'body': comment.body[:self.max_comment_length],
                    'created': comment.created
                })
        
        # Get epic information
        epic_name = None
        epic_key = None
        try:
            if hasattr(fields, 'parent') and fields.parent:
                epic_key = fields.parent.key
                epic_name = fields.parent.fields.summary
        except (AttributeError, Exception) as e:
            self.logger.debug("Could not extract epic info for %s: %s", issue.key, e)

        # Construct robust issue URL
        base_url = self.auth_manager.jira_url.rstrip('/')
        issue_url = f"{base_url}/browse/{issue.key}"

        return {
            'key': issue.key,
            'summary': fields.summary,
            'description': fields.description[:self.max_description_length] if fields.description else "",
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
            'url': issue_url
        }
    
    def _get_sprint_info(self) -> List[Dict[str, Any]]:
        """Get active sprint information.
        
        When ``board_ids`` is set in config, only those boards are queried (fast).
        Otherwise all boards visible to the user are listed (``maxResults=False``
        so more than the default page of 50 is included).

        Returns:
            List of sprint data dictionaries
        """
        if not self.track_sprints:
            return []
        
        sprints: List[Dict[str, Any]] = []
        try:
            if self.board_ids:
                for bid in self.board_ids:
                    board_name = self._resolve_board_name(bid)
                    try:
                        active_sprints = self.jira.sprints(bid, state="active")
                        for sprint in active_sprints:
                            sprints.append({
                                "id": sprint.id,
                                "name": sprint.name,
                                "state": sprint.state,
                                "board": board_name,
                            })
                    except Exception as exc:
                        self.logger.debug(
                            "Could not get active sprints for board %s (%s): %s",
                            bid,
                            board_name,
                            exc,
                            exc_info=True
                        )
            else:
                boards = self.jira.boards(maxResults=False)
                for board in boards:
                    try:
                        active_sprints = self.jira.sprints(board.id, state="active")
                        for sprint in active_sprints:
                            sprints.append({
                                "id": sprint.id,
                                "name": sprint.name,
                                "state": sprint.state,
                                "board": board.name,
                            })
                    except Exception as exc:
                        board_name = getattr(board, "name", "unknown")
                        board_id = getattr(board, "id", "?")
                        self.logger.debug(
                            "Could not get active sprints for board %s (%s): %s",
                            board_id,
                            board_name,
                            exc,
                            exc_info=True
                        )
        except Exception as e:
            self.logger.debug("Could not get sprint info: %s", e, exc_info=True)

        return sprints
    
    def _search_issues_paginated(self, jql: str) -> List[Any]:
        """Run JQL search with pagination until all results are fetched or max_issues reached."""
        collected: List[Any] = []
        start_at = 0
        fields = _SEARCH_FIELDS

        while True:
            remaining = None
            if self.max_issues is not None:
                remaining = self.max_issues - len(collected)
                if remaining <= 0:
                    break

            page_limit = self.search_page_size
            if remaining is not None:
                page_limit = min(page_limit, remaining)

            # Use jql_search or search_issues
            # Note: jira 3.10+ recommends jql_search but search_issues still works
            batch = self.jira.search_issues(
                jql,
                startAt=start_at,
                maxResults=page_limit,
                fields=fields,
            )

            if not batch:
                break

            collected.extend(batch)
            self.logger.debug(
                "Jira search page: startAt=%s got=%s total_so_far=%s",
                start_at,
                len(batch),
                len(collected),
            )

            if self.max_issues is not None and len(collected) >= self.max_issues:
                collected = collected[: self.max_issues]
                break

            if len(batch) < page_limit:
                break

            start_at += len(batch)

        return collected
    
    def collect(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Collect Jira issues for the date range.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of issue dictionaries
        """
        start_time = time.time()
        self.logger.info("Starting Jira collection")

        try:
            # Build JQL query
            jql = self._build_jql(start_date, end_date)
            self.logger.debug(f"JQL query: {jql}")

            issues = self._search_issues_paginated(jql)

            self.logger.info(f"Found {len(issues)} issues")

            changes_by_key: Optional[Dict[str, List[Dict[str, Any]]]] = None
            if self.bulk_changelog and issues:
                changes_by_key = self._fetch_status_changes_bulk(issues)
                if changes_by_key is not None:
                    self.logger.debug("Using bulk changelog for %s issues", len(issues))

            # Process issues with progress tracking
            issue_data = []
            total = len(issues)
            for idx, issue in enumerate(issues, 1):
                # Log progress for large collections
                if total > 20 and (idx % 10 == 0 or idx == total):
                    self.logger.info(f"Processing issue {idx}/{total}")

                precomputed = (
                    changes_by_key.get(issue.key) if changes_by_key is not None else None
                )
                data = self._extract_issue_data(issue, status_changes=precomputed)
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

            # Log performance metrics
            elapsed = time.time() - start_time
            items_per_sec = len(issue_data) / elapsed if elapsed > 0 else 0
            self.logger.info(
                f"Successfully collected {len(issue_data)} items in {elapsed:.2f}s "
                f"({items_per_sec:.1f} items/sec)"
            )
            return issue_data

        except Exception as e:
            self.logger.error(f"Error collecting Jira data: {str(e)}", exc_info=True)
            return []
