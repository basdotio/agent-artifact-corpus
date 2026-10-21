import { describe, it, expect } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { server } from "./index.js";
 
describe("synth-execute", () => {
  it("サイン波が出力されるか確認", async () => {

    const client = new Client({
      name: "test client",
      version: "0.1.0",
    });
 
    // インメモリ通信チャネルの作成
    const [clientTransport, serverTransport] =
      InMemoryTransport.createLinkedPair();
      
    // クライアントとサーバーを接続
    await Promise.all([
      client.connect(clientTransport),
      server.connect(serverTransport),
    ]);
 
    const result = await client.callTool({
      name: "synth-execute",
      arguments: {
        synth: {
            name: "test-synth",
            code: `
            {
                arg freq = 440;
                var sig = SinOsc.ar(freq);
                Out.ar(0, sig);
            }
            `,
        },
        duration: 500
      },
    });
 
    expect(result).toEqual({
      content: [
        {
          type: "text",
          text: "シンセ名: test-synth",
        },
        {
          type: "text",
          text: `コード: 
            {
                arg freq = 440;
                var sig = SinOsc.ar(freq);
                Out.ar(0, sig);
            }
            `,
        },
        {
          type: "text",
          text: "再生時間: 0.5秒",
        },
      ],
    });
  });
});


describe("multi-synth-execute", () => {
    it("サイン波とノイズが出力されるか確認", async () => {
    
        const client = new Client({
        name: "test client",
        version: "0.1.0",
        });
     
        // インメモリ通信チャネルの作成
        const [clientTransport, serverTransport] =
        InMemoryTransport.createLinkedPair();
        
        // クライアントとサーバーを接続
        await Promise.all([
        client.connect(clientTransport),
        server.connect(serverTransport),
        ]);
     
        const result = await client.callTool({
        name: "multi-synth-execute",
        arguments: {
            synths: [
            {
                name: "test-synth",
                code: `
                {
                    arg freq = 440;
                    var sig = SinOsc.ar(freq);
                    Out.ar(0, sig);
                }
                `,
            },
            {
                name: "noise-synth",
                code: `
                {
                    var sig = WhiteNoise.ar;
                    Out.ar(0, sig);
                }
                `,
            },
            ],
            duration: 500,
        },
        });
     
        expect(result).toEqual({
        content: [
            {
            type: "text",
            text: "2個のシンセを同時に再生しました。"
            },
            {
            type: "text",
            text: "再生したシンセ: test-synth, noise-synth"
            },
            {
            type: "text",
            text: "合計再生時間: 0.5秒"
            },
        ],
        });
    });
    });