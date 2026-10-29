import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, buildDesign, exportDesign, fetchRules, fetchSizes } from "./api";
import type { RingParams } from "./types";

const P: RingParams = {
  metal: "silver_925", ring_size_mm: 17.3, band_width_mm: 3, band_thickness_mm: 1.8,
  stone_shape: "round", stone_size_mm: 6, prong_count: 4, prong_diameter_mm: 1, finish: "polished",
};

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

afterEach(() => vi.unstubAllGlobals());

describe("api client", () => {
  it("buildDesign posts the parameters as JSON", async () => {
    const fetchMock = vi.fn().mockResolvedValue(json({ exportable: true }));
    vi.stubGlobal("fetch", fetchMock);
    const out = await buildDesign(P);
    expect(out).toEqual({ exportable: true });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/designs\/build$/);
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual(P);
  });

  it("fetchSizes sends the system and value as a query string", async () => {
    const fetchMock = vi.fn().mockResolvedValue(json({ mm: 17.32, us: 7, uk: "N\u00bd", eu: 54 }));
    vi.stubGlobal("fetch", fetchMock);
    await fetchSizes("uk", "N 1/2");
    const url = String(fetchMock.mock.calls[0][0]);
    expect(url).toMatch(/\/sizes\?/);
    expect(url).toContain("system=uk");
    expect(url).toContain("value=N+1%2F2");
  });

  it("turns a plain 422 message into an ApiError the user can read", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({ detail: "That size is outside the supported range." }, 422)));
    await expect(fetchSizes("us", "99")).rejects.toMatchObject({
      name: "ApiError", status: 422, message: "That size is outside the supported range.",
    });
  });

  it("export refusal carries the report (NFR-01)", async () => {
    const report = { exportable: false, results: [] };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      json({ detail: { message: "Export refused: a check failed.", report } }, 422)));
    const err = await exportDesign(P).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toBe("Export refused: a check failed.");
    expect(err.report).toEqual(report);
  });

  it("export success returns the zip bytes as a blob", async () => {
    const zipMagic = new Uint8Array([0x50, 0x4b, 0x03, 0x04]); // "PK" header of a zip file
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(zipMagic, { status: 200 })));
    const blob = await exportDesign(P);
    expect(blob.size).toBe(4);
  });

  it("explains when the server cannot be reached", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(fetchRules()).rejects.toMatchObject({ status: 0, message: expect.stringContaining("Could not reach") });
  });

  it("names the field when the server rejects a value, without needing the value itself", async () => {
    const detail = [{ loc: ["body", "band_thickness_mm"], msg: "Input should be less than or equal to 100", type: "less_than_equal" }];
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({ detail }, 422)));
    await expect(buildDesign(P)).rejects.toMatchObject({
      message: "Band thickness is not a valid value. Input should be less than or equal to 100",
    });
  });

  it("falls back to a general message for an unknown field", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({ detail: [{ loc: ["body"], msg: "bad" }] }, 422)));
    await expect(buildDesign(P)).rejects.toMatchObject({ message: "Some values are not valid." });
  });

  it("handles a non-JSON server error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("oops", { status: 500 })));
    await expect(buildDesign(P)).rejects.toMatchObject({ status: 500, message: expect.stringContaining("500") });
  });
});
