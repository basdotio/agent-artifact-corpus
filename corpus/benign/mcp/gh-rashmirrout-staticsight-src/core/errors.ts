// Error types rendered as Markdown cards instead of crashing the server.
export class StaticSightError extends Error {
  title = "StaticSight error";
  hint: string | undefined;
  constructor(message: string, hint?: string) {
    super(message);
    this.hint = hint;
  }
}

export class ToolMissing extends StaticSightError {
  tool: string;
  constructor(tool: string, hint?: string) {
    super(`\`${tool}\` was not found on PATH.`, hint);
    this.title = "Required CLI tool is not installed";
    this.tool = tool;
  }
}

export class ToolFailed extends StaticSightError {
  constructor(message: string, hint?: string) {
    super(message, hint);
    this.title = "CLI tool failed";
  }
}

export class ToolTimeout extends StaticSightError {
  constructor(message: string, hint?: string) {
    super(message, hint);
    this.title = "CLI tool timed out";
  }
}

export class InvalidArgument extends StaticSightError {
  constructor(message: string, hint?: string) {
    super(message, hint);
    this.title = "Invalid argument";
  }
}
