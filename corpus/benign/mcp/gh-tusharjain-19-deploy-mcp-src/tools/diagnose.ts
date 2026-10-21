export interface DiagnosisResult {
  errorType: string;
  file?: string;
  line?: number;
  issue: string;
  suggestion: string;
  relevantLogs?: string[];
}

export async function diagnoseBuildFailure(
  logs: string[]
): Promise<DiagnosisResult> {
  const logStr = logs.join('\n');

  // Extract the most relevant error lines (lines containing "error", "Error", "ERR", "failed", "not found")
  const relevantLogs = logs.filter(line =>
    /error|ERR|failed|not found|cannot|unexpected|missing|invalid/i.test(line)
  ).slice(0, 20);

  // --- Missing module / import errors ---
  if (logStr.includes("Module not found:") || logStr.includes("Cannot find module")) {
    const match =
      logStr.match(/Module not found: Error: Can't resolve '(.*?)' in '(.*?)'/) ||
      logStr.match(/Cannot find module '(.*?)'/);
    const moduleName = match ? match[1] : "unknown";
    return {
      errorType: "MISSING_MODULE",
      issue: `Missing module: '${moduleName}'`,
      suggestion: `Install the missing dependency by running:\n\nnpm install ${moduleName}\n\nThen retry the deployment.`,
      relevantLogs
    };
  }

  // --- TypeScript type errors ---
  if (logStr.match(/Type error:|TS\d{4}:|error TS/)) {
    const tsMatch = logStr.match(/error TS(\d+): (.+)/);
    const lineMatch = logStr.match(/(.+\.tsx?)\((\d+),\d+\)/);
    return {
      errorType: "TYPESCRIPT_ERROR",
      file: lineMatch ? lineMatch[1] : undefined,
      line: lineMatch ? parseInt(lineMatch[2]) : undefined,
      issue: tsMatch ? `TypeScript error TS${tsMatch[1]}: ${tsMatch[2]}` : "TypeScript compilation failed.",
      suggestion: "Fix the TypeScript error in the file listed above. Run `npx tsc --noEmit` locally to see all type errors before deploying.",
      relevantLogs
    };
  }

  // --- Syntax errors ---
  if (logStr.includes("SyntaxError")) {
    const syntaxMatch = logStr.match(/SyntaxError: (.+)/);
    const fileMatch = logStr.match(/at (.+\.(?:ts|tsx|js|jsx)):(\d+)/);
    return {
      errorType: "SYNTAX_ERROR",
      file: fileMatch ? fileMatch[1] : undefined,
      line: fileMatch ? parseInt(fileMatch[2]) : undefined,
      issue: syntaxMatch ? `Syntax error: ${syntaxMatch[1]}` : "A syntax error was found in your code.",
      suggestion: "Fix the syntax error in the file and line listed. You can run `node --check <file>` locally to validate JavaScript syntax.",
      relevantLogs
    };
  }

  // --- Missing environment variables ---
  if (logStr.match(/environment variable|process\.env\.\w+ is (undefined|not defined)|Missing env/i)) {
    const envMatch = logStr.match(/process\.env\.(\w+)/);
    return {
      errorType: "MISSING_ENV_VAR",
      issue: `A required environment variable is missing${envMatch ? `: ${envMatch[1]}` : ""}.`,
      suggestion: "Use the `compare_env` tool to see which variables are missing from Vercel, then use `sync_env` to upload them securely.",
      relevantLogs
    };
  }

  // --- Out of memory ---
  if (logStr.match(/out of memory|JavaScript heap out of memory|ENOMEM/i)) {
    return {
      errorType: "OUT_OF_MEMORY",
      issue: "The build ran out of memory.",
      suggestion: "Increase the Node.js heap size. Add this to your build script:\n\nNODE_OPTIONS='--max-old-space-size=4096' npm run build\n\nOr check for memory leaks in your build process.",
      relevantLogs
    };
  }

  // --- Package install errors ---
  if (logStr.match(/npm ERR!|yarn error|pnpm ERR!/)) {
    const npmMatch = logStr.match(/npm ERR! (.+)/);
    return {
      errorType: "PACKAGE_INSTALL_FAILED",
      issue: npmMatch ? `Package install failed: ${npmMatch[1]}` : "Dependency installation failed.",
      suggestion: "Delete `node_modules` and `package-lock.json` locally, run `npm install` again, and verify no peer dependency conflicts exist before deploying.",
      relevantLogs
    };
  }

  // --- Port/network binding errors ---
  if (logStr.match(/EADDRINUSE|address already in use/i)) {
    return {
      errorType: "PORT_CONFLICT",
      issue: "A port is already in use.",
      suggestion: "This is unusual for Vercel deployments. Check your server code to ensure you're using `process.env.PORT` instead of a hardcoded port.",
      relevantLogs
    };
  }

  // --- Build command exit code ---
  if (logStr.match(/exited with (code|status) [1-9]|Build failed|build failed/)) {
    return {
      errorType: "BUILD_COMMAND_FAILED",
      issue: "The build command exited with a non-zero exit code.",
      suggestion: "Run `npm run build` locally to reproduce the error and see the full output. Fix the error, then redeploy.",
      relevantLogs
    };
  }

  // --- Default unknown ---
  return {
    errorType: "UNKNOWN_ERROR",
    issue: "An unrecognised error occurred during deployment.",
    suggestion: "Review the full deployment logs to identify the issue. You can also run your build locally with `npm run build` to reproduce it.",
    relevantLogs
  };
}
