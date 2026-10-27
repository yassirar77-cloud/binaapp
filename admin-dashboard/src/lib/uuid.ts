const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

/** True when the value is a UUID string (safe to pass to a uuid column filter). */
export function isUuid(value: unknown): value is string {
  return typeof value === 'string' && UUID_RE.test(value)
}

/** Unique UUID values from a list that may contain nulls or non-UUID text ids. */
export function uniqueUuids(values: unknown[]): string[] {
  return [...new Set(values.filter(isUuid))]
}
