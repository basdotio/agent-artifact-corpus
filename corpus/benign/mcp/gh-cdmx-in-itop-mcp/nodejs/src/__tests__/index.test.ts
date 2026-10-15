import { describe, test, expect, jest, beforeEach } from '@jest/globals';
import axios from 'axios';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Import our module after mocking
import { ITopClientImpl } from '../index';

describe('iTop MCP Server Node.js', () => {
  let client: ITopClientImpl;

  beforeEach(() => {
    client = new ITopClientImpl('https://test.itop.com', 'testuser', 'testpass', '1.4');
    jest.clearAllMocks();
  });

  describe('ITopClient', () => {
    test('should initialize correctly', () => {
      expect(client['baseUrl']).toBe('https://test.itop.com');
      expect(client['username']).toBe('testuser');
      expect(client['password']).toBe('testpass');
      expect(client['version']).toBe('1.4');
      expect(client['restUrl']).toBe('https://test.itop.com/webservices/rest.php');
    });

    test('should normalize URL by removing trailing slash', () => {
      const clientWithSlash = new ITopClientImpl('https://test.itop.com/', 'user', 'pass');
      expect(clientWithSlash['baseUrl']).toBe('https://test.itop.com');
    });

    test('should make successful API request', async () => {
      const mockResponse = {
        data: {
          code: 0,
          message: 'OK',
          objects: {}
        }
      };

      mockedAxios.post.mockResolvedValue(mockResponse);

      const result = await client.makeRequest({ operation: 'list_operations' });

      expect(result.code).toBe(0);
      expect(result.message).toBe('OK');
      expect(mockedAxios.post).toHaveBeenCalledWith(
        'https://test.itop.com/webservices/rest.php',
        expect.any(URLSearchParams),
        expect.objectContaining({
          headers: {
            'User-Agent': 'iTop-MCP-Server-NodeJS/1.0',
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          timeout: 30000
        })
      );
    });

    test('should handle HTTP errors', async () => {
      const error = {
        response: {
          status: 404,
          data: 'Not Found'
        }
      };

      mockedAxios.post.mockRejectedValue(error);

      await expect(client.makeRequest({ operation: 'test' }))
        .rejects
        .toThrow('HTTP error 404: Not Found');
    });

    test('should handle network errors', async () => {
      const error = {
        request: {},
        message: 'Network Error'
      };

      mockedAxios.post.mockRejectedValue(error);

      await expect(client.makeRequest({ operation: 'test' }))
        .rejects
        .toThrow('Request failed: Network Error');
    });

    test('should handle request setup errors', async () => {
      const error = {
        message: 'Request setup failed'
      };

      mockedAxios.post.mockRejectedValue(error);

      await expect(client.makeRequest({ operation: 'test' }))
        .rejects
        .toThrow('Request setup failed: Request setup failed');
    });
  });

  describe('Support Ticket Formatting', () => {
    test('should format support tickets in table format', () => {
      const mockObjects = {
        'ticket1': {
          code: 0,
          fields: {
            ref: 'R-000001',
            title: 'Test ticket 1',
            status: 'new',
            sla_tto_passed: '1',
            sla_ttr_passed: '0',
            start_date: '2024-01-01',
            close_date: ''
          }
        },
        'ticket2': {
          code: 0,
          fields: {
            ref: 'R-000002',
            title: 'Test ticket 2',
            status: 'resolved',
            sla_tto_passed: '1',
            sla_ttr_passed: '1',
            start_date: '2024-01-02',
            close_date: '2024-01-03'
          }
        }
      };

      // Import the function dynamically to avoid issues with mocking
      const { formatSupportTicketsOutput } = require('../index');
      const result = formatSupportTicketsOutput(mockObjects, 'UserRequest', 'table', true);

      expect(result).toContain('Found 2 UserRequest tickets');
      expect(result).toContain('R-000001');
      expect(result).toContain('R-000002');
      expect(result).toContain('✓'); // SLA passed
      expect(result).toContain('✗'); // SLA failed
      expect(result).toContain('|'); // Table formatting
    });

    test('should format support tickets in summary format', () => {
      const mockObjects = {
        'ticket1': {
          code: 0,
          fields: {
            status: 'new',
            sla_tto_passed: '1',
            sla_ttr_passed: '0'
          }
        },
        'ticket2': {
          code: 0,
          fields: {
            status: 'new',
            sla_tto_passed: '0',
            sla_ttr_passed: '0'
          }
        },
        'ticket3': {
          code: 0,
          fields: {
            status: 'resolved',
            sla_tto_passed: '1',
            sla_ttr_passed: '1'
          }
        }
      };

      const { formatSupportTicketsOutput } = require('../index');
      const result = formatSupportTicketsOutput(mockObjects, 'UserRequest', 'summary', true);

      expect(result).toContain('📊 **Summary**');
      expect(result).toContain('Total tickets: 3');
      expect(result).toContain('SLA breached: 2'); // 2 tickets have SLA breaches
      expect(result).toContain('new: 2');
      expect(result).toContain('resolved: 1');
    });

    test('should format support tickets in detailed format', () => {
      const mockObjects = {
        'ticket1': {
          code: 0,
          fields: {
            ref: 'R-000001',
            title: 'Test ticket',
            status: 'new',
            sla_tto_passed: '1',
            sla_ttr_passed: '0',
            start_date: '2024-01-01',
            caller_name: 'John Doe',
            agent_name: 'Jane Smith',
            org_name: 'ACME Corp'
          }
        }
      };

      const { formatSupportTicketsOutput } = require('../index');
      const result = formatSupportTicketsOutput(mockObjects, 'UserRequest', 'detailed', true);

      expect(result).toContain('🎫 **R-000001**');
      expect(result).toContain('Title: Test ticket');
      expect(result).toContain('Status: new');
      expect(result).toContain('SLA TTO: ✓ On Time');
      expect(result).toContain('SLA TTR: ✗ Breached');
      expect(result).toContain('Caller: John Doe');
      expect(result).toContain('Agent: Jane Smith');
      expect(result).toContain('Organization: ACME Corp');
    });
  });

  describe('Configuration', () => {
    test('should have correct support ticket fields configuration', () => {
      const { SUPPORT_TICKET_FIELDS } = require('../index');

      expect(SUPPORT_TICKET_FIELDS).toHaveProperty('UserRequest');
      expect(SUPPORT_TICKET_FIELDS).toHaveProperty('Incident');

      const urConfig = SUPPORT_TICKET_FIELDS.UserRequest;
      expect(urConfig.defaultFields).toContain('sla_tto_passed');
      expect(urConfig.defaultFields).toContain('sla_ttr_passed');

      const incidentConfig = SUPPORT_TICKET_FIELDS.Incident;
      expect(incidentConfig.defaultFields).toContain('priority');
      expect(incidentConfig.defaultFields).toContain('impact');
      expect(incidentConfig.defaultFields).toContain('urgency');
    });
  });

  describe('Environment Variables', () => {
    const originalEnv = process.env;

    beforeEach(() => {
      jest.resetModules();
      process.env = { ...originalEnv };
    });

    afterEach(() => {
      process.env = originalEnv;
    });

    test('should throw error when environment variables are missing', () => {
      delete process.env.ITOP_BASE_URL;
      delete process.env.ITOP_USER;
      delete process.env.ITOP_PASSWORD;

      const { getITopClient } = require('../index');

      expect(() => getITopClient()).toThrow('Missing required environment variables');
    });

    test('should use environment variables when available', () => {
      process.env.ITOP_BASE_URL = 'https://env.itop.com';
      process.env.ITOP_USER = 'envuser';
      process.env.ITOP_PASSWORD = 'envpass';
      process.env.ITOP_VERSION = '1.5';

      const { getITopClient } = require('../index');
      const client = getITopClient();

      expect(client['baseUrl']).toBe('https://env.itop.com');
      expect(client['username']).toBe('envuser');
      expect(client['password']).toBe('envpass');
      expect(client['version']).toBe('1.5');
    });
  });
});
