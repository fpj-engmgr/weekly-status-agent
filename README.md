# Weekly Status Report Agent

An automated Python agent that generates comprehensive weekly status reports by collecting and analyzing data from Gmail, Jira, and Google Drive.

## Features

- **Automated Data Collection**: Fetches emails, Jira issues, and Drive file changes from the past week
- **AI-Powered Analysis**: Uses LLM (Claude/GPT-4) to summarize and categorize information
- **Google Docs Output**: Generates beautifully formatted reports as Google Docs
- **Scheduled Execution**: Runs automatically on a weekly schedule
- **Smart Deduplication**: Tracks processed items to avoid redundant reporting

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

- **schedule**: Day and time to generate reports
- **gmail**: Labels, senders, lookback period
- **jira**: Projects, JQL filters, sprint tracking
- **gdrive**: Folder IDs to monitor
- **ai**: Provider (anthropic/openai), model, temperature
- **output**: Drive folder for reports, sharing settings

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
- Increase `lookback_days` to reduce Gmail queries
- Adjust JQL filters to limit Jira results
- Add delays in collector code if needed

### Report Quality

If AI summaries aren't useful:
- Adjust temperature in config (lower = more focused)
- Modify prompts in `src/ai/summarizer.py`
- Try different model (Claude vs GPT-4)

## Development

Run tests:

```bash
pytest tests/
```

Add logging for debugging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

- Web dashboard for historical reports
- Slack/Teams integration
- Calendar event integration
- Multi-user support
- Template customization UI

## License

MIT License

## Contributing

Contributions welcome! Please open an issue or PR.
