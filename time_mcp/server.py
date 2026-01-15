import json
from typing import Optional
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP(
    name="Time & Scheduler Tool",
)

# Constants
DEFAULT_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
ISO_FORMAT = "%Y-%m-%dT%H:%M:%S"


# ============================================================================
# Utility Functions
# ============================================================================

def json_error(message: str) -> str:
    """
    Create a standardized JSON error response.
    
    Args:
        message: Error message
        
    Returns:
        JSON string with error
    """
    return json.dumps({"error": message}, indent=2)


def json_success(message: str, **kwargs) -> str:
    """
    Create a standardized JSON success response.
    
    Args:
        message: Success message
        **kwargs: Additional data to include
        
    Returns:
        JSON string with success and data
    """
    result = {"success": True, "message": message, **kwargs}
    return json.dumps(result, indent=2)


def get_timezone_info(timezone: str) -> Optional[ZoneInfo]:
    """
    Get ZoneInfo object for a timezone string.
    
    Args:
        timezone: Timezone string (e.g., 'UTC', 'America/New_York', 'Europe/London')
        
    Returns:
        ZoneInfo object or None if invalid
    """
    try:
        return ZoneInfo(timezone)
    except Exception:
        return None


# ============================================================================
# Time & Scheduler Tool Functions
# ============================================================================

@mcp.tool()
def current_time(timezone: Optional[str] = None, format: Optional[str] = None) -> str:
    """
    Get the current time. Useful for SLA checks and time-based decisions.
    
    Args:
        timezone: Optional timezone (e.g., 'UTC', 'America/New_York'). Defaults to system timezone.
        format: Optional time format string. Defaults to ISO format with timezone.
        
    Returns:
        JSON string containing current time information
    """
    try:
        # Get current time
        if timezone:
            tz = get_timezone_info(timezone)
            if tz is None:
                return json_error(f"Invalid timezone: {timezone}")
            now = datetime.now(tz)
        else:
            now = datetime.now()
        
        # Format time
        if format:
            try:
                time_str = now.strftime(format)
            except ValueError as e:
                return json_error(f"Invalid format string: {str(e)}")
        else:
            # Default ISO format with timezone
            if now.tzinfo:
                time_str = now.isoformat()
            else:
                time_str = now.strftime(ISO_FORMAT)
        
        result = {
            "current_time": time_str,
            "timezone": str(now.tzinfo) if now.tzinfo else "system",
            "timestamp": now.timestamp(),
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "hour": now.hour,
            "minute": now.minute,
            "second": now.second,
            "weekday": now.strftime("%A"),
            "iso_format": now.isoformat(),
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        return json_error(f"Error getting current time: {str(e)}")


@mcp.tool()
def convert_timezone(
    time_str: str,
    from_timezone: str,
    to_timezone: str,
    format: Optional[str] = None
) -> str:
    """
    Convert time from one timezone to another. Useful for scheduled workflows and global operations.
    
    Args:
        time_str: Time string to convert (ISO format or specified format)
        from_timezone: Source timezone (e.g., 'UTC', 'America/New_York')
        to_timezone: Target timezone (e.g., 'Europe/London', 'Asia/Tokyo')
        format: Optional format string if time_str is not in ISO format
        
    Returns:
        JSON string containing converted time information
    """
    try:
        # Get timezone objects
        from_tz = get_timezone_info(from_timezone)
        to_tz = get_timezone_info(to_timezone)
        
        if from_tz is None:
            return json_error(f"Invalid source timezone: {from_timezone}")
        if to_tz is None:
            return json_error(f"Invalid target timezone: {to_timezone}")
        
        # Parse time string
        try:
            if format:
                dt = datetime.strptime(time_str, format)
            else:
                # Try ISO format first
                try:
                    dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                except ValueError:
                    # Try common formats
                    for fmt in [ISO_FORMAT, DEFAULT_TIME_FORMAT, "%Y-%m-%d %H:%M:%S"]:
                        try:
                            dt = datetime.strptime(time_str, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        raise ValueError(f"Could not parse time string: {time_str}")
            
            # Localize to source timezone if not already timezone-aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=from_tz)
            else:
                # Convert to source timezone first
                dt = dt.astimezone(from_tz)
            
            # Convert to target timezone
            converted_dt = dt.astimezone(to_tz)
            
            # Calculate time difference (offset difference between timezones)
            time_diff_seconds = (converted_dt.utcoffset() - dt.utcoffset()).total_seconds()
            
            result = {
                "original_time": dt.isoformat(),
                "converted_time": converted_dt.isoformat(),
                "from_timezone": from_timezone,
                "to_timezone": to_timezone,
                "timezone_offset_difference_hours": time_diff_seconds / 3600,
                "formatted_original": dt.strftime(DEFAULT_TIME_FORMAT),
                "formatted_converted": converted_dt.strftime(DEFAULT_TIME_FORMAT),
            }
            
            return json.dumps(result, indent=2)
        
        except ValueError as e:
            return json_error(f"Error parsing time string: {str(e)}")
    
    except Exception as e:
        return json_error(f"Error converting timezone: {str(e)}")


@mcp.tool()
def time_difference(time1: str, time2: str, timezone: Optional[str] = None) -> str:
    """
    Calculate the difference between two times. Useful for SLA checks and duration calculations.
    
    Args:
        time1: First time string (ISO format or system format)
        time2: Second time string (ISO format or system format)
        timezone: Optional timezone for both times if not specified in strings
        
    Returns:
        JSON string containing time difference information
    """
    try:
        # Parse time strings
        def parse_time(ts: str, tz: Optional[ZoneInfo]) -> datetime:
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except ValueError:
                for fmt in [ISO_FORMAT, DEFAULT_TIME_FORMAT, "%Y-%m-%d %H:%M:%S"]:
                    try:
                        dt = datetime.strptime(ts, fmt)
                        if tz and dt.tzinfo is None:
                            dt = dt.replace(tzinfo=tz)
                        return dt
                    except ValueError:
                        continue
                raise ValueError(f"Could not parse time: {ts}")
            return dt
        
        tz = get_timezone_info(timezone) if timezone else None
        
        dt1 = parse_time(time1, tz)
        dt2 = parse_time(time2, tz)
        
        # Calculate difference
        diff = dt2 - dt1
        
        result = {
            "time1": dt1.isoformat(),
            "time2": dt2.isoformat(),
            "difference_seconds": diff.total_seconds(),
            "difference_minutes": diff.total_seconds() / 60,
            "difference_hours": diff.total_seconds() / 3600,
            "difference_days": diff.days,
            "is_negative": diff.total_seconds() < 0,
            "absolute_difference_seconds": abs(diff.total_seconds()),
            "formatted": str(diff),
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        return json_error(f"Error calculating time difference: {str(e)}")


@mcp.tool()
def add_time_duration(
    time_str: str,
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
    timezone: Optional[str] = None
) -> str:
    """
    Add a duration to a time. Useful for scheduled workflows and deadline calculations.
    
    Args:
        time_str: Base time string (ISO format or system format)
        days: Number of days to add
        hours: Number of hours to add
        minutes: Number of minutes to add
        seconds: Number of seconds to add
        timezone: Optional timezone if time_str doesn't include timezone info
        
    Returns:
        JSON string containing the new time
    """
    try:
        # Parse time string
        try:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        except ValueError:
            tz = get_timezone_info(timezone) if timezone else None
            for fmt in [ISO_FORMAT, DEFAULT_TIME_FORMAT, "%Y-%m-%d %H:%M:%S"]:
                try:
                    dt = datetime.strptime(time_str, fmt)
                    if tz and dt.tzinfo is None:
                        dt = dt.replace(tzinfo=tz)
                    break
                except ValueError:
                    continue
            else:
                return json_error(f"Could not parse time string: {time_str}")
        
        # Add duration
        duration = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
        new_time = dt + duration
        
        result = {
            "original_time": dt.isoformat(),
            "new_time": new_time.isoformat(),
            "duration_added": {
                "days": days,
                "hours": hours,
                "minutes": minutes,
                "seconds": seconds,
                "total_seconds": duration.total_seconds(),
            },
            "formatted_original": dt.strftime(DEFAULT_TIME_FORMAT),
            "formatted_new": new_time.strftime(DEFAULT_TIME_FORMAT),
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        return json_error(f"Error adding time duration: {str(e)}")


@mcp.tool()
def check_sla_deadline(
    start_time: str,
    sla_hours: float,
    current_time: Optional[str] = None,
    timezone: Optional[str] = None
) -> str:
    """
    Check if an SLA deadline has been met or exceeded. Useful for SLA monitoring and alerts.
    
    Args:
        start_time: Start time string (ISO format or system format)
        sla_hours: SLA duration in hours
        current_time: Optional current time string. If not provided, uses system time.
        timezone: Optional timezone for times if not specified in strings
        
    Returns:
        JSON string containing SLA status and deadline information
    """
    try:
        # Parse start time
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        except ValueError:
            tz = get_timezone_info(timezone) if timezone else None
            for fmt in [ISO_FORMAT, DEFAULT_TIME_FORMAT, "%Y-%m-%d %H:%M:%S"]:
                try:
                    start_dt = datetime.strptime(start_time, fmt)
                    if tz and start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=tz)
                    break
                except ValueError:
                    continue
            else:
                return json_error(f"Could not parse start time: {start_time}")
        
        # Get current time
        if current_time:
            try:
                now_dt = datetime.fromisoformat(current_time.replace('Z', '+00:00'))
            except ValueError:
                tz = get_timezone_info(timezone) if timezone else None
                for fmt in [ISO_FORMAT, DEFAULT_TIME_FORMAT, "%Y-%m-%d %H:%M:%S"]:
                    try:
                        now_dt = datetime.strptime(current_time, fmt)
                        if tz and now_dt.tzinfo is None:
                            now_dt = now_dt.replace(tzinfo=tz)
                        break
                    except ValueError:
                        continue
                else:
                    return json_error(f"Could not parse current time: {current_time}")
        else:
            tz = get_timezone_info(timezone) if timezone else None
            now_dt = datetime.now(tz) if tz else datetime.now()
            if start_dt.tzinfo and now_dt.tzinfo is None:
                now_dt = now_dt.replace(tzinfo=start_dt.tzinfo)
            elif now_dt.tzinfo and start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=now_dt.tzinfo)
        
        # Calculate deadline
        sla_duration = timedelta(hours=sla_hours)
        deadline = start_dt + sla_duration
        
        # Calculate elapsed time
        elapsed = now_dt - start_dt
        remaining = deadline - now_dt
        
        # Check status
        is_met = elapsed.total_seconds() <= sla_duration.total_seconds()
        is_exceeded = remaining.total_seconds() < 0
        
        result = {
            "start_time": start_dt.isoformat(),
            "current_time": now_dt.isoformat(),
            "deadline": deadline.isoformat(),
            "sla_hours": sla_hours,
            "elapsed_hours": elapsed.total_seconds() / 3600,
            "remaining_hours": remaining.total_seconds() / 3600 if remaining.total_seconds() > 0 else 0,
            "sla_met": is_met,
            "sla_exceeded": is_exceeded,
            "status": "exceeded" if is_exceeded else ("met" if is_met else "pending"),
            "percentage_used": min(100, (elapsed.total_seconds() / sla_duration.total_seconds()) * 100),
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        return json_error(f"Error checking SLA deadline: {str(e)}")


if __name__ == "__main__":
    mcp.run()