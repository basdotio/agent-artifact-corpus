import { z } from 'zod';

// Schema for a documentation section
// First declare the type, then define it to handle recursion
type DocumentationSectionSchemaType = z.ZodType<{
  title: string;
  content: string;
  subsections?: Array<{
    title: string;
    content: string;
    subsections?: any[];
    metadata?: {
      lastUpdated: string;
      version: string;
      tags?: string[];
    };
  }>;
  metadata?: {
    lastUpdated: string;
    version: string;
    tags?: string[];
  };
}>;

export const DocumentationSectionSchema: DocumentationSectionSchemaType =
  z.object({
    title: z.string(),
    content: z.string(),
    subsections: z.array(z.lazy(() => DocumentationSectionSchema)).optional(),
    metadata: z
      .object({
        lastUpdated: z.string(),
        version: z.string(),
        tags: z.array(z.string()).optional(),
      })
      .optional(),
  });

// Schema for the full documentation
export const DocumentationSchema = z.object({
  version: z.string(),
  lastUpdated: z.string(),
  title: z.string(),
  description: z.string(),
  sections: z.array(DocumentationSectionSchema),
  metadata: z.object({
    format: z.literal('mcp-docs-v1'),
    sourceUrl: z.string().optional(),
    tags: z.array(z.string()).optional(),
  }),
});

export type Documentation = z.infer<typeof DocumentationSchema>;
export type DocumentationSection = z.infer<typeof DocumentationSectionSchema>;
