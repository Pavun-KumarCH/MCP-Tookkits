# Database Connection Strings Guide

Complete reference for all supported database connection string formats.

## 📋 Table of Contents

- [PostgreSQL](#postgresql)
- [MySQL/MariaDB](#mysqlmariadb)
- [SQLite](#sqlite)
- [MongoDB](#mongodb)
- [Usage Examples](#usage-examples)

---

## PostgreSQL

### Connection String Format
```
postgresql://[user[:password]@][host][:port][/database][?param1=value1&...]
postgres://[user[:password]@][host][:port][/database][?param1=value1&...]
```

### Examples

**Basic Connection:**
```
postgresql://postgres:password@localhost:5432/mydb
```

**Without Password (will prompt):**
```
postgresql://postgres@localhost:5432/mydb
```

**With Default Port:**
```
postgresql://user:pass@localhost/mydb
```

**Remote Server:**
```
postgresql://user:pass@192.168.1.100:5432/production_db
```

**With SSL:**
```
postgresql://user:pass@host:5432/db?sslmode=require
```

**Docker Container:**
```
postgresql://postgres:password@localhost:5432/postgres
```

**Cloud Providers:**
```
# AWS RDS
postgresql://username:password@your-instance.region.rds.amazonaws.com:5432/dbname

# Google Cloud SQL
postgresql://user:pass@/dbname?host=/cloudsql/project:region:instance

# Azure Database
postgresql://user@server:password@server.postgres.database.azure.com:5432/dbname
```

### Individual Parameters
```python
connect_database(
    db_type="postgresql",
    host="localhost",
    port=5432,
    database="mydb",
    user="postgres",
    password="password"
)
```

---

## MySQL/MariaDB

### Connection String Format
```
mysql://[user[:password]@][host][:port][/database][?param1=value1&...]
mariadb://[user[:password]@][host][:port][/database][?param1=value1&...]
```

### Examples

**Basic Connection:**
```
mysql://root:password@localhost:3306/mydb
```

**Without Password:**
```
mysql://root@localhost:3306/mydb
```

**With Default Port:**
```
mysql://user:pass@localhost/mydb
```

**Remote Server:**
```
mysql://user:pass@192.168.1.100:3306/production_db
```

**Docker Container:**
```
mysql://root:password@localhost:3306/mysql
```

**Cloud Providers:**
```
# AWS RDS
mysql://username:password@your-instance.region.rds.amazonaws.com:3306/dbname

# Google Cloud SQL
mysql://user:pass@/dbname?unix_socket=/cloudsql/project:region:instance

# Azure Database
mysql://user@server:password@server.mysql.database.azure.com:3306/dbname
```

### Individual Parameters
```python
connect_database(
    db_type="mysql",
    host="localhost",
    port=3306,
    database="mydb",
    user="root",
    password="password"
)
```

---

## SQLite

### Connection String Format
```
/path/to/database.db
sqlite:///path/to/database.db
sqlite:path/to/database.db
./relative/path/database.db
```

### Examples

**Absolute Path:**
```
/Users/apple/data/database.db
/var/lib/sqlite/mydb.db
```

**Relative Path:**
```
./data/database.db
../databases/mydb.db
```

**With sqlite:// Prefix:**
```
sqlite:///Users/apple/data/database.db
sqlite:///./data/database.db
```

**Docker Volume Mount:**
```
/data/database.db
/volumes/sqlite/mydb.db
```

**In-Memory Database:**
```
:memory:
sqlite:///:memory:
```

### Individual Parameters
```python
connect_database(
    db_type="sqlite",
    connection_string="/path/to/database.db"
)

# Or using database parameter
connect_database(
    db_type="sqlite",
    database="/path/to/database.db"
)
```

---

## MongoDB

### Connection String Format
```
mongodb://[username:password@]host1[:port1][,host2[:port2],...]/[database][?options]
mongodb+srv://[username:password@]host[/database][?options]
```

### Examples

**Basic Connection:**
```
mongodb://localhost:27017/
mongodb://localhost:27017/mydb
```

**With Authentication:**
```
mongodb://user:password@localhost:27017/mydb
```

**Multiple Hosts (Replica Set):**
```
mongodb://host1:27017,host2:27017,host3:27017/mydb?replicaSet=myReplicaSet
```

**MongoDB Atlas (Cloud):**
```
mongodb+srv://username:password@cluster.mongodb.net/mydb
mongodb+srv://username:password@cluster.mongodb.net/mydb?retryWrites=true&w=majority
```

**With Options:**
```
mongodb://user:pass@host:27017/mydb?authSource=admin&ssl=true
mongodb://user:pass@host:27017/mydb?readPreference=secondary
```

**Docker Container:**
```
mongodb://localhost:27017/test
```

**Local with Authentication:**
```
mongodb://admin:password@localhost:27017/admin
```

### Individual Parameters
```python
connect_database(
    db_type="mongodb",
    connection_string="mongodb://localhost:27017/",
    database_name="mydb"
)

# Or with full connection string including database
connect_database(
    db_type="mongodb",
    connection_string="mongodb://user:pass@localhost:27017/mydb"
)
```

---

## Usage Examples

### Using Connection Strings

```python
# PostgreSQL
connect_database(
    db_type="postgresql",
    connection_string="postgresql://postgres:password@localhost:5432/mydb"
)

# MySQL
connect_database(
    db_type="mysql",
    connection_string="mysql://root:password@localhost:3306/mydb"
)

# SQLite
connect_database(
    db_type="sqlite",
    connection_string="/path/to/database.db"
)

# MongoDB
connect_database(
    db_type="mongodb",
    connection_string="mongodb://localhost:27017/",
    database_name="mydb"
)
```

### Using Individual Parameters

```python
# PostgreSQL
connect_database(
    db_type="postgresql",
    host="localhost",
    port=5432,
    database="mydb",
    user="postgres",
    password="password"
)

# MySQL
connect_database(
    db_type="mysql",
    host="localhost",
    port=3306,
    database="mydb",
    user="root",
    password="password"
)

# SQLite
connect_database(
    db_type="sqlite",
    database="/path/to/database.db"
)

# MongoDB
connect_database(
    db_type="mongodb",
    connection_string="mongodb://localhost:27017/",
    database_name="mydb"
)
```

### Common Connection Patterns

**Local Development:**
```python
# PostgreSQL (Docker)
connect_database(
    db_type="postgresql",
    connection_string="postgresql://postgres:postgres@localhost:5432/postgres"
)

# MySQL (Docker)
connect_database(
    db_type="mysql",
    connection_string="mysql://root:password@localhost:3306/mysql"
)

# SQLite (Local file)
connect_database(
    db_type="sqlite",
    connection_string="./data/local.db"
)

# MongoDB (Docker)
connect_database(
    db_type="mongodb",
    connection_string="mongodb://localhost:27017/",
    database_name="test"
)
```

**Production (Cloud):**
```python
# PostgreSQL (AWS RDS)
connect_database(
    db_type="postgresql",
    connection_string="postgresql://user:pass@prod-db.region.rds.amazonaws.com:5432/proddb"
)

# MongoDB Atlas
connect_database(
    db_type="mongodb",
    connection_string="mongodb+srv://user:pass@cluster.mongodb.net/proddb"
)
```

---

## Connection String Components

### General Format
```
scheme://[credentials@]host[:port][/path][?parameters]
```

### Components Explained

- **scheme**: Database type (`postgresql`, `mysql`, `sqlite`, `mongodb`)
- **credentials**: `username:password` (optional)
- **host**: Server address (IP or hostname)
- **port**: Port number (optional, uses defaults if omitted)
- **path**: Database name or file path
- **parameters**: Query string with additional options

### Default Ports

- **PostgreSQL**: 5432
- **MySQL**: 3306
- **MongoDB**: 27017
- **SQLite**: N/A (file-based)

---

## Security Notes

⚠️ **Important Security Considerations:**

1. **Never commit connection strings with passwords to version control**
2. **Use environment variables for sensitive credentials**
3. **Use SSL/TLS for production connections**
4. **Rotate passwords regularly**
5. **Use read-only users when possible**

### Best Practices

```python
# ✅ Good: Use environment variables
import os
connect_database(
    db_type="postgresql",
    connection_string=os.getenv("DATABASE_URL")
)

# ❌ Bad: Hardcoded credentials
connect_database(
    db_type="postgresql",
    connection_string="postgresql://user:password@host/db"  # Don't do this!
)
```

---

## Troubleshooting

### Connection Refused
- Check if database server is running
- Verify port number
- Check firewall settings
- Ensure host is accessible

### Authentication Failed
- Verify username and password
- Check if user has access to database
- Verify database name exists

### SSL/TLS Issues
- Add `?sslmode=require` for PostgreSQL
- Check certificate validity
- Verify SSL configuration

---

**Last Updated:** January 2025
