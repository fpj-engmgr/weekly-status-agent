# Dashboard Strategy: From Weekly Reports to Live Metrics

## Executive Summary

This document outlines how to transform your existing `weekly-status-agent` and Jira analysis scripts into a live, interactive dashboard similar to the GitLab Pages statistics dashboard you referenced.

**Current State:** Markdown reports generated from Jira/Gmail/Drive data  
**Target State:** Live web dashboard with historical metrics, visualizations, and drill-down capabilities

---

## 1. Current Metrics Collection Capabilities

### What You're Already Collecting

#### From Jira Collector (`src/collectors/jira_collector.py`):
- **Issue Data:**
  - Summary, status, priority, issue type
  - Created/updated/resolution dates
  - Assignee, reporter, creator
  - Sprint information
  - Epic/parent relationships
  - Components, labels, fix versions
  - Time tracking data
  
- **Comments & Descriptions:**
  - Configurable limits (max 5 comments, 500 chars each)
  - Description text (up to 1000 chars)
  
- **Status History:**
  - Bulk changelog API (for Jira Cloud)
  - Status transitions with timestamps
  
- **Sprint Tracking:**
  - Active sprints
  - Sprint associations
  - Board information (with caching)

#### From Gmail Collector:
- Email metadata (sender, subject, date)
- Labels and categories
- Body content (up to 1000 chars)
- Thread information

#### From Google Drive Collector:
- File changes and modifications
- Folder activity
- Document metadata

#### From Analysis Scripts:
- **Package Mention Analysis:** Tracks 253 packages across issue text
- **Date Distributions:** When issues are created/closed
- **Time-to-Close Metrics:** Resolution time calculations
- **Status Transitions:** Issue lifecycle tracking
- **Categorization:** By component, package, type

---

## 2. Dashboard Architecture Design

### Recommended Technology Stack

#### Backend - Data Pipeline:
```
┌─────────────────┐
│ Jira/Gmail/     │
│ Drive APIs      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Data Collectors │  (Your existing collectors)
│ (Python)        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Metrics         │  (New: Extract & aggregate metrics)
│ Processor       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Time-Series DB  │  (InfluxDB, TimescaleDB, or SQLite)
│ + JSON Storage  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ API Server      │  (FastAPI or Flask)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Static Site     │  (GitLab Pages / GitHub Pages)
│ Generator       │
└─────────────────┘
```

#### Frontend - Dashboard:
```
Option 1: Static Site (Like GitLab Pages)
├── Static HTML/CSS/JS
├── Chart.js or Plotly.js for visualizations
├── Fetch data from JSON files
└── Deploy to GitLab Pages

Option 2: Interactive Dashboard
├── React/Vue.js frontend
├── Recharts/D3.js for visualizations
├── Fetch from API backend
└── Deploy to Vercel/Netlify

Option 3: Python Dashboard (Simplest)
├── Dash (Plotly) or Streamlit
├── Direct connection to database
└── Deploy to Heroku/Cloud Run
```

### Database Schema for Metrics

```sql
-- Time-series metrics table
CREATE TABLE metrics (
    timestamp DATETIME,
    metric_name VARCHAR(100),
    metric_value FLOAT,
    dimensions JSON,  -- {project, component, assignee, etc.}
    INDEX(timestamp, metric_name)
);

-- Issue snapshots (daily)
CREATE TABLE issue_snapshots (
    snapshot_date DATE,
    issue_key VARCHAR(20),
    status VARCHAR(50),
    assignee VARCHAR(100),
    sprint_id INT,
    component VARCHAR(100),
    packages JSON,
    PRIMARY KEY(snapshot_date, issue_key)
);

-- Package mentions over time
CREATE TABLE package_metrics (
    date DATE,
    package_name VARCHAR(100),
    mention_count INT,
    issue_count INT,
    open_issues INT,
    closed_issues INT,
    PRIMARY KEY(date, package_name)
);

-- Sprint metrics
CREATE TABLE sprint_metrics (
    sprint_id INT,
    sprint_name VARCHAR(200),
    start_date DATE,
    end_date DATE,
    planned_points INT,
    completed_points INT,
    total_issues INT,
    completed_issues INT,
    PRIMARY KEY(sprint_id)
);
```

---

## 3. Extended Metrics for Detailed Gathering

### Metrics You Can Add Now (Using Existing Data)

#### Velocity & Throughput:
- **Issues completed per week/sprint**
- **Story points completed** (if using story points)
- **Cycle time:** Time from "In Progress" → "Done"
- **Lead time:** Time from "Created" → "Done"
- **Work in Progress (WIP):** Issues in "In Progress" status

#### Quality Metrics:
- **Bug ratio:** Bugs vs. features created/resolved
- **Reopened issues:** Issues that went from Done → Reopened
- **Time to first response:** On comments/issues
- **Issue aging:** How long issues stay open

#### Team Metrics:
- **Workload distribution:** Issues per assignee
- **Contribution patterns:** Who creates/closes most issues
- **Cross-component work:** Assignees working across components
- **Response time:** Average time for assignee to update issue

#### Package-Specific Metrics:
- **Top packages by issue volume:** Which packages have most issues
- **Package issue velocity:** How fast package-related issues get resolved
- **Package complexity score:** Issues per package + avg resolution time
- **Package coupling:** Which packages appear together in issues

#### Sprint/Project Health:
- **Sprint burndown:** Remaining work over sprint
- **Scope creep:** Issues added mid-sprint
- **Sprint predictability:** Planned vs. actual completion
- **Blocker frequency:** Issues marked as blocked

#### Trend Analysis:
- **7-day/30-day moving averages** for all metrics
- **Week-over-week change** percentages
- **Anomaly detection:** Unusual spikes/drops in metrics

### New Data You Could Collect

#### From Jira (Requires Additional API Calls):
- **Full changelog history:** All field changes, not just status
- **Worklogs:** Time spent on issues
- **Links between issues:** Blocks/depends on relationships
- **Attachments metadata:** File types, sizes
- **Votes and watchers:** Interest level
- **SLA metrics:** If using Jira Service Management

#### From Git Integration:
- **Commit frequency:** Commits linked to issues
- **Code churn:** Lines changed per issue
- **PR metrics:** Reviews, time to merge
- **Branch patterns:** Feature branches per issue

#### From CI/CD:
- **Build success rates:** Per issue/PR
- **Test coverage changes:** Impact on coverage
- **Deployment frequency:** Issues deployed per week

#### From Communication:
- **Slack mentions:** Issues discussed in channels
- **Meeting references:** Issues in meeting notes
- **Documentation updates:** Docs created/updated per issue

---

## 4. Implementation Roadmap

### Phase 1: Metrics Extraction (Week 1-2)

**Goal:** Export metrics from existing collectors to structured format

1. **Create Metrics Extractor Module:**
   ```python
   # src/metrics/extractor.py
   class MetricsExtractor:
       def extract_from_issues(self, issues) -> List[Metric]:
           # Extract time-series metrics
           # Calculate aggregations
           # Return structured metrics
   ```

2. **Add Database Storage:**
   ```bash
   # Use SQLite for simplicity, or PostgreSQL for production
   pip install sqlalchemy pandas
   ```

3. **Modify Existing Collectors:**
   - Keep current functionality
   - Add metrics extraction hooks
   - Store raw data + calculated metrics

4. **Create Daily Snapshot Job:**
   ```python
   # scripts/snapshot_metrics.py
   # Run daily via cron/launchd
   # Captures point-in-time metrics
   ```

### Phase 2: Dashboard Backend (Week 3-4)

**Goal:** API to serve metrics data

1. **Choose Approach:**
   - **Simple:** Generate static JSON files
   - **Advanced:** FastAPI REST API

2. **Static JSON Approach (Recommended for GitLab Pages):**
   ```python
   # scripts/generate_dashboard_data.py
   import json
   from datetime import datetime, timedelta
   
   def generate_dashboard_data():
       data = {
           'last_updated': datetime.now().isoformat(),
           'summary': {
               'total_issues': 1234,
               'open_issues': 456,
               'closed_this_week': 78
           },
           'time_series': {
               'issues_created': [...],  # [{date, count}, ...]
               'issues_closed': [...],
               'packages': {...}  # {package_name: [{date, count}, ...]}
           },
           'top_packages': [...],
           'team_metrics': {...}
       }
       
       with open('dashboard/data/metrics.json', 'w') as f:
           json.dump(data, f)
   ```

3. **Schedule Updates:**
   ```bash
   # Run every 6 hours
   0 */6 * * * cd /path/to/project && python scripts/generate_dashboard_data.py
   ```

### Phase 3: Dashboard Frontend (Week 5-6)

**Goal:** Interactive visualizations

1. **Create Static Dashboard:**
   ```
   dashboard/
   ├── index.html
   ├── css/
   │   └── styles.css
   ├── js/
   │   ├── main.js
   │   ├── charts.js
   │   └── metrics.js
   └── data/
       └── metrics.json (generated)
   ```

2. **Sample Dashboard Layout:**
   ```html
   <!DOCTYPE html>
   <html>
   <head>
       <title>AIPCC Development Statistics</title>
       <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
       <script src="https://cdn.jsdelivr.net/npm/plotly.js-dist"></script>
   </head>
   <body>
       <div class="dashboard">
           <header>
               <h1>AIPCC Development Metrics</h1>
               <p id="last-updated"></p>
           </header>
           
           <section class="summary-cards">
               <div class="card" id="total-issues"></div>
               <div class="card" id="open-issues"></div>
               <div class="card" id="closed-this-week"></div>
               <div class="card" id="avg-resolution-time"></div>
           </section>
           
           <section class="charts">
               <div class="chart-container">
                   <h2>Issues Over Time</h2>
                   <canvas id="issues-timeline"></canvas>
               </div>
               
               <div class="chart-container">
                   <h2>Top Packages by Issue Volume</h2>
                   <div id="packages-chart"></div>
               </div>
               
               <div class="chart-container">
                   <h2>Team Workload Distribution</h2>
                   <canvas id="team-workload"></canvas>
               </div>
               
               <div class="chart-container">
                   <h2>Resolution Time Trend</h2>
                   <canvas id="resolution-trend"></canvas>
               </div>
           </section>
           
           <section class="tables">
               <h2>Recent Issues</h2>
               <table id="recent-issues"></table>
           </section>
       </div>
       
       <script src="js/main.js"></script>
   </body>
   </html>
   ```

3. **JavaScript for Charts:**
   ```javascript
   // js/main.js
   async function loadDashboard() {
       const response = await fetch('data/metrics.json');
       const data = await response.json();
       
       // Update summary cards
       document.getElementById('total-issues').textContent = data.summary.total_issues;
       
       // Create timeline chart
       const ctx = document.getElementById('issues-timeline');
       new Chart(ctx, {
           type: 'line',
           data: {
               labels: data.time_series.issues_created.map(d => d.date),
               datasets: [
                   {
                       label: 'Created',
                       data: data.time_series.issues_created.map(d => d.count),
                       borderColor: 'rgb(75, 192, 192)'
                   },
                   {
                       label: 'Closed',
                       data: data.time_series.issues_closed.map(d => d.count),
                       borderColor: 'rgb(255, 99, 132)'
                   }
               ]
           }
       });
   }
   
   loadDashboard();
   ```

### Phase 4: Deployment (Week 7)

**Option A: GitLab Pages (Recommended)**

1. **Create `.gitlab-ci.yml`:**
   ```yaml
   pages:
     stage: deploy
     script:
       - pip install -r requirements.txt
       - python scripts/generate_dashboard_data.py
       - mkdir -p public
       - cp -r dashboard/* public/
     artifacts:
       paths:
         - public
     only:
       - main
   ```

2. **Push to GitLab:**
   ```bash
   git add .gitlab-ci.yml dashboard/
   git commit -m "Add dashboard"
   git push
   ```

**Option B: Python Dashboard (Streamlit/Dash)**

1. **Create Streamlit App:**
   ```python
   # dashboard_app.py
   import streamlit as st
   import pandas as pd
   import plotly.express as px
   
   st.title('AIPCC Development Statistics')
   
   # Load data
   df = pd.read_sql('SELECT * FROM metrics', engine)
   
   # Display charts
   fig = px.line(df, x='date', y='issue_count', color='status')
   st.plotly_chart(fig)
   ```

2. **Deploy:**
   ```bash
   streamlit run dashboard_app.py
   # Or deploy to Streamlit Cloud
   ```

---

## 5. Quick Start: Minimal Dashboard (2-3 Hours)

If you want to see results quickly, here's a minimal implementation:

### Step 1: Extract Current Metrics
```python
# scripts/quick_metrics.py
import json
from datetime import datetime, timedelta
from src.collectors.jira_collector import JiraCollector
from collections import Counter

def generate_quick_metrics():
    collector = JiraCollector(config['jira'])
    
    # Get last 90 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    issues = collector.collect(start_date, end_date)
    
    # Calculate metrics
    metrics = {
        'total': len(issues),
        'by_status': Counter(i['status'] for i in issues),
        'by_priority': Counter(i['priority'] for i in issues),
        'by_assignee': Counter(i['assignee'] for i in issues),
        'created_by_week': calculate_weekly_counts(issues, 'created'),
        'closed_by_week': calculate_weekly_counts(issues, 'updated', status='Closed')
    }
    
    with open('dashboard/data/metrics.json', 'w') as f:
        json.dump(metrics, f, default=str)

if __name__ == '__main__':
    generate_quick_metrics()
```

### Step 2: Simple HTML Dashboard
```html
<!-- dashboard/index.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Quick Metrics Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        .card { background: #f5f5f5; padding: 20px; margin: 10px; border-radius: 8px; }
        .chart { margin: 20px 0; }
    </style>
</head>
<body>
    <h1>AIPCC Metrics Dashboard</h1>
    <div id="summary"></div>
    <div class="chart">
        <canvas id="statusChart"></canvas>
    </div>
    <div class="chart">
        <canvas id="weeklyTrend"></canvas>
    </div>
    
    <script>
        fetch('data/metrics.json')
            .then(r => r.json())
            .then(data => {
                // Display summary
                document.getElementById('summary').innerHTML = 
                    `<div class="card">Total Issues: ${data.total}</div>`;
                
                // Status chart
                new Chart(document.getElementById('statusChart'), {
                    type: 'pie',
                    data: {
                        labels: Object.keys(data.by_status),
                        datasets: [{
                            data: Object.values(data.by_status)
                        }]
                    }
                });
                
                // Weekly trend
                new Chart(document.getElementById('weeklyTrend'), {
                    type: 'line',
                    data: {
                        labels: Object.keys(data.created_by_week),
                        datasets: [
                            {
                                label: 'Created',
                                data: Object.values(data.created_by_week)
                            },
                            {
                                label: 'Closed',
                                data: Object.values(data.closed_by_week)
                            }
                        ]
                    }
                });
            });
    </script>
</body>
</html>
```

### Step 3: Test Locally
```bash
cd dashboard
python -m http.server 8000
# Open http://localhost:8000
```

---

## 6. Recommended Tools & Libraries

### Data Collection & Processing:
- **pandas:** Data manipulation and aggregation
- **SQLAlchemy:** Database ORM
- **schedule:** Automated metric collection
- **python-dateutil:** Date handling

### Storage:
- **SQLite:** Simple, file-based (good for < 1M records)
- **PostgreSQL:** Production-ready relational DB
- **TimescaleDB:** Time-series extension for PostgreSQL
- **InfluxDB:** Purpose-built time-series database

### Visualization Libraries:
- **Chart.js:** Simple, clean charts (recommended for static sites)
- **Plotly.js:** Interactive, feature-rich charts
- **D3.js:** Maximum customization (steep learning curve)
- **Apache ECharts:** Beautiful, performant charts

### Dashboard Frameworks:
- **Streamlit:** Python-only, fastest to build
- **Dash (Plotly):** Python, more customizable
- **Metabase:** No-code dashboard on top of DB
- **Grafana:** Time-series focused, powerful

---

## 7. Sample Metrics Queries

### Daily Issue Snapshot:
```sql
-- Track issue states over time
INSERT INTO issue_snapshots
SELECT 
    CURRENT_DATE as snapshot_date,
    key as issue_key,
    status,
    assignee,
    sprint_id,
    component,
    JSON_EXTRACT(metadata, '$.packages') as packages
FROM jira_issues;
```

### Weekly Velocity:
```python
def calculate_weekly_velocity(start_date, end_date):
    """Calculate issues completed per week."""
    query = """
        SELECT 
            DATE_TRUNC('week', resolution_date) as week,
            COUNT(*) as issues_completed,
            SUM(story_points) as points_completed
        FROM jira_issues
        WHERE resolution_date BETWEEN ? AND ?
            AND status = 'Closed'
        GROUP BY week
        ORDER BY week
    """
    return pd.read_sql(query, engine, params=[start_date, end_date])
```

### Package Trend Analysis:
```python
def package_trends(package_name, days=90):
    """Get issue counts for a package over time."""
    query = """
        SELECT 
            DATE(created) as date,
            COUNT(*) as new_issues,
            SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) as closed_issues
        FROM jira_issues
        WHERE JSON_CONTAINS(packages, ?)
            AND created >= DATE_SUB(NOW(), INTERVAL ? DAY)
        GROUP BY date
        ORDER BY date
    """
    return pd.read_sql(query, engine, params=[f'"{package_name}"', days])
```

---

## 8. Next Steps

1. **Review this strategy** and decide on your approach
2. **Choose dashboard technology** (Static site vs. Python dashboard)
3. **Start with Phase 1** - Metrics extraction
4. **Build minimal dashboard** using the Quick Start guide
5. **Iterate and expand** based on feedback

Would you like me to help you implement any specific part of this strategy?
