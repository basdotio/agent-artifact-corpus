import { z } from "zod";
export declare const zodToJsonSchema: (schema: Record<string, z.ZodType<any>>) => z.core.ZodStandardJSONSchemaPayload<z.ZodObject<{
    [x: string]: z.ZodType<any, unknown, z.core.$ZodTypeInternals<any, unknown>>;
}, z.core.$strip>>;
