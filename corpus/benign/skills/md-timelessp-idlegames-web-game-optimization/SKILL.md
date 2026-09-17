---
name: web-game-optimization
description: Optimize web-based games for performance, accessibility, and cross-device compatibility. Use when improving game speed, reducing load times, or enhancing game accessibility.
---

# Web Game Optimization

Optimize your games for smooth performance across all devices, from high-end desktops to low-end mobile phones. This includes canvas optimization for complex scenes, managing many entities, synthesized audio, and frame-rate independent animations.

## Performance Analysis & Measurement

### FPS and Frame Time Monitoring
```javascript
class PerformanceMonitor {
  constructor() {
    this.frameCount = 0;
    this.fps = 0;
    this.frameTime = 0;
    this.lastTime = performance.now();
  }

  update() {
    const now = performance.now();
    this.frameTime = now - this.lastTime;
    this.lastTime = now;
    this.frameCount++;
  }

  logMetrics() {
    if (this.frameCount % 60 === 0) {
      console.log(`FPS: ${(1000 / this.frameTime).toFixed(1)}, ` +
                  `Frame Time: ${this.frameTime.toFixed(2)}ms`);
    }
  }
}
```

### Memory Profiling
```javascript
// Monitor memory usage
if (performance.memory) {
  const used = Math.round(performance.memory.usedJSHeapSize / 1048576);
  const limit = Math.round(performance.memory.jsHeapSizeLimit / 1048576);
  console.log(`Memory: ${used}MB / ${limit}MB`);
}
```

### Chrome DevTools Integration
```javascript
// Measure performance with User Timing API
performance.mark('game-update-start');
// ... game update code ...
performance.mark('game-update-end');
performance.measure('game-update', 'game-update-start', 'game-update-end');

// Get measurements
const measures = performance.getEntriesByType('measure');
measures.forEach(m => console.log(`${m.name}: ${m.duration.toFixed(2)}ms`));
```

## Rendering Optimization

## Canvas Optimization

### Canvas Optimization

#### Using performance.now() for Frame-Rate Independent Animation
For consistent animation across different frame rates, use wall-clock time instead of frame counting:

```javascript
// GOOD - animations run at same speed regardless of FPS
const timeSeconds = performance.now() * 0.001;

// Sine wave animation (slow breath/float)
const breathe = Math.sin(timeSeconds * 2) * 2; // Consistent speed

// Canvas drawing uses this for smooth animation
ctx.translate(x, y + breathe);

// Wave patterns with consistent phase
const wavePhase = timeSeconds * 0.5 + xPosition * 0.02;
ctx.lineTo(x, y + Math.sin(wavePhase) * amplitude);
```

#### Rendering Complex Scenes with Multiple Layers
For games with many arenas, particles, and decorative elements:

```javascript
// Group rendering operations by type to minimize state changes
class RenderBatcher {
  constructor(ctx) {
    this.ctx = ctx;
    this.batches = {};
  }
  
  add(layer, x, y, width, height, fillColor) {
    const key = `${layer}-${fillColor}`;
    if (!this.batches[key]) this.batches[key] = [];
    this.batches[key].push({x, y, width, height});
  }
  
  flush() {
    for (const [key, rects] of Object.entries(this.batches)) {
      const [, color] = key.split('-');
      this.ctx.fillStyle = color;
      for (const rect of rects) {
        this.ctx.fillRect(rect.x, rect.y, rect.width, rect.height);
      }
    }
    this.batches = {};
  }
}
```

#### Object Pooling for Weapons/Projectiles
Reuse objects instead of creating/destroying to reduce garbage collection:

```javascript
class ProjectilePool {
  constructor(maxSize = 100) {
    this.pool = [];
    this.active = [];
    
    for (let i = 0; i < maxSize; i++) {
      this.pool.push(new Projectile());
    }
  }
  
  create(x, y, vx, vy) {
    let proj = this.pool.pop();
    if (!proj) proj = new Projectile();
    proj.reset(x, y, vx, vy);
    this.active.push(proj);
    return proj;
  }
  
  update(dt) {
    for (let i = this.active.length - 1; i >= 0; i--) {
      this.active[i].update(dt);
      if (this.active[i].isDead) {
        this.pool.push(this.active.splice(i, 1)[0]);
      }
    }
  }
}
```

### Web Audio Synthesis vs Pre-recorded

Web Audio API synthesis is CPU-light for short sound effects but uses CPU. Pre-recorded audio is better for continuous loops:

```javascript
// Synthesis: Good for short sfx, minimal file size
const synth = (freq = 60, duration = 0.1, vol = 0.1) => {
  const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  
  osc.frequency.value = freq;
  gain.gain.setValueAtTime(vol, audioCtx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + duration);
  
  osc.connect(gain);
  gain.connect(audioCtx.destination);
  osc.start();
  osc.stop(audioCtx.currentTime + duration);
};

// Use synthesis for game effects
synth(100, 0.15); // Punch sound
synth(80, 0.2);   // Kick sound
```

## DOM Rendering Optimization
```javascript
// Use CSS transforms and opacity (GPU-accelerated)
// GOOD - GPU accelerated
element.style.transform = 'translate3d(x, y, 0)';
element.style.opacity = 0.5;

// BAD - CPU heavy reflows
element.style.left = x + 'px';
element.style.top = y + 'px';

// Batch DOM updates
const fragment = document.createDocumentFragment();
for (let i = 0; i < count; i++) {
  const el = document.createElement('div');
  fragment.appendChild(el);
}
container.appendChild(fragment); // Single reflow

// Reduce reflows with classList
element.classList.toggle('active'); // Better than style changes
```

### WebGL Optimization
```javascript
// Use WebGL for complex graphics
const canvas = document.createElement('canvas');
const gl = canvas.getContext('webgl2');

// Batch render calls
// Use fewer draw calls with larger vertex buffers
// Reuse shaders and programs
```

## JavaScript Optimization

### Memory Management
```javascript
// 1. Avoid memory leaks
class GameEntity {
  constructor() {
    this.listeners = [];
  }

  addEventListener(event, handler) {
    this.listeners.push({ event, handler });
    element.addEventListener(event, handler);
  }

  destroy() {
    // Clean up listeners!
    this.listeners.forEach(({ event, handler }) => {
      element.removeEventListener(event, handler);
    });
    this.listeners = [];
  }
}

// 2. Use object pooling for frequently created objects
class BulletPool {
  constructor(size = 1000) {
    this.available = [];
    for (let i = 0; i < size; i++) {
      this.available.push(new Bullet());
    }
    this.active = [];
  }

  get() {
    return this.available.pop() || new Bullet();
  }

  return(bullet) {
    bullet.reset();
    this.available.push(bullet);
  }

  update(dt) {
    const toReturn = [];
    this.active.forEach(bullet => {
      bullet.update(dt);
      if (bullet.isDead) {
        toReturn.push(bullet);
      }
    });
    toReturn.forEach(b => {
      this.active.splice(this.active.indexOf(b), 1);
      this.return(b);
    });
  }
}

// 3. Minimize garbage collection pressure
// Reuse objects instead of creating new ones
const velocity = { x: 0, y: 0 };
velocity.x = newVelX;  // Reuse
velocity.y = newVelY;

// NOT: const velocity = { x: newVelX, y: newVelY }; // New object
```

### Algorithm Optimization
```javascript
// 1. Use spatial indexing for collision detection
class SpatialIndex {
  constructor(cellSize = 100) {
    this.cellSize = cellSize;
    this.grid = new Map();
  }

  insert(entity) {
    const key = this.getCellKey(entity);
    if (!this.grid.has(key)) {
      this.grid.set(key, []);
    }
    this.grid.get(key).push(entity);
  }

  getCellKey(entity) {
    const x = Math.floor(entity.x / this.cellSize);
    const y = Math.floor(entity.y / this.cellSize);
    return `${x},${y}`;
  }

  getNearby(entity) {
    const nearby = [];
    const key = this.getCellKey(entity);
    const [cx, cy] = key.split(',').map(Number);
    
    for (let x = cx - 1; x <= cx + 1; x++) {
      for (let y = cy - 1; y <= cy + 1; y++) {
        const cellKey = `${x},${y}`;
        nearby.push(...(this.grid.get(cellKey) || []));
      }
    }
    return nearby;
  }
}

// 2. Use lookup tables instead of calculations
const sinLookup = new Float32Array(360);
for (let i = 0; i < 360; i++) {
  sinLookup[i] = Math.sin(i * Math.PI / 180);
}
// Use: sinLookup[angle] instead of Math.sin(angle * Math.PI / 180)

// 3. Avoid expensive operations in hot loops
// BAD
for (let i = 0; i < entities.length; i++) {
  entities[i].draw(ctx, Math.cos(rotation), Math.sin(rotation));
}

// GOOD
const cos = Math.cos(rotation);
const sin = Math.sin(rotation);
for (let i = 0; i < entities.length; i++) {
  entities[i].draw(ctx, cos, sin);
}
```

## Asset Loading & Optimization

### Lazy Loading
```javascript
class AssetLoader {
  constructor() {
    this.assets = new Map();
    this.loading = new Map();
  }

  async load(key, src) {
    // Return if already loading
    if (this.loading.has(key)) {
      return this.loading.get(key);
    }

    const promise = this.loadAsset(key, src);
    this.loading.set(key, promise);
    
    try {
      await promise;
      this.loading.delete(key);
    } catch (e) {
      this.loading.delete(key);
      throw e;
    }
  }

  async loadAsset(key, src) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        this.assets.set(key, img);
        resolve(img);
      };
      img.onerror = reject;
      img.src = src;
    });
  }

  get(key) {
    return this.assets.get(key);
  }
}
```

### Image Compression & Formats
```javascript
// Use modern image formats with fallbacks
const imageUrl = 
  'image.webp' // Modern browsers
  : 'image.png'; // Fallback

// Optimize image sizes
// - Use CSS to downscale large images
// - Provide multiple sizes for different devices
// - Use srcset for responsive images
```

### Audio Optimization
```javascript
// 1. Use compressed audio formats
// MP3 for wide compatibility, OGG for modern browsers

// 2. Use shorter loops for background music
// - 30-60 second loops for repetitive music

// 3. Lazy load audio
class AudioManager {
  preloadAudio(key, src) {
    const audio = new Audio();
    audio.src = src;
    this.assets.set(key, audio);
  }

  // Don't load all audio at startup!
  // Load based on level/scene
}
```

## Mobile Optimization

### Device Detection
```javascript
const deviceInfo = {
  isMobile: /Android|webOS|iPhone|iPad|iPod|BlackBerry/i.test(navigator.userAgent),
  isTablet: /iPad|Android(?!.*Mobile)/i.test(navigator.userAgent),
  isLandscape: window.innerWidth > window.innerHeight,
  pixelRatio: window.devicePixelRatio
};

// Adjust game quality based on device
if (deviceInfo.isMobile && deviceInfo.pixelRatio <= 2) {
  // Reduce particle count, disable shadows, etc.
  gameConfig.maxParticles = 100;
  gameConfig.enableShadows = false;
}
```

### Touch Performance
```javascript
// Use passive listeners for touch events
element.addEventListener('touchmove', handleMove, { passive: true });
element.addEventListener('touchstart', handleStart, { passive: true });

// Reduce touch event frequency with throttling
let lastTouchTime = 0;
const TOUCH_THROTTLE = 1000 / 60; // 60 FPS max

document.addEventListener('touchmove', (e) => {
  const now = Date.now();
  if (now - lastTouchTime < TOUCH_THROTTLE) return;
  lastTouchTime = now;
  
  handleTouchMove(e);
}, { passive: true });
```

### Battery & Thermal Management
```javascript
// Detect low power mode
const lowPowerMode = navigator.deviceMemory <= 4;
const slowConnection = navigator.connection?.effectiveType === '4g';

if (lowPowerMode) {
  // Reduce update frequency
  gameConfig.targetFPS = 30;
  gameConfig.maxEntities = 200;
}

// Pause game when not visible
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    game.pause();
  } else {
    game.resume();
  }
});
```

## Accessibility in Games

### Screen Reader Support
```javascript
// Provide text alternatives
const gameContainer = document.querySelector('#game');
gameContainer.setAttribute('role', 'application');
gameContainer.setAttribute('aria-label', 'Game Name - Use keyboard to play');

// Update aria-live regions for important events
const statusDiv = document.createElement('div');
statusDiv.setAttribute('aria-live', 'polite');
statusDiv.setAttribute('aria-atomic', 'true');
statusDiv.className = 'sr-only'; // Visually hidden

function updateStatus(message) {
  statusDiv.textContent = message;
}
```

### Keyboard Navigation
```javascript
class AccessibleGame {
  constructor() {
    this.keyBindings = {
      'ArrowUp': () => this.moveUp(),
      'ArrowDown': () => this.moveDown(),
      'w': () => this.moveUp(),
      's': () => this.moveDown(),
      ' ': () => this.action(),
      'Enter': () => this.action()
    };

    window.addEventListener('keydown', (e) => {
      const handler = this.keyBindings[e.key];
      if (handler) {
        e.preventDefault();
        handler();
      }
    });
  }
}
```

### Color Contrast & Colorblind Support
```css
/* Ensure sufficient contrast */
body {
  color: #222; /* Not black-on-white, helps with eye strain */
  background: #f8f9fa;
}

/* Optional: Provide colorblind-friendly themes */
[data-theme="deuteranopia"] .game-board {
  --color-primary: #0173b2;  /* Blue instead of red */
  --color-secondary: #de8f05; /* Orange instead of green */
}
```

### Motor Accessibility
```javascript
// Support multiple control schemes
const controlSchemes = {
  default: { up: 'ArrowUp', down: 'ArrowDown', action: ' ' },
  wasd: { up: 'w', down: 's', action: 'e' },
  mouse: { move: 'mousemove', action: 'click' },
  gamepad: { /* gamepad mapping */ }
};

// Provide adjustable timing windows
const timingConfig = {
  keyPressDuration: 500, // ms to register input
  comboWindow: 1000     // ms for combo inputs
};
```

## Network Optimization

### Bandwidth Reduction
```javascript
// Compress data sent over network
// Use MessagePack or similar instead of JSON
const compressed = msgpack.encode(gameState);

// Send diffs, not full states
class StateDelta {
  static compute(prev, current) {
    const delta = {};
    for (const key in current) {
      if (JSON.stringify(current[key]) !== 
          JSON.stringify(prev[key])) {
        delta[key] = current[key];
      }
    }
    return delta;
  }
}
```

## Debugging Performance Issues

### Common Bottlenecks
1. **Main Thread Blocking** - Move heavy work to Web Workers
2. **Memory Leaks** - Use Chrome DevTools Memory tab
3. **Excessive Repaints** - Check DevTools Rendering tab
4. **Heavy Computations** - Profile with Performance tab
5. **Network Delays** - Use Network throttling in DevTools

### Profiling Tools
```javascript
// Use Performance API
performance.mark('operation-start');
// ... operation ...
performance.mark('operation-end');
performance.measure('operation', 'operation-start', 'operation-end');

// Export for analysis
const measures = performance.getEntriesByType('measure');
console.table(measures);
```
