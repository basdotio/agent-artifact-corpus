/*
 * three.js (kit): real, rich 3D in a product film, driven by the same clock.
 *
 * Three.js and its add-ons ship as ES modules. They load in one module
 * script (after an import map) and hand themselves to the classic kit:
 *
 *   <script type="importmap">{ "imports": { "three": "./vendor/three/three.module.min.js" } }
 *   (end the import map script here)
 *   <script type="module">
 *     import * as THREE from "three";
 *     import { EffectComposer } from "./vendor/three/addons/postprocessing/EffectComposer.js";
 *     import { RenderPass } from "./vendor/three/addons/postprocessing/RenderPass.js";
 *     import { UnrealBloomPass } from "./vendor/three/addons/postprocessing/UnrealBloomPass.js";
 *     import { OutputPass } from "./vendor/three/addons/postprocessing/OutputPass.js";
 *     import { RoomEnvironment } from "./vendor/three/addons/environments/RoomEnvironment.js";
 *     window.THREE = THREE;
 *     window.THREE_ADDONS = { EffectComposer, RenderPass, UnrealBloomPass, OutputPass, RoomEnvironment };
 *     PF.signal("three").resolve();
 *   (end the module script here)
 *   PF.film({ ..., waitFor: [PF.signal("three")] });
 *
 * `setup.mjs` vendors Three.js and the add-ons (unless --no-three). Render inside draw(t):
 * no requestAnimationFrame, no clock, no Math.random (use PF.random).
 *
 * What makes 3D look expensive (and why a first try looks like CAD blocks):
 *   1. an environment map (PF.three.stage({ env: true })): reflections and soft light on every material
 *   2. bloom on the few brightest things (stage({ bloom })): the highlight glows, nothing else
 *   3. materials with clearcoat, sheen or transmission (PF.three.mat), not flat MeshStandard
 *   4. colour ramps across many instances (PF.three.ramp), inside the brand's palette
 *   5. something moving inside every shot: particles, a camera drift, a wave
 */
(function () {
  const PF = window.PF;
  PF.three = {};
  const T = () => window.THREE;

  /**
   * Renderer, scene, camera, and optionally a studio environment and bloom.
   *   const st = PF.three.stage(canvas, { width: 1080, height: 1920, env: true,
   *     bloom: { strength: 0.9, radius: 0.6, threshold: 1.0 }, fog: { color: 0x101014, near: 8, far: 30 } });
   * st.render() draws the current scene (st.scene; switch scenes with st.use(scene)).
   */
  PF.three.stage = function (canvas, { width, height, fov = 35, background = null, fog = null, exposure = 1, env = false, bloom = null } = {}) {
    const THREE = T();
    const A = window.THREE_ADDONS || {};
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: background === null, preserveDrawingBuffer: true });
    renderer.setPixelRatio(1);
    renderer.setSize(width, height, false);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = exposure;
    const camera = new THREE.PerspectiveCamera(fov, width / height, 0.05, 400);
    let envTex = null;
    if (env && A.RoomEnvironment) {
      const pm = new THREE.PMREMGenerator(renderer);
      envTex = pm.fromScene(new A.RoomEnvironment(), 0.04).texture;
    }
    const make = () => {
      const s = new THREE.Scene();
      if (background !== null) s.background = new THREE.Color(background);
      if (fog) s.fog = new THREE.Fog(fog.color, fog.near, fog.far);
      if (envTex) s.environment = envTex;
      return s;
    };
    const st = { THREE, renderer, camera, scene: make(), newScene: make, width, height };
    let composer = null, renderPass = null;
    if (bloom && A.EffectComposer) {
      composer = new A.EffectComposer(renderer);
      composer.setPixelRatio(1);
      composer.setSize(width, height);
      renderPass = new A.RenderPass(st.scene, camera);
      renderPass.clearAlpha = background === null ? 0 : 1;
      composer.addPass(renderPass);
      st.bloomPass = new A.UnrealBloomPass(new THREE.Vector2(width, height), bloom.strength ?? 0.8, bloom.radius ?? 0.5, bloom.threshold ?? 0.85);
      composer.addPass(st.bloomPass);
      composer.addPass(new A.OutputPass());
    }
    st.use = (scene) => { st.scene = scene; if (renderPass) renderPass.scene = scene; };
    st.render = () => (composer ? composer.render() : renderer.render(st.scene, camera));
    return st;
  };

  /** Point the camera from spherical coordinates around a target (angles in degrees). */
  PF.three.orbit = function (camera, { radius, azimuth, elevation, target = [0, 0, 0], roll = 0 }) {
    const a = (azimuth * Math.PI) / 180, e = (elevation * Math.PI) / 180;
    camera.position.set(target[0] + radius * Math.cos(e) * Math.sin(a), target[1] + radius * Math.sin(e), target[2] + radius * Math.cos(e) * Math.cos(a));
    camera.up.set(Math.sin(roll), Math.cos(roll), 0);
    camera.lookAt(target[0], target[1], target[2]);
  };

  /**
   * Camera shots: an array of { at, azimuth, elevation, radius, target, drift }
   * cut hard at each `at` (a new angle every 2 beats reads as an edit), with a
   * slow drift inside each shot so no frame is still.
   */
  PF.three.shots = function (camera, t, shots) {
    let k = 0;
    for (let i = 0; i < shots.length; i++) if (t >= shots[i].at) k = i;
    const s = shots[k], next = shots[k + 1];
    const len = next ? next.at - s.at : 2;
    const u = PF.clamp01((t - s.at) / len);
    const d = s.drift || {};
    PF.three.orbit(camera, {
      radius: s.radius + (d.radius || 0) * u,
      azimuth: s.azimuth + (d.azimuth || 0) * u,
      elevation: s.elevation + (d.elevation || 0) * u,
      target: s.target || [0, 0, 0],
      roll: s.roll || 0,
    });
    return { index: k, u };
  };

  /** Soft key and fill lights (use with env: true for the rich look). */
  PF.three.lights = function (stage, { sky = 0xffffff, ground = 0x202024, fill = 0.6, key = 2.0, keyPos = [3, 6, 4], scene } = {}) {
    const THREE = stage.THREE, s = scene || stage.scene;
    s.add(new THREE.HemisphereLight(sky, ground, fill));
    const d = new THREE.DirectionalLight(0xffffff, key);
    d.position.set(...keyPos);
    s.add(d);
    return d;
  };

  /**
   * Material presets that read as premium. Colours are hex from the brand.
   *   PF.three.mat("gloss", "#2563EB")   clearcoat plastic (stickers, blocks)
   *   PF.three.mat("glass", "#BFDBFE")   transmission glass
   *   PF.three.mat("satin", "#F5F5F0")   paper, soft sheen
   *   PF.three.mat("glow",  "#FF4500")   emissive: the one highlight that blooms
   *   PF.three.mat("metal", "#FFFFFF")   polished chrome
   */
  PF.three.mat = function (kind, hex, extra) {
    const THREE = T();
    const c = new THREE.Color(hex);
    const o = {
      gloss: { color: c, roughness: 0.28, metalness: 0.05, clearcoat: 1, clearcoatRoughness: 0.12 },
      glass: { color: c, roughness: 0.08, metalness: 0, transmission: 0.92, thickness: 0.8, ior: 1.45, clearcoat: 1 },
      satin: { color: c, roughness: 0.62, metalness: 0, sheen: 0.4, sheenColor: new THREE.Color(0xffffff) },
      glow: { color: c, emissive: c, emissiveIntensity: 2.2, roughness: 0.3, metalness: 0 },
      metal: { color: c, roughness: 0.12, metalness: 1 },
    }[kind];
    return new THREE.MeshPhysicalMaterial(Object.assign(o, extra || {}));
  };

  /** A colour ramp through brand hexes: ramp(["#111827", "#2563EB", "#BFDBFE"])(0..1) -> hex. */
  PF.three.ramp = (stops) => (u) => {
    u = PF.clamp01(u) * (stops.length - 1);
    const i = Math.min(stops.length - 2, Math.floor(u));
    return PF.mix(stops[i], stops[i + 1], u - i);
  };

  /**
   * A field of nx x nz instanced boxes on the x-z plane. Each frame,
   * height(i, j, x, z, t) gives the box's top y and color(i, j, y, t) its hex.
   */
  PF.three.field = function (stage, { nx, nz, xRange = [-1, 1], zRange = [-1, 1], size = 0.08, depth = 1.2, height, color, material, scene, round = 0 } = {}) {
    const THREE = stage.THREE;
    const geo = new THREE.BoxGeometry(size, 1, size);
    geo.translate(0, -0.5, 0);
    const mat = material || PF.three.mat("gloss", "#ffffff");
    const mesh = new THREE.InstancedMesh(geo, mat, nx * nz);
    (scene || stage.scene).add(mesh);
    const m = new THREE.Matrix4(), c = new THREE.Color();
    const xs = (i) => PF.lerp(xRange[0], xRange[1], nx === 1 ? 0.5 : i / (nx - 1));
    const zs = (j) => PF.lerp(zRange[0], zRange[1], nz === 1 ? 0.5 : j / (nz - 1));
    return {
      mesh, x: xs, z: zs,
      update(t) {
        let k = 0;
        for (let i = 0; i < nx; i++) for (let j = 0; j < nz; j++, k++) {
          const x = xs(i), z = zs(j), y = height(i, j, x, z, t);
          m.makeScale(1, depth, 1);
          m.setPosition(x, y, z);
          mesh.setMatrixAt(k, m);
          if (color) mesh.setColorAt(k, c.set(color(i, j, y, t)));
        }
        mesh.instanceMatrix.needsUpdate = true;
        if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
      },
    };
  };

  /**
   * A thick tube along a 3D path (the brand's signature line, a graph, a route).
   * points: array of [x, y, z]. Returns { mesh, draw(p) } where draw reveals the
   * tube from its start (0..1): the line plots itself in 3D.
   */
  PF.three.tube = function (stage, points, { radius = 0.06, radial = 16, segments = 400, material, scene } = {}) {
    const THREE = stage.THREE;
    const curve = new THREE.CatmullRomCurve3(points.map((p) => new THREE.Vector3(...p)));
    const geo = new THREE.TubeGeometry(curve, segments, radius, radial, false);
    const mesh = new THREE.Mesh(geo, material || PF.three.mat("gloss", "#ffffff"));
    (scene || stage.scene).add(mesh);
    const perSeg = radial * 6;
    return {
      mesh, curve,
      draw(p) {
        p = PF.clamp01(p);
        geo.setDrawRange(0, Math.floor(p * segments) * perSeg);
        mesh.visible = p > 0;
      },
      at: (u) => curve.getPointAt(PF.clamp01(u)),
    };
  };

  /** A 2D canvas painted once, as a texture: paint(ctx, w, h). */
  PF.three.canvasTexture = function (stage, w, h, paint) {
    const THREE = stage.THREE;
    const c = document.createElement("canvas");
    c.width = w; c.height = h;
    const ctx = c.getContext("2d");
    paint(ctx, w, h);
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = 8;
    tex.repaint = (fn) => { ctx.clearRect(0, 0, w, h); fn(ctx, w, h); tex.needsUpdate = true; };
    return tex;
  };

  /** A flat card (plane) with a canvas texture; width in world units, height from the aspect. */
  PF.three.card = function (stage, tex, width, { opacity = 1, lit = false, roughness = 0.6 } = {}) {
    const THREE = stage.THREE;
    const img = tex.image;
    const mat = lit
      ? new THREE.MeshPhysicalMaterial({ map: tex, transparent: true, opacity, side: THREE.DoubleSide, roughness, clearcoat: 0.3 })
      : new THREE.MeshBasicMaterial({ map: tex, transparent: true, opacity, side: THREE.DoubleSide, fog: true, toneMapped: false });
    return new THREE.Mesh(new THREE.PlaneGeometry(width, (width * img.height) / img.width), mat);
  };

  /**
   * A die-cut sticker texture: a pill / rounded rect / starburst in `fill`,
   * a white outline, a soft shadow, the text centred. Returns a card mesh.
   *   PF.three.sticker(st, "NEW", { fill: "#FFD60A", ink: "#111111", font: "900 120px sans-serif", shape: "pill" })
   */
  PF.three.sticker = function (stage, text, { fill = "#ffffff", ink = "#111111", font = "900 120px sans-serif", shape = "pill", outline = 18, width = 1.6, dir } = {}) {
    const probe = document.createElement("canvas").getContext("2d");
    probe.font = font;
    const tw = probe.measureText(text).width;
    const size = parseFloat(font.match(/(\d+)px/)[1]);
    const pad = size * 0.55;
    const w = Math.ceil(shape === "burst" ? Math.max(tw, size * 2.2) + pad * 2.6 : tw + pad * 2 + outline * 2 + 40);
    const h = Math.ceil(shape === "burst" ? w : size * 1.5 + outline * 2 + 40);
    const tex = PF.three.canvasTexture(stage, w, h, (c) => {
      const draw = () => {
        c.beginPath();
        if (shape === "burst") {
          const n = 14, R = w / 2 - outline - 12, r = R * 0.8;
          for (let i = 0; i < n * 2; i++) {
            const a = (i * Math.PI) / n, rr = i % 2 ? r : R;
            c.lineTo(w / 2 + Math.cos(a) * rr, h / 2 + Math.sin(a) * rr);
          }
          c.closePath();
        } else {
          const rad = shape === "pill" ? (h - outline * 2 - 40) / 2 : 36;
          c.roundRect(outline + 20, outline + 14, w - outline * 2 - 40, h - outline * 2 - 40, rad);
        }
      };
      c.save(); c.shadowColor = "rgba(0,0,0,.4)"; c.shadowBlur = 24; c.shadowOffsetY = 12;
      draw(); c.lineJoin = "round"; c.lineWidth = outline * 2; c.strokeStyle = "#ffffff"; c.stroke(); c.restore();
      draw(); c.lineWidth = outline * 2; c.strokeStyle = "#ffffff"; c.stroke(); c.fillStyle = fill; c.fill();
      c.fillStyle = ink; c.font = font; c.textAlign = "center"; c.textBaseline = "middle";
      if (dir) c.direction = dir;
      c.fillText(text, w / 2, h / 2 + size * 0.04);
    });
    return PF.three.card(stage, tex, width);
  };

  /**
   * Sample n points from anything you can draw on a 2D canvas (a word, a logo
   * path, a shape): paint(ctx, w, h) in white, points come from lit pixels.
   * Returns [{ x, y }] centred and normalised so the drawing spans x in [-1, 1].
   */
  /**
   * A user's photo or screenshot as a 3D card (from PF.loadImages). Unlit by
   * default so its colours stay true; { lit: true } lets it catch the light.
   * A cut-out PNG keeps its transparency. Add the mesh to a scene yourself.
   */
  PF.three.photo = function (stage, img, width, opts = {}) {
    const w = img.naturalWidth, h = img.naturalHeight;
    const tex = PF.three.canvasTexture(stage, w, h, (c) => c.drawImage(img, 0, 0, w, h));
    return PF.three.card(stage, tex, width, opts);
  };

  PF.three.samplePoints = function (paint, n, { w = 1200, h = 600, seed = 3 } = {}) {
    const c = document.createElement("canvas");
    c.width = w; c.height = h;
    const ctx = c.getContext("2d");
    ctx.fillStyle = ctx.strokeStyle = "#fff";
    paint(ctx, w, h);
    const d = ctx.getImageData(0, 0, w, h).data;
    const lit = [];
    for (let y = 0; y < h; y += 2) for (let x = 0; x < w; x += 2) if (d[(y * w + x) * 4 + 3] > 128) lit.push([x, y]);
    const rand = PF.random(seed), out = [];
    for (let i = 0; i < n && lit.length; i++) {
      const [x, y] = lit[Math.floor(rand() * lit.length)];
      out.push({ x: (x - w / 2) / (w / 2), y: -(y - h / 2) / (w / 2) });
    }
    return out;
  };

  /**
   * Particles: n points whose position you set from t. pos(i, t, out) writes
   * out.x, out.y, out.z; color(i) gives a hex once. Soft round sprites.
   * Returns update(t).
   */
  PF.three.particles = function (stage, n, { pos, color, size = 0.05, scene, opacity = 1, additive = false } = {}) {
    const THREE = stage.THREE;
    const g = new THREE.BufferGeometry();
    const p = new Float32Array(n * 3), col = new Float32Array(n * 3);
    const c = new THREE.Color();
    for (let i = 0; i < n; i++) { c.set(color ? color(i) : "#ffffff"); col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b; }
    g.setAttribute("position", new THREE.BufferAttribute(p, 3));
    g.setAttribute("color", new THREE.BufferAttribute(col, 3));
    const sprite = document.createElement("canvas");
    sprite.width = sprite.height = 64;
    const sc = sprite.getContext("2d"), gr = sc.createRadialGradient(32, 32, 0, 32, 32, 32);
    gr.addColorStop(0, "rgba(255,255,255,1)"); gr.addColorStop(0.45, "rgba(255,255,255,.9)"); gr.addColorStop(1, "rgba(255,255,255,0)");
    sc.fillStyle = gr; sc.fillRect(0, 0, 64, 64);
    const mat = new THREE.PointsMaterial({ size, map: new THREE.CanvasTexture(sprite), vertexColors: true, transparent: true, opacity, depthWrite: false, blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending, sizeAttenuation: true });
    const pts = new THREE.Points(g, mat);
    (scene || stage.scene).add(pts);
    const o = { x: 0, y: 0, z: 0 };
    return {
      points: pts,
      update(t) {
        for (let i = 0; i < n; i++) { pos(i, t, o); p[i * 3] = o.x; p[i * 3 + 1] = o.y; p[i * 3 + 2] = o.z; }
        g.attributes.position.needsUpdate = true;
      },
    };
  };
})();
