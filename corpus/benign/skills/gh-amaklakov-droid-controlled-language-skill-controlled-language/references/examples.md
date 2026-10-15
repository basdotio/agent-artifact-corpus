# Calibration examples

These examples show the difference between the levels. Use them to calibrate
your output. Do not copy their wording into other documents.

## Example 1: a procedure

**Original**

<!-- controlled-language: off -->
> Before you get started, it's important to make sure that you've backed up
> your wallet, since the upgrade process may potentially result in loss of
> data if something goes wrong. Once you've done that, simply navigate to the
> Settings page, click on the Advanced tab and hit Upgrade - the app will then
> begin downloading the new version and will automatically restart once it's
> finished.
<!-- controlled-language: on -->

Problems:

- The safety information is in the middle of a long sentence (SF1, SF2).
- "May potentially" does not show if the risk is real (V5).
- "Since" and "once" have two meanings (W1).
- "Backed up" and "hit" are a phrasal verb and slang (V3, W3).
- "Simply" and "navigate to" are not simple words (W2).
- One sentence has three instructions (P2).
- "Downloading" is an "-ing" form (W6), and "you've backed up" is a perfect
  tense (V2).

**Level 1 — Light**

<!-- controlled-language: level 1 -->
> WARNING: Back up your wallet before you upgrade. If the upgrade fails, you
> can lose data.
>
> 1. Open the **Settings** page.
> 2. Click the **Advanced** tab, then click **Upgrade**.
>
> The app downloads the new version and then restarts automatically.

Level 1 accepts "back up" (V3 is only "prefer") and two related actions in
one step (P2 is only "prefer").

**Level 2 — Standard**

<!-- controlled-language: level 2 -->
> WARNING: Make a backup of your wallet before you upgrade the app. If the
> upgrade fails, you can lose the data in your wallet.
>
> 1. Open the **Settings** page.
> 2. Click the **Advanced** tab.
> 3. Click **Upgrade**.
>    The app downloads the new version. Then the app restarts automatically.

**Level 3 — Strict**

> WARNING: Make a backup copy of your wallet before you start the upgrade. If
> an error occurs during the upgrade, you can lose the data in your wallet.
>
> 1. Open the **Settings** page.
> 2. Click the **Advanced** tab.
> 3. Click **Upgrade**.
>    The application downloads the new version. Then the application starts
>    again automatically.

Notes for Level 3: technical nouns are "wallet", "backup copy", "upgrade",
"application", "Settings page", "Advanced tab". Technical verbs are "click"
and "download". "Fails" became "an error occurs" because the writer was not
sure that "fail" is approved.

## Example 2: a description

**Original**

<!-- controlled-language: off -->
> Two-factor authentication (2FA) is an additional security layer that
> ensures that only you can access your account. Once enabled, you'll be
> required to enter a verification code that is displayed in your
> authenticator app each time you're logging in from a new device. This
> allows us to verify your identity even if your password has been
> compromised.
<!-- controlled-language: on -->

**Level 1 — Light**

<!-- controlled-language: level 1 -->
> Two-factor authentication (2FA) adds a second security check to your
> account. After you enable 2FA, you enter a code from your authenticator app
> each time you sign in on a new device. This protects your account even if
> someone steals your password.

**Level 2 — Standard**

<!-- controlled-language: level 2 -->
> Two-factor authentication (2FA) gives your account a second level of
> protection. With 2FA, a person needs your password and your phone to sign
> in.
>
> When 2FA is on, the sign-in page asks for a verification code. Your
> authenticator app shows this code. The page asks for the code each time
> you sign in on a new device. As a result, a person who knows your password
> cannot sign in without your phone.

**Level 3 — Strict**

> Two-factor authentication (2FA) gives your account a second level of
> protection. With 2FA, a person must have your password and your phone to
> sign in.
>
> When 2FA is on, the sign-in page shows a field for a verification code.
> Your authenticator app shows this code. Type the code each time you sign
> in on a new device. If another person knows your password, that person
> cannot sign in to your account without your phone.
>
> Words to verify: "protection".

"Ensure", "allow", "require", "display", and "verify" are gone at Level 3
(W5). The writer was not sure that "protection" is approved, so the word is
in the "Words to verify" list (W5, step 3).

## Example 3: text in Russian (universal and Russian rules, Level 2)

**Original**

<!-- controlled-language: off -->
> Для осуществления подключения к серверу базы данных необходимо произвести
> настройку параметров подключения, после чего, нажав кнопку «Проверить»,
> убедиться в том, что соединение было успешно установлено.
<!-- controlled-language: on -->

**Result**

> Настройте подключение к серверу базы данных:
>
> 1. Введите параметры подключения.
> 2. Нажмите **Проверить**.
> 3. Убедитесь, что соединение установлено.

Changes: nouns made from verbs became verbs (V4, RU2), the
adverbial-participle clause became a separate step (P2, RU6), and one long
sentence became a list (S4). The ASD-STE100 vocabulary rules do not apply to
Russian.

## Example 4: a review report (Level 2)

**Input** (lines 10–12 of `docs/install.md`)

<!-- controlled-language: off -->
> 10 The installer should be run as an administrator, and you'll need to
> 11 set up the license key before starting the service; otherwise it
> 12 won't work properly.
<!-- controlled-language: on -->

**Report**

> ## Controlled language review: Level 2, English (source: default)
>
> 1 sentence checked: 5 violations, 0 warnings, 1 suggestion.
>
> | # | Line | Rule | Problem | Fix |
> | --- | --- | --- | --- | --- |
> | 1 | 10 | V5 | "should" does not show if the action is necessary. | Use an imperative. |
> | 2 | 10 | V1 | Passive voice in an instruction: "should be run". | "Run the installer as an administrator." |
> | 3 | 11 | V3 | Phrasal verb "set up". | "Add the license key." |
> | 4 | 11 | S5 | Semicolon. | Make separate sentences. |
> | 5 | 12 | W7 | "properly" is vague. | Say what does not work: "the service does not start". |
> | 6 | 11 | W6 | "-ing" form: "before starting" (suggestion at Level 2). | "before you start". |
>
> Suggested text:
>
> 1. Run the installer as an administrator.
> 2. Add the license key.
> 3. Start the service.
>
> If you do not add the license key, the service does not start.
>
> Meaning check: the original does not say what "won't work" means. I
> assumed that the service does not start. Please confirm.
