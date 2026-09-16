# Firebase Realtime Database - Patterns & Implementation

## Real-Time Listeners

```typescript
// Realtime Database structure for chat/messaging
interface Message {
  id: string;
  userId: string;
  text: string;
  timestamp: number;
  edited?: boolean;
  reactions?: Record<string, string[]>;
}

interface Conversation {
  id: string;
  participants: string[];
  lastMessage: string;
  lastMessageTime: number;
  unreadCount: Record<string, number>;
}

interface UserPresence {
  userId: string;
  status: 'online' | 'away' | 'offline';
  lastSeen: number;
}

// Service for Realtime DB operations
import { getDatabase, ref, onValue, set, update, push } from 'firebase/database';

const db = getDatabase();

export const realtimeService = {
  // Listen to messages in real-time
  subscribeToMessages(
    conversationId: string,
    callback: (messages: Message[]) => void
  ) {
    const messagesRef = ref(db, `conversations/${conversationId}/messages`);

    const unsubscribe = onValue(messagesRef, (snapshot) => {
      const messages: Message[] = [];

      snapshot.forEach((childSnapshot) => {
        messages.push({
          id: childSnapshot.key || '',
          ...childSnapshot.val(),
        });
      });

      // Sort by timestamp
      messages.sort((a, b) => a.timestamp - b.timestamp);
      callback(messages);
    });

    return unsubscribe;
  },

  // Send message
  async sendMessage(
    conversationId: string,
    userId: string,
    text: string
  ): Promise<string> {
    const messagesRef = ref(
      db,
      `conversations/${conversationId}/messages`
    );
    const newMessageRef = push(messagesRef);

    const message: Message = {
      id: newMessageRef.key || '',
      userId,
      text,
      timestamp: Date.now(),
    };

    await set(newMessageRef, message);

    // Update conversation last message
    await update(
      ref(db, `conversations/${conversationId}`),
      {
        lastMessage: text,
        lastMessageTime: Date.now(),
      }
    );

    return message.id;
  },

  // Listen to user presence
  subscribeToPresence(
    userId: string,
    callback: (presence: UserPresence | null) => void
  ) {
    const presenceRef = ref(db, `presence/${userId}`);

    return onValue(presenceRef, (snapshot) => {
      if (snapshot.exists()) {
        callback(snapshot.val() as UserPresence);
      } else {
        callback(null);
      }
    });
  },

  // Set user online
  async setUserOnline(userId: string): Promise<void> {
    const presenceRef = ref(db, `presence/${userId}`);

    await set(presenceRef, {
      userId,
      status: 'online',
      lastSeen: Date.now(),
    });

    // Handle disconnect
    const connectedRef = ref(db, '.info/connected');
    onValue(connectedRef, async (snapshot) => {
      if (!snapshot.val()) {
        await set(presenceRef, {
          status: 'offline',
          lastSeen: Date.now(),
        });
      }
    });
  },

  // Listen to typing indicator
  subscribeToTyping(
    conversationId: string,
    callback: (typingUsers: Record<string, number>) => void
  ) {
    const typingRef = ref(
      db,
      `conversations/${conversationId}/typing`
    );

    return onValue(typingRef, (snapshot) => {
      const typingUsers = snapshot.val() || {};
      
      // Remove old typing indicators (older than 5 seconds)
      Object.keys(typingUsers).forEach((userId) => {
        if (Date.now() - typingUsers[userId] > 5000) {
          delete typingUsers[userId];
        }
      });

      callback(typingUsers);
    });
  },

  // Set typing indicator
  async setTyping(
    conversationId: string,
    userId: string
  ): Promise<void> {
    const typingRef = ref(
      db,
      `conversations/${conversationId}/typing/${userId}`
    );
    await set(typingRef, Date.now());

    // Auto-remove after 5 seconds
    setTimeout(async () => {
      const { remove } = await import('firebase/database');
      await remove(typingRef);
    }, 5000);
  },
};
```

## Presence & Activity Tracking

```typescript
// Complete presence tracking system
export const presenceService = {
  // Initialize presence on app load
  async initializePresence(userId: string) {
    const presenceRef = ref(db, `presence/${userId}`);
    const connectedRef = ref(db, '.info/connected');

    return onValue(connectedRef, async (snapshot) => {
      if (snapshot.val()) {
        // User is connected
        await set(presenceRef, {
          userId,
          status: 'online',
          lastSeen: Date.now(),
          device: navigator.userAgent,
        });

        // Set disconnect handler
        const { onDisconnect } = await import('firebase/database');
        const disconnectRef = ref(db, `presence/${userId}`);

        onDisconnect(disconnectRef).set({
          status: 'offline',
          lastSeen: Date.now(),
        });
      }
    });
  },

  // Get all active users
  async getActiveUsers(): Promise<
    Record<string, UserPresence>
  > {
    const presenceRef = ref(db, 'presence');
    const snapshot = await get(presenceRef);

    return snapshot.val() || {};
  },

  // Get online friends
  async getOnlineFriends(
    userId: string
  ): Promise<UserPresence[]> {
    const userRef = ref(db, `users/${userId}/friends`);
    const friendsSnapshot = await get(userRef);

    const friends: UserPresence[] = [];

    for (const friendId of Object.keys(friendsSnapshot.val() || {})) {
      const presenceRef = ref(db, `presence/${friendId}`);
      const presenceSnapshot = await get(presenceRef);

      if (
        presenceSnapshot.exists() &&
        presenceSnapshot.val().status === 'online'
      ) {
        friends.push(presenceSnapshot.val());
      }
    }

    return friends;
  },

  // Sync activity log
  async logActivity(
    userId: string,
    action: string,
    metadata?: Record<string, any>
  ) {
    const activityRef = ref(db, `activity_logs/${userId}`);
    const newActivityRef = push(activityRef);

    await set(newActivityRef, {
      action,
      timestamp: Date.now(),
      metadata,
    });
  },
};
```

## Data Synchronization Patterns

```typescript
// Offline sync and conflict resolution
export const syncService = {
  // Sync local changes when online
  async syncQueuedUpdates(userId: string) {
    const queue = localStorage.getItem(`sync_queue_${userId}`);
    if (!queue) return;

    const updates = JSON.parse(queue);

    try {
      for (const update of updates) {
        const updateRef = ref(db, update.path);
        await set(updateRef, update.data);
      }

      // Clear queue after successful sync
      localStorage.removeItem(`sync_queue_${userId}`);
    } catch (error) {
      console.error('Sync failed:', error);
    }
  },

  // Queue update for offline sync
  async queueUpdate(
    userId: string,
    path: string,
    data: any
  ) {
    const queueKey = `sync_queue_${userId}`;
    const existingQueue = JSON.parse(
      localStorage.getItem(queueKey) || '[]'
    );

    existingQueue.push({
      path,
      data,
      timestamp: Date.now(),
    });

    localStorage.setItem(queueKey, JSON.stringify(existingQueue));

    // Try to sync if online
    if (navigator.onLine) {
      await this.syncQueuedUpdates(userId);
    }
  },

  // Conflict resolution
  async resolveConflict(
    path: string,
    localData: any,
    remoteData: any,
    strategy: 'local' | 'remote' | 'merge' = 'merge'
  ) {
    const ref_path = ref(db, path);

    switch (strategy) {
      case 'local':
        await set(ref_path, localData);
        break;
      case 'remote':
        // Keep remote, don't update
        break;
      case 'merge':
        const merged = { ...remoteData, ...localData };
        await set(ref_path, merged);
        break;
    }
  },
};
```

## Real-Time Analytics Dashboard

```typescript
// Real-time analytics using Realtime DB
export const analyticsService = {
  // Track page view
  async trackPageView(userId: string, page: string) {
    const analyticsRef = ref(db, `analytics/page_views/${page}`);

    await update(analyticsRef, {
      count: increment(1),
      lastViewed: Date.now(),
    });

    // Track per user
    const userAnalyticsRef = ref(
      db,
      `user_analytics/${userId}/pages/${page}`
    );
    await update(userAnalyticsRef, {
      viewCount: increment(1),
      lastViewed: Date.now(),
    });
  },

  // Listen to live page views
  subscribeToPageViewStats(page: string, callback: any) {
    const statsRef = ref(db, `analytics/page_views/${page}`);

    return onValue(statsRef, (snapshot) => {
      callback(snapshot.val());
    });
  },

  // Real-time user count
  async trackActiveUsers() {
    const activeRef = ref(db, 'analytics/active_users');

    // Increment on load
    await update(activeRef, { count: increment(1) });

    // Decrement on unload
    window.addEventListener('beforeunload', async () => {
      await update(activeRef, { count: increment(-1) });
    });
  },

  // Subscribe to live statistics
  subscribeToLiveStats(callback: any) {
    const statsRef = ref(db, 'analytics/live_stats');

    return onValue(statsRef, (snapshot) => {
      callback(snapshot.val());
    });
  },
};

// Realtime DB rules for analytics
const rulesForAnalytics = `
{
  "rules": {
    "analytics": {
      "page_views": {
        "$page": {
          ".read": true,
          ".write": "root.child('admins').child(auth.uid).exists()"
        }
      },
      "active_users": {
        ".read": true,
        ".write": "root.child('admins').child(auth.uid).exists()"
      }
    }
  }
}
`;
```

## Multi-Room Chat System

```typescript
// Complete chat system with Realtime DB
export const chatService = {
  // Create room
  async createChatRoom(
    participants: string[],
    roomName: string
  ): Promise<string> {
    const roomRef = ref(db, 'chat_rooms');
    const newRoomRef = push(roomRef);

    const roomData = {
      name: roomName,
      participants,
      createdAt: Date.now(),
      createdBy: participants[0],
      messageCount: 0,
      lastMessage: '',
      lastMessageTime: 0,
    };

    await set(newRoomRef, roomData);

    // Add to participant's rooms list
    for (const participantId of participants) {
      const userRoomRef = ref(
        db,
        `user_rooms/${participantId}/${newRoomRef.key}`
      );
      await set(userRoomRef, { joinedAt: Date.now() });
    }

    return newRoomRef.key || '';
  },

  // Send message to room
  async sendRoomMessage(
    roomId: string,
    userId: string,
    message: string
  ): Promise<string> {
    const messagesRef = ref(db, `chat_rooms/${roomId}/messages`);
    const newMessageRef = push(messagesRef);

    const messageData = {
      userId,
      text: message,
      timestamp: Date.now(),
      reads: {
        [userId]: Date.now(),
      },
    };

    await set(newMessageRef, messageData);

    // Update room metadata
    await update(ref(db, `chat_rooms/${roomId}`), {
      lastMessage: message,
      lastMessageTime: Date.now(),
      messageCount: increment(1),
    });

    return newMessageRef.key || '';
  },

  // Subscribe to room messages
  subscribeToRoomMessages(
    roomId: string,
    callback: (messages: any[]) => void
  ) {
    const messagesRef = ref(
      db,
      `chat_rooms/${roomId}/messages`
    );

    return onValue(messagesRef, (snapshot) => {
      const messages: any[] = [];

      snapshot.forEach((childSnapshot) => {
        messages.push({
          id: childSnapshot.key,
          ...childSnapshot.val(),
        });
      });

      // Sort by timestamp
      messages.sort((a, b) => a.timestamp - b.timestamp);
      callback(messages);
    });
  },

  // Mark message as read
  async markMessageAsRead(
    roomId: string,
    messageId: string,
    userId: string
  ) {
    const readRef = ref(
      db,
      `chat_rooms/${roomId}/messages/${messageId}/reads/${userId}`
    );
    await set(readRef, Date.now());
  },
};
```

## Best Practices

**Performance:**
- Keep data shallow (avoid deeply nested structures)
- Use pagination for large datasets
- Index frequently queried data
- Clean up old data regularly
- Limit listener scope

**Real-Time Sync:**
- Use transactions for consistency
- Implement conflict resolution
- Handle network disconnections
- Queue offline changes
- Verify sync completion

**Security:**
- Validate all inputs server-side
- Use database rules for access control
- Encrypt sensitive data
- Implement rate limiting
- Log all critical operations

**Scalability:**
- Shard high-write collections
- Archive old messages
- Use separate databases for different features
- Monitor connection usage
- Implement connection pooling