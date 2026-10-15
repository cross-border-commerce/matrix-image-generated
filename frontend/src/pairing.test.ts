import { describe, expect, it } from "vitest";
import { groupProducts, pairModels } from "./pairing";

describe("groupProducts", () => {
  it("merges files whose stem matches after stripping view words", () => {
    const groups = groupProducts([
      { name: "白色-正面.jpeg" },
      { name: "白色-背面.jpeg" },
      { name: "黑色.jpeg" },
    ]);
    expect(groups.map((group) => group.id)).toEqual(["白色", "黑色"]);
    expect(groups[0].photos.map((photo) => photo.name)).toEqual([
      "白色-正面.jpeg",
      "白色-背面.jpeg",
    ]);
  });

  it("merges english view suffixes", () => {
    const groups = groupProducts([
      { name: "white-front.png" },
      { name: "white-back.png" },
      { name: "navy_side.png" },
      { name: "navy-detail.png" },
    ]);
    expect(groups.map((group) => group.id)).toEqual(["white", "navy"]);
  });

  it("merges files in the same logical directory", () => {
    const groups = groupProducts([
      { name: "white/front.jpeg" },
      { name: "white/back.jpeg" },
      { name: "red.jpeg" },
    ]);
    expect(groups.map((group) => group.id)).toEqual(["white", "red"]);
  });

  it("keeps flat names in one folder as separate products", () => {
    const groups = groupProducts([{ name: "red.png" }, { name: "blue.png" }]);
    expect(groups.map((group) => group.id)).toEqual(["red", "blue"]);
  });

  it("keeps different stems in a shared upload folder separate", () => {
    const groups = groupProducts([
      { name: "fixtures/realshot/white.jpeg" },
      { name: "fixtures/realshot/block.jpeg" },
      { name: "fixtures/realshot/light_gray.jpeg" },
    ]);
    expect(groups.map((group) => group.id)).toEqual([
      "white",
      "block",
      "light-gray",
    ]);
  });
});

describe("pairModels", () => {
  it("pairs by index and cycles products when there are extra models", () => {
    const pairs = pairModels(
      [{ name: "m1" }, { name: "m2" }, { name: "m3" }],
      [{ id: "white", photos: [] }, { id: "black", photos: [] }],
    );
    expect(pairs.map((pair) => [pair.model.name, pair.group.id])).toEqual([
      ["m1", "white"],
      ["m2", "black"],
      ["m3", "white"],
    ]);
  });

  it("keeps one row per reference when there are more products", () => {
    const pairs = pairModels(
      [{ name: "m1" }, { name: "m2" }],
      [
        { id: "white", photos: [] },
        { id: "black", photos: [] },
        { id: "navy", photos: [] },
      ],
      { m1: "navy", m2: "black" },
    );
    expect(pairs.map((pair) => [pair.model.name, pair.group.id])).toEqual([
      ["m1", "navy"],
      ["m2", "black"],
    ]);
  });

  it("uses assignments when models cover every product", () => {
    const pairs = pairModels(
      [{ name: "m1" }, { name: "m2" }],
      [{ id: "white", photos: [] }, { id: "black", photos: [] }],
      { m1: "black", m2: "white" },
    );
    expect(pairs.map((pair) => [pair.model.name, pair.group.id])).toEqual([
      ["m1", "black"],
      ["m2", "white"],
    ]);
  });
});
