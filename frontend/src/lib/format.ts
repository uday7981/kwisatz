export function pct(v: number, digits = 0): string {
  return `${(v * 100).toFixed(digits)}%`;
}

export function score(v: number): string {
  return v.toFixed(2);
}

export function categoryLabel(cat: string): string {
  return cat.replace(/_/g, " ");
}

export function diagnosisLabel(code: string): string {
  switch (code) {
    case "D1": return "Reseller invasion";
    case "D2": return "Stockout-prone";
    case "D3": return "Weak converter";
    case "D4": return "Price erosion";
    case "D5": return "Under-advertised riser";
    case "D6": return "Healthy riser";
    default: return code;
  }
}

export function angleLabel(a: string): string {
  return a.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
