import { BassfishError, type Mutation, type ResourceType } from '../domain.js';
import type { Bassfish } from '../service.js';
type Options = {
  taskCapable?: boolean;
};
type Credential = {
  id: string;
  fencingToken: string;
};

const mutation = (value: unknown): Mutation => value as Mutation;
export async function dispatchAdmin(
  service: Bassfish,
  handle: string,
  name: string,
  args: Record<string, unknown>,
  signal?: AbortSignal,
  options: Options = {},
): Promise<unknown> {
  switch (name) {
    case 'getSession':
      return await service.info(handle);
    case 'setAgentName':
      return await service.requestName(handle, args.name as string);
    case 'listAgents':
      return await service.listAgents(
        handle,
        args.onlineOnly as boolean,
        args.includeSelf as boolean,
      );
    case 'followThread':
      return service.followThread(handle, args.threadId as string);
    case 'unfollowThread':
      return service.unfollowThread(handle, args.threadId as string);
    case 'listNotifications':
      return service.listNotifications(
        handle,
        args.limit as number,
        args.cursor as string | undefined,
      );
    case 'waitForWork':
      throw new BassfishError(
        'TASKS_REQUIRED',
        'waitForWork is available through a Tasks-capable MCP connection.',
      );
    case 'ackNotifications':
      return await service.ackNotifications(handle, args.notificationIds as string[]);
    case 'createThread':
      return service.createThread(handle, args.title as string, args.description as string);
    case 'listThreads':
      return service.listThreadMetadata(handle, args);
    case 'getThread':
      return service.getThreadMetadata(handle, args.threadId as string);
    case 'searchThreads':
      return service.searchThreadMetadata(handle, args);
    case 'requestTurn': {
      const target = args.target as {
        type: ResourceType;
        id?: string;
      };
      const mode = options.taskCapable ? 'task' : 'ticket';
      const result = await service.requestResourceTurn(handle, target.type, target.id!, mode);
      const task = await service.control.view(async state =>
        (await state.all('tasks')).find(value => value.requestId === result.requestId),
      );
      return task?.status === 'working' ? { task: service.taskView(task) } : result;
    }
    case 'getTurnRequest':
      return await service.status(handle, args.requestId as string);
    case 'waitForTurn':
      return service.waitForTurn(
        handle,
        args.requestId as string,
        args.timeoutMs as number,
        signal,
      );
    case 'cancelTurnRequest':
      return await service.cancelTurnRequest(handle, args.requestId as string);
    case 'claimTurn':
      return service.claimTurn(handle, args.offerId as string, 20);
    case 'readTurn': {
      const credential = args.turn as Credential;
      return service.readTurn(
        handle,
        credential.id,
        credential.fencingToken,
        args.cursor as string | undefined,
      );
    }
    case 'releaseTurn': {
      const credential = args.turn as Credential;
      return await service.releaseTurn(handle, credential.id, credential.fencingToken);
    }
    case 'commitTurn': {
      const credential = args.turn as Credential;
      return service.commitTurn(
        handle,
        credential.id,
        credential.fencingToken,
        args.baseRevision as string,
        mutation(args.mutation),
      );
    }
    case 'inspectProject':
      return service.projectSnapshotInfo(handle);
    case 'exportProject':
      return service.exportProject(handle);
    case 'listProjectHistory':
      return service.projectHistoryList(
        handle,
        args.limit as number,
        args.cursor as string | undefined,
      );
    case 'listHistory':
      return service.resourceHistory(
        handle,
        args.resourceId as string,
        args.offset as number,
        args.limit as number,
      );
    case 'readRevision':
      return service.resourceAt(
        handle,
        args.resourceId as string,
        args.revision as string,
        20,
        args.cursor as string | undefined,
      );
    case 'diffRevision':
      return service.diffResource(handle, args.resourceId as string, args.revision as string);
  }
  throw new BassfishError('UNKNOWN_TOOL', 'Unknown Bassfish operation.');
}
