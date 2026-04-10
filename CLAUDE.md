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
- **jira**: Projects to track, custom JQL, sprint/epic settings
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

### Modular Design
Each collector/processor/generator can be tested independently. To add a new data source:
1. Create collector in `src/collectors/` implementing `collect(start_date, end_date)`
2. Add normalization logic in `DataProcessor`
3. Update `main.py` to initialize and call new collector
4. Extend AI prompts in `summarizer.py` to handle new data type

## Testing Strategy

- `tests/test_auth.py`: Validates Google OAuth and Jira authentication
- `tests/test_processor.py`: Tests data normalization and deduplication
- Mock external APIs in tests to avoid real API calls
- Use `--dry-run` flag for integration testing without document creation

## Troubleshooting

### OAuth Issues
Delete `config/credentials/google_token.pickle` to force re-authentication

### Empty Reports
Check logs for collector errors, verify config (labels/projects/folder IDs), ensure lookback period is appropriate

### Rate Limiting
Reduce `max_emails`, increase `lookback_days`, narrow JQL filters

### AI Quality
Adjust `temperature` (lower = more focused), modify prompts in `src/ai/summarizer.py`, try different model
