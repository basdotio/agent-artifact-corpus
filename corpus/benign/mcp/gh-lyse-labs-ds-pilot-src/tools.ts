import { type ComponentInfo, type ComponentWithProps, getComponentProps } from "./scanner/components.js";
import { type Token } from "./scanner/tokens.js";

export function searchComponents(components: ComponentInfo[], query: string): ComponentInfo[] {
  const lower = query.toLowerCase();
  return components.filter((c) => c.name.toLowerCase().includes(lower));
}

export function getComponentWithProps(components: ComponentInfo[], name: string): ComponentWithProps | null {
  const component = components.find((c) => c.name === name);
  if (!component) return null;

  const props = getComponentProps(component.filePath, name);
  return { ...component, props };
}

export function listTokens(tokens: Token[], type?: string): Token[] {
  if (!type) return tokens;
  return tokens.filter((t) => t.type === type);
}

export function getToken(tokens: Token[], name: string): Token | null {
  return tokens.find((t) => t.name === name) || null;
}
