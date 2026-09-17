---
name: kleva-business
description: Specialized knowledge for working with Kleva business operations, including product development, sales sequences, LinkedIn campaigns, financial models, and business documentation. Use when working on any Kleva-related business tasks.
license: Proprietary
metadata:
  author: edescobar
  version: "1.0"
  organization: kleva
---

# Kleva Business Workflow

Specialized skill for working with Kleva business operations, documentation, and development.

## When to use this skill

Use this skill when working on:
- Kleva product development and roadmaps
- Sales sequences and templates
- LinkedIn advertising campaigns
- Financial forecasts and models
- Investor deck materials
- Business documentation and proposals
- AI agent implementations for Kleva
- Debt collections voice agents
- Conversation flow builders

## Project Structure

### Key Directories

**Code/Holding/Kleva**: Main codebase and projects
- `kleva-product/`: Core product development
- `agents/`: AI agent implementations
- `debt-collections-voice-agent/`: Voice AI agent
- `conv-flow-builder/`: Conversation flow tools
- `kleva-internal-docs/`: Internal documentation
- `kleva-dd/`: Due diligence materials
- `finances/`: Financial tracking and models

**Code/Notes/Kleva**: Business documentation
- Product roadmaps and planning
- Sales sequences and templates
- LinkedIn advertising campaigns
- Financial forecasts
- Investor materials
- Subscription offers

## Business Context

### Core Products
1. **AI-powered debt collections**
2. **Voice agent solutions**
3. **Conversation flow automation**
4. **Customer engagement tools**

### Target Customers
- Financial institutions
- Debt collection agencies
- Banks (e.g., Banco de Córdoba)
- Customer service operations

### Technology Stack
- AI/ML agents
- Voice synthesis
- Natural language processing
- Integration APIs

## Common Workflows

### Product Development
When working on product features:
1. Check `holding/kleva/kleva-product/` for current implementation
2. Review `notes/kleva/` for business requirements
3. Consider AI agent optimization opportunities
4. Document decisions in appropriate location

### Sales and Marketing
When creating sales materials:
1. Reference existing sequences in `notes/kleva/`
2. Align with current product positioning
3. Consider customer pain points
4. Include ROI and value propositions

### Financial Planning
When working with finances:
1. Check `holding/kleva/finances/` for current models
2. Maintain consistency with investor materials
3. Update forecasts based on actuals
4. Document assumptions clearly

### AI Agent Development
When building or optimizing agents:
1. Review `holding/kleva/agents/` for existing implementations
2. Check `kleva-ai-agent-optimization/` for optimization patterns
3. Consider voice agent patterns from `debt-collections-voice-agent/`
4. Document agent behaviors and decision trees

## Documentation Standards

### File Naming
- Use lowercase with hyphens
- Include version or date when relevant
- Be descriptive but concise

### Content Organization
- Start with executive summary for business docs
- Include clear next steps or action items
- Link to related documents
- Maintain context.md and WARP.md files

### Version Control
- Commit regularly with clear messages
- Tag major milestones
- Document breaking changes
- Include co-author attribution when AI-assisted

## Key Stakeholders

When creating materials, consider:
- Investors and board members
- Internal team members
- Customer prospects
- Integration partners
- Regulatory requirements

## Best Practices

### Business Documentation
- Be concise and action-oriented
- Use data to support claims
- Include clear timelines
- Define success metrics

### Technical Documentation
- Document architecture decisions
- Include integration points
- Provide examples and use cases
- Keep API documentation current

### Cross-functional Work
- Align technical capabilities with business goals
- Communicate trade-offs clearly
- Include stakeholder feedback
- Maintain transparent progress tracking

## Resources

### Internal References
- See `holding/kleva/context.md` for detailed project context
- Check `notes/kleva/WARP.md` for folder structure
- Review `kleva-internal-docs/` for team documentation

### Related Skills
- Use `ai-engineer` skill for LLM implementations
- Use `context-manager` skill for complex projects
- Use `note-management` skill for organizing documentation
