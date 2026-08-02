export function titleCase(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function displayValue(value: string | number | null | undefined, unit?: string | null): string {
  if (value === null || value === undefined || value === "") {
    return "Not available";
  }

  return String(value) + (unit ? " " + unit : "");
}

export function displayLikelihood(
  likelihood?: number | null,
  unit: "%" | "probability" = "probability"
): string {
  if (likelihood === null || likelihood === undefined) {
    return "Not available";
  }

  if (unit === "probability") {
    return (likelihood * 100).toFixed(1) + "%";
  }

  return likelihood.toFixed(1) + "%";
}
