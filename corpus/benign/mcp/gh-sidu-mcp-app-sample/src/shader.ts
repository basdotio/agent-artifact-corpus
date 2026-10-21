/**
 * Shader View. Capabilities exercised:
 *   [CAP-APP-PARTIAL] — ontoolinputpartial streams shader code for preview
 *   fullscreen display-mode request
 *   IntersectionObserver pause on offscreen
 */
import { App } from "@modelcontextprotocol/ext-apps";

const canvas = document.getElementById("c") as HTMLCanvasElement;
const preview = document.getElementById("preview") as HTMLPreElement;
const info = document.getElementById("info")!;
const fsBtn = document.getElementById("fs") as HTMLButtonElement;

const gl = canvas.getContext("webgl");
let program: WebGLProgram | null = null;
let rafId: number | null = null;
let paused = false;
let startTime = performance.now();

const DEFAULT_FRAG = `
precision mediump float;
uniform vec2 u_res;
uniform float u_time;
void main() {
  vec2 uv = gl_FragCoord.xy / u_res;
  vec3 col = 0.5 + 0.5 * cos(u_time + uv.xyx + vec3(0.0, 2.0, 4.0));
  gl_FragColor = vec4(col, 1.0);
}
`;

const VERT = `
attribute vec2 pos;
void main() { gl_Position = vec4(pos, 0.0, 1.0); }
`;

function resize() {
  if (!gl) return;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = canvas.clientWidth * dpr;
  canvas.height = canvas.clientHeight * dpr;
  gl.viewport(0, 0, canvas.width, canvas.height);
}
window.addEventListener("resize", resize);

function compile(source: string, type: number): WebGLShader | null {
  if (!gl) return null;
  const s = gl.createShader(type)!;
  gl.shaderSource(s, source);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
    info.textContent = `Shader compile error: ${gl.getShaderInfoLog(s)}`;
    gl.deleteShader(s);
    return null;
  }
  return s;
}

function loadShader(fragSource: string): boolean {
  if (!gl) return false;
  const v = compile(VERT, gl.VERTEX_SHADER);
  const f = compile(fragSource, gl.FRAGMENT_SHADER);
  if (!v || !f) return false;
  const p = gl.createProgram()!;
  gl.attachShader(p, v);
  gl.attachShader(p, f);
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) {
    info.textContent = `link error: ${gl.getProgramInfoLog(p)}`;
    return false;
  }
  if (program) gl.deleteProgram(program);
  program = p;

  // Fullscreen triangle
  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(
    gl.ARRAY_BUFFER,
    new Float32Array([-1, -1, 3, -1, -1, 3]),
    gl.STATIC_DRAW,
  );
  const posLoc = gl.getAttribLocation(program, "pos");
  gl.enableVertexAttribArray(posLoc);
  gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

  startTime = performance.now();
  info.textContent = "shader compiled";
  return true;
}

function frame() {
  rafId = requestAnimationFrame(frame);
  if (paused || !gl || !program) return;
  gl.useProgram(program);
  const uRes = gl.getUniformLocation(program, "u_res");
  const uTime = gl.getUniformLocation(program, "u_time");
  gl.uniform2f(uRes, canvas.width, canvas.height);
  gl.uniform1f(uTime, (performance.now() - startTime) / 1000);
  gl.drawArrays(gl.TRIANGLES, 0, 3);
}

resize();
loadShader(DEFAULT_FRAG);
frame();

// Pause when scrolled offscreen
const observer = new IntersectionObserver((entries) => {
  for (const entry of entries) {
    paused = !entry.isIntersecting;
    info.textContent = paused ? "paused (offscreen)" : "rendering";
  }
});
observer.observe(canvas);

const app = new App({ name: "Shader View", version: "0.1.0" });

app.ontoolinputpartial = (params) => {
  const code = (params.arguments?.code as string | undefined) ?? "";
  preview.textContent = code;
  preview.style.display = "block";
  info.textContent = `streaming (${code.length} chars)`;
};

app.ontoolinput = (params) => {
  const code = (params.arguments?.code as string | undefined) ?? "";
  preview.style.display = "none";
  loadShader(code);
};

app.ontoolresult = (result) => {
  const sc = result.structuredContent as { code?: string } | undefined;
  if (sc?.code) loadShader(sc.code);
};

app.onteardown = async () => {
  if (rafId !== null) cancelAnimationFrame(rafId);
  observer.disconnect();
  return {};
};

fsBtn.addEventListener("click", async () => {
  const ctx = app.getHostContext();
  const target = ctx?.displayMode === "fullscreen" ? "inline" : "fullscreen";
  if (!ctx?.availableDisplayModes?.includes(target)) {
    info.textContent = `Host does not offer ${target} mode`;
    return;
  }
  await app.requestDisplayMode({ mode: target });
});

app.connect();
