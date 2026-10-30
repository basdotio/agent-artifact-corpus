/**
 * The Error class for validation errors in zod.
 */
export declare class ValidateError extends Error {
    constructor(message: string);
}
export type NodeEdgeDataType = {
    nodes: Array<{
        name: string;
    }>;
    edges: Array<{
        name: string;
        source: string;
        target: string;
    }>;
};
export type TreeDataType = {
    name: string;
    children?: TreeDataType[];
};
/**
 * Valid node name is unique.
 * Valid edge source and target are existing in nodes.
 * Valid edge source edge target pair are unique.
 * @param data
 * @returns boolean
 */
export declare const validatedNodeEdgeDataSchema: (data: NodeEdgeDataType) => boolean;
/**
 * Valid TreeData name is unique.
 * @param data
 * @returns boolean
 */
export declare const validatedTreeDataSchema: (data: TreeDataType) => boolean;
