# Sober Up Feature Implementation Plan

## Overview
Replace the current `fact_checked_answer` prompt with a more robust `sober_up` feature that helps ground the LLM agent in the project's reality by checking and validating key aspects of the environment and project configuration.

## Goals
1. Prevent incorrect assumptions about the development environment
2. Ensure consistent behavior across different contexts
3. Provide clear feedback when the agent makes incorrect assumptions
4. Maintain awareness of project-specific configurations

## Implementation Checklist

### 1. Environment Validation
- [ ] Detect and validate operating system (Windows-specific checks)
- [ ] Verify development tools and versions (Node.js, npm, etc.)
- [ ] Check for required environment variables
- [ ] Validate network/proxy settings if applicable

### 2. Project Configuration
- [ ] Verify deployment target (Railway, Cloudflare or Vercel, NEVER Netlify)
- [ ] Check project dependencies and versions
- [ ] Validate project structure
- [ ] Verify configuration files (.env, etc.)

### 3. System Prompt Enhancement
- [ ] Create a comprehensive system prompt that includes:
  - [ ] Current environment details
  - [ ] Project-specific constraints
  - [ ] Common pitfalls to avoid
  - [ ] Correct command syntax for Windows

### 4. Command Validation
- [ ] Implement command validation to catch Windows-incompatible commands
- [ ] Add suggestions for Windows alternatives to common Linux commands
- [ ] Validate file paths for Windows compatibility

### 5. Feedback Mechanism
- [ ] Provide clear error messages when incorrect assumptions are made
- [ ] Include correction suggestions in error messages
- [ ] Log common mistakes for future reference

### 6. Testing
- [ ] Test with various incorrect assumptions
- [ ] Verify Windows command handling
- [ ] Test deployment-related commands
- [ ] Validate environment-specific behaviors

## Implementation Steps

1. **Create New Prompt Handler**
   - Replace `fact_checked_answer` with `sober_up`
   - Implement environment detection
   - Add validation logic

2. **Update Server Configuration**
   - Modify server.ts to include the new prompt
   - Update any related type definitions

3. **Documentation**
   - Update README.md with new feature details
   - Add examples of common scenarios
   - Document any new environment variables

4. **Testing**
   - Create test cases for different scenarios
   - Verify error handling
   - Test edge cases

## Example Implementation (server.ts)

```typescript
case 'sober_up':
  return {
    description: 'Ground the LLM in project reality',
    messages: [
      { 
        role: 'system', 
        content: { 
          type: 'text', 
          text: `You are running in a Windows environment. 
                 This project uses Railway for deployment.
                 Always use Windows-style paths (backslashes) and commands, never && or ||.
                 Current project structure: ${JSON.stringify(getProjectStructure(), null, 2)}`
        } 
      },
      { 
        role: 'user', 
        content: { 
          type: 'text', 
          text: `Context: ${args['CONTEXT'] || 'No additional context provided'}` 
        } 
      }
    ]
  };
```

## Future Enhancements
- Add more granular environment checks
- Implement automatic correction of common mistakes
- Create a learning system to remember user preferences
- Add support for additional development environments

## Changelog
- 2025-05-18: Initial plan created (Claude 3.5 Sonnet)
