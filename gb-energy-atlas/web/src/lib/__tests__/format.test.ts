import { describe, expect, it } from "vitest";
import { csvEscape, fmtDate, fmtGw, fmtMw, fmtMwh, fmtNum, NOT_IDENTIFIED, safeUrl, UNKNOWN } from "../format";

describe("csvEscape", () => {
  it("neutralises spreadsheet formula injection from source text", () => {
    for (const evil of ["=HYPERLINK(\"http://x\")", "+1+1", "-2+3", "@SUM(A1)", "\t=1", "\r=1"]) {
      expect(csvEscape(evil).replace(/^"/, "")).toMatch(/^'/);
    }
  });
  it("quotes fields with commas, quotes and newlines", () => {
    expect(csvEscape("a,b")).toBe('"a,b"');
    expect(csvEscape('say "hi"')).toBe('"say ""hi"""');
    expect(csvEscape("line1\nline2")).toBe('"line1\nline2"');
  });
  it("renders null/undefined as empty and dates as ISO dates", () => {
    expect(csvEscape(null)).toBe("");
    expect(csvEscape(undefined)).toBe("");
    expect(csvEscape(new Date("2026-08-03T10:00:00Z"))).toBe("2026-08-03");
    expect(csvEscape(0)).toBe("0");
  });
});

describe("safeUrl", () => {
  it("only lets http(s) URLs through to hrefs", () => {
    expect(safeUrl("https://www.gov.uk/x")).toBe("https://www.gov.uk/x");
    expect(safeUrl("http://example.org")).toBe("http://example.org/");
    for (const bad of ["javascript:alert(1)", "data:text/html,<script>", "file:///etc/passwd", "vbscript:x", "//evil.example", "not a url", "", null, undefined]) {
      expect(safeUrl(bad as string | null | undefined)).toBeNull();
    }
  });
});

describe("number and date formatting", () => {
  it("never turns a missing value into a number", () => {
    expect(fmtNum(null)).toBe("—");
    expect(fmtNum("")).toBe("—");
    expect(fmtNum("abc")).toBe("—");
    expect(fmtMw(null)).toBe("—");
    expect(fmtMwh(undefined)).toBe("—");
    expect(fmtDate(null)).toBe("—");
    expect(fmtDate("not a date")).toBe("—");
  });
  it("keeps MW and MWh distinct and formats GW", () => {
    expect(fmtMw(322)).toBe("322 MW");
    expect(fmtMw(2.3)).toBe("2.3 MW");
    expect(fmtMwh(100)).toBe("100 MWh");
    expect(fmtGw(1200)).toBe("1.2 GW");
    expect(fmtGw(450)).toBe("450 MW");
  });
  it("treats numeric strings from the database (numeric -> text) as numbers", () => {
    expect(fmtMw("12.5")).toBe("12.5 MW");
  });
  it("formats dates in UTC so the day never shifts", () => {
    expect(fmtDate("2026-01-01")).toBe("01 January 2026");
  });
  it("uses the specified wording for unknowns", () => {
    expect(UNKNOWN).toBe("Unknown");
    expect(NOT_IDENTIFIED).toBe("Not publicly identified");
  });
});
