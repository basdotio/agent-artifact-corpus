import { z } from "zod";
export declare const liquid: {
    schema: {
        percent: z.ZodNumber;
        shape: z.ZodDefault<z.ZodOptional<z.ZodEnum<{
            circle: "circle";
            rect: "rect";
            pin: "pin";
            triangle: "triangle";
        }>>>;
        style: z.ZodOptional<z.ZodObject<{
            backgroundColor: z.ZodOptional<z.ZodString>;
            texture: z.ZodDefault<z.ZodOptional<z.ZodEnum<{
                default: "default";
                rough: "rough";
            }>>>;
            color: z.ZodOptional<z.ZodString>;
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
