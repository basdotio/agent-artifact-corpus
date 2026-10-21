import test from "node:test";
import assert from "node:assert/strict";
import { evaluateJev, jevConfig } from "../jev.js";

const input = { state: { user_request: "Read README.md", actions_taken: [] },
  instructions: "Choose the next tool", doneInstructions: "Is the work done?",
  criteria: { Read: "Read a file", respond_to_user: "Answer when done" } };
function result(provider: string) {
  return { answers: { next_tool: { type: "choice", choice: "Read", probabilities: { Read: 0.9, respond_to_user: 0.1 } },
    done: provider === "vercel" ? { type: "boolean", probability: 0.02 } : { type: "noul", noul: 0.02 } } };
}

test("classifier credentials are independent from model upstream and session credentials", () => {
  for (const [provider, key] of [["typesafe", "TYPESAFE_API_KEY"], ["openrouter", "OPENROUTER_API_KEY"], ["vercel", "AI_GATEWAY_API_KEY"]]) {
    const env = { JEV_PROVIDER: provider, [key!]: "classifier-key", UPSTREAM_API_KEY: "wrong-key", OPENAI_API_KEY: "agent-key" };
    assert.equal(jevConfig(env).apiKey, "classifier-key");
    assert.equal(jevConfig({ ...env, JEV_API_KEY: "override" }).apiKey, "override");
    assert.equal(jevConfig({ JEV_PROVIDER: provider, UPSTREAM_API_KEY: "wrong-key" }).apiKey, undefined);
  }
  assert.throws(() => jevConfig({ JEV_PROVIDER: "typo" }));
});

for (const provider of ["openrouter", "vercel"]) {
  test(`${provider} uses its evaluation API, not chat completion`, async () => {
    const config = jevConfig({ JEV_PROVIDER: provider, JEV_API_KEY: "classifier-only" });
    let calls = 0;
    const request: typeof fetch = async (url, init) => {
      calls++;
      assert.equal(String(url), provider === "openrouter" ? "https://openrouter.ai/api/alpha/decisions" : "https://ai-gateway.vercel.sh/v4/ai/evaluation-model");
      assert.equal(init?.method, "POST");
      assert.equal(init?.redirect, "error");
      const headers = new Headers(init?.headers);
      assert.equal(headers.get("authorization"), "Bearer classifier-only");
      assert.equal(headers.get("chatgpt-account-id"), null);
      const body = JSON.parse(String(init?.body));
      assert.deepEqual(body.state, input.state);
      assert.deepEqual(body.questions.next_tool.criteria, input.criteria);
      assert.equal(body.questions.done.type, provider === "vercel" ? "boolean" : "noul");
      assert.equal(body.messages, undefined);
      if (provider === "vercel") {
        assert.equal(body.model, undefined);
        assert.equal(headers.get("ai-model-id"), "typesafe-ai/jev");
        assert.equal(headers.get("ai-evaluation-model-specification-version"), "4");
        assert.equal(headers.get("ai-gateway-protocol-version"), "0.0.1");
      } else assert.equal(body.model, "~typesafe/jev-latest");
      return Response.json(result(provider));
    };
    assert.deepEqual(await evaluateJev(input, config, request), {
      choice: "Read", probabilities: { Read: 0.9, respond_to_user: 0.1 }, confidence: 0.9, done: 0.02,
    });
    assert.equal(calls, 1);
  });

  test(`${provider} rejects incomplete, unknown, and invalid decisions`, async () => {
    const config = jevConfig({ JEV_PROVIDER: provider, JEV_API_KEY: "secret" });
    for (const next_tool of [
      { type: "choice", choice: "Delete", probabilities: { Read: 0.9, respond_to_user: 0.1 } },
      { type: "choice", choice: "Read" },
      { type: "choice", choice: "Read", probabilities: { Read: -0.1, respond_to_user: 1.1 } },
      { type: "choice", choice: "Read", probabilities: { Read: 1 } },
    ]) {
      const body = result(provider);
      await assert.rejects(evaluateJev(input, config, async () => Response.json({ answers: { ...body.answers, next_tool } })));
    }
    await assert.rejects(evaluateJev(input, config, async () => new Response("secret and prompt", { status: 401 })),
      { message: `Jev ${provider} returned HTTP 401. Check the selected provider's key in setup.` });
    await assert.rejects(evaluateJev(input, { ...config, apiKey: undefined }, async () => { throw Error("Must not call"); }), /Set /);
  });
}

test("native confidence is preserved when a gateway supplies it", async () => {
  const body = result("openrouter");
  const value = await evaluateJev(input, jevConfig({ JEV_PROVIDER: "openrouter", JEV_API_KEY: "test" }),
    async () => Response.json({ answers: { ...body.answers, next_tool: { ...body.answers.next_tool, confidence: 0.8 } } }));
  assert.equal(value.confidence, 0.8);
});
