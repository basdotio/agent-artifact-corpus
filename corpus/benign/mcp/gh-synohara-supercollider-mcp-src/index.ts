#! /usr/bin/env node

import supercolliderjs from "supercolliderjs";
const sc = supercolliderjs;

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

interface SCServer {
  synthDef: (name: string, code: string) => Promise<any>;
  synth: (def: any, options?: any) => Promise<any>;
  quit: () => void;
}

let scServerInstance: SCServer | null = null;
let serverInitPromise: Promise<SCServer> | null = null;

let activeSynths: any[] = [];

async function initServer(): Promise<SCServer> {
  if (serverInitPromise) {
    return serverInitPromise;
  }

  serverInitPromise = (async () => {
    try {
      console.error("SuperColliderサーバーを起動中...");
      const server = await (sc as any).server.boot({
        debug: false,
        echo: false,
        stderr: './supercollider-error.log'
      }) as SCServer;

      console.error("SuperColliderサーバー起動完了");
      scServerInstance = server;
      return server;
    } catch (err) {
      console.error("SuperColliderサーバー起動エラー:", err);
      serverInitPromise = null;
      throw err;
    }
  })();

  return serverInitPromise!;
}

async function loadAndPlaySynth(scServer: SCServer, synthName: string, synthCode: string): Promise<any> {
  const def = await scServer.synthDef(synthName, synthCode);
  const synth = await scServer.synth(def);
  activeSynths.push(synth);
  return synth;
}

async function cleanupServer() {
  if (scServerInstance) {
    try {
      await scServerInstance.quit();

      scServerInstance = null;
      serverInitPromise = null;
      activeSynths = [];

      try {
        if (process.platform === 'win32') {
          require('child_process').execSync('taskkill /F /IM sclang.exe', { stdio: 'ignore' });
        } else {
          require('child_process').execSync('pkill -f sclang', { stdio: 'ignore' });
        }
      } catch (killErr) {
        console.error('sclangプロセス終了試行:', killErr);
      }

      console.error('SuperColliderサーバーを終了しました');
    } catch (error) {
      console.error("サーバー終了エラー:", error);
    }
  }
}

// サーバーインスタンスの作成
export const server = new McpServer({
  name: "SuperColliderMcpServer",
  version: "0.1.0",
});


server.tool(
  "synth-execute",
  `SynthDefのコードを生成し、そのコードを実行して音を出します。
  コードは{}でくくるようにしてください。`,
  {
    synth: z.object({
      name: z.string().describe("シンセの名前"),
      code: z.string().describe("シンセのコード")
    }).describe("再生するシンセの情報"),
    duration: z.number().optional().describe("再生時間（ミリ秒）。デフォルトは5000（5秒）")
  },
  async ({ synth, duration = 5000 }) => {
    try {
      const scServer = await initServer();

      const def = await scServer.synthDef(synth.name, synth.code);
      await scServer.synth(def);

      console.error(`シンセを${duration / 1000}秒間演奏中...`);
      await new Promise(resolve => setTimeout(resolve, duration));

      await cleanupServer();

      console.error('シンセの演奏完了');

      return {
        content: [
          {
            type: "text",
            text: `シンセ名: ${synth.name}`,
          },
          {
            type: "text",
            text: `コード: ${synth.code}`,
          },
          {
            type: "text",
            text: `再生時間: ${duration / 1000}秒`,
          }
        ],
      };
    } catch (error) {
      console.error("SuperCollider実行エラー:", error);
      return {
        content: [
          {
            type: "text",
            text: `エラーが発生しました: ${error instanceof Error ? error.message : JSON.stringify(error, Object.getOwnPropertyNames(error), 2)}`,
          }
        ],
      };
    }
  }
);

server.tool(
  "multi-synth-execute",
  "複数のSynthDefを同時に実行します。",
  {
    synths: z.array(
      z.object({
        name: z.string().describe("シンセの名前"),
        code: z.string().describe("シンセのコード")
      })
    ).describe("再生するシンセのリスト"),
    duration: z.number().optional().describe("再生時間（ミリ秒）。デフォルトは10000（10秒）")
  },
  async (
    { synths, duration = 10000 }:
      {
        synths: { name: string, code: string }[],
        duration?: number
      }
  ) => {
    try {
      const scServer = await initServer();
      const synthPromises = [];

      for (const synth of synths) {
        synthPromises.push(loadAndPlaySynth(scServer, synth.name, synth.code));
      }

      const loadedSynths = await Promise.all(synthPromises);

      console.error(`${synths.length}個のシンセを${duration / 1000}秒間演奏中...`);
      await new Promise(resolve => setTimeout(resolve, duration));

      await cleanupServer();

      console.error('複数シンセの演奏完了');

      return {
        content: [
          {
            type: "text",
            text: `${synths.length}個のシンセを同時に再生しました。`,
          },
          {
            type: "text",
            text: `再生したシンセ: ${synths.map(s => s.name).join(', ')}`,
          },
          {
            type: "text",
            text: `合計再生時間: ${duration / 1000}秒`,
          }
        ],
      };
    } catch (error) {
      console.error("複数シンセ実行エラー:", error);
      return {
        content: [
          {
            type: "text",
            text: `エラーが発生しました: ${error instanceof Error ? error.message : JSON.stringify(error, Object.getOwnPropertyNames(error), 2)}`,
          }
        ],
      };
    }
  }
);

const transport = new StdioServerTransport();
await server.connect(transport);
console.error("supercollider MCP Server running on stdio");

