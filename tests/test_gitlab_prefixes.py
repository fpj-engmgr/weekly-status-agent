#!/usr/bin/env python
"""Test GitLab project prefix matching."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils import load_env_vars
from collectors.gitlab_collector import GitLabCollector
import yaml

def test_prefix_matching():
    """Test that project_prefixes correctly matches subprojects."""

    print("=" * 70)
    print("GITLAB PROJECT PREFIX MATCHING TEST")
    print("=" * 70)
    print()

    # Load environment
    load_env_vars()

    # Test configuration with prefixes
    test_config = {
        "project_prefixes": ["redhat/rhel-ai/core"],
        "states": ["opened", "merged"],
        "lookback_days": 7,
        "max_mrs_per_project": 10,
    }

    print("Test Configuration:")
    print(f"  Project Prefixes: {test_config['project_prefixes']}")
    print()

    try:
        collector = GitLabCollector(test_config)

        # Resolve projects from prefixes
        matched_projects = collector._resolve_projects_from_prefixes()

        print(f"✓ Found {len(matched_projects)} projects matching prefixes")
        print()

        if matched_projects:
            print("Matched Projects (first 20):")
            for i, proj in enumerate(matched_projects[:20], 1):
                print(f"  {i}. {proj}")

            print()
            print("Summary by namespace:")
            namespaces = {}
            for proj in matched_projects:
                # Get second-level namespace (e.g., "tools", "mirrors")
                parts = proj.split('/')
                if len(parts) >= 4:
                    ns = '/'.join(parts[:4])  # redhat/rhel-ai/core/tools
                    namespaces[ns] = namespaces.get(ns, 0) + 1

            for ns, count in sorted(namespaces.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {ns}/... : {count} projects")

        else:
            print("⚠️  No projects matched the prefixes")

        print()
        print("=" * 70)
        print("✅ PREFIX MATCHING TEST COMPLETE")
        print("=" * 70)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_prefix_matching()
