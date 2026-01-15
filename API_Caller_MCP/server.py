"""Goal: Make agents useful in real workflows."""
import json
import time
from collections import defaultdict
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
try:
    from urllib3.util.retry import Retry
except ImportError:
    from requests.packages.urllib3.util.retry import Retry
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP(
    name="API Caller Tool",
)

# Constants
DEFAULT_TIMEOUT = 30  # seconds
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BACKOFF_FACTOR = 1
RATE_LIMIT_WINDOW = 60  # seconds
MAX_REQUESTS_PER_WINDOW = 100  # per domain

# Rate limiting tracking
rate_limit_tracker: Dict[str, list] = defaultdict(list)


# ============================================================================
# Utility Functions
# ============================================================================

def json_error(message: str, **kwargs) -> str:
    """
    Create a standardized JSON error response.
    
    Args:
        message: Error message
        **kwargs: Additional error data
        
    Returns:
        JSON string with error
    """
    result = {"error": message, **kwargs}
    return json.dumps(result, indent=2)


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


def check_rate_limit(url: str) -> tuple[bool, Optional[str]]:
    """
    Check if request is within rate limit.
    
    Args:
        url: Request URL
        
    Returns:
        Tuple of (allowed, error_message)
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split('/')[0]
        
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW
        
        # Clean old entries
        rate_limit_tracker[domain] = [
            ts for ts in rate_limit_tracker[domain] if ts > window_start
        ]
        
        # Check limit
        if len(rate_limit_tracker[domain]) >= MAX_REQUESTS_PER_WINDOW:
            return False, f"Rate limit exceeded for {domain}. Max {MAX_REQUESTS_PER_WINDOW} requests per {RATE_LIMIT_WINDOW} seconds."
        
        # Record request
        rate_limit_tracker[domain].append(now)
        return True, None
    
    except Exception as e:
        # Don't block on rate limit errors
        return True, None


def create_session(
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_RETRY_BACKOFF_FACTOR
) -> requests.Session:
    """
    Create a requests session with retry strategy and timeout.
    
    Args:
        timeout: Request timeout in seconds
        max_retries: Maximum number of retries
        backoff_factor: Backoff factor for retries
        
    Returns:
        Configured requests.Session
    """
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


def prepare_headers(headers: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """
    Prepare headers for request.
    
    Args:
        headers: Optional headers dictionary
        
    Returns:
        Prepared headers dictionary
    """
    default_headers = {
        "User-Agent": "API-Caller-Tool/1.0",
        "Accept": "application/json",
    }
    
    if headers:
        # Convert all header values to strings
        prepared_headers = {str(k): str(v) for k, v in headers.items()}
        default_headers.update(prepared_headers)
    
    return default_headers


def prepare_body(body: Optional[Any] = None, content_type: Optional[str] = None) -> tuple[Optional[Any], Optional[str]]:
    """
    Prepare request body based on content type.
    
    Args:
        body: Request body (dict, str, or None)
        content_type: Content type hint
        
    Returns:
        Tuple of (prepared_body, final_content_type)
    """
    if body is None:
        return None, None
    
    # Determine content type
    if content_type:
        final_content_type = content_type
    elif isinstance(body, dict):
        final_content_type = "application/json"
    elif isinstance(body, str):
        final_content_type = "text/plain"
    else:
        final_content_type = "application/json"
    
    # Prepare body based on content type
    if final_content_type == "application/json" and isinstance(body, dict):
        return json.dumps(body), final_content_type
    elif isinstance(body, str):
        return body, final_content_type
    else:
        # Try to serialize as JSON
        try:
            return json.dumps(body), "application/json"
        except (TypeError, ValueError):
            return str(body), "text/plain"


# ============================================================================
# HTTP / API Caller Tool Functions
# ============================================================================

@mcp.tool()
def get(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    params: Optional[Dict[str, Any]] = None
) -> str:
    """
    Make a GET request to an API endpoint. Useful for fetching data from SaaS integrations.
    
    Args:
        url: API endpoint URL
        headers: Optional HTTP headers dictionary
        timeout: Request timeout in seconds (default: 30)
        params: Optional query parameters dictionary
        
    Returns:
        JSON string containing response data and metadata
    """
    try:
        # Validate URL
        if not url or not url.startswith(('http://', 'https://')):
            return json_error("Invalid URL. Must start with http:// or https://")
        
        # Check rate limit
        allowed, error_msg = check_rate_limit(url)
        if not allowed:
            return json_error(error_msg or "Rate limit exceeded")
        
        # Prepare headers
        prepared_headers = prepare_headers(headers)
        
        # Create session with retry strategy
        session = create_session(timeout=timeout)
        
        # Make request
        start_time = time.time()
        try:
            response = session.get(
                url,
                headers=prepared_headers,
                params=params,
                timeout=timeout
            )
            elapsed_time = time.time() - start_time
            
            # Parse response
            try:
                response_data = response.json()
            except ValueError:
                response_data = response.text
            
            result = {
                "success": response.ok,
                "status_code": response.status_code,
                "url": url,
                "method": "GET",
                "headers_sent": prepared_headers,
                "response_headers": dict(response.headers),
                "response_data": response_data,
                "elapsed_time_seconds": round(elapsed_time, 3),
                "content_type": response.headers.get("Content-Type", "unknown"),
                "content_length": len(response.content) if response.content else 0,
            }
            
            if not response.ok:
                result["error"] = f"HTTP {response.status_code}: {response.reason}"
            
            return json.dumps(result, indent=2, default=str)
        
        except requests.exceptions.Timeout:
            return json_error(f"Request timeout after {timeout} seconds", url=url)
        except requests.exceptions.ConnectionError as e:
            return json_error(f"Connection error: {str(e)}", url=url)
        except requests.exceptions.RequestException as e:
            return json_error(f"Request error: {str(e)}", url=url)
        finally:
            session.close()
    
    except Exception as e:
        return json_error(f"Error making GET request: {str(e)}", url=url)


@mcp.tool()
def post(
    url: str,
    body: Optional[Any] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    content_type: Optional[str] = None
) -> str:
    """
    Make a POST request to an API endpoint. Useful for creating resources and webhooks.
    
    Args:
        url: API endpoint URL
        body: Request body (dict for JSON, str for text, etc.)
        headers: Optional HTTP headers dictionary
        timeout: Request timeout in seconds (default: 30)
        content_type: Optional content type (defaults to application/json for dicts)
        
    Returns:
        JSON string containing response data and metadata
    """
    try:
        # Validate URL
        if not url or not url.startswith(('http://', 'https://')):
            return json_error("Invalid URL. Must start with http:// or https://")
        
        # Check rate limit
        allowed, error_msg = check_rate_limit(url)
        if not allowed:
            return json_error(error_msg or "Rate limit exceeded")
        
        # Prepare headers and body
        prepared_body, final_content_type = prepare_body(body, content_type)
        prepared_headers = prepare_headers(headers)
        
        if final_content_type:
            prepared_headers["Content-Type"] = final_content_type
        
        # Create session with retry strategy
        session = create_session(timeout=timeout)
        
        # Make request
        start_time = time.time()
        try:
            response = session.post(
                url,
                data=prepared_body,
                headers=prepared_headers,
                timeout=timeout
            )
            elapsed_time = time.time() - start_time
            
            # Parse response
            try:
                response_data = response.json()
            except ValueError:
                response_data = response.text
            
            result = {
                "success": response.ok,
                "status_code": response.status_code,
                "url": url,
                "method": "POST",
                "headers_sent": prepared_headers,
                "body_sent": body,
                "response_headers": dict(response.headers),
                "response_data": response_data,
                "elapsed_time_seconds": round(elapsed_time, 3),
                "content_type": response.headers.get("Content-Type", "unknown"),
                "content_length": len(response.content) if response.content else 0,
            }
            
            if not response.ok:
                result["error"] = f"HTTP {response.status_code}: {response.reason}"
            
            return json.dumps(result, indent=2, default=str)
        
        except requests.exceptions.Timeout:
            return json_error(f"Request timeout after {timeout} seconds", url=url)
        except requests.exceptions.ConnectionError as e:
            return json_error(f"Connection error: {str(e)}", url=url)
        except requests.exceptions.RequestException as e:
            return json_error(f"Request error: {str(e)}", url=url)
        finally:
            session.close()
    
    except Exception as e:
        return json_error(f"Error making POST request: {str(e)}", url=url)


@mcp.tool()
def put(
    url: str,
    body: Optional[Any] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    content_type: Optional[str] = None
) -> str:
    """
    Make a PUT request to an API endpoint. Useful for updating resources.
    
    Args:
        url: API endpoint URL
        body: Request body (dict for JSON, str for text, etc.)
        headers: Optional HTTP headers dictionary
        timeout: Request timeout in seconds (default: 30)
        content_type: Optional content type (defaults to application/json for dicts)
        
    Returns:
        JSON string containing response data and metadata
    """
    try:
        # Validate URL
        if not url or not url.startswith(('http://', 'https://')):
            return json_error("Invalid URL. Must start with http:// or https://")
        
        # Check rate limit
        allowed, error_msg = check_rate_limit(url)
        if not allowed:
            return json_error(error_msg or "Rate limit exceeded")
        
        # Prepare headers and body
        prepared_body, final_content_type = prepare_body(body, content_type)
        prepared_headers = prepare_headers(headers)
        
        if final_content_type:
            prepared_headers["Content-Type"] = final_content_type
        
        # Create session with retry strategy
        session = create_session(timeout=timeout)
        
        # Make request
        start_time = time.time()
        try:
            response = session.put(
                url,
                data=prepared_body,
                headers=prepared_headers,
                timeout=timeout
            )
            elapsed_time = time.time() - start_time
            
            # Parse response
            try:
                response_data = response.json()
            except ValueError:
                response_data = response.text
            
            result = {
                "success": response.ok,
                "status_code": response.status_code,
                "url": url,
                "method": "PUT",
                "headers_sent": prepared_headers,
                "body_sent": body,
                "response_headers": dict(response.headers),
                "response_data": response_data,
                "elapsed_time_seconds": round(elapsed_time, 3),
            }
            
            if not response.ok:
                result["error"] = f"HTTP {response.status_code}: {response.reason}"
            
            return json.dumps(result, indent=2, default=str)
        
        except requests.exceptions.Timeout:
            return json_error(f"Request timeout after {timeout} seconds", url=url)
        except requests.exceptions.RequestException as e:
            return json_error(f"Request error: {str(e)}", url=url)
        finally:
            session.close()
    
    except Exception as e:
        return json_error(f"Error making PUT request: {str(e)}", url=url)


@mcp.tool()
def delete(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT
) -> str:
    """
    Make a DELETE request to an API endpoint. Useful for deleting resources.
    
    Args:
        url: API endpoint URL
        headers: Optional HTTP headers dictionary
        timeout: Request timeout in seconds (default: 30)
        
    Returns:
        JSON string containing response data and metadata
    """
    try:
        # Validate URL
        if not url or not url.startswith(('http://', 'https://')):
            return json_error("Invalid URL. Must start with http:// or https://")
        
        # Check rate limit
        allowed, error_msg = check_rate_limit(url)
        if not allowed:
            return json_error(error_msg or "Rate limit exceeded")
        
        # Prepare headers
        prepared_headers = prepare_headers(headers)
        
        # Create session with retry strategy
        session = create_session(timeout=timeout)
        
        # Make request
        start_time = time.time()
        try:
            response = session.delete(
                url,
                headers=prepared_headers,
                timeout=timeout
            )
            elapsed_time = time.time() - start_time
            
            # Parse response
            try:
                response_data = response.json()
            except ValueError:
                response_data = response.text
            
            result = {
                "success": response.ok,
                "status_code": response.status_code,
                "url": url,
                "method": "DELETE",
                "headers_sent": prepared_headers,
                "response_headers": dict(response.headers),
                "response_data": response_data,
                "elapsed_time_seconds": round(elapsed_time, 3),
            }
            
            if not response.ok:
                result["error"] = f"HTTP {response.status_code}: {response.reason}"
            
            return json.dumps(result, indent=2, default=str)
        
        except requests.exceptions.Timeout:
            return json_error(f"Request timeout after {timeout} seconds", url=url)
        except requests.exceptions.RequestException as e:
            return json_error(f"Request error: {str(e)}", url=url)
        finally:
            session.close()
    
    except Exception as e:
        return json_error(f"Error making DELETE request: {str(e)}", url=url)


@mcp.tool()
def patch(
    url: str,
    body: Optional[Any] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    content_type: Optional[str] = None
) -> str:
    """
    Make a PATCH request to an API endpoint. Useful for partial updates.
    
    Args:
        url: API endpoint URL
        body: Request body (dict for JSON, str for text, etc.)
        headers: Optional HTTP headers dictionary
        timeout: Request timeout in seconds (default: 30)
        content_type: Optional content type (defaults to application/json for dicts)
        
    Returns:
        JSON string containing response data and metadata
    """
    try:
        # Validate URL
        if not url or not url.startswith(('http://', 'https://')):
            return json_error("Invalid URL. Must start with http:// or https://")
        
        # Check rate limit
        allowed, error_msg = check_rate_limit(url)
        if not allowed:
            return json_error(error_msg or "Rate limit exceeded")
        
        # Prepare headers and body
        prepared_body, final_content_type = prepare_body(body, content_type)
        prepared_headers = prepare_headers(headers)
        
        if final_content_type:
            prepared_headers["Content-Type"] = final_content_type
        
        # Create session with retry strategy
        session = create_session(timeout=timeout)
        
        # Make request
        start_time = time.time()
        try:
            response = session.patch(
                url,
                data=prepared_body,
                headers=prepared_headers,
                timeout=timeout
            )
            elapsed_time = time.time() - start_time
            
            # Parse response
            try:
                response_data = response.json()
            except ValueError:
                response_data = response.text
            
            result = {
                "success": response.ok,
                "status_code": response.status_code,
                "url": url,
                "method": "PATCH",
                "headers_sent": prepared_headers,
                "body_sent": body,
                "response_headers": dict(response.headers),
                "response_data": response_data,
                "elapsed_time_seconds": round(elapsed_time, 3),
            }
            
            if not response.ok:
                result["error"] = f"HTTP {response.status_code}: {response.reason}"
            
            return json.dumps(result, indent=2, default=str)
        
        except requests.exceptions.Timeout:
            return json_error(f"Request timeout after {timeout} seconds", url=url)
        except requests.exceptions.RequestException as e:
            return json_error(f"Request error: {str(e)}", url=url)
        finally:
            session.close()
    
    except Exception as e:
        return json_error(f"Error making PATCH request: {str(e)}", url=url)


if __name__ == "__main__":
    mcp.run()
