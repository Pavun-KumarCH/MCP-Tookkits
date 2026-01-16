# SQL/DB Query Tool

A production-ready MCP server for structured data access with security guardrails. Supports multiple database backends and provides safe query execution for analytics, reporting, and decision support.

## 🚀 Features

- **Multi-Database Support**: SQLite, PostgreSQL, MySQL/MariaDB, MongoDB
- **Security Guardrails**: SQL injection protection, read-only mode, row limits
- **Schema Discovery**: Fetch schemas, list tables, describe columns
- **Connection String Based**: Simple connection string API for all databases
- **Production Ready**: Built for analytics, reporting, and decision support

## 📋 Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Security Features](#security-features)
- [API Reference](#api-reference)
- [Use Cases](#use-cases)
- [Troubleshooting](#troubleshooting)

## 🏗️ Architecture

### Modules

1. **`database_connection.py`**: Multi-database connection management
   - SQLite, PostgreSQL, MySQL, MongoDB support
   - Connection pooling and reuse
   - Database-agnostic interface

2. **`query_validator.py`**: Security and validation
   - SQL injection detection
   - Read-only mode enforcement
   - Row limit enforcement
   - Dangerous operation blocking

3. **`schema_fetcher.py`**: Schema discovery and formatting
   - Table listing
   - Column information
   - Schema formatting

4. **`json_serializer.py`**: JSON serialization utilities
   - Handles date/datetime objects
   - Converts Decimal to float
   - Bytes to string conversion

5. **`server.py`**: MCP server with essential tool endpoints
   - Query execution
   - Schema operations
   - Dynamic database connections

## 📦 Prerequisites

### SQLite (Default)

SQLite is included with Python. For Docker usage:

```bash
docker run -d \
  --name sqlite-db \
  -v $(pwd)/data:/data \
  alpine/sqlite:latest
```

### PostgreSQL (Optional)

```bash
docker run -d \
  --name postgres-db \
  -e POSTGRES_PASSWORD=yourpassword \
  -p 5432:5432 \
  postgres:latest
```

### MySQL (Optional)

```bash
docker run -d \
  --name mysql-db \
  -e MYSQL_ROOT_PASSWORD=yourpassword \
  -e MYSQL_DATABASE=testdb \
  -p 3306:3306 \
  mysql:latest
```

### MongoDB (Optional)

```bash
docker run -d \
  --name mongodb \
  -p 27017:27017 \
  mongo:latest
```

## 🔧 Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment variables:**
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your database configuration
nano .env
```

## ⚙️ Configuration

All configuration is managed through the `.env` file.

### Database Type

Set `DB_TYPE` to one of:
- `sqlite` (default)
- `postgresql`
- `mysql`
- `mongodb`

### Security Settings

```bash
# Read-only mode (prevents write operations)
READ_ONLY=true

# Maximum rows returned per query
MAX_ROWS=1000

# Query timeout in seconds
QUERY_TIMEOUT=30
```

### Database-Specific Configuration

#### SQLite
```bash
DB_TYPE=sqlite
SQLITE_DATABASE_PATH=./data/database.db
```

#### PostgreSQL
```bash
DB_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=yourpassword
```

#### MySQL
```bash
DB_TYPE=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=mysql
MYSQL_USER=root
MYSQL_PASSWORD=yourpassword
```

#### MongoDB
```bash
DB_TYPE=mongodb
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=test
```

## 📖 Usage

### Dynamic Database Connections

The tool supports connecting to any database dynamically at runtime using connection strings. You can switch between different databases without restarting the server.

### Connection String Formats

**PostgreSQL:**
```
postgresql://username:password@host:port/database
postgresql://postgres:mypass@localhost:5432/mydb
```

**MySQL:**
```
mysql://username:password@host:port/database
mysql://root:password@localhost:3306/mydb
```

**MongoDB:**
```
mongodb://host:port/
mongodb://localhost:27017/
mongodb://user:password@localhost:27017/database
mongodb+srv://username:password@cluster.mongodb.net/database
```

**SQLite:**
```
/path/to/database.db
sqlite:///path/to/database.db
sqlite:./relative/path.db
```

### MCP Tools

#### 1. `connect_database`

Connect to a database dynamically using a connection string:

```python
# PostgreSQL
connect_database(
    db_type="postgresql",
    connection_string="postgresql://user:password@localhost:5432/mydb"
)

# MySQL
connect_database(
    db_type="mysql",
    connection_string="mysql://user:password@localhost:3306/mydb"
)

# MongoDB
connect_database(
    db_type="mongodb",
    connection_string="mongodb://localhost:27017/mydb"
)

# SQLite
connect_database(
    db_type="sqlite",
    connection_string="/path/to/database.db"
)
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully connected to postgresql database",
  "db_type": "postgresql",
  "connected": true,
  "connection_string": "postgresql://user:****@localhost:5432/mydb"
}
```

#### 2. `run_query`

Execute a SQL query with security guardrails:

```python
run_query(
    sql="SELECT * FROM users WHERE age > 18 LIMIT 10",
    limit=50  # Optional: override default MAX_ROWS
)
```

**Response:**
```json
{
  "success": true,
  "message": "Query executed successfully",
  "rows": [
    {"id": 1, "name": "John", "age": 25},
    {"id": 2, "name": "Jane", "age": 30}
  ],
  "row_count": 2,
  "columns": ["id", "name", "age"]
}
```

#### 3. `fetch_schema`

Fetch database schema information:

```python
# Get all tables schema
fetch_schema()

# Get specific table schema
fetch_schema(table_name="users")
```

**Response:**
```json
{
  "success": true,
  "message": "Schema fetched successfully",
  "schema": {
    "database": "mydb",
    "tables": {
      "users": {
        "table_name": "users",
        "columns": [
          {"name": "id", "type": "INTEGER", "primary_key": true},
          {"name": "name", "type": "VARCHAR", "not_null": true}
        ]
      }
    }
  },
  "formatted": "Database: mydb\nTables: 1\n..."
}
```

#### 4. `list_tables`

List all tables in the database:

```python
list_tables()
```

**Response:**
```json
{
  "success": true,
  "message": "Found 5 tables",
  "tables": ["users", "orders", "products", "categories", "reviews"],
  "count": 5
}
```

#### 5. `describe_table`

Get detailed table information including columns, types, row count, and statistics:

```python
describe_table(table_name="users")
```

**Response:**
```json
{
  "success": true,
  "message": "Table 'users' described successfully",
  "table_name": "users",
  "row_count": 1000,
  "column_count": 5,
  "columns": [
    {
      "name": "id",
      "type": "INTEGER",
      "nullable": false,
      "primary_key": true
    },
    {
      "name": "name",
      "type": "VARCHAR(255)",
      "nullable": false,
      "primary_key": false
    },
    {
      "name": "email",
      "type": "VARCHAR(255)",
      "nullable": true,
      "primary_key": false
    }
  ],
  "formatted": "Table: users\nRows: 1000\nColumns:\n  - id (INTEGER) [PRIMARY KEY] [NOT NULL]..."
}
```

## 🔒 Security Features

### SQL Injection Protection

The tool detects common SQL injection patterns:
- `OR 1=1` attacks
- `UNION SELECT` attacks
- Comment-based injections (`--`, `/* */`)
- Time-based attacks
- Function-based attacks

### Read-Only Mode

When `READ_ONLY=true`, the following operations are blocked:
- `INSERT`, `UPDATE`, `DELETE`
- `DROP`, `CREATE`, `ALTER`, `TRUNCATE`
- `GRANT`, `REVOKE`
- `EXEC`, `EXECUTE`, `CALL`

Only allowed operations:
- `SELECT`, `SHOW`, `DESCRIBE`, `EXPLAIN`
- `WITH` (CTEs)

### Row Limits

- Automatic `LIMIT` clause addition
- Configurable `MAX_ROWS` (default: 1000)
- Prevents large result sets that could cause memory issues
- Can be overridden per query using the `limit` parameter

### Query Validation

- Length limits (100KB max)
- Syntax validation
- Dangerous keyword detection
- Pattern matching for injection attempts

## 📚 API Reference

### DatabaseConnection

Base class for all database connections.

#### Methods

- `execute_query(query, params=None)`: Execute a query
- `get_schema(table_name=None)`: Get schema information
- `list_tables()`: List all tables
- `test_connection()`: Test connection
- `close()`: Close connection

### QueryValidator

Validates and sanitizes SQL queries.

#### Methods

- `validate(query)`: Validate a query
- `add_limit_if_needed(query)`: Add LIMIT clause
- `sanitize_query(query)`: Remove comments and normalize

### SchemaFetcher

Fetches and formats schema information.

#### Methods

- `get_full_schema()`: Get full database schema
- `get_table_info(table_name)`: Get table information with row count
- `list_all_tables()`: List all tables
- `get_table_columns(table_name)`: Get column information

## 🔄 Dynamic Connection Examples

### Switch Between Databases

```python
# Connect to PostgreSQL
connect_database(
    db_type="postgresql",
    connection_string="postgresql://user:pass@localhost:5432/prod_db"
)

# Run queries
run_query("SELECT * FROM users LIMIT 10")

# Switch to MySQL
connect_database(
    db_type="mysql",
    connection_string="mysql://root:password@localhost:3306/analytics_db"
)

# Run queries on new database
run_query("SELECT * FROM events WHERE date > '2024-01-01'")

# Switch to SQLite
connect_database(
    db_type="sqlite",
    connection_string="/path/to/local.db"
)

# Continue querying
run_query("SELECT * FROM local_data")
```

### Complete Workflow Example

```python
# 1. Connect to database
connect_database(
    db_type="postgresql",
    connection_string="postgresql://postgres:password@localhost:5432/mydb"
)

# 2. Discover available tables
tables = list_tables()
# Returns: {"tables": ["users", "orders", "products"], "count": 3}

# 3. Get schema for a specific table
schema = describe_table(table_name="users")
# Returns: Detailed table information with columns, types, row count

# 4. Fetch full database schema
full_schema = fetch_schema()
# Returns: Complete database schema with all tables

# 5. Execute queries
results = run_query("SELECT * FROM users WHERE age > 18 LIMIT 10")
# Returns: Query results with rows, columns, and row count
```

## 🎯 Use Cases

### 1. Analytics

```python
# Get sales statistics
run_query("""
    SELECT 
        DATE(created_at) as date,
        COUNT(*) as orders,
        SUM(total) as revenue
    FROM orders
    WHERE created_at >= DATE('now', '-30 days')
    GROUP BY DATE(created_at)
    ORDER BY date DESC
""")
```

### 2. Reporting

```python
# Generate user report
run_query("""
    SELECT 
        u.id,
        u.name,
        u.email,
        COUNT(o.id) as order_count,
        SUM(o.total) as total_spent
    FROM users u
    LEFT JOIN orders o ON u.id = o.user_id
    GROUP BY u.id, u.name, u.email
    ORDER BY total_spent DESC
    LIMIT 100
""")
```

### 3. Decision Support

```python
# Analyze product performance
run_query("""
    SELECT 
        p.name,
        p.category,
        COUNT(o.id) as sales_count,
        AVG(o.total) as avg_order_value
    FROM products p
    JOIN order_items oi ON p.id = oi.product_id
    JOIN orders o ON oi.order_id = o.id
    WHERE o.created_at >= DATE('now', '-90 days')
    GROUP BY p.id, p.name, p.category
    HAVING sales_count > 10
    ORDER BY sales_count DESC
""")
```

### 4. Schema Discovery

```python
# Discover database structure
tables = list_tables()
for table in tables['tables']:
    info = describe_table(table_name=table)
    print(f"Table: {table}")
    print(f"Rows: {info['row_count']}")
    print(f"Columns: {info['columns']}")
```

## 🔍 Troubleshooting

### Connection Issues

**Problem:** Cannot connect to database

**Solutions:**
```bash
# Check database is running
docker ps | grep -E "postgres|mysql|mongodb|sqlite"

# Verify configuration in .env
cat .env | grep DB_TYPE

# Check connection string format
# PostgreSQL: postgresql://user:pass@host:port/db
# MySQL: mysql://user:pass@host:port/db
# MongoDB: mongodb://host:port/
# SQLite: /path/to/database.db
```

**Common Errors:**
- `Connection refused`: Database server is not running or wrong port
- `unable to open database file`: SQLite path doesn't exist or is inaccessible
- `Invalid connection string`: Check connection string format

### SQL Injection False Positives

**Problem:** Valid query flagged as SQL injection

**Solutions:**
- Review query for suspicious patterns
- Ensure query follows standard SQL syntax
- Check for accidental injection patterns in WHERE clauses

### Read-Only Violations

**Problem:** Query blocked in read-only mode

**Solutions:**
- Verify query only uses SELECT/SHOW/DESCRIBE/EXPLAIN
- Check if write operations are needed
- Contact administrator to enable write mode if required

### Row Limit Issues

**Problem:** Results truncated by MAX_ROWS

**Solutions:**
```python
# Override limit for specific query
run_query(sql="SELECT * FROM large_table", limit=5000)

# Or update MAX_ROWS in .env
MAX_ROWS=5000
```

### MongoDB Queries

MongoDB uses JSON-based queries:

```python
run_query(json.dumps({
    "collection": "users",
    "operation": "find",
    "filter": {"age": {"$gt": 18}},
    "projection": {"name": 1, "email": 1},
    "limit": 100
}))
```

## 📊 Supported Databases

### SQLite
- ✅ Full support
- ✅ Schema discovery
- ✅ Query execution
- ✅ Best for: Development, small datasets

### PostgreSQL
- ✅ Full support
- ✅ Advanced schema queries
- ✅ Complex SQL support
- ✅ Best for: Production, complex queries

### MySQL/MariaDB
- ✅ Full support
- ✅ Standard SQL
- ✅ Performance optimized
- ✅ Best for: Web applications

### MongoDB
- ✅ Basic support
- ✅ JSON-based queries
- ✅ Collection discovery
- ✅ Best for: Document databases

## 🔒 Best Practices

1. **Always Use Read-Only Mode**: Enable `READ_ONLY=true` for production
2. **Set Appropriate Limits**: Configure `MAX_ROWS` based on your needs
3. **Use Connection Strings**: Always use connection strings for consistency
4. **Discover Schema First**: Use `list_tables()` and `describe_table()` before querying
5. **Monitor Query Performance**: Set appropriate `QUERY_TIMEOUT`
6. **Handle Errors Gracefully**: Check for connection errors and handle them appropriately

## 📝 License

Production Tools Suite

## 🤝 Contributing

This is part of the Production Tools Suite. For issues or contributions, please refer to the main project repository.

## 📞 Support

For issues related to:
- **SQLite**: Check [SQLite documentation](https://www.sqlite.org/docs.html)
- **PostgreSQL**: Check [PostgreSQL documentation](https://www.postgresql.org/docs/)
- **MySQL**: Check [MySQL documentation](https://dev.mysql.com/doc/)
- **MongoDB**: Check [MongoDB documentation](https://docs.mongodb.com/)
- **MCP**: Check [MCP documentation](https://modelcontextprotocol.io)

---

**Version:** 2.0.0  
**Last Updated:** January 2025
