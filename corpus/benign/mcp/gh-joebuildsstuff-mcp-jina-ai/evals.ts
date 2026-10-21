//evals.ts

import { EvalConfig } from 'mcp-evals';
import { openai } from "@ai-sdk/openai";
import { grade, EvalFunction } from "mcp-evals";

const read_webpageEval: EvalFunction = {
    name: 'read_webpage Tool Evaluation',
    description: 'Evaluates the tool’s ability to extract webpage content optimized for LLMs',
    run: async () => {
        const result = await grade(openai("gpt-4o"), "Extract the main content from https://example.com");
        return JSON.parse(result);
    }
};

const search_web: EvalFunction = {
    name: "search_web Tool Evaluation",
    description: "Evaluates the search_web tool for correctness",
    run: async () => {
        const result = await grade(openai("gpt-4o"), "What are the top search results for 'best pizza in NYC' using Jina AI's search API?");
        return JSON.parse(result);
    }
};

const fact_checkEval: EvalFunction = {
    name: 'fact_check Tool Evaluation',
    description: 'Evaluates the correctness of the fact-checking tool',
    run: async () => {
        const result = await grade(openai("gpt-4o"), "Is it true that the Great Wall of China is visible from space?");
        return JSON.parse(result);
    }
};

const config: EvalConfig = {
    model: openai("gpt-4o"),
    evals: [read_webpageEval, search_web, fact_checkEval]
};
  
export default config;
  
export const evals = [read_webpageEval, search_web, fact_checkEval];
