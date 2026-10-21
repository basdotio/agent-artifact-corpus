import path from 'node:path';
import fs from 'node:fs/promises';
import type { GeneratedDocs, WebsiteData } from '../types/website.js';
import { resolveOutputDir } from '../lib/paths.js';
import { analyzeColors } from '../analyzers/color.js';
import { analyzeTypography } from '../analyzers/typography.js';
import { analyzeSpacing, analyzeShadows } from '../analyzers/spacing.js';
import { analyzeLayout } from '../analyzers/layout.js';
import { analyzeComponents } from '../analyzers/component.js';
import { analyzeResponsive, responsiveOutputDir } from '../analyzers/responsive.js';
import { analyzeContent } from '../lib/dom.js';
import { generateDesignDoc, generateDesignJson } from '../generators/design.js';
import { generateRulesDoc } from '../generators/rule.js';
import { generateComponentsDoc } from '../generators/component.js';
import { generateLayoutDoc } from '../generators/layout.js';
import { generateContentDoc } from '../generators/content.js';
import { generateReadme } from '../generators/readme.js';
import { viewportWidthsFromConfig, config } from '../config.js';
import { inspectPage } from './inspect.js';

export type DocKind = 'design' | 'rule' | 'component' | 'layout' | 'content' | 'readme';

const ALL_DOCS: DocKind[] = ['design', 'rule', 'component', 'layout', 'content', 'readme'];

function siteDir(base: string, url: string): string {
  const host = new URL(url).host.replace(/[^a-z0-9._-]+/gi, '-').toLowerCase();
  return path.join(base, host);
}

export async function generateDocs(
  url: string,
  options?: {
    outputDir?: string;
    documents?: DocKind[];
    screenshots?: boolean;
  },
): Promise<GeneratedDocs & { data: WebsiteData }> {
  const baseDir = resolveOutputDir(options?.outputDir ?? './docs');
  const docs = options?.documents?.length ? options.documents : ALL_DOCS;
  const wantShots = options?.screenshots ?? config.screenshot;

  const { data } = await inspectPage(url);
  const spacing = analyzeSpacing(data);
  const shadows = analyzeShadows(data);
  const layout = analyzeLayout(data);
  const components = analyzeComponents(data);
  const content = analyzeContent(data.html, data.title, data.description);

  const responsive = await analyzeResponsive(data, {
    captureScreenshots: wantShots,
    outputDir: responsiveOutputDir(baseDir, new URL(data.url).host),
    widths: viewportWidthsFromConfig(),
  });

  const design = {
    colors: analyzeColors(data),
    typography: analyzeTypography(data),
    spacing,
    layout,
    responsive,
    borderRadii: spacing.borderRadii,
    shadows,
  };

  const outDir = siteDir(baseDir, data.url);
  await fs.mkdir(outDir, { recursive: true });

  const absoluteFiles: string[] = [];
  const relativeNames: string[] = [];

  const write = async (name: string, body: string) => {
    const fp = path.join(outDir, name);
    await fs.writeFile(fp, body, 'utf8');
    absoluteFiles.push(fp);
    relativeNames.push(name);
  };

  if (docs.includes('design')) {
    await write('design.md', generateDesignDoc(data, design));
    await write('design.json', generateDesignJson(data, design));
  }
  if (docs.includes('rule')) await write('rule.md', generateRulesDoc(data, design));
  if (docs.includes('component')) await write('component.md', generateComponentsDoc(data, components));
  if (docs.includes('layout')) await write('layout.md', generateLayoutDoc(data, layout, responsive));
  if (docs.includes('content')) await write('content.md', generateContentDoc(data, content));
  if (docs.includes('readme')) {
    await write(
      'README.md',
      generateReadme(data, design, components, [
        ...relativeNames.filter((n) => n !== 'README.md'),
        'README.md',
        ...responsive.breakpoints.filter((b) => b.screenshotPath).map((b) => path.relative(outDir, b.screenshotPath!)),
      ]),
    );
  }

  return { outputDir: outDir, files: absoluteFiles, data };
}
