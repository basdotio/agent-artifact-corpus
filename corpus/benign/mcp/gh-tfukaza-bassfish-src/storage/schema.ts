export const schemaVersion = 2;

export const coordinationSchema = `
      CREATE TABLE IF NOT EXISTS notificationBatches (
        _key TEXT NOT NULL UNIQUE, id TEXT PRIMARY KEY, projectId TEXT NOT NULL,
        identityId TEXT NOT NULL, sessionId TEXT, status TEXT NOT NULL,
        entriesJson TEXT NOT NULL CHECK(json_valid(entriesJson)),
        acknowledgedJson TEXT NOT NULL CHECK(json_valid(acknowledgedJson)),
        payloadJson TEXT NOT NULL CHECK(json_valid(payloadJson)), createdAt INTEGER NOT NULL,
        finishedAt INTEGER, issue TEXT
      );
      CREATE INDEX IF NOT EXISTS batches_recipient ON notificationBatches(projectId,identityId,status);
      CREATE TABLE IF NOT EXISTS projects (
        _key TEXT NOT NULL UNIQUE,
        id TEXT PRIMARY KEY, commonDir TEXT NOT NULL UNIQUE
      );
      CREATE TABLE IF NOT EXISTS identities (
        _key TEXT NOT NULL UNIQUE,
        id TEXT PRIMARY KEY, projectId TEXT NOT NULL, name TEXT NOT NULL,
        FOREIGN KEY(projectId) REFERENCES projects(id), UNIQUE(projectId,name COLLATE NOCASE)
      );
      CREATE TABLE IF NOT EXISTS instances (
        _key TEXT NOT NULL UNIQUE,
        id TEXT PRIMARY KEY, projectId TEXT NOT NULL, identityId TEXT NOT NULL, handle TEXT NOT NULL UNIQUE,
        epoch TEXT NOT NULL, active INTEGER NOT NULL CHECK(active IN (0,1)), lastSeen INTEGER NOT NULL, workspace TEXT NOT NULL,
        host TEXT CHECK(host IS NULL OR host IN ('claude','codex','opencode')), hostSessionId TEXT,
        FOREIGN KEY(projectId) REFERENCES projects(id), FOREIGN KEY(identityId) REFERENCES identities(id)
      );
      CREATE TABLE IF NOT EXISTS resources (
        _key TEXT NOT NULL UNIQUE,
        id TEXT PRIMARY KEY, projectId TEXT NOT NULL, type TEXT NOT NULL CHECK(type IN ('thread','ticket')),
        fence TEXT NOT NULL, queueSequence TEXT NOT NULL, present INTEGER NOT NULL CHECK(present IN (0,1)), FOREIGN KEY(projectId) REFERENCES projects(id)
      );
      CREATE TABLE IF NOT EXISTS turnRequests (
        _key TEXT NOT NULL UNIQUE,
        id TEXT PRIMARY KEY, projectId TEXT NOT NULL, resourceId TEXT,
        resourceType TEXT NOT NULL CHECK(resourceType IN ('thread','ticket','files')),
        pathsJson TEXT CHECK(pathsJson IS NULL OR json_valid(pathsJson)),
        identityId TEXT NOT NULL, instanceId TEXT NOT NULL, sequence TEXT NOT NULL,
        state TEXT NOT NULL CHECK(state IN ('QUEUED','READY','OFFERED','CLAIMED','COMMITTING','COMMITTED','RELEASED','EXPIRED','CANCELLED','FAILED')),
        createdAt INTEGER NOT NULL, updatedAt INTEGER NOT NULL, queueUntil INTEGER NOT NULL, reconnectUntil INTEGER,
        offerId TEXT UNIQUE, claimBy INTEGER, turnId TEXT UNIQUE, fence TEXT, baseRevision TEXT,
        expiresAt INTEGER, finishedAt INTEGER, resultJson TEXT CHECK(resultJson IS NULL OR json_valid(resultJson)),
        deliveryMode TEXT NOT NULL CHECK(deliveryMode IN ('ticket','task')), claimedAt INTEGER, terminalReason TEXT,
        CHECK((resourceType='files' AND resourceId IS NULL AND pathsJson IS NOT NULL AND fence IS NULL AND baseRevision IS NULL AND expiresAt IS NULL AND resultJson IS NULL AND state NOT IN ('COMMITTING','COMMITTED')) OR (resourceType!='files' AND resourceId IS NOT NULL AND pathsJson IS NULL)),
        FOREIGN KEY(projectId) REFERENCES projects(id), FOREIGN KEY(resourceId) REFERENCES resources(id),
        FOREIGN KEY(identityId) REFERENCES identities(id), FOREIGN KEY(instanceId) REFERENCES instances(id)
      );
      CREATE UNIQUE INDEX IF NOT EXISTS reserved_resource ON turnRequests(projectId,resourceId)
        WHERE state IN ('READY','OFFERED','CLAIMED','COMMITTING');
      CREATE UNIQUE INDEX IF NOT EXISTS one_content_request_per_instance ON turnRequests(instanceId)
        WHERE resourceType!='files' AND state IN ('QUEUED','READY','OFFERED','CLAIMED','COMMITTING');
      CREATE UNIQUE INDEX IF NOT EXISTS one_file_request_per_instance ON turnRequests(instanceId)
        WHERE resourceType='files' AND state IN ('QUEUED','READY','OFFERED','CLAIMED');
      CREATE TABLE IF NOT EXISTS tasks (
        _key TEXT NOT NULL UNIQUE,
        id TEXT PRIMARY KEY, projectId TEXT NOT NULL, identityId TEXT NOT NULL, requestId TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL CHECK(status IN ('working','completed','failed','cancelled')),
        statusMessage TEXT, createdAt INTEGER NOT NULL, updatedAt INTEGER NOT NULL, discardAt INTEGER NOT NULL,
        resultJson TEXT CHECK(resultJson IS NULL OR json_valid(resultJson)),
        errorJson TEXT CHECK(errorJson IS NULL OR json_valid(errorJson)),
        FOREIGN KEY(projectId) REFERENCES projects(id), FOREIGN KEY(identityId) REFERENCES identities(id), FOREIGN KEY(requestId) REFERENCES turnRequests(id)
      );
      CREATE TABLE IF NOT EXISTS workTasks (
        _key TEXT NOT NULL UNIQUE,
        id TEXT PRIMARY KEY, projectId TEXT NOT NULL, identityId TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('working','completed','failed','cancelled')),
        statusMessage TEXT, createdAt INTEGER NOT NULL, updatedAt INTEGER NOT NULL, discardAt INTEGER NOT NULL,
        resultJson TEXT CHECK(resultJson IS NULL OR json_valid(resultJson)),
        errorJson TEXT CHECK(errorJson IS NULL OR json_valid(errorJson)),
        FOREIGN KEY(projectId) REFERENCES projects(id), FOREIGN KEY(identityId) REFERENCES identities(id)
      );
      CREATE TABLE IF NOT EXISTS threadFollows (
        _key TEXT NOT NULL UNIQUE,
        projectId TEXT NOT NULL, threadId TEXT NOT NULL, identityId TEXT NOT NULL, createdAt INTEGER NOT NULL,
        PRIMARY KEY(projectId,threadId,identityId), FOREIGN KEY(projectId) REFERENCES projects(id),
        FOREIGN KEY(identityId) REFERENCES identities(id)
      );
      CREATE TABLE IF NOT EXISTS notifications (
        _key TEXT NOT NULL UNIQUE,
        id TEXT PRIMARY KEY, projectId TEXT NOT NULL, identityId TEXT NOT NULL,
        resourceType TEXT NOT NULL CHECK(resourceType IN ('thread','ticket')), resourceId TEXT NOT NULL, eventId TEXT NOT NULL,
        threadId TEXT, ticketId TEXT, messageId TEXT, sequence TEXT, senderIdentityId TEXT NOT NULL, senderName TEXT NOT NULL,
        createdAt INTEGER NOT NULL, reasonsJson TEXT NOT NULL CHECK(json_valid(reasonsJson)), lastDeliveredWakeKey TEXT,
        contentJson TEXT CHECK(contentJson IS NULL OR json_valid(contentJson)), lastDeliveredAt INTEGER,
        UNIQUE(identityId,eventId,resourceType,resourceId), FOREIGN KEY(projectId) REFERENCES projects(id), FOREIGN KEY(identityId) REFERENCES identities(id)
      );
      CREATE TABLE IF NOT EXISTS hostSessionBindings (
        _key TEXT NOT NULL UNIQUE,
        projectId TEXT NOT NULL, identityId TEXT NOT NULL, host TEXT NOT NULL CHECK(host IN ('claude','codex','opencode')),
        sessionId TEXT NOT NULL, wakeKey TEXT NOT NULL, createdAt INTEGER NOT NULL, updatedAt INTEGER NOT NULL,
        PRIMARY KEY(projectId,host,sessionId), UNIQUE(projectId,identityId),
        FOREIGN KEY(projectId) REFERENCES projects(id), FOREIGN KEY(identityId) REFERENCES identities(id)
      );
      CREATE INDEX IF NOT EXISTS instances_identity ON instances(identityId);
      CREATE INDEX IF NOT EXISTS instances_project ON instances(projectId);
      CREATE INDEX IF NOT EXISTS requests_instance ON turnRequests(instanceId,state);
      CREATE INDEX IF NOT EXISTS requests_project ON turnRequests(projectId,state);
      CREATE INDEX IF NOT EXISTS notifications_recipient ON notifications(projectId,identityId);
      CREATE TABLE IF NOT EXISTS controlMeta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
      INSERT OR IGNORE INTO controlMeta(key,value) VALUES('wallClockHighWaterMs','0'),('fileQueueSequence','0');

`;

export const contentSchema = `
CREATE TABLE IF NOT EXISTS threadContent (
 id TEXT PRIMARY KEY, projectId TEXT NOT NULL REFERENCES projects(id), revision TEXT NOT NULL,
 dataJson TEXT NOT NULL CHECK(json_valid(dataJson))
);
CREATE INDEX IF NOT EXISTS thread_project ON threadContent(projectId);
CREATE TABLE IF NOT EXISTS ticketContent (
 id TEXT PRIMARY KEY, projectId TEXT NOT NULL REFERENCES projects(id), revision TEXT NOT NULL,
 dataJson TEXT NOT NULL CHECK(json_valid(dataJson))
);
CREATE INDEX IF NOT EXISTS ticket_project ON ticketContent(projectId);
CREATE TABLE IF NOT EXISTS messages (
 id TEXT PRIMARY KEY, threadId TEXT NOT NULL REFERENCES threadContent(id), sequence TEXT NOT NULL,
 dataJson TEXT NOT NULL CHECK(json_valid(dataJson)), UNIQUE(threadId,sequence)
);
CREATE TABLE IF NOT EXISTS revisions (
 operationId TEXT PRIMARY KEY, projectId TEXT NOT NULL REFERENCES projects(id), resourceId TEXT NOT NULL,
 resourceType TEXT NOT NULL CHECK(resourceType IN ('thread','ticket')), revision TEXT NOT NULL,
 at TEXT NOT NULL, dataJson TEXT NOT NULL CHECK(json_valid(dataJson)),
 historyJson TEXT NOT NULL CHECK(json_valid(historyJson)), resultJson TEXT NOT NULL CHECK(json_valid(resultJson)),
 UNIQUE(resourceId,revision)
);
CREATE INDEX IF NOT EXISTS revision_project ON revisions(projectId,at,operationId);
CREATE TABLE IF NOT EXISTS messageVisibility (
 operationId TEXT PRIMARY KEY REFERENCES revisions(operationId), threadId TEXT NOT NULL,
 messageId TEXT NOT NULL REFERENCES messages(id), revision TEXT NOT NULL, visible INTEGER NOT NULL CHECK(visible IN (0,1))
);
CREATE INDEX IF NOT EXISTS visibility_message ON messageVisibility(messageId,revision);
CREATE TABLE IF NOT EXISTS coordinationGuards(id TEXT PRIMARY KEY, revision INTEGER NOT NULL);
INSERT OR IGNORE INTO coordinationGuards VALUES('files',0);
CREATE TABLE IF NOT EXISTS activityOutbox (
 id TEXT PRIMARY KEY, batchId TEXT NOT NULL, position INTEGER NOT NULL, projectId TEXT NOT NULL, at INTEGER NOT NULL, eventJson TEXT NOT NULL CHECK(json_valid(eventJson))
);
CREATE TABLE IF NOT EXISTS activityEvents (
 seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
 projectId TEXT NOT NULL, at INTEGER NOT NULL, kind TEXT NOT NULL,
 actor TEXT, resourceId TEXT NOT NULL, eventJson TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS activity_project_sequence ON activityEvents(projectId,seq);
CREATE INDEX IF NOT EXISTS activity_project_time ON activityEvents(projectId,at);
CREATE TABLE IF NOT EXISTS activityProjects (projectId TEXT PRIMARY KEY, since INTEGER NOT NULL, prunedThrough INTEGER NOT NULL DEFAULT 0);
INSERT OR IGNORE INTO controlMeta(key,value) VALUES('activitySince','0'),('activityHead','0');
PRAGMA user_version=2;
`;
