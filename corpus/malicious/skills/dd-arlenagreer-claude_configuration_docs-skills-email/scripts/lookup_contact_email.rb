#!/usr/bin/env ruby
# Ruby 3.3.7 required for google-apis-people_v1 gem

# Google Contacts Email Lookup Script
#
# Purpose: Query Google Contacts by exact name match and return email address
# Usage: ./lookup_contact_email.rb --name "First Last"
# Output: JSON with email or error
# Exit codes: 0=success, 1=no match, 2=auth error, 3=api error, 4=invalid args

require 'optparse'
require 'json'
require 'fileutils'
require 'google/apis/people_v1'
require 'googleauth'
require 'googleauth/stores/file_token_store'

# Script version
VERSION = '1.0.0'

# Configuration constants
SCOPE = Google::Apis::PeopleV1::AUTH_CONTACTS
CREDENTIALS_PATH = File.join(Dir.home, '.claude', '.google', 'client_secret.json')
TOKEN_PATH = File.join(Dir.home, '.claude', '.google', 'token.json')
OOB_URI = 'urn:ietf:wg:oauth:2.0:oob'

# Preferred email overrides for specific contacts
# These take precedence over Google Contacts lookup
PREFERRED_EMAILS = {
  'mark whitney' => 'mark@dreamanager.com',
  'julie whitney' => 'julie@dreamanager.com',
  'rose fletcher' => 'rose@dreamanager.com'
  # Ed Korkuch handled separately based on context
}.freeze

# Authorize with Google OAuth 2.0
def authorize
  # Check if credentials file exists
  unless File.exist?(CREDENTIALS_PATH)
    puts JSON.generate({
      status: 'error',
      code: 'AUTH_ERROR',
      message: "Credentials file not found at #{CREDENTIALS_PATH}",
      query: nil
    })
    exit 2  # Authentication error
  end

  # Load client secrets
  begin
    client_id = Google::Auth::ClientId.from_file(CREDENTIALS_PATH)
  rescue => e
    puts JSON.generate({
      status: 'error',
      code: 'AUTH_ERROR',
      message: "Failed to load credentials: #{e.message}",
      query: nil
    })
    exit 2  # Authentication error
  end

  # Create token store
  token_store = Google::Auth::Stores::FileTokenStore.new(file: TOKEN_PATH)
  authorizer = Google::Auth::UserAuthorizer.new(client_id, SCOPE, token_store)

  # Get user credentials (this will use cached token if available)
  user_id = 'default'
  credentials = authorizer.get_credentials(user_id)

  # If no valid credentials, prompt for authorization
  if credentials.nil?
    url = authorizer.get_authorization_url(base_url: OOB_URI)

    puts "Open the following URL in your browser and authorize the application:"
    puts url
    puts "\nEnter the authorization code:"

    code = gets.chomp

    begin
      credentials = authorizer.get_and_store_credentials_from_code(
        user_id: user_id,
        code: code,
        base_url: OOB_URI
      )
    rescue => e
      puts JSON.generate({
        status: 'error',
        code: 'AUTH_ERROR',
        message: "Authorization failed: #{e.message}",
        query: nil
      })
      exit 2  # Authentication error
    end
  end

  # Automatically refresh token if expired
  begin
    credentials.refresh! if credentials.expired?
  rescue => e
    puts JSON.generate({
      status: 'error',
      code: 'AUTH_ERROR',
      message: "Token refresh failed: #{e.message}",
      query: nil
    })
    exit 2  # Authentication error
  end

  credentials
end

# Look up contact email by exact name match
def lookup_contact(name_query)
  # Authorize and get credentials
  credentials = authorize

  # Initialize People API service
  service = Google::Apis::PeopleV1::PeopleServiceService.new
  service.authorization = credentials

  # Split the name query into parts for matching
  name_parts = name_query.strip.split(/\s+/)

  if name_parts.length < 2
    return {
      status: 'error',
      code: 'NO_MATCH_FOUND',
      message: 'Please provide both first and last name (e.g., "John Doe")',
      query: name_query
    }
  end

  # Extract first and last name (ignoring middle names)
  query_first = name_parts.first.downcase
  query_last = name_parts.last.downcase

  # Check for preferred email override
  name_normalized = "#{query_first} #{query_last}"
  if PREFERRED_EMAILS.key?(name_normalized)
    return {
      status: 'success',
      email: PREFERRED_EMAILS[name_normalized],
      name: name_query,
      note: 'Using preferred email address override'
    }
  end

  begin
    # Fetch all contacts with names and email addresses
    response = service.list_person_connections(
      'people/me',
      person_fields: 'names,emailAddresses',
      page_size: 1000
    )

    # Search for exact name match (case-insensitive)
    matching_contacts = []

    if response.connections
      response.connections.each do |person|
        next unless person.names && person.email_addresses

        person.names.each do |name|
          # Case-insensitive comparison (Decision 003)
          if name.given_name&.downcase == query_first &&
             name.family_name&.downcase == query_last

            # Find primary email or first available email
            primary_email = person.email_addresses.find { |e| e.metadata&.primary }
            email = primary_email || person.email_addresses.first
            email_count = person.email_addresses.length

            if email&.value
              matching_contacts << {
                name: "#{name.given_name} #{name.family_name}",
                email: email.value,
                contact_id: person.resource_name,
                email_count: email_count
              }
            end
          end
        end
      end
    end

    # Return results
    if matching_contacts.empty?
      {
        status: 'error',
        code: 'NO_MATCH_FOUND',
        message: "No contact found matching '#{name_query}'",
        query: name_query
      }
    elsif matching_contacts.length == 1
      # Single match found
      contact = matching_contacts.first
      result = {
        status: 'success',
        email: contact[:email],
        name: contact[:name],
        matched_contact_id: contact[:contact_id]
      }
      # Add note if contact has multiple email addresses
      if contact[:email_count] > 1
        result[:note] = "Contact has #{contact[:email_count]} email addresses. Returning primary/first."
      end
      result
    else
      # Multiple matches found - return first (Decision 001: pending, but implementing option A)
      contact = matching_contacts.first
      result = {
        status: 'success',
        email: contact[:email],
        name: contact[:name],
        matched_contact_id: contact[:contact_id],
        note: "Multiple contacts found with this name. Returning first match."
      }
      # Add additional note if contact also has multiple emails
      if contact[:email_count] > 1
        result[:note] += " Contact has #{contact[:email_count]} email addresses."
      end
      result
    end

  rescue Google::Apis::Error => e
    {
      status: 'error',
      code: 'API_ERROR',
      message: "Google API error: #{e.message}",
      query: name_query
    }
  rescue => e
    {
      status: 'error',
      code: 'API_ERROR',
      message: "Unexpected error: #{e.message}",
      query: name_query
    }
  end
end

# Parse command-line arguments
def parse_arguments
  options = {}

  parser = OptionParser.new do |opts|
    opts.banner = "Usage: #{File.basename($0)} --name \"First Last\""
    opts.separator ""
    opts.separator "Google Contacts Email Lookup Script"
    opts.separator "Queries Google Contacts for exact name match and returns email address"
    opts.separator ""
    opts.separator "Required options:"

    opts.on("-n", "--name NAME", "Contact name (e.g., \"John Doe\")") do |name|
      options[:name] = name
    end

    opts.separator ""
    opts.separator "Other options:"

    opts.on("-h", "--help", "Show this help message") do
      puts opts
      exit 0
    end

    opts.on("-v", "--version", "Show version") do
      puts "Google Contacts Email Lookup - Version #{VERSION}"
      exit 0
    end
  end

  begin
    parser.parse!

    # Validate required arguments
    if options[:name].nil? || options[:name].strip.empty?
      puts "Error: --name argument is required"
      puts parser
      exit 4  # Invalid arguments
    end

  rescue OptionParser::InvalidOption, OptionParser::MissingArgument => e
    puts "Error: #{e.message}"
    puts parser
    exit 4  # Invalid arguments
  end

  options
end

# Main execution
if __FILE__ == $0
  options = parse_arguments

  # Perform contact lookup
  result = lookup_contact(options[:name])

  # Output JSON result
  puts JSON.generate(result)

  # Exit with appropriate code
  case result[:status]
  when 'success'
    exit 0  # Success
  when 'error'
    case result[:code]
    when 'NO_MATCH_FOUND'
      exit 1  # No match found
    when 'AUTH_ERROR'
      exit 2  # Authentication error (already handled in authorize function)
    when 'API_ERROR'
      exit 3  # API error
    else
      exit 3  # Default to API error for unknown errors
    end
  else
    exit 3  # Unknown status
  end
end
