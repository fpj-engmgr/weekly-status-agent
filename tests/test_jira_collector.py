"""Tests for JiraCollector pagination."""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from collectors.jira_collector import JiraCollector


_JIRA_ENV = {
    "JIRA_URL": "https://test.atlassian.net",
    "JIRA_EMAIL": "test@example.com",
    "JIRA_API_TOKEN": "test-token",
}


class TestJiraSearchPagination(unittest.TestCase):
    """Paginated Jira search behavior."""

    @patch.dict(os.environ, _JIRA_ENV, clear=True)
    @patch("collectors.jira_collector.JiraAuthManager")
    def test_single_page(self, mock_auth_cls):
        mock_jira = MagicMock()
        mock_auth = mock_auth_cls.return_value
        mock_auth.get_jira_client.return_value = mock_jira
        mock_auth.jira_url = "https://test.atlassian.net"

        mock_jira.search_issues.return_value = [Mock(key="A-1")]

        c = JiraCollector({})
        out = c._search_issues_paginated("project = FOO")

        self.assertEqual(len(out), 1)
        mock_jira.search_issues.assert_called_once()
        _, kwargs = mock_jira.search_issues.call_args
        self.assertEqual(kwargs["startAt"], 0)
        self.assertEqual(kwargs["maxResults"], 100)

    @patch.dict(os.environ, _JIRA_ENV, clear=True)
    @patch("collectors.jira_collector.JiraAuthManager")
    def test_multiple_pages(self, mock_auth_cls):
        mock_jira = MagicMock()
        mock_auth = mock_auth_cls.return_value
        mock_auth.get_jira_client.return_value = mock_jira
        mock_auth.jira_url = "https://test.atlassian.net"

        def side_effect(jql, startAt=0, maxResults=100, fields=None):
            if startAt == 0:
                return [Mock(key=f"K-{i}") for i in range(100)]
            if startAt == 100:
                return [Mock(key=f"K-{i}") for i in range(100, 135)]
            return []

        mock_jira.search_issues.side_effect = side_effect

        c = JiraCollector({"search_page_size": 100})
        out = c._search_issues_paginated("project = FOO")

        self.assertEqual(len(out), 135)
        self.assertEqual(mock_jira.search_issues.call_count, 2)

    @patch.dict(os.environ, _JIRA_ENV, clear=True)
    @patch("collectors.jira_collector.JiraAuthManager")
    def test_max_issues_truncates(self, mock_auth_cls):
        mock_jira = MagicMock()
        mock_auth = mock_auth_cls.return_value
        mock_auth.get_jira_client.return_value = mock_jira
        mock_auth.jira_url = "https://test.atlassian.net"

        def side_effect(jql, startAt=0, maxResults=100, fields=None):
            if startAt == 0:
                return [Mock(key=f"K-{i}") for i in range(100)]
            if startAt == 100:
                return [Mock(key=f"K-{i}") for i in range(100, 200)]
            return []

        mock_jira.search_issues.side_effect = side_effect

        c = JiraCollector({"search_page_size": 100, "max_issues": 120})
        out = c._search_issues_paginated("project = FOO")

        self.assertEqual(len(out), 120)
        self.assertEqual(mock_jira.search_issues.call_count, 2)
        second_call = mock_jira.search_issues.call_args_list[1]
        self.assertEqual(second_call.kwargs["maxResults"], 20)

    @patch.dict(os.environ, _JIRA_ENV, clear=True)
    @patch("collectors.jira_collector.JiraAuthManager")
    def test_search_page_size_clamped(self, mock_auth_cls):
        mock_jira = MagicMock()
        mock_auth = mock_auth_cls.return_value
        mock_auth.get_jira_client.return_value = mock_jira
        mock_auth.jira_url = "https://test.atlassian.net"
        mock_jira.search_issues.return_value = []

        c = JiraCollector({"search_page_size": 500})
        self.assertEqual(c.search_page_size, 100)


class TestJiraSprintBoards(unittest.TestCase):
    """Board-scoped sprint collection."""

    @patch.dict(os.environ, _JIRA_ENV, clear=True)
    @patch("jira.resources.Board")
    @patch("collectors.jira_collector.JiraAuthManager")
    def test_board_ids_queries_sprints_only(
        self, mock_auth_cls, mock_board_class
    ):
        mock_board_inst = MagicMock()
        mock_board_inst.name = "Engineering Scrum"
        mock_board_class.return_value = mock_board_inst

        mock_jira = MagicMock()
        mock_auth = mock_auth_cls.return_value
        mock_auth.get_jira_client.return_value = mock_jira
        mock_auth.jira_url = "https://test.atlassian.net"

        sprint = Mock(id=55, name="Sprint 12", state="active")
        mock_jira.sprints.return_value = [sprint]

        c = JiraCollector({"board_ids": [42]})
        out = c._get_sprint_info()

        mock_jira.boards.assert_not_called()
        mock_jira.sprints.assert_called_once_with(42, state="active")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["id"], 55)
        self.assertEqual(out[0]["board"], "Engineering Scrum")

    @patch.dict(os.environ, _JIRA_ENV, clear=True)
    @patch("collectors.jira_collector.JiraAuthManager")
    def test_no_board_ids_lists_all_boards(self, mock_auth_cls):
        mock_jira = MagicMock()
        mock_auth = mock_auth_cls.return_value
        mock_auth.get_jira_client.return_value = mock_jira
        mock_auth.jira_url = "https://test.atlassian.net"

        board = Mock()
        board.id = 9
        board.name = "All-hands board"
        mock_jira.boards.return_value = [board]
        mock_jira.sprints.return_value = [
            Mock(id=1, name="S1", state="active"),
        ]

        c = JiraCollector({})
        out = c._get_sprint_info()

        mock_jira.boards.assert_called_once_with(maxResults=False)
        mock_jira.sprints.assert_called_once_with(9, state="active")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["board"], "All-hands board")

    @patch.dict(os.environ, _JIRA_ENV, clear=True)
    @patch("collectors.jira_collector.JiraAuthManager")
    def test_track_sprints_disabled(self, mock_auth_cls):
        mock_jira = MagicMock()
        mock_auth = mock_auth_cls.return_value
        mock_auth.get_jira_client.return_value = mock_jira

        c = JiraCollector({"track_sprints": False, "board_ids": [1]})
        self.assertEqual(c._get_sprint_info(), [])
        mock_jira.sprints.assert_not_called()
        mock_jira.boards.assert_not_called()

    @patch.dict(os.environ, _JIRA_ENV, clear=True)
    @patch("collectors.jira_collector.JiraAuthManager")
    def test_board_ids_deduped(self, mock_auth_cls):
        mock_jira = MagicMock()
        mock_auth = mock_auth_cls.return_value
        mock_auth.get_jira_client.return_value = mock_jira
        mock_auth.jira_url = "https://test.atlassian.net"
        mock_jira.sprints.return_value = []

        with patch("jira.resources.Board") as mock_board_class:
            mock_board_class.return_value.name = "B"
            c = JiraCollector({"board_ids": [3, 3, 3]})
            _ = c._get_sprint_info()

        mock_jira.sprints.assert_called_once_with(3, state="active")


class TestBulkChangelog(unittest.TestCase):
    """Bulk changelog API (Jira Cloud)."""

    @patch.dict(os.environ, _JIRA_ENV, clear=True)
    @patch("collectors.jira_collector.JiraAuthManager")
    def test_bulk_fetch_parses_status_changes(self, mock_auth_cls):
        mock_jira = MagicMock()
        mock_jira._options = {"server": "https://test.atlassian.net"}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "issueChangeLogs": [
                {
                    "issueId": "10001",
                    "changeHistories": [
                        {
                            "created": "2026-01-05T12:00:00.000+0000",
                            "author": {"displayName": "Dev One"},
                            "items": [
                                {
                                    "field": "status",
                                    "fromString": "Open",
                                    "toString": "Done",
                                }
                            ],
                        }
                    ],
                }
            ],
            "nextPageToken": None,
        }
        mock_jira._session.post.return_value = mock_response
        mock_auth_cls.return_value.get_jira_client.return_value = mock_jira

        c = JiraCollector({})
        i1 = Mock(key="PRJ-1", id="10001")
        out = c._fetch_status_changes_bulk([i1])

        self.assertIsNotNone(out)
        self.assertEqual(len(out["PRJ-1"]), 1)
        self.assertEqual(out["PRJ-1"][0]["to"], "Done")
        self.assertEqual(out["PRJ-1"][0]["author"], "Dev One")
        mock_jira._session.post.assert_called_once()
        args, kwargs = mock_jira._session.post.call_args
        self.assertIn("/rest/api/3/changelog/bulkfetch", args[0])
        body = json.loads(kwargs["data"])
        self.assertEqual(body["issueIdsOrKeys"], ["PRJ-1"])
        self.assertEqual(body["fieldIds"], ["status"])

    @patch.dict(os.environ, _JIRA_ENV, clear=True)
    @patch("collectors.jira_collector.JiraAuthManager")
    def test_bulk_fetch_404_returns_none(self, mock_auth_cls):
        mock_jira = MagicMock()
        mock_jira._options = {"server": "https://test.atlassian.net"}
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_jira._session.post.return_value = mock_response
        mock_auth_cls.return_value.get_jira_client.return_value = mock_jira

        c = JiraCollector({})
        i1 = Mock(key="PRJ-1", id="10001")
        self.assertIsNone(c._fetch_status_changes_bulk([i1]))

    @patch.dict(os.environ, _JIRA_ENV, clear=True)
    @patch("collectors.jira_collector.JiraAuthManager")
    def test_extract_skips_expand_when_status_changes_passed(self, mock_auth_cls):
        mock_jira = MagicMock()
        mock_auth_cls.return_value.get_jira_client.return_value = mock_jira
        mock_auth_cls.return_value.jira_url = "https://test.atlassian.net"

        fields = Mock()
        fields.summary = "Hi"
        fields.description = None
        fields.status = Mock()
        fields.status.name = "Done"
        fields.issuetype = Mock()
        fields.issuetype.name = "Task"
        fields.priority = None
        fields.assignee = None
        fields.reporter = Mock(displayName="Rep")
        fields.created = "2026-01-01"
        fields.updated = "2026-01-02"
        fields.resolution = None
        fields.labels = []
        fields.parent = None
        issue = Mock(key="PRJ-9", fields=fields)

        c = JiraCollector({"include_comments": False})
        changes = [
            {
                "date": "2026-01-03T00:00:00.000+0000",
                "from": "Open",
                "to": "Done",
                "author": "A",
            }
        ]
        data = c._extract_issue_data(issue, status_changes=changes)

        mock_jira.issue.assert_not_called()
        self.assertEqual(len(data["status_changes"]), 1)
        self.assertEqual(data["status_changes"][0]["to"], "Done")


if __name__ == "__main__":
    unittest.main()
