import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

export async function executeOSAScript(script: string): Promise<string> {
    try {
        const { stdout, stderr } = await execAsync(
            `osascript -l JavaScript -e "${script
                .replace(/"/g, '\\"')
                .replace(/\n/g, " ")}"`
        );

        if (stderr) {
            throw new Error(`osascript error: ${stderr}`);
        }

        return stdout;
    } catch (error) {
        if (error instanceof Error) {
            throw new Error(`Failed to execute osascript: ${error.message}`);
        } else {
            throw new Error(`Failed to execute osascript: ${error}`);
        }
    }
}
