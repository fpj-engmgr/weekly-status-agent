#!/usr/bin/env python
"""Test GitLab integration end-to-end."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils import load_env_vars, get_date_range
from collectors.gitlab_collector import GitLabCollector
from processors.data_processor import DataProcessor
import yaml

def test_gitlab_integration():
    """Test GitLab data collection and processing."""

    print("=" * 70)
    print("GITLAB INTEGRATION TEST")
    print("=" * 70)
    print()

    # Load environment
    load_env_vars()

    # Load config
    with open('config/config.yaml') as f:
        config = yaml.safe_load(f)

    gitlab_config = config.get('gitlab', {})

    # Check if GitLab is configured
    if not gitlab_config.get('projects') and not gitlab_config.get('project_prefixes'):
        print("⚠️  GitLab not configured in config.yaml")
        print()
        print("To test GitLab integration:")
        print("1. Add projects or project_prefixes to config.yaml")
        print("2. Re-run this test")
        print()
        return

    print("Step 1: Collecting GitLab MRs...")
    print("-" * 70)

    try:
        collector = GitLabCollector(gitlab_config)
        start_date, end_date = get_date_range(7, 'UTC')

        print(f"Date range: {start_date.date()} to {end_date.date()}")
        if gitlab_config.get('projects'):
            print(f"Projects: {gitlab_config.get('projects')}")
        if gitlab_config.get('project_prefixes'):
            print(f"Project prefixes: {gitlab_config.get('project_prefixes')}")
        print()

        gitlab_data = collector.collect(start_date, end_date)
        print(f"✓ Collected {len(gitlab_data)} MRs")
        print()

        if gitlab_data:
            print("Sample MRs:")
            for mr in gitlab_data[:3]:
                print(f"  !{mr['mr_iid']}: {mr['title']}")
                print(f"    Project: {mr['project_name']}")
                print(f"    State: {mr['state']} | Author: {mr['author']}")
                if mr['state'] == 'merged':
                    print(f"    Merged by: {mr.get('merged_by', 'Unknown')}")
                print()

    except Exception as e:
        print(f"❌ Error collecting GitLab data: {e}")
        import traceback
        traceback.print_exc()
        return

    print("Step 2: Processing GitLab data...")
    print("-" * 70)

    try:
        processor = DataProcessor(config.get('database', {}))

        # Process with empty data for other sources
        processed = processor.process(
            gmail_data=[],
            jira_data=[],
            gdrive_data=[],
            gitlab_data=gitlab_data
        )

        gitlab_summary = processed['gitlab']
        print(f"✓ Processed {gitlab_summary['total_count']} MRs")
        print()

        print("Summary:")
        print(f"  Total: {gitlab_summary['total_count']}")
        print(f"  Merged this period: {len(gitlab_summary['merged_this_period'])}")
        print(f"  Ready for review: {len(gitlab_summary['ready_for_review'])}")
        print(f"  Stale MRs: {len(gitlab_summary['stale_mrs'])}")
        print(f"  By state: {dict([(k, len(v)) for k, v in gitlab_summary['by_state'].items()])}")
        print()

        if gitlab_summary['merged_this_period']:
            print("Merged MRs:")
            for mr in gitlab_summary['merged_this_period'][:3]:
                print(f"  !{mr['mr_iid']}: {mr['title']}")

    except Exception as e:
        print(f"❌ Error processing GitLab data: {e}")
        import traceback
        traceback.print_exc()
        return

    print()
    print("=" * 70)
    print("✅ GITLAB INTEGRATION TEST COMPLETE")
    print("=" * 70)
    print()
    print("GitLab integration is working correctly!")
    print("Next step: Run full report generation with:")
    print("  python src/main.py --dry-run")

if __name__ == "__main__":
    test_gitlab_integration()
