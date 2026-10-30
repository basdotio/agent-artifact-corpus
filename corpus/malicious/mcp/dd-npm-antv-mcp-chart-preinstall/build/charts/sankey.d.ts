import { z } from "zod";
export declare const sankey: {
    schema: {
        data: z.ZodArray<z.ZodObject<{
            source: z.ZodString;
            target: z.ZodString;
            value: z.ZodNumber;
        }, z.core.$strip>>;
        nodeAlign: z.ZodDefault<z.ZodOptional<z.ZodEnum<{
            left: "left";
            right: "right";
            justify: "justify";
            center: "center";
        }>>>;
        style: z.ZodOptional<z.ZodObject<{
            backgroundColor: z.ZodOptional<z.ZodString>;
            palette: z.ZodOptional<z.ZodArray<z.ZodString>>;
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
        title: z.ZodDefault<z.ZodOptional<z.ZodString>>;
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
