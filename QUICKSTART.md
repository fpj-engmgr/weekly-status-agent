# Quick Start Guide

Get your Weekly Status Report Agent running in 15 minutes!

## 1. Install (2 minutes)

```bash
cd weekly-status-agent
./scripts/install.sh
```

This creates a virtual environment and installs all dependencies.

## 2. Configure Google APIs (5 minutes)

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable these APIs:
   - Gmail API
   - Google Drive API
   - Google Docs API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download credentials → save as `config/credentials/google_oauth.json`

[Detailed instructions in SETUP.md](SETUP.md#2-configure-google-cloud-apis)

## 3. Set Up API Keys (3 minutes)

Edit `.env`:

```bash
# Jira (get token from: https://id.atlassian.com/manage-profile/security/api-tokens)
JIRA_URL=https://your-company.atlassian.net
JIRA_EMAIL=you@company.com
JIRA_API_TOKEN=your-token-here

# AI - Choose one:
ANTHROPIC_API_KEY=sk-ant-...  # Get from: https://console.anthropic.com/
# or
# OPENAI_API_KEY=sk-...        # Get from: https://platform.openai.com/
```

## 4. Configure Settings (3 minutes)

Edit `config/config.yaml`:

```yaml
gmail:
  labels: ["Work", "Important"]  # Gmail labels to monitor

jira:
  projects: ["PROJ", "DEV"]      # Your Jira project keys

gdrive:
  folders:
    - id: "YOUR_FOLDER_ID"       # Get from folder URL in browser
      name: "Projects"

output:
  drive_folder_id: "OUTPUT_ID"  # Where to save reports
  share_with:
    - "boss@company.com"
```

To get Google Drive folder IDs:
- Open folder in browser
- Copy ID from URL: `drive.google.com/drive/folders/FOLDER_ID_HERE`

## 5. Test (2 minutes)

```bash
source venv/bin/activate
python scripts/test_setup.py
```

This verifies all your credentials and configuration.

## 6. Generate Your First Report!

### Dry run (preview without creating doc):
```bash
python src/main.py --dry-run
```

### Create actual report:
```bash
python src/main.py
```

The agent will:
1. Collect emails, Jira issues, and Drive files from the past week
2. Analyze everything with AI
3. Create a beautiful Google Doc report
4. Share it with configured people
5. Print the document URL

## 7. Automate (Optional)

### macOS - Run in background:
```bash
./scripts/setup_launchd.sh
```

### Any OS - Run as daemon:
```bash
python src/main.py --daemon
```

## Common Issues

**"OAuth credentials not found"**
- Make sure you saved credentials as `config/credentials/google_oauth.json`

**"Jira authentication failed"**
- Verify JIRA_URL includes `https://`
- Check API token hasn't expired

**"No emails/issues found"**
- Verify your labels/project keys are correct
- Try increasing lookback_days in config

**Need help?**
- Check logs: `tail -f logs/agent.log`
- Run diagnostics: `python scripts/test_setup.py`
- See full guide: [SETUP.md](SETUP.md)

## What You Get

Your weekly report includes:

- **Executive Summary** - AI-generated overview of your week
- **Email Highlights** - Key communications grouped by theme
- **Project Progress** - Jira issues completed, in progress, and blocked
- **Document Activity** - Important Google Drive updates
- **Action Items** - Prioritized next steps from all sources

## Next Steps

- Refine your configuration based on first report
- Add more Gmail labels or Jira projects
- Customize report format in `src/generators/doc_generator.py`
- Set up weekly automation
- Share with your team!

## Resources

- [SETUP.md](SETUP.md) - Detailed setup instructions
- [README.md](README.md) - Full documentation
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribute to the project
