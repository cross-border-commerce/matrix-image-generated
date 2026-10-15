export type Photo = {
  name: string;
};

export type ProductGroup = {
  id: string;
  photos: Photo[];
};

export type Pair = {
  model: Photo;
  group: ProductGroup;
};

const VIEW_TOKENS = new Set([
  "正面",
  "背面",
  "侧面",
  "细节",
  "局部",
  "front",
  "back",
  "side",
  "detail",
]);

export function fileStem(filename: string): string {
  const base = filename.split(/[/\\]/).pop() ?? filename;
  const index = base.lastIndexOf(".");
  return index > 0 ? base.slice(0, index) : base;
}

export function canonicalProductId(filename: string): string {
  const stem = fileStem(filename);
  const parts = stem.split(/[-_\s]+/).filter(Boolean);
  const kept = parts.filter((part) => !VIEW_TOKENS.has(part.toLowerCase()));
  return kept.length ? kept.join("-") : "";
}

function logicalParent(name: string): string | null {
  const normalized = name.replaceAll("\\", "/");
  const index = normalized.lastIndexOf("/");
  if (index <= 0) {
    return null;
  }
  return normalized.slice(0, index);
}

export function groupProducts(products: Photo[]): ProductGroup[] {
  const n = products.length;
  const parentOf = Array.from({ length: n }, (_, i) => i);

  const find = (i: number): number => {
    let current = i;
    while (parentOf[current] !== current) {
      parentOf[current] = parentOf[parentOf[current]];
      current = parentOf[current];
    }
    return current;
  };

  const union = (i: number, j: number): void => {
    const ri = find(i);
    const rj = find(j);
    if (ri !== rj) {
      parentOf[rj] = ri;
    }
  };

  const stems = products.map((item) => canonicalProductId(item.name));
  const parents = products.map((item) => logicalParent(item.name));

  const stemIndex = new Map<string, number>();
  for (let i = 0; i < n; i += 1) {
    const stem = stems[i];
    if (stem) {
      const existing = stemIndex.get(stem);
      if (existing !== undefined) {
        union(existing, i);
      } else {
        stemIndex.set(stem, i);
      }
    }
  }

  const dirFiles = new Map<string, number[]>();
  for (let i = 0; i < n; i += 1) {
    const parent = parents[i];
    if (parent !== null) {
      const list = dirFiles.get(parent);
      if (list) {
        list.push(i);
      } else {
        dirFiles.set(parent, [i]);
      }
    }
  }
  for (const indexes of dirFiles.values()) {
    const uniqueStems = new Set(
      indexes.map((i) => stems[i]).filter((stem) => stem.length > 0),
    );
    if (uniqueStems.size <= 1) {
      for (const other of indexes.slice(1)) {
        union(indexes[0], other);
      }
    }
  }

  const buckets = new Map<number, number[]>();
  for (let i = 0; i < n; i += 1) {
    const root = find(i);
    const list = buckets.get(root);
    if (list) {
      list.push(i);
    } else {
      buckets.set(root, [i]);
    }
  }

  const groups: ProductGroup[] = [];
  for (const indexes of buckets.values()) {
    const first = products[indexes[0]];
    const stem = stems[indexes[0]];
    const parent = parents[indexes[0]];
    groups.push({
      id: stem || parent || fileStem(first.name),
      photos: indexes.map((i) => products[i]),
    });
  }
  return groups;
}

export function pairModels(
  models: Photo[],
  groups: ProductGroup[],
  assignments: Record<string, string> | null = null,
): Pair[] {
  if (!models.length || !groups.length) {
    return [];
  }

  const byId = new Map(groups.map((group) => [group.id, group]));
  return models.map((model, i) => {
    let group = groups[i % groups.length];
    if (assignments) {
      const assigned = assignments[model.name];
      if (assigned !== undefined) {
        const found = byId.get(assigned);
        if (found) {
          group = found;
        }
      }
    }
    return { model, group };
  });
}

export function outputCount(modelCount: number, logoCount: number): number {
  return modelCount * logoCount;
}
