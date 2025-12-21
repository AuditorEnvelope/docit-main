/**
 * Draft Store Module
 * Export all store-related types and functions
 */

export { useDraftStore } from './useDraftStore';
export type {
  FileNode,
  FileNodeType,
  OpenFile,
  FileChange,
  StructureChange,
  PendingChanges,
  DraftState,
  DraftActions,
  DraftStore,
} from './types';
export {
  convertOldStructureToFileNodes,
  convertFileNodesToOldStructure,
  flattenFileTree,
  findNode,
  countFiles,
  getParentChain,
  isAncestor,
} from './utils';
