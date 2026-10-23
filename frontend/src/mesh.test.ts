import { describe, expect, it } from "vitest";
import { toBufferData } from "./mesh";

const tri = { vertices: [0, 0, 0, 1, 0, 0, 0, 1, 0], indices: [0, 1, 2] };

describe("toBufferData (FR-11)", () => {
  it("converts a valid mesh to typed arrays", () => {
    const d = toBufferData(tri);
    expect(d.positions).toBeInstanceOf(Float32Array);
    expect(d.indices).toBeInstanceOf(Uint32Array);
    expect(Array.from(d.positions)).toEqual(tri.vertices);
    expect(Array.from(d.indices)).toEqual([0, 1, 2]);
  });

  it("rejects an empty or broken vertex list", () => {
    expect(() => toBufferData({ vertices: [], indices: [0, 1, 2] })).toThrow(/vertices/);
    expect(() => toBufferData({ vertices: [0, 0], indices: [0, 1, 2] })).toThrow(/vertices/);
  });

  it("rejects an empty or broken triangle list", () => {
    expect(() => toBufferData({ vertices: tri.vertices, indices: [] })).toThrow(/triangles/);
    expect(() => toBufferData({ vertices: tri.vertices, indices: [0, 1] })).toThrow(/triangles/);
  });

  it("rejects an index that points outside the vertex list", () => {
    expect(() => toBufferData({ vertices: tri.vertices, indices: [0, 1, 3] })).toThrow(/does not exist/);
    expect(() => toBufferData({ vertices: tri.vertices, indices: [0, 1, -1] })).toThrow(/does not exist/);
    expect(() => toBufferData({ vertices: tri.vertices, indices: [0, 1, 1.5] })).toThrow(/does not exist/);
  });
});
