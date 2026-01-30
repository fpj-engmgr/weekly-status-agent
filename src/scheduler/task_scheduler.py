"""Task scheduler for automated report generation."""

import logging
import time
from datetime import datetime
from typing import Callable
import schedule
import pytz


class TaskScheduler:
    """Manages scheduled execution of the report generation."""
    
    def __init__(self, config: dict):
        """Initialize task scheduler.
        
        Args:
            config: Full configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        schedule_config = config.get("schedule", {})
        self.day = schedule_config.get("day", "Friday")
        self.time = schedule_config.get("time", "17:00")
        self.timezone = schedule_config.get("timezone", "UTC")
        
        # Validate timezone
        try:
            self.tz = pytz.timezone(self.timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            self.logger.warning(f"Unknown timezone {self.timezone}, using UTC")
            self.tz = pytz.UTC
    
    def _get_schedule_function(self, day: str):
        """Get the appropriate schedule function for the day.
        
        Args:
            day: Day of week (e.g., "Monday", "Friday")
            
        Returns:
            schedule day function
        """
        day_map = {
            "monday": schedule.every().monday,
            "tuesday": schedule.every().tuesday,
            "wednesday": schedule.every().wednesday,
            "thursday": schedule.every().thursday,
            "friday": schedule.every().friday,
            "saturday": schedule.every().saturday,
            "sunday": schedule.every().sunday
        }
        
        day_lower = day.lower()
        if day_lower in day_map:
            return day_map[day_lower]
        else:
            self.logger.warning(f"Unknown day {day}, defaulting to Friday")
            return schedule.every().friday
    
    def schedule_task(self, task: Callable):
        """Schedule the task to run weekly.
        
        Args:
            task: Function to execute on schedule
        """
        day_schedule = self._get_schedule_function(self.day)
        day_schedule.at(self.time).do(task)
        
        self.logger.info(f"Task scheduled for every {self.day} at {self.time} ({self.timezone})")
    
    def start(self, task: Callable):
        """Start the scheduler in daemon mode.
        
        Args:
            task: Function to execute on schedule
        """
        self.logger.info("Starting task scheduler")
        
        # Schedule the task
        self.schedule_task(task)
        
        # Run immediately on first start (optional)
        # Uncomment the next line if you want to run immediately when daemon starts
        # task()
        
        # Keep running
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            self.logger.info("Scheduler stopped by user")
    
    def run_once(self, task: Callable):
        """Run the task once immediately.
        
        Args:
            task: Function to execute
        """
        self.logger.info("Running task once")
        task()
