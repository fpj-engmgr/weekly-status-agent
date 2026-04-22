# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Weekly Status Report Agent - An automated Python tool that collects data from Gmail, Jira, GitLab, and Google Drive, analyzes it with AI, and generates weekly status reports as Google Docs.

## Essential Commands

### Development Setup
```bash
# Create virtual environment and install dependencies
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt

# Verify setup
python scripts/test_setup.py
```

### Running the Agent
```bash
# Manual execution
python src/main.py

# Dry run (collect and analyze without creating document)
python src/main.py --dry-run

# Custom config file
python src/main.py --config path/to/config.yaml

# Daemon mode (runs on schedule)
python src/main.py --daemon
```

### Testing
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_processor.py

# Test authentication setup
python src/auth.py
```

### Development Tools
```bash
# Code formatting
black src/

# Linting
flake8 src/
```

## Architecture

The agent follows a **5-stage pipeline architecture**:

### 1. Collectors (`src/collectors/`)
Fetch raw data from external APIs:
- **GmailCollector**: Fetches emails via Gmail API, filters by labels/senders
- **JiraCollector**: Queries Jira issues using JQL, tracks sprints/epics
- **GitLabCollector**: Collects merge requests with project prefix matching, approvals, pipeline status
- **GDriveCollector**: Monitors Google Drive folders for file changes

Each collector returns a list of normalized dictionaries with consistent structure.

### 2. Processor (`src/processors/data_processor.py`)
- **Deduplication**: Uses SQLite (`data/tracking.db`) to track processed items
- **Normalization**: Converts raw API responses to consistent internal format
- **Categorization**: Groups data by sender/status/type/folder for analysis

The processor prevents duplicate reporting by maintaining four tracking tables: `processed_emails`, `processed_jira_issues`, `processed_gitlab_mrs`, `processed_drive_files`.

### 3. AI Analyzer (`src/ai/summarizer.py`)
- Sends processed data to LLM (Claude or GPT-4)
- Generates executive summary, identifies themes, extracts action items
- Returns structured analysis with sections for the report

### 4. Generator (`src/generators/doc_generator.py`)
- Creates Google Doc using Docs API
- Formats report with structured sections
- Shares document with configured recipients
- Returns document URL

### 5. Scheduler (`src/scheduler/task_scheduler.py`)
- Runs agent on weekly schedule (configurable day/time)
- Uses `schedule` library for in-process scheduling
- Daemon mode keeps process running

### Authentication (`src/auth.py`)
Two authentication managers:
- **GoogleAuthManager**: OAuth 2.0 flow for Gmail/Drive/Docs APIs
  - Stores tokens in `config/credentials/google_token.pickle`
  - Auto-refreshes expired tokens
- **JiraAuthManager**: Basic auth (API token for Cloud, username/password for Server)

## Configuration

### File Structure
```
config/
├── config.yaml              # Main configuration (copy from config.example.yaml)
└── credentials/             # OAuth tokens and credentials (gitignored)
    ├── google_oauth.json    # OAuth 2.0 client credentials from GCP
    └── google_token.pickle  # Auto-generated access/refresh tokens
```

### Environment Variables (`.env`)
Required:
- `JIRA_URL`: Jira instance URL
- `JIRA_EMAIL` + `JIRA_API_TOKEN`: For Jira Cloud
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`: LLM provider

Optional:
- `GITLAB_URL`: GitLab instance URL (defaults to https://gitlab.com)
- `GITLAB_TOKEN`: GitLab personal access token with `read_api` scope

### Config Sections (`config/config.yaml`)
- **schedule**: Day/time for automatic report generation
- **gmail**: Labels to monitor, senders to include/exclude, lookback period
- **jira**: Projects to track, components to filter, custom JQL, sprint/epic settings, configurable data limits
  - `components`: Optional list of component names to filter (empty = all components)
  - `max_comments_per_issue`: Number of comments per issue (default: 5)
  - `max_comment_length`: Character limit per comment (default: 500)
  - `max_description_length`: Character limit for issue descriptions (default: 1000)
- **gitlab**: Projects and project prefixes to track, MR states, pipeline/approval settings
  - `projects`: Explicit project IDs or paths
  - `project_prefixes`: Namespace prefixes for automatic subproject inclusion
  - `states`: MR states to include (opened, merged, closed)
  - `max_comments_per_mr`: Number of comments per MR (default: 5)
  - `max_comment_length`: Character limit per comment (default: 500)
  - `max_description_length`: Character limit for MR descriptions (default: 1000)
- **gdrive**: Folder IDs to monitor, file types to include
- **ai**: Provider (anthropic/openai/vertex), model, temperature, max_tokens (default: 8000)
- **output**: Drive folder for reports, sharing recipients
- **database**: SQLite path for deduplication tracking
- **logging**: Log level, file path, rotation settings

## Data Flow

```
External APIs → Collectors → Processor → AI Analyzer → Generator → Google Doc
                              ↓
                         SQLite DB (deduplication)
```

1. Collectors fetch data from Gmail/Jira/GitLab/Drive for specified date range
2. Processor normalizes data and filters out previously processed items
3. AI Analyzer generates insights and summaries
4. Generator creates formatted Google Doc and shares it
5. Database tracks processed items to prevent duplicates in future runs

## Key Implementation Details

### Date Handling
- Uses `utils.get_date_range()` to calculate lookback period
- Timezone-aware (configured in `schedule.timezone`)
- Default lookback: 7 days

### Deduplication Strategy
- Emails tracked by `message_id` (Gmail internal ID)
- Jira issues tracked by `issue_key` and `last_updated` timestamp
- GitLab MRs tracked by `(project_id, mr_iid, last_updated)` composite key
- Drive files tracked by `file_id` and `last_modified` timestamp
- Old entries cleaned up based on `database.retention_days`

### Error Handling
- Authentication failures raise descriptive errors with setup instructions
- API rate limiting should be handled by adjusting config (reduce lookback, add filters)
- Logs written to `logs/agent.log` with configurable rotation
- Enhanced error logging with stack traces (`exc_info=True`) for debugging
- Configuration validation on startup warns about potential issues
- JQL queries validated for excessive length (>2000 chars)

### Modular Design
Each collector/processor/generator can be tested independently. To add a new data source:
1. Create collector in `src/collectors/` implementing `collect(start_date, end_date)`
2. Add normalization logic in `DataProcessor`
3. Update `main.py` to initialize and call new collector
4. Extend AI prompts in `summarizer.py` to handle new data type

## AI Analyzer Details

### Prompt Structure
The AI analyzer (`src/ai/summarizer.py`) sends a structured prompt requesting JSON response with six sections:
1. **executive_summary**: 2-3 paragraph overview
2. **email_highlights**: themes, action_items, critical_messages
3. **project_progress**: completed, in_progress, blockers, sprint_summary
4. **gitlab_activity**: merged_count, open_count, highlights, ready_for_review, stale_mrs
5. **document_activity**: new_documents, major_updates
6. **action_items**: prioritized list (high/medium/low)

### Token Management
To avoid token overflow, formatters limit items sent to LLM:
- Emails: First 15 with 150-char snippet
- Jira issues: First 20 with configurable description limit (default: 1000 chars)
- GitLab MRs: First 20 with configurable description limit (default: 1000 chars)
- Drive files: First 20
- Comments: Configurable count per issue/MR (default: 5) with configurable length (default: 500 chars)

These limits can be adjusted in `config.yaml` under `jira` and `gitlab` sections using `max_comments_per_issue`, `max_comment_length`, and `max_description_length`.

### Response Parsing
- Expects JSON response from LLM
- Automatically extracts JSON from markdown code blocks (```json...```)
- Falls back to empty section structures if JSON parsing fails (preserves document structure)
- Logs debug information (first/last 500 chars) when parsing fails
- Adds metadata (timestamp, model, provider, data summary)
- Default `max_tokens` is 8000 to ensure complete responses

## Document Generator Details

### Google Docs API Pattern
Uses batch requests to build documents efficiently:
- Tracks character index position throughout document
- Inserts text then applies styles (HEADING_1, HEADING_2, HEADING_3, bold)
- All formatting happens in single `batchUpdate` call

### Report Structure
Generated documents have this hierarchy:
```
Report Period
├── Executive Summary
├── Email Highlights
│   ├── Key Communication Themes
│   ├── Action Items from Emails
│   └── Critical Messages
├── Project Progress
│   ├── Completed This Week
│   ├── Currently In Progress
│   ├── Blockers & Concerns
│   └── Sprint Summary
├── Code Review Activity (GitLab)
│   ├── Merged This Period
│   ├── Ready for Review
│   └── Stale MRs Needing Attention
├── Document Activity
│   ├── New Documents
│   └── Major Updates
├── Action Items & Next Steps
│   ├── High Priority
│   ├── Medium Priority
│   └── Low Priority
└── Recommendations
```

### Sharing Mechanism
- Documents created in root, then moved to `output.drive_folder_id`
- Shares with `output.share_with` emails as readers
- Sends email notification if configured

## Collector Implementation Details

### Gmail Collector
**Query Building**: Constructs complex Gmail search query:
```
after:YYYY/MM/DD before:YYYY/MM/DD 
(label:Work OR label:Important) 
(from:sender1 OR from:sender2)
-from:noreply@ -in:spam -in:trash
```

**Data Extraction**:
- Fetches full message format to get headers and body
- Decodes base64-encoded message parts
- Limits body to 1000 chars, falls back to snippet
- Filters system labels (those starting with `Label_`)

**Limits**: `max_emails` (default 100) caps results

### Jira Collector
**JQL Building**: Constructs query with projects, date range, issue types, components, custom JQL
```sql
project in (PROJ, DEV) 
AND updated >= 'YYYY-MM-DD' AND updated <= 'YYYY-MM-DD'
AND issuetype in ("Story", "Task", "Bug", "Epic")
AND component in ("Backend", "API")
ORDER BY updated DESC
```
- Validates JQL length (<2000 chars) to prevent server rejections
- Logs configuration summary on initialization for troubleshooting

**Configuration Validation**:
- Raises `ValueError` if config is None or empty
- Warns if no projects, custom_jql, or board_ids are configured (prevents accidental over-collection)

**Pagination**: Uses `_search_issues_paginated()` to fetch all results in chunks
- Page size: `search_page_size` (default 100, Jira API max)
- Optional `max_issues` cap to limit total results

**Changelog Retrieval** (two strategies):
1. **Bulk Changelog API** (Jira Cloud): Fetches status changes for up to 1000 issues per request - much faster
2. **Expand Changelog** (fallback/Server): Individual `expand=changelog` per issue

**Sprint Tracking**:
- If `board_ids` specified: Only queries those boards (fast)
- Otherwise: Queries all visible boards with `maxResults=False`
- Returns active sprints as metadata item
- Board names cached to avoid repeated API lookups

**Field Extraction** (configurable limits):
- Description: `max_description_length` chars (default: 1000)
- Comments: Last `max_comments_per_issue` (default: 5), truncated to `max_comment_length` chars (default: 500)
- Gets parent (epic) information if available
- Robust URL construction with proper trailing slash handling

**Performance Features**:
- Progress tracking for large collections (logs every 10 items when >20 total)
- Performance metrics logged: total time, items/sec
- Board name caching reduces redundant API calls
- Enhanced error logging with stack traces and issue context (type, board name)

### GitLab Collector
**Project Resolution**: Supports two modes for identifying projects:
1. **Explicit projects**: Direct project IDs or paths (e.g., `["12345", "group/project"]`)
2. **Project prefixes**: Namespace patterns that match all subprojects (e.g., `["company/team"]`)

**Prefix Matching** (`_resolve_projects_from_prefixes()`):
- Fetches all accessible projects from GitLab API
- Filters by prefix using `startswith()` pattern matching
- Automatically includes all subprojects under the specified namespace
- Example: `"redhat/rhel-ai/core/team-docs"` matches that project and all nested subprojects

**MR Collection** (`_collect_project_mrs()`):
- Token-based pagination for handling large MR lists
- Filters by state (opened, merged, closed), date range, labels, authors
- Optionally includes/excludes draft MRs
- Configurable limit per project (`max_mrs_per_project`, default: 50)

**Data Extraction** (`_extract_mr_data()`):
- **Basic info**: MR IID, title, description (truncated to `max_description_length`)
- **Approvals**: Fetches approval details if `include_approvals` enabled
- **Comments**: Recent discussions limited to `max_comments_per_mr` (default: 5)
- **Pipeline status**: CI/CD status if `include_pipelines` enabled
- **Merge info**: Merged by, merge time for merged MRs
- **Age calculation**: Days open/since merge for prioritization

**Configurable Data Limits**:
- `max_comments_per_mr`: Number of discussion threads (default: 5)
- `max_comment_length`: Character limit per comment (default: 500)
- `max_description_length`: Character limit for MR description (default: 1000)

**Error Handling**:
- Graceful fallback if GitLab token not configured (skips collection)
- Handles GitLab API 502 errors by logging warning and continuing
- Validates project access before attempting collection
- Uses `get_all=False` to suppress pagination warnings

**Performance**:
- Only fetches specified projects or prefix-matched projects
- Caches project list to avoid repeated API calls
- Efficient pagination with token-based approach

## Scheduler Implementation

**Library**: Uses `schedule` library (not APScheduler, despite it being in requirements.txt)

**Timezone Handling**:
- Config specifies timezone (e.g., "America/Los_Angeles")
- Validates timezone with `pytz.timezone()`
- Falls back to UTC if invalid

**Execution Loop**:
- Checks `schedule.run_pending()` every 60 seconds
- Weekly schedule: `schedule.every().<day>.at("<time>").do(task)`
- Runs until interrupted (Ctrl+C)

**Note**: Daemon mode does NOT run report immediately on start (that line is commented out)

## Utility Functions

Key helpers in `src/utils.py`:

- **setup_logging()**: Configures dual output (file + console), creates log directory
- **get_date_range()**: Returns timezone-aware start/end dates with configurable lookback
- **format_date_for_display()**: Formats as "Jan 23, 2026" for reports
- **get_env_var()**: Validates required env vars with helpful error messages
- **ensure_credentials_dir()**: Creates `config/credentials/` if missing

## Testing Strategy

- `tests/test_auth.py`: Validates Google OAuth and Jira authentication
- `tests/test_processor.py`: Tests data normalization and deduplication
- `tests/test_gitlab_access.py`: Tests GitLab authentication and lists accessible projects
- `tests/test_gitlab_prefixes.py`: Tests project prefix matching to verify which projects are included
- `tests/test_gitlab_integration.py`: End-to-end GitLab collection and processing test
- Mock external APIs in tests to avoid real API calls
- Use `--dry-run` flag for integration testing without document creation
- See `tests/README.md` for detailed test documentation

## Troubleshooting

### OAuth Issues
Delete `config/credentials/google_token.pickle` to force re-authentication. Check that all three APIs (Gmail, Drive, Docs) are enabled in Google Cloud Console.

### Empty Reports
Check logs for collector errors, verify config (labels/projects/folder IDs), ensure lookback period is appropriate. Gmail labels are case-sensitive.

### Rate Limiting
- Gmail: Reduce `max_emails`, increase `lookback_days` to batch fewer requests
- Jira: Use `max_issues` cap, narrow JQL with `custom_jql`, specify `board_ids` for sprint tracking
- GitLab: Reduce `max_mrs_per_project`, use specific `projects` instead of broad `project_prefixes`
- Drive: Reduce number of monitored folders

### GitLab Issues
- **No MRs collected**: Verify `GITLAB_TOKEN` has `read_api` scope, check project access permissions
- **502 Bad Gateway**: Temporary GitLab server error - agent logs warning and continues with other sources
- **Too many projects matched**: Narrow `project_prefixes` to more specific namespace paths
- **Missing MRs**: Check `states` filter (default: opened, merged), verify `lookback_days` covers the period
- **Token not configured**: GitLab is optional - agent will skip collection if `GITLAB_TOKEN` not set

### AI Quality
- Adjust `temperature` (lower = more focused, 0.0-1.0)
- Modify prompt in `src/ai/summarizer.py` `_build_analysis_prompt()`
- Try different model (Claude Haiku/Sonnet, GPT-4, Vertex AI)
- Increase `max_tokens` if responses are truncated (default: 8000)
- Check logs for "Failed to parse LLM response" - indicates truncated or malformed JSON
- If JSON parsing fails, response falls back to empty sections with error note

### Jira Bulk Changelog Fails
If bulk changelog returns 404, agent falls back to per-issue `expand=changelog` (slower but works on Jira Server/DC). Check logs for "Bulk changelog fetch failed" message with stack trace for detailed error information.

### Slow Jira Collection
- Check logs for performance metrics: "Successfully collected X items in Y.ZZs (N items/sec)"
- For large collections, watch for progress messages: "Processing issue X/Y"
- Board name caching automatically reduces API calls for sprint tracking
- If collection is slower than expected, consider:
  - Narrowing JQL with `custom_jql` to reduce result set
  - Setting `max_issues` to cap collection
  - Specifying `board_ids` instead of querying all boards
  - Reducing `max_comments_per_issue` if comment fetching is slow

### Debug Logging
Enable debug logging (`logging.level: DEBUG` in config) to see:
- Full configuration summary on startup
- JQL query validation warnings
- Stack traces for all errors
- Board name cache hits/misses
- Detailed API interaction logs

## Configuration Best Practices

- **Gmail labels**: Use specific labels rather than querying all mail to reduce API calls
- **Jira board_ids**: Specify exact board IDs if you know them - avoids querying all boards
- **Jira data limits**: Adjust `max_comments_per_issue`, `max_comment_length`, and `max_description_length` to balance detail vs. token usage
  - Increase limits for detailed analysis, decrease for high-volume issue tracking
  - Check debug logs for configuration summary on startup
- **GitLab project selection**: 
  - Use `project_prefixes` for automatic subproject inclusion (e.g., `"company/team"`)
  - Use `projects` for explicit project list when you know exact paths/IDs
  - Start with narrow prefixes, expand as needed to avoid matching too many projects
  - Set `max_mrs_per_project` to limit collection per project
- **GitLab data limits**: Similar to Jira - adjust `max_comments_per_mr`, `max_comment_length`, `max_description_length`
- **Lookback period**: 7 days is optimal; longer periods = more API calls and larger LLM context
- **Temperature**: 0.3 works well for factual summaries; increase to 0.5-0.7 for more creative analysis
- **max_tokens**: Default 8000 provides complete responses; increase if dealing with very large data sets
- **File types**: Limit `gdrive.file_types` to reduce noise in reports
- **Configuration validation**: Enable debug logging to see configuration summary and catch misconfigurations early
