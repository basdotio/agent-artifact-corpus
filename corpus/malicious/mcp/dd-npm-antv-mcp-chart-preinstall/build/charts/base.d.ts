import { z } from "zod";
export declare const ThemeSchema: z.ZodDefault<z.ZodOptional<z.ZodEnum<{
    dark: "dark";
    default: "default";
    academy: "academy";
}>>>;
export declare const BackgroundColorSchema: z.ZodOptional<z.ZodString>;
export declare const PaletteSchema: z.ZodOptional<z.ZodArray<z.ZodString>>;
export declare const TextureSchema: z.ZodDefault<z.ZodOptional<z.ZodEnum<{
    default: "default";
    rough: "rough";
}>>>;
export declare const StartAtZeroSchema: z.ZodDefault<z.ZodOptional<z.ZodBoolean>>;
export declare const WidthSchema: z.ZodDefault<z.ZodOptional<z.ZodNumber>>;
export declare const HeightSchema: z.ZodDefault<z.ZodOptional<z.ZodNumber>>;
export declare const TitleSchema: z.ZodDefault<z.ZodOptional<z.ZodString>>;
export declare const AxisXTitleSchema: z.ZodDefault<z.ZodOptional<z.ZodString>>;
export declare const AxisYTitleSchema: z.ZodDefault<z.ZodOptional<z.ZodString>>;
export declare const NodeSchema: z.ZodObject<{
    name: z.ZodString;
}, z.core.$strip>;
export declare const EdgeSchema: z.ZodObject<{
    source: z.ZodString;
    target: z.ZodString;
    name: z.ZodDefault<z.ZodOptional<z.ZodString>>;
}, z.core.$strip>;
export declare const MapTitleSchema: z.ZodString;
export declare const MapWidthSchema: z.ZodDefault<z.ZodOptional<z.ZodNumber>>;
export declare const MapHeightSchema: z.ZodDefault<z.ZodOptional<z.ZodNumber>>;
export declare const POIsSchema: z.ZodArray<z.ZodString>;
