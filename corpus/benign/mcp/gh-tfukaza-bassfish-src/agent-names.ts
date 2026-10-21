import { randomInt } from 'node:crypto';

const currents = [
  'Azure',
  'Blue',
  'Bright',
  'Calm',
  'Clear',
  'Coral',
  'Deep',
  'Drift',
  'Emerald',
  'Moon',
  'Pacific',
  'Quiet',
  'Silver',
  'Tidal',
  'Wave',
  'Wild',
] as const;

const swimmers = [
  'Anchovy',
  'Bass',
  'Beluga',
  'Bluefish',
  'Carp',
  'Dolphin',
  'Eel',
  'Heron',
  'Koi',
  'Manta',
  'Marlin',
  'Otter',
  'Ray',
  'Salmon',
  'Seal',
  'Trout',
] as const;

/** A fixed pool of 256 readable aquatic codenames. */
export const generatedAgentNames = Object.freeze(
  currents.flatMap(current => swimmers.map(swimmer => `${current}${swimmer}`)),
);

export function selectGeneratedAgentName(
  usedNames: Iterable<string>,
  selectIndex: (size: number) => number = size => randomInt(size),
): string | undefined {
  const used = new Set([...usedNames].map(name => name.toLowerCase()));
  const available = generatedAgentNames.filter(name => !used.has(name.toLowerCase()));
  if (available.length === 0) return undefined;
  const index = selectIndex(available.length);
  if (!Number.isSafeInteger(index) || index < 0 || index >= available.length)
    throw new RangeError('Generated agent-name index is out of range.');
  return available[index];
}
