#!/usr/bin/env node
/**
 * detect-project.mjs — figure out what kind of project we are integrating into.
 *
 * Usage: node detect-project.mjs [projectDir] [--json]
 *
 * Prints a summary (and JSON with --json):
 *   platform   web | react-native | none | unknown
 *   framework  vite | next | cra | remix | expo | bare-rn | react-unknown | none
 *   router     react-router | next-app | next-pages | expo-router | react-navigation | none
 *   pm         npm | yarn | pnpm | bun
 *   typescript true/false, srcDir, entry candidates, env file convention, ethora package already installed
 *   backend    servers in any language (Node, Python, PHP, Ruby, Go, Java/Kotlin, .NET) found in this project,
 *              its subfolders (server/, backend/, api/, apps/*, packages/*) and sibling folders —
 *              decides whether the client-JWT token route can be added here
 */
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';

const args = process.argv.slice(2);
const JSON_OUT = args.includes('--json');
const dir = resolve(args.find((a) => !a.startsWith('--')) || process.cwd());

const readJson = (p) => { try { return JSON.parse(readFileSync(p, 'utf8')); } catch { return null; } };
const has = (...p) => existsSync(join(dir, ...p));
const pkg = readJson(join(dir, 'package.json'));
const deps = { ...(pkg?.dependencies || {}), ...(pkg?.devDependencies || {}) };
const dep = (n) => deps[n];

const result = {
  dir,
  hasPackageJson: !!pkg,
  name: pkg?.name || null,
  platform: 'unknown',
  framework: 'none',
  router: 'none',
  pm: 'npm',
  typescript: has('tsconfig.json'),
  srcDir: has('src') ? 'src' : '.',
  react: dep('react') || null,
  reactNative: dep('react-native') || null,
  expo: dep('expo') || null,
  ethoraWeb: dep('@ethora/chat-component') || null,
  ethoraRn: dep('@ethora/chat-component-rn') || null,
  envConvention: null,
  envFile: null,
  entryCandidates: [],
  pagesDir: null,
  notes: [],
};

if (!pkg) {
  result.platform = 'none';
  result.notes.push('No package.json: this is an empty directory or not a JS project. Offer to scaffold a new app (Vite React or Expo).');
} else {
  if (has('yarn.lock')) result.pm = 'yarn';
  if (has('pnpm-lock.yaml')) result.pm = 'pnpm';
  if (has('bun.lockb') || has('bun.lock')) result.pm = 'bun';

  if (dep('react-native') || dep('expo')) {
    result.platform = 'react-native';
    result.framework = dep('expo') ? 'expo' : 'bare-rn';
    if (dep('expo-router')) result.router = 'expo-router';
    else if (dep('@react-navigation/native')) result.router = 'react-navigation';
    result.envConvention = dep('expo') ? 'EXPO_PUBLIC_' : (dep('react-native-config') ? 'react-native-config' : 'config-file');
    result.envFile = dep('expo') ? '.env' : (dep('react-native-config') ? '.env' : 'src/ethora.config.ts');
    const appJson = readJson(join(dir, 'app.json'));
    if (appJson?.expo) result.notes.push(`Expo app "${appJson.expo.name}" (slug ${appJson.expo.slug}); newArchEnabled=${appJson.expo.newArchEnabled ?? 'default'}`);
    if (result.router === 'expo-router') {
      result.pagesDir = has('app') ? 'app' : (has('src', 'app') ? 'src/app' : null);
      result.notes.push('Expo Router: a new screen is a file under app/ (e.g. app/chat.tsx or app/(tabs)/chat.tsx).');
    }
    for (const c of ['App.tsx', 'App.js', 'index.js', 'index.tsx', 'app/_layout.tsx', 'app/_layout.js', 'src/App.tsx', 'src/App.js', 'src/app/_layout.tsx', 'src/app/_layout.js']) if (has(c)) result.entryCandidates.push(c);
    if (dep('expo')) result.notes.push('The Ethora RN SDK has native modules: Expo Go cannot run it. Use a development build (`npx expo run:ios|android`).');
    const expoMajor = Number(String(dep('expo') || '').replace(/[^0-9.]/g, '').split('.')[0]);
    if (result.router === 'expo-router' && expoMajor >= 56) result.notes.push(`Expo SDK ${expoMajor} + Expo Router: app code must not import from @react-navigation/* (bundler error). Use 'expo-router' (useIsFocused) or 'expo-router/react-navigation'.`);
    const peers = ['react-native-reanimated', 'react-native-worklets', 'react-native-gesture-handler', 'react-native-svg', '@react-native-async-storage/async-storage', '@react-native-community/netinfo', 'react-native-get-random-values'];
    const reanimatedMajor = Number(String(dep('react-native-reanimated') || '4').replace(/[^0-9.]/g, '').split('.')[0]);
    const missing = peers.filter((p) => !dep(p) && !(p === 'react-native-worklets' && reanimatedMajor < 4)); // worklets: Reanimated 4+ only
    if (missing.length) result.notes.push(`Missing RN peers: ${missing.join(', ')} — install them with \`npx expo install\` BEFORE the SDK (see references/rn-integration.md §1).`);
    if (has('ios')) result.notes.push('ios/ exists → run `pod install` after installing native peers.');
  } else if (dep('react')) {
    result.platform = 'web';
    if (dep('next')) {
      result.framework = 'next';
      result.router = has('app') || has('src', 'app') ? 'next-app' : 'next-pages';
      result.pagesDir = result.router === 'next-app' ? (has('src', 'app') ? 'src/app' : 'app') : (has('src', 'pages') ? 'src/pages' : 'pages');
      result.envConvention = 'NEXT_PUBLIC_';
      result.envFile = '.env.local';
      result.notes.push('Next.js: the chat must render client-side only ("use client" + next/dynamic with ssr:false). Server routes can mint the client JWT.');
    } else if (dep('vite')) {
      result.framework = 'vite';
      result.envConvention = 'VITE_';
      result.envFile = '.env.local';
    } else if (dep('react-scripts')) {
      result.framework = 'cra';
      result.envConvention = 'REACT_APP_';
      result.envFile = '.env.local';
    } else if (dep('@remix-run/react') || dep('react-router') && has('react-router.config.ts')) {
      result.framework = 'remix';
      result.envConvention = 'VITE_';
      result.envFile = '.env';
      result.notes.push('Remix / React Router framework mode: render the chat only on the client (useEffect-gated or ClientOnly).');
    } else {
      result.framework = 'react-unknown';
      result.envConvention = 'VITE_';
      result.envFile = '.env.local';
      result.notes.push('React detected but bundler unknown — check how env vars are exposed to the browser.');
    }
    if (dep('react-router-dom') || dep('react-router')) result.router = result.router === 'none' ? 'react-router' : result.router;
    for (const c of ['src/main.tsx', 'src/main.jsx', 'src/index.tsx', 'src/index.jsx', 'src/App.tsx', 'src/App.jsx', 'app/layout.tsx', 'src/app/layout.tsx', 'pages/_app.tsx', 'src/pages/_app.tsx', 'app/root.tsx']) if (has(c)) result.entryCandidates.push(c);
    if (!result.pagesDir) {
      for (const c of ['src/pages', 'src/routes', 'src/views', 'src/screens', 'app/routes']) if (has(c)) { result.pagesDir = c; break; }
    }
  } else {
    result.platform = 'unknown';
    result.notes.push('No react / react-native dependency. If this is a backend-only repo, only the server-side token route applies here.');
  }

  const major = (v) => Number(String(v || '').replace(/[^0-9.]/g, '').split('.')[0]);
  if (result.platform === 'web' && result.react && major(result.react) < 18) result.notes.push(`React ${result.react} is below the ^18.3 peer requirement of @ethora/chat-component.`);
  if (result.platform === 'react-native' && result.reactNative && major(result.reactNative.replace(/^0\./, '')) < 73 && /^[~^]?0\./.test(result.reactNative)) result.notes.push(`react-native ${result.reactNative} is below the >=0.73 peer requirement.`);
}

// Backend detection: the "auto sign-in" flow needs a server route, in whatever language the backend uses.
// Look here, in typical subfolders and in sibling folders (monorepo / frontend+backend side by side).
const SERVER_DEPS = { express: 'express', fastify: 'fastify', koa: 'koa', '@nestjs/core': 'nest', hono: 'hono', '@hapi/hapi': 'hapi', 'next': 'next (route handlers)' };
const readText = (p) => { try { return readFileSync(p, 'utf8'); } catch { return ''; } };
// [language, manifest files, [regex on manifest text, framework name]...]
const OTHER_BACKENDS = [
  ['python', ['requirements.txt', 'pyproject.toml', 'Pipfile', 'setup.py'], [[/\bdjango\b/i, 'django'], [/\bfastapi\b/i, 'fastapi'], [/\bflask\b/i, 'flask'], [/\b(starlette|aiohttp|sanic|litestar)\b/i, 'python web']]],
  ['php', ['composer.json'], [[/laravel\/framework/i, 'laravel'], [/symfony\/framework-bundle/i, 'symfony'], [/slim\/slim/i, 'slim']]],
  ['ruby', ['Gemfile'], [[/['"]rails['"]/, 'rails'], [/['"]sinatra['"]/, 'sinatra']]],
  ['go', ['go.mod'], [[/gin-gonic\/gin/, 'gin'], [/labstack\/echo/, 'echo'], [/gofiber\/fiber/, 'fiber'], [/go-chi\/chi/, 'chi'], [/^module /m, 'go net/http']]],
  ['java/kotlin', ['pom.xml', 'build.gradle', 'build.gradle.kts'], [[/spring-boot/i, 'spring boot'], [/io\.ktor/i, 'ktor'], [/quarkus/i, 'quarkus'], [/micronaut/i, 'micronaut']]],
];
function serverFramework(p) {
  const d = { ...(p?.dependencies || {}), ...(p?.devDependencies || {}) };
  for (const [k, v] of Object.entries(SERVER_DEPS)) if (d[k]) return v;
  return null;
}
function otherBackend(abs) {
  for (const [language, files, fws] of OTHER_BACKENDS) {
    for (const file of files) {
      const text = readText(join(abs, file));
      if (!text) continue;
      for (const [re, fw] of fws) if (re.test(text)) return { language, framework: fw };
    }
  }
  try { if (readdirSync(abs).some((f) => f.endsWith('.csproj')) && readdirSync(abs).some((f) => /^(Program|Startup)\.cs$/.test(f))) return { language: 'c#', framework: 'asp.net core' }; } catch { /* ignore */ }
  return null;
}
const backendCandidates = [];
const seen = new Set();
const consider = (d) => {
  const abs = resolve(d);
  if (seen.has(abs)) return; seen.add(abs);
  const relation = abs === dir ? 'this project' : (abs.startsWith(dir) ? 'subfolder' : 'sibling');
  const fw = serverFramework(readJson(join(abs, 'package.json')));
  if (fw) { backendCandidates.push({ dir: abs, language: 'node', framework: fw, relation }); return; }
  const other = otherBackend(abs);
  if (other) backendCandidates.push({ dir: abs, ...other, relation });
};
const listDirs = (d) => { try { return readdirSync(d).filter((f) => !f.startsWith('.') && f !== 'node_modules' && statSync(join(d, f)).isDirectory()).map((f) => join(d, f)); } catch { return []; } };
consider(dir);
for (const sub of listDirs(dir)) { consider(sub); if (/^(apps|packages|services)$/.test(sub.split('/').pop())) listDirs(sub).forEach(consider); }
for (const sib of listDirs(resolve(dir, '..'))) consider(sib);
result.backend = { found: backendCandidates.length > 0, candidates: backendCandidates.slice(0, 10) };
if (result.backend.found) result.notes.push(`Backend candidates: ${backendCandidates.map((b) => `${b.dir} (${b.language}: ${b.framework}, ${b.relation})`).join('; ')}. Confirm with the user that they own it before adding the token route (any language works: see SKILL.md §7).`);
else result.notes.push('No backend found here or next to this project. Ask the user: backend in another repo, owned by another team, or none at all (see SKILL.md §7).');

// existing pages/screens listing (helps the "which page?" question)
if (result.pagesDir && has(result.pagesDir)) {
  try {
    const walk = (d, depth = 0) => {
      if (depth > 2) return [];
      return readdirSync(join(dir, d)).flatMap((f) => {
        const p = join(d, f);
        if (f === 'node_modules' || f.startsWith('.')) return [];
        if (statSync(join(dir, p)).isDirectory()) return walk(p, depth + 1);
        return /\.(t|j)sx?$/.test(f) ? [p] : [];
      });
    };
    result.existingPages = walk(result.pagesDir).slice(0, 60);
  } catch { /* ignore */ }
}

if (JSON_OUT) {
  console.log(JSON.stringify(result, null, 2));
} else {
  console.log(`Project: ${result.name || '(no package.json)'}  @ ${dir}`);
  console.log(`  platform:   ${result.platform}`);
  console.log(`  framework:  ${result.framework}`);
  console.log(`  router:     ${result.router}`);
  console.log(`  pm:         ${result.pm}   typescript: ${result.typescript}`);
  console.log(`  react:      ${result.react || '-'}   react-native: ${result.reactNative || '-'}   expo: ${result.expo || '-'}`);
  console.log(`  ethora:     web=${result.ethoraWeb || '-'}  rn=${result.ethoraRn || '-'}`);
  console.log(`  env:        ${result.envConvention || '-'} → ${result.envFile || '-'}`);
  console.log(`  entries:    ${result.entryCandidates.join(', ') || '-'}`);
  if (result.pagesDir) console.log(`  pages dir:  ${result.pagesDir}${result.existingPages?.length ? ' (' + result.existingPages.length + ' files)' : ''}`);
  console.log(`  backend:    ${result.backend.found ? result.backend.candidates.map((b) => `${b.dir} (${b.language}: ${b.framework}, ${b.relation})`).join('; ') : 'none found'}`);
  for (const n of result.notes) console.log(`  note: ${n}`);
}
