#!/usr/bin/env ruby
# frozen_string_literal: true

require 'google/apis/gmail_v1'
require 'google/apis/calendar_v3'
require 'google/apis/people_v1'
require 'googleauth'
require 'googleauth/stores/file_token_store'
require 'fileutils'
require 'json'
require 'mail'
require 'base64'

# Gmail Manager - Google CLI Integration for Email Operations
# Version: 3.0.0
# Scopes: Gmail (MODIFY), Calendar, Contacts
class GmailManager
  GMAIL_SCOPE = Google::Apis::GmailV1::AUTH_GMAIL_MODIFY
  CALENDAR_SCOPE = Google::Apis::CalendarV3::AUTH_CALENDAR
  CONTACTS_SCOPE = Google::Apis::PeopleV1::AUTH_CONTACTS

  CREDENTIALS_PATH = File.join(Dir.home, '.claude', '.google', 'client_secret.json')
  TOKEN_PATH = File.join(Dir.home, '.claude', '.google', 'token.json')

  # Exit codes
  EXIT_SUCCESS = 0
  EXIT_OPERATION_FAILED = 1
  EXIT_AUTH_ERROR = 2
  EXIT_API_ERROR = 3
  EXIT_INVALID_ARGS = 4

  def initialize
    @gmail_service = Google::Apis::GmailV1::GmailService.new
    @gmail_service.client_options.application_name = 'Claude Email Skill'
    @gmail_service.authorization = authorize
  end

  # Authorize using shared OAuth token with three scopes
  def authorize
    client_id = Google::Auth::ClientId.from_file(CREDENTIALS_PATH)
    token_store = Google::Auth::Stores::FileTokenStore.new(file: TOKEN_PATH)

    authorizer = Google::Auth::UserAuthorizer.new(
      client_id,
      [CALENDAR_SCOPE, CONTACTS_SCOPE, GMAIL_SCOPE],
      token_store
    )

    user_id = 'default'
    credentials = authorizer.get_credentials(user_id)

    if credentials.nil?
      url = authorizer.get_authorization_url(base_url: 'urn:ietf:wg:oauth:2.0:oob')
      output_json({
        status: 'error',
        error_code: 'AUTH_REQUIRED',
        message: 'Authorization required. Please visit the URL and enter the code.',
        auth_url: url,
        instructions: [
          '1. Visit the authorization URL',
          '2. Grant access to Gmail, Calendar, and Contacts',
          '3. Copy the authorization code',
          "4. Run: ruby #{__FILE__} auth <code>"
        ]
      })
      exit EXIT_AUTH_ERROR
    end

    credentials
  end

  # Complete OAuth authorization with code
  def complete_auth(code)
    client_id = Google::Auth::ClientId.from_file(CREDENTIALS_PATH)
    token_store = Google::Auth::Stores::FileTokenStore.new(file: TOKEN_PATH)

    authorizer = Google::Auth::UserAuthorizer.new(
      client_id,
      [CALENDAR_SCOPE, CONTACTS_SCOPE, GMAIL_SCOPE],
      token_store
    )

    user_id = 'default'
    credentials = authorizer.get_and_store_credentials_from_code(
      user_id: user_id,
      code: code,
      base_url: 'urn:ietf:wg:oauth:2.0:oob'
    )

    output_json({
      status: 'success',
      message: 'Authorization complete. Token stored successfully.',
      token_path: TOKEN_PATH,
      scopes: [GMAIL_SCOPE, CALENDAR_SCOPE, CONTACTS_SCOPE]
    })
  rescue StandardError => e
    output_json({
      status: 'error',
      error_code: 'AUTH_FAILED',
      message: "Authorization failed: #{e.message}"
    })
    exit EXIT_AUTH_ERROR
  end

  # Send email with automatic BCC to arlenagreer@gmail.com
  def send_email(to:, subject:, body_html:, cc: [], bcc: [], attachments: [])
    # Ensure BCC always includes arlenagreer@gmail.com
    bcc = Array(bcc)
    bcc << 'arlenagreer@gmail.com' unless bcc.include?('arlenagreer@gmail.com')

    mail = Mail.new do
      to       to
      cc       cc if cc.any?
      bcc      bcc if bcc.any?
      subject  subject

      html_part do
        content_type 'text/html; charset=UTF-8'
        body body_html
      end
    end

    # Add attachments if provided
    if attachments.any?
      attachments.each do |attachment_path|
        if File.exist?(attachment_path)
          mail.add_file(attachment_path)
        else
          raise "Attachment file not found: #{attachment_path}"
        end
      end
    end

    # Ruby API client handles Base64 encoding automatically
    message_object = Google::Apis::GmailV1::Message.new(raw: mail.to_s)

    result = @gmail_service.send_user_message('me', message_object)

    output_json({
      status: 'success',
      operation: 'send',
      message_id: result.id,
      thread_id: result.thread_id,
      recipients: {
        to: Array(to),
        cc: Array(cc),
        bcc: bcc
      },
      subject: subject
    })
  rescue Google::Apis::Error => e
    output_json({
      status: 'error',
      error_code: 'API_ERROR',
      operation: 'send',
      message: "Gmail API error: #{e.message}",
      details: e.body
    })
    exit EXIT_API_ERROR
  rescue StandardError => e
    output_json({
      status: 'error',
      error_code: 'SEND_FAILED',
      operation: 'send',
      message: "Failed to send email: #{e.message}"
    })
    exit EXIT_OPERATION_FAILED
  end

  # Create draft email with automatic BCC to arlenagreer@gmail.com
  def draft_email(to:, subject:, body_html:, cc: [], bcc: [], attachments: [])
    # Ensure BCC always includes arlenagreer@gmail.com
    bcc = Array(bcc)
    bcc << 'arlenagreer@gmail.com' unless bcc.include?('arlenagreer@gmail.com')

    mail = Mail.new do
      to       to
      cc       cc if cc.any?
      bcc      bcc if bcc.any?
      subject  subject

      html_part do
        content_type 'text/html; charset=UTF-8'
        body body_html
      end
    end

    # Add attachments if provided
    if attachments.any?
      attachments.each do |attachment_path|
        if File.exist?(attachment_path)
          mail.add_file(attachment_path)
        else
          raise "Attachment file not found: #{attachment_path}"
        end
      end
    end

    # Ruby API client handles Base64 encoding automatically
    message_object = Google::Apis::GmailV1::Message.new(raw: mail.to_s)
    draft_object = Google::Apis::GmailV1::Draft.new(message: message_object)

    result = @gmail_service.create_user_draft('me', draft_object)

    output_json({
      status: 'success',
      operation: 'draft',
      draft_id: result.id,
      message_id: result.message.id,
      thread_id: result.message.thread_id,
      recipients: {
        to: Array(to),
        cc: Array(cc),
        bcc: bcc
      },
      subject: subject
    })
  rescue Google::Apis::Error => e
    output_json({
      status: 'error',
      error_code: 'API_ERROR',
      operation: 'draft',
      message: "Gmail API error: #{e.message}",
      details: e.body
    })
    exit EXIT_API_ERROR
  rescue StandardError => e
    output_json({
      status: 'error',
      error_code: 'DRAFT_FAILED',
      operation: 'draft',
      message: "Failed to create draft: #{e.message}"
    })
    exit EXIT_OPERATION_FAILED
  end

  # List messages (future capability enabled by GMAIL_MODIFY scope)
  def list_messages(query: nil, max_results: 10)
    list_params = {
      max_results: max_results
    }
    list_params[:q] = query if query

    result = @gmail_service.list_user_messages('me', **list_params)

    messages = []
    if result.messages
      result.messages.each do |msg|
        message = @gmail_service.get_user_message('me', msg.id, format: 'full')
        messages << {
          id: message.id,
          thread_id: message.thread_id,
          snippet: message.snippet,
          from: extract_header(message, 'From'),
          to: extract_header(message, 'To'),
          subject: extract_header(message, 'Subject'),
          date: extract_header(message, 'Date')
        }
      end
    end

    output_json({
      status: 'success',
      operation: 'list',
      query: query,
      count: messages.length,
      messages: messages
    })
  rescue Google::Apis::Error => e
    output_json({
      status: 'error',
      error_code: 'API_ERROR',
      operation: 'list',
      message: "Gmail API error: #{e.message}",
      details: e.body
    })
    exit EXIT_API_ERROR
  rescue StandardError => e
    output_json({
      status: 'error',
      error_code: 'LIST_FAILED',
      operation: 'list',
      message: "Failed to list messages: #{e.message}"
    })
    exit EXIT_OPERATION_FAILED
  end

  private

  # Extract header value from message
  def extract_header(message, header_name)
    header = message.payload.headers.find { |h| h.name == header_name }
    header&.value
  end

  # Output JSON to stdout
  def output_json(data)
    puts JSON.pretty_generate(data)
  end
end

# CLI Interface
def usage
  puts <<~USAGE
    Gmail Manager - Google CLI Integration for Email Operations
    Version: 3.0.0

    Usage:
      #{File.basename($PROGRAM_NAME)} <command> [options]

    Commands:
      auth <code>           Complete OAuth authorization with code
      send                  Send email
      draft                 Create email draft
      list                  List messages (optional query)
      sync                  Sync credentials from 1Password to local cache

    Send/Draft Options (JSON via stdin):
      {
        "to": ["email@example.com"],
        "subject": "Subject line",
        "body_html": "<html>...</html>",
        "cc": ["cc@example.com"],          # Optional
        "bcc": ["bcc@example.com"],        # Optional (auto-adds arlenagreer@gmail.com)
        "attachments": ["/path/to/file"]   # Optional - array of absolute file paths
      }

    List Options (JSON via stdin):
      {
        "query": "is:unread",              # Optional Gmail search query
        "max_results": 10                  # Optional, default 10
      }

    Examples:
      # Complete OAuth authorization
      #{File.basename($PROGRAM_NAME)} auth YOUR_AUTH_CODE

      # Send email
      echo '{"to":["test@example.com"],"subject":"Test","body_html":"<p>Hello</p>"}' | #{File.basename($PROGRAM_NAME)} send

      # Create draft
      echo '{"to":["test@example.com"],"subject":"Draft","body_html":"<p>Draft</p>"}' | #{File.basename($PROGRAM_NAME)} draft

      # Send email with attachment
      echo '{"to":["test@example.com"],"subject":"Report","body_html":"<p>Please see attached report.</p>","attachments":["/path/to/report.pdf"]}' | #{File.basename($PROGRAM_NAME)} send

      # List unread messages
      echo '{"query":"is:unread","max_results":5}' | #{File.basename($PROGRAM_NAME)} list

    Exit Codes:
      0 - Success
      1 - Operation failed
      2 - Authentication error
      3 - API error
      4 - Invalid arguments
  USAGE
end

# Main execution
if __FILE__ == $PROGRAM_NAME
  if ARGV.empty?
    usage
    exit GmailManager::EXIT_INVALID_ARGS
  end

  command = ARGV[0]

  # Handle auth command separately (doesn't require initialized service)
  if command == 'auth'
    if ARGV.length < 2
      puts JSON.pretty_generate({
        status: 'error',
        error_code: 'MISSING_CODE',
        message: 'Authorization code required',
        usage: "#{File.basename($PROGRAM_NAME)} auth <code>"
      })
      exit GmailManager::EXIT_INVALID_ARGS
    end

    # Create temporary manager just for auth completion
    temp_manager = GmailManager.allocate
    temp_manager.complete_auth(ARGV[1])
    exit GmailManager::EXIT_SUCCESS
  end

  # For all other commands, create manager (which requires authorization)
  manager = GmailManager.new

  case command

  when 'send'
    input = JSON.parse(STDIN.read, symbolize_names: true)

    unless input[:to] && input[:subject] && input[:body_html]
      puts JSON.pretty_generate({
        status: 'error',
        error_code: 'MISSING_REQUIRED_FIELDS',
        message: 'Required fields: to, subject, body_html'
      })
      exit GmailManager::EXIT_INVALID_ARGS
    end

    manager.send_email(
      to: input[:to],
      subject: input[:subject],
      body_html: input[:body_html],
      cc: input[:cc] || [],
      bcc: input[:bcc] || [],
      attachments: input[:attachments] || []
    )

  when 'draft'
    input = JSON.parse(STDIN.read, symbolize_names: true)

    unless input[:to] && input[:subject] && input[:body_html]
      puts JSON.pretty_generate({
        status: 'error',
        error_code: 'MISSING_REQUIRED_FIELDS',
        message: 'Required fields: to, subject, body_html'
      })
      exit GmailManager::EXIT_INVALID_ARGS
    end

    manager.draft_email(
      to: input[:to],
      subject: input[:subject],
      body_html: input[:body_html],
      cc: input[:cc] || [],
      bcc: input[:bcc] || [],
      attachments: input[:attachments] || []
    )

  when 'list'
    input = STDIN.read.strip
    options = input.empty? ? {} : JSON.parse(input, symbolize_names: true)

    manager.list_messages(
      query: options[:query],
      max_results: options[:max_results] || 10
    )

  when 'sync'
    # Sync credentials from 1Password to local cache
    require_relative '../../../lib/onepassword_helper'

    if OnePasswordHelper.available?
      begin
        token_path = OnePasswordHelper.write_google_token_cache
        client_path = OnePasswordHelper.write_google_client_cache

        puts JSON.pretty_generate({
          status: 'success',
          operation: 'sync',
          message: 'Credentials synced from 1Password',
          files_updated: [token_path, client_path]
        })
      rescue StandardError => e
        puts JSON.pretty_generate({
          status: 'error',
          error_code: 'SYNC_FAILED',
          operation: 'sync',
          message: "Failed to sync from 1Password: #{e.message}"
        })
        exit GmailManager::EXIT_OPERATION_FAILED
      end
    else
      puts JSON.pretty_generate({
        status: 'error',
        error_code: '1PASSWORD_UNAVAILABLE',
        operation: 'sync',
        message: '1Password CLI is not available or not authenticated. Run: op signin'
      })
      exit GmailManager::EXIT_AUTH_ERROR
    end

  else
    puts JSON.pretty_generate({
      status: 'error',
      error_code: 'INVALID_COMMAND',
      message: "Unknown command: #{command}",
      valid_commands: ['auth', 'send', 'draft', 'list', 'sync']
    })
    usage
    exit GmailManager::EXIT_INVALID_ARGS
  end

  exit GmailManager::EXIT_SUCCESS
end
