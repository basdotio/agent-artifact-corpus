# Fix templates

Templates are starting points. Adapt to the project framework. Replace every bracketed placeholder. Have a lawyer review the final text.

## 1. Neutral age gate (HTML + JS)

```html
<label for="birth-year">Year of birth</label>
<select id="birth-year" name="birth_year" required></select>
<script>
  const sel = document.getElementById('birth-year');
  const y = new Date().getFullYear();
  for (let i = y; i >= y - 110; i--) sel.add(new Option(i, i));
  document.querySelector('form').addEventListener('submit', (e) => {
    const age = y - Number(sel.value);
    if (!sel.value || age < 13 || sessionStorage.getItem('age_blocked')) {
      e.preventDefault();
      sessionStorage.setItem('age_blocked', '1');
      alert('Sorry. We cannot create an account for you.');
    }
  });
</script>
```

Server side: validate the age again. Do not store the birth date unless needed. Store only an over-13 boolean.

## 2. Self-host fonts

Next.js: `import { Inter } from 'next/font/google'` (downloads at build time and serves from your domain).
Other stacks: `npm i @fontsource/inter` then `import '@fontsource/inter/400.css'`.
Remove these lines:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter&display=swap" rel="stylesheet">
```

## 3. Consent-gated analytics loader

```js
function loadReplay() {
  if (navigator.globalPrivacyControl) return;
  if (localStorage.getItem('analytics_consent') !== 'granted') return;
  const s = document.createElement('script');
  s.src = '[VENDOR_SCRIPT_URL]';
  s.async = true;
  document.head.appendChild(s);
}
window.addEventListener('consent-granted', loadReplay);
```

Mask inputs in the vendor config (for example `maskAllInputs: true`). Disable recording on payment and password pages.

## 4. Email footer

```html
<p style="font-size:12px;color:#666">
  You are receiving this because you signed up at [SITE_NAME].<br>
  [COMPANY_LEGAL_NAME] · [POSTAL_ADDRESS]<br>
  <a href="{{unsubscribe_url}}">Unsubscribe</a>
</p>
```

Headers:
```
List-Unsubscribe: <https://[DOMAIN]/unsubscribe?token={{token}}>, <mailto:unsubscribe@[DOMAIN]>
List-Unsubscribe-Post: List-Unsubscribe=One-Click
```

Honour every opt-out within 10 business days and never sell or transfer the address.

## 5. Renewal disclosure next to the pay button

```html
<p class="renewal-terms">
  [PLAN_NAME]: $[PRICE] per [month|year]. Your subscription renews automatically every [period] at $[PRICE] until you cancel.
  [If trial: Your free trial ends on [DATE]. You will be charged $[PRICE] unless you cancel before then.]
  Cancel any time online at Account > Billing.
</p>
<label><input type="checkbox" required> I agree to the automatic renewal terms above.</label>
<button type="submit">Start subscription</button>
```

Also provide: an online cancel button, a confirmation email that restates the terms and cancellation method and an annual reminder for annual plans.

## 6. DMCA policy page outline

- Title: Copyright and DMCA Policy
- How to send a notice of claimed infringement (the six elements in 17 U.S.C. 512(c)(3)(A))
- Designated agent: [NAME or ROLE] · [ADDRESS] · [EMAIL] · [PHONE]
- Counter-notice process (17 U.S.C. 512(g))
- Repeat-infringer policy: accounts are terminated in appropriate circumstances
- Link to this page from the footer and from every upload form

Register the same agent details at https://dmca.copyright.gov ($6 per designation. Renew every three years).

## 7. Clickwrap acceptance with a log

```html
<label><input type="checkbox" name="terms" required>
  I agree to the <a href="/terms">Terms of Service</a> and the <a href="/privacy">Privacy Policy</a>.</label>
```

```js
// server: store proof of assent
await db.consents.insert({
  user_id, purpose: 'terms_and_privacy', granted: true,
  notice_version: '2026-10-01', consented_at: new Date().toISOString(), ip_hash
});
```

## 8. DPDP consent record and withdrawal

- One row per purpose with notice version and timestamp. Never pre-tick the box.
- Withdrawal must be as easy as giving consent. Add a settings toggle that writes granted=false and stops the related processing.

## 9. Breach response skeleton (DPDP Rule 7)

1. Contain and record the facts (nature and extent and time and location).
2. Tell each affected person without delay in plain language (what happened and likely consequences and what you did and what they can do and your contact).
3. Tell the Data Protection Board without delay.
4. File the detailed report with the Board within 72 hours (causes and findings and measures and a summary of the person notices).
5. Keep logs for at least one year (Rule 6 and Rule 8(3)).

## 10. Retention and erasure job (DPDP Rule 8)

```js
// nightly: warn 48 hours before purge then delete
const cutoff = daysAgo(RETENTION_DAYS);
const warn = await users.inactiveSince(daysAgo(RETENTION_DAYS - 2));
for (const u of warn) await sendErasureNotice(u);   // at least 48 hours notice
await users.purgeInactiveBefore(cutoff, { keepLogsForDays: 365 }); // keep processing logs 1 year
```

Cascade the deletion to processors and backups on your schedule.

## 11. Contact and grievance block

[DPO or privacy contact name] · [email] · [postal address]. Grievance response time: not more than [N] days (maximum 90). Link to the complaint form and to the Data Protection Board complaint route.
