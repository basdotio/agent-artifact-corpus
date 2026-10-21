import { publicClient } from "../../../config.js";

export async function getLatestBlock() {
  try {
    const blockNumber = await publicClient.getBlockNumber();
    return {
      content: [
        {
          type: "text",
          text: `Latest block number: ${blockNumber.toString()}`,
        },
      ],
    };
  } catch (error) {
    console.error("Error fetching block number:", error);
    throw new Error(
      `Failed to fetch latest block: ${
        error instanceof Error ? error.message : String(error)
      }`
    );
  }
}
