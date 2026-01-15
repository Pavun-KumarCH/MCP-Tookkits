# Email Operations MCP Tool

A production-ready MCP (Model Context Protocol) server for email operations using Gmail/SMTP. This tool provides comprehensive email management capabilities including searching, reading, downloading attachments, and sending emails.

## Features

- 🔍 **Email Search** - Search emails using Gmail syntax or IMAP keywords
- 📧 **Read Emails** - Read full email content with metadata
- 📎 **Download Attachments** - Download and save email attachments
- ✉️ **Send Emails** - Send emails with HTML support and attachments
- 🔒 **Secure** - Supports Gmail App Passwords and secure authentication
- 🚀 **Production Ready** - Error handling, state management, and robust connection handling

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Usage Examples](#usage-examples)
- [Error Handling](#error-handling)
- [Architecture](#architecture)

## Installation

### Prerequisites

- Python 3.11+
- Gmail account (or other IMAP/SMTP email provider)
- Gmail App Password (for Gmail accounts)

### Install Dependencies

```bash
pip install python-dotenv
# Or if using uv:
uv sync
```

## Configuration

### 1. Set Up Environment Variables

Copy the example environment file and configure it:

```bash
cp ../env.example .env
```

Edit `.env` with your credentials:

```bash
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-16-character-app-password
EMAIL_APP_PASSWORD=your-16-character-app-password  # Alternative name
IMAP_SERVER=imap.gmail.com  # Optional, defaults to Gmail
SMTP_SERVER=smtp.gmail.com  # Optional, defaults to Gmail
```

### 2. Gmail App Password Setup

For Gmail accounts, you need to generate an App Password:

1. Go to [Google Account Settings](https://myaccount.google.com/)
2. Navigate to **Security** → **2-Step Verification** (must be enabled)
3. Go to **App passwords**
4. Generate a new app password for "Mail"
5. Use the 16-character password (no spaces) as `EMAIL_PASSWORD`

### 3. Other Email Providers

For non-Gmail providers, update the server addresses:

```bash
# Outlook/Office365
IMAP_SERVER=outlook.office365.com
SMTP_SERVER=smtp.office365.com

# Yahoo
IMAP_SERVER=imap.mail.yahoo.com
SMTP_SERVER=smtp.mail.yahoo.com
```

## API Reference

### `search_emails(query, folder, max_results, ...)`

Search for emails using IMAP/Gmail query syntax.

**Parameters:**
- `query` (str, required): Search query
  - Gmail syntax: `from:email@example.com`, `subject:text`, `is:unread`, `has:attachment`
  - IMAP keywords: `ALL`, `UNSEEN`, `SEEN`, `FLAGGED`
  - Simple text: searches in subject and body (Gmail only)
- `folder` (str, optional): Email folder (default: `"INBOX"`)
- `max_results` (int, optional): Maximum results (default: `50`)
- `email_address` (str, optional): Override EMAIL_ADDRESS env var
- `password` (str, optional): Override EMAIL_PASSWORD env var
- `imap_server` (str, optional): Override IMAP_SERVER env var

**Returns:** JSON string with email list and metadata

**Example:**
```python
# Search unread emails
search_emails("is:unread")

# Search emails from specific sender
search_emails("from:invoice@company.com")

# Search emails with attachments
search_emails("has:attachment")

# Search by subject
search_emails("subject:invoice")
```

### `read_email(email_id, folder, ...)`

Read a specific email by its message ID.

**Parameters:**
- `email_id` (str, required): Message ID from `search_emails()` results (numeric)
- `folder` (str, optional): Email folder (default: `"INBOX"`)
- `email_address` (str, optional): Override EMAIL_ADDRESS env var
- `password` (str, optional): Override EMAIL_PASSWORD env var
- `imap_server` (str, optional): Override IMAP_SERVER env var

**Returns:** JSON string with full email content

**Example:**
```python
# First search for emails
results = search_emails("from:sender@example.com")
# Parse results to get email IDs
# Then read specific email
read_email("123")  # Use the 'id' field from search results
```

### `download_attachments(email_id, download_path, folder, ...)`

Download all attachments from an email.

**Parameters:**
- `email_id` (str, required): Message ID from `search_emails()` or `read_email()` results
- `download_path` (str, optional): Directory to save attachments (default: `./attachments`)
- `folder` (str, optional): Email folder (default: `"INBOX"`)
- `email_address` (str, optional): Override EMAIL_ADDRESS env var
- `password` (str, optional): Override EMAIL_PASSWORD env var
- `imap_server` (str, optional): Override IMAP_SERVER env var

**Returns:** JSON string with list of downloaded files

**Example:**
```python
# Download attachments from email ID 123
download_attachments("123", download_path="./my_attachments")
```

### `send_email(to, subject, body, ...)`

Send an email via SMTP.

**Parameters:**
- `to` (str, required): Recipient email(s), comma-separated for multiple
- `subject` (str, required): Email subject
- `body` (str, required): Email body text
- `cc` (str, optional): CC recipients, comma-separated
- `bcc` (str, optional): BCC recipients, comma-separated
- `attachments` (List[str], optional): List of file paths to attach
- `html_body` (str, optional): HTML version of body (if provided, body is plain text alternative)
- `email_address` (str, optional): Sender email (defaults to EMAIL_ADDRESS env var)
- `password` (str, optional): Override EMAIL_PASSWORD env var
- `smtp_server` (str, optional): Override SMTP_SERVER env var
- `smtp_port` (int, optional): SMTP port (default: `587`)

**Returns:** JSON string with send status

**Example:**
```python
# Simple email
send_email(
    to="recipient@example.com",
    subject="Test Email",
    body="This is a test email."
)

# Email with HTML and attachments
send_email(
    to="recipient@example.com",
    subject="Invoice",
    body="Please find the invoice attached.",
    html_body="<h1>Invoice</h1><p>Please find the invoice attached.</p>",
    attachments=["./invoice.pdf", "./receipt.pdf"]
)
```

## Usage Examples

### Example 1: Invoice Processing Workflow

```python
# 1. Search for invoices
invoices = search_emails("subject:invoice has:attachment")

# 2. Parse results to get email IDs
# (In real usage, parse the JSON response)

# 3. Read specific invoice email
invoice_email = read_email("123")

# 4. Download attachments
attachments = download_attachments("123", download_path="./invoices")
```

### Example 2: Support Ticket Automation

```python
# Search for unread support emails
support_emails = search_emails("is:unread from:support@company.com")

# Read each email
for email_id in email_ids:
    email_content = read_email(email_id)
    # Process email content
    # Mark as read, create ticket, etc.
```

### Example 3: Send Alert Email

```python
# Send alert with attachment
send_email(
    to="admin@company.com",
    subject="System Alert",
    body="System error detected. See attached log file.",
    attachments=["./error.log"]
)
```

## Error Handling

All functions return JSON responses with error information:

**Success Response:**
```json
{
  "success": true,
  "message": "Operation completed",
  "data": {...}
}
```

**Error Response:**
```json
{
  "error": "Error message here",
  "additional_info": "..."
}
```

### Common Errors

1. **Authentication Errors**
   - Check EMAIL_ADDRESS and EMAIL_PASSWORD are set correctly
   - For Gmail, ensure you're using an App Password, not your regular password

2. **Invalid Email ID**
   - Email IDs must be numeric (from search_emails results)
   - Don't use email addresses as IDs - use search_emails first

3. **Folder Not Found**
   - Ensure folder name is correct (case-sensitive)
   - Common folders: INBOX, Sent, Drafts, Trash

4. **Connection Errors**
   - Check internet connection
   - Verify IMAP/SMTP server addresses
   - Check firewall settings

## Architecture

### Code Structure

```
server.py
├── Constants
│   ├── Server addresses
│   └── Port configurations
├── Utility Functions
│   ├── json_error/json_success - Response formatting
│   ├── decode_mime_words - Header decoding
│   ├── parse_imap_query - Query parsing
│   ├── parse_email_message - Email parsing
│   ├── get_email_credentials - Credential management
│   ├── safe_close_imap - Connection cleanup
│   └── connect_imap - Connection helper
└── MCP Tool Functions
    ├── search_emails
    ├── read_email
    ├── download_attachments
    └── send_email
```

### Key Design Decisions

1. **State Management**: Proper IMAP state handling prevents "command illegal in state" errors
2. **Error Recovery**: Graceful fallback from Gmail X-GM-RAW to standard IMAP
3. **Connection Pooling**: Each function manages its own connection lifecycle
4. **Security**: Credentials via environment variables, never hardcoded
5. **Flexibility**: Supports both Gmail and standard IMAP/SMTP servers

### IMAP State Machine

The tool properly handles IMAP state transitions:

```
AUTH → SELECT → SELECTED → CLOSE → AUTH → LOGOUT
```

- `mail.select()` moves from AUTH to SELECTED
- `mail.close()` only works in SELECTED state
- `safe_close_imap()` handles state-aware cleanup

## Running the Server

### Development Mode

```bash
mcp dev server.py
```

### Production Mode

```bash
mcp run server.py
```

### Using with MCP Client

The server exposes these tools:
- `search_emails`
- `read_email`
- `download_attachments`
- `send_email`

## Troubleshooting

### Issue: "IMAP connection error"

**Solution:**
- Verify EMAIL_ADDRESS and EMAIL_PASSWORD are correct
- For Gmail, use App Password (not regular password)
- Check IMAP is enabled in email account settings

### Issue: "FETCH command error: Could not parse command"

**Solution:**
- Ensure email_id is numeric (from search_emails results)
- Don't pass email addresses as email_id
- Use the 'id' field from search results

### Issue: "command CLOSE illegal in state AUTH"

**Solution:**
- This is handled automatically by `safe_close_imap()`
- If you see this, ensure you're using the latest version

### Issue: "Search failed" or "Could not parse command"

**Solution:**
- Use proper Gmail syntax: `from:email@example.com`
- Or use IMAP keywords: `ALL`, `UNSEEN`, `SEEN`
- Avoid complex queries that might not parse correctly

## Best Practices

1. **Always use search_emails first** to get message IDs before reading emails
2. **Handle errors gracefully** - check for "error" key in JSON responses
3. **Limit search results** - use `max_results` parameter to avoid large responses
4. **Clean up attachments** - regularly clean the attachments directory
5. **Use environment variables** - never hardcode credentials
6. **Test with small queries first** - verify connection before large operations

## Security Notes

- ✅ Credentials stored in environment variables
- ✅ Supports App Passwords (more secure than regular passwords)
- ✅ No credentials in code or logs
- ✅ Secure IMAP/SMTP connections (SSL/TLS)
- ⚠️ Never commit `.env` file to version control
- ⚠️ Rotate App Passwords regularly
- ⚠️ Use read-only access when possible

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Review error messages for specific guidance
3. Verify configuration matches examples
4. Check IMAP/SMTP server status

---

**Made with ❤️ for production email automation**
