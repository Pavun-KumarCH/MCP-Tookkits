"""Email Operations Tool for Gmail/SMTP - Production ready."""
import os
import re
import json
import email
import imaplib
import smtplib
from pathlib import Path
from dotenv import load_dotenv
from email import encoders
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.header import decode_header
from email.utils import parsedate_to_datetime
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, List, Any, Tuple

from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Initialize the MCP server
mcp = FastMCP(
    name="Email Operations Tool",
)
# Constants
DEFAULT_IMAP_PORT = 993
DEFAULT_SMTP_PORT = 587
GMAIL_IMAP_SERVER = "imap.gmail.com"
GMAIL_SMTP_SERVER = "smtp.gmail.com"

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


def decode_mime_words(s: str) -> str:
    """
    Decode MIME encoded words in email headers.
    
    Args:
        s: String to decode
        
    Returns:
        Decoded string
    """
    if not s:
        return ""
    decoded_parts = decode_header(s)
    decoded_str = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            decoded_str += part.decode(encoding or 'utf-8', errors='ignore')
        else:
            decoded_str += part
    return decoded_str


def parse_imap_query(query: str) -> tuple[str, bool]:
    """
    Parse and convert user-friendly query to IMAP search criteria.
    Supports Gmail X-GM-RAW syntax and standard IMAP criteria.
    
    Args:
        query: User query string
        
    Returns:
        Tuple of (formatted_query, use_gmail_raw)
    """
    query = query.strip()
    
    # Check if it's already a Gmail X-GM-RAW query (starts with special chars or contains Gmail syntax)
    gmail_syntax_indicators = ['from:', 'to:', 'subject:', 'has:', 'is:', 'in:', 'label:', 'filename:', 'after:', 'before:', 'older:', 'newer:']
    query_lower = query.lower()
    
    # If query contains Gmail-specific syntax, use X-GM-RAW
    if any(indicator in query_lower for indicator in gmail_syntax_indicators):
        return (query, True)
    
    # Try to parse common patterns
    parts = query.split()
    imap_criteria = []
    
    # Handle simple keywords
    keyword_map = {
        'unseen': 'UNSEEN',
        'seen': 'SEEN',
        'read': 'SEEN',
        'unread': 'UNSEEN',
        'flagged': 'FLAGGED',
        'unflagged': 'UNFLAGGED',
        'answered': 'ANSWERED',
        'unanswered': 'UNANSWERED',
        'deleted': 'DELETED',
        'all': 'ALL',
    }
    
    # Check for simple keyword queries
    if len(parts) == 1 and parts[0].lower() in keyword_map:
        return (keyword_map[parts[0].lower()], False)
    
    # Try to parse FROM, TO, SUBJECT patterns
    for part in parts:
        part_lower = part.lower()
        if part_lower.startswith('from:'):
            email = part[5:].strip('"\'')
            imap_criteria.append(f'FROM "{email}"')
        elif part_lower.startswith('to:'):
            email = part[3:].strip('"\'')
            imap_criteria.append(f'TO "{email}"')
        elif part_lower.startswith('subject:'):
            text = part[8:].strip('"\'')
            imap_criteria.append(f'SUBJECT "{text}"')
        elif part_lower.startswith('body:'):
            text = part[5:].strip('"\'')
            imap_criteria.append(f'BODY "{text}"')
        elif part_lower in keyword_map:
            imap_criteria.append(keyword_map[part_lower])
    
    # If we parsed criteria, return them
    if imap_criteria:
        return (' '.join(imap_criteria), False)
    
    # Default: use as-is, but try Gmail X-GM-RAW first
    # For simple text searches, search in subject and body
    return (query, True)


def parse_email_message(msg) -> Dict[str, Any]:
    """
    Parse an email message into a structured dictionary.
    
    Args:
        msg: Email message object
        
    Returns:
        Dictionary with email data
    """
    email_data = {
        "id": None,
        "subject": "",
        "from": "",
        "to": "",
        "cc": "",
        "date": "",
        "body_text": "",
        "body_html": "",
        "attachments": [],
    }
    
    # Get headers
    email_data["subject"] = decode_mime_words(msg.get("Subject", ""))
    email_data["from"] = decode_mime_words(msg.get("From", ""))
    email_data["to"] = decode_mime_words(msg.get("To", ""))
    email_data["cc"] = decode_mime_words(msg.get("Cc", ""))
    
    # Parse date
    date_str = msg.get("Date", "")
    if date_str:
        try:
            email_data["date"] = parsedate_to_datetime(date_str).isoformat()
        except Exception:
            email_data["date"] = date_str
    
    # Parse body and attachments
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            
            # Extract body
            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    body = part.get_payload(decode=True)
                    if body:
                        email_data["body_text"] = body.decode('utf-8', errors='ignore')
                except Exception:
                    pass
            
            elif content_type == "text/html" and "attachment" not in content_disposition:
                try:
                    body = part.get_payload(decode=True)
                    if body:
                        email_data["body_html"] = body.decode('utf-8', errors='ignore')
                except Exception:
                    pass
            
            # Extract attachments
            elif "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                    filename = decode_mime_words(filename)
                    email_data["attachments"].append({
                        "filename": filename,
                        "content_type": content_type,
                        "size": len(part.get_payload(decode=True) or b""),
                    })
    else:
        # Simple email without multipart
        try:
            body = msg.get_payload(decode=True)
            if body:
                content_type = msg.get_content_type()
                if content_type == "text/html":
                    email_data["body_html"] = body.decode('utf-8', errors='ignore')
                else:
                    email_data["body_text"] = body.decode('utf-8', errors='ignore')
        except Exception:
            pass
    
    return email_data


def get_email_credentials() -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Get email credentials from environment variables.
    
    Returns:
        Tuple of (email, password, imap_server, smtp_server)
    """
    email = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD") or os.getenv("EMAIL_APP_PASSWORD")
    imap_server = os.getenv("IMAP_SERVER", GMAIL_IMAP_SERVER)
    smtp_server = os.getenv("SMTP_SERVER", GMAIL_SMTP_SERVER)
    
    return email, password, imap_server, smtp_server


def safe_close_imap(mail: imaplib.IMAP4_SSL, folder_selected: bool = False) -> None:
    """
    Safely close IMAP connection, handling state errors.
    
    Args:
        mail: IMAP connection object
        folder_selected: Whether a folder was successfully selected
    """
    try:
        if folder_selected:
            try:
                mail.close()
            except imaplib.IMAP4.error:
                # Ignore close errors if not in SELECTED state
                pass
    except Exception:
        pass
    
    try:
        mail.logout()
    except Exception:
        # Ignore logout errors
        pass


def connect_imap(
    email_address: Optional[str] = None,
    password: Optional[str] = None,
    imap_server: Optional[str] = None,
    folder: str = "INBOX"
) -> Tuple[imaplib.IMAP4_SSL, bool]:
    """
    Connect to IMAP server and select folder.
    
    Args:
        email_address: Email address (defaults to EMAIL_ADDRESS env var)
        password: Email password/app password (defaults to EMAIL_PASSWORD env var)
        imap_server: IMAP server address (defaults to Gmail IMAP)
        folder: Folder to select (default: 'INBOX')
        
    Returns:
        Tuple of (mail_connection, folder_selected)
        
    Raises:
        ValueError: If credentials are missing
        imaplib.IMAP4.error: If connection fails
    """
    # Get credentials
    if not email_address or not password:
        env_email, env_password, env_imap, _ = get_email_credentials()
        email_address = email_address or env_email
        password = password or env_password
        imap_server = imap_server or env_imap
    
    if not email_address or not password:
        raise ValueError(
            "Email credentials not provided. Set EMAIL_ADDRESS and EMAIL_PASSWORD environment variables, "
            "or provide email_address and password parameters."
        )
    
    if not imap_server:
        imap_server = GMAIL_IMAP_SERVER
    
    # Connect to IMAP server
    mail = imaplib.IMAP4_SSL(imap_server, DEFAULT_IMAP_PORT)
    mail.login(email_address, password)
    status, _ = mail.select(folder)
    
    if status != "OK":
        safe_close_imap(mail, False)
        raise ValueError(f"Failed to select folder '{folder}': {status}")
    
    return mail, True


# ============================================================================
# Email Operations Tool Functions
# ============================================================================

@mcp.tool()
def search_emails(
    query: str,
    folder: str = "INBOX",
    max_results: int = 50,
    email_address: Optional[str] = None,
    password: Optional[str] = None,
    imap_server: Optional[str] = None
) -> str:
    """
    Search emails using a query. Useful for invoice processing and support automation.
    
    Args:
        query: Search query. Supports:
               - Gmail syntax: 'from:email@example.com', 'subject:text', 'is:unread', 'has:attachment'
               - IMAP keywords: 'UNSEEN', 'SEEN', 'FLAGGED', 'ALL'
               - Simple text: searches in subject and body (Gmail only)
        folder: Email folder to search (default: 'INBOX')
        max_results: Maximum number of results to return (default: 50)
        email_address: Email address (defaults to EMAIL_ADDRESS env var)
        password: Email password/app password (defaults to EMAIL_PASSWORD or EMAIL_APP_PASSWORD env var)
        imap_server: IMAP server address (defaults to Gmail IMAP)
        
    Returns:
        JSON string containing list of matching emails with metadata
    """
    try:
        # Connect to IMAP server
        mail = None
        folder_selected = False
        try:
            mail, folder_selected = connect_imap(email_address, password, imap_server, folder)
        except ValueError as e:
            return json_error(str(e))
        except imaplib.IMAP4.error as e:
            return json_error(f"IMAP connection error: {str(e)}")
        except Exception as e:
            return json_error(f"Connection error: {str(e)}")
        
        try:
            # Parse and format query for IMAP
            formatted_query, use_gmail_raw = parse_imap_query(query)
            
            if not formatted_query:
                formatted_query = "ALL"  # Default to all emails
            
            # Search for emails
            # Try Gmail X-GM-RAW first if it's a Gmail server and query suggests it
            if use_gmail_raw and imap_server == GMAIL_IMAP_SERVER:
                try:
                    # Use Gmail's X-GM-RAW for advanced search
                    # Format: search(None, 'X-GM-RAW', 'query string')
                    status, messages = mail.search(None, 'X-GM-RAW', formatted_query)
                    if status != "OK":
                        # Fall back to standard IMAP
                        status, messages = mail.search(None, formatted_query)
                except (imaplib.IMAP4.error, Exception) as e:
                    # Fall back to standard IMAP
                    try:
                        status, messages = mail.search(None, formatted_query)
                    except Exception as fallback_error:
                        safe_close_imap(mail, folder_selected)
                        return json_error(
                            f"Search failed with both Gmail and IMAP syntax. "
                            f"Error: {str(fallback_error)}. "
                            f"Try using: 'ALL', 'UNSEEN', 'from:email@example.com', or 'subject:text'"
                        )
            else:
                # Use standard IMAP search
                try:
                    status, messages = mail.search(None, formatted_query)
                except imaplib.IMAP4.error as e:
                    safe_close_imap(mail, folder_selected)
                    return json_error(
                        f"IMAP search error: {str(e)}. "
                        f"Query: {formatted_query}. "
                        f"Try using: 'ALL', 'UNSEEN', 'SEEN', or Gmail syntax: 'from:email@example.com'"
                    )
            
            if status != "OK":
                safe_close_imap(mail, folder_selected)
                return json_error(
                    f"Search failed: {status}. "
                    f"Query used: {formatted_query}. "
                    f"Try using Gmail search syntax: 'from:email@example.com', 'subject:text', 'is:unread', etc."
                )
            
            email_ids = messages[0].split()
            
            # Limit results
            email_ids = email_ids[-max_results:] if len(email_ids) > max_results else email_ids
            
            results = []
            for email_id_bytes in reversed(email_ids):  # Most recent first
                try:
                    # email_id_bytes is bytes, convert to string for fetch
                    email_id_str = email_id_bytes.decode('utf-8')
                    status, msg_data = mail.fetch(email_id_str, "(RFC822)")
                    if status == "OK":
                        email_body = msg_data[0][1]
                        msg = email.message_from_bytes(email_body)
                        
                        email_info = parse_email_message(msg)
                        email_info["id"] = email_id_str
                        email_info["has_attachments"] = len(email_info["attachments"]) > 0
                        
                        # Remove body content from list view (too large)
                        email_info.pop("body_text", None)
                        email_info.pop("body_html", None)
                        
                        results.append(email_info)
                except Exception as e:
                    # Skip problematic emails
                    continue
            
            safe_close_imap(mail, folder_selected)
            
            return json.dumps({
                "success": True,
                "query": query,
                "folder": folder,
                "total_found": len(email_ids),
                "returned": len(results),
                "emails": results
            }, indent=2, default=str)
        
        except Exception as e:
            safe_close_imap(mail, folder_selected)
            return json_error(f"Error searching emails: {str(e)}")
    
    except Exception as e:
        return json_error(f"Error in search_emails: {str(e)}")


@mcp.tool()
def read_email(
    email_id: str,
    folder: str = "INBOX",
    email_address: Optional[str] = None,
    password: Optional[str] = None,
    imap_server: Optional[str] = None
) -> str:
    """
    Read a specific email by ID. Useful for support automation and detailed email processing.
    
    Args:
        email_id: Email ID (from search_emails results) - must be the numeric 'id' field
        folder: Email folder (default: 'INBOX')
        email_address: Email address (defaults to EMAIL_ADDRESS env var)
        password: Email password/app password (defaults to EMAIL_PASSWORD or EMAIL_APP_PASSWORD env var)
        imap_server: IMAP server address (defaults to Gmail IMAP)
        
    Returns:
        JSON string containing full email content including body and attachments list
    """
    try:
        # Get credentials
        if not email_address or not password:
            env_email, env_password, env_imap, _ = get_email_credentials()
            email_address = email_address or env_email
            password = password or env_password
            imap_server = imap_server or env_imap
        
        if not email_address or not password:
            return json_error(
                "Email credentials not provided. Set EMAIL_ADDRESS and EMAIL_PASSWORD environment variables, "
                "or provide email_address and password parameters."
            )
        
        if not imap_server:
            imap_server = GMAIL_IMAP_SERVER
        
        # Connect to IMAP server
        mail = None
        folder_selected = False
        try:
            mail = imaplib.IMAP4_SSL(imap_server, DEFAULT_IMAP_PORT)
            mail.login(email_address, password)
            status, _ = mail.select(folder)
            if status != "OK":
                safe_close_imap(mail, False)
                return json_error(f"Failed to select folder '{folder}': {status}")
            folder_selected = True
        except imaplib.IMAP4.error as e:
            if mail:
                safe_close_imap(mail, False)
            return json_error(f"IMAP connection error: {str(e)}")
        except Exception as e:
            if mail:
                safe_close_imap(mail, False)
            return json_error(f"Connection error: {str(e)}")
        
        try:
            # Fetch email - email_id should be a string message number from search_emails results
            # Validate that it's not an email address
            email_id_str = str(email_id).strip()
            
            # Check if it looks like an email address instead of a message ID
            if '@' in email_id_str:
                safe_close_imap(mail, folder_selected)
                return json_error(
                    f"Invalid email_id: '{email_id}' appears to be an email address, not a message ID. "
                    f"To read emails from this address:\n"
                    f"1. First use search_emails('from:{email_id}') to find emails\n"
                    f"2. Then use read_email() with the 'id' field from the search results\n"
                    f"Example: search_emails('from:{email_id}') returns emails with 'id' fields, use those IDs."
                )
            
            # Extract numeric message number
            match = re.match(r'^(\d+)', email_id_str)
            if not match:
                safe_close_imap(mail, folder_selected)
                return json_error(
                    f"Invalid email_id format: '{email_id}' is not a valid message number. "
                    f"Email IDs must be numeric (e.g., '1', '2', '123'). "
                    f"Get the 'id' field from search_emails() results."
                )
            
            msg_num = match.group(1)
            
            # Try fetching with the message number
            try:
                status, msg_data = mail.fetch(msg_num, "(RFC822)")
            except imaplib.IMAP4.error as fetch_error:
                safe_close_imap(mail, folder_selected)
                return json_error(
                    f"FETCH command error: {str(fetch_error)}. "
                    f"Email ID received: '{email_id}' (parsed as message number: '{msg_num}'). "
                    f"Make sure you're using the numeric 'id' field from search_emails() results, "
                    f"not an email address or other identifier."
                )
            
            if status != "OK":
                safe_close_imap(mail, folder_selected)
                return json_error(f"Failed to fetch email: {status}. Email ID: {email_id} (cleaned: {msg_num})")
            
            if not msg_data or not msg_data[0] or len(msg_data[0]) < 2:
                safe_close_imap(mail, folder_selected)
                return json_error(f"No email data returned for ID: {email_id}")
            
            email_body = msg_data[0][1]
            msg = email.message_from_bytes(email_body)
            
            email_info = parse_email_message(msg)
            email_info["id"] = email_id
            
            safe_close_imap(mail, folder_selected)
            
            return json.dumps({
                "success": True,
                "email": email_info
            }, indent=2, default=str)
        
        except Exception as e:
            safe_close_imap(mail, folder_selected)
            return json_error(f"Error reading email: {str(e)}")
    
    except Exception as e:
        return json_error(f"Error in read_email: {str(e)}")


@mcp.tool()
def download_attachments(
    email_id: str,
    download_path: Optional[str] = None,
    folder: str = "INBOX",
    email_address: Optional[str] = None,
    password: Optional[str] = None,
    imap_server: Optional[str] = None
) -> str:
    """
    Download attachments from an email. Useful for invoice processing and document handling.
    
    Args:
        email_id: Email ID (from search_emails or read_email results)
        download_path: Path to save attachments (defaults to ./attachments)
        folder: Email folder (default: 'INBOX')
        email_address: Email address (defaults to EMAIL_ADDRESS env var)
        password: Email password/app password (defaults to EMAIL_PASSWORD or EMAIL_APP_PASSWORD env var)
        imap_server: IMAP server address (defaults to Gmail IMAP)
        
    Returns:
        JSON string containing list of downloaded attachments with paths
    """
    try:
        # Get credentials
        if not email_address or not password:
            env_email, env_password, env_imap, _ = get_email_credentials()
            email_address = email_address or env_email
            password = password or env_password
            imap_server = imap_server or env_imap
        
        if not email_address or not password:
            return json_error(
                "Email credentials not provided. Set EMAIL_ADDRESS and EMAIL_PASSWORD environment variables, "
                "or provide email_address and password parameters."
            )
        
        if not imap_server:
            imap_server = GMAIL_IMAP_SERVER
        
        # Set download path
        if not download_path:
            download_path = Path(__file__).parent / "attachments"
        else:
            download_path = Path(download_path)
        
        download_path.mkdir(parents=True, exist_ok=True)
        
        # Connect to IMAP server
        mail = None
        folder_selected = False
        try:
            mail = imaplib.IMAP4_SSL(imap_server, DEFAULT_IMAP_PORT)
            mail.login(email_address, password)
            status, _ = mail.select(folder)
            if status != "OK":
                safe_close_imap(mail, False)
                return json_error(f"Failed to select folder '{folder}': {status}")
            folder_selected = True
        except imaplib.IMAP4.error as e:
            if mail:
                safe_close_imap(mail, False)
            return json_error(f"IMAP connection error: {str(e)}")
        except Exception as e:
            if mail:
                safe_close_imap(mail, False)
            return json_error(f"Connection error: {str(e)}")
        
        try:
            # Fetch email - email_id should be a string message number
            # Clean and validate the email_id
            email_id_str = str(email_id).strip()
            
            # Remove any non-numeric characters except for valid IMAP sequence syntax
            import re
            # Extract just the numeric part if it's a simple number
            match = re.match(r'^(\d+)', email_id_str)
            if match:
                msg_num = match.group(1)
            else:
                # If no number found, try to use as-is but log warning
                msg_num = email_id_str
            
            # Try fetching with the message number
            try:
                status, msg_data = mail.fetch(msg_num, "(RFC822)")
            except imaplib.IMAP4.error as fetch_error:
                safe_close_imap(mail, folder_selected)
                return json_error(
                    f"FETCH command error: {str(fetch_error)}. "
                    f"Email ID received: '{email_id}' (cleaned: '{msg_num}'). "
                    f"Make sure you're using the 'id' field from search_emails results."
                )
            
            if status != "OK":
                safe_close_imap(mail, folder_selected)
                return json_error(f"Failed to fetch email: {status}. Email ID: {email_id} (cleaned: {msg_num})")
            
            if not msg_data or not msg_data[0] or len(msg_data[0]) < 2:
                safe_close_imap(mail, folder_selected)
                return json_error(f"No email data returned for ID: {email_id}")
            
            email_body = msg_data[0][1]
            msg = email.message_from_bytes(email_body)
            
            downloaded_files = []
            
            # Extract attachments
            if msg.is_multipart():
                for part in msg.walk():
                    content_disposition = str(part.get("Content-Disposition", ""))
                    
                    if "attachment" in content_disposition:
                        filename = part.get_filename()
                        if filename:
                            filename = decode_mime_words(filename)
                            filepath = download_path / filename
                            
                            # Handle duplicate filenames
                            counter = 1
                            original_filepath = filepath
                            while filepath.exists():
                                stem = original_filepath.stem
                                suffix = original_filepath.suffix
                                filepath = download_path / f"{stem}_{counter}{suffix}"
                                counter += 1
                            
                            # Save attachment
                            try:
                                payload = part.get_payload(decode=True)
                                if payload:
                                    with open(filepath, 'wb') as f:
                                        f.write(payload)
                                    
                                    downloaded_files.append({
                                        "filename": filename,
                                        "saved_as": filepath.name,
                                        "path": str(filepath),
                                        "size": len(payload),
                                        "content_type": part.get_content_type(),
                                    })
                            except Exception as e:
                                downloaded_files.append({
                                    "filename": filename,
                                    "error": str(e)
                                })
            
            safe_close_imap(mail, folder_selected)
            
            if not downloaded_files:
                return json.dumps({
                    "success": True,
                    "message": "No attachments found in email",
                    "email_id": email_id,
                    "attachments": []
                }, indent=2)
            
            return json.dumps({
                "success": True,
                "message": f"Downloaded {len(downloaded_files)} attachment(s)",
                "email_id": email_id,
                "download_path": str(download_path),
                "attachments": downloaded_files
            }, indent=2, default=str)
        
        except Exception as e:
            safe_close_imap(mail, folder_selected)
            return json_error(f"Error downloading attachments: {str(e)}")
    
    except Exception as e:
        return json_error(f"Error in download_attachments: {str(e)}")


@mcp.tool()
def send_email(
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
    attachments: Optional[List[str]] = None,
    html_body: Optional[str] = None,
    email_address: Optional[str] = None,
    password: Optional[str] = None,
    smtp_server: Optional[str] = None,
    smtp_port: int = DEFAULT_SMTP_PORT
) -> str:
    """
    Send an email via SMTP. Useful for alerts and automated notifications.
    
    Args:
        to: Recipient email address(es), comma-separated for multiple
        subject: Email subject
        body: Email body text
        cc: Optional CC recipients, comma-separated
        bcc: Optional BCC recipients, comma-separated
        attachments: Optional list of file paths to attach
        html_body: Optional HTML body (if provided, body is used as plain text alternative)
        email_address: Sender email address (defaults to EMAIL_ADDRESS env var)
        password: Email password/app password (defaults to EMAIL_PASSWORD or EMAIL_APP_PASSWORD env var)
        smtp_server: SMTP server address (defaults to Gmail SMTP)
        smtp_port: SMTP port (default: 587)
        
    Returns:
        JSON string with send status
    """
    try:
        # Get credentials
        if not email_address or not password:
            env_email, env_password, _, env_smtp = get_email_credentials()
            email_address = email_address or env_email
            password = password or env_password
            smtp_server = smtp_server or env_smtp
        
        if not email_address or not password:
            return json_error(
                "Email credentials not provided. Set EMAIL_ADDRESS and EMAIL_PASSWORD environment variables, "
                "or provide email_address and password parameters."
            )
        
        if not smtp_server:
            smtp_server = GMAIL_SMTP_SERVER
        
        # Create message
        if html_body or attachments:
            msg = MIMEMultipart('alternative')
        else:
            msg = MIMEMultipart()
        
        msg['From'] = email_address
        msg['To'] = to
        if cc:
            msg['Cc'] = cc
        if bcc:
            msg['Bcc'] = bcc
        msg['Subject'] = subject
        
        # Add body
        if html_body:
            part1 = MIMEText(body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)
        else:
            msg.attach(MIMEText(body, 'plain'))
        
        # Add attachments
        if attachments:
            for filepath in attachments:
                try:
                    filepath_obj = Path(filepath)
                    if not filepath_obj.exists():
                        return json_error(f"Attachment file not found: {filepath}")
                    
                    with open(filepath_obj, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                    
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {filepath_obj.name}'
                    )
                    msg.attach(part)
                except Exception as e:
                    return json_error(f"Error attaching file {filepath}: {str(e)}")
        
        # Send email
        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(email_address, password)
            
            # Prepare recipients
            recipients = [to]
            if cc:
                recipients.extend([addr.strip() for addr in cc.split(',')])
            if bcc:
                recipients.extend([addr.strip() for addr in bcc.split(',')])
            
            text = msg.as_string()
            server.sendmail(email_address, recipients, text)
            server.quit()
            
            return json_success(
                f"Email sent successfully to {to}",
                subject=subject,
                recipients=recipients,
                attachments_count=len(attachments) if attachments else 0
            )
        
        except smtplib.SMTPAuthenticationError:
            return json_error("SMTP authentication failed. Check your email and password/app password.")
        except smtplib.SMTPException as e:
            return json_error(f"SMTP error: {str(e)}")
        except Exception as e:
            return json_error(f"Error sending email: {str(e)}")
    
    except Exception as e:
        return json_error(f"Error in send_email: {str(e)}")


if __name__ == "__main__":
    mcp.run()