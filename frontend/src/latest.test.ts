import { describe, expect, it } from "vitest";
import { makeLatestGuard } from "./latest";

describe("makeLatestGuard", () => {
  it("only the most recent request counts", () => {
    const g = makeLatestGuard();
    const first = g.next();
    expect(g.isLatest(first)).toBe(true);
    const second = g.next();
    expect(g.isLatest(first)).toBe(false);
    expect(g.isLatest(second)).toBe(true);
  });
});
