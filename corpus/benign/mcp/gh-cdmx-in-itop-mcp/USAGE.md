# iTop MCP Server Usage Guide

This document provides detailed examples and usage patterns for the iTop MCP Server.

## Quick Start

1. **Setup the server:**
   ```bash
   make setup
   ```

2. **Configure your iTop connection:**
   ```bash
   # Edit .env with your credentials
   nano .env
   ```

3. **Test the connection:**
   ```bash
   make test
   ```

4. **Add to Claude Desktop configuration.**

## Tool Reference

### 1. list_operations

Lists all available operations in your iTop REST API.

**Usage:**
```
"List all available iTop operations"
```

**Example Output:**
```
Available iTop REST API operations:

• core/get: Search for objects
• core/create: Create an object
• core/update: Update an object
• core/delete: Delete objects
• core/apply_stimulus: Apply a stimulus (state change)
• core/get_related: Get related objects
• core/check_credentials: Check credentials
```

### 2. get_objects

Search and retrieve iTop objects.

**Parameters:**
- `class_name`: iTop class (e.g., UserRequest, Person, Organization)
- `key`: Search criteria (optional)
- `output_fields`: Fields to return (default: "*")

**Examples:**

Get all organizations:
```
"Get all organizations from iTop"
```

Get specific user request:
```
"Get user request with ID 123"
```

Search for open tickets:
```
"Find all UserRequest objects where status is 'new'"
```

**Advanced OQL Queries:**
```
"Get objects with class 'UserRequest', key 'SELECT UserRequest WHERE caller_name LIKE \"john%\"', and output fields 'id,title,status,caller_name'"
```

### 3. create_object

Create new objects in iTop.

**Parameters:**
- `class_name`: Object type to create
- `fields_json`: JSON string with field values
- `comment`: Optional comment

**Examples:**

Create a user request:
```
"Create a UserRequest with title 'Email not working', description 'Cannot access email', and org_id 'SELECT Organization WHERE name = \"Demo\"'"
```

Create an incident:
```
"Create an Incident with these fields: {\"title\": \"Server down\", \"description\": \"Web server not responding\", \"impact\": \"2\", \"urgency\": \"2\"}"
```

Create a person:
```
"Create a Person with fields: {\"name\": \"Smith\", \"first_name\": \"John\", \"email\": \"john.smith@company.com\", \"org_id\": 1}"
```

### 4. update_object

Update existing objects.

**Parameters:**
- `class_name`: Object type
- `key`: Object identifier
- `fields_json`: JSON with fields to update
- `comment`: Optional comment

**Examples:**

Update ticket priority:
```
"Update UserRequest with ID 123, set priority to '1' (high priority)"
```

Update person's email:
```
"Update Person with ID 456, change email to 'newemail@company.com'"
```

Add description to ticket:
```
"Update UserRequest 789, add description 'Customer called to report the issue is resolved'"
```

### 5. delete_object

Delete objects (with simulation mode for safety).

**Parameters:**
- `class_name`: Object type
- `key`: Object identifier
- `simulate`: Safety mode (default: true)
- `comment`: Optional comment

**Examples:**

Simulate deletion (safe):
```
"Simulate deleting UserRequest with ID 123"
```

Actually delete (use with caution):
```
"Delete Person with ID 456, set simulate to false"
```

### 6. apply_stimulus

Apply state transitions to objects.

**Parameters:**
- `class_name`: Object type
- `key`: Object identifier
- `stimulus`: State transition to apply
- `fields_json`: Additional fields to set
- `comment`: Optional comment

**Common Stimuli:**
- `ev_assign`: Assign ticket
- `ev_resolve`: Resolve ticket  
- `ev_close`: Close ticket
- `ev_reopen`: Reopen ticket

**Examples:**

Resolve a ticket:
```
"Apply stimulus 'ev_resolve' to UserRequest 123, with solution field 'Issue resolved by restarting the service'"
```

Assign a ticket:
```
"Assign UserRequest 456 to agent with ID 789 using the ev_assign stimulus"
```

Close an incident:
```
"Close Incident 321 using ev_close stimulus with closure code 'resolved'"
```

### 7. get_related_objects

Find objects related through impact/dependency relationships.

**Parameters:**
- `class_name`: Starting object type
- `key`: Object identifier
- `relation`: "impacts" or "depends on"
- `depth`: Search depth (default: 1)
- `direction`: "up" or "down"

**Examples:**

Find what a server impacts:
```
"Find all objects impacted by Server with ID 100, search depth 2, direction down"
```

Find dependencies:
```
"Get objects that Service 'Email Service' depends on"
```

### 8. check_credentials

Verify iTop API credentials.

**Usage:**
```
"Check my iTop credentials"
```

## Common Use Cases

### Ticket Management

**Create a ticket:**
```
"Create a new UserRequest for a printer issue. Title: 'Printer not working', Description: 'Office printer shows error message', assign to organization 'IT Department'"
```

**Update ticket status:**
```
"Update ticket 123 to set status to 'assigned' and add a note 'Assigned to John for investigation'"
```

**Resolve ticket:**
```
"Resolve UserRequest 456 with solution 'Replaced network cable, issue resolved'"
```

### Configuration Management

**Find server dependencies:**
```
"Show me all services that depend on the Mail Server"
```

**Get server details:**
```
"Get details for all Server objects with status 'active'"
```

### User Management

**Create user:**
```
"Create a new Person: John Doe, email john.doe@company.com, organization Demo"
```

**Find users:**
```
"Find all Person objects where email contains 'company.com'"
```

## Error Handling

The server handles common errors gracefully:

- **Authentication errors**: Check credentials and user permissions
- **Missing objects**: Verify object IDs and class names
- **Permission errors**: Ensure user has proper rights
- **Invalid JSON**: Check field syntax in create/update operations

## Best Practices

1. **Test first**: Use simulation mode for delete operations
2. **Use specific queries**: Include relevant filters to avoid large result sets
3. **Check permissions**: Ensure your iTop user has necessary rights
4. **Validate data**: Check field names and values before operations
5. **Use comments**: Add meaningful comments to track changes

## Troubleshooting

### Common Issues

**"User does not have enough rights"**
- Ensure iTop user has "REST Services User" profile
- Check object-level permissions

**"Several items found"**
- Make your key more specific
- Use exact IDs instead of search criteria for updates

**"Invalid JSON"**
- Validate JSON syntax in fields_json parameters
- Check for proper escaping of quotes

**"Connection refused"**
- Verify ITOP_BASE_URL is correct
- Check network connectivity to iTop instance
