// テスト用の偽 CLI。本物の claude の代わりに STYLE_GUIDE_LLM_CMD で差し込む
import fs from "node:fs";

const argv = process.argv.slice(2);
if (argv.includes("--version")) {
  console.log("mock 1.0");
  process.exit(0);
}

const stdin = fs.readFileSync(0, "utf8");
const mode = process.env.MOCK_LLM_MODE || "brief";

function brief(id) {
  return {
    id,
    name: "テスト",
    tone: "落ち着いた雰囲気。",
    needsJapanese: true,
    state: { product: "Invoicing app", audience: "Small businesses", mood: ["calm", "trustworthy", "clean"], references: "", avoid: "" },
    explicit: { brandColor: null, baseMode: null },
  };
}
const out = (o) => console.log(JSON.stringify(o));

if (mode === "brief") {
  out({ is_error: false, structured_output: brief("calm-blue") });
} else if (mode === "bad-then-good") {
  const f = process.env.MOCK_LLM_COUNTER;
  let n = 0;
  try {
    n = Number(fs.readFileSync(f, "utf8")) || 0;
  } catch {
    n = 0;
  }
  fs.writeFileSync(f, String(n + 1));
  out({ is_error: false, structured_output: brief(n === 0 ? "Bad Id" : "calm-blue") });
} else if (mode === "always-bad") {
  out({ is_error: false, structured_output: brief("Bad Id") });
} else if (mode === "error") {
  out({ is_error: true, result: "boom" });
} else if (mode === "estimate") {
  const schema = JSON.parse(argv[argv.indexOf("--json-schema") + 1]);
  const ans = {};
  for (const [k, p] of Object.entries(schema.properties)) {
    const props = p.properties;
    if (props.choice) {
      const c = props.choice.enum[0];
      ans[k] = { choice: c, confidence: 0.8, probabilities: { [c]: 0.8 } };
    } else if (props.noul) {
      ans[k] = { noul: 0.7 };
    } else {
      ans[k] = { score: 2, confidence: 0.8 };
    }
  }
  out({ is_error: false, structured_output: ans });
} else if (mode === "echo-args") {
  out({ is_error: false, structured_output: { args: argv, stdin } });
} else {
  console.error("unknown mode");
  process.exit(1);
}
