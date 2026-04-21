#!/usr/bin/env python
"""Quick test of Jira collection + Claude Sonnet 4.6 analysis."""

import sys
sys.path.insert(0, 'src')

from utils import load_env_vars, get_date_range
from collectors.jira_collector import JiraCollector
from ai.summarizer import AISummarizer
import yaml
import json

# Load environment
load_env_vars()

print("="*70)
print("JIRA + CLAUDE SONNET 4.6 TEST")
print("="*70)
print()

# Load config
with open('config/config.yaml') as f:
    config = yaml.safe_load(f)

# Step 1: Collect Jira data
print("Step 1: Collecting Jira data...")
print("-"*70)

jira_config = config.get('jira', {})
jira_config['track_sprints'] = False  # Skip sprint tracking for speed

collector = JiraCollector(jira_config)

start_date, end_date = get_date_range(7, "UTC")
print(f"Date range: {start_date.date()} to {end_date.date()}")
print(f"Project: {jira_config.get('projects')}")
print()

jira_issues = collector.collect(start_date, end_date)
print(f"✓ Collected {len(jira_issues)} Jira issues")
print()

# If no real data, create mock data
if len(jira_issues) == 0:
    print("⚠ No real issues found - creating mock data for testing...")
    jira_issues = [
        {
            'key': 'TEST-1',
            'summary': 'Implement user authentication system',
            'description': 'Add OAuth2 authentication to the application',
            'status': 'In Progress',
            'issue_type': 'Story',
            'priority': 'High',
            'assignee': 'John Doe',
            'reporter': 'Jane Smith',
            'created': '2026-04-15T10:00:00',
            'updated': '2026-04-18T14:30:00',
            'resolution': None,
            'labels': ['security', 'auth'],
            'epic_key': 'TEST-100',
            'epic_name': 'Security Improvements',
            'status_changes': [
                {'date': '2026-04-15T10:00:00', 'from': 'To Do', 'to': 'In Progress', 'author': 'John Doe'}
            ],
            'comments': [
                {'author': 'Jane Smith', 'body': 'Please prioritize this for the upcoming release', 'created': '2026-04-16T09:00:00'}
            ],
            'url': 'https://example.atlassian.net/browse/TEST-1'
        },
        {
            'key': 'TEST-2',
            'summary': 'Fix database connection pool leak',
            'description': 'Connection pool is not releasing connections properly',
            'status': 'Done',
            'issue_type': 'Bug',
            'priority': 'Critical',
            'assignee': 'Alice Johnson',
            'reporter': 'Bob Wilson',
            'created': '2026-04-14T08:00:00',
            'updated': '2026-04-17T16:00:00',
            'resolution': 'Fixed',
            'labels': ['database', 'performance'],
            'epic_key': None,
            'epic_name': None,
            'status_changes': [
                {'date': '2026-04-14T09:00:00', 'from': 'To Do', 'to': 'In Progress', 'author': 'Alice Johnson'},
                {'date': '2026-04-17T16:00:00', 'from': 'In Progress', 'to': 'Done', 'author': 'Alice Johnson'}
            ],
            'comments': [],
            'url': 'https://example.atlassian.net/browse/TEST-2'
        },
        {
            'key': 'TEST-3',
            'summary': 'Add weekly status report generation',
            'description': 'Automate weekly status reports using AI',
            'status': 'In Review',
            'issue_type': 'Task',
            'priority': 'Medium',
            'assignee': 'Claude AI',
            'reporter': 'Project Manager',
            'created': '2026-04-13T14:00:00',
            'updated': '2026-04-19T11:00:00',
            'resolution': None,
            'labels': ['automation', 'reporting'],
            'epic_key': 'TEST-100',
            'epic_name': 'Process Automation',
            'status_changes': [
                {'date': '2026-04-13T15:00:00', 'from': 'To Do', 'to': 'In Progress', 'author': 'Claude AI'},
                {'date': '2026-04-19T11:00:00', 'from': 'In Progress', 'to': 'In Review', 'author': 'Claude AI'}
            ],
            'comments': [
                {'author': 'Project Manager', 'body': 'Looking forward to seeing this in action!', 'created': '2026-04-18T10:00:00'}
            ],
            'url': 'https://example.atlassian.net/browse/TEST-3'
        }
    ]
    print(f"✓ Created {len(jira_issues)} mock issues for testing")
    print()

# Show sample
if jira_issues:
    print("Sample issues:")
    for issue in jira_issues[:3]:
        print(f"  • {issue.get('key', 'N/A')}: {issue.get('summary', 'N/A')[:50]}")
    print()

# Step 2: Prepare data for AI
print("Step 2: Preparing data for AI analysis...")
print("-"*70)

# Create minimal processed data structure
processed_data = {
    'gmail': {
        'total_count': 0,
        'important': [],
        'by_sender': {},
        'all_emails': []
    },
    'jira': {
        'total_count': len(jira_issues),
        'completed': [i for i in jira_issues if i.get('status') == 'Done'],
        'in_progress': [i for i in jira_issues if i.get('status') in ['In Progress', 'In Review']],
        'by_status': {},
        'by_priority': {},
        'all_issues': jira_issues
    },
    'gdrive': {
        'total_count': 0,
        'newly_created': [],
        'recently_modified': [],
        'by_folder': {},
        'all_files': []
    },
    'summary': {
        'total_emails': 0,
        'total_jira_issues': len(jira_issues),
        'total_drive_files': 0
    }
}

# Categorize by status
for issue in jira_issues:
    status = issue.get('status', 'Unknown')
    if status not in processed_data['jira']['by_status']:
        processed_data['jira']['by_status'][status] = []
    processed_data['jira']['by_status'][status].append(issue)

    priority = issue.get('priority', 'None')
    if priority not in processed_data['jira']['by_priority']:
        processed_data['jira']['by_priority'][priority] = []
    processed_data['jira']['by_priority'][priority].append(issue)

print(f"✓ Data prepared")
print(f"  - Total issues: {processed_data['jira']['total_count']}")
print(f"  - Completed: {len(processed_data['jira']['completed'])}")
print(f"  - In Progress: {len(processed_data['jira']['in_progress'])}")
print()

# Step 3: Analyze with Claude Sonnet 4.6
print("Step 3: Analyzing with Claude Sonnet 4.6...")
print("-"*70)

ai_config = config.get('ai', {})
print(f"Provider: {ai_config.get('provider')}")
print(f"Model: {ai_config.get('model')}")
print(f"Region: {config.get('ai', {}).get('region', 'us-east1')}")
print()

summarizer = AISummarizer(ai_config)

try:
    print("Sending data to Claude for analysis...")
    analysis = summarizer.analyze(processed_data, start_date, end_date)

    print()
    print("="*70)
    print("✅ SUCCESS! Claude Sonnet 4.6 Analysis Complete")
    print("="*70)
    print()

    # Display the analysis
    print("EXECUTIVE SUMMARY:")
    print("-"*70)
    print(analysis.get('executive_summary', 'N/A'))
    print()

    if 'project_progress' in analysis:
        print("PROJECT PROGRESS:")
        print("-"*70)
        progress = analysis['project_progress']

        if progress.get('completed'):
            print(f"\nCompleted ({len(progress['completed'])} items):")
            for item in progress['completed'][:3]:
                print(f"  • {item.get('key', 'N/A')}: {item.get('summary', 'N/A')[:50]}")

        if progress.get('in_progress'):
            print(f"\nIn Progress ({len(progress['in_progress'])} items):")
            for item in progress['in_progress'][:3]:
                print(f"  • {item.get('key', 'N/A')}: {item.get('summary', 'N/A')[:50]}")

        if progress.get('blockers'):
            print(f"\nBlockers:")
            for blocker in progress['blockers']:
                print(f"  • {blocker}")
        print()

    if 'action_items' in analysis:
        print("ACTION ITEMS:")
        print("-"*70)
        for item in analysis['action_items'][:5]:
            priority = item.get('priority', 'medium').upper()
            print(f"  [{priority}] {item.get('item', 'N/A')}")
        print()

    # Show metadata
    if 'metadata' in analysis:
        print("METADATA:")
        print("-"*70)
        meta = analysis['metadata']
        print(f"  Model: {meta.get('model', 'N/A')}")
        print(f"  Provider: {meta.get('provider', 'N/A')}")
        print(f"  Generated: {meta.get('generated_at', 'N/A')}")
        print()

    print("="*70)
    print("✅ Test Complete! Claude Sonnet 4.6 is working correctly.")
    print("="*70)
    print()
    print("Full analysis saved to: test_analysis_output.json")

    # Save full output
    with open('test_analysis_output.json', 'w') as f:
        json.dump(analysis, f, indent=2)

except Exception as e:
    print()
    print("="*70)
    print("❌ ERROR during AI analysis")
    print("="*70)
    print(f"Error: {e}")
    print()
    import traceback
    traceback.print_exc()
    sys.exit(1)
