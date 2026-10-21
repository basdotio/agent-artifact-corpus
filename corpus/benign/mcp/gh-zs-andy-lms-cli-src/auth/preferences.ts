import { z } from 'zod';
import { vault, type Vault } from '../vault.js';
import type { Platform, Profile } from '../config.js';
import { parseTotpSecret, totpCode, TotpRecordSchema, type TotpRecord } from './totp.js';

/** No query strings: SSO state/nonces must not become stored form identities. */
export function loginPage(value: string): string | null {
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || url.username || url.password) return null;
    return url.origin + url.pathname;
  } catch { return null; }
}
const page = z.string().max(2048).refine(s => loginPage(s) === s);
export const LoginForm = z.object({
  page, action: page, usernameField: z.string().min(1).max(200), passwordField: z.string().min(1).max(200),
}).strict();
export const LoginCredential = z.object({
  form: LoginForm, username: z.string().min(1).max(512), password: z.string().min(1).max(4096),
  // Some institutions split username and password across two SSO pages. The
  // exact page/action/field triplet for each step is remembered alongside the
  // final credential, so a password is never filled into an unrecognised page.
  steps: z.array(z.object({ page, action: page, field: z.string().min(1).max(200), kind: z.enum(['username', 'password']) }).strict()).max(4).optional(),
}).strict();
export type LoginCredential = z.infer<typeof LoginCredential>;
export const LoginOptions = z.object({ rememberPassword: z.boolean(), autoLogin: z.boolean() }).strict()
  .refine(s => !s.autoLogin || s.rememberPassword);
const RecordSchema = z.object({
  version: z.literal(1), rememberPassword: z.literal(true), autoLogin: z.boolean(), credential: LoginCredential.optional(),
}).strict();
export type LoginRecord = z.infer<typeof RecordSchema>;
export type LoginSummary = { rememberPassword: boolean; autoLogin: boolean; hasPassword: boolean; totpConfigured?: boolean };
export const defaultLoginSummary = (): LoginSummary => ({ rememberPassword: false, autoLogin: false, hasPassword: false });
/** Both remembered modes skip the launcher; only autoLogin permits submission. */
export function canRestoreLogin(requested: readonly Platform[], saved?: Partial<Record<Platform, LoginSummary>>) {
  return requested.length > 0 && requested.every(platform => saved?.[platform]?.rememberPassword && saved[platform]?.hasPassword);
}
export function loginSummary(record: LoginRecord | null, totp: TotpRecord | null = null): LoginSummary {
  const summary = record ? { rememberPassword: true, autoLogin: record.autoLogin, hasPassword: !!record.credential } : defaultLoginSummary();
  return totp ? { ...summary, totpConfigured: true } : summary;
}
export function matchesLoginForm(credential: LoginCredential, form: unknown): boolean {
  const parsed = LoginForm.safeParse(form);
  return parsed.success && (Object.keys(parsed.data) as Array<keyof typeof parsed.data>).every(k => parsed.data[k] === credential.form[k]);
}
function matchesLoginStep(credential: LoginCredential, form: unknown, kind: 'username' | 'password'): boolean {
  const parsed = z.object({ page, action: page, field: z.string().min(1).max(200), kind: z.enum(['username', 'password']) }).strict().safeParse(form);
  return parsed.success && parsed.data.kind === kind && !!credential.steps?.some(step => step.page === parsed.data.page && step.action === parsed.data.action && step.field === parsed.data.field && step.kind === kind);
}

/** Per-window-tree attempt. The Electron boundary separately verifies sender/frame. */
export class LoginAttempt {
  candidate?: LoginCredential;
  private filled = false;
  private filledOtp = new Set<string>();
  private filledSteps = new Set<string>();
  private pendingSteps: Partial<Record<'username' | 'password', { form: { page: string; action: string; field: string; kind: 'username' | 'password' }; value: string }>> = {};
  private automationStopped = false;
  constructor(public record: LoginRecord | null, public totp: TotpRecord | null = null) {}
  stopAutomation() { this.automationStopped = true; }
  cancel() { this.stopAutomation(); this.candidate = undefined; this.pendingSteps = {}; this.record = null; }
  updateOptions(options: z.infer<typeof LoginOptions>) {
    if (!options.rememberPassword) { this.cancel(); return; }
    if (!options.autoLogin) this.stopAutomation();
    this.record = { version: 1, rememberPassword: true, autoLogin: options.autoLogin, credential: this.record?.credential };
  }
  canSubmit(senderPage: string, form: unknown) {
    return !this.automationStopped && !!this.record?.autoLogin && !!this.record.credential &&
      loginPage(senderPage) === this.record.credential.form.page && matchesLoginForm(this.record.credential, form);
  }
  canSubmitStep(senderPage: string, form: unknown) {
    const parsed = z.object({ page, action: page, field: z.string().min(1).max(200), kind: z.enum(['username', 'password']) }).strict().safeParse(form);
    if (!parsed.success || !this.record?.autoLogin || this.automationStopped || !this.record.credential || loginPage(senderPage) !== parsed.data.page) return false;
    return matchesLoginStep(this.record.credential, parsed.data, parsed.data.kind) && this.filledSteps.has(stepKey(parsed.data));
  }
  capture(senderPage: string, input: unknown) {
    if (!this.record?.rememberPassword) return;
    const parsed = LoginCredential.safeParse(input);
    if (parsed.success && parsed.data.form.page === loginPage(senderPage)) this.candidate = parsed.data;
  }
  captureStep(senderPage: string, input: unknown) {
    if (!this.record?.rememberPassword) return;
    const parsed = z.object({ form: z.object({ page, action: page, field: z.string().min(1).max(200), kind: z.enum(['username', 'password']) }).strict(), value: z.string().min(1).max(4096) }).strict().safeParse(input);
    if (!parsed.success || parsed.data.form.page !== loginPage(senderPage)) return;
    this.pendingSteps[parsed.data.form.kind] = parsed.data;
    const prior = this.candidate?.steps ?? Object.values(this.pendingSteps).map(step => step!.form);
    const steps = [...prior.filter(step => step.kind !== parsed.data.form.kind), parsed.data.form];
    const username = this.pendingSteps.username?.value;
    const password = this.pendingSteps.password?.value;
    if (!username || !password) {
      this.candidate = undefined;
      return;
    }
    this.candidate = { form: { page: parsed.data.form.page, action: parsed.data.form.action, usernameField: steps.find(step => step.kind === 'username')?.field ?? 'username', passwordField: steps.find(step => step.kind === 'password')?.field ?? 'password' }, username, password, steps };
  }
  fill(senderPage: string, form: unknown) {
    const saved = this.record;
    if (this.automationStopped || !saved?.credential) return null;
    if (!this.filled && loginPage(senderPage) === saved.credential.form.page && matchesLoginForm(saved.credential, form)) {
      this.filled = true;
      return { username: saved.credential.username, password: saved.credential.password, autoLogin: saved.autoLogin };
    }
    const step = z.object({ page, action: page, field: z.string().min(1).max(200), kind: z.enum(['username', 'password']) }).strict().safeParse(form);
    if (!step.success || loginPage(senderPage) !== step.data.page || !matchesLoginStep(saved.credential, step.data, step.data.kind)) return null;
    const key = stepKey(step.data);
    if (this.filledSteps.has(key)) return null;
    this.filledSteps.add(key);
    return { step: step.data.kind, value: step.data.kind === 'username' ? saved.credential.username : saved.credential.password, autoLogin: saved.autoLogin };
  }
  canFillOtp(senderPage: string, form: unknown) {
    const parsed = OtpForm.safeParse(form);
    const record = this.record;
    if (!parsed.success || !this.totp || !record?.autoLogin || this.automationStopped || !record.credential) return false;
    // Keep the seed scoped to the origins already present in the verified
    // login form. This covers common cross-origin IdP/MFA hops without ever
    // allowing an arbitrary page to receive a code.
    const trusted = new Set([new URL(record.credential.form.page).origin, new URL(record.credential.form.action).origin]);
    return trusted.has(new URL(senderPage).origin) &&
      trusted.has(new URL(parsed.data.action).origin) &&
      !this.filledOtp.has(otpKey(parsed.data));
  }
  fillOtp(senderPage: string, form: unknown) {
    if (!this.canFillOtp(senderPage, form)) return null;
    const parsed = OtpForm.parse(form); this.filledOtp.add(otpKey(parsed));
    return { code: totpCode(this.totp!), autoLogin: true };
  }
  canSubmitOtp(senderPage: string, form: unknown) {
    const parsed = OtpForm.safeParse(form);
    return parsed.success && !!this.totp && !this.automationStopped && !!this.record?.autoLogin &&
      !!this.record.credential && new Set([new URL(this.record.credential.form.page).origin, new URL(this.record.credential.form.action).origin]).has(new URL(senderPage).origin) &&
      new Set([new URL(this.record.credential.form.page).origin, new URL(this.record.credential.form.action).origin]).has(new URL(parsed.data.action).origin) && this.filledOtp.has(otpKey(parsed.data));
  }
}

export const OtpForm = z.object({
  page, action: page, otpField: z.string().min(1).max(200),
}).strict();
export type OtpForm = z.infer<typeof OtpForm>;
const otpKey = (form: OtpForm) => `${form.page}\0${form.action}\0${form.otpField}`;
const stepKey = (form: { page: string; action: string; field: string; kind: string }) => `${form.kind}\0${form.page}\0${form.action}\0${form.field}`;

/** Only the authorization main process uses this store; no public tool returns it. */
export class LoginStore {
  constructor(private storage: Vault = vault) {}
  async read(p: Profile, platform: Platform): Promise<LoginRecord | null> {
    const saved = await this.storage.read(p, `login:${platform}`);
    return saved ? RecordSchema.parse(saved.value) : null;
  }
  async readTotp(p: Profile, platform: Platform): Promise<TotpRecord | null> {
    const saved = await this.storage.read(p, `totp:${platform}`);
    return saved ? TotpRecordSchema.parse(saved.value) : null;
  }
  async setOptions(p: Profile, platform: Platform, input: unknown) {
    const options = LoginOptions.parse(input);
    if (!options.rememberPassword) {
      await this.storage.remove(p, `login:${platform}`);
      await this.storage.remove(p, `totp:${platform}`);
      return defaultLoginSummary();
    }
    const record = await this.storage.update<LoginRecord>(p, `login:${platform}`, previous => ({
      version: 1, rememberPassword: true, autoLogin: options.autoLogin,
      ...(previous ? { credential: RecordSchema.parse(previous).credential } : {}),
    }));
    return loginSummary(record, await this.readTotp(p, platform));
  }
  async saveVerified(p: Profile, platform: Platform, input: unknown) {
    const credential = LoginCredential.parse(input);
    const saved = await this.storage.read<LoginRecord>(p, `login:${platform}`);
    if (!saved) return; // Consent withdrawn / logged out during authorization.
    const record = RecordSchema.parse(saved.value);
    await this.storage.write(p, `login:${platform}`, { ...record, credential }, saved.generation);
  }
  async setTotp(p: Profile, platform: Platform, input: string) {
    const parsed = TotpRecordSchema.parse({ version: 1, ...parseTotpSecret(input) });
    await this.storage.write(p, `totp:${platform}`, parsed);
    return parsed;
  }
  async clearTotp(p: Profile, platform: Platform) { await this.storage.remove(p, `totp:${platform}`); }
}
export const loginStore = new LoginStore();
