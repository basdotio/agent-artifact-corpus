import { JiraService } from './jira.service';

// Mock the jira.js client
jest.mock('jira.js', () => ({
  Version3Client: jest.fn().mockImplementation(() => ({
    issues: {
      getIssue: jest.fn(),
      editIssue: jest.fn(),
    },
    issueFields: {
      getFields: jest.fn(),
    },
  })),
}));

describe('JiraService transformations', () => {
  let jiraService: JiraService;
  let mockClient: any;

  beforeEach(() => {
    jiraService = new JiraService({
      apiBaseUrl: 'https://test.atlassian.net',
      userEmail: 'test@example.com',
      apiToken: 'test-token',
    });
    mockClient = (jiraService as any).client;
  });

  describe('getTicketDetails', () => {
    it('should transform issue fields into flattened format', async () => {
      const mockIssue = {
        id: 'ISSUE-123',
        key: 'PROJ-123',
        fields: {
          summary: 'Test Issue',
          description: {
            type: 'doc',
            version: 1,
            content: [
              {
                type: 'paragraph',
                content: [{ type: 'text', text: 'This is a test description' }],
              },
            ],
          },
          status: { name: 'In Progress' },
          priority: { name: 'High' },
          labels: ['bug', 'frontend'],
          updated: '2023-01-01T00:00:00.000Z',
          created: '2022-12-01T00:00:00.000Z',
          issuetype: { name: 'Bug' },
          assignee: {
            displayName: 'John Doe',
            emailAddress: 'john@example.com',
            accountId: 'user123',
          },
          reporter: {
            displayName: 'Jane Smith',
            emailAddress: 'jane@example.com',
            accountId: 'user456',
          },
          customfield_10001: 'Custom Value',
          customfield_10002: { name: 'Epic Name' },
          customfield_10003: null, // Should be filtered out
          customfield_10004: '', // Should be filtered out
          attachment: [{ filename: 'test.pdf' }], // Should be filtered out
        },
      };

      const mockFields = [
        {
          id: 'customfield_10001',
          name: 'Story Points',
          custom: true,
          orderable: true,
          navigable: true,
          searchable: true,
          clauseNames: ['cf[10001]'],
          schema: { type: 'number' },
        },
        {
          id: 'customfield_10002',
          name: 'Epic Link',
          custom: true,
          orderable: true,
          navigable: true,
          searchable: true,
          clauseNames: ['cf[10002]'],
          schema: { type: 'string' },
        },
      ];

      mockClient.issues.getIssue.mockResolvedValue(mockIssue);
      mockClient.issueFields.getFields.mockResolvedValue(mockFields);

      const result = await jiraService.getTicketDetails('PROJ-123');

      expect(result).toEqual({
        id: 'ISSUE-123',
        key: 'PROJ-123',
        summary: 'Test Issue',
        description: 'This is a test description',
        status: 'In Progress',
        priority: 'High',
        labels: ['bug', 'frontend'],
        updated: '2023-01-01T00:00:00.000Z',
        created: '2022-12-01T00:00:00.000Z',
        issueType: 'Bug',
        assignee: {
          displayName: 'John Doe',
          emailAddress: 'john@example.com',
          accountId: 'user123',
        },
        reporter: {
          displayName: 'Jane Smith',
          emailAddress: 'jane@example.com',
          accountId: 'user456',
        },
        storyPoints: 'Custom Value',
        epicLink: 'Epic Name',
      });

      expect(mockClient.issues.getIssue).toHaveBeenCalledWith({
        issueIdOrKey: 'PROJ-123',
        expand: ['names', 'schema', 'operations', 'editmeta', 'changelog', 'renderedFields'],
      });
    });

    it('should handle null/undefined assignee and reporter', async () => {
      const mockIssue = {
        id: 'ISSUE-124',
        key: 'PROJ-124',
        fields: {
          summary: 'Test Issue Without Assignee',
          description: 'Simple description',
          status: { name: 'Open' },
          priority: { name: 'Medium' },
          labels: [],
          updated: '2023-01-01T00:00:00.000Z',
          created: '2022-12-01T00:00:00.000Z',
          issuetype: { name: 'Task' },
          assignee: null,
          reporter: null,
        },
      };

      mockClient.issues.getIssue.mockResolvedValue(mockIssue);
      mockClient.issueFields.getFields.mockResolvedValue([]);

      const result = await jiraService.getTicketDetails('PROJ-124');

      expect(result.assignee).toBeNull();
      expect(result.reporter).toBeNull();
    });
  });

  describe('updateTicketPriority', () => {
    it('should update ticket priority using exact match from allowed values', async () => {
      const mockFields = [
        {
          id: 'customfield_10010',
          name: 'Priority',
          custom: true,
          orderable: true,
          navigable: true,
          searchable: true,
          clauseNames: ['cf[10010]'],
          schema: { type: 'option' },
        },
      ];

      const mockIssueWithEditMeta = {
        id: 'ISSUE-123',
        key: 'PROJ-123',
        editmeta: {
          fields: {
            'customfield_10010': {
              allowedValues: [
                { id: '1', value: 'Low' },
                { id: '2', value: 'Medium' },
                { id: '3', value: 'High' },
                { id: '4', value: 'Critical' },
              ],
            },
          },
        },
      };

      mockClient.issueFields.getFields.mockResolvedValue(mockFields);
      mockClient.issues.getIssue.mockResolvedValue(mockIssueWithEditMeta);
      mockClient.issues.editIssue.mockResolvedValue({});

      await jiraService.updateTicketPriority('PROJ-123', 'High');

      expect(mockClient.issues.getIssue).toHaveBeenCalledWith({
        issueIdOrKey: 'PROJ-123',
        expand: ['editmeta'],
      });

      expect(mockClient.issues.editIssue).toHaveBeenCalledWith({
        issueIdOrKey: 'PROJ-123',
        fields: {
          'customfield_10010': { id: '3', value: 'High' },
        },
      });
    });

    it('should use fuzzy matching when exact match is not found', async () => {
      const mockFields = [
        {
          id: 'customfield_10010',
          name: 'Priority',
          custom: true,
          orderable: true,
          navigable: true,
          searchable: true,
          clauseNames: ['cf[10010]'],
          schema: { type: 'option' },
        },
      ];

      const mockIssueWithEditMeta = {
        id: 'ISSUE-123',
        key: 'PROJ-123',
        editmeta: {
          fields: {
            'customfield_10010': {
              allowedValues: [
                { id: '1', value: 'Low' },
                { id: '2', value: 'Medium' },
                { id: '3', value: 'High' },
                { id: '4', value: 'Critical' },
              ],
            },
          },
        },
      };

      mockClient.issueFields.getFields.mockResolvedValue(mockFields);
      mockClient.issues.getIssue.mockResolvedValue(mockIssueWithEditMeta);
      mockClient.issues.editIssue.mockResolvedValue({});

      // Test fuzzy matching: 'hi' should match 'High'
      await jiraService.updateTicketPriority('PROJ-123', 'hi');

      expect(mockClient.issues.editIssue).toHaveBeenCalledWith({
        issueIdOrKey: 'PROJ-123',
        fields: {
          'customfield_10010': { id: '3', value: 'High' },
        },
      });
    });

    it('should throw error when no close match is found', async () => {
      const mockFields = [
        {
          id: 'customfield_10010',
          name: 'Priority',
          custom: true,
          orderable: true,
          navigable: true,
          searchable: true,
          clauseNames: ['cf[10010]'],
          schema: { type: 'option' },
        },
      ];

      const mockIssueWithEditMeta = {
        id: 'ISSUE-123',
        key: 'PROJ-123',
        editmeta: {
          fields: {
            'customfield_10010': {
              allowedValues: [
                { id: '1', value: 'Low' },
                { id: '2', value: 'Medium' },
                { id: '3', value: 'High' },
                { id: '4', value: 'Critical' },
              ],
            },
          },
        },
      };

      mockClient.issueFields.getFields.mockResolvedValue(mockFields);
      mockClient.issues.getIssue.mockResolvedValue(mockIssueWithEditMeta);

      // Test fuzzy matching that should fail: 'xyz' should not match anything well
      await expect(jiraService.updateTicketPriority('PROJ-123', 'xyz123')).rejects.toThrow(
        'No close match found for "xyz123". Available options: Low, Medium, High, Critical',
      );
    });

    it('should throw error when Priority field is not found', async () => {
      const mockFields = [
        {
          id: 'customfield_10030',
          name: 'Other Field',
          custom: true,
          orderable: true,
          navigable: true,
          searchable: true,
          clauseNames: ['cf[10030]'],
          schema: { type: 'string' },
        },
      ];

      mockClient.issueFields.getFields.mockResolvedValue(mockFields);

      await expect(jiraService.updateTicketPriority('PROJ-123', 'High')).rejects.toThrow(
        'Could not retrieve custom field ID for Priority.',
      );
    });

    it('should throw error when field has no allowed values', async () => {
      const mockFields = [
        {
          id: 'customfield_10010',
          name: 'Priority',
          custom: true,
          orderable: true,
          navigable: true,
          searchable: true,
          clauseNames: ['cf[10010]'],
          schema: { type: 'option' },
        },
      ];

      const mockIssueWithEditMeta = {
        id: 'ISSUE-123',
        key: 'PROJ-123',
        editmeta: {
          fields: {
            'customfield_10010': {
              // No allowedValues property
            },
          },
        },
      };

      mockClient.issueFields.getFields.mockResolvedValue(mockFields);
      mockClient.issues.getIssue.mockResolvedValue(mockIssueWithEditMeta);

      await expect(jiraService.updateTicketPriority('PROJ-123', 'High')).rejects.toThrow(
        'customfield_10010 does not have allowed values (may not be an option field).',
      );
    });
  });

  describe('updateTicketSprint', () => {
    beforeEach(() => {
      // Add the makeAgileRequest method mock
      (jiraService as any).makeAgileRequest = jest.fn();
    });

    it('should update ticket sprint using exact match from available sprints', async () => {
      const mockFields = [
        {
          id: 'customfield_10020',
          name: 'Sprint',
          custom: true,
          orderable: true,
          navigable: true,
          searchable: true,
          clauseNames: ['cf[10020]'],
          schema: { custom: 'com.pyxis.greenhopper.jira:gh-sprint' },
        },
      ];

      const mockIssueWithProject = {
        id: 'ISSUE-123',
        key: 'PROJ-123',
        fields: {
          project: { key: 'PROJ' },
        },
      };

      const mockBoards = {
        values: [
          { 
            id: 1, 
            name: 'Test Board', 
            type: 'scrum',
            location: { 
              projectKey: 'PROJ',
              projectName: 'Test Project' 
            }
          },
        ],
        total: 1,
        isLast: true,
      };

      const mockSprints = {
        values: [
          { id: 1, name: 'Sprint 1', state: 'active' },
          { id: 2, name: 'Sprint 2', state: 'future' },
          { id: 3, name: 'Bug Fix Sprint', state: 'active' },
        ],
        total: 3,
        isLast: true,
      };

      mockClient.issueFields.getFields.mockResolvedValue(mockFields);
      mockClient.issues.getIssue
        .mockResolvedValueOnce(mockIssueWithProject)  // for getTicketProjectKey
        .mockResolvedValueOnce(mockIssueWithProject); // for actual update
      (jiraService as any).makeAgileRequest
        .mockResolvedValueOnce(mockBoards)    // for getAllBoards
        .mockResolvedValueOnce(mockSprints);  // for getSprintsForBoard
      mockClient.issues.editIssue.mockResolvedValue({});

      await jiraService.updateTicketSprint('PROJ-123', 'Sprint 1');

      expect(mockClient.issues.editIssue).toHaveBeenCalledWith({
        issueIdOrKey: 'PROJ-123',
        fields: {
          'customfield_10020': [1],
        },
      });
    });

    it('should use fuzzy matching when exact match is not found', async () => {
      const mockFields = [
        {
          id: 'customfield_10020',
          name: 'Sprint',
          custom: true,
          orderable: true,
          navigable: true,
          searchable: true,
          clauseNames: ['cf[10020]'],
          schema: { custom: 'com.pyxis.greenhopper.jira:gh-sprint' },
        },
      ];

      const mockIssueWithProject = {
        id: 'ISSUE-123',
        key: 'PROJ-123',
        fields: {
          project: { key: 'PROJ' },
        },
      };

      const mockBoards = {
        values: [
          { 
            id: 1, 
            name: 'Test Board', 
            type: 'scrum',
            location: { 
              projectKey: 'PROJ',
              projectName: 'Test Project' 
            }
          },
        ],
        total: 1,
        isLast: true,
      };

      const mockSprints = {
        values: [
          { id: 1, name: 'Sprint 1', state: 'active' },
          { id: 2, name: 'Sprint 2', state: 'future' },
          { id: 3, name: 'Bug Fix Sprint', state: 'active' },
        ],
        total: 3,
        isLast: true,
      };

      mockClient.issueFields.getFields.mockResolvedValue(mockFields);
      mockClient.issues.getIssue
        .mockResolvedValueOnce(mockIssueWithProject)
        .mockResolvedValueOnce(mockIssueWithProject);
      (jiraService as any).makeAgileRequest
        .mockResolvedValueOnce(mockBoards)
        .mockResolvedValueOnce(mockSprints);
      mockClient.issues.editIssue.mockResolvedValue({});

      // Test fuzzy matching: 'bug fix' should match 'Bug Fix Sprint'
      await jiraService.updateTicketSprint('PROJ-123', 'bug fix');

      expect(mockClient.issues.editIssue).toHaveBeenCalledWith({
        issueIdOrKey: 'PROJ-123',
        fields: {
          'customfield_10020': [3],
        },
      });
    });

    it('should throw error when no close match is found', async () => {
      const mockFields = [
        {
          id: 'customfield_10020',
          name: 'Sprint',
          custom: true,
          orderable: true,
          navigable: true,
          searchable: true,
          clauseNames: ['cf[10020]'],
          schema: { custom: 'com.pyxis.greenhopper.jira:gh-sprint' },
        },
      ];

      const mockIssueWithProject = {
        id: 'ISSUE-123',
        key: 'PROJ-123',
        fields: {
          project: { key: 'PROJ' },
        },
      };

      const mockBoards = {
        values: [
          { 
            id: 1, 
            name: 'Test Board', 
            type: 'scrum',
            location: { 
              projectKey: 'PROJ',
              projectName: 'Test Project' 
            }
          },
        ],
        total: 1,
        isLast: true,
      };

      const mockSprints = {
        values: [
          { id: 1, name: 'Sprint 1', state: 'active' },
          { id: 2, name: 'Sprint 2', state: 'future' },
        ],
        total: 2,
        isLast: true,
      };

      mockClient.issueFields.getFields.mockResolvedValue(mockFields);
      mockClient.issues.getIssue.mockResolvedValue(mockIssueWithProject);
      (jiraService as any).makeAgileRequest
        .mockResolvedValueOnce(mockBoards)
        .mockResolvedValueOnce(mockSprints);

      await expect(jiraService.updateTicketSprint('PROJ-123', 'completely-unrelated-name-xyz')).rejects.toThrow(
        'No close match found for "completely-unrelated-name-xyz". Available sprints: Sprint 1 (active), Sprint 2 (future)',
      );
    });

    it('should throw error when Sprint field is not found', async () => {
      const mockFields = [
        {
          id: 'customfield_10030',
          name: 'Other Field',
          custom: true,
          orderable: true,
          navigable: true,
          searchable: true,
          clauseNames: ['cf[10030]'],
          schema: { type: 'string' },
        },
      ];

      mockClient.issueFields.getFields.mockResolvedValue(mockFields);

      await expect(jiraService.updateTicketSprint('PROJ-123', 'Sprint 1')).rejects.toThrow(
        'Could not retrieve custom field ID for Sprint.',
      );
    });

    it('should throw error when no boards found for project', async () => {
      const mockFields = [
        {
          id: 'customfield_10020',
          name: 'Sprint',
          custom: true,
          orderable: true,
          navigable: true,
          searchable: true,
          clauseNames: ['cf[10020]'],
          schema: { custom: 'com.pyxis.greenhopper.jira:gh-sprint' },
        },
      ];

      const mockIssueWithProject = {
        id: 'ISSUE-123',
        key: 'PROJ-123',
        fields: {
          project: { key: 'PROJ' },
        },
      };

      const mockEmptyBoards = {
        values: [],
        total: 0,
        isLast: true,
      };

      mockClient.issueFields.getFields.mockResolvedValue(mockFields);
      mockClient.issues.getIssue.mockResolvedValue(mockIssueWithProject);
      (jiraService as any).makeAgileRequest.mockResolvedValue(mockEmptyBoards);

      await expect(jiraService.updateTicketSprint('PROJ-123', 'Sprint 1')).rejects.toThrow(
        'No boards found for project PROJ. Available boards:',
      );
    });
  });

  describe('pagination handling', () => {
    beforeEach(() => {
      // Add the makeAgileRequest method mock
      (jiraService as any).makeAgileRequest = jest.fn();
    });

    it('should handle pagination when fetching all boards', async () => {
      const page1Response = {
        values: [
          { id: 1, name: 'Board 1', type: 'scrum', location: { projectKey: 'PROJ1' } },
          { id: 2, name: 'Board 2', type: 'kanban', location: { projectKey: 'PROJ2' } },
        ],
        total: 4,
        startAt: 0,
        maxResults: 50,
        isLast: false,
      };

      const page2Response = {
        values: [
          { id: 3, name: 'Board 3', type: 'scrum', location: { projectKey: 'PROJ3' } },
          { id: 4, name: 'Board 4', type: 'kanban', location: { projectKey: 'PROJ4' } },
        ],
        total: 4,
        startAt: 50,
        maxResults: 50,
        isLast: true,
      };

      const mockFn = jest.fn()
        .mockResolvedValueOnce(page1Response)
        .mockResolvedValueOnce(page2Response);
      
      (jiraService as any).makeAgileRequest = mockFn;

      // Use simplified API that always fetches all pages
      const result = await jiraService.getAllBoards();

      expect(result.values).toHaveLength(4);
      expect(result.values[0].name).toBe('Board 1');
      expect(result.values[3].name).toBe('Board 4');
      expect(result.total).toBe(4);
      expect(result.isLast).toBe(true);

      // Verify both API calls were made with correct pagination
      expect(mockFn).toHaveBeenCalledTimes(2);
      expect(mockFn).toHaveBeenNthCalledWith(1, '/board?startAt=0&maxResults=50');
      expect(mockFn).toHaveBeenNthCalledWith(2, '/board?startAt=50&maxResults=50');
    });

    it('should handle pagination when fetching sprints for a board', async () => {
      const page1Response = {
        values: [
          { id: 1, name: 'Sprint 1', state: 'active' },
          { id: 2, name: 'Sprint 2', state: 'future' },
        ],
        total: 3,
        startAt: 0,
        maxResults: 50,
        isLast: false,
      };

      const page2Response = {
        values: [
          { id: 3, name: 'Sprint 3', state: 'closed' },
        ],
        total: 3,
        startAt: 50,
        maxResults: 50,
        isLast: true,
      };

      (jiraService as any).makeAgileRequest
        .mockResolvedValueOnce(page1Response)
        .mockResolvedValueOnce(page2Response);

      // Use simplified API that always fetches all pages
      const result = await jiraService.getSprintsForBoard(123);

      expect(result.values).toHaveLength(3);
      expect(result.values[0].name).toBe('Sprint 1');
      expect(result.values[2].name).toBe('Sprint 3');
      expect(result.total).toBe(3);
      expect(result.isLast).toBe(true);

      // Verify both API calls were made with correct pagination
      expect((jiraService as any).makeAgileRequest).toHaveBeenCalledTimes(2);
      expect((jiraService as any).makeAgileRequest).toHaveBeenNthCalledWith(1, '/board/123/sprint?startAt=0&maxResults=50');
      expect((jiraService as any).makeAgileRequest).toHaveBeenNthCalledWith(2, '/board/123/sprint?startAt=50&maxResults=50');
    });
  });
});