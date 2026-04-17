#!/usr/bin/env python3
"""
Extract metrics from Jira data for dashboard visualization.
This script demonstrates how to transform your existing collectors
into structured metrics for a dashboard.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collectors.jira_collector import JiraCollector
from src.utils import get_date_range
import yaml


def load_config():
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'
    with open(config_path) as f:
        return yaml.safe_load(f)


def calculate_time_to_close(issue):
    """Calculate days from created to resolved."""
    if not issue.get('resolution_date'):
        return None

    created = datetime.fromisoformat(issue['created'].replace('Z', '+00:00'))
    resolved = datetime.fromisoformat(issue['resolution_date'].replace('Z', '+00:00'))
    return (resolved - created).days


def group_by_week(issues, date_field):
    """Group issues by week."""
    weekly = defaultdict(int)

    for issue in issues:
        date_str = issue.get(date_field)
        if not date_str:
            continue

        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        week_start = date - timedelta(days=date.weekday())
        week_key = week_start.strftime('%Y-%m-%d')
        weekly[week_key] += 1

    return dict(sorted(weekly.items()))


def extract_packages_from_text(text):
    """Extract package mentions from text."""
    # Simplified version - you can use your existing package list
    packages = [
        'pytorch', 'torch', 'cuda', 'numpy', 'tensorflow',
        'transformers', 'build', 'cmake', 'nccl', 'triton'
    ]

    found = set()
    if not text:
        return found

    text_lower = text.lower()
    for pkg in packages:
        if pkg.lower() in text_lower:
            found.add(pkg)

    return found


def extract_metrics(issues):
    """Extract comprehensive metrics from issues."""

    metrics = {
        'generated_at': datetime.now().isoformat(),
        'total_issues': len(issues),
        'summary': {},
        'time_series': {},
        'distributions': {},
        'package_metrics': {},
        'team_metrics': {},
        'quality_metrics': {}
    }

    # Summary metrics
    open_issues = [i for i in issues if i['status'] not in ['Closed', 'Resolved', 'Done']]
    closed_issues = [i for i in issues if i['status'] in ['Closed', 'Resolved', 'Done']]

    metrics['summary'] = {
        'total': len(issues),
        'open': len(open_issues),
        'closed': len(closed_issues),
        'open_percentage': round(len(open_issues) / len(issues) * 100, 1) if issues else 0
    }

    # Time-to-close metrics
    close_times = [calculate_time_to_close(i) for i in closed_issues]
    close_times = [t for t in close_times if t is not None]

    if close_times:
        metrics['summary']['avg_time_to_close_days'] = round(sum(close_times) / len(close_times), 1)
        metrics['summary']['median_time_to_close_days'] = sorted(close_times)[len(close_times) // 2]

    # Time series data
    metrics['time_series'] = {
        'created_by_week': group_by_week(issues, 'created'),
        'closed_by_week': group_by_week(closed_issues, 'resolution_date')
    }

    # Status distribution
    status_counts = Counter(i['status'] for i in issues)
    metrics['distributions']['by_status'] = dict(status_counts.most_common())

    # Priority distribution
    priority_counts = Counter(i.get('priority', 'None') for i in issues)
    metrics['distributions']['by_priority'] = dict(priority_counts.most_common())

    # Issue type distribution
    type_counts = Counter(i.get('issue_type', 'Unknown') for i in issues)
    metrics['distributions']['by_type'] = dict(type_counts.most_common())

    # Component distribution
    component_counts = Counter()
    for issue in issues:
        components = issue.get('components', [])
        for comp in components:
            component_counts[comp] += 1
    metrics['distributions']['by_component'] = dict(component_counts.most_common(10))

    # Package mentions
    package_mentions = Counter()
    package_issues = defaultdict(list)

    for issue in issues:
        text = f"{issue.get('summary', '')} {issue.get('description', '')}"
        packages = extract_packages_from_text(text)
        for pkg in packages:
            package_mentions[pkg] += 1
            package_issues[pkg].append(issue['key'])

    metrics['package_metrics'] = {
        'top_packages': dict(package_mentions.most_common(20)),
        'package_details': {
            pkg: {
                'mention_count': count,
                'issue_count': len(package_issues[pkg]),
                'sample_issues': package_issues[pkg][:5]
            }
            for pkg, count in package_mentions.most_common(10)
        }
    }

    # Team metrics
    assignee_counts = Counter()
    assignee_closed = Counter()

    for issue in issues:
        assignee = issue.get('assignee', 'Unassigned')
        assignee_counts[assignee] += 1
        if issue['status'] in ['Closed', 'Resolved', 'Done']:
            assignee_closed[assignee] += 1

    metrics['team_metrics'] = {
        'workload_distribution': dict(assignee_counts.most_common(10)),
        'closure_by_assignee': dict(assignee_closed.most_common(10))
    }

    # Quality metrics
    bug_issues = [i for i in issues if i.get('issue_type', '').lower() == 'bug']
    metrics['quality_metrics'] = {
        'total_bugs': len(bug_issues),
        'open_bugs': len([i for i in bug_issues if i['status'] not in ['Closed', 'Resolved', 'Done']]),
        'bug_ratio': round(len(bug_issues) / len(issues) * 100, 1) if issues else 0
    }

    return metrics


def save_metrics(metrics, output_dir):
    """Save metrics to JSON files for dashboard consumption."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save complete metrics
    with open(output_path / 'metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)

    # Save separate files for easier consumption
    with open(output_path / 'summary.json', 'w') as f:
        json.dump({
            'generated_at': metrics['generated_at'],
            'summary': metrics['summary']
        }, f, indent=2)

    with open(output_path / 'time_series.json', 'w') as f:
        json.dump(metrics['time_series'], f, indent=2)

    with open(output_path / 'packages.json', 'w') as f:
        json.dump(metrics['package_metrics'], f, indent=2)

    print(f"✓ Metrics saved to {output_path}")


def main():
    """Main execution function."""
    print("="*80)
    print("JIRA METRICS EXTRACTION")
    print("="*80)
    print()

    # Load configuration
    print("Loading configuration...")
    config = load_config()

    # Initialize collector
    print("Initializing Jira collector...")
    jira_config = config.get('jira', {})
    collector = JiraCollector(jira_config)

    # Get date range (last 90 days)
    lookback_days = 90
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)

    print(f"Collecting issues from {start_date.date()} to {end_date.date()}...")

    # Collect issues
    issues = collector.collect(start_date, end_date)
    print(f"✓ Collected {len(issues)} issues")
    print()

    # Extract metrics
    print("Extracting metrics...")
    metrics = extract_metrics(issues)
    print()

    # Display summary
    print("SUMMARY METRICS:")
    print(f"  Total Issues: {metrics['summary']['total']}")
    print(f"  Open: {metrics['summary']['open']} ({metrics['summary']['open_percentage']}%)")
    print(f"  Closed: {metrics['summary']['closed']}")
    if 'avg_time_to_close_days' in metrics['summary']:
        print(f"  Avg Time to Close: {metrics['summary']['avg_time_to_close_days']} days")
    print()

    print("TOP PACKAGES:")
    for pkg, count in list(metrics['package_metrics']['top_packages'].items())[:5]:
        print(f"  {pkg}: {count} mentions")
    print()

    print("TOP ASSIGNEES:")
    for assignee, count in list(metrics['team_metrics']['workload_distribution'].items())[:5]:
        print(f"  {assignee}: {count} issues")
    print()

    # Save metrics
    output_dir = Path(__file__).parent.parent / 'dashboard' / 'data'
    save_metrics(metrics, output_dir)

    print()
    print("="*80)
    print(f"✓ Metrics extraction complete!")
    print(f"✓ Data ready for dashboard at: {output_dir}")
    print("="*80)


if __name__ == '__main__':
    main()
