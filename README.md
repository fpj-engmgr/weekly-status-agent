# Weekly Status Report Agent

An automated Python agent that generates comprehensive weekly status reports by collecting and analyzing data from Gmail, Jira, and Google Drive.

## Recent Improvements

**Jira Collector Enhancements** (Latest):
- ✅ **Configurable Data Limits**: Control comment counts and text lengths via config
- ✅ **Performance Metrics**: See collection time and items/sec in logs
- ✅ **Progress Tracking**: Get updates during large collections (>20 issues)
- ✅ **Board Name Caching**: Reduced API calls for sprint tracking
- ✅ **Enhanced Error Logging**: Stack traces with issue context for easier debugging
- ✅ **Configuration Validation**: Warns about missing or invalid settings on startup
- ✅ **JQL Validation**: Checks query length to prevent server rejections
- ✅ **Robust Error Handling**: No more silent failures, all errors logged with context

See [CLAUDE.md](CLAUDE.md) for detailed implementation notes.

## Features

- **Automated Data Collection**: Fetches emails, Jira issues, and Drive file changes from the past week
- **AI-Powered Analysis**: Uses LLM (Claude/GPT-4) to summarize and categorize information
- **Google Docs Output**: Generates beautifully formatted reports as Google Docs
- **Scheduled Execution**: Runs automatically on a weekly schedule
- **Smart Deduplication**: Tracks processed items to avoid redundant reporting
- **Configurable Data Limits**: Control comment counts, text lengths, and description sizes to balance detail vs. performance
- **Performance Optimization**: Board name caching, bulk changelog API, progress tracking for large collections
- **Enhanced Debugging**: Detailed logging with stack traces, configuration validation, and performance metrics

## Architecture

The agent follows a modular pipeline architecture:
1. **Collectors**: Fetch data from Gmail, Jira, and Google Drive APIs
2. **Processor**: Normalizes and structures collected data
3. **AI Analyzer**: Summarizes and extracts insights using LLM
4. **Generator**: Creates formatted Google Doc report
5. **Scheduler**: Automates weekly execution

## Prerequisites

- Python 3.10 or higher
- Google Cloud Platform account with enabled APIs (Gmail, Drive, Docs)
- Jira account with API access
- Anthropic API key (for Claude) or OpenAI API key (for GPT-4)

## Setup

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt
```

### 2. Configure Google Cloud APIs

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable the following APIs:
   - Gmail API
   - Google Drive API
   - Google Docs API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download credentials and save as `config/credentials/google_oauth.json`

### 3. Configure Jira Access

1. Generate Jira API token from your account settings
2. Create `.env` file in project root:

```bash
JIRA_URL=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-api-token
ANTHROPIC_API_KEY=your-anthropic-key
# Or use OpenAI instead:
# OPENAI_API_KEY=your-openai-key
```

### 4. Configure Settings

Copy and customize the configuration:

```bash
cp config/config.example.yaml config/config.yaml
```

Edit `config/config.yaml` with your preferences:
- Gmail labels to monitor
- Jira projects to track
- Google Drive folders to watch
- Report schedule and output settings

## Usage

### Manual Execution

Run the agent manually:

```bash
python src/main.py
```

With custom config:

```bash
python src/main.py --config config/config.yaml
```

Test mode (dry-run without creating doc):

```bash
python src/main.py --test --dry-run
```

### Automated Execution

#### Using schedule (within Python)

The agent uses the `schedule` library to run automatically. Just keep the process running:

```bash
python src/main.py --daemon
```

#### Using macOS launchd

For true background execution without keeping terminal open:

1. Edit `scripts/com.user.weekly-status.plist` with your paths
2. Copy to LaunchAgents:

```bash
cp scripts/com.user.weekly-status.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.user.weekly-status.plist
```

## Project Structure

```
weekly-status-agent/
├── config/
│   ├── config.yaml              # Main configuration
│   └── credentials/             # API credentials (gitignored)
├── src/
│   ├── main.py                  # Entry point
│   ├── collectors/              # Data collection modules
│   ├── processors/              # Data processing
│   ├── ai/                      # AI/LLM integration
│   ├── generators/              # Report generation
│   └── scheduler/               # Scheduling logic
├── data/                        # SQLite database
├── logs/                        # Application logs
└── tests/                       # Unit tests
```

## Configuration

Key configuration options in `config.yaml`:

### Schedule
- **day**: Day of week to generate report (e.g., "Friday")
- **time**: Time in 24-hour format (e.g., "17:00")
- **timezone**: Timezone for scheduling (e.g., "America/Los_Angeles")

### Gmail
- **labels**: Gmail labels to monitor (e.g., ["Work", "Important"])
- **exclude_senders**: Email patterns to exclude (e.g., "noreply@")
- **lookback_days**: Number of days to look back (default: 7)
- **max_emails**: Maximum emails to collect (default: 100)

### Jira
- **projects**: Jira projects to track (e.g., ["PROJ", "DEV"])
- **issue_types**: Issue types to include (e.g., ["Story", "Task", "Bug", "Epic"])
- **custom_jql**: Optional custom JQL filter
- **board_ids**: Optional board IDs for faster sprint tracking (recommended)
- **track_sprints**: Enable sprint tracking (default: true)
- **bulk_changelog**: Use bulk changelog API for faster status history (default: true)

**New: Configurable Data Limits** (helps manage token usage and performance):
- **max_comments_per_issue**: Number of recent comments per issue (default: 5)
- **max_comment_length**: Character limit per comment (default: 500)
- **max_description_length**: Character limit for issue descriptions (default: 1000)

Adjust these to balance detail vs. performance:
- **Increase** for detailed analysis (more context for AI)
- **Decrease** for high-volume tracking (faster collection, lower token usage)

### Google Drive
- **folders**: List of folder IDs to monitor
- **file_types**: Mime types to include (empty for all)
- **lookback_days**: Number of days to look back (default: 7)

### AI
- **provider**: "anthropic" or "openai"
- **model**: Model name (e.g., "claude-3-5-sonnet-20241022")
- **temperature**: 0.0-1.0 (lower = more focused, default: 0.3)
- **max_tokens**: Maximum response tokens (default: 4000)

### Output
- **drive_folder_id**: Google Drive folder for generated reports
- **share_with**: List of email addresses to share with
- **title_format**: Report title template

### Logging
- **level**: Log level - INFO, DEBUG, WARNING, ERROR
- **file**: Log file path (default: "logs/agent.log")

**Use DEBUG level to see:**
- Full configuration summary on startup
- JQL query validation details
- Performance metrics and caching info
- Stack traces for all errors

## Example Configurations

### High-Detail Analysis

For comprehensive reports with maximum context:

```yaml
jira:
  max_comments_per_issue: 10
  max_comment_length: 1000
  max_description_length: 2000
  board_ids: [123, 456]  # Specify boards for faster collection
  bulk_changelog: true

logging:
  level: "INFO"
```

### High-Volume Tracking

For tracking many issues with reduced overhead:

```yaml
jira:
  max_comments_per_issue: 3
  max_comment_length: 250
  max_description_length: 500
  max_issues: 200  # Cap total issues
  board_ids: [123]  # Single board only

logging:
  level: "INFO"
```

### Performance Debugging

For troubleshooting slow collection:

```yaml
jira:
  max_comments_per_issue: 5
  max_comment_length: 500
  max_description_length: 1000
  board_ids: [123, 456]  # Always specify for best performance
  bulk_changelog: true

logging:
  level: "DEBUG"  # See all performance metrics
```

## Security

- All credentials stored in `.env` and `config/credentials/` (gitignored)
- OAuth tokens automatically refreshed
- Read-only access where possible
- Sensitive data not logged

## Troubleshooting

### Authentication Issues

If you see OAuth errors:
1. Delete token files in `config/credentials/`
2. Re-run agent to trigger new OAuth flow
3. Verify enabled APIs in Google Cloud Console

### Rate Limiting

If hitting API limits:
- **Gmail**: Reduce `max_emails` or increase `lookback_days`
- **Jira**: Set `max_issues` cap, narrow with `custom_jql`, or specify `board_ids`
- **Drive**: Reduce number of monitored folders

### Slow Jira Collection

Check logs for performance metrics (shows collection time and items/sec). To improve performance:
- **Specify board_ids**: Avoids scanning all visible boards (board names are cached)
- **Narrow JQL**: Use `custom_jql` to reduce result set
- **Set max_issues**: Cap total collection (e.g., 500)
- **Reduce data limits**: Lower `max_comments_per_issue` if comment fetching is slow
- **Enable bulk_changelog**: Uses faster bulk API for Jira Cloud (default: true)

Watch for progress messages in logs: `Processing issue X/Y`

### Empty or Missing Data

Check configuration validation warnings in logs:
- Enable DEBUG logging: `logging.level: DEBUG`
- Look for "No projects, custom_jql, or board_ids configured" warning
- Verify JQL query length warnings (<2000 chars recommended)
- Review configuration summary logged on startup

### Configuration Validation Errors

The Jira collector now validates configuration on startup:
- **ValueError: "Jira configuration is required"**: Check `jira` section exists in config
- **Warning about missing data sources**: Add `projects`, `custom_jql`, or `board_ids`
- **JQL query too long**: Simplify or split your query

### Debugging Tips

Enable DEBUG logging to see:
```yaml
logging:
  level: "DEBUG"
```

This shows:
- Full configuration summary with all Jira settings
- JQL query validation and warnings
- Performance metrics: collection time, items/sec
- Board name cache hits/misses
- Stack traces for all errors with full context
- API interaction details

### Report Quality

If AI summaries aren't useful:
- **Adjust temperature**: Lower (0.1-0.3) for focused summaries, higher (0.5-0.7) for creative analysis
- **Modify data limits**: Increase `max_description_length` and `max_comment_length` for more context
- **Try different model**: Claude vs GPT-4
- **Edit prompts**: Modify `src/ai/summarizer.py` for custom analysis
- **Check token usage**: Increase `max_tokens` if responses are truncated

### Jira Bulk Changelog Failures

If you see "Bulk changelog fetch failed" in logs:
- Agent automatically falls back to per-issue `expand=changelog` (slower but works)
- This is normal for Jira Server/DC (bulk API is Cloud-only)
- Check stack traces in DEBUG mode for detailed error info

## Development

### Running Tests

```bash
pytest tests/
```

### Debugging

Enable DEBUG logging in `config/config.yaml`:

```yaml
logging:
  level: "DEBUG"
```

Or set programmatically:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Debug logging shows:
- Configuration summary on startup
- Performance metrics (collection time, items/sec)
- JQL query validation warnings
- Stack traces for all errors
- API call details
- Caching behavior (board names, etc.)

### Testing Setup

Verify your configuration:

```bash
python scripts/test_setup.py
```

### Dry Run

Test collection and analysis without creating a document:

```bash
python src/main.py --dry-run
```

### Performance Profiling

Watch for these log messages to identify bottlenecks:
- `"JQL query is very long"` - Query optimization needed
- `"Processing issue X/Y"` - Collection progress (appears every 10 issues)
- `"Successfully collected X items in Y.ZZs"` - Overall performance metrics
- `"Using bulk changelog for X issues"` - Bulk API status

## Best Practices

### Jira Configuration

1. **Always specify board_ids** if you track sprints - avoids scanning all boards
2. **Start with default data limits**, adjust based on your needs:
   - Detailed weekly reviews → increase limits
   - Daily check-ins → decrease limits
3. **Use custom_jql** to narrow results (filters issues before collection)
4. **Monitor performance logs** - watch for collection time and adjust limits
5. **Enable bulk_changelog** for Jira Cloud (much faster than per-issue)

### Performance Optimization

1. **Gmail**: Use specific labels rather than querying all mail
2. **Jira**: Specify exact `board_ids` to avoid board scanning
3. **Lookback period**: 7 days is optimal (more = more API calls + larger LLM context)
4. **Data limits**: Balance detail vs. speed based on issue volume
5. **Debug mode**: Only enable when troubleshooting (generates verbose logs)

### Configuration Management

1. **Version control**: Keep `config.example.yaml` updated with new options
2. **Documentation**: Comment complex JQL or custom filters in config
3. **Validation**: Enable DEBUG mode initially to catch configuration issues
4. **Incremental changes**: Test one collector at a time when adjusting settings

### Token Usage (AI)

- Default limits are optimized for ~100 issues
- For >200 issues, consider reducing data limits
- Temperature 0.3 works well for factual summaries
- Increase to 0.5-0.7 for more creative/analytical reports

## Future Enhancements

- Web dashboard for historical reports
- Slack/Teams integration
- Calendar event integration
- Multi-user support
- Template customization UI
- Webhook support for real-time updates
- Additional collectors (GitHub, Confluence, Slack)

## Quick Reference

### Common Configuration Patterns

**Minimal Jira setup (projects only):**
```yaml
jira:
  projects: ["PROJ"]
```

**Performance-optimized Jira setup:**
```yaml
jira:
  projects: ["PROJ"]
  board_ids: [123]
  max_issues: 100
  bulk_changelog: true
```

**Detailed analysis Jira setup:**
```yaml
jira:
  projects: ["PROJ", "DEV"]
  board_ids: [123, 456]
  max_comments_per_issue: 10
  max_comment_length: 1000
  max_description_length: 2000
  custom_jql: "assignee = currentUser()"
```

### Troubleshooting Commands

```bash
# Enable debug logging
# Edit config/config.yaml: logging.level: "DEBUG"

# Test setup
python scripts/test_setup.py

# Dry run (no document creation)
python src/main.py --dry-run

# Watch logs in real-time
tail -f logs/agent.log

# Check for configuration warnings
grep -i "warning" logs/agent.log

# Check performance metrics
grep "Successfully collected" logs/agent.log
```

### Environment Variables

```bash
# Required
JIRA_URL=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-api-token

# AI Provider (choose one)
ANTHROPIC_API_KEY=your-anthropic-key
# OR
OPENAI_API_KEY=your-openai-key
```

## License

MIT License

## Contributing

Contributions welcome! Please open an issue or PR.

## Resources

- **CLAUDE.md**: Detailed implementation notes and architecture guide
- **config.example.yaml**: Fully documented configuration template
- **Issue Tracker**: Report bugs or request features
