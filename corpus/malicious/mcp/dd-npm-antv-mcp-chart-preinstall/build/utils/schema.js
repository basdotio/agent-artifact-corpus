"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.zodToJsonSchema = void 0;
const zod_1 = require("zod");
// biome-ignore lint/suspicious/noExplicitAny: <explanation>
const zodToJsonSchema = (schema) => {
    return zod_1.z.object(schema).toJSONSchema({
        io: "input",
        target: "draft-07",
    });
};
exports.zodToJsonSchema = zodToJsonSchema;
