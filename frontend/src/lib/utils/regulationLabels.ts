/** `RBI-4.1` -> `RBI section 4.1`, in words a compliance officer uses. */
export function regulationLabel(ruleId: string): string {
  return ruleId.replace(/^RBI-/, 'RBI section ');
}

const VERSION_STAMP = /(\d{4})(\d{2})(\d{2})T\d{6}(?:\d{6})?Z$/;

/** `RBI-4.1-20261007T120000Z` -> `7 Oct 2026`, or null if there is no timestamp. */
export function versionDate(versionId: string): string | null {
  const match = VERSION_STAMP.exec(versionId);
  if (!match) return null;
  const [, year, month, day] = match;
  const date = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  });
}

/** `RBI section 4.1, version of 7 Oct 2026`: the regulation version, in plain words. */
export function regulationVersionLabel(ruleId: string, versionId: string): string {
  const date = versionDate(versionId);
  return date
    ? `${regulationLabel(ruleId)}, version of ${date}`
    : regulationLabel(ruleId);
}
