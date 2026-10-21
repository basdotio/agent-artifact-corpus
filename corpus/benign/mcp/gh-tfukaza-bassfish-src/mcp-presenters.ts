type Data = Record<string, unknown>;

const data = (value: unknown): Data => value as Data;
const strings = (value: unknown): string[] =>
  Array.isArray(value) ? (value.filter(item => typeof item === 'string') as string[]) : [];

function presentTarget(value: unknown): Data {
  const target = data(value);
  if (target.type === 'thread') return { type: 'thread', threadId: target.id };
  if (target.type === 'files') return { type: 'files', paths: target.paths };
  if (target.type === 'ticket') return { type: 'ticket', ticketId: target.id };
  return { type: target.type, ...(target.purpose ? { purpose: target.purpose } : {}) };
}

export function presentTurnStatus(value: unknown): Data {
  const status = data(value);
  return {
    state: status.state,
    requestToken: status.requestId,
    target: presentTarget(status.target),
    ...(status.position !== undefined ? { position: status.position } : {}),
    ...(data(status.target).type === 'files' ? { lifetime: 'session' } : {}),
    ...(status.expiresAt ? { expiresAt: status.expiresAt } : {}),
  };
}

function presentNotification(value: unknown): Data {
  const item = data(value);
  const sender = data(item.sender);
  return {
    ...(item.notificationId ? { notificationId: item.notificationId } : { index: item.index }),
    resourceType: item.resourceType,
    resourceId: item.resourceId,
    ...(item.threadId ? { threadId: item.threadId, sequence: item.sequence } : {}),
    ...(item.ticketId ? { ticketId: item.ticketId } : {}),
    sender: typeof item.sender === 'string' ? item.sender : sender.name,
    reasons: strings(item.reasons),
    ...(item.createdAt ? { createdAt: item.createdAt } : {}),
    ...(item.content ? { content: item.content } : {}),
    ...(item.truncated ? { truncated: true } : {}),
  };
}

export function presentNotifications(value: unknown): Data {
  const page = data(value);
  const rows = Array.isArray(page.notifications) ? page.notifications.map(presentNotification) : [];
  return {
    notifications: rows,
    ...(page.batchToken ? { batchToken: page.batchToken, kind: page.kind, count: page.count } : {}),
    ...(page.nextCursor !== undefined ? { nextCursor: page.nextCursor } : {}),
    ...(page.moreAvailable !== undefined ? { moreAvailable: page.moreAvailable } : {}),
  };
}

export function presentThread(value: unknown): Data {
  const thread = data(value);
  const description = typeof thread.description === 'string' ? thread.description : '';
  return {
    threadId: thread.id,
    title: thread.title,
    descriptionPreview: description.length > 240 ? `${description.slice(0, 237)}...` : description,
    state: thread.state,
    revision: thread.revision,
    following: Boolean(thread.following),
    createdAt: thread.createdAt,
  };
}

export function presentTicket(value: unknown): Data {
  const ticket = data(value);
  return {
    ticketId: ticket.id,
    title: ticket.title,
    descriptionPreview:
      typeof ticket.description === 'string' ? ticket.description.slice(0, 240) : '',
    owner: ticket.ownerName,
    state: ticket.state,
    dependsOn: strings(ticket.dependsOn),
    blockedBy: strings(ticket.blockedBy),
    ready: Boolean(ticket.ready),
    revision: ticket.revision,
    createdAt: ticket.createdAt,
    updatedAt: ticket.updatedAt,
  };
}

export function presentMessage(value: unknown): Data {
  const message = data(value);
  const mentions = data(message.mentions);
  return {
    messageId: message.id,
    sequence: message.sequence,
    author: message.name,
    createdAt: message.createdAt,
    body: message.body,
    ...((Array.isArray(mentions.agents) && mentions.agents.length > 0) ||
    mentions.here ||
    mentions.global
      ? {
          mentions: {
            agents: strings(mentions.agents),
            here: Boolean(mentions.here),
            global: Boolean(mentions.global),
          },
        }
      : {}),
    retracted: Boolean(message.retracted),
  };
}

export function presentClaim(value: unknown): Data {
  const result = data(value);
  if (data(result.target).type === 'files') {
    if (result.state && result.state !== 'claimed') return presentTurnStatus(result);
    return {
      state: 'claimed',
      requestToken: result.requestId,
      turnToken: data(result.turn).id,
      target: presentTarget(result.target),
      lifetime: 'session',
    };
  }
  const turn = data(result.turn);
  const page = data(result.page);
  if (page.type === 'thread') {
    return {
      state: 'claimed',
      requestToken: result.requestId,
      turnToken: turn.id,
      expiresAt: turn.expiresAt,
      resource: { ...presentThread(page.thread), following: true },
    };
  }
  if (page.type === 'ticket') {
    return {
      state: 'claimed',
      requestToken: result.requestId,
      turnToken: turn.id,
      expiresAt: turn.expiresAt,
      resource: presentTicket(page.ticket),
    };
  }
  throw new Error('Unsupported content claim.');
}

export function presentTask(value: unknown): Data {
  const task = data(value);
  const result = task.result ? presentClaim(task.result) : undefined;
  return { ...task, ...(result ? { result } : {}) };
}

export function presentMentionTask(value: unknown): Data {
  const task = data(value);
  const result = task.result ? presentNotifications(task.result) : undefined;
  return { ...task, ...(result ? { result } : {}) };
}
