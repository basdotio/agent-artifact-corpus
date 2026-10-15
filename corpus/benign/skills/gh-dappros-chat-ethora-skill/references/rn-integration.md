# React Native integration — `@ethora/chat-component-rn` (Expo & bare RN)

Package: https://www.npmjs.com/package/@ethora/chat-component-rn · repo: https://github.com/dappros/ethora-chat-component-rn
Requirements: react >= 18, react-native >= 0.73 (tested on Expo SDK 53–57, New Architecture on).

> **Expo Go cannot run this SDK.** It has native modules (reanimated/worklets, keyboard-controller, media…), and Expo Go ships its own fixed native versions. Typical symptom: `[Worklets] Mismatch between JavaScript code version and Worklets Babel plugin version`. Tell the user up front that they need a development build (`npx expo run:ios|android`). The first build takes ~5–10 min; after that `npx expo start --dev-client` is enough.

## 1. Install — order matters

npm 7+ auto-installs peer dependencies. The SDK declares many optional peers (livekit, callkeep, mmkv…), and `npm install @ethora/chat-component-rn` on a fresh Expo app fails with `ERESOLVE` (e.g. `react-dom@19.x` vs the app's `react`). It can also leave **newer** native packages (e.g. `react-native-worklets`) than the Expo SDK supports. So install the peers first with `expo install`, then add the SDK without peer auto-install:

```bash
# 1) required native peers — expo install picks the versions that match the Expo SDK (works in bare RN too)
npx expo install react-native-reanimated react-native-worklets react-native-gesture-handler react-native-svg \
  @react-native-async-storage/async-storage @react-native-community/netinfo react-native-get-random-values \
  react-native-safe-area-context
# 2) media features (optional peers, but every real app wants them). expo-asset is a required peer of expo-audio.
npx expo install expo-audio expo-asset expo-video expo-clipboard expo-document-picker expo-image-manipulator \
  expo-image-picker expo-media-library expo-file-system expo-font expo-secure-store expo-blur expo-haptics
# 3) the SDK itself, without npm's peer auto-install
npm view @ethora/chat-component-rn dist-tags --json   # current stable = `latest`
npm install @ethora/chat-component-rn@latest --legacy-peer-deps
# optional: faster encrypted cache
npx expo install react-native-mmkv
```

- `react-native-worklets` is only for Reanimated 4+ (Expo SDK 54+). Skip it on Reanimated 3.
- If later `npx expo install …` also fails with `ERESOLVE`, add `legacy-peer-deps=true` to the project's `.npmrc` (npm only; yarn/pnpm/bun are unaffected). Tell the user why.
- Finish with `npx expo-doctor` and `npx expo install --check`. Both must be clean.

Bare RN without Expo modules: `npx install-expo-modules@latest` first, or skip the `expo-*` list (pickers/playback then no-op).

**Native build and a clean bundler cache** after installing peers:
- Expo: `npx expo run:ios` / `run:android` (runs prebuild + pods). Expo Go does **not** work.
- Bare: `cd ios && pod install && cd ..`, then `npx react-native run-ios` / `run-android`.
- **Restart Metro with a cleared cache:** `npx expo start --dev-client -c` (bare: `npx react-native start --reset-cache`). A Metro that was already running during the install keeps transforms made with the old worklets Babel plugin, and the app shows the same Worklets mismatch error even in a correct dev build. If a dev server is already running (`expo run` then prints "Skipping dev server"), stop it first.

Entry: import `react-native-gesture-handler` first in the app entry (`app/_layout.tsx` / `index.js`) and wrap the root in `<GestureHandlerRootView style={{ flex: 1 }}>`. `babel-preset-expo` adds the reanimated/worklets Babel plugin automatically, so no `babel.config.js` change is needed on Expo.

## 2. Screen

Template: `assets/templates/rn/EthoraChatScreen.tsx` (+ `ethora.config.ts`). The project is JavaScript? Convert the template to `.js` (drop the types) instead of adding TypeScript.

- **Expo Router**: `app/chat.tsx` or `app/(tabs)/chat.tsx` (under `src/app/` if the project uses it). On Expo SDK 56+ app code **must not import from `@react-navigation/*`** (bundler error "expo-router is no longer compatible with react-navigation"): use `useIsFocused` from `expo-router`, other helpers from `expo-router/react-navigation`.
- **React Navigation**: `<Stack.Screen name="Chat" component={EthoraChatScreen} />`. For a tab that stays mounted while hidden pass `isVisible={useIsFocused()}` so unread counts stay right.
- Use `SafeAreaView` from `react-native-safe-area-context` (the `react-native` one is deprecated). If a tab/stack header is shown above it, use `edges={['top']}` or hide that header (the chat has its own).

**Do not wrap `<Chat>` in your own `XmppProvider`.** `<Chat>` already mounts the SDK's redux `Provider` and an `XmppProvider` inside it (26.4.x and 26.9.x). Since 26.9.x `XmppProvider` also renders the video-call overlay, which reads the redux store. An outer `XmppProvider` sits outside that store and crashes the screen: `could not find react-redux context value; please ensure the component is wrapped in a <Provider>` (component stack: `VideoCallOverlay` → `XmppProvider`). This differs from the web SDK, where the outer provider is required. Unread badges outside the chat screen (an outer provider at the app root) are not supported this way in RN 26.9.x. If the user needs them, say so and check the package changelog for a fix.

## 3. Config (note the RN differences)

```ts
const config = {
  appId: ETHORA.appId,
  customAppToken: ETHORA.appToken,           // "JWT eyJ…" with the JWT prefix
  baseUrl: 'https://api.chat.ethora.com',    // API root; legacy ".../v1" accepted
  xmppSettings: {
    devServer: 'xmpp.chat.ethora.com',       // RN: BARE HOST — the SDK builds wss://<host>/ws itself
    host: 'xmpp.chat.ethora.com',
    conference: 'conference.xmpp.chat.ethora.com',
  },
  initBeforeLoad: true,
  newArch: true,
  refreshTokens: { enabled: true },
  jwtLogin: { enabled: true, token: clientJwt },   // or userLogin / customLogin — see auth-modes.md
};
```

Other RN-specific knobs (full reference: `README.md` in the package): `dark: true | 'system'` + `darkColors`, `logout: { enabled: true, onAfterLogout }` (built-in Sign out item), `settings.{languages,changePassword}`, `reactions`, `e2ee`, `enableAudio`, `keyboardStickyInput` / `disableKeyboardAvoidingView` / `inputDockPaddingBottom` (when the host already handles the keyboard or a tab bar), `disableConnectionErrorOverlay`.

## 4. Env

- **Expo**: `.env` with `EXPO_PUBLIC_ETHORA_*` (write-env `--target expo`). For the token endpoint, a fixed `EXPO_PUBLIC_ETHORA_TOKEN_ENDPOINT` breaks on devices because `localhost` is the phone. Best: if the app already has an API base URL helper, build the endpoint from it (`${API_URL}/api/ethora/token`). Otherwise derive the dev host from `Constants.expoConfig?.hostUri` (the Metro host's LAN IP), or use a tunnel.
- **Bare RN**: `src/ethora.config.ts` with literals (write-env `--target rn`), or `react-native-config` if the project already uses it.
- Never put `ETHORA_APP_SECRET` in the app.

## 5. Auth on mobile

Same model as web: the backend signs a client JWT for the signed-in user → `jwtLogin`. The screen template fetches it from `ETHORA.tokenEndpoint` and sends the app's session as `Authorization: Bearer <sessionToken>`. Pass the session token in from the app's auth context. **This needs a backend change**: settle it with the user first (SKILL.md §7).

Frontend-only (no backend, or the backend belongs to another team), options in the order to offer them:
1. **Dev token while the backend is pending**: `node scripts/client-jwt.mjs --user-id dev-user-1 --expires 7d` → `write-env.mjs --target expo --dev-jwt <token>` → `EXPO_PUBLIC_ETHORA_DEV_CLIENT_JWT`. Every app user is the same chat user, and the token expires. Dev only. Pair it with the backend handoff doc (`assets/templates/backend/BACKEND_HANDOFF.md`).
2. **Ethora's own login inside the chat**: no `jwtLogin`, keep `appId` + `customAppToken`. The chat shows its login/registration screen, and chat accounts are separate from the app's accounts (a second login). Works with zero backend.
3. **`customLogin` with a test account** (`POST /v1/users/login-with-email` with `appId`, sign up via `/v2/users/sign-up-with-email` on first use): dev only, because the password lives in the app.

Logout: when the app signs out, call `await logoutService.performLogout()` (works outside React, safe to import in an auth context) or `await useLogout()()` **before** clearing your own session. It also wipes the SDK cache and releases push registrations. Otherwise the next user can see the previous user's chats.

## 6. Push (optional)

The SDK does not mint tokens. Get one with `expo-notifications` or `@react-native-firebase/messaging` and either return it from `config.pushNotifications.getPushTokens` or call `registerPushToken(token)`; hand tapped notifications to `handlePushPayload(data)`. Sender keys (APNs .p8 / Firebase service account) are uploaded in the admin panel → app → Settings → Push.

## 7. Checklist

1. `node scripts/verify-setup.mjs --user-id <id> --email <email>` passes.
2. `npx expo-doctor` is clean; no `@react-navigation/*` imports in app code on Expo Router SDK 56+.
3. Native build runs on a simulator/device (not Expo Go), with Metro started using `-c` after the install.
4. The chat screen shows the room list and sends a message.
5. Metro logs show one XMPP connection; no "two copies of React" error (don't add `react`/`react-native` as dependencies of a library).
