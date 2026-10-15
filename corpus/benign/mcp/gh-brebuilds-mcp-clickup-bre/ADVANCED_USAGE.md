# Advanced Features Usage Guide

This guide shows you how to use the advanced features of your ClickUp MCP server.

## 🚀 Bulk Operations

### Bulk Create Tasks
Create multiple tasks efficiently in a single operation:

```javascript
{
  "list_id": "123456",
  "tasks": [
    {
      "name": "Task 1",
      "description": "First task",
      "priority": 2
    },
    {
      "name": "Task 2",
      "description": "Second task",
      "priority": 1,
      "tags": ["urgent"]
    }
    // ... up to hundreds of tasks
  ]
}
```

Returns a detailed report with success/failure status for each task.

### Bulk Update Tasks
Update multiple tasks at once:

```javascript
{
  "tasks": [
    {
      "id": "task123",
      "status": "in progress",
      "priority": 1
    },
    {
      "id": "task456",
      "status": "complete",
      "assignees": {"add": ["user123"]}
    }
  ]
}
```

### Bulk Delete Tasks
Delete multiple tasks efficiently:

```javascript
{
  "task_ids": ["task1", "task2", "task3", ...]
}
```

## ⚡ Automation Rules

### Create Automation
Create ClickUp native automations programmatically:

```javascript
{
  "workspace_id": "12345",
  "name": "Auto-assign when moved to In Progress",
  "trigger": {
    "type": "status_changed",
    "status_to": "in progress"
  },
  "actions": [
    {
      "type": "assign",
      "assignee": "user123"
    },
    {
      "type": "add_tag",
      "tag_name": "active"
    }
  ],
  "space_id": "67890"
}
```

### Common Automation Patterns

**Status-based assignment:**
```javascript
{
  "trigger": {"type": "status_changed", "status_to": "review"},
  "actions": [{"type": "assign", "assignee": "reviewer_id"}]
}
```

**Due date notifications:**
```javascript
{
  "trigger": {"type": "due_date_approaching", "days": 1},
  "actions": [{"type": "send_notification", "message": "Task due tomorrow!"}]
}
```

**Auto-tagging:**
```javascript
{
  "trigger": {"type": "task_created"},
  "actions": [{"type": "add_tag", "tag_name": "new"}]
}
```

## 🔧 Advanced Custom Fields

### Create Custom Field
Create any type of custom field:

**Dropdown field:**
```javascript
{
  "list_id": "123456",
  "name": "Department",
  "type": "drop_down",
  "type_config": {
    "options": [
      {"name": "Engineering", "color": "#0000FF"},
      {"name": "Sales", "color": "#00FF00"},
      {"name": "Marketing", "color": "#FF0000"}
    ]
  }
}
```

**Number field with format:**
```javascript
{
  "list_id": "123456",
  "name": "Budget",
  "type": "currency",
  "type_config": {
    "currency": "USD",
    "precision": 2
  }
}
```

**Rating field:**
```javascript
{
  "list_id": "123456",
  "name": "Priority Rating",
  "type": "rating",
  "type_config": {
    "max": 5,
    "theme": "stars"
  }
}
```

## 📊 Dashboard & Analytics

### Workspace Dashboard
Get comprehensive workspace analytics:

```javascript
{
  "workspace_id": "12345",
  "date_from": 1704067200000,  // Unix timestamp
  "date_to": 1706745600000
}
```

Returns metrics like:
- Tasks created/completed
- Average completion time
- User productivity
- Status distribution

### Time Tracking Report
Generate detailed time reports:

```javascript
{
  "team_id": "12345",
  "date_from": 1704067200000,
  "date_to": 1706745600000,
  "assignee": "user123"  // Optional filter
}
```

Returns:
- Total time tracked
- Time by task/user
- Billable vs non-billable
- Daily breakdowns

## 🔔 Webhooks for Real-time Triggers

### Create Webhook for n8n
Set up webhooks to trigger n8n workflows:

```javascript
{
  "workspace_id": "12345",
  "endpoint": "https://your-n8n-instance.com/webhook/clickup",
  "client_id": "your-client-id",
  "events": [
    "taskCreated",
    "taskUpdated",
    "taskDeleted",
    "taskCommentPosted",
    "taskStatusUpdated",
    "taskAssigneeUpdated"
  ],
  "space_id": "67890"  // Optional filter
}
```

### Available Events
- `taskCreated` - New task created
- `taskUpdated` - Task updated
- `taskDeleted` - Task deleted
- `taskCommentPosted` - Comment added
- `taskStatusUpdated` - Status changed
- `taskAssigneeUpdated` - Assignee changed
- `taskDueDateUpdated` - Due date changed
- `taskPriorityUpdated` - Priority changed
- `taskTimeTracked` - Time tracked
- `goalCreated` - Goal created
- `goalUpdated` - Goal updated

## 🎨 Advanced Documents

### Create Document with Formatting
Create rich documents with formatting:

```javascript
{
  "workspace_id": "12345",
  "name": "Project Requirements",
  "content": "# Project Overview\n\n## Goals\n- Goal 1\n- Goal 2\n\n**Important**: This is a critical project.",
  "parent_id": "parent_doc_id"  // Optional for nested docs
}
```

### Create Document Pages
Add pages to existing documents:

```javascript
{
  "document_id": "doc123",
  "name": "Implementation Details",
  "content": "## Technical Specifications\n\nDetailed implementation notes..."
}
```

## 🗑️ Safe Deletion

All delete operations are available, but use with caution:

```javascript
// Delete a space (and everything in it)
{"space_id": "123"}

// Delete a task
{"task_id": "abc123"}

// Delete a goal
{"goal_id": "goal123"}
```

## Integration Patterns

### n8n Workflow Pattern
1. **Webhook Trigger**: ClickUp webhook → n8n
2. **Process Data**: Transform ClickUp data in n8n
3. **Bulk Update**: Use bulk operations to update multiple tasks
4. **Dashboard**: Pull analytics for reporting

### AI Agent Pattern (Claude)
1. **Search Tasks**: Get relevant tasks
2. **Analyze**: Use Claude to analyze task data
3. **Bulk Create**: Generate and create tasks based on analysis
4. **Create Automation**: Set up automation rules
5. **Dashboard**: Pull metrics for insights

### Automation Creation Pattern
1. **Get Templates**: Fetch task templates
2. **Create Automation**: Auto-apply templates on task creation
3. **Webhook**: Notify external systems
4. **Dashboard**: Monitor automation effectiveness

## Tips for Advanced Usage

1. **Use Bulk Operations for Scale**: When dealing with >10 items, always use bulk operations
2. **Combine Webhooks + Automations**: Webhooks for external integrations, automations for internal workflows
3. **Custom Fields for Structure**: Use custom fields to add rich metadata to tasks
4. **Dashboard for Insights**: Regularly pull dashboard data for reporting
5. **Templates + Automation**: Combine templates with automation for consistent workflows

## Error Handling

Bulk operations return detailed success/failure reports:

```javascript
{
  "results": [
    {"success": true, "task_id": "123", "data": {...}},
    {"success": false, "error": "Missing required field", "task": {...}}
  ],
  "total": 10,
  "successful": 9
}
```

Always check the results array to identify and fix failures.

## Next Steps

1. Test basic operations first (create, update, get)
2. Experiment with bulk operations on small batches
3. Set up webhooks for real-time notifications
4. Create automations for common workflows
5. Pull dashboard data for insights
6. Build complex workflows combining multiple features

For the complete API reference, see the [ClickUp API Documentation](https://clickup.com/api).
