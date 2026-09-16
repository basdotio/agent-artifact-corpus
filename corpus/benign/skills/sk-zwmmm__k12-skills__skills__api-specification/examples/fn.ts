import type { GlobalHowList } from '@repo/types';
import { request } from '../utils';

/**
 * 查询 GlobalHow（按 groupId）
 * GET /secure/globalTask/by/group/{groupId}
 */
export const getGlobalHowDetails = async (groupId: number) => {
  return request<GlobalHowList>(
    `/api/lab-timesheet/secure/globalTask/by/group/${groupId}`,
    {
      method: 'get',
    },
  );
};
