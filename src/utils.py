"""Utility functions for the weekly status agent."""

import os
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
import pytz


def setup_logging(config: dict) -> logging.Logger:
    """Set up logging configuration.
    
    Args:
        config: Logging configuration from config.yaml
        
    Returns:
        Configured logger instance
    """
    log_level = getattr(logging, config.get("level", "INFO"))
    log_file = config.get("file", "logs/agent.log")
    
    # Create logs directory if it doesn't exist
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger("weekly_status_agent")


def get_date_range(lookback_days: int = 7, timezone: str = "UTC") -> tuple[datetime, datetime]:
    """Get start and end dates for the reporting period.
    
    Args:
        lookback_days: Number of days to look back
        timezone: Timezone string (e.g., "America/Los_Angeles")
        
    Returns:
        Tuple of (start_date, end_date) as timezone-aware datetime objects
    """
    tz = pytz.timezone(timezone)
    end_date = datetime.now(tz)
    start_date = end_date - timedelta(days=lookback_days)
    
    return start_date, end_date


def format_date_for_display(date: datetime) -> str:
    """Format date for display in reports.
    
    Args:
        date: Datetime object
        
    Returns:
        Formatted date string (e.g., "Jan 23, 2026")
    """
    return date.strftime("%b %d, %Y")


def ensure_credentials_dir() -> Path:
    """Ensure credentials directory exists.
    
    Returns:
        Path to credentials directory
    """
    creds_dir = Path("config/credentials")
    creds_dir.mkdir(parents=True, exist_ok=True)
    return creds_dir


def load_env_vars() -> None:
    """Load environment variables from .env file."""
    from dotenv import load_dotenv
    load_dotenv()


def get_env_var(name: str, required: bool = True) -> Optional[str]:
    """Get environment variable with validation.
    
    Args:
        name: Environment variable name
        required: Whether the variable is required
        
    Returns:
        Environment variable value or None
        
    Raises:
        ValueError: If required variable is not set
    """
    value = os.getenv(name)
    
    if required and not value:
        raise ValueError(f"Required environment variable {name} is not set")
    
    return value
