import { dbAll, dbExec, dbRun } from '../db/index.js';
import { formatSuccessResponse } from '../utils/formatUtils.js';

/**
 * Add a business insight to the memo
 * @param insight Business insight text
 * @returns Result of the operation
 */
export async function appendInsight(insight: string) {
  try {
    if (!insight) {
      throw new Error("Insight text is required");
    }

    // Create insights table if it doesn't exist
    await dbExec(`
      CREATE TABLE IF NOT EXISTS mcp_insights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        insight TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
    
    // Insert the insight
    await dbRun(
      "INSERT INTO mcp_insights (insight) VALUES (?)",
      [insight]
    );
    
    return formatSuccessResponse({ success: true, message: "Insight added" });
  } catch (error: any) {
    throw new Error(`Error adding insight: ${error.message}`);
  }
}

/**
 * List all insights in the memo
 * @returns Array of insights
 */
export async function listInsights() {
  try {
    // Check if insights table exists
    const tableExists = await dbAll(
      "SELECT name FROM sqlite_master WHERE type='table' AND name = 'mcp_insights'"
    );
    
    if (tableExists.length === 0) {
      // Create table if it doesn't exist
      await dbExec(`
        CREATE TABLE IF NOT EXISTS mcp_insights (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          insight TEXT NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      `);
      return formatSuccessResponse([]);
    }
    
    const insights = await dbAll("SELECT * FROM mcp_insights ORDER BY created_at DESC");
    return formatSuccessResponse(insights);
  } catch (error: any) {
    throw new Error(`Error listing insights: ${error.message}`);
  }
} 