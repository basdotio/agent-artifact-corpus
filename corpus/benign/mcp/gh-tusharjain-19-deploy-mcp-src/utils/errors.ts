export class DeployMcpError extends Error {
  public readonly code: string;
  public readonly suggestion: string;
  public readonly details?: any;

  constructor(
    code: string,
    message: string,
    suggestion: string = "Verify the input arguments and try again.",
    details?: any
  ) {
    super(message);
    this.name = this.constructor.name;
    this.code = code;
    this.suggestion = suggestion;
    this.details = details;

    // Restore prototype chain
    Object.setPrototypeOf(this, new.target.prototype);
  }

  public toStructuredSignal() {
    return {
      errorSignal: true,
      code: this.code,
      name: this.name,
      message: this.message,
      suggestion: this.suggestion,
      details: this.details || null
    };
  }
}

export class RateLimitError extends DeployMcpError {
  constructor(toolName: string, resetInSeconds: number) {
    super(
      "ERR_RATE_LIMIT_EXCEEDED",
      `Rate limit exceeded for tool '${toolName}'.`,
      `Please wait ${resetInSeconds} second(s) before invoking '${toolName}' again.`,
      { toolName, resetInSeconds }
    );
  }
}

export class ValidationError extends DeployMcpError {
  constructor(field: string, reason: string) {
    super(
      "ERR_INVALID_ARGUMENTS",
      `Validation failed for field '${field}': ${reason}`,
      `Provide a valid '${field}' parameter matching required format and type.`,
      { field, reason }
    );
  }
}

export class VercelApiError extends DeployMcpError {
  constructor(status: number, statusText: string, details?: any) {
    super(
      "ERR_VERCEL_API_FAILURE",
      `Vercel API returned status ${status}: ${statusText}`,
      "Ensure your Vercel Personal Access Token is valid and has Full Access scope. Run 'npx deploymcp setup' to re-authenticate.",
      { status, statusText, vercelResponse: details }
    );
  }
}

export class GitSafetyError extends DeployMcpError {
  constructor(message: string, leakedFiles: string[] = []) {
    super(
      "ERR_GIT_SAFETY_VIOLATION",
      message,
      "Remove tracked secrets from git tracking (e.g. add to .gitignore and run 'git rm --cached .env') before deploying.",
      { leakedFiles }
    );
  }
}

export class BuildDiagnosticError extends DeployMcpError {
  constructor(issue: string, suggestion: string, file?: string, line?: number) {
    super(
      "ERR_BUILD_FAILED",
      `Build failed: ${issue}`,
      suggestion,
      { file, line }
    );
  }
}
