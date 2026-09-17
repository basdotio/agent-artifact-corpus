---
name: hackathon-todo-advanced
description: Complete guide for Panaversity Hackathon II (Todo Spec-Driven Development) Phases 2-5. Use when working on Phase 3 (MCP + OpenAI Agents + ChatKit chatbot), Phase 4 (Kubernetes with Minikube, Helm, Docker), Phase 5 (Cloud deployment with Dapr, Kafka, advanced features), or implementing bonus features (Reusable Intelligence, Cloud-Native Blueprints, Urdu support, Voice commands). Includes detailed references, scaffolding scripts, troubleshooting guides, and implementation patterns for AI-powered todo chatbot with event-driven architecture.
---

# Hackathon Todo - Advanced Phases Guide

This skill provides comprehensive guidance for **Panaversity Hackathon II: Phase 3 through Phase 5** plus bonus features.

## When to Use This Skill

Use this skill when:
- **Phase 3**: Implementing MCP server, OpenAI Agents SDK, or ChatKit
- **Phase 4**: Deploying to Kubernetes (Minikube) with Helm and Docker
- **Phase 5**: Cloud deployment with Dapr, Kafka, advanced features
- **Bonus Features**: Implementing +600 bonus points opportunities
- **Troubleshooting**: MCP connectivity, K8s pods, Dapr issues
- **Architecture**: Understanding event-driven patterns, stateless design

## Skill Contents

### 📚 References (Detailed Guides)

#### Phase 2 Completion
- **phase2-completion.md** - Final checklist before moving to Phase 3
  - Backend/Frontend requirements
  - Better Auth JWT verification
  - Deployment verification
  - Common issues & solutions

#### Phase 3: AI Chatbot (Primary Focus)
- **phase3-mcp-complete-guide.md** - Comprehensive MCP server implementation
  - Official MCP SDK setup
  - Tool implementation (add_task, list_tasks, etc.)
  - Database integration
  - Testing procedures
  - Troubleshooting connectivity issues

- **phase3-openai-agents.md** - OpenAI Agents SDK integration
  - Agent configuration
  - Tool calling patterns
  - Stateless conversation management
  - Multi-turn conversations
  - Error handling

- **phase3-chatkit-setup.md** - OpenAI ChatKit frontend
  - Domain allowlist configuration (CRITICAL)
  - ChatKit component setup
  - Authentication integration
  - Custom message rendering
  - Troubleshooting domain errors

#### Phase 4: Kubernetes
- **phase4-kubernetes-local.md** - Local Kubernetes deployment
  - Docker containerization
  - Minikube setup
  - Helm chart creation
  - kubectl-ai and kagent usage
  - Monitoring and debugging

#### Phase 5: Cloud & Advanced
- **phase5-cloud-deployment.md** - Production deployment
  - Cloud provider setup (DigitalOcean/GKE/AKS)
  - Dapr installation and components
  - Kafka integration (Redpanda Cloud or self-hosted)
  - Recurring tasks implementation
  - Due dates & reminders with Dapr Jobs
  - CI/CD with GitHub Actions

#### Bonus Features (+600 Points)
- **bonus-features.md** - Implementation strategies
  - Reusable Intelligence (+200): Agent Skills, Subagents
  - Cloud-Native Blueprints (+200): Spec-driven deployment
  - Multi-language Support (+100): Urdu integration
  - Voice Commands (+200): Web Speech API

### 🔧 Scripts (Ready-to-Use Tools)

- **init_mcp_server.py** - Scaffold complete MCP server with Official SDK
  ```bash
  python scripts/init_mcp_server.py ./backend/mcp_server
  ```

- **test_mcp_connection.py** - Verify MCP server connectivity
  ```bash
  python scripts/test_mcp_connection.py ./backend/mcp_server.py
  ```

- **generate_helm_charts.py** - Generate Kubernetes Helm charts
  ```bash
  python scripts/generate_helm_charts.py ./helm
  ```

- **setup_dapr_components.py** - Create Dapr component configs
  ```bash
  python scripts/setup_dapr_components.py ./dapr-components
  ```

## Quick Start by Phase

### Starting Phase 3?

1. **Verify Phase 2 Complete**:
   ```
   Read references/phase2-completion.md
   ```

2. **Setup MCP Server**:
   ```bash
   python scripts/init_mcp_server.py ./backend/mcp_server
   python scripts/test_mcp_connection.py ./backend/mcp_server/mcp_server.py
   ```

3. **Read Implementation Guides**:
   - Read `references/phase3-mcp-complete-guide.md` for MCP patterns
   - Read `references/phase3-openai-agents.md` for agent integration
   - Read `references/phase3-chatkit-setup.md` for frontend

4. **Key Focus Areas**:
   - MCP server connectivity (most common issue)
   - Stateless chat endpoint design
   - OpenAI domain allowlist setup
   - Conversation state in database

### Starting Phase 4?

1. **Containerize Applications**:
   - Follow Docker sections in `references/phase4-kubernetes-local.md`

2. **Generate Helm Charts**:
   ```bash
   python scripts/generate_helm_charts.py ./helm
   ```

3. **Deploy Locally**:
   - Read full guide in `references/phase4-kubernetes-local.md`
   - Use kubectl-ai for intelligent operations

### Starting Phase 5?

1. **Choose Cloud Provider**:
   - DigitalOcean (recommended), GKE, or AKS
   - Follow setup in `references/phase5-cloud-deployment.md`

2. **Setup Kafka**:
   - Redpanda Cloud (free tier) or self-hosted with Strimzi

3. **Configure Dapr**:
   ```bash
   python scripts/setup_dapr_components.py ./dapr-components
   ```

4. **Implement Advanced Features**:
   - Recurring tasks with event consumers
   - Reminders with Dapr Jobs API
   - Event-driven architecture patterns

### Implementing Bonus Features?

Read `references/bonus-features.md` for:
- **Reusable Intelligence**: Creating Agent Skills and Subagents
- **Cloud-Native Blueprints**: Spec-driven deployment generators
- **Multi-language**: Urdu translation patterns
- **Voice Commands**: Web Speech API integration

## Common Issues & Quick Solutions

### MCP Server Won't Connect
→ Read troubleshooting section in `references/phase3-mcp-complete-guide.md`
→ Run `python scripts/test_mcp_connection.py` to diagnose

### ChatKit Domain Error
→ **MUST** configure domain allowlist first
→ Follow steps in `references/phase3-chatkit-setup.md` section "Domain Allowlist"

### Agent Not Calling Tools
→ Check agent system prompt in `references/phase3-openai-agents.md`
→ Verify MCP tools are being offered to agent

### Kubernetes Pods Failing
→ Check logs: `kubectl logs <pod-name>`
→ Use kubectl-ai: `kubectl ai "why are my pods failing"`

### Dapr Sidecar Not Injecting
→ Verify annotations in deployment YAML
→ Check Dapr installation: `dapr status -k`

## Best Practices

1. **Always test locally first** before deploying to cloud
2. **Use provided scripts** for scaffolding - they follow best practices
3. **Read the full reference** before implementing a phase
4. **Keep conversation state in database** (stateless backend)
5. **Document your process** for submission README
6. **Test end-to-end** before marking phase complete

## Submission Checklist

Before submitting each phase:
- [ ] Feature fully working and tested
- [ ] Code committed to GitHub with clear commit messages
- [ ] README section documenting the phase
- [ ] Demo video showing functionality (< 90 seconds total)
- [ ] All environment variables documented
- [ ] Deployment instructions clear and tested

## Getting Help

If stuck:
1. Check the relevant reference file for your phase
2. Look at "Common Issues" section in that reference
3. Run diagnostic scripts (test_mcp_connection.py, etc.)
4. Review architecture diagrams in reference files
5. Check your Phase 2 is truly complete (common blocker)

## Next Steps After Phase 5

1. Polish your implementation
2. Consider implementing 1-2 bonus features
3. Create comprehensive demo video
4. Document deployment architecture
5. Prepare for live presentation

Good luck! You're building something impressive! 🚀
