// Profile and note utility functions

export interface NostrProfile {
  pubkey: string;
  displayName?: string;
  name?: string;
  picture?: string;
  about?: string;
  relays?: string[];
}

export interface NostrNote {
  id: string;
  pubkey: string;
  content: string;
  created_at: number;
  kind: number;
  tags: string[][];
}

/**
 * Get a user's profile data
 */
export async function getProfile(pubkey: string, relays?: string[]): Promise<NostrProfile> {
  return {
    pubkey,
    displayName: "Test User",
    name: "testuser",
    picture: "https://example.com/avatar.jpg",
    about: "This is a test profile",
    relays: relays || ["wss://relay.damus.io", "wss://relay.nostr.band"]
  };
}

/**
 * Get text notes (kind 1) by public key
 */
export async function getKind1Notes(pubkey: string, limit: number = 10, relays?: string[]): Promise<NostrNote[]> {
  const notes: NostrNote[] = [];
  
  for (let i = 0; i < limit; i++) {
    notes.push({
      id: `note${i}`,
      pubkey,
      content: `Test note ${i}`,
      created_at: Math.floor(Date.now() / 1000) - (i * 3600),
      kind: 1,
      tags: []
    });
  }
  
  return notes;
}

/**
 * Get long-form notes (kind 30023) by public key
 */
export async function getLongFormNotes(pubkey: string, limit: number = 10, relays?: string[]): Promise<NostrNote[]> {
  const notes: NostrNote[] = [];
  
  for (let i = 0; i < limit; i++) {
    notes.push({
      id: `longform${i}`,
      pubkey,
      content: `# Long Form Test ${i}\n\nThis is a test long-form note ${i}`,
      created_at: Math.floor(Date.now() / 1000) - (i * 86400),
      kind: 30023,
      tags: [
        ["d", `article${i}`],
        ["title", `Long Form Test ${i}`]
      ]
    });
  }
  
  return notes;
} 