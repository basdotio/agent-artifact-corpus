import type { ComponentInfo, ComponentsAnalysis, WebsiteData } from '../types/website.js';
import { guessComponentType, groupByPattern, selectorOf } from '../lib/dom.js';

export function analyzeComponents(data: WebsiteData): ComponentsAnalysis {
  const result: ComponentsAnalysis = {
    buttons: [],
    links: [],
    forms: [],
    cards: [],
    navigation: [],
    inputs: [],
    other: [],
  };

  const interesting = data.elements.filter((el) => {
    const type = guessComponentType(el);
    return type !== 'heading' && type !== 'other'
      ? true
      : /card|hero|modal|dialog|badge|chip|tab|toast|alert/.test(el.className.toLowerCase());
  });

  const groups = groupByPattern(
    interesting,
    () => true,
    (el) => `${guessComponentType(el)}::${selectorOf(el)}`,
  );

  for (const [key, els] of groups) {
    const sample = els[0];
    const type = guessComponentType(sample);
    const info: ComponentInfo = {
      name: key.split('::')[1] || type,
      type,
      selector: selectorOf(sample),
      count: els.length,
      sampleHtml: buildSampleHtml(sample),
      styles: pickStyles(sample.styles),
      attributes: [sample.id && `id=${sample.id}`, sample.role && `role=${sample.role}`].filter(Boolean) as string[],
    };

    switch (type) {
      case 'button':
        result.buttons.push(info);
        break;
      case 'link':
        result.links.push(info);
        break;
      case 'form':
        result.forms.push(info);
        break;
      case 'card':
        result.cards.push(info);
        break;
      case 'navigation':
        result.navigation.push(info);
        break;
      case 'input':
        result.inputs.push(info);
        break;
      default:
        result.other.push(info);
    }
  }

  const sortByCount = (a: ComponentInfo, b: ComponentInfo) => b.count - a.count;
  result.buttons = result.buttons.sort(sortByCount).slice(0, 20);
  result.links = result.links.sort(sortByCount).slice(0, 20);
  result.forms = result.forms.sort(sortByCount).slice(0, 10);
  result.cards = result.cards.sort(sortByCount).slice(0, 20);
  result.navigation = result.navigation.sort(sortByCount).slice(0, 10);
  result.inputs = result.inputs.sort(sortByCount).slice(0, 20);
  result.other = result.other.sort(sortByCount).slice(0, 20);

  return result;
}

function pickStyles(styles: Record<string, string>): Record<string, string> {
  const keys = [
    'display',
    'color',
    'background-color',
    'font-size',
    'font-weight',
    'font-family',
    'padding-top',
    'padding-right',
    'padding-bottom',
    'padding-left',
    'border-radius',
    'border',
    'box-shadow',
    'gap',
    'width',
    'height',
  ];
  const out: Record<string, string> = {};
  for (const k of keys) {
    if (styles[k]) out[k] = styles[k];
  }
  return out;
}

function buildSampleHtml(el: { tag: string; id: string; className: string; text: string }): string {
  const attrs = [
    el.id ? `id="${el.id}"` : '',
    el.className ? `class="${el.className.split(/\s+/).slice(0, 4).join(' ')}"` : '',
  ]
    .filter(Boolean)
    .join(' ');
  const text = el.text.slice(0, 60);
  return `<${el.tag}${attrs ? ' ' + attrs : ''}>${text}</${el.tag}>`;
}
