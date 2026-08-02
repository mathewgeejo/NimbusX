export function isValidIanaTimeZone(value: string): boolean {
  try {
    Intl.DateTimeFormat(undefined, { timeZone: value }).format();
    return true;
  } catch {
    return false;
  }
}

function zoneOffsetMilliseconds(date: Date, timeZone: string): number {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23"
  }).formatToParts(date);

  const values: Record<string, string> = {};
  for (const part of parts) {
    if (part.type !== "literal") {
      values[part.type] = part.value;
    }
  }

  const projectedUtc = Date.UTC(
    Number(values.year),
    Number(values.month) - 1,
    Number(values.day),
    Number(values.hour),
    Number(values.minute),
    Number(values.second)
  );
  return projectedUtc - date.getTime();
}

function localTimestampInZone(date: Date, timeZone: string): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23"
  }).formatToParts(date);
  const values: Record<string, string> = {};
  for (const part of parts) {
    if (part.type !== "literal") {
      values[part.type] = part.value;
    }
  }
  return (
    values.year +
    "-" +
    values.month +
    "-" +
    values.day +
    "T" +
    values.hour +
    ":" +
    values.minute +
    ":" +
    values.second
  );
}

/**
 * Converts a date-time entered in a site's IANA time zone into an offset-aware
 * instant for the API. The form deliberately asks for a named zone, rather
 * than silently interpreting site dates in the analyst's browser zone.
 */
export function localDateTimeInZoneToIso(value: string, timeZone: string): string {
  const match = value.match(
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/
  );
  if (!match) {
    throw new Error("Enter a complete local date and time.");
  }

  const tentativeUtc = Date.UTC(
    Number(match[1]),
    Number(match[2]) - 1,
    Number(match[3]),
    Number(match[4]),
    Number(match[5]),
    Number(match[6] ?? "0")
  );
  const tentativeDate = new Date(tentativeUtc);
  let instant = tentativeUtc - zoneOffsetMilliseconds(tentativeDate, timeZone);
  instant = tentativeUtc - zoneOffsetMilliseconds(new Date(instant), timeZone);
  const expectedLocalTime =
    match[1] + "-" + match[2] + "-" + match[3] + "T" + match[4] + ":" + match[5] + ":" + (match[6] ?? "00");

  const matchingInstants = new Set<number>();
  for (let offset = -7_200_000; offset <= 7_200_000; offset += 900_000) {
    const candidate = instant + offset;
    if (localTimestampInZone(new Date(candidate), timeZone) === expectedLocalTime) {
      matchingInstants.add(candidate);
    }
  }

  if (matchingInstants.size === 0) {
    throw new Error("This local time does not exist in the selected time zone. Choose a valid time.");
  }
  if (matchingInstants.size > 1) {
    throw new Error(
      "This local time is ambiguous in the selected time zone. Choose a time outside the daylight-saving transition."
    );
  }

  return new Date(instant).toISOString();
}

/** Formats a source calendar day without converting it through the browser's zone. */
export function displayCalendarDate(value?: string | null): string {
  if (!value) {
    return "Not available";
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return value;
  }

  const date = new Date(value + "T00:00:00.000Z");
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeZone: "UTC"
  }).format(date);
}

export function displayDateTime(value?: string | null): string {
  if (!value) {
    return "Not available";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
    timeZoneName: "short"
  }).format(date);
}
