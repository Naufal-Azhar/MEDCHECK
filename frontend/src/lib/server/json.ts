/** JSON.parse alone silently overwrites duplicate keys, including escaped spellings. */
export function parseUniqueJson(raw: string): unknown {
  if (typeof raw !== 'string') throw new Error('Invalid JSON');
  // Let the native parser enforce JSON syntax before inspecting object member names.
  const value: unknown = JSON.parse(raw);
  const tokens = raw.match(/"(?:[^"\\]|\\[\s\S])*"|[{}\[\],:]|[^\s{}\[\],:]+/g) ?? [];
  let index = 0;
  function visit(): void {
    const token = tokens[index++];
    if (token === '{') {
      const keys = new Set<string>();
      if (tokens[index] === '}') { index++; return; }
      do {
        const key = JSON.parse(tokens[index++]) as string;
        if (keys.has(key)) throw new Error('Duplicate JSON key');
        keys.add(key);
        index++; // colon; syntax has already been checked
        visit();
      } while (tokens[index++] === ',');
    } else if (token === '[') {
      if (tokens[index] === ']') { index++; return; }
      do { visit(); } while (tokens[index++] === ',');
    }
  }
  visit();
  return value;
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function hasExactKeys(value: Record<string, unknown>, keys: readonly string[]): boolean {
  const actual = Object.keys(value);
  return actual.length === keys.length && keys.every((key) => Object.hasOwn(value, key));
}
