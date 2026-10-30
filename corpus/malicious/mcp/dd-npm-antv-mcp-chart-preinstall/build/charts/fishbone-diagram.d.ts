import { z } from "zod";
import { type TreeDataType } from "../utils/validator";
export declare const FishboneNodeSchema: z.ZodType<TreeDataType>;
export declare const fishboneDiagram: {
    schema: {
        data: z.ZodType<TreeDataType, unknown, z.core.$ZodTypeInternals<TreeDataType, unknown>>;
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
