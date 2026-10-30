import { z } from "zod";
export declare const pinMap: {
    schema: {
        title: z.ZodString;
        data: z.ZodArray<z.ZodString>;
        markerPopup: z.ZodOptional<z.ZodObject<{
            type: z.ZodDefault<z.ZodString>;
            width: z.ZodDefault<z.ZodNumber>;
            height: z.ZodDefault<z.ZodNumber>;
            borderRadius: z.ZodDefault<z.ZodNumber>;
        }, z.core.$strip>>;
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
