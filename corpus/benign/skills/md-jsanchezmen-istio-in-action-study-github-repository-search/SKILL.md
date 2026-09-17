---
name: github-repository-search
description: |
  Use this skill to search and fetch information from GitHub repositories when the user:
  - Asks about configuration, documentation, or code from a specific GitHub repository
  - Requests values.yaml, Chart.yaml, README, or other files from GitHub projects
  - Mentions repositories like: kube-prometheus-stack, istio, prometheus-community charts
  - Needs reference documentation from official chart repositories
  - Says phrases like "search github", "look up on github", "check the github repo", "find in the repository"

  This skill maintains a registry of frequently used repositories in GITHUB_LINKS.md. Only use this skill if you expect the repository to be in that registry.

  Do NOT use this skill for:
  - General web searches
  - Local file operations
  - Questions that don't require external GitHub content
---

# github-repository-search

## Instructions

1. **Identify the repository**: Extract the repository name or project name from the user's question
   - Examples: "kube-prometheus-stack", "istio charts", "prometheus-community"

2. **Check the registry**: Read [GITHUB_LINKS.md](./GITHUB_LINKS.md) to see if the repository exists
   - The file contains mappings like: `repository-name: github-url`
   - Look for partial matches (e.g., "kube-prometheus" matches "kube-prometheus-stack")

3. **Select the appropriate link**:
   - If multiple links exist for the repository (e.g., main repo + specific file), choose the most relevant one
   - For specific file requests (values.yaml, README.md), prefer the direct file link
   - For general questions, use the main repository link

4. **Fetch and analyze**: Use the WebFetch tool with the GitHub URL to retrieve the information
   - Provide a clear prompt describing what information to extract
   - Focus on answering the user's specific question

5. **Handle missing repositories**: If the repository is not found in GITHUB_LINKS.md:
   - Inform the user that the repository is not in the registry
   - Suggest adding it to GITHUB_LINKS.md for future use
   - Do NOT attempt to guess or construct GitHub URLs

## Error Handling

- **Ambiguous repository names**: Ask the user for clarification
- **Multiple matching links**: Choose based on context (file-specific vs general)
- **GitHub rate limiting**: Inform the user and suggest trying again later
- **Dead/moved links**: Report the issue and suggest updating GITHUB_LINKS.md

## Examples

**Example 1 - Specific File Request**:
```
User: "What are the default values for prometheus retention in kube-prometheus-stack?"
→ Reads GITHUB_LINKS.md
→ Finds: kube-prometheus-stack values.yaml
→ Fetches: https://github.com/prometheus-community/helm-charts/blob/main/charts/kube-prometheus-stack/values.yaml
→ Returns: retention configuration details
```

**Example 2 - General Repository Question**:
```
User: "How does the kube-prometheus-stack chart work?"
→ Reads GITHUB_LINKS.md
→ Finds: kube-prometheus-stack (main repo link)
→ Fetches: https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack
→ Returns: README content and overview
```

**Example 3 - Repository Not in Registry**:
```
User: "Show me the nginx-ingress values.yaml from GitHub"
→ Reads GITHUB_LINKS.md
→ Not found: nginx-ingress
→ Response: "The nginx-ingress repository is not in the registry. Would you like me to search for it, or would you like to add it to GITHUB_LINKS.md?"
```
