#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
  CallToolRequest,
} from '@modelcontextprotocol/sdk/types.js';
import { GitLabService } from './gitlab.service.js';
import { GitLabConfig, GitLabPosition } from './gitlab.js';
import { JiraService } from './jira.service.js';
import { levenshteinDistance } from './utils.js';
import {
  JiraConfig,
  JiraTicketUpdatePayload,
  JiraCustomFieldUpdatePayload,
} from './jira.js';

// Load GitLab configuration from environment variables
const gitlabUrl = process.env.GITLAB_URL;
const gitlabAccessToken = process.env.GITLAB_ACCESS_TOKEN || process.env.GITLAB_API_TOKEN;

let gitlabService: GitLabService | undefined;
try {
  if (gitlabUrl && gitlabAccessToken) {
    const gitlabConfig: GitLabConfig = {
      url: gitlabUrl,
      accessToken: gitlabAccessToken,
    };
    gitlabService = new GitLabService(gitlabConfig);
    console.error('GitLab service initialized');
  } else {
    console.error(
      'Warning: GITLAB_URL and GITLAB_ACCESS_TOKEN environment variables are not set. GitLab tools will be unavailable.',
    );
  }
} catch (error) {
  console.error('Error initializing GitLab service:', error);
}

// Load Jira configuration from environment variables
const jiraApiBaseUrl = process.env.ATLASSIAN_SITE_NAME;
const jiraUserEmail = process.env.ATLASSIAN_USER_EMAIL;
const jiraApiToken = process.env.ATLASSIAN_API_TOKEN;

let jiraService: JiraService | undefined;
try {
  if (jiraApiBaseUrl && jiraUserEmail && jiraApiToken) {
    const jiraConfig: JiraConfig = {
      apiBaseUrl: jiraApiBaseUrl,
      userEmail: jiraUserEmail,
      apiToken: jiraApiToken,
    };
    jiraService = new JiraService(jiraConfig);
    console.error('Jira service initialized');
  } else {
    console.error(
      'Warning: ATLASSIAN_SITE_NAME, ATLASSIAN_USER_EMAIL, and ATLASSIAN_API_TOKEN environment variables are not set. Jira tools will be unavailable.',
    );
  }
} catch (error) {
  console.error('Error initializing Jira service:', error);
}

// Define all possible tools
const allTools: Tool[] = [
  {
    name: 'gitlab_get_merge_request_details',
    description:
      'Fetches detailed information about a GitLab Merge Request, including file diffs.',
    inputSchema: {
      type: 'object',
      properties: {
        mrUrl: {
          type: 'string',
          description: 'The URL of the GitLab Merge Request.',
        },
      },
      required: ['mrUrl'],
    },
  },
  {
    name: 'gitlab_get_file_content',
    description:
      'Fetches the content of a specific file at a given SHA in a GitLab project.',
    inputSchema: {
      type: 'object',
      properties: {
        mrUrl: {
          type: 'string',
          description:
            'The URL of the GitLab Merge Request (used to derive project path).',
        },
        filePath: {
          type: 'string',
          description: 'The path of the file to fetch.',
        },
        sha: {
          type: 'string',
          description:
            'The SHA of the commit or branch to fetch the file from.',
        },
      },
      required: ['mrUrl', 'filePath', 'sha'],
    },
  },
  {
    name: 'gitlab_add_comment_to_merge_request',
    description:
      'Adds a comment to a GitLab Merge Request. Can be a general comment, a reply to an existing discussion, or an inline comment on a specific line.',
    inputSchema: {
      type: 'object',
      properties: {
        mrUrl: {
          type: 'string',
          description: 'The URL of the GitLab Merge Request.',
        },
        commentBody: {
          type: 'string',
          description: 'The content of the comment.',
        },
        discussionId: {
          type: 'string',
          description:
            'Optional: The ID of an existing discussion to reply to.',
        },
        position: {
          type: 'object',
          description:
            'Optional: Position object for inline comments, specifying file paths, SHAs, and line numbers.',
          properties: {
            base_sha: { type: 'string' },
            start_sha: { type: 'string' },
            head_sha: { type: 'string' },
            position_type: { type: 'string' },
            old_path: { type: 'string' },
            new_path: { type: 'string' },
            new_line: { type: 'number' },
            old_line: { type: 'number' },
          },
        },
      },
      required: ['mrUrl', 'commentBody'],
    },
  },
  {
    name: 'gitlab_list_merge_requests',
    description: 'Lists merge requests for a given GitLab project.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description:
            'The path of the GitLab project (e.g., "namespace/project-name").',
        },
      },
      required: ['projectPath'],
    },
  },
  {
    name: 'gitlab_assign_reviewers_to_merge_request',
    description: 'Assigns reviewers to a GitLab Merge Request.',
    inputSchema: {
      type: 'object',
      properties: {
        mrUrl: {
          type: 'string',
          description: 'The URL of the GitLab Merge Request.',
        },
        reviewerIds: {
          type: 'array',
          items: {
            type: 'number',
          },
          description: 'An array of GitLab user IDs to assign as reviewers.',
        },
      },
      required: ['mrUrl', 'reviewerIds'],
    },
  },
  {
    name: 'gitlab_list_project_members',
    description: 'Lists all members (contributors) of a given GitLab project.',
    inputSchema: {
      type: 'object',
      properties: {
        mrUrl: {
          type: 'string',
          description: 'The URL of a GitLab Merge Request within the project.',
        },
      },
      required: ['mrUrl'],
    },
  },
  {
    name: 'gitlab_list_project_members_by_project_name',
    description:
      'Lists all members (contributors) of a given GitLab project by project name.',
    inputSchema: {
      type: 'object',
      properties: {
        projectName: {
          type: 'string',
          description: 'The name of the GitLab project.',
        },
      },
      required: ['projectName'],
    },
  },
  {
    name: 'gitlab_list_projects_by_name',
    description:
      'Filters GitLab projects by name using a fuzzy, case-insensitive match.',
    inputSchema: {
      type: 'object',
      properties: {
        projectName: {
          type: 'string',
          description: 'The name or partial name of the project to filter by.',
        },
      },
      required: ['projectName'],
    },
  },
  {
    name: 'gitlab_list_all_projects',
    description:
      'Lists all accessible GitLab projects. (Try to use list_projects_by_name as it is more efficient)',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'gitlab_list_all_releases',
    description: 'Fetches releases for a given GitLab project.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description:
            'The path of the GitLab project (e.g., "namespace/project-name").',
        },
      },
      required: ['projectPath'],
    },
  },
  {
    name: 'gitlab_list_releases_since_version',
    description:
      'Filters releases for a given GitLab project since a specific version.',
    inputSchema: {
      type: 'object',
      properties: {
        projectName: {
          type: 'string',
          description: 'The name or partial name of the GitLab project.',
        },
        sinceVersion: {
          type: 'string',
          description: 'The version to filter releases since (e.g., "1.0.0").',
        },
      },
      required: ['projectName', 'sinceVersion'],
    },
  },
  {
    name: 'gitlab_get_user_id_by_username',
    description: 'Retrieves the GitLab user ID for a given username.',
    inputSchema: {
      type: 'object',
      properties: {
        username: {
          type: 'string',
          description: 'The username of the GitLab user.',
        },
      },
      required: ['username'],
    },
  },
  {
    name: 'gitlab_get_user_activities',
    description:
      'Fetches activities for a given GitLab user by their username, optionally filtered by date.',
    inputSchema: {
      type: 'object',
      properties: {
        username: {
          type: 'string',
          description: 'The username of the GitLab user.',
        },
        sinceDate: {
          type: 'string',
          format: 'date',
          description:
            'Optional: Activities since this date (YYYY-MM-DD). Defaults to 1 day ago if not provided.',
        },
      },
      required: ['username'],
    },
  },
  {
    name: 'jira_get_ticket_details',
    description: 'Fetches detailed information about a Jira ticket.',
    inputSchema: {
      type: 'object',
      properties: {
        ticketId: {
          type: 'string',
          description: 'The ID of the Jira ticket (e.g., "JIRA-123").',
        },
      },
      required: ['ticketId'],
    },
  },
  {
    name: 'jira_get_ticket_comments',
    description: 'Fetches comments for a Jira ticket.',
    inputSchema: {
      type: 'object',
      properties: {
        ticketId: {
          type: 'string',
          description: 'The ID of the Jira ticket.',
        },
      },
      required: ['ticketId'],
    },
  },
  {
    name: 'jira_add_comment_to_ticket',
    description: 'Adds a comment to a Jira ticket.',
    inputSchema: {
      type: 'object',
      properties: {
        ticketId: {
          type: 'string',
          description: 'The ID of the Jira ticket.',
        },
        comment: {
          type: 'string',
          description: 'The comment to add to the ticket.',
        },
      },
      required: ['ticketId', 'comment'],
    },
  },
  {
    name: 'jira_search_tickets_by_jql',
    description:
      'Searches for Jira tickets using a JQL (Jira Query Language) string.',
    inputSchema: {
      type: 'object',
      properties: {
        jql: {
          type: 'string',
          description: 'The JQL query string.',
        },
      },
      required: ['jql'],
    },
  },
  {
    name: 'jira_create_ticket',
    description: 'Creates a new Jira ticket with given fields.',
    inputSchema: {
      type: 'object',
      properties: {
        fields: {
          type: 'object',
          description: 'Jira createIssue fields payload.',
        },
      },
      required: ['fields'],
    },
  },
  {
    name: 'jira_get_available_transitions',
    description: 'Fetches available transitions for a Jira ticket.',
    inputSchema: {
      type: 'object',
      properties: {
        ticketId: {
          type: 'string',
          description: 'The ID of the Jira ticket (e.g., "JIRA-123").',
        },
      },
      required: ['ticketId'],
    },
  },
  {
    name: 'jira_update_ticket',
    description: 'Updates a Jira ticket with standard fields like summary, description, labels, and story points.',
    inputSchema: {
      type: 'object',
      properties: {
        ticketId: {
          type: 'string',
          description: 'The ID or key of the Jira ticket to update.',
        },
        payload: {
          type: 'object',
          description: 'An object containing the fields to update.',
          properties: {
            summary: { type: 'string', description: 'The new summary for the ticket.' },
            description: { type: 'string', description: 'The new description for the ticket.' },
            labels: { type: 'array', items: { type: 'string' }, description: 'The labels to set on the ticket.' },
            assigneeAccountId: { type: 'string', description: 'The account ID of the new assignee.' },
            reporterAccountId: { type: 'string', description: 'The account ID of the new reporter.' },
            priorityId: { type: 'string', description: 'The ID of the new priority.' },
            fixVersions: { type: 'array', items: { type: 'string' }, description: 'The names of the fix versions.' },
            components: { type: 'array', items: { type: 'string' }, description: 'The names of the components.' },
            duedate: { type: 'string', description: 'The new due date in YYYY-MM-DD format.' },
          },
        },
      },
      required: ['ticketId', 'payload'],
    },
  },
  {
    name: 'jira_update_custom_fields',
    description: 'Updates custom fields on a Jira ticket.',
    inputSchema: {
      type: 'object',
      properties: {
        ticketId: {
          type: 'string',
          description: 'The ID or key of the Jira ticket to update.',
        },
        payload: {
          type: 'object',
          description: 'An object containing the custom fields to update. The keys of the object are the field names, and the values are the new values.',
        },
      },
      required: ['ticketId', 'payload'],
    },
  },
  {
    name: 'jira_update_ticket_story_point',
    description: 'Updates the story points value for a Jira ticket. Automatically finds the story points custom field (case-insensitive search for "story points", "story_points", etc.).',
    inputSchema: {
      type: 'object',
      properties: {
        ticketId: {
          type: 'string',
          description: 'The ID or key of the Jira ticket to update.',
        },
        storyPoints: {
          type: 'number',
          description: 'The story points value to set (e.g., 1, 2, 3, 5, 8, 13, etc.).',
        },
      },
      required: ['ticketId', 'storyPoints'],
    },
  },
  {
    name: 'jira_update_ticket_priority',
    description: 'Updates the priority value for a Jira ticket. Automatically finds the priority custom field (case-insensitive search for "Priority" or "priority"), fetches the allowed values for that field, and matches the provided priority name using fuzzy string matching. Accepts values like "Critical", "High", "Medium", "Low", etc., and will find the best match from the predefined options.',
    inputSchema: {
      type: 'object',
      properties: {
        ticketId: {
          type: 'string',
          description: 'The ID or key of the Jira ticket to update.',
        },
        priority: {
          type: 'string',
          description: 'The priority value to set (e.g., "Critical", "High", "Medium", "Low", "Highest", etc.).',
        },
      },
      required: ['ticketId', 'priority'],
    },
  },
  {
    name: 'jira_update_ticket_sprint',
    description: 'Updates the sprint assignment for a Jira ticket. Automatically finds the sprint custom field, fetches available sprints from the ticket\'s project boards, and matches the provided sprint name using fuzzy string matching. Accepts sprint names and will find the best match from available sprints.',
    inputSchema: {
      type: 'object',
      properties: {
        ticketId: {
          type: 'string',
          description: 'The ID or key of the Jira ticket to update.',
        },
        sprintName: {
          type: 'string',
          description: 'The sprint name to assign (e.g., "Sprint 1", "Release Sprint", "Bug Fix Sprint", etc.).',
        },
        boardId: {
          type: 'number',
          description: 'Optional: Specific board ID to fetch sprints from. If not provided, will search all boards associated with the ticket\'s project.',
        },
      },
      required: ['ticketId', 'sprintName'],
    },
  },
  {
    name: 'jira_transition_ticket',
    description: 'Transitions a Jira ticket to a new status by name.',
    inputSchema: {
      type: 'object',
      properties: {
        ticketId: {
          type: 'string',
          description: 'The ID or key of the Jira ticket to transition.',
        },
        statusName: {
          type: 'string',
          description: 'The name of the status to transition to. The tool will find the closest match.',
        },
      },
      required: ['ticketId', 'statusName'],
    },
  },
  {
    name: 'jira_get_all_fields',
    description: 'Fetches the list of all fields from Jira.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'jira_search_tickets',
    description: 'Searches for Jira tickets using multiple criteria. This is a convenience tool that builds JQL queries from simple parameters, making it easier for agents to search without writing complex JQL.',
    inputSchema: {
      type: 'object',
      properties: {
        projectKey: {
          type: 'string',
          description: 'Filter by project key or name. Supports fuzzy matching for partial names (e.g., "PROJ", "My Project").',
        },
        assigneeEmail: {
          type: 'string',
          description: 'Filter by assignee email, username, or display name. Supports fuzzy matching for names.',
        },
        assignedToMe: {
          type: 'boolean',
          description: 'Filter to tickets assigned to current user.',
        },
        statusCategory: {
          type: 'string',
          enum: ['To Do', 'In Progress', 'Done'],
          description: 'Filter by status category.',
        },
        status: {
          type: 'string',
          description: 'Filter by status with fuzzy matching. Accepts: "open", "progress", "review", "testing", "done/closed".',
        },
        priority: {
          type: 'string',
          description: 'Filter by priority with fuzzy matching. Accepts: "high/urgent/critical", "medium/normal", "low/minor".',
        },
        labels: {
          type: 'array',
          items: { type: 'string' },
          description: 'Filter by labels.',
        },
        labelsMatchAll: {
          type: 'boolean',
          description: 'If true, tickets must have ALL labels. If false, tickets with ANY label (default: false).',
        },
        updatedSince: {
          type: 'string',
          description: 'Updated since date (e.g., "-7d", "-1w", "-1M", "2024-01-01").',
        },
        updatedBefore: {
          type: 'string',
          description: 'Updated before date.',
        },
        createdSince: {
          type: 'string',
          description: 'Created since date.',
        },
        createdBefore: {
          type: 'string',
          description: 'Created before date.',
        },
        recentDays: {
          type: 'number',
          description: 'Show tickets updated in last N days (shortcut for updatedSince).',
        },
        issueType: {
          type: 'string',
          description: 'Filter by issue type with fuzzy matching. Accepts: "bug/defect", "story/feature", "task", "epic".',
        },
        reporter: {
          type: 'string',
          description: 'Filter by reporter email, username, or display name. Supports fuzzy matching.',
        },
        text: {
          type: 'string',
          description: 'Fuzzy search text across summary, description, and comments. Supports multiple keywords.',
        },
        maxResults: {
          type: 'number',
          description: 'Maximum number of results to return (default: 50).',
        },
        orderBy: {
          type: 'string',
          description: 'Order results by field (default: "updated DESC"). Examples: "created ASC", "priority DESC", "key ASC".',
        },
      },
    },
  },
  // New GitLab Pipeline/CI/CD Tools
  {
    name: 'gitlab_get_project_pipelines',
    description: 'Gets pipelines for a GitLab project, optionally filtered by branch/ref.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'The path of the GitLab project (e.g., "namespace/project-name").',
        },
        ref: {
          type: 'string',
          description: 'Optional: Branch or ref to filter pipelines.',
        },
      },
      required: ['projectPath'],
    },
  },
  {
    name: 'gitlab_get_merge_request_pipelines',
    description: 'Gets pipelines for a specific GitLab Merge Request.',
    inputSchema: {
      type: 'object',
      properties: {
        mrUrl: {
          type: 'string',
          description: 'The URL of the GitLab Merge Request.',
        },
      },
      required: ['mrUrl'],
    },
  },
  {
    name: 'gitlab_get_pipeline_details',
    description: 'Gets detailed information about a specific pipeline.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'The path of the GitLab project.',
        },
        pipelineId: {
          type: 'number',
          description: 'The ID of the pipeline.',
        },
      },
      required: ['projectPath', 'pipelineId'],
    },
  },
  {
    name: 'gitlab_get_pipeline_jobs',
    description: 'Gets jobs for a specific pipeline.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'The path of the GitLab project.',
        },
        pipelineId: {
          type: 'number',
          description: 'The ID of the pipeline.',
        },
      },
      required: ['projectPath', 'pipelineId'],
    },
  },
  {
    name: 'gitlab_get_job_logs',
    description: 'Gets logs for a specific job.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'The path of the GitLab project.',
        },
        jobId: {
          type: 'number',
          description: 'The ID of the job.',
        },
      },
      required: ['projectPath', 'jobId'],
    },
  },
  {
    name: 'gitlab_trigger_pipeline',
    description: 'Triggers a new pipeline for a specific branch/ref.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'The path of the GitLab project.',
        },
        ref: {
          type: 'string',
          description: 'The branch or ref to trigger the pipeline for.',
        },
        variables: {
          type: 'object',
          description: 'Optional: Pipeline variables as key-value pairs.',
        },
      },
      required: ['projectPath', 'ref'],
    },
  },
  {
    name: 'gitlab_retry_pipeline',
    description: 'Retries a failed pipeline.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'The path of the GitLab project.',
        },
        pipelineId: {
          type: 'number',
          description: 'The ID of the pipeline to retry.',
        },
      },
      required: ['projectPath', 'pipelineId'],
    },
  },
  {
    name: 'gitlab_cancel_pipeline',
    description: 'Cancels a running pipeline.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'The path of the GitLab project.',
        },
        pipelineId: {
          type: 'number',
          description: 'The ID of the pipeline to cancel.',
        },
      },
      required: ['projectPath', 'pipelineId'],
    },
  },
  // New GitLab Branch Management Tools
  {
    name: 'gitlab_list_branches',
    description: 'Lists all branches in a GitLab project.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'The path of the GitLab project.',
        },
      },
      required: ['projectPath'],
    },
  },
  {
    name: 'gitlab_create_branch',
    description: 'Creates a new branch in a GitLab project.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'The path of the GitLab project.',
        },
        branchName: {
          type: 'string',
          description: 'The name of the new branch.',
        },
        ref: {
          type: 'string',
          description: 'The branch or SHA to create the branch from.',
        },
      },
      required: ['projectPath', 'branchName', 'ref'],
    },
  },
  {
    name: 'gitlab_delete_branch',
    description: 'Deletes a branch from a GitLab project.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'The path of the GitLab project.',
        },
        branchName: {
          type: 'string',
          description: 'The name of the branch to delete.',
        },
      },
      required: ['projectPath', 'branchName'],
    },
  },
  {
    name: 'gitlab_get_branch_details',
    description: 'Gets detailed information about a specific branch.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'The path of the GitLab project.',
        },
        branchName: {
          type: 'string',
          description: 'The name of the branch.',
        },
      },
      required: ['projectPath', 'branchName'],
    },
  },
  // New GitLab Issue Management Tools
  {
    name: 'gitlab_list_project_issues',
    description: 'Lists issues in a GitLab project.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'The path of the GitLab project.',
        },
        state: {
          type: 'string',
          enum: ['opened', 'closed', 'all'],
          description: 'Filter issues by state.',
        },
      },
      required: ['projectPath'],
    },
  },
  {
    name: 'gitlab_get_issue_details',
    description: 'Gets detailed information about a specific GitLab issue.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'The path of the GitLab project.',
        },
        issueIid: {
          type: 'number',
          description: 'The internal ID of the issue.',
        },
      },
      required: ['projectPath', 'issueIid'],
    },
  },
  {
    name: 'gitlab_create_issue',
    description: 'Creates a new issue in a GitLab project.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'The path of the GitLab project.',
        },
        title: {
          type: 'string',
          description: 'The title of the issue.',
        },
        description: {
          type: 'string',
          description: 'The description of the issue.',
        },
        labels: {
          type: 'array',
          items: { type: 'string' },
          description: 'Labels to assign to the issue.',
        },
        assigneeIds: {
          type: 'array',
          items: { type: 'number' },
          description: 'User IDs to assign the issue to.',
        },
      },
      required: ['projectPath', 'title'],
    },
  },
  {
    name: 'gitlab_update_issue',
    description: 'Updates an existing GitLab issue.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'The path of the GitLab project.',
        },
        issueIid: {
          type: 'number',
          description: 'The internal ID of the issue.',
        },
        updates: {
          type: 'object',
          properties: {
            title: { type: 'string' },
            description: { type: 'string' },
            labels: { type: 'array', items: { type: 'string' } },
            assigneeIds: { type: 'array', items: { type: 'number' } },
            state: { type: 'string', enum: ['close', 'reopen'] },
          },
          description: 'Fields to update.',
        },
      },
      required: ['projectPath', 'issueIid', 'updates'],
    },
  },
  {
    name: 'gitlab_close_issue',
    description: 'Closes a GitLab issue.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'The path of the GitLab project.',
        },
        issueIid: {
          type: 'number',
          description: 'The internal ID of the issue.',
        },
      },
      required: ['projectPath', 'issueIid'],
    },
  },
  {
    name: 'gitlab_add_comment_to_issue',
    description: 'Adds a comment to a GitLab issue.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'The path of the GitLab project.',
        },
        issueIid: {
          type: 'number',
          description: 'The internal ID of the issue.',
        },
        body: {
          type: 'string',
          description: 'The comment text.',
        },
      },
      required: ['projectPath', 'issueIid', 'body'],
    },
  },
  {
    name: 'gitlab_get_issue_comments',
    description: 'Gets comments for a GitLab issue.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'The path of the GitLab project.',
        },
        issueIid: {
          type: 'number',
          description: 'The internal ID of the issue.',
        },
      },
      required: ['projectPath', 'issueIid'],
    },
  },
  // New JIRA Project Management Tools
  {
    name: 'jira_get_all_projects',
    description: 'Gets all accessible Jira projects.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'jira_get_project_details',
    description: 'Gets detailed information about a specific Jira project.',
    inputSchema: {
      type: 'object',
      properties: {
        projectKey: {
          type: 'string',
          description: 'The key of the Jira project.',
        },
      },
      required: ['projectKey'],
    },
  },
  {
    name: 'jira_get_project_components',
    description: 'Gets components for a Jira project.',
    inputSchema: {
      type: 'object',
      properties: {
        projectKey: {
          type: 'string',
          description: 'The key of the Jira project.',
        },
      },
      required: ['projectKey'],
    },
  },
  {
    name: 'jira_get_project_versions',
    description: 'Gets versions for a Jira project.',
    inputSchema: {
      type: 'object',
      properties: {
        projectKey: {
          type: 'string',
          description: 'The key of the Jira project.',
        },
      },
      required: ['projectKey'],
    },
  },
  {
    name: 'jira_get_all_boards',
    description: 'Gets all Jira boards accessible to the user.',
    inputSchema: {
      type: 'object',
      properties: {
        type: {
          type: 'string',
          enum: ['scrum', 'kanban'],
          description: 'Filter boards by type (optional).',
        },
        name: {
          type: 'string',
          description: 'Filter boards by name (optional).',
        }
      },
    },
  },
  {
    name: 'jira_get_board_details',
    description: 'Gets details of a specific Jira board.',
    inputSchema: {
      type: 'object',
      properties: {
        boardId: {
          type: 'number',
          description: 'The ID of the Jira board.',
        },
      },
      required: ['boardId'],
    },
  },
  {
    name: 'jira_find_boards',
    description: 'Finds and validates Jira boards using various criteria. Helpful for identifying the correct board ID when board discovery is not working as expected.',
    inputSchema: {
      type: 'object',
      properties: {
        projectKey: {
          type: 'string',
          description: 'Filter boards by project key (optional).',
        },
        boardName: {
          type: 'string',
          description: 'Filter boards by name (partial match, optional).',
        },
        boardId: {
          type: 'number',
          description: 'Get details of a specific board ID (optional).',
        },
        type: {
          type: 'string',
          enum: ['scrum', 'kanban'],
          description: 'Filter boards by type (optional).',
        },
        maxResults: {
          type: 'number',
          description: 'Maximum number of results to return (default: 50).',
        },
      },
    },
  },
  {
    name: 'jira_search_sprints',
    description: 'Searches for sprints in a specific Jira board by board name or ID.',
    inputSchema: {
      type: 'object',
      properties: {
        boardName: {
          type: 'string',
          description: 'Name of the board to search sprints in (case-insensitive partial match).',
        },
        boardId: {
          type: 'number',
          description: 'ID of the board to search sprints in (alternative to boardName).',
        },
        name: {
          type: 'string',
          description: 'Filter sprints by name (case-insensitive partial match).',
        },
        state: {
          type: 'string',
          enum: ['future', 'active', 'closed'],
          description: 'Filter sprints by state.',
        },
        maxResults: {
          type: 'number',
          description: 'Maximum number of results to return (default: 50).',
        },
      },
    },
  },
  {
    name: 'jira_get_sprint_details',
    description: 'Gets details of a specific sprint.',
    inputSchema: {
      type: 'object',
      properties: {
        sprintId: {
          type: 'number',
          description: 'The ID of the sprint.',
        },
      },
      required: ['sprintId'],
    },
  },
  {
    name: 'jira_get_sprints_for_board',
    description: 'Gets all sprints for a specific board.',
    inputSchema: {
      type: 'object',
      properties: {
        boardId: {
          type: 'number',
          description: 'The ID of the Jira board.',
        },
        state: {
          type: 'string',
          enum: ['future', 'active', 'closed'],
          description: 'Filter sprints by state (optional).',
        }
      },
      required: ['boardId'],
    },
  },
  {
    name: 'jira_get_sprint_issues',
    description: 'Gets all issues in a specific sprint.',
    inputSchema: {
      type: 'object',
      properties: {
        sprintId: {
          type: 'number',
          description: 'The ID of the sprint.',
        },
        maxResults: {
          type: 'number',
          description: 'Maximum number of results to return (default: 50).',
        },
        jql: {
          type: 'string',
          description: 'Additional JQL filter for the issues (optional).',
        },
      },
      required: ['sprintId'],
    },
  },
];

// Filter tools based on service availability
const availableTools = allTools.filter((tool) => {
  if (tool.name.startsWith('gitlab_')) {
    return !!gitlabService;
  }
  if (tool.name.startsWith('jira_')) {
    return !!jiraService;
  }
  return true;
});

// Initialize the MCP server
const server = new Server(
  { name: 'gitlab-jira-mcp-server', version: '1.0.0' },
  { capabilities: { tools: {} } },
);

// Handle tool listing
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools: availableTools };
});

// Handle tool calls
server.setRequestHandler(
  CallToolRequestSchema,
  async (request: CallToolRequest) => {
    const { name, arguments: args } = request.params;

    try {
      switch (name) {
        case 'gitlab_get_merge_request_details': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { mrUrl } = args as { mrUrl: string };
          const result =
            await gitlabService.getMergeRequestDetailsFromUrl(mrUrl);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'gitlab_get_file_content': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { mrUrl, filePath, sha } = args as {
            mrUrl: string;
            filePath: string;
            sha: string;
          };
          const result = await gitlabService.getFileContentFromMrUrl(
            mrUrl,
            filePath,
            sha,
          );
          return {
            content: [
              {
                type: 'text',
                text: result,
              },
            ],
          };
        }

        case 'gitlab_add_comment_to_merge_request': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { mrUrl, commentBody, discussionId, position } = args as {
            mrUrl: string;
            commentBody: string;
            discussionId?: string;
            position?: GitLabPosition;
          };
          const result = await gitlabService.addCommentToMergeRequestFromUrl(
            mrUrl,
            commentBody,
            discussionId,
            position,
          );
          return {
            content: [
              {
                type: 'text',
                text: `Comment added successfully: ${JSON.stringify(result)}`,
              },
            ],
          };
        }

        case 'gitlab_list_merge_requests': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectPath } = args as { projectPath: string };
          const result = await gitlabService.listMergeRequests(projectPath);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'gitlab_assign_reviewers_to_merge_request': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { mrUrl, reviewerIds } = args as {
            mrUrl: string;
            reviewerIds: number[];
          };
          const result =
            await gitlabService.assignReviewersToMergeRequestFromUrl(
              mrUrl,
              reviewerIds,
            );
          return {
            content: [
              {
                type: 'text',
                text: `Reviewers assigned successfully: ${JSON.stringify(
                  result,
                )}`,
              },
            ],
          };
        }

        case 'gitlab_list_project_members': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { mrUrl } = args as { mrUrl: string };
          const result = await gitlabService.listProjectMembersFromMrUrl(mrUrl);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'gitlab_list_project_members_by_project_name': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectName } = args as { projectName: string };
          const result =
            await gitlabService.listProjectMembersByProjectName(projectName);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'gitlab_list_projects_by_name': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectName } = args as { projectName: string };
          const result = await gitlabService.filterProjectsByName(projectName);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'gitlab_list_all_projects': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const result = await gitlabService.listProjects();
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'gitlab_list_all_releases': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectPath } = args as { projectPath: string };
          const result = await gitlabService.getReleases(projectPath);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'gitlab_list_releases_since_version': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectName, sinceVersion } = args as {
            projectName: string;
            sinceVersion: string;
          };
          const projects =
            await gitlabService.filterProjectsByName(projectName);
          if (projects.length === 0) {
            throw new Error(`No project found with name: ${projectName}`);
          }
          const projectPath = projects[0].path_with_namespace;
          const result = await gitlabService.filterReleasesSinceVersion(
            projectPath,
            sinceVersion,
          );
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'gitlab_get_user_id_by_username': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { username } = args as { username: string };
          const userId = await gitlabService.getUserIdByUsername(username);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify({ userId }, null, 2),
              },
            ],
          };
        }

        case 'gitlab_get_user_activities': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { username, sinceDate } = args as {
            username: string;
            sinceDate?: string;
          };
          const userId = await gitlabService.getUserIdByUsername(username);
          let activities;
          if (sinceDate) {
            activities = await gitlabService.getUserActivities(
              userId,
              new Date(sinceDate),
            );
          } else {
            const oneDayAgo = new Date();
            oneDayAgo.setDate(oneDayAgo.getDate() - 1);
            activities = await gitlabService.getUserActivities(
              userId,
              oneDayAgo,
            );
          }
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(activities, null, 2),
              },
            ],
          };
        }

        case 'jira_get_ticket_details': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const { ticketId } = args as { ticketId: string };
          const result = await jiraService.getTicketDetails(ticketId);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'jira_get_ticket_comments': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const { ticketId } = args as { ticketId: string };
          const result = await jiraService.getTicketComments(ticketId);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'jira_add_comment_to_ticket': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const { ticketId, comment } = args as {
            ticketId: string;
            comment: string;
          };
          await jiraService.addCommentToTicket(ticketId, comment);
          return {
            content: [
              {
                type: 'text',
                text: `Comment added to Jira ticket ${ticketId} successfully.`,
              },
            ],
          };
        }

        case 'jira_search_tickets_by_jql': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const { jql } = args as { jql: string };
          const result = await jiraService.searchTicketsByJQL(jql);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'jira_create_ticket': {
            if (!jiraService) {
                throw new Error('Jira service is not initialized.');
            }
            const { fields } = args as { fields: any };
            await jiraService.createTicket(fields);
            return {
                content: [
                    {
                        type: 'text',
                        text: 'Jira ticket created successfully.',
                    },
                ],
            };
        }

        case 'jira_get_available_transitions': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const { ticketId } = args as { ticketId: string };
          const result = await jiraService.getAvailableTransitions(ticketId);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'jira_update_ticket': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const { ticketId, payload } = args as {
            ticketId: string;
            payload: JiraTicketUpdatePayload;
          };
          await jiraService.updateTicket(ticketId, payload);
          return {
            content: [
              {
                type: 'text',
                text: `Ticket ${ticketId} updated successfully.`,
              },
            ],
          };
        }

        case 'jira_update_custom_fields': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const { ticketId, payload } = args as {
            ticketId: string;
            payload: JiraCustomFieldUpdatePayload;
          };
          await jiraService.updateCustomFields(ticketId, payload);
          return {
            content: [
              {
                type: 'text',
                text: `Custom fields for ticket ${ticketId} updated successfully.`,
              },
            ],
          };
        }

        case 'jira_update_ticket_story_point': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const { ticketId, storyPoints } = args as {
            ticketId: string;
            storyPoints: number;
          };
          await jiraService.updateTicketStoryPoints(ticketId, storyPoints);
          return {
            content: [
              {
                type: 'text',
                text: `Story points for ticket ${ticketId} updated to ${storyPoints} successfully.`,
              },
            ],
          };
        }

        case 'jira_update_ticket_priority': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const { ticketId, priority } = args as {
            ticketId: string;
            priority: string;
          };
          await jiraService.updateTicketPriority(ticketId, priority);
          return {
            content: [
              {
                type: 'text',
                text: `Priority for ticket ${ticketId} updated to ${priority} successfully.`,
              },
            ],
          };
        }

        case 'jira_update_ticket_sprint': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const { ticketId, sprintName, boardId } = args as {
            ticketId: string;
            sprintName: string;
            boardId?: number;
          };
          await jiraService.updateTicketSprint(ticketId, sprintName, boardId);
          return {
            content: [
              {
                type: 'text',
                text: `Sprint for ticket ${ticketId} updated to ${sprintName} successfully.`,
              },
            ],
          };
        }

        case 'jira_transition_ticket': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const { ticketId, statusName } = args as {
            ticketId: string;
            statusName: string;
          };
          const availableTransitions = await jiraService.getAvailableTransitions(ticketId);
          if (availableTransitions.length === 0) {
            throw new Error(`No available transitions for ticket ${ticketId}.`);
          }

          const bestMatch = availableTransitions.reduce(
            (best: { distance: number; transition: any }, transition: any) => {
              const distance = levenshteinDistance(statusName, transition.name);
              if (distance < best.distance) {
                return { distance, transition };
              }
              return best;
            },
            { distance: Infinity, transition: availableTransitions[0] },
          );

          await jiraService.transitionTicket(ticketId, bestMatch.transition.id);
          return {
            content: [
              {
                type: 'text',
                text: `Ticket ${ticketId} transitioned to ${bestMatch.transition.name} successfully.`,
              },
            ],
          };
        }

        case 'jira_get_all_fields': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const result = await jiraService.getAllFields();
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'jira_search_tickets': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const searchCriteria = args as {
            projectKey?: string;
            assigneeEmail?: string;
            assignedToMe?: boolean;
            statusCategory?: 'To Do' | 'In Progress' | 'Done';
            status?: string;
            priority?: string;
            labels?: string[];
            labelsMatchAll?: boolean;
            updatedSince?: string;
            updatedBefore?: string;
            createdSince?: string;
            createdBefore?: string;
            recentDays?: number;
            issueType?: string;
            reporter?: string;
            text?: string;
            maxResults?: number;
            orderBy?: string;
          };
          const result = await jiraService.searchTickets(searchCriteria);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        // New GitLab Pipeline/CI/CD handlers
        case 'gitlab_get_project_pipelines': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectPath, ref } = args as { projectPath: string; ref?: string };
          const result = await gitlabService.getProjectPipelines(projectPath, ref);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'gitlab_get_merge_request_pipelines': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { mrUrl } = args as { mrUrl: string };
          const result = await gitlabService.getMergeRequestPipelines(mrUrl);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'gitlab_get_pipeline_details': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectPath, pipelineId } = args as { projectPath: string; pipelineId: number };
          const result = await gitlabService.getPipelineDetails(projectPath, pipelineId);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'gitlab_get_pipeline_jobs': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectPath, pipelineId } = args as { projectPath: string; pipelineId: number };
          const result = await gitlabService.getPipelineJobs(projectPath, pipelineId);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'gitlab_get_job_logs': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectPath, jobId } = args as { projectPath: string; jobId: number };
          const result = await gitlabService.getJobLogs(projectPath, jobId);
          return {
            content: [
              {
                type: 'text',
                text: result,
              },
            ],
          };
        }

        case 'gitlab_trigger_pipeline': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectPath, ref, variables } = args as { projectPath: string; ref: string; variables?: Record<string, string> };
          const result = await gitlabService.triggerPipeline(projectPath, ref, variables);
          return {
            content: [
              {
                type: 'text',
                text: `Pipeline triggered successfully: ${JSON.stringify(result, null, 2)}`,
              },
            ],
          };
        }

        case 'gitlab_retry_pipeline': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectPath, pipelineId } = args as { projectPath: string; pipelineId: number };
          const result = await gitlabService.retryPipeline(projectPath, pipelineId);
          return {
            content: [
              {
                type: 'text',
                text: `Pipeline retry triggered successfully: ${JSON.stringify(result, null, 2)}`,
              },
            ],
          };
        }

        case 'gitlab_cancel_pipeline': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectPath, pipelineId } = args as { projectPath: string; pipelineId: number };
          const result = await gitlabService.cancelPipeline(projectPath, pipelineId);
          return {
            content: [
              {
                type: 'text',
                text: `Pipeline cancelled successfully: ${JSON.stringify(result, null, 2)}`,
              },
            ],
          };
        }

        // New GitLab Branch Management handlers
        case 'gitlab_list_branches': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectPath } = args as { projectPath: string };
          const result = await gitlabService.listBranches(projectPath);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'gitlab_create_branch': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectPath, branchName, ref } = args as { projectPath: string; branchName: string; ref: string };
          const result = await gitlabService.createBranch(projectPath, branchName, ref);
          return {
            content: [
              {
                type: 'text',
                text: `Branch created successfully: ${JSON.stringify(result, null, 2)}`,
              },
            ],
          };
        }

        case 'gitlab_delete_branch': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectPath, branchName } = args as { projectPath: string; branchName: string };
          await gitlabService.deleteBranch(projectPath, branchName);
          return {
            content: [
              {
                type: 'text',
                text: `Branch ${branchName} deleted successfully.`,
              },
            ],
          };
        }

        case 'gitlab_get_branch_details': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectPath, branchName } = args as { projectPath: string; branchName: string };
          const result = await gitlabService.getBranchDetails(projectPath, branchName);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        // New GitLab Issue Management handlers
        case 'gitlab_list_project_issues': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectPath, state } = args as { projectPath: string; state?: 'opened' | 'closed' | 'all' };
          const result = await gitlabService.listProjectIssues(projectPath, state);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'gitlab_get_issue_details': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectPath, issueIid } = args as { projectPath: string; issueIid: number };
          const result = await gitlabService.getIssueDetails(projectPath, issueIid);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'gitlab_create_issue': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectPath, title, description, labels, assigneeIds } = args as { 
            projectPath: string; 
            title: string; 
            description?: string; 
            labels?: string[]; 
            assigneeIds?: number[] 
          };
          const result = await gitlabService.createIssue(projectPath, title, description, labels, assigneeIds);
          return {
            content: [
              {
                type: 'text',
                text: `Issue created successfully: ${JSON.stringify(result, null, 2)}`,
              },
            ],
          };
        }

        case 'gitlab_update_issue': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectPath, issueIid, updates } = args as { 
            projectPath: string; 
            issueIid: number; 
            updates: {
              title?: string;
              description?: string;
              labels?: string[];
              assigneeIds?: number[];
              state?: 'close' | 'reopen';
            };
          };
          const result = await gitlabService.updateIssue(projectPath, issueIid, updates);
          return {
            content: [
              {
                type: 'text',
                text: `Issue updated successfully: ${JSON.stringify(result, null, 2)}`,
              },
            ],
          };
        }

        case 'gitlab_close_issue': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectPath, issueIid } = args as { projectPath: string; issueIid: number };
          const result = await gitlabService.closeIssue(projectPath, issueIid);
          return {
            content: [
              {
                type: 'text',
                text: `Issue closed successfully: ${JSON.stringify(result, null, 2)}`,
              },
            ],
          };
        }

        case 'gitlab_add_comment_to_issue': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectPath, issueIid, body } = args as { projectPath: string; issueIid: number; body: string };
          const result = await gitlabService.addCommentToIssue(projectPath, issueIid, body);
          return {
            content: [
              {
                type: 'text',
                text: `Comment added successfully: ${JSON.stringify(result, null, 2)}`,
              },
            ],
          };
        }

        case 'gitlab_get_issue_comments': {
          if (!gitlabService) {
            throw new Error('GitLab service is not initialized.');
          }
          const { projectPath, issueIid } = args as { projectPath: string; issueIid: number };
          const result = await gitlabService.getIssueComments(projectPath, issueIid);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        // New JIRA Project Management handlers
        case 'jira_get_all_projects': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const result = await jiraService.getAllProjects();
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'jira_get_project_details': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const { projectKey } = args as { projectKey: string };
          const result = await jiraService.getProjectDetails(projectKey);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'jira_get_project_components': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const { projectKey } = args as { projectKey: string };
          const result = await jiraService.getProjectComponents(projectKey);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'jira_get_project_versions': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const { projectKey } = args as { projectKey: string };
          const result = await jiraService.getProjectVersions(projectKey);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'jira_get_all_boards': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const { type, name } = args as {
            type?: 'scrum' | 'kanban';
            name?: string;
            projectKeyOrId?: string;
            maxResults?: number;
          };
          const result = await jiraService.getAllBoards({
            type,
            name,
          });
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'jira_get_board_details': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const { boardId } = args as { boardId: number };
          const result = await jiraService.getBoardById(boardId);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'jira_find_boards': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const { projectKey, boardName, boardId, type, maxResults } = args as {
            projectKey?: string;
            boardName?: string;
            boardId?: number;
            type?: 'scrum' | 'kanban';
            maxResults?: number;
          };
          const result = await jiraService.findBoards({
            projectKey,
            boardName,
            boardId,
            type,
            maxResults,
          });
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'jira_search_sprints': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const { boardName, boardId, name, state, maxResults } = args as {
            boardName?: string;
            boardId?: number;
            name?: string;
            state?: 'future' | 'active' | 'closed';
            maxResults?: number;
          };
          
          if (!boardName && !boardId) {
            throw new Error('Either boardName or boardId must be provided.');
          }
          
          const result = await jiraService.searchSprints({
            boardName,
            boardId,
            name,
            state,
            maxResults,
          });
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'jira_get_sprint_details': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const { sprintId } = args as { sprintId: number };
          const result = await jiraService.getSprintById(sprintId);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'jira_get_sprints_for_board': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const { boardId, state } = args as {
            boardId: number;
            state?: 'future' | 'active' | 'closed';
            maxResults?: number;
          };
          const result = await jiraService.getSprintsForBoard(boardId, {
            state,
          });
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'jira_get_sprint_issues': {
          if (!jiraService) {
            throw new Error('Jira service is not initialized.');
          }
          const { sprintId, maxResults, jql } = args as {
            sprintId: number;
            maxResults?: number;
            jql?: string;
          };
          const result = await jiraService.getIssuesForSprint(sprintId, {
            maxResults,
            jql,
          });
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    } catch (error) {
      throw new Error(
        `Error executing tool ${name}: ${error instanceof Error ? error.message : String(error)}`,
      );
    }
  },
);

// Start the server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('GitLab/Jira MCP server started');
  while (true) {
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
}

main().catch((error) => {
  console.error('Failed to start server:', error);
  process.exit(1);
});