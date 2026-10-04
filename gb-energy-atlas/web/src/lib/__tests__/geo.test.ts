import { describe, expect, it } from "vitest";
import { bearingDeg, bngToWgs84, circlePolygon, compass, gridRefToBng, haversineM, parseCoordinateInput, wgs84ToBng } from "../geo";

describe("OS grid references", () => {
  it("converts 100 m, 1 km and 10 km references to the south-west corner", () => {
    expect(gridRefToBng("NT 730 745")).toEqual({ e: 373000, n: 674500, res: 100 });
    expect(gridRefToBng("TQ3080")).toEqual({ e: 530000, n: 180000, res: 1000 });
    expect(gridRefToBng("su 387 148")).toMatchObject({ e: 438700, n: 114800 });
  });
  it("rejects malformed references, odd digit counts and the letter I", () => {
    expect(gridRefToBng("IO1234")).toBeNull();
    expect(gridRefToBng("NT123")).toBeNull();
    expect(gridRefToBng("hello")).toBeNull();
    expect(gridRefToBng("")).toBeNull();
  });
});

describe("British National Grid <-> WGS84", () => {
  it("round-trips within a metre", () => {
    const { lon, lat } = bngToWgs84(373000, 674500);
    const back = wgs84ToBng(lon, lat);
    expect(Math.abs(back.e - 373000)).toBeLessThan(1);
    expect(Math.abs(back.n - 674500)).toBeLessThan(1);
  });
  it("places Edinburgh-area grid squares in the right place", () => {
    const { lon, lat } = bngToWgs84(325000, 673000);
    expect(lat).toBeGreaterThan(55.9);
    expect(lat).toBeLessThan(56.0);
    expect(lon).toBeGreaterThan(-3.3);
    expect(lon).toBeLessThan(-3.1);
  });
});

describe("distance and bearing", () => {
  it("London to Edinburgh is roughly 534 km, bearing roughly north", () => {
    const d = haversineM(51.5074, -0.1278, 55.9533, -3.1883);
    expect(d / 1000).toBeGreaterThan(525);
    expect(d / 1000).toBeLessThan(545);
    const b = bearingDeg(51.5074, -0.1278, 55.9533, -3.1883);
    expect(["N", "NNW"]).toContain(compass(b));
  });
  it("compass points wrap correctly", () => {
    expect(compass(0)).toBe("N");
    expect(compass(359)).toBe("N");
    expect(compass(90)).toBe("E");
    expect(compass(225)).toBe("SW");
  });
});

describe("parseCoordinateInput", () => {
  it("understands lat/lon, easting/northing and grid references", () => {
    expect(parseCoordinateInput("55.68, -4.28")).toMatchObject({ kind: "WGS84 lat, lon", lat: 55.68, lon: -4.28 });
    expect(parseCoordinateInput("373000 674500")?.kind).toBe("British National Grid E, N");
    expect(parseCoordinateInput("NT 730 745")?.kind).toBe("OS grid reference");
  });
  it("refuses coordinates outside Great Britain's extent and free text", () => {
    expect(parseCoordinateInput("10, 10")).toBeNull();
    expect(parseCoordinateInput("40.7, -74.0")).toBeNull();
    expect(parseCoordinateInput("Glasgow")).toBeNull();
  });
});

describe("circlePolygon", () => {
  it("is a closed ring whose vertices are at the requested radius", () => {
    const f = circlePolygon(55.9, -3.2, 5000);
    const ring = f.geometry.coordinates[0];
    expect(ring[0]).toEqual(ring[ring.length - 1]);
    for (const [lon, lat] of ring) expect(Math.abs(haversineM(55.9, -3.2, lat, lon) - 5000)).toBeLessThan(5);
  });
});
