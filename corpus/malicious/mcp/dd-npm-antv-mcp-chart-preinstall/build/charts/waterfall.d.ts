import { z } from "zod";
export declare const waterfall: {
    schema: {
        data: z.ZodArray<z.ZodObject<{
            category: z.ZodString;
            value: z.ZodOptional<z.ZodNumber>;
            isIntermediateTotal: z.ZodOptional<z.ZodBoolean>;
            isTotal: z.ZodOptional<z.ZodBoolean>;
        }, z.core.$strip>>;
        style: z.ZodOptional<z.ZodObject<{
            backgroundColor: z.ZodOptional<z.ZodString>;
            texture: z.ZodDefault<z.ZodOptional<z.ZodEnum<{
                default: "default";
                rough: "rough";
            }>>>;
            palette: z.ZodOptional<z.ZodObject<{
                positiveColor: z.ZodOptional<z.ZodString>;
                negativeColor: z.ZodOptional<z.ZodString>;
                totalColor: z.ZodOptional<z.ZodString>;
            }, z.core.$strip>>;
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
