# WebGL: shader backgrounds, particles, bloom (Three.js)

Use WebGL only when the direction asks for it (Noir Spotlight's shader bg, a hero "light field" for Ember Dark). It is the most expensive thing on the page, so it must degrade: **the CSS glow from `shared/light.md` is always underneath, the canvas fades in over it**, and the page looks finished if the canvas never appears.

## Setup (single-file, no build)

```html
<script type="importmap">{"imports":{
  "three":"https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js",
  "three/addons/":"https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/"}}</script>
<canvas id="gl" aria-hidden="true"></canvas>
<style>#gl{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;opacity:0;transition:opacity 1.2s ease-out}#gl.on{opacity:1}</style>
```

Gate: skip WebGL entirely (keep the CSS glow) when `matchMedia('(max-width:768px)').matches || navigator.hardwareConcurrency <= 4`, and wrap setup in `try/catch` so a missing WebGL context cannot break the page. Reduced motion: render one static frame, no loop.

## Recipe A: flowing accent light (fragment-only background)

```html
<script type="module">
import * as THREE from 'three';
const el = document.getElementById('gl');
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const lite = matchMedia('(max-width:768px)').matches || navigator.hardwareConcurrency <= 4;
if (!lite) try {
  const renderer = new THREE.WebGLRenderer({ canvas: el, antialias: false, alpha: false });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));          // DPR cap: 4x pixels is the #1 cost
  const scene = new THREE.Scene(), cam = new THREE.Camera();
  const u = { uTime:{value:0}, uRes:{value:new THREE.Vector2()}, uMouse:{value:new THREE.Vector2(.5,.5)},
              uBg:{value:new THREE.Color('#05060a')}, uAccent:{value:new THREE.Color('#ff5a1f')} }; // = your --bg / --accent
  scene.add(new THREE.Mesh(new THREE.PlaneGeometry(2,2), new THREE.ShaderMaterial({ uniforms:u,
    vertexShader:`varying vec2 vUv; void main(){ vUv=uv; gl_Position=vec4(position.xy,0.,1.); }`,
    fragmentShader:`
      uniform float uTime; uniform vec2 uRes, uMouse; uniform vec3 uBg, uAccent; varying vec2 vUv;
      float hash(vec2 p){ return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453); }
      float noise(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.-2.*f);
        return mix(mix(hash(i),hash(i+vec2(1,0)),f.x), mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x), f.y); }
      float fbm(vec2 p){ float v=0., a=.5; for(int i=0;i<4;i++){ v+=a*noise(p); p*=2.; a*=.5; } return v; } // 4 octaves max
      void main(){
        vec2 asp=vec2(uRes.x/uRes.y,1.), p=(vUv-.5)*asp, t=vec2(uTime*.05,-uTime*.05);
        float n=fbm(p*2.+t+fbm(p*3.-t));
        float d=length(p-(uMouse-.5)*asp*.4-vec2(0.,-.25));      // light source sits low, drifts toward the cursor
        vec3 c=mix(uBg,uAccent,clamp(smoothstep(.9,0.,d)*n*1.6,0.,1.));
        c+=(hash(vUv*uRes+uTime)-.5)*.014;                        // grain kills banding; above ~.02 it reads as noise
        gl_FragColor=vec4(c,1.);
        #include <colorspace_fragment>                            // uniforms are linear; convert to sRGB on output
      }` })));
  const size = () => { const r = el.getBoundingClientRect(); renderer.setSize(r.width, r.height, false);
    u.uRes.value.set(r.width*renderer.getPixelRatio(), r.height*renderer.getPixelRatio()); };
  size(); addEventListener('resize', size);
  let visible = true, raf = 0;
  const frame = t => { u.uTime.value = t/1000; renderer.render(scene, cam);
    raf = visible && !reduce ? requestAnimationFrame(frame) : 0; };
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; if (visible && !raf) raf = requestAnimationFrame(frame); })
    .observe(el);                                                  // never render offscreen
  if (!reduce) addEventListener('pointermove', e => u.uMouse.value.set(e.clientX/innerWidth, 1-e.clientY/innerHeight), { passive:true });
  requestAnimationFrame(t => { frame(t); el.classList.add('on'); });
} catch (e) { /* the CSS glow underneath stays */ }
</script>
```

Tie it to scroll by writing a uniform from GSAP (`ScrollTrigger.create({ trigger:'.hero', start:'top top', end:'bottom top', scrub:true, onUpdate:s => u.uScroll.value = s.progress })`) and dimming the light in the shader. Never read layout or allocate objects inside `onUpdate`.

Keep the lit area to roughly half of the hero (raise the `smoothstep` start, e.g. `.9` to `.7`) so headline and body text keep their contrast against it; a light that floods the whole screen turns the accent into a flat green/orange wash.

## Recipe B: particle field (accent specks drifting in depth)

```js
const N = 2500, pos = new Float32Array(N*3);
for (let i=0;i<N*3;i++) pos[i] = (Math.random()-.5) * (i%3===2 ? 6 : 12);
const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos,3));
const m = new THREE.ShaderMaterial({ transparent:true, depthWrite:false, blending:THREE.AdditiveBlending,
  uniforms:{ uTime:u.uTime, uAccent:u.uAccent, uPx:{value:renderer.getPixelRatio()} },
  vertexShader:`uniform float uTime,uPx; void main(){ vec3 p=position; p.y+=sin(uTime*.3+p.x)*.15; p.x+=uTime*.02; p.x=mod(p.x+6.,12.)-6.;
    vec4 mv=modelViewMatrix*vec4(p,1.); gl_PointSize=(2.5+1.5*fract(p.x*7.))*uPx*(4./-mv.z); gl_Position=projectionMatrix*mv; }`,
  fragmentShader:`uniform vec3 uAccent; void main(){ float d=length(gl_PointCoord-.5); if(d>.5) discard; gl_FragColor=vec4(uAccent,smoothstep(.5,0.,d)*.8); }` });
scene.add(new THREE.Points(g, m));   // use a PerspectiveCamera at z=5 instead of THREE.Camera from Recipe A
```
Keep N under ~3000. One `Points` object, never one mesh per particle.

## Recipe C: bloom (only for a lit object, never for the whole page)

```js
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
composer.addPass(new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.6, 0.5, 1.0)); // strength, radius, threshold
composer.addPass(new OutputPass());
// loop: composer.render() instead of renderer.render(); on resize: composer.setSize(w, h)
```
Threshold ≈ 1 means only emissive/over-bright materials glow (set `emissiveIntensity > 1`), so text and UI stay crisp. Strength above ~0.8 looks like a 2010 lens flare. A background that is already a glow (Recipe A) needs no bloom, and the CSS recipe in `light.md` is cheaper for that look.

## Rules that keep it fast and leak-free
- One canvas per page; one renderer; never re-create it on scroll or resize (call `setSize`).
- DPR capped at 1.5; `antialias:false` for full-screen shader planes.
- Render only while visible (IntersectionObserver) and stop the loop under reduced motion.
- No `new Vector3()/Color()` inside the frame loop; update `.value`/`.set()` on objects created once.
- If the canvas is ever removed (SPA route, tab component): `geometry.dispose()`, `material.dispose()`, `renderer.dispose()`.
- GLSL: at most 4 fbm octaves, no loops with dynamic bounds, no `pow`/`sin` on hot paths where a multiply works.
- Text and CTAs stay in HTML above the canvas (`z-index`), so selection, SEO and contrast checks keep working.
