// Load this function once into the already initialized CUA runtime.
// The parent agent verifies authorization for the request's workout ID and supplies
// a bound, documented CUA Tab. SDK/server do not launch/control the browser.
// First attempt: await observeQueuedWorkout(requestReady.value, reusableWorkoutTab,
//   {privateRoot: publicMcpContext.value.browser_home}).
// If and only if status is browser_not_ready: retry the same request with
// {privateRoot: publicMcpContext.value.browser_home, navigate:false}; do not reload
// on that loading retry. Never retry access_denied.
// After observation_saved, call the package publish-read command with unchanged run_dir/request_id.
// It is not acceptable to save offline fixtures as real observations.
async function observeQueuedWorkout(meta, tab, {privateRoot, navigate = true} = {}) {
  const fs = await import('node:fs/promises');
  if (typeof privateRoot !== 'string' || !privateRoot.startsWith('/') ||
      privateRoot.includes('\0') || privateRoot.split('/').includes('..')) return {status:'request_rejected'};
  const root = privateRoot.replace(/\/$/, '') + '/read';
  const token = /^[0-9a-f]{32}$/;
  if (!meta || typeof meta.run_dir !== 'string' || typeof meta.request_id !== 'string' ||
      !token.test(meta.request_id) || !meta.run_dir.startsWith(root + '/runs/') ||
      !token.test(meta.run_dir.slice((root + '/runs/').length))) {
    return {status: 'request_rejected'};
  }
  const directory = meta.run_dir + '/queue/' + meta.request_id;
  if (meta.request_dir !== directory || typeof navigate !== 'boolean') return {status:'request_rejected'};
  const rootStat = await fs.lstat(root);
  for (const path of [root, root + '/runs', meta.run_dir, meta.run_dir + '/queue', directory]) {
    const info = await fs.lstat(path);
    if (!info.isDirectory() || info.isSymbolicLink() || (info.mode & 511) !== 448 || info.uid !== rootStat.uid) {
      return {status:'private_directory_rejected'};
    }
  }
  const file = await fs.open(directory + '/request.json', fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
  let request;
  try {
    const info = await file.stat();
    if (!info.isFile() || (info.mode & 511) !== 384 || info.uid !== rootStat.uid || info.size > 65536) {
      return {status:'request_rejected'};
    }
    request = JSON.parse(await file.readFile({encoding:'utf8'}));
  } finally { await file.close(); }
  const created = Date.parse(request.created_at);
  const expiry = Date.parse(request.expires_at);
  if (request.request_id !== meta.request_id || request.operation !== 'read_workout' ||
      !Number.isSafeInteger(request.workout_id) || request.workout_id < 1 ||
      request.workout_id !== meta.workout_id || !Number.isFinite(created) ||
      expiry - created !== 300000 || Date.now() < created || Date.now() >= expiry) {
    return {status:'request_rejected'};
  }
  const canonical = 'https://connect.garmin.com/app/workout/' + String(request.workout_id);
  // This is the only navigation target. Access/tool exceptions propagate untouched
  // to the parent (do not log them or try another route).
  // Tab.reload is documented by the target CUA API. An initial same-URL read
  // refreshes the page after request creation; a loading retry only re-reads DOM.
  if (navigate) {
    if (await tab.url() === canonical) await tab.reload();
    else await tab.goto(canonical);
  }
  const page = new URL(await tab.url());
  if (page.origin !== 'https://connect.garmin.com' || page.pathname !== '/app/workout/' + String(request.workout_id)) {
    return {status:'access_denied_or_wrong_page', request_id:request.request_id};
  }
  const result = await tab.playwright.evaluate(() => {
    const visible = e => Boolean(e && e.getClientRects().length);
    const blockers = Array.from(document.querySelectorAll(
      'input[type="password"],input[autocomplete="one-time-code"],iframe[src*="captcha" i],iframe[title*="challenge" i],[id*="captcha" i]'));
    const pageText = document.body?.innerText || '';
    if (blockers.some(visible) || /access denied|permission denied|not authorized|two[- ](?:step|factor) authentication|verify your identity|驗證您的身分|存取被拒|權限不足/i.test(pageText)) {
      return {status:'access_denied'};
    }
    // These classes were observed on the authorized workout page. Any changed UI
    // is treated as unknown/loading; do not discover unrelated account/profile data.
    const title = document.querySelector('.WorkoutName_workoutName__E7sq8');
    const boxes = Array.from(document.querySelectorAll('.WorkoutStep_stepReadOnlyWrapper__u3DgD')).filter(visible);
    const name = visible(title) ? title.innerText.trim() || null : null;
    if (!name && boxes.length === 0) return {status:'browser_not_ready'};
    const steps = boxes.map(box => {
      const heading = box.querySelector('.WorkoutStep_stepTitle__kgFG7');
      const lines = box.innerText.split('\n').map(s => s.trim()).filter(Boolean);
      const label = lines.indexOf('Total Time');
      const match = label > 0 ? /^(\d+):(\d{2})$/.exec(lines[label - 1]) : null;
      const seconds = match && Number(match[2]) < 60 ? Number(match[1]) * 60 + Number(match[2]) : null;
      return {name:visible(heading) ? heading.innerText.trim() || null : null,
        duration_seconds:seconds, targets:null};
    });
    return {status:'observed', selected:{name, sport:null, steps:steps.length ? steps : null,
      calendar_evidence:'unknown', watch_evidence:'unknown', api_authentication:'unknown'}};
  });
  if (result.status !== 'observed') return {status:result.status, request_id:request.request_id};
  const pageAfter = new URL(await tab.url());
  if (pageAfter.origin !== 'https://connect.garmin.com' || pageAfter.pathname !== '/app/workout/' + String(request.workout_id) || Date.now() >= expiry) {
    return {status:'request_rejected'};
  }
  const observation = {observed_at:new Date().toISOString(), ...result.selected};
  const payload = JSON.stringify(observation) + '\n';
  if (new TextEncoder().encode(payload).length > 65536) return {status:'observation_rejected'};
  const temporary = directory + '/.selected-' + request.request_id + '.tmp';
  const selected = await fs.open(temporary, 'wx', 384);
  try { await selected.chmod(384); await selected.writeFile(payload); await selected.sync(); }
  finally { await selected.close(); }
  // Hard link is atomic and refuses to overwrite any old observation.
  await fs.link(temporary, directory + '/selected-observation.json');
  await fs.unlink(temporary);
  const directoryHandle = await fs.open(directory, fs.constants.O_RDONLY | fs.constants.O_DIRECTORY | fs.constants.O_NOFOLLOW);
  try { await directoryHandle.sync(); } finally { await directoryHandle.close(); }
  return {status:'observation_saved', request_id:request.request_id,
    run_dir:meta.run_dir, request_dir:directory};
}

// Pure local fingerprinting of the parent's already observed OWN account-menu
// View Profile href. This does not read a browser, navigate, approve, or attest it.
// Keep the href in the CUA runtime; do not print/store it or put it in a command.
async function accountKeyFromProfileUrl(profileUrl) {
  if (typeof profileUrl !== 'string' || profileUrl.length > 1024 ||
      /[\x00-\x20\x7f-\uffff]/.test(profileUrl)) return null;
  let url;
  try { url = new URL(profileUrl); } catch { return null; }
  const match = /^\/app\/profile\/([A-Za-z0-9._~%-]{1,160})\/?$/.exec(url.pathname);
  if (url.protocol !== 'https:' || url.hostname !== 'connect.garmin.com' ||
      url.port || url.username || url.password || url.search || url.hash || !match) return null;
  const canonical = 'https://connect.garmin.com/app/profile/' + match[1];
  const {createHash} = await import('node:crypto');
  return createHash('sha256').update('garmin-browser-account-v1\0' + canonical, 'utf8').digest('hex');
}
