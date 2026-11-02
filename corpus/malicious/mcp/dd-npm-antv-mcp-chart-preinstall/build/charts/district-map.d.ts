import { z } from "zod";
export declare const districtMap: {
    schema: {
        title: z.ZodString;
        data: z.ZodObject<{
            name: z.ZodString;
            style: z.ZodOptional<z.ZodObject<{
                fillColor: z.ZodOptional<z.ZodString>;
            }, z.core.$strip>>;
            colors: z.ZodOptional<z.ZodDefault<z.ZodArray<z.ZodString>>>;
            dataType: z.ZodOptional<z.ZodEnum<{
                number: "number";
                enum: "enum";
            }>>;
            dataLabel: z.ZodOptional<z.ZodString>;
            dataValue: z.ZodOptional<z.ZodString>;
            dataValueUnit: z.ZodOptional<z.ZodString>;
            showAllSubdistricts: z.ZodDefault<z.ZodOptional<z.ZodBoolean>>;
            subdistricts: z.ZodOptional<z.ZodArray<z.ZodObject<{
                name: z.ZodString;
                dataValue: z.ZodOptional<z.ZodString>;
                style: z.ZodOptional<z.ZodObject<{
                    fillColor: z.ZodOptional<z.ZodString>;
                }, z.core.$strip>>;
            }, z.core.$strip>>>;
        }, z.core.$strip>;
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
