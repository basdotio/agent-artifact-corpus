// Helper functions that extract the handler logic from index.ts for testing

import {
  formatProfile,
  formatNote
} from '../note/note-tools.js';

import {
  NostrEvent,
  NostrFilter,
  KINDS,
  DEFAULT_RELAYS,
  QUERY_TIMEOUT,
  getFreshPool,
  npubToHex,
  formatPubkey
} from '../utils/index.js';

// Extracted handler for getProfile tool
export const getProfileHandler = async ({ pubkey, relays }) => {
  // Convert npub to hex if needed
  const hexPubkey = npubToHex(pubkey);
  if (!hexPubkey) {
    return {
      content: [
        {
          type: "text",
          text: "Invalid public key format. Please provide a valid hex pubkey or npub.",
        },
      ],
    };
  }
  
  // Generate a friendly display version of the pubkey
  const displayPubkey = formatPubkey(hexPubkey);
  
  const relaysToUse = relays || DEFAULT_RELAYS;
  // Create a fresh pool for this request
  const pool = getFreshPool();
  
  try {
    console.error(`Fetching profile for ${hexPubkey} from ${relaysToUse.join(", ")}`);
    
    // Create a timeout promise
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error("Timeout")), QUERY_TIMEOUT);
    });
    
    // Create a query promise for profile (kind 0)
    const profilePromise = pool.get(
      relaysToUse,
      {
        kinds: [KINDS.Metadata],
        authors: [hexPubkey],
      }
    );
    
    // Race the promises
    const profile = await Promise.race([profilePromise, timeoutPromise]);
    
    if (!profile) {
      return {
        content: [
          {
            type: "text",
            text: `No profile found for ${displayPubkey}`,
          },
        ],
      };
    }
    
    const formatted = formatProfile(profile);
    
    return {
      content: [
        {
          type: "text",
          text: `Profile for ${displayPubkey}:\n\n${formatted}`,
        },
      ],
    };
  } catch (error) {
    console.error("Error fetching profile:", error);
    
    return {
      content: [
        {
          type: "text",
          text: `Error fetching profile for ${displayPubkey}: ${error instanceof Error ? error.message : "Unknown error"}`,
        },
      ],
    };
  } finally {
    // Clean up any subscriptions and close the pool
    pool.close(relaysToUse);
  }
};

// Extracted handler for getKind1Notes tool
export const getKind1NotesHandler = async ({ pubkey, limit, relays }) => {
  // Convert npub to hex if needed
  const hexPubkey = npubToHex(pubkey);
  if (!hexPubkey) {
    return {
      content: [
        {
          type: "text",
          text: "Invalid public key format. Please provide a valid hex pubkey or npub.",
        },
      ],
    };
  }
  
  // Generate a friendly display version of the pubkey
  const displayPubkey = formatPubkey(hexPubkey);
  
  const relaysToUse = relays || DEFAULT_RELAYS;
  // Create a fresh pool for this request
  const pool = getFreshPool();
  
  try {
    console.error(`Fetching kind 1 notes for ${hexPubkey} from ${relaysToUse.join(", ")}`);
    
    // Use the querySync method with a timeout
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error("Timeout")), QUERY_TIMEOUT);
    });
    
    const notesPromise = pool.querySync(
      relaysToUse,
      {
        kinds: [KINDS.Text],
        authors: [hexPubkey],
        limit,
      }
    );
    
    const notes = await Promise.race([notesPromise, timeoutPromise]);
    
    if (!notes || notes.length === 0) {
      return {
        content: [
          {
            type: "text",
            text: `No notes found for ${displayPubkey}`,
          },
        ],
      };
    }
    
    // Sort notes by created_at in descending order (newest first)
    notes.sort((a, b) => b.created_at - a.created_at);
    
    const formattedNotes = notes.map(formatNote).join("\n");
    
    return {
      content: [
        {
          type: "text",
          text: `Found ${notes.length} notes from ${displayPubkey}:\n\n${formattedNotes}`,
        },
      ],
    };
  } catch (error) {
    console.error("Error fetching notes:", error);
    
    return {
      content: [
        {
          type: "text",
          text: `Error fetching notes for ${displayPubkey}: ${error instanceof Error ? error.message : "Unknown error"}`,
        },
      ],
    };
  } finally {
    // Clean up any subscriptions and close the pool
    pool.close(relaysToUse);
  }
};

// Extracted handler for getLongFormNotes tool
export const getLongFormNotesHandler = async ({ pubkey, limit, relays }) => {
  // Convert npub to hex if needed
  const hexPubkey = npubToHex(pubkey);
  if (!hexPubkey) {
    return {
      content: [
        {
          type: "text",
          text: "Invalid public key format. Please provide a valid hex pubkey or npub.",
        },
      ],
    };
  }
  
  // Generate a friendly display version of the pubkey
  const displayPubkey = formatPubkey(hexPubkey);
  
  const relaysToUse = relays || DEFAULT_RELAYS;
  // Create a fresh pool for this request
  const pool = getFreshPool();
  
  try {
    console.error(`Fetching long-form notes for ${hexPubkey} from ${relaysToUse.join(", ")}`);
    
    // Use the querySync method with a timeout
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error("Timeout")), QUERY_TIMEOUT);
    });
    
    const notesPromise = pool.querySync(
      relaysToUse,
      {
        kinds: [30023], // NIP-23 long-form content
        authors: [hexPubkey],
        limit,
      }
    );
    
    const notes = await Promise.race([notesPromise, timeoutPromise]);
    
    if (!notes || notes.length === 0) {
      return {
        content: [
          {
            type: "text",
            text: `No long-form notes found for ${displayPubkey}`,
          },
        ],
      };
    }
    
    // Return a simple mock result for testing - we'll test the full formatting elsewhere
    return {
      content: [
        {
          type: "text",
          text: `Found ${notes.length} long-form notes from ${displayPubkey}:\n\nMocked formatted notes here`,
        },
      ],
    };
  } catch (error) {
    console.error("Error fetching long-form notes:", error);
    
    return {
      content: [
        {
          type: "text",
          text: `Error fetching long-form notes for ${displayPubkey}: ${error instanceof Error ? error.message : "Unknown error"}`,
        },
      ],
    };
  } finally {
    // Clean up any subscriptions and close the pool
    pool.close(relaysToUse);
  }
};

// Default export for the module
export default {
  getProfileHandler,
  getKind1NotesHandler,
  getLongFormNotesHandler
}; 