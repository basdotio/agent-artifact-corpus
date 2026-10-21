declare module '@google-cloud/local-auth' {
  interface AuthOptions {
    keyfilePath: string;
    scopes: string[];
  }

  interface Credentials {
    access_token: string;
    refresh_token: string;
    scope: string;
    token_type: string;
    expiry_date: number;
  }

  interface Auth {
    credentials: Credentials;
  }

  export function authenticate(options: AuthOptions): Promise<Auth>;
} 