type Node = string | Node[];

function tokenize(source: string): string[] {
  return source.match(/\(|\)|[^\s()]+/g) ?? [];
}

function parse(tokens: string[]): Node[] | null {
  const stack: Node[][] = [[]];
  for (const token of tokens) {
    if (token === '(') {
      stack.push([]);
    } else if (token === ')') {
      const done = stack.pop();
      const parent = stack[stack.length - 1];
      if (!done || !parent) return null;
      parent.push(done);
    } else {
      stack[stack.length - 1].push(token);
    }
  }
  return stack.length === 1 ? stack[0] : null;
}

const COMPARISONS: Record<string, string> = {
  '=': 'equals',
  '>': 'is greater than',
  '<': 'is less than',
  '>=': 'is at least',
  '<=': 'is at most',
};

function variableName(symbol: string): string {
  const base = symbol.replace(/_weight$/, '').replace(/_/g, ' ');
  return symbol.endsWith('_weight') ? `the weight of ${base}` : base;
}

function render(node: Node): string | null {
  if (typeof node === 'string') {
    return /^-?\d+(\.\d+)?$/.test(node) ? node : variableName(node);
  }
  const [head, ...args] = node;
  if (typeof head !== 'string') return null;
  const parts = args.map(render);
  if (parts.some((p) => p === null)) return null;
  const text = parts as string[];
  if (head in COMPARISONS && text.length === 2) {
    return `${text[0]} ${COMPARISONS[head]} ${text[1]}`;
  }
  switch (head) {
    case 'and':
      return text.map((t) => `(${t})`).join(' and ');
    case 'or':
      return text.map((t) => `(${t})`).join(' or ');
    case 'not':
      return text.length === 1 ? `it is not true that ${text[0]}` : null;
    case '=>':
      return text.length === 2 ? `if ${text[0]}, then ${text[1]}` : null;
    case '/':
      return text.length === 2 ? String(Number(text[0]) / Number(text[1])) : null;
    case '+':
    case '-':
    case '*':
      return text.length >= 2 ? text.join(` ${head} `) : null;
    default:
      return null;
  }
}

/** The exact condition of a rule in plain words, built by rule, not by an LLM,
 * so a compliance officer can check it against the summary. Returns null if the
 * rule uses something this cannot express; callers must not show raw logic. */
export function readableRule(formula: string): string | null {
  const tree = parse(tokenize(formula));
  if (!tree) return null;
  const sentences: string[] = [];
  for (const node of tree) {
    if (!Array.isArray(node) || typeof node[0] !== 'string') return null;
    if (node[0].startsWith('declare-')) continue;
    if (node[0] !== 'assert' || node.length !== 2) return null;
    const text = render(node[1]);
    if (text === null) return null;
    sentences.push(text);
  }
  if (sentences.length === 0) return null;
  const joined = sentences.join(', and ');
  return joined.charAt(0).toUpperCase() + joined.slice(1) + '.';
}
