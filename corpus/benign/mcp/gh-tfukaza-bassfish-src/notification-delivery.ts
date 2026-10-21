export interface DeliveredNotification {
  index: number;
  resourceType: 'thread' | 'ticket';
  resourceId: string;
  sender: string;
  reasons: string[];
  content?:
    | { kind: 'thread_message'; threadTitle: string; body: string; retracted: boolean }
    | { kind: 'ticket_summary'; title: string; state: string; owner: string };
  truncated?: boolean;
}
export interface DeliveryBatch {
  kind: 'actionable' | 'activity' | 'none';
  count: number;
  batchToken?: string;
  moreAvailable: boolean;
  notifications: DeliveredNotification[];
}
export const emptyBatch = (): DeliveryBatch => ({
  kind: 'none',
  count: 0,
  moreAvailable: false,
  notifications: [],
});
export function formatDeliveryContext(batch: DeliveryBatch): string {
  const lines = [
    batch.kind === 'actionable' ? '[Bassfish: action requested]' : '[Bassfish: project activity]',
  ];
  const groups = new Map<string, DeliveredNotification[]>();
  for (const item of batch.notifications)
    groups.set(item.resourceId, [...(groups.get(item.resourceId) ?? []), item]);
  for (const [id, items] of groups) {
    const first = items[0]!;
    const title =
      first.content?.kind === 'thread_message' ? first.content.threadTitle : first.content?.title;
    lines.push(`${first.resourceType} ${id}${title ? ` · ${title}` : ''}`);
    for (const item of items) {
      lines.push(`${item.index}. ${item.sender} · ${item.reasons.join(', ')}`);
      if (item.content?.kind === 'thread_message')
        lines.push(item.content.retracted ? '[retracted]' : item.content.body);
      else if (item.content) lines.push(`state=${item.content.state}; owner=${item.content.owner}`);
      if (item.truncated)
        lines.push(
          `[truncated: notifications read batchToken=${batch.batchToken} item=${item.index}]`,
        );
    }
  }
  if (batch.moreAvailable)
    lines.push('More updates remain; fetch the next batch at your checkpoint.');
  lines.push(
    `After processing: notifications acknowledge batchToken=${batch.batchToken}. Use items for partial acknowledgement.`,
  );
  return lines.join('\n');
}
