// ============================================================
// Rule-Based Entity & Topic Extraction (No LLM Required)
// ============================================================
//
// Dogfooding revealed the gap: manually tagging entities and topics
// when calling remember() is tedious. This module auto-extracts
// entities and topics from raw text using simple heuristics.
//
// Not as good as LLM extraction, but works offline, costs nothing,
// and handles 80% of cases.

export interface ExtractionResult {
  entities: string[];
  topics: string[];
  suggestedSalience: number;
}

// Common stop words that shouldn't be entities
const STOP_WORDS = new Set([
  'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
  'should', 'may', 'might', 'can', 'shall', 'to', 'of', 'in', 'for',
  'on', 'with', 'at', 'by', 'from', 'as', 'into', 'about', 'between',
  'through', 'during', 'before', 'after', 'and', 'but', 'or', 'not',
  'so', 'yet', 'both', 'either', 'neither', 'each', 'every', 'all',
  'any', 'some', 'no', 'only', 'very', 'just', 'also', 'than', 'too',
  'i', 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'she', 'it',
  'they', 'them', 'his', 'her', 'its', 'their', 'this', 'that',
  'these', 'those', 'what', 'which', 'who', 'whom', 'how', 'when',
  'where', 'why', 'if', 'then', 'else', 'up', 'out', 'off', 'over',
  'under', 'again', 'once', 'here', 'there', 'more', 'most', 'other',
  'been', 'being', 'because', 'until', 'while', 'into', 'own', 'same',
  'such', 'few', 'much', 'many', 'like', 'just', 'now', 'still',
  'already', 'even', 'really', 'quite', 'well', 'back', 'way',
  'things', 'thing', 'something', 'nothing', 'everything', 'anything',
  'get', 'got', 'getting', 'make', 'made', 'making', 'take', 'took',
  'know', 'think', 'want', 'need', 'use', 'used', 'using', 'try',
  'going', 'come', 'came', 'see', 'look', 'say', 'said', 'tell',
]);

// Topic keyword patterns
const TOPIC_PATTERNS: Record<string, RegExp> = {
  'fitness': /\b(running|marathon|training|exercise|workout|gym|race|miles?|pace)\b/i,
  'engineering': /\b(code|programming|api|sdk|database|deploy|build|test|bug|refactor|typescript|python|react|node)\b/i,
  'career': /\b(job|work|company|team|promotion|role|position|hired|salary|interview|manager|pm|product\s*manager)\b/i,
  'preferences': /\b(prefer|prefers|preferred|like|love|hate|dislike|favorite|always|never|rather|instead|over)\b/i,
  'goals': /\b(goal|plan|want to|going to|will|hope|aim|target|dream|aspire|training for|preparing for)\b/i,
  'decisions': /\b(decided|decision|chose|picked|going with|switched to|pivoted|moved to)\b/i,
  'project': /\b(project|build|launch|ship|release|feature|roadmap|milestone|sprint)\b/i,
  'learning': /\b(learn|study|course|tutorial|reading|book|class|practice|piano)\b/i,
  'people': /\b(friend|family|wife|husband|partner|kid|child|parent|mom|dad|brother|sister|coach)\b/i,
  'strategy': /\b(strategy|approach|plan|roadmap|competitive|market|monetize|revenue|pricing)\b/i,
  'ai': /\b(ai|agent|llm|model|gpt|claude|openai|anthropic|memory|embedding|vector)\b/i,
};

// Salience signals
const HIGH_SALIENCE_PATTERNS = [
  /\b(important|critical|key|must|always|never|essential|crucial)\b/i,
  /\b(decided|committed|promise|goal|deadline)\b/i,
  /\b(love|hate|strongly|absolutely|definitely)\b/i,
  /\b(problem|issue|bug|error|broken|fix)\b/i,
];

const LOW_SALIENCE_PATTERNS = [
  /\b(maybe|perhaps|might|could|possibly|sometime|eventually)\b/i,
  /\b(minor|trivial|small|little|slightly)\b/i,
];

/**
 * Extract entities and topics from raw text without an LLM.
 * Uses capitalization heuristics, pattern matching, and simple NLP.
 */
export function extract(text: string): ExtractionResult {
  const entities = extractEntities(text);
  const topics = extractTopics(text);
  const suggestedSalience = estimateSalience(text);

  return { entities, topics, suggestedSalience };
}

function extractEntities(text: string): string[] {
  const entities = new Set<string>();

  // 1. Capitalized words/phrases (likely proper nouns)
  //    Match sequences of capitalized words, including camelCase/PascalCase compounds
  const capitalizedPattern = /\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\b/g;
  let match;
  while ((match = capitalizedPattern.exec(text)) !== null) {
    const candidate = match[1];
    // Skip if it's at the start of a sentence (check if preceded by . or start of string)
    const before = text.substring(Math.max(0, match.index - 3), match.index).trim();
    const isStartOfSentence = before === '' || before.endsWith('.') || before.endsWith('!') || before.endsWith('?') || before.endsWith('\n');

    // If it's a single word at the start of a sentence, skip (probably just capitalized normally)
    // Exception: don't skip after colons — those are labels/prefixes, not sentence boundaries
    if (isStartOfSentence && !candidate.includes(' ')) continue;

    // Skip common words that happen to be capitalized
    if (STOP_WORDS.has(candidate.toLowerCase())) continue;
    if (candidate.length < 2) continue;
    // Skip label prefixes commonly used in structured text
    if (['Correction', 'Shipped', 'Decision', 'Bug', 'Fix', 'Note', 'Todo',
         'Updated', 'Added', 'Removed', 'Changed', 'Status', 'Version',
         'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
        ].includes(candidate)) continue;

    entities.add(candidate);
  }

  // 2. All-caps acronyms (API, SDK, LLM, etc.)
  const acronymPattern = /\b([A-Z]{2,6})\b/g;
  while ((match = acronymPattern.exec(text)) !== null) {
    const acr = match[1];
    // Skip common non-entity acronyms and label words
    if (['OK', 'AM', 'PM', 'US', 'ID', 'VS', 'OR', 'IT', 'IF', 'DO', 'NO',
         'BUG', 'FIX', 'NOTE', 'TODO', 'NEW', 'OLD', 'URL', 'THE'].includes(acr)) continue;
    entities.add(acr);
  }

  // 3. Technology names (often lowercase in text)
  const techPattern = /\b(typescript|javascript|python|react|vue|angular|node\.?js|sqlite|postgres|redis|docker|vercel|aws|gcp|anthropic|openai|langchain|crewai|engram|gemini|github|npm)\b/gi;
  while ((match = techPattern.exec(text)) !== null) {
    // Normalize casing
    const tech = match[1];
    const normalized = tech.charAt(0).toUpperCase() + tech.slice(1).toLowerCase();
    entities.add(normalized);
  }

  return [...entities].slice(0, 15); // Cap at 15 entities
}

function extractTopics(text: string): string[] {
  const topics: string[] = [];

  for (const [topic, pattern] of Object.entries(TOPIC_PATTERNS)) {
    if (pattern.test(text)) {
      topics.push(topic);
    }
  }

  return topics.slice(0, 8); // Cap at 8 topics
}

function estimateSalience(text: string): number {
  let salience = 0.35; // Default baseline — most memories are normal importance

  // Count how many high-salience signals are present (diminishing returns)
  let highSignals = 0;
  for (const pattern of HIGH_SALIENCE_PATTERNS) {
    if (pattern.test(text)) highSignals++;
  }
  // First signal: +0.15, second: +0.10, third+: +0.05 each (diminishing)
  if (highSignals >= 1) salience += 0.15;
  if (highSignals >= 2) salience += 0.10;
  if (highSignals >= 3) salience += 0.05 * Math.min(highSignals - 2, 3);

  // Reduce for low-salience signals
  for (const pattern of LOW_SALIENCE_PATTERNS) {
    if (pattern.test(text)) {
      salience -= 0.1;
    }
  }

  // Longer, more substantial content gets a small boost
  if (text.length > 300) salience += 0.05;
  if (text.length > 600) salience += 0.05;

  // Clamp to [0.1, 1.0]
  return Math.max(0.1, Math.min(1.0, salience));
}
