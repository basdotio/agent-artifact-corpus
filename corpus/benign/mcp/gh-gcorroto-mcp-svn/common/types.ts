// ===== BASE TYPES =====

export interface SvnConfig {
  svnPath?: string;
  workingDirectory?: string;
  /**
   * Repository URL. When set, bare repo-relative targets like
   * `/trunk/file.sql` are resolved against it, and URL-only workflows
   * no longer require a working copy.
   */
  url?: string;
  username?: string;
  password?: string;
  timeout?: number;
}

export interface SvnResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  command: string;
  workingDirectory: string;
  executionTime?: number;
}

export class SvnError extends Error {
  code?: number;
  stderr?: string;
  command?: string;

  constructor(message: string) {
    super(message);
    this.name = 'SvnError';
  }
}

// ===== REPOSITORY INFORMATION TYPES =====

export interface SvnInfo {
  path: string;
  workingCopyRootPath: string;
  url: string;
  relativeUrl: string;
  repositoryRoot: string;
  repositoryUuid: string;
  revision: number;
  nodeKind: 'file' | 'directory';
  schedule: string;
  lastChangedAuthor: string;
  lastChangedRev: number;
  lastChangedDate: string;
  textLastUpdated?: string;
  checksum?: string;
}

export interface SvnStatus {
  path: string;
  status: 'unversioned' | 'added' | 'deleted' | 'modified' | 'replaced' | 'merged' | 'conflicted' | 'ignored' | 'none' | 'normal' | 'external' | 'incomplete';
  revision?: number;
  changedRev?: number;
  changedAuthor?: string;
  changedDate?: string;
}

export interface SvnLogEntry {
  revision: number;
  author: string;
  date: string;
  message: string;
  changedPaths?: SvnChangedPath[];
}

export interface SvnChangedPath {
  action: 'A' | 'D' | 'M' | 'R';
  path: string;
  copyFromPath?: string;
  copyFromRev?: number;
}

// ===== DIFF TYPES =====

export interface SvnDiff {
  oldPath: string;
  newPath: string;
  oldRevision?: number;
  newRevision?: number;
  hunks: SvnDiffHunk[];
}

export interface SvnDiffHunk {
  oldStart: number;
  oldCount: number;
  newStart: number;
  newCount: number;
  lines: SvnDiffLine[];
}

export interface SvnDiffLine {
  type: 'context' | 'added' | 'deleted';
  content: string;
  oldLineNumber?: number;
  newLineNumber?: number;
}

// ===== BRANCH TYPES =====

export interface SvnBranch {
  name: string;
  url: string;
  lastChangedRev: number;
  lastChangedAuthor: string;
  lastChangedDate: string;
}

export interface SvnMergeInfo {
  sourcePath: string;
  mergedRevisions: number[];
  eligibleRevisions: number[];
}

// ===== PROPERTY TYPES =====

export interface SvnProperty {
  name: string;
  value: string;
  path: string;
}

export interface SvnPropertyList {
  path: string;
  properties: Record<string, string>;
}

// ===== LOCK TYPES =====

export interface SvnLock {
  path: string;
  token: string;
  owner: string;
  comment?: string;
  created: string;
  expires?: string;
}

// ===== BLAME/ANNOTATION TYPES =====

export interface SvnBlameLine {
  revision: number;
  author: string;
  date: string;
  lineNumber: number;
  content: string;
}

export interface SvnBlame {
  path: string;
  lines: SvnBlameLine[];
}

// ===== FILE OPERATION TYPES =====

export interface SvnAddOptions {
  force?: boolean;
  noIgnore?: boolean;
  autoProps?: boolean;
  noAutoProps?: boolean;
  parents?: boolean;
}

export interface SvnCommitOptions {
  message: string;
  file?: string;
  force?: boolean;
  keepLocks?: boolean;
  noUnlock?: boolean;
  targets?: string[];
}

export interface SvnUpdateOptions {
  revision?: number | 'HEAD' | 'BASE' | 'COMMITTED' | 'PREV';
  force?: boolean;
  ignoreExternals?: boolean;
  acceptConflicts?: 'postpone' | 'base' | 'mine-conflict' | 'theirs-conflict' | 'mine-full' | 'theirs-full';
}

export interface SvnCheckoutOptions {
  revision?: number | 'HEAD';
  depth?: 'empty' | 'files' | 'immediates' | 'infinity';
  force?: boolean;
  ignoreExternals?: boolean;
}

export interface SvnCopyOptions {
  message?: string;
  revision?: number | 'HEAD' | 'BASE' | 'COMMITTED' | 'PREV';
  parents?: boolean;
}

export interface SvnMoveOptions {
  message?: string;
  force?: boolean;
  parents?: boolean;
}

export interface SvnDeleteOptions {
  message?: string;
  force?: boolean;
  keepLocal?: boolean;
}

// ===== MERGE TYPES =====

export interface SvnMergeOptions {
  dryRun?: boolean;
  force?: boolean;
  ignoreAncestry?: boolean;
  recordOnly?: boolean;
  acceptConflicts?: 'postpone' | 'base' | 'mine-conflict' | 'theirs-conflict' | 'mine-full' | 'theirs-full';
}

// ===== SWITCH TYPES =====

export interface SvnSwitchOptions {
  revision?: number | 'HEAD';
  force?: boolean;
  ignoreExternals?: boolean;
  acceptConflicts?: 'postpone' | 'base' | 'mine-conflict' | 'theirs-conflict' | 'mine-full' | 'theirs-full';
}

// ===== RESOLVE TYPES =====

export interface SvnResolveOptions {
  accept: 'base' | 'working' | 'mine-conflict' | 'theirs-conflict' | 'mine-full' | 'theirs-full';
  recursive?: boolean;
}

// ===== IMPORT/EXPORT TYPES =====

export interface SvnImportOptions {
  message: string;
  noIgnore?: boolean;
  force?: boolean;
  noAutoProps?: boolean;
  autoProps?: boolean;
}

export interface SvnExportOptions {
  revision?: number | 'HEAD';
  force?: boolean;
  nativeEol?: 'LF' | 'CR' | 'CRLF';
  ignoreExternals?: boolean;
}

// ===== CAT / LIST TYPES =====

export interface SvnCatOptions {
  revision?: number | 'HEAD' | 'BASE' | 'COMMITTED' | 'PREV' | string;
}

export interface SvnListOptions {
  revision?: number | 'HEAD' | 'BASE' | 'COMMITTED' | 'PREV' | string;
  verbose?: boolean;
  recursive?: boolean;
  depth?: 'empty' | 'files' | 'immediates' | 'infinity';
  includeExternals?: boolean;
}

export interface SvnListEntry {
  name: string;
  kind: 'file' | 'dir';
  size?: number;
  revision?: number;
  author?: string;
  date?: string;
}

// ===== ANALYSIS TOOL TYPES =====

export interface SvnWorkingCopySummary {
  info: SvnInfo;
  status: SvnStatus[];
  branches: SvnBranch[];
  conflictedFiles: string[];
  modifiedFiles: string[];
  addedFiles: string[];
  deletedFiles: string[];
  unversionedFiles: string[];
  totalFiles: number;
  totalSize?: number;
}

export interface SvnBranchComparison {
  sourceBranch: string;
  targetBranch: string;
  differences: SvnLogEntry[];
  mergeInfo: SvnMergeInfo;
  conflictingFiles: string[];
}

export interface SvnHealthCheck {
  status: 'healthy' | 'warning' | 'error';
  issues: SvnHealthIssue[];
  workingCopyValid: boolean;
  repositoryAccessible: boolean;
  conflictsDetected: boolean;
  uncommittedChanges: boolean;
  lastUpdate: string;
}

export interface SvnHealthIssue {
  type: 'error' | 'warning' | 'info';
  message: string;
  path?: string;
  suggestion?: string;
}

// ===== BATCH OPERATION TYPES =====

export interface SvnBatchOperation {
  type: 'add' | 'delete' | 'move' | 'copy' | 'revert';
  source: string;
  target?: string;
  options?: any;
}

export interface SvnBatchResult {
  operation: SvnBatchOperation;
  success: boolean;
  error?: string;
  result?: any;
}

// ===== CONSTANTS =====

export const SVN_STATUS_CODES = {
  ' ': 'none',
  'A': 'added',
  'D': 'deleted',
  'M': 'modified',
  'R': 'replaced',
  'C': 'conflicted',
  'X': 'external',
  'I': 'ignored',
  '?': 'unversioned',
  '!': 'missing',
  '~': 'obstructed'
} as const;

export const SVN_ACTION_CODES = {
  'A': 'added',
  'D': 'deleted',
  'M': 'modified',
  'R': 'replaced'
} as const; 