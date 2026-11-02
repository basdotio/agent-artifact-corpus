import { z } from "zod";
export declare const flowDiagram: {
    schema: {
        data: z.ZodObject<{
            nodes: z.ZodArray<z.ZodObject<{
                name: z.ZodString;
            }, z.core.$strip>>;
            edges: z.ZodArray<z.ZodObject<{
                source: z.ZodString;
                target: z.ZodString;
                name: z.ZodDefault<z.ZodOptional<z.ZodString>>;
            }, z.core.$strip>>;
        }, z.core.$strip>;
        style: z.ZodOptional<z.ZodObject<{
            texture: z.ZodDefault<z.ZodOptional<z.ZodEnum<{
                default: "default";
                rough: "rough";
            }>>>;
        }, z.core.$strip>>;
        theme: z.ZodDefault<z.ZodOptional<z.ZodEnum<{
            dark: "dark";
            default: "default";
            academy: "academy";
        }>>>;
        width: z.ZodDefault<z.ZodOptional<z.ZodNumber>>;
        height: z.ZodDefault<z.ZodOptional<z.ZodNumber>>;
    };
    tool: {
        name: string;
        description: string;
        inputSchema: z.core.ZodStandardJSONSchemaPayload<z.ZodObject<{
            [x: string]: z.ZodType<any, unknown, z.core.$ZodTypeInternals<any, unknown>>;
        }, z.core.$strip>>;
        annotations: {
            title: string;
            readOnlyHint: boolean;
        };
    };
};
