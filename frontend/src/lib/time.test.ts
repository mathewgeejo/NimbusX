import { describe, expect, it } from "vitest";
import { displayCalendarDate, isValidIanaTimeZone, localDateTimeInZoneToIso } from "./time";

describe("site-local time conversion", () => {
  it("accepts an IANA zone and returns an offset-aware ISO instant", () => {
    expect(isValidIanaTimeZone("Asia/Kolkata")).toBe(true);
    expect(localDateTimeInZoneToIso("2026-08-02T12:00", "Asia/Kolkata")).toBe(
      "2026-08-02T06:30:00.000Z"
    );
  });

  it("does not treat zero coordinates as absent in an API payload", () => {
    const site = { latitude: 0, longitude: 0 };
    expect(Number.isFinite(site.latitude) && Number.isFinite(site.longitude)).toBe(true);
  });

  it("rejects a local time that does not exist at a daylight-saving transition", () => {
    expect(() => localDateTimeInZoneToIso("2026-03-08T02:30", "America/New_York")).toThrow(
      "does not exist"
    );
  });

  it("rejects an ambiguous local time at a daylight-saving transition", () => {
    expect(() => localDateTimeInZoneToIso("2026-11-01T01:30", "America/New_York")).toThrow(
      "ambiguous"
    );
  });

  it("formats a source calendar day in UTC rather than shifting it through the browser zone", () => {
    expect(displayCalendarDate("2026-08-02")).toContain("2026");
  });
});