import { ipcRenderer } from 'electron';

// Runs in the isolated sandbox, not the school's JS world. No contextBridge,
// filesystem, general IPC or credentials are exposed to remote scripts.
if (process.isMainFrame) {
  let automationStopped = false;
  ipcRenderer.on('lms:stop-automation', () => { automationStopped = true; });
  let trustedGestureAt = 0;
  let trustedGestureTarget: Element | null = null;
  const markTrustedGesture = (event: Event) => {
    if (event.isTrusted && event.target instanceof Element) {
      trustedGestureAt = Date.now(); trustedGestureTarget = event.target;
    }
  };
  const hasRecentTrustedGesture = (form: HTMLFormElement) =>
    Date.now() - trustedGestureAt < 1500 && !!trustedGestureTarget && form.contains(trustedGestureTarget);
  const page = () => location.origin + location.pathname;
  const fieldKey = (field: HTMLInputElement) => field.name || field.id;
  // Microsoft ADFS uses a span whose click handler normalizes the NetID and
  // calls form.submit(); neither a submit event nor a native submitter exists.
  // Match the complete known form shape, never an arbitrary page button.
  function adfsSubmit(form: HTMLFormElement) {
    if (!/^\/adfs\/ls\/?$/i.test(location.pathname) || form.id !== 'loginForm' ||
        !form.querySelector('input#userNameInput[name=UserName]') ||
        !form.querySelector('input#passwordInput[name=Password][type=password]')) return null;
    const button = form.querySelector<HTMLElement>('span#submitButton[role=button]');
    return button?.getClientRects().length && button.getAttribute('aria-disabled') !== 'true' ? button : null;
  }
  function genericSubmit(form: HTMLFormElement) {
    const controls = Array.from(form.querySelectorAll<HTMLElement>(
      'button[type=submit],input[type=submit],button:not([type]),input[type=image],[role=button]',
    )).filter(el => el.getClientRects().length && !el.hasAttribute('disabled') && el.getAttribute('aria-disabled') !== 'true');
    if (controls.length !== 1) return null;
    const text = `${controls[0]!.textContent ?? ''} ${controls[0]!.getAttribute('aria-label') ?? ''}`;
    return /sign[ -]?in|log[ -]?in|continue|next|submit/i.test(text) ? controls[0]! : null;
  }
  function inspect(form: HTMLFormElement) {
    if (location.protocol !== 'https:' || form.method.toLowerCase() !== 'post') return null;
    const action = new URL(form.action || location.href);
    if (action.username || action.password) return null;
    const fields = Array.from(form.elements).filter((el): el is HTMLInputElement => el instanceof HTMLInputElement);
    if (fields.some(el => el.autocomplete === 'one-time-code' ||
        (el.type !== 'hidden' && /otp|one.?time|verification|mfa/i.test(fieldKey(el))))) return null;
    const passwords = fields.filter(el => el.type === 'password' && !el.disabled && el.getClientRects().length > 0);
    if (passwords.length !== 1) return null; // Password changes / confirmations.
    const password = passwords[0]!;
    if (/new-password|one-time-code/i.test(password.autocomplete) || /otp|one.?time|verification|pin|mfa|code/i.test(fieldKey(password))) return null;
    const users = fields.filter(el => ['text', 'email'].includes(el.type) && !el.disabled && el.getClientRects().length > 0 &&
      (el.autocomplete === 'username' || /user|email|login|netid|account/i.test(fieldKey(el))));
    if (users.length !== 1 || !fieldKey(password) || !fieldKey(users[0]!)) return null;
    const username = users[0]!;
    return { username, password, form: { page: page(), action: action.origin + action.pathname, usernameField: fieldKey(username), passwordField: fieldKey(password) } };
  }
  function inspectStep(form: HTMLFormElement) {
    if (location.protocol !== 'https:' || form.method.toLowerCase() !== 'post') return null;
    let action: URL;
    try { action = new URL(form.action || location.href); } catch { return null; }
    if (action.username || action.password) return null;
    const fields = Array.from(form.elements).filter((el): el is HTMLInputElement => el instanceof HTMLInputElement);
    if (fields.some(el => el.autocomplete === 'one-time-code' || /captcha|recaptcha|challenge|verification|mfa|otp/i.test(fieldKey(el)))) return null;
    const visible = fields.filter(el => !el.disabled && el.getClientRects().length > 0);
    const passwords = visible.filter(el => el.type === 'password');
    const users = visible.filter(el => ['text', 'email'].includes(el.type) && (el.autocomplete === 'username' || /user|email|login|netid|account/i.test(fieldKey(el))));
    if (passwords.length === 1 && users.length === 0) {
      const field = passwords[0]!;
      if (/new-password|one-time-code/i.test(field.autocomplete) || /new|confirm|otp|verification|pin|mfa|code/i.test(fieldKey(field))) return null;
      return { field, form: { page: page(), action: action.origin + action.pathname, field: fieldKey(field), kind: 'password' as const } };
    }
    if (passwords.length === 0 && users.length === 1 && visible.filter(el => el.type !== 'hidden').length === 1) {
      const field = users[0]!;
      return { field, form: { page: page(), action: action.origin + action.pathname, field: fieldKey(field), kind: 'username' as const } };
    }
    return null;
  }
  function inspectOtp(form: HTMLFormElement) {
    if (location.protocol !== 'https:' || form.method.toLowerCase() !== 'post') return null;
    let action: URL;
    try { action = new URL(form.action || location.href); } catch { return null; }
    if (action.username || action.password) return null;
    const fields = Array.from(form.elements).filter((el): el is HTMLInputElement => el instanceof HTMLInputElement);
    if (fields.some(el => el.type === 'password' || /captcha|recaptcha|challenge/i.test(fieldKey(el)))) return null;
    const candidates = fields.filter(el => !el.disabled && el.getClientRects().length > 0 &&
      ['text', 'tel', 'number'].includes(el.type) &&
      (el.autocomplete === 'one-time-code' || /otp|one.?time|verification|mfa|passcode|security.?code/i.test(fieldKey(el))));
    if (candidates.length !== 1) return null;
    const field = candidates[0]!;
    return { field, form: { page: page(), action: action.origin + action.pathname, otpField: fieldKey(field) } };
  }
  function capture(form: HTMLFormElement) {
    const found = inspect(form);
    if (!found?.username.value || !found.password.value) return;
    ipcRenderer.send('lms:login-capture', { form: found.form, username: found.username.value, password: found.password.value });
  }
  function captureStep(form: HTMLFormElement) {
    const found = inspectStep(form);
    if (!found?.field.value) return;
    ipcRenderer.send('lms:login-capture-step', { form: found.form, value: found.field.value });
  }
  // Capture only a real submission gesture, never arbitrary typing, script
  // clicks or an MFA code. Persistence still requires verified LMS identity.
  document.addEventListener('submit', event => {
    // requestSubmit() can create a trusted event even when page JS invokes it.
    // Require a recent real user gesture as well; automatic fill needs no recapture.
    if (!event.isTrusted || !(event.target instanceof HTMLFormElement) || !hasRecentTrustedGesture(event.target)) return;
    capture(event.target);
    captureStep(event.target);
  }, true);
  document.addEventListener('click', event => {
    if (!event.isTrusted || !(event.target instanceof Element)) return;
      const form = event.target.closest('form');
      const button = form && (adfsSubmit(form) ?? genericSubmit(form));
    if (button && button.contains(event.target)) { capture(form!); captureStep(form!); }
  }, true);
  document.addEventListener('keydown', event => {
    if (!event.isTrusted || !(event.target instanceof Element)) return;
    const form = event.target.closest('form');
    const button = form && (adfsSubmit(form) ?? genericSubmit(form));
    if (!button) return;
    if ((event.key === 'Enter' && event.target.matches('#userNameInput,#passwordInput')) ||
        (event.key === ' ' && button.contains(event.target))) { capture(form!); captureStep(form!); }
  }, true);
  document.addEventListener('pointerdown', markTrustedGesture, true);
  document.addEventListener('click', markTrustedGesture, true);
  document.addEventListener('keydown', markTrustedGesture, true);
  let running = false;
  const attempted = new WeakSet<HTMLFormElement>();
  const attemptedOtp = new WeakSet<HTMLFormElement>();
  const attemptedSteps = new WeakSet<HTMLFormElement>();
  const setInputValue = (field: HTMLInputElement, value: string) => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(field, value);
    field.dispatchEvent(new Event('input', { bubbles: true }));
    field.dispatchEvent(new Event('change', { bubbles: true }));
  };
  const fillOtp = async () => {
    for (const form of Array.from(document.forms)) {
      if (automationStopped || attemptedOtp.has(form)) return;
      const found = inspectOtp(form);
      if (!found) continue;
      attemptedOtp.add(form);
      const saved = await ipcRenderer.invoke('lms:login-otp-fill', found.form);
      if (automationStopped || !saved || !form.isConnected || page() !== found.form.page || found.field.value) continue;
      const current = inspectOtp(form);
      if (!current || JSON.stringify(current.form) !== JSON.stringify(found.form)) continue;
      setInputValue(found.field, saved.code);
      ipcRenderer.send('lms:login-progress', found.form, 'otp-filled');
      const filledCode = found.field.value;
      const manual = (event: Event) => {
        if (!event.isTrusted || event.target !== found.field) return;
        automationStopped = true; ipcRenderer.send('lms:login-progress', found.form, 'otp-manual');
      };
      document.addEventListener('input', manual, true);
      try { await new Promise(resolve => setTimeout(resolve, 2000)); }
      finally { document.removeEventListener('input', manual, true); }
      if (automationStopped || !form.isConnected || found.field.value !== filledCode ||
          JSON.stringify(inspectOtp(form)?.form) !== JSON.stringify(found.form)) continue;
      if (!await ipcRenderer.invoke('lms:login-otp-submit', found.form) || automationStopped || !form.isConnected || found.field.value !== filledCode) continue;
      const submit = form.querySelector<HTMLButtonElement | HTMLInputElement>('button[type=submit],input[type=submit],button:not([type])');
      if (submit && !submit.disabled) form.requestSubmit(submit);
    }
  };
  const fill = async () => {
    if (running || automationStopped) return;
    running = true;
    try {
      for (const form of Array.from(document.forms)) {
        if (automationStopped) return;
        if (attempted.has(form)) continue;
        const found = inspect(form);
        if (!found) continue;
        attempted.add(form);
        const saved = await ipcRenderer.invoke('lms:login-fill', found.form);
        if (automationStopped || !saved || !form.isConnected || page() !== found.form.page ||
            (found.username.value && found.username.value !== saved.username) || found.password.value) continue;
        const current = inspect(form);
        if (!current || JSON.stringify(current.form) !== JSON.stringify(found.form)) continue;
        for (const [field, value] of [[found.username, saved.username], [found.password, saved.password]] as const) {
          if (automationStopped) return;
          setInputValue(field, value);
        }
        ipcRenderer.send('lms:login-progress', found.form, 'filled');
        if (!automationStopped && saved.autoLogin) {
          const filledUser = found.username.value, filledPassword = found.password.value;
          const manual = (event: Event) => {
            if (!event.isTrusted || (event.target !== found.username && event.target !== found.password)) return;
            automationStopped = true; ipcRenderer.send('lms:login-progress', found.form, 'manual');
          };
          document.addEventListener('input', manual, true);
          // A short, cancellable grace period also gives users time to take over.
          try { await new Promise(resolve => setTimeout(resolve, 2000)); }
          finally { document.removeEventListener('input', manual, true); }
          if (automationStopped || !form.isConnected) continue;
          if (found.username.value !== filledUser || found.password.value !== filledPassword ||
              JSON.stringify(inspect(form)?.form) !== JSON.stringify(found.form)) {
            ipcRenderer.send('lms:login-progress', found.form, 'manual'); continue;
          }
          if (!await ipcRenderer.invoke('lms:login-submit', found.form) || automationStopped || !form.isConnected ||
              found.username.value !== filledUser || found.password.value !== filledPassword ||
              JSON.stringify(inspect(form)?.form) !== JSON.stringify(found.form)) continue;
          const submit = adfsSubmit(form) ?? genericSubmit(form);
          if (submit) { submit.click(); continue; } // Run the school's own validation/normalization.
          if (typeof form.requestSubmit === 'function') form.requestSubmit();
        }
      }
      for (const form of Array.from(document.forms)) {
        if (automationStopped || attemptedSteps.has(form)) continue;
        const found = inspectStep(form);
        if (!found) continue;
        attemptedSteps.add(form);
        const saved = await ipcRenderer.invoke('lms:login-fill', found.form);
        if (automationStopped || !saved || !form.isConnected || page() !== found.form.page || found.field.value) continue;
        const current = inspectStep(form);
        if (!current || JSON.stringify(current.form) !== JSON.stringify(found.form)) continue;
        setInputValue(found.field, saved.value);
        ipcRenderer.send('lms:login-progress', found.form, 'step-filled');
        if (!saved.autoLogin) continue;
        const filled = found.field.value;
        const manual = (event: Event) => {
          if (!event.isTrusted || event.target !== found.field) return;
          automationStopped = true; ipcRenderer.send('lms:login-progress', found.form, 'step-manual');
        };
        document.addEventListener('input', manual, true);
        try { await new Promise(resolve => setTimeout(resolve, 2000)); }
        finally { document.removeEventListener('input', manual, true); }
        if (automationStopped || !form.isConnected || found.field.value !== filled || JSON.stringify(inspectStep(form)?.form) !== JSON.stringify(found.form)) continue;
        if (!await ipcRenderer.invoke('lms:login-submit', found.form) || automationStopped || found.field.value !== filled) continue;
        const submit = adfsSubmit(form) ?? genericSubmit(form);
        if (submit) submit.click(); else if (typeof form.requestSubmit === 'function') form.requestSubmit();
      }
      await fillOtp();
    } catch { /* No secrets or provider errors in renderer logs. Manual login remains available. */ }
    finally { running = false; }
  };
  window.addEventListener('DOMContentLoaded', () => {
    void fill();
    let timer: ReturnType<typeof setTimeout> | undefined;
    const observer = new MutationObserver(() => { clearTimeout(timer); timer = setTimeout(() => void fill(), 150); });
    observer.observe(document.documentElement, { childList: true, subtree: true });
    window.addEventListener('pagehide', () => { observer.disconnect(); clearTimeout(timer); }, { once: true });
  }, { once: true });
}
