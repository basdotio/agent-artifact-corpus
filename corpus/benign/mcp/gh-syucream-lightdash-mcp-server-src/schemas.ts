import { z } from 'zod';

export const ListProjectsRequestSchema = z.object({});

export const GetProjectRequestSchema = z.object({
  projectUuid: z
    .string()
    .uuid()
    .describe(
      'The UUID of the project. You can obtain it from the project list.'
    ),
});

export const ListSpacesRequestSchema = z.object({
  projectUuid: z
    .string()
    .uuid()
    .describe(
      'The UUID of the project. You can obtain it from the project list.'
    ),
});

export const ListChartsRequestSchema = z.object({
  projectUuid: z
    .string()
    .uuid()
    .describe(
      'The UUID of the project. You can obtain it from the project list.'
    ),
});

export const ListDashboardsRequestSchema = z.object({
  projectUuid: z
    .string()
    .uuid()
    .describe(
      'The UUID of the project. You can obtain it from the project list.'
    ),
});

export const GetCustomMetricsRequestSchema = z.object({
  projectUuid: z
    .string()
    .uuid()
    .describe(
      'The UUID of the project. You can obtain it from the project list.'
    ),
});

export const GetCatalogRequestSchema = z.object({
  projectUuid: z
    .string()
    .uuid()
    .describe(
      'The UUID of the project. You can obtain it from the project list.'
    ),
});

export const GetMetricsCatalogRequestSchema = z.object({
  projectUuid: z
    .string()
    .uuid()
    .describe(
      'The UUID of the project. You can obtain it from the project list.'
    ),
});

export const GetChartsAsCodeRequestSchema = z.object({
  projectUuid: z
    .string()
    .uuid()
    .describe(
      'The UUID of the project. You can obtain it from the project list.'
    ),
});

export const GetDashboardsAsCodeRequestSchema = z.object({
  projectUuid: z
    .string()
    .uuid()
    .describe(
      'The UUID of the project. You can obtain it from the project list.'
    ),
});

export const GetMetadataRequestSchema = z.object({
  projectUuid: z
    .string()
    .uuid()
    .describe(
      'The UUID of the project. You can obtain it from the project list.'
    ),
  table: z.string().min(1, 'Table name cannot be empty'),
});

export const GetAnalyticsRequestSchema = z.object({
  projectUuid: z
    .string()
    .uuid()
    .describe(
      'The UUID of the project. You can obtain it from the project list.'
    ),
  table: z.string(),
});

export const GetUserAttributesRequestSchema = z.object({});
