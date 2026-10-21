/**
 * Graph API — Users (for owner lookup and reassignment)
 */
import type { User } from "../types.js";
import { useMockData, graphFetch } from "./client.js";
import { MOCK_USERS } from "../mock/users.js";

export async function searchUsers(query: string, incomingToken?: string): Promise<User[]> {
  if (useMockData()) {
    const q = query.toLowerCase();
    return MOCK_USERS.filter(
      (u) => u.displayName.toLowerCase().includes(q) || u.mail.toLowerCase().includes(q),
    );
  }

  const response = await graphFetch<{ value: User[] }>(
    `/users?$filter=startswith(displayName,'${encodeURIComponent(query)}')&$top=10&$select=id,displayName,mail,jobTitle,department`,
    incomingToken,
  );

  return response.value;
}

/** Preload licensed users for the people picker (top 50). */
export async function getAssignableUsers(incomingToken?: string): Promise<User[]> {
  if (useMockData()) {
    return MOCK_USERS;
  }

  try {
    const response = await graphFetch<{ value: User[] }>(
      `/users?$top=50&$select=id,displayName,mail,jobTitle,department&$filter=accountEnabled eq true`,
      incomingToken,
    );
    return response.value;
  } catch (e) {
    if (process.env.DEBUG === "true") console.log(`Could not preload assignable users: ${e}`);
    return [];
  }
}
