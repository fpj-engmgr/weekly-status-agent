"""Main entry point for the Weekly Status Report Agent."""

import argparse
import sys
from pathlib import Path
from typing import Optional
import yaml

from utils import setup_logging, load_env_vars, get_date_range, format_date_for_display


def load_config(config_path: str = "config/config.yaml") -> dict:
    """Load configuration from YAML file.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Configuration dictionary
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            "Please copy config/config.example.yaml to config/config.yaml and customize it."
        )
    
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    return config


def generate_report(config: dict, test_mode: bool = False, dry_run: bool = False) -> bool:
    """Generate the weekly status report.
    
    Args:
        config: Configuration dictionary
        test_mode: If True, run in test mode
        dry_run: If True, don't create actual document
        
    Returns:
        True if successful, False otherwise
    """
    from collectors.gmail_collector import GmailCollector
    from collectors.jira_collector import JiraCollector
    from collectors.gdrive_collector import GDriveCollector
    from processors.data_processor import DataProcessor
    from ai.summarizer import AISummarizer
    from generators.doc_generator import DocGenerator
    
    logger = setup_logging(config.get("logging", {}))
    logger.info("Starting weekly status report generation")
    
    try:
        # Get date range
        timezone = config.get("schedule", {}).get("timezone", "UTC")
        lookback_days = config.get("gmail", {}).get("lookback_days", 7)
        start_date, end_date = get_date_range(lookback_days, timezone)
        
        logger.info(f"Report period: {format_date_for_display(start_date)} to {format_date_for_display(end_date)}")
        
        # Initialize collectors
        logger.info("Initializing data collectors...")
        gmail_collector = GmailCollector(config.get("gmail", {}))
        jira_collector = JiraCollector(config.get("jira", {}))
        gdrive_collector = GDriveCollector(config.get("gdrive", {}))
        
        # Collect data
        logger.info("Collecting Gmail data...")
        gmail_data = gmail_collector.collect(start_date, end_date)
        logger.info(f"Collected {len(gmail_data)} emails")
        
        logger.info("Collecting Jira data...")
        jira_data = jira_collector.collect(start_date, end_date)
        logger.info(f"Collected {len(jira_data)} Jira issues")
        
        logger.info("Collecting Google Drive data...")
        gdrive_data = gdrive_collector.collect(start_date, end_date)
        logger.info(f"Collected {len(gdrive_data)} Drive file updates")
        
        # Process data
        logger.info("Processing collected data...")
        processor = DataProcessor(config.get("database", {}))
        processed_data = processor.process(
            gmail_data=gmail_data,
            jira_data=jira_data,
            gdrive_data=gdrive_data
        )
        
        # AI Analysis
        logger.info("Analyzing data with AI...")
        summarizer = AISummarizer(config.get("ai", {}))
        analysis = summarizer.analyze(processed_data, start_date, end_date)
        logger.info("AI analysis complete")
        
        if dry_run:
            logger.info("Dry run mode - skipping document generation")
            logger.info(f"Analysis preview: {analysis.get('executive_summary', '')[:200]}...")
            return True
        
        # Generate report
        logger.info("Generating Google Doc report...")
        generator = DocGenerator(config.get("output", {}))
        doc_url = generator.create_report(analysis, start_date, end_date)
        
        logger.info(f"Report generated successfully: {doc_url}")
        
        # Send notification if configured
        if config.get("output", {}).get("send_email_notification", False):
            notification_email = config.get("output", {}).get("notification_email")
            if notification_email:
                logger.info(f"Sending notification to {notification_email}")
                # Email notification would be implemented here
        
        return True
        
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        return False


def run_daemon(config: dict) -> None:
    """Run the agent in daemon mode with scheduling.
    
    Args:
        config: Configuration dictionary
    """
    from scheduler.task_scheduler import TaskScheduler
    
    logger = setup_logging(config.get("logging", {}))
    logger.info("Starting agent in daemon mode")
    
    scheduler = TaskScheduler(config)
    scheduler.start(lambda: generate_report(config))


def main() -> int:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Weekly Status Report Agent - Automated report generation from Gmail, Jira, and Google Drive"
    )
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Path to configuration file (default: config/config.yaml)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process data but don't create document"
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run in daemon mode with scheduling"
    )
    
    args = parser.parse_args()
    
    try:
        # Load environment variables
        load_env_vars()
        
        # Load configuration
        config = load_config(args.config)
        
        if args.daemon:
            run_daemon(config)
        else:
            success = generate_report(config, test_mode=args.test, dry_run=args.dry_run)
            return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
