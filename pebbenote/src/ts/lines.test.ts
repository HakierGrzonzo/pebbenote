import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { deleteLines, rebaseDeletes } from "./lines";

describe("deleteLines", () => {
  it("takes each index after the deletes before it", () => {
    const { content, deleted } = deleteLines("a\nb\nc\nd", [1, 1]);

    assert.equal(content, "a\nd");
    assert.deepEqual(deleted, [
      { text: "b", index: 1 },
      { text: "c", index: 2 },
    ]);
  });

  it("skips indexes past the end", () => {
    assert.equal(deleteLines("a\nb", [5]).content, "a\nb");
  });
});

describe("rebaseDeletes", () => {
  it("deletes the moved line closest to its old place", () => {
    const deleted = [{ text: "x", index: 3 }];

    assert.equal(rebaseDeletes("x\nnew\na\nb\nx", deleted), "x\nnew\na\nb");
  });

  it("leaves changed lines alone", () => {
    assert.equal(rebaseDeletes("a\nB", [{ text: "b", index: 1 }]), "a\nB");
  });
});
