import {
  activeStates,
  reservedStates,
  type ControlState,
  type FileTurnRequest,
  type TurnRequest,
} from '../domain.js';
import { fileSetsOverlap } from '../files.js';

type FinalTurnState = 'EXPIRED' | 'CANCELLED' | 'RELEASED' | 'FAILED' | 'COMMITTED';
export async function pendingFor(state: ControlState, instanceId: string): Promise<TurnRequest[]> {
  return (await state.all('requests')).filter(
    request => request.instanceId === instanceId && activeStates.includes(request.state),
  );
}
export async function finishRequest(
  request: TurnRequest,
  finalState: FinalTurnState,
  now: number,
  retentionMs: number,
  control?: ControlState,
): Promise<void> {
  request.state = finalState;
  request.finishedAt = now;
  request.updatedAt = now;
  const task =
    control &&
    (await control.all('tasks')).find(
      value => value.requestId === request.id && value.status === 'working',
    );
  if (!task) return;
  task.updatedAt = now;
  task.discardAt = now + retentionMs;
  if (finalState === 'FAILED') {
    task.status = 'failed';
    task.statusMessage = 'The turn request failed.';
    task.error = { code: -32603, message: 'The turn request failed.' };
  } else if (finalState !== 'COMMITTED') {
    task.status = 'cancelled';
    task.statusMessage =
      finalState === 'EXPIRED' ? 'The turn request expired.' : 'The turn request was cancelled.';
  }
}
async function makeRequestAvailable(
  state: ControlState,
  request: TurnRequest,
  now: number,
  offerMs: number,
  newId: () => string,
): Promise<void> {
  request.updatedAt = now;
  if (request.deliveryMode === 'task') {
    request.state = 'READY';
    const task = (await state.all('tasks')).find(value => value.requestId === request.id);
    if (task) {
      task.updatedAt = now;
      task.statusMessage = 'Turn ready; poll the task to claim it.';
    }
    return;
  }
  request.state = 'OFFERED';
  request.offerId = newId();
  request.claimBy = now + offerMs;
}
export async function materializeRequestOffer(
  state: ControlState,
  request: TurnRequest,
  now: number,
  offerMs: number,
  newId: () => string,
): Promise<void> {
  if (request.state !== 'READY') return;
  request.state = 'OFFERED';
  request.offerId = newId();
  request.claimBy = now + offerMs;
  request.updatedAt = now;
  const task = (await state.all('tasks')).find(
    value => value.requestId === request.id && value.status === 'working',
  );
  if (task) {
    task.statusMessage = 'Claiming the turn.';
    task.updatedAt = now;
  }
}
export async function promoteFileRequests(
  state: ControlState,
  now: number,
  offerMs: number,
  newId: () => string,
): Promise<void> {
  const requests = (await state.all('requests'))
    .filter(
      (request): request is FileTurnRequest =>
        request.resourceType === 'files' && activeStates.includes(request.state),
    )
    .sort((a, b) => (BigInt(a.sequence) < BigInt(b.sequence) ? -1 : 1));
  const reserved = requests.filter(request => reservedStates.includes(request.state));
  const earlier: FileTurnRequest[] = [];
  for (const request of requests) {
    if (request.state !== 'QUEUED') continue;
    if (
      (await state.get('instances', request.instanceId))?.active &&
      !reserved.some(other => fileSetsOverlap(request.paths, other.paths)) &&
      !earlier.some(other => fileSetsOverlap(request.paths, other.paths))
    ) {
      await makeRequestAvailable(state, request, now, offerMs, newId);
      reserved.push(request);
    }
    earlier.push(request);
  }
}
export async function promoteRequests(
  state: ControlState,
  now: number,
  offerMs: number,
  newId: () => string,
): Promise<void> {
  await promoteFileRequests(state, now, offerMs, newId);
  for (const project of await state.all('projects')) {
    const all = (await state.all('requests', { projectId: project.id })).filter(
      request => request.resourceType !== 'files',
    );
    for (const resource of await state.all('resources', { projectId: project.id, present: true })) {
      const requests = all.filter(request => request.resourceId === resource.id);
      if (requests.some(request => reservedStates.includes(request.state))) continue;
      const next = requests
        .filter(request => request.state === 'QUEUED')
        .sort((a, b) => (BigInt(a.sequence) < BigInt(b.sequence) ? -1 : 1))[0];
      if (!next || !(await state.get('instances', next.instanceId))?.active) continue;
      await makeRequestAvailable(state, next, now, offerMs, newId);
    }
  }
}
