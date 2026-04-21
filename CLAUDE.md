# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Weekly Status Report Agent - An automated Python tool that collects data from Gmail, Jira, and Google Drive, analyzes it with AI, and generates weekly status reports as Google Docs.

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
- **GDriveCollector**: Monitors Google Drive folders for file changes

Each collector returns a list of normalized dictionaries with consistent structure.

### 2. Processor (`src/processors/data_processor.py`)
- **Deduplication**: Uses SQLite (`data/tracking.db`) to track processed items
- **Normalization**: Converts raw API responses to consistent internal format
- **Categorization**: Groups data by sender/status/type/folder for analysis

The processor prevents duplicate reporting by maintaining three tracking tables: `processed_emails`, `processed_jira_issues`, `processed_drive_files`.

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

### Config Sections (`config/config.yaml`)
- **schedule**: Day/time for automatic report generation
- **gmail**: Labels to monitor, senders to include/exclude, lookback period
- **jira**: Projects to track, components to filter, custom JQL, sprint/epic settings, configurable data limits
  - `components`: Optional list of component names to filter (empty = all components)
  - `max_comments_per_issue`: Number of comments per issue (default: 5)
  - `max_comment_length`: Character limit per comment (default: 500)
  - `max_description_length`: Character limit for issue descriptions (default: 1000)
- **gdrive**: Folder IDs to monitor, file types to include
- **ai**: Provider (anthropic/openai), model, temperature, max_tokens
- **output**: Drive folder for reports, sharing recipients
- **database**: SQLite path for deduplication tracking
- **logging**: Log level, file path, rotation settings

## Data Flow

```
External APIs → Collectors → Processor → AI Analyzer → Generator → Google Doc
                              ↓
                         SQLite DB (deduplication)
```

1. Collectors fetch data from Gmail/Jira/Drive for specified date range
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
The AI analyzer (`src/ai/summarizer.py`) sends a structured prompt requesting JSON response with five sections:
1. **executive_summary**: 2-3 paragraph overview
2. **email_highlights**: themes, action_items, critical_messages
3. **project_progress**: completed, in_progress, blockers, sprint_summary
4. **document_activity**: new_documents, major_updates
5. **action_items**: prioritized list (high/medium/low)

### Token Management
To avoid token overflow, formatters limit items sent to LLM:
- Emails: First 15 with 150-char snippet
- Jira issues: First 20 with configurable description limit (default: 1000 chars)
- Drive files: First 20
- Comments: Configurable count per issue (default: 5) with configurable length (default: 500 chars)

These Jira limits can be adjusted in `config.yaml` under the `jira` section using `max_comments_per_issue`, `max_comment_length`, and `max_description_length`.

### Response Parsing
- Expects JSON response from LLM
- Automatically extracts JSON from markdown code blocks (```json...```)
- Falls back to raw text if JSON parsing fails
- Adds metadata (timestamp, model, provider, data summary)

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
- Mock external APIs in tests to avoid real API calls
- Use `--dry-run` flag for integration testing without document creation
- `scripts/test_setup.py`: Validates environment variables and API connections

## Troubleshooting

### OAuth Issues
Delete `config/credentials/google_token.pickle` to force re-authentication. Check that all three APIs (Gmail, Drive, Docs) are enabled in Google Cloud Console.

### Empty Reports
Check logs for collector errors, verify config (labels/projects/folder IDs), ensure lookback period is appropriate. Gmail labels are case-sensitive.

### Rate Limiting
- Gmail: Reduce `max_emails`, increase `lookback_days` to batch fewer requests
- Jira: Use `max_issues` cap, narrow JQL with `custom_jql`, specify `board_ids` for sprint tracking
- Drive: Reduce number of monitored folders

### AI Quality
- Adjust `temperature` (lower = more focused, 0.0-1.0)
- Modify prompt in `src/ai/summarizer.py` `_build_analysis_prompt()`
- Try different model (Claude vs GPT-4)
- Increase `max_tokens` if responses are truncated

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
- **Lookback period**: 7 days is optimal; longer periods = more API calls and larger LLM context
- **Temperature**: 0.3 works well for factual summaries; increase to 0.5-0.7 for more creative analysis
- **File types**: Limit `gdrive.file_types` to reduce noise in reports
- **Configuration validation**: Enable debug logging to see configuration summary and catch misconfigurations early
