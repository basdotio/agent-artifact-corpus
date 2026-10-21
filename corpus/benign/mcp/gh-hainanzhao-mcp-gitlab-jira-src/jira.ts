/**
 * Shared types for Jira integration
 */

export interface JiraConfig {
  apiBaseUrl: string;
  userEmail: string;
  apiToken: string;
}

export interface JiraTicket {
  id: string;
  key: string;
  summary: string;
  description?: string;
  status: string;
  assignee?: {
    displayName: string;
    emailAddress: string;
    accountId: string;
  } | null;
  priority?: string;
  labels?: string[];
  updated?: string;
  created?: string;
  issueType?: string;
  reporter?: {
    displayName: string;
    emailAddress: string;
    accountId: string;
  } | null;
  // Allow for dynamic additional fields
  [key: string]: any;
}

export interface JiraComment {
  id: string;
  author: {
    displayName: string;
    emailAddress: string;
  };
  body: string;
  created: string;
  updated: string;
}

export interface JiraTransition {
  id: string;
  name: string;
  to: {
    name: string;
  };
}

export interface JiraTicketUpdatePayload {
  summary?: string;
  description?: string;
  labels?: string[];
  assigneeAccountId?: string;
  reporterAccountId?: string;
  priorityId?: string;
  fixVersions?: string[];
  components?: string[];
  duedate?: string; // YYYY-MM-DD
}

export interface JiraCustomFieldUpdatePayload {
  [key: string]: string | number | boolean | string[] | null | undefined;
}

export interface JiraTicketTransitionPayload {
  transitionId: string;
}

export interface JiraField {
  id: string;
  name: string;
  custom: boolean;
  orderable: boolean;
  navigable: boolean;
  searchable: boolean;
  clauseNames: string[];
  schema: {
    type: string;
    custom?: string;
    customId?: number;
  };
}

export interface JiraSprint {
  id: number;
  self: string;
  state: 'future' | 'active' | 'closed';
  name: string;
  startDate?: string;
  endDate?: string;
  completeDate?: string;
  originBoardId?: number;
  goal?: string;
}

export interface JiraBoard {
  id: number;
  self: string;
  name: string;
  type: 'scrum' | 'kanban' | 'simple';
  location?: {
    displayName: string;
    projectId: number;
    projectKey: string;
    projectName: string;
  };
}
