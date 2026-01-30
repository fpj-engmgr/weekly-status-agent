# Setup Guide - Weekly Status Report Agent

This guide will walk you through setting up the Weekly Status Report Agent from scratch.

## Prerequisites

- Python 3.10 or higher
- pip or pipenv
- Google Cloud account
- Jira account with API access
- Anthropic or OpenAI API key

## Step-by-Step Setup

### 1. Install Dependencies

```bash
cd weekly-status-agent

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Google Cloud APIs

#### a. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name your project (e.g., "Weekly Status Agent")
4. Click "Create"

#### b. Enable Required APIs

1. In the Cloud Console, go to "APIs & Services" → "Library"
2. Search for and enable each of these APIs:
   - **Gmail API**
   - **Google Drive API**
   - **Google Docs API**

#### c. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - Choose "External" user type
   - Fill in app name and your email
   - Add your email as a test user
   - Save and continue through all steps
4. Back in Credentials, click "Create Credentials" → "OAuth client ID"
5. Select "Desktop app" as the application type
6. Name it "Weekly Status Agent"
7. Click "Create"
8. Download the JSON file
9. Save it as `config/credentials/google_oauth.json`

### 3. Configure Jira Access

#### For Jira Cloud:

1. Go to [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click "Create API token"
3. Give it a label (e.g., "Weekly Status Agent")
4. Copy the token (you won't see it again!)

#### For Jira Server/Data Center:

Use your username and password.

### 4. Get AI API Key

#### Option A: Anthropic Claude (Recommended)

1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Create an account if needed
3. Go to "API Keys"
4. Create a new API key
5. Copy the key

#### Option B: OpenAI GPT-4

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Create an account if needed
3. Go to "API Keys"
4. Create a new API key
5. Copy the key

### 5. Create Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```bash
# Jira
JIRA_URL=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-api-token

# AI (choose one)
ANTHROPIC_API_KEY=sk-ant-...
# or
# OPENAI_API_KEY=sk-...
```

### 6. Configure the Agent

Create your configuration file:

```bash
cp config/config.example.yaml config/config.yaml
```

Edit `config/config.yaml` and customize:

1. **Schedule**: Set day and time for automatic reports
2. **Gmail**: Add labels or senders to monitor
3. **Jira**: Add your project keys (e.g., ["PROJ", "DEV"])
4. **Google Drive**: Add folder IDs you want to monitor
   - To get folder ID: Open folder in browser, copy ID from URL
   - URL format: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
5. **Output**: Set output folder ID and people to share with

### 7. Test the Setup

Run the setup test script:

```bash
python scripts/test_setup.py
```

This will verify:
- Environment variables are set
- Configuration file is valid
- Google authentication works
- Jira authentication works

### 8. Run Your First Report

Generate a test report:

```bash
python src/main.py --dry-run
```

This will collect data and analyze it without creating a document.

To create an actual report:

```bash
python src/main.py
```

### 9. Set Up Automation (Optional)

#### Option A: Python Scheduler (Simple)

Run the agent in daemon mode:

```bash
python src/main.py --daemon
```

This keeps the process running and executes on schedule. You'll need to keep the terminal open or use `nohup` or `screen`.

#### Option B: macOS launchd (Recommended)

1. Edit `scripts/com.user.weekly-status.plist`
2. Update the paths to match your installation
3. Run the setup script:

```bash
./scripts/setup_launchd.sh
```

The agent will now run automatically in the background.

To check status:

```bash
launchctl list | grep weekly-status
```

To view logs:

```bash
tail -f logs/launchd-out.log
```

## Troubleshooting

### Google Authentication Issues

If you see "Access blocked: Authorization Error":
1. Make sure you added yourself as a test user in OAuth consent screen
2. Verify all three APIs are enabled (Gmail, Drive, Docs)
3. Try deleting `config/credentials/google_token.pickle` and re-authenticating

### Jira Connection Fails

- Verify your Jira URL is correct (include https://)
- Check that API token hasn't expired
- For Jira Cloud, use email + API token (not username + password)
- For Jira Server/DC, use username + password

### AI Analysis Errors

- Verify API key is correct and has credits/quota
- Check that you've set the right provider in config.yaml
- Try reducing `max_tokens` if hitting token limits

### Empty Reports

- Check date range in Gmail query (might be too restrictive)
- Verify Jira project keys are correct
- Ensure Google Drive folder IDs are valid
- Check logs for collection errors: `tail -f logs/agent.log`

## Next Steps

1. Review your first report and adjust configuration
2. Refine Gmail labels and Jira filters
3. Add more Google Drive folders if needed
4. Customize the report template in `src/generators/doc_generator.py`
5. Set up automation for weekly generation

## Support

For issues or questions:
1. Check the logs in `logs/agent.log`
2. Run `python scripts/test_setup.py` to diagnose
3. Review the README.md for additional information
