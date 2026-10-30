"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.validatedTreeDataSchema = exports.validatedNodeEdgeDataSchema = exports.ValidateError = void 0;
/**
 * The Error class for validation errors in zod.
 */
class ValidateError extends Error {
    constructor(message) {
        super(message);
        this.name = "ValidateError";
    }
}
exports.ValidateError = ValidateError;
/**
 * Valid node name is unique.
 * Valid edge source and target are existing in nodes.
 * Valid edge source edge target pair are unique.
 * @param data
 * @returns boolean
 */
const validatedNodeEdgeDataSchema = (data) => {
    const nodeNames = new Set(data.nodes.map((node) => node.name));
    const uniqueNodeNames = new Set();
    // 1. valid node name is unique
    for (const node of data.nodes) {
        if (uniqueNodeNames.has(node.name)) {
            throw new ValidateError(`Invalid parameters: node's name '${node.name}' should be unique.`);
        }
        uniqueNodeNames.add(node.name);
    }
    // 2. valid edge source and target are existing in nodes
    for (const edge of data.edges) {
        if (!nodeNames.has(edge.source)) {
            throw new ValidateError(`Invalid parameters: edge's source '${edge.source}' should exist in nodes.`);
        }
        if (!nodeNames.has(edge.target)) {
            throw new ValidateError(`Invalid parameters: edge's target '${edge.target}' should exist in nodes.`);
        }
    }
    // 3. valid edge source edge target pair are unique
    const edgePairs = new Set();
    for (const edge of data.edges) {
        const pair = `${edge.source}-${edge.target}`;
        if (edgePairs.has(pair)) {
            throw new ValidateError(`Invalid parameters: edge pair '${pair}' should be unique.`);
        }
        edgePairs.add(pair);
    }
    return true;
};
exports.validatedNodeEdgeDataSchema = validatedNodeEdgeDataSchema;
/**
 * Valid TreeData name is unique.
 * @param data
 * @returns boolean
 */
const validatedTreeDataSchema = (data) => {
    const node = data;
    const names = new Set();
    // valid node name is unique
    const checkUniqueness = (currentNode) => {
        if (names.has(currentNode.name)) {
            throw new ValidateError(`Invalid parameters: node's name '${currentNode.name}' should be unique.`);
        }
        names.add(currentNode.name);
        if (currentNode.children) {
            for (let i = 0; i < currentNode.children.length; i++) {
                const child = currentNode.children[i];
                checkUniqueness(child);
            }
        }
    };
    checkUniqueness(node);
    return true;
};
exports.validatedTreeDataSchema = validatedTreeDataSchema;
