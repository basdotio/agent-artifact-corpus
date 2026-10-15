# Examples

## OAuth Authorization

To use features that require authentication (applying to vacancies, viewing resumes), you need to complete OAuth authorization.

### oauth_flow.py

Interactive script for obtaining OAuth tokens.

**Usage:**

```bash
python examples/oauth_flow.py
```

**Steps:**

1. Script generates authorization URL
2. Open URL in browser and authorize the application
3. Copy the authorization code from redirect URL
4. Paste code into terminal
5. Tokens are automatically saved to `.env`

**What you'll get:**

- `HH_ACCESS_TOKEN` - for making authenticated requests
- `HH_REFRESH_TOKEN` - for refreshing access token when it expires

**Token lifetime:** Access tokens expire after ~14 days. Use refresh token to get new access token.

## Example Queries

Once the MCP server is configured in Claude Code, you can use natural language queries:

### Search Vacancies

```
Find 10 Python developer jobs in Moscow with salary above 200000
```

```
Search for remote Product Manager positions
```

### View Resumes

```
Show my resumes
```

```
Show details of resume with ID abc123
```

### Apply to Jobs

```
Apply to vacancy 126209046 with my Python Developer resume
```

```
Apply to vacancy 123456 with resume xyz789 and cover letter: "Dear Hiring Manager, I am excited to apply..."
```

### Track Applications

```
Show my last 20 job applications
```

```
Show status of my applications from this month
```

## Advanced: Using Vacancy Hunter Agent

The automated agent can search and analyze vacancies across multiple resumes:

```
Run vacancy-hunter agent
```

The agent will:
1. Load your specified resumes
2. Search for relevant vacancies
3. Score each vacancy by match quality (0-30 points)
4. Generate CSV report with recommendations

Results are saved to `/root/vacancy-reports/` (or your configured path).
