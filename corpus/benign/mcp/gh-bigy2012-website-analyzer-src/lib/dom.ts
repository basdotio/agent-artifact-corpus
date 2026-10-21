import * as cheerio from 'cheerio';
import type {
  ButtonSummary,
  ContentAnalysis,
  FormSummary,
  HeadingSummary,
  ImageSummary,
  LinkSummary,
  PageInspectResult,
  ScrapedElement,
} from '../types/website.js';

export function parseDomStructure(html: string): {
  landmarkCount: Record<string, number>;
  headingOutline: string[];
  formCount: number;
  linkCount: number;
  imageCount: number;
  buttonCount: number;
} {
  const $ = cheerio.load(html);
  const landmarks = ['header', 'nav', 'main', 'footer', 'aside', 'section', 'article'];
  const landmarkCount: Record<string, number> = {};
  for (const tag of landmarks) {
    landmarkCount[tag] = $(tag).length;
  }

  const headingOutline: string[] = [];
  $('h1, h2, h3, h4, h5, h6').each((_, el) => {
    const tag = el.tagName.toLowerCase();
    const text = $(el).text().trim().slice(0, 80);
    if (text) headingOutline.push(`${tag}: ${text}`);
  });

  return {
    landmarkCount,
    headingOutline: headingOutline.slice(0, 40),
    formCount: $('form').length,
    linkCount: $('a[href]').length,
    imageCount: $('img').length,
    buttonCount: $('button, [role="button"], input[type="button"], input[type="submit"]').length,
  };
}

export function analyzeContent(html: string, title: string, description: string): ContentAnalysis {
  const structure = parseDomStructure(html);
  return {
    title,
    description,
    headings: structure.headingOutline,
    landmarkCounts: structure.landmarkCount,
    linkCount: structure.linkCount,
    imageCount: structure.imageCount,
    formCount: structure.formCount,
    buttonCount: structure.buttonCount,
  };
}

export function inspectPageFromHtml(
  html: string,
  meta: { url: string; title: string; description: string; inspectedAt?: string },
): PageInspectResult {
  const $ = cheerio.load(html);
  const structure = parseDomStructure(html);

  const headings: HeadingSummary[] = [];
  $('h1, h2, h3, h4, h5, h6').each((_, el) => {
    const tag = el.tagName.toLowerCase();
    const text = $(el).text().trim().slice(0, 120);
    if (!text) return;
    headings.push({
      level: Number(tag.slice(1)),
      text,
      tag,
    });
  });

  const links: LinkSummary[] = [];
  $('a[href]').each((_, el) => {
    if (links.length >= 80) return false;
    const href = $(el).attr('href') ?? '';
    const text = $(el).text().trim().slice(0, 80);
    if (!href) return;
    links.push({ href, text });
  });

  const images: ImageSummary[] = [];
  $('img').each((_, el) => {
    if (images.length >= 60) return false;
    images.push({
      src: $(el).attr('src') ?? '',
      alt: $(el).attr('alt') ?? '',
    });
  });

  const buttons: ButtonSummary[] = [];
  $('button, [role="button"], input[type="button"], input[type="submit"]').each((_, el) => {
    if (buttons.length >= 40) return false;
    const $el = $(el);
    const tag = el.tagName.toLowerCase();
    const id = $el.attr('id');
    const cls = ($el.attr('class') ?? '').split(/\s+/).filter(Boolean)[0];
    const text =
      tag === 'input'
        ? ($el.attr('value') ?? $el.attr('aria-label') ?? '').trim().slice(0, 80)
        : $el.text().trim().slice(0, 80);
    buttons.push({
      text,
      type: $el.attr('type') ?? tag,
      selector: id ? `#${id}` : cls ? `${tag}.${cls}` : tag,
    });
  });

  const forms: FormSummary[] = [];
  $('form').each((_, el) => {
    if (forms.length >= 20) return false;
    const $el = $(el);
    forms.push({
      action: $el.attr('action') ?? '',
      method: ($el.attr('method') ?? 'get').toLowerCase(),
      fieldCount: $el.find('input, textarea, select').length,
      id: $el.attr('id') ?? '',
    });
  });

  return {
    url: meta.url,
    title: meta.title,
    description: meta.description,
    headings: headings.slice(0, 40),
    links,
    images,
    buttons,
    forms,
    semanticElements: structure.landmarkCount,
    inspectedAt: meta.inspectedAt ?? new Date().toISOString(),
  };
}

export function groupByPattern(
  elements: ScrapedElement[],
  predicate: (el: ScrapedElement) => boolean,
  nameFrom: (el: ScrapedElement) => string,
) {
  const groups = new Map<string, ScrapedElement[]>();
  for (const el of elements) {
    if (!predicate(el)) continue;
    const key = nameFrom(el);
    const list = groups.get(key) ?? [];
    list.push(el);
    groups.set(key, list);
  }
  return groups;
}

export function selectorOf(el: ScrapedElement): string {
  if (el.id) return `#${el.id}`;
  const firstClass = el.className.split(/\s+/).filter(Boolean)[0];
  if (firstClass) return `${el.tag}.${firstClass}`;
  return el.tag;
}

export function guessComponentType(el: ScrapedElement): string {
  const cls = el.className.toLowerCase();
  const role = (el.role ?? '').toLowerCase();
  const tag = el.tag;

  if (tag === 'button' || role === 'button' || /btn|button/.test(cls)) return 'button';
  if (tag === 'a' || role === 'link') return 'link';
  if (tag === 'nav' || role === 'navigation' || /nav|menu/.test(cls)) return 'navigation';
  if (tag === 'form') return 'form';
  if (['input', 'textarea', 'select'].includes(tag) || role === 'textbox') return 'input';
  if (/card|tile|panel/.test(cls)) return 'card';
  if (/hero|banner/.test(cls)) return 'hero';
  if (tag === 'header') return 'header';
  if (tag === 'footer') return 'footer';
  if (['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].includes(tag)) return 'heading';
  return 'other';
}
