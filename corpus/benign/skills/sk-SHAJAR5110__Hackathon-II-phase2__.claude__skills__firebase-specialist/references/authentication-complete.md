# Firebase Authentication - Complete Guide

## Email & Password Authentication

### Setup and Registration

```typescript
// services/auth.service.ts
import {
  createUserWithEmailAndPassword,
  sendEmailVerification,
  signInWithEmailAndPassword,
  signOut,
  updateProfile,
  sendPasswordResetEmail,
  confirmPasswordReset,
  Auth,
  User,
} from 'firebase/auth';
import { doc, setDoc, Timestamp } from 'firebase/firestore';
import { auth, db } from './firebase.config';

interface UserProfile {
  uid: string;
  email: string;
  displayName: string;
  photoURL?: string;
  emailVerified: boolean;
  createdAt: Timestamp;
  role: 'customer' | 'vendor' | 'admin';
  metadata: {
    lastLogin?: Timestamp;
    loginCount: number;
  };
}

export const authService = {
  // Register new user
  async registerUser(
    email: string,
    password: string,
    displayName: string
  ): Promise<{ success: boolean; uid?: string; error?: string }> {
    try {
      // Create auth user
      const userCredential = await createUserWithEmailAndPassword(
        auth,
        email,
        password
      );
      const user = userCredential.user;

      // Update profile
      await updateProfile(user, { displayName });

      // Send verification email
      await sendEmailVerification(user, {
        url: `${window.location.origin}/verify-email?uid=${user.uid}`,
        handleCodeInApp: true,
      });

      // Create user profile document
      const userProfile: UserProfile = {
        uid: user.uid,
        email: user.email || '',
        displayName,
        emailVerified: false,
        createdAt: Timestamp.now(),
        role: 'customer',
        metadata: {
          loginCount: 0,
        },
      };

      await setDoc(doc(db, 'users', user.uid), userProfile);

      return { success: true, uid: user.uid };
    } catch (error) {
      const err = error as any;
      return {
        success: false,
        error: err.message || 'Registration failed',
      };
    }
  },

  // Login user
  async loginUser(
    email: string,
    password: string
  ): Promise<{ success: boolean; user?: User; error?: string }> {
    try {
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      const user = userCredential.user;

      // Update last login
      const userRef = doc(db, 'users', user.uid);
      await setDoc(
        userRef,
        {
          metadata: {
            lastLogin: Timestamp.now(),
            loginCount: increment(1),
          },
        },
        { merge: true }
      );

      return { success: true, user };
    } catch (error) {
      const err = error as any;
      return {
        success: false,
        error: err.message || 'Login failed',
      };
    }
  },

  // Logout user
  async logoutUser(): Promise<void> {
    try {
      await signOut(auth);
    } catch (error) {
      console.error('Logout error:', error);
      throw error;
    }
  },

  // Send password reset email
  async sendPasswordReset(email: string): Promise<void> {
    await sendPasswordResetEmail(auth, email, {
      url: `${window.location.origin}/reset-password`,
      handleCodeInApp: true,
    });
  },

  // Confirm password reset with code
  async resetPassword(code: string, newPassword: string): Promise<void> {
    await confirmPasswordReset(auth, code, newPassword);
  },

  // Verify email
  async verifyEmail(code: string): Promise<void> {
    const { applyActionCode } = await import('firebase/auth');
    await applyActionCode(auth, code);
  },

  // Get current user
  getCurrentUser(): User | null {
    return auth.currentUser;
  },

  // Get user ID token
  async getIdToken(): Promise<string> {
    const user = auth.currentUser;
    if (!user) throw new Error('User not authenticated');
    return user.getIdToken();
  },
};
```

## OAuth and Social Login

### Google, GitHub, Facebook OAuth

```typescript
// services/oauth.service.ts
import {
  signInWithPopup,
  signInWithRedirect,
  getRedirectResult,
  GoogleAuthProvider,
  GithubAuthProvider,
  FacebookAuthProvider,
  linkWithPopup,
} from 'firebase/auth';
import { auth, db } from './firebase.config';
import { doc, setDoc, getDoc } from 'firebase/firestore';

const googleProvider = new GoogleAuthProvider();
const githubProvider = new GithubAuthProvider();
const facebookProvider = new FacebookAuthProvider();

export const oauthService = {
  // Google Sign-In
  async signInWithGoogle() {
    try {
      const result = await signInWithPopup(auth, googleProvider);
      await this.createOrUpdateUserProfile(result.user);
      return { success: true, user: result.user };
    } catch (error) {
      const err = error as any;
      return {
        success: false,
        error: err.message || 'Google sign-in failed',
      };
    }
  },

  // GitHub Sign-In
  async signInWithGitHub() {
    try {
      const result = await signInWithPopup(auth, githubProvider);
      await this.createOrUpdateUserProfile(result.user);
      return { success: true, user: result.user };
    } catch (error) {
      const err = error as any;
      return {
        success: false,
        error: err.message || 'GitHub sign-in failed',
      };
    }
  },

  // Facebook Sign-In
  async signInWithFacebook() {
    try {
      const result = await signInWithPopup(auth, facebookProvider);
      await this.createOrUpdateUserProfile(result.user);
      return { success: true, user: result.user };
    } catch (error) {
      const err = error as any;
      return {
        success: false,
        error: err.message || 'Facebook sign-in failed',
      };
    }
  },

  // Link provider to existing account
  async linkProvider(provider: 'google' | 'github' | 'facebook') {
    const user = auth.currentUser;
    if (!user) throw new Error('User not authenticated');

    const providerInstance =
      provider === 'google'
        ? googleProvider
        : provider === 'github'
          ? githubProvider
          : facebookProvider;

    try {
      const result = await linkWithPopup(user, providerInstance);
      return { success: true, user: result.user };
    } catch (error) {
      const err = error as any;
      return {
        success: false,
        error: err.message || `Failed to link ${provider}`,
      };
    }
  },

  // Create or update user profile
  async createOrUpdateUserProfile(user: any) {
    const userRef = doc(db, 'users', user.uid);
    const userDoc = await getDoc(userRef);

    if (!userDoc.exists()) {
      // New user
      await setDoc(userRef, {
        uid: user.uid,
        email: user.email,
        displayName: user.displayName,
        photoURL: user.photoURL,
        emailVerified: user.emailVerified,
        createdAt: new Date(),
        role: 'customer',
        metadata: {
          lastLogin: new Date(),
          loginCount: 1,
        },
      });
    } else {
      // Existing user - update login info
      await setDoc(
        userRef,
        {
          displayName: user.displayName,
          photoURL: user.photoURL,
          emailVerified: user.emailVerified,
          metadata: {
            lastLogin: new Date(),
            loginCount: (userDoc.data()?.metadata?.loginCount || 0) + 1,
          },
        },
        { merge: true }
      );
    }
  },
};
```

## Multi-Factor Authentication (MFA)

### Phone-Based MFA

```typescript
// services/mfa.service.ts
import {
  multiFactor,
  PhoneAuthProvider,
  RecaptchaVerifier,
} from 'firebase/auth';
import { auth } from './firebase.config';

export const mfaService = {
  // Setup MFA
  async enrollPhoneMFA(phoneNumber: string, recaptchaContainerId: string) {
    try {
      const user = auth.currentUser;
      if (!user) throw new Error('User not authenticated');

      // Initialize reCAPTCHA
      const recaptchaVerifier = new RecaptchaVerifier(
        recaptchaContainerId,
        { size: 'invisible' },
        auth
      );

      // Send SMS code
      const phoneAuthProvider = new PhoneAuthProvider(auth);
      const verificationId = await phoneAuthProvider.verifyPhoneNumber(
        phoneNumber,
        recaptchaVerifier
      );

      return { success: true, verificationId };
    } catch (error) {
      const err = error as any;
      return {
        success: false,
        error: err.message || 'Failed to enroll MFA',
      };
    }
  },

  // Confirm MFA enrollment
  async confirmMFAEnrollment(
    displayName: string,
    verificationId: string,
    smsCode: string
  ) {
    try {
      const user = auth.currentUser;
      if (!user) throw new Error('User not authenticated');

      const phoneAuthProvider = new PhoneAuthProvider(auth);
      const phoneCredential = phoneAuthProvider.credential(
        verificationId,
        smsCode
      );

      const multiFactorAssertion = multiFactor.PhoneMultiFactorAssertion(
        phoneCredential
      );

      await multiFactor(user).enroll(multiFactorAssertion, displayName);

      return { success: true };
    } catch (error) {
      const err = error as any;
      return {
        success: false,
        error: err.message || 'MFA confirmation failed',
      };
    }
  },

  // Check if user has MFA enabled
  async isMFAEnabled(): Promise<boolean> {
    const user = auth.currentUser;
    if (!user) return false;
    return user.multiFactor.enrolledFactors.length > 0;
  },

  // List enrolled factors
  async getEnrolledFactors() {
    const user = auth.currentUser;
    if (!user) return [];
    return user.multiFactor.enrolledFactors;
  },

  // Unenroll MFA
  async unenrollMFA(factorUid: string) {
    try {
      const user = auth.currentUser;
      if (!user) throw new Error('User not authenticated');

      const enrolledFactor = user.multiFactor.enrolledFactors.find(
        (factor) => factor.uid === factorUid
      );

      if (!enrolledFactor) throw new Error('Factor not found');

      await multiFactor(user).unenroll(enrolledFactor);
      return { success: true };
    } catch (error) {
      const err = error as any;
      return {
        success: false,
        error: err.message || 'Failed to unenroll MFA',
      };
    }
  },
};
```

## Custom Claims & RBAC

### Role-Based Access Control

```typescript
// services/rbac.service.ts
import { auth, db } from './firebase.config';
import { httpsCallable } from 'firebase/functions';
import { functions } from './firebase.config';

interface UserRole {
  role: 'customer' | 'vendor' | 'moderator' | 'admin';
  permissions: string[];
  createdAt: Date;
}

export const rbacService = {
  // Set custom claims (Admin only - call from backend)
  async setCustomClaims(
    uid: string,
    claims: Record<string, any>
  ): Promise<void> {
    const setClaimsFunction = httpsCallable(functions, 'setCustomClaims');
    await setClaimsFunction({ uid, claims });
  },

  // Get custom claims
  async getCustomClaims(): Promise<Record<string, any> | undefined> {
    const user = auth.currentUser;
    if (!user) throw new Error('User not authenticated');

    const idTokenResult = await user.getIdTokenResult(true);
    return idTokenResult.claims;
  },

  // Check permission
  async hasPermission(permission: string): Promise<boolean> {
    const claims = await this.getCustomClaims();
    return claims?.permissions?.includes(permission) ?? false;
  },

  // Get user role
  async getUserRole(): Promise<string | null> {
    const claims = await this.getCustomClaims();
    return claims?.role ?? null;
  },

  // Check if admin
  async isAdmin(): Promise<boolean> {
    const role = await this.getUserRole();
    return role === 'admin';
  },

  // Refresh claims after update
  async refreshClaims(): Promise<void> {
    const user = auth.currentUser;
    if (!user) throw new Error('User not authenticated');
    await user.getIdTokenResult(true);
  },
};

// Backend Cloud Function to set claims
export const setCustomClaimsFunction = functions.https.onCall(
  async (data, context) => {
    // Verify caller is admin
    if (!context.auth) {
      throw new functions.https.HttpsError(
        'unauthenticated',
        'User must be authenticated'
      );
    }

    const uid = data.uid;
    const claims = data.claims;

    try {
      await admin.auth().setCustomUserClaims(uid, claims);

      // Update user document with role
      await db.collection('users').doc(uid).update({
        role: claims.role,
        permissions: claims.permissions,
        updatedAt: admin.firestore.FieldValue.serverTimestamp(),
      });

      return { success: true };
    } catch (error) {
      throw new functions.https.HttpsError(
        'internal',
        'Failed to set custom claims'
      );
    }
  }
);
```

## Session Management

### Persistent Sessions

```typescript
// services/session.service.ts
import {
  onAuthStateChanged,
  setPersistence,
  browserLocalPersistence,
  browserSessionPersistence,
  Unsubscribe,
} from 'firebase/auth';
import { auth, db } from './firebase.config';

interface SessionConfig {
  persistence: 'local' | 'session';
  rememberMe: boolean;
}

export const sessionService = {
  // Initialize session
  async initializeSession(config: SessionConfig): Promise<void> {
    const persistence =
      config.persistence === 'local'
        ? browserLocalPersistence
        : browserSessionPersistence;

    await setPersistence(auth, persistence);

    if (config.rememberMe) {
      localStorage.setItem('rememberMe', 'true');
    }
  },

  // Monitor auth state
  onAuthStateChanged(
    callback: (user: any | null) => void
  ): Unsubscribe {
    return onAuthStateChanged(auth, callback);
  },

  // Logout all devices
  async logoutAllDevices(): Promise<void> {
    const user = auth.currentUser;
    if (!user) throw new Error('User not authenticated');

    try {
      // Revoke all refresh tokens by changing password
      // Or use custom claim to invalidate sessions
      await db
        .collection('users')
        .doc(user.uid)
        .update({
          sessionVersion: new Date().getTime(),
        });

      await auth.signOut();
    } catch (error) {
      console.error('Failed to logout all devices:', error);
      throw error;
    }
  },

  // Check session validity
  async isSessionValid(): Promise<boolean> {
    const user = auth.currentUser;
    if (!user) return false;

    try {
      const idTokenResult = await user.getIdTokenResult();
      return !idTokenResult.issuedAtTime;
    } catch {
      return false;
    }
  },
};
```

## Token Management

### JWT Token Refresh

```typescript
// services/token.service.ts
export const tokenService = {
  // Get fresh ID token
  async getFreshIdToken(): Promise<string> {
    const user = auth.currentUser;
    if (!user) throw new Error('User not authenticated');

    // Force refresh
    const token = await user.getIdToken(true);
    return token;
  },

  // Store token
  storeToken(token: string): void {
    localStorage.setItem('idToken', token);
    localStorage.setItem('tokenExpiry', (Date.now() + 3600000).toString()); // 1 hour
  },

  // Get stored token
  getStoredToken(): string | null {
    return localStorage.getItem('idToken');
  },

  // Is token expired
  isTokenExpired(): boolean {
    const expiry = localStorage.getItem('tokenExpiry');
    if (!expiry) return true;
    return Date.now() > parseInt(expiry);
  },

  // Refresh token if needed
  async ensureValidToken(): Promise<string> {
    const user = auth.currentUser;
    if (!user) throw new Error('User not authenticated');

    if (this.isTokenExpired()) {
      const token = await user.getIdToken(true);
      this.storeToken(token);
      return token;
    }

    const stored = this.getStoredToken();
    return stored || (await user.getIdToken());
  },

  // Clear token
  clearToken(): void {
    localStorage.removeItem('idToken');
    localStorage.removeItem('tokenExpiry');
  },
};
```

## Account Linking & Merging

```typescript
// Link multiple auth providers
async function linkMultipleProviders(user: any) {
  const linkedProviders: string[] = [];

  for (const provider of user.providerData) {
    linkedProviders.push(provider.providerId);
  }

  // Update user document with linked providers
  await db.collection('users').doc(user.uid).update({
    linkedProviders,
    updatedAt: new Date(),
  });

  return linkedProviders;
}

// Merge anonymous account with Google account
async function mergeAnonymousAccount(googleCredential: any) {
  const anonUser = auth.currentUser;
  if (!anonUser?.isAnonymous) throw new Error('User is not anonymous');

  try {
    // Sign in with Google credential
    const result = await signInWithCredential(auth, googleCredential);

    // Copy anonymous user data to authenticated user
    const anonData = await db.collection('users').doc(anonUser.uid).get();
    if (anonData.exists()) {
      await db.collection('users').doc(result.user.uid).set(
        {
          ...anonData.data(),
          mergedFrom: anonUser.uid,
          mergedAt: new Date(),
        },
        { merge: true }
      );

      // Delete anonymous user document
      await db.collection('users').doc(anonUser.uid).delete();
    }

    return result.user;
  } catch (error) {
    console.error('Merge failed:', error);
    throw error;
  }
}
```