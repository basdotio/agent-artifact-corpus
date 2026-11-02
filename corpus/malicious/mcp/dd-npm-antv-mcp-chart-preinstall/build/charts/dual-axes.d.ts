import { z } from "zod";
export declare const dualAxes: {
    schema: {
        categories: z.ZodArray<z.ZodString>;
        series: z.ZodArray<z.ZodObject<{
            type: z.ZodEnum<{
                column: "column";
                line: "line";
            }>;
            data: z.ZodArray<z.ZodNumber>;
            axisYTitle: z.ZodOptional<z.ZodDefault<z.ZodString>>;
        }, z.core.$strip>>;
        style: z.ZodOptional<z.ZodObject<{
            backgroundColor: z.ZodOptional<z.ZodString>;
            palette: z.ZodOptional<z.ZodArray<z.ZodString>>;
            startAtZero: z.ZodDefault<z.ZodOptional<z.ZodBoolean>>;
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
        axisXTitle: z.ZodDefault<z.ZodOptional<z.ZodString>>;
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
