# Context-Sensitive Email Routing

## Overview

Some recipients require context-sensitive email address selection based on the topic and nature of the communication. This document provides guidelines for determining the appropriate email address based on context.

## Ed Korkuch - Dual Email Routing

Ed Korkuch has two email addresses that should be used based on the communication context:

### Email Addresses

1. **ed@dreamanager.com** - Dreamanager project communications
2. **ekorkuch@versacomputing.com** - All other communications

### Dreamanager Context Indicators

Use `ed@dreamanager.com` when the email relates to:

**Project Work**:
- Feature development and implementation
- Bug reports and fixes
- Code reviews and pull requests
- Database operations and migrations
- Rails application work
- Deployment and production issues

**Business Operations**:
- Investor and resident functionality
- Property management features
- Transaction processing
- Document compliance system
- User interface improvements

**Technical Topics**:
- Application architecture
- Performance optimization
- Security concerns related to the application
- Infrastructure and hosting
- Testing and quality assurance

**Examples**:
- "Summary of new document types feature deployment"
- "Bug in investor statement generation"
- "Need to discuss database upgrade timeline"
- "Code review for authentication changes"

### Non-Dreamanager Context Indicators

Use `ekorkuch@versacomputing.com` when the email relates to:

**General Consulting**:
- Non-Dreamanager projects
- General technical consulting
- Professional advice not specific to Dreamanager
- Business discussions unrelated to the application

**Administrative**:
- Invoicing and billing
- Contract and agreement discussions
- General business correspondence
- Scheduling and availability

**Personal**:
- Personal communications
- Social invitations
- Non-work related topics

**Examples**:
- "Invoice for October consulting hours"
- "Would you be available for a new project?"
- "General question about Ruby best practices"
- "Contract renewal discussion"

### Decision Guidelines

**When in doubt**: Default to `ekorkuch@versacomputing.com` for professional safety

**High confidence Dreamanager context**:
- Email mentions "Dreamanager" explicitly
- References specific application features or code
- Discusses investors, residents, or properties
- Relates to production deployment or database

**Uncertain context**:
- General technical questions
- Mixed topics (both Dreamanager and other)
- New requests without clear project context
- Follow-up to previous conversations (check context of original)

## Implementation Notes

### In Email Skill

The email skill should analyze the email subject and content to determine context before selecting Ed Korkuch's email address.

**Analysis Process**:
1. Scan email subject and body for Dreamanager-related keywords
2. Check for references to specific application features or components
3. Look for mentions of investors, residents, properties, transactions
4. Consider deployment, database, or Rails-specific topics
5. Default to `ekorkuch@versacomputing.com` if context unclear

**Keywords for Dreamanager Context**:
- dreamanager, investor, resident, property, transaction
- database, migration, rails, deployment, production
- statement, document, compliance, tenant, landlord
- authentication, api, controller, model
- feature, bug, issue, pull request, PR

### In Contact Lookup Script

The `lookup_contact_email.rb` script does NOT handle context-sensitive routing. It always returns the contact's primary email from Google Contacts.

Context-sensitive routing for Ed Korkuch should be implemented in the email skill itself, which has access to the full email context (subject, body, conversation history).

## Version History

- **1.0.0** (2025-10-29) - Initial documentation for Ed Korkuch context-sensitive routing
