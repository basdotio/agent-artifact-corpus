# Test Database Setup

This directory contains a Docker setup for running an Oracle Free database for testing.

## Prerequisites

- Docker and Docker Compose
- Access to Oracle Container Registry (you need to accept the terms and login)

## Login to Oracle Container Registry

Before running the database, you need to login to the Oracle Container Registry:

```bash
docker login container-registry.oracle.com
```

## Starting the Database

From this directory, run:

```bash
docker-compose up -d
```

The database will take a few minutes to initialize. You can check the logs with:

```bash
docker-compose logs -f
```

## Connection Details

### Main Schema (Complex)
- Hostname: localhost
- Port: 1521
- Service Name: FREEPDB1
- Test User: testuser
- Test Password: testpass
- Connection String: testuser/testpass@//localhost:1521/FREEPDB1

### Simple Schema
- User: simpleschema
- Password: simplepass
- Connection String: simpleschema/simplepass@//localhost:1521/FREEPDB1

Note: The testuser has SELECT privileges on the simpleschema tables for demonstration purposes.

## Schema Structure

### Main Schema (testuser)
Contains a comprehensive set of tables across multiple domains:
- customers
- orders
- products
- order_items
- (and many more business domain tables)

### Simple Schema (simpleschema)
Contains a basic set of tables:
- categories
- items

The simple schema is useful for demonstrating cross-schema queries and schema switching functionality.

## Sample Data

Both schemas are pre-populated with sample data. The main schema contains extensive test data across all domains, while the simple schema contains a basic set of categories and items.

## Stopping the Database

To stop the database:

```bash
docker-compose down
```

To remove all data and start fresh:

```bash
docker-compose down -v
```