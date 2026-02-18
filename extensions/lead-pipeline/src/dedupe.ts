export interface DedupeStore {
  isNew(source: string, sourceItemId: string): boolean;
  markSeen(source: string, sourceItemId: string): void;
  size(): number;
}

export function createDedupeStore(): DedupeStore {
  const seen = new Set<string>();

  function key(source: string, sourceItemId: string): string {
    return `${source}:${sourceItemId}`;
  }

  return {
    isNew(source, sourceItemId) {
      return !seen.has(key(source, sourceItemId));
    },
    markSeen(source, sourceItemId) {
      seen.add(key(source, sourceItemId));
    },
    size() {
      return seen.size;
    },
  };
}
