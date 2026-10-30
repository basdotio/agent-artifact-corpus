import { z } from "zod";
export declare const area: {
    schema: {
        data: z.ZodArray<z.ZodObject<{
            time: z.ZodString;
            value: z.ZodNumber;
            group: z.ZodOptional<z.ZodString>;
        }, z.core.$strip>>;
        stack: z.ZodDefault<z.ZodOptional<z.ZodBoolean>>;
        style: z.ZodOptional<z.ZodObject<{
            backgroundColor: z.ZodOptional<z.ZodString>;
            palette: z.ZodOptional<z.ZodArray<z.ZodString>>;
            texture: z.ZodDefault<z.ZodOptional<z.ZodEnum<{
                default: "default";
                rough: "rough";
            }>>>;
            lineWidth: z.ZodOptional<z.ZodNumber>;
        }, z.core.$strip>>;
        theme: z.ZodDefault<z.ZodOptional<z.ZodEnum<{
            dark: "dark";
            default: "default";
            academy: "academy";
        }>>>;
        width: z.ZodDefault<z.ZodOptional<z.ZodNumber>>;
        height: z.ZodDefault<z.ZodOptional<z.ZodNumber>>;
        title: z.ZodDefault<z.ZodOptional<z.ZodString>>;
        axisXTitle: z.ZodDefault<z.ZodOptional<z.ZodString>>;
        axisYTitle: z.ZodDefault<z.ZodOptional<z.ZodString>>;
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
