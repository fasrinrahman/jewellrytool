import type { MeshData } from "./types";

export interface BufferData {
  positions: Float32Array;
  indices: Uint32Array;
}

/** Check the server's mesh and convert it to typed arrays for three.js. */
export function toBufferData(mesh: MeshData): BufferData {
  const { vertices, indices } = mesh;
  if (vertices.length === 0 || vertices.length % 3 !== 0) {
    throw new Error("The mesh has no vertices or a broken vertex list.");
  }
  if (indices.length === 0 || indices.length % 3 !== 0) {
    throw new Error("The mesh has no triangles or a broken triangle list.");
  }
  const count = vertices.length / 3;
  for (const i of indices) {
    if (!Number.isInteger(i) || i < 0 || i >= count) {
      throw new Error("The mesh refers to a vertex that does not exist.");
    }
  }
  return { positions: new Float32Array(vertices), indices: new Uint32Array(indices) };
}
