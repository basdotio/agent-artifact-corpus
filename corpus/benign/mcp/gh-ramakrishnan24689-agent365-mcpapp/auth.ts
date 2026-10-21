/**
 * Auth module — OBO token exchange for Microsoft Graph.
 * Exchanges the incoming Copilot bearer token for a Graph-scoped
 * access token using the On-Behalf-Of flow via MSAL Node.
 */
import { ConfidentialClientApplication } from "@azure/msal-node";

let msalClient: ConfidentialClientApplication | null = null;

function getMsalClient(): ConfidentialClientApplication {
  if (msalClient) return msalClient;

  const clientId = process.env.ENTRA_CLIENT_ID;
  const clientSecret = process.env.ENTRA_CLIENT_SECRET;
  const tenantId = process.env.ENTRA_TENANT_ID;

  if (!clientId || !clientSecret || !tenantId) {
    throw new Error(
      "Missing Entra ID configuration. Set ENTRA_CLIENT_ID, ENTRA_CLIENT_SECRET, and ENTRA_TENANT_ID environment variables.",
    );
  }

  msalClient = new ConfidentialClientApplication({
    auth: {
      clientId,
      clientSecret,
      authority: `https://login.microsoftonline.com/${tenantId}`,
    },
  });

  return msalClient;
}

/**
 * Exchange an incoming bearer token (scoped to this app) for a
 * Microsoft Graph access token using the OBO flow.
 */
export async function exchangeTokenForGraph(incomingToken: string): Promise<string> {
  const client = getMsalClient();

  const result = await client.acquireTokenOnBehalfOf({
    oboAssertion: incomingToken,
    scopes: ["https://graph.microsoft.com/.default"],
  });

  if (!result?.accessToken) {
    throw new Error("OBO token exchange failed — no access token returned");
  }

  return result.accessToken;
}
