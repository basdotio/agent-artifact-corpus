export interface ObservationFilter {
  threadOffset?: number;
  ticketOffset?: number;
  agentOffset?: number;
  turnOffset?: number;
  query?: string;
  threadState?: 'active' | 'archived' | 'deleted' | 'all';
  ticketState?: 'todo' | 'in_progress' | 'blocked' | 'done' | 'all';
  owner?: string;
}
