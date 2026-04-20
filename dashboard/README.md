# Dashboard Quick Start Guide

This dashboard visualizes metrics collected from your Jira, Gmail, and Google Drive data.

## Directory Structure

```
dashboard/
├── index.html          # Main dashboard page
├── css/
│   └── styles.css      # Dashboard styling
├── js/
│   └── dashboard.js    # Chart rendering and data loading
└── data/
    └── metrics.json    # Generated metrics (created by extract_metrics.py)
```

## Usage

### Step 1: Extract Metrics

Run the metrics extraction script to generate data:

```bash
cd /Users/fpj/Development/python/weekly-status-agent
source venv/bin/activate  # or your virtual environment

# Make script executable
chmod +x scripts/extract_metrics.py

# Run extraction
python scripts/extract_metrics.py
```

This will:
- Collect issues from Jira (last 90 days)
- Calculate various metrics
- Save results to `dashboard/data/metrics.json`

### Step 2: View Dashboard

Open the dashboard in your browser:

```bash
cd dashboard
python -m http.server 8000
```

Then visit: **http://localhost:8000**

Alternatively, just open `index.html` directly in your browser.

## What's Displayed

### Summary Cards
- Total issues
- Open issues (with percentage)
- Closed issues
- Average resolution time

### Charts
1. **Issues Over Time** - Timeline of created vs closed issues
2. **Status Distribution** - Current status breakdown
3. **Priority Distribution** - Priority levels
4. **Top Packages** - Most mentioned packages
5. **Team Workload** - Issues per assignee
6. **Issue Types** - Bug, Story, Task, etc.
7. **Top Components** - Issues by component

### Package Details Table
- Package mention counts
- Issue counts
- Sample issue keys

## Automation

### Schedule Regular Updates

Add to your crontab to update metrics automatically:

```bash
# Update metrics every 6 hours
0 */6 * * * cd /Users/fpj/Development/python/weekly-status-agent && /path/to/venv/bin/python scripts/extract_metrics.py >> logs/metrics.log 2>&1
```

Or use macOS launchd:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.metrics-extraction</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/venv/bin/python</string>
        <string>/Users/fpj/Development/python/weekly-status-agent/scripts/extract_metrics.py</string>
    </array>
    <key>StartInterval</key>
    <integer>21600</integer> <!-- 6 hours -->
    <key>StandardErrorPath</key>
    <string>/Users/fpj/Development/python/weekly-status-agent/logs/metrics-error.log</string>
    <key>StandardOutPath</key>
    <string>/Users/fpj/Development/python/weekly-status-agent/logs/metrics.log</string>
</dict>
</plist>
```

Save to `~/Library/LaunchAgents/com.user.metrics-extraction.plist` and load:

```bash
launchctl load ~/Library/LaunchAgents/com.user.metrics-extraction.plist
```

## Deploy to GitLab Pages

### Option 1: Manual Deployment

1. Create a GitLab repository
2. Add this dashboard folder
3. Create `.gitlab-ci.yml`:

```yaml
pages:
  stage: deploy
  script:
    - pip install -r requirements.txt
    - python scripts/extract_metrics.py
    - mkdir -p public
    - cp -r dashboard/* public/
  artifacts:
    paths:
      - public
  only:
    - main
```

4. Push to GitLab - your dashboard will be at `https://yourusername.gitlab.io/projectname`

### Option 2: Scheduled Pipeline

Update `.gitlab-ci.yml` to run metrics extraction on a schedule:

```yaml
pages:
  stage: deploy
  script:
    - pip install -r requirements.txt
    - python scripts/extract_metrics.py
    - mkdir -p public
    - cp -r dashboard/* public/
  artifacts:
    paths:
      - public
  only:
    - schedules
    - main
```

Then in GitLab: Settings → CI/CD → Schedules → Add new schedule (e.g., every 6 hours)

## Customization

### Add New Metrics

Edit `scripts/extract_metrics.py`:

```python
def extract_metrics(issues):
    metrics = {
        # ... existing metrics ...
        'custom_metrics': {
            'my_metric': calculate_my_metric(issues)
        }
    }
    return metrics
```

### Add New Charts

1. Update `dashboard/index.html` to add a new canvas:
```html
<div class="chart-container">
    <h2>My Custom Chart</h2>
    <canvas id="myChart"></canvas>
</div>
```

2. Update `dashboard/js/dashboard.js`:
```javascript
function createCharts(data) {
    // ... existing charts ...
    createMyChart(data.custom_metrics.my_metric);
}

function createMyChart(myData) {
    const ctx = document.getElementById('myChart');
    new Chart(ctx, {
        // ... chart configuration ...
    });
}
```

### Modify Styling

Edit `dashboard/css/styles.css` to change colors, layouts, fonts, etc.

## Troubleshooting

### "Failed to load metrics data"
- Ensure `dashboard/data/metrics.json` exists
- Run `python scripts/extract_metrics.py` to generate it

### CORS Errors in Browser
- Use `python -m http.server` instead of opening `index.html` directly
- Or configure your browser to allow local file access

### No Data Showing
- Check browser console (F12) for errors
- Verify JSON structure in `data/metrics.json`
- Check that Jira credentials are configured correctly

### Metrics Extraction Fails
- Verify `.env` file has correct Jira credentials
- Check `config/config.yaml` has valid Jira configuration
- Review logs in `logs/agent.log`

## Next Steps

See `DASHBOARD_STRATEGY.md` for advanced features:
- Time-series database integration
- Historical trend analysis
- Real-time updates
- Advanced metrics (velocity, cycle time, etc.)
- Git integration
- CI/CD metrics
