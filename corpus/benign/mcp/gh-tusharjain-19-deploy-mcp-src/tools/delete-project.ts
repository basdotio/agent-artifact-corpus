import { getVercelClient } from "../vercel/client.js";
import { getVercelToken } from "../utils/config.js";
import { execSync } from "child_process";
import os from "os";

export interface DeleteProjectResult {
  success: boolean;
  message: string;
}

/**
 * Prompts the user with a native OS-level dialog to confirm deletion.
 * This physically blocks execution until the user clicks Yes or No.
 * The AI cannot bypass this dialog.
 */
function confirmNativePrompt(projectName: string): boolean {
  const platform = os.platform();
  const promptMessage = `Are you absolutely sure you want to PERMANENTLY delete the Vercel project '${projectName}'? This action cannot be undone.`;
  const promptTitle = "Confirm Vercel Project Deletion";

  try {
    if (platform === "win32") {
      // Windows PowerShell MessageBox
      const psCommand = `
        Add-Type -AssemblyName PresentationFramework;
        $result = [System.Windows.MessageBox]::Show('${promptMessage}', '${promptTitle}', 'YesNo', 'Warning');
        Write-Output $result;
      `;
      const output = execSync(`powershell -Command "${psCommand.replace(/\n/g, '')}"`, { encoding: "utf8" }).trim();
      return output === "Yes";
    } else if (platform === "darwin") {
      // macOS AppleScript dialog
      const asCommand = `
        display dialog "${promptMessage}" with title "${promptTitle}" buttons {"No", "Yes"} default button "No" with icon caution
      `;
      const output = execSync(`osascript -e '${asCommand}'`, { encoding: "utf8" }).trim();
      return output.includes("button returned:Yes");
    } else {
      // Linux zenity (if installed) or throw error requiring manual user confirmation
      try {
        execSync(`zenity --question --text="${promptMessage}" --title="${promptTitle}"`);
        return true;
      } catch {
        throw new Error("Could not spawn a native UI prompt on this Linux system. Please confirm manually.");
      }
    }
  } catch (error) {
    if (error instanceof Error && error.message.includes("manual")) {
      throw error;
    }
    console.error("Native prompt failed:", error);
    throw new Error("Failed to show native confirmation dialog. Deletion aborted for safety.");
  }
}

export async function deleteProject(
  projectName: string
): Promise<DeleteProjectResult> {
  try {
    const token = await getVercelToken();
    if (!token) {
      return {
        success: false,
        message: "Vercel not authenticated. Run 'npx deploy-mcp setup' first."
      };
    }

    const client = await getVercelClient();
    if (!client) {
      return { success: false, message: "Failed to initialize Vercel client." };
    }

    // 1. Verify project exists and get its ID
    // We use the internal request method or we can extract logic from ensureProject.
    // For now, we fetch the project directly.
    let project;
    try {
      project = await client["request"]("GET", `/v9/projects/${projectName}`);
    } catch {
      return { success: false, message: `Project '${projectName}' not found on Vercel.` };
    }

    if (!project || !project.id) {
      return { success: false, message: `Could not retrieve ID for project '${projectName}'.` };
    }

    // 2. SHOW NATIVE OS CONFIRMATION PROMPT
    // This will block the thread and wait for user physical interaction.
    const confirmed = confirmNativePrompt(projectName);

    if (!confirmed) {
      return {
        success: false,
        message: "User declined the deletion request in the native OS prompt."
      };
    }

    // 3. Perform deletion
    await client.deleteProject(project.id);

    return {
      success: true,
      message: `Successfully deleted project '${projectName}' from Vercel.`
    };
  } catch (error) {
    return {
      success: false,
      message: error instanceof Error ? error.message : "Deletion failed unexpectedly."
    };
  }
}
