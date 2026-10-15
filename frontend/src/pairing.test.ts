import { describe, expect, it } from "vitest";
import { groupModels, groupProducts, outputCount, pairModels } from "./pairing";

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

describe("groupModels", () => {
  it("uses each subdirectory as a group", () => {
    const groups = groupModels([
      { name: "reference/model1/a1.jpg" },
      { name: "reference/model1/a2.jpg" },
      { name: "reference/model2/b1.jpg" },
    ]);
    expect(groups.map((group) => group.id)).toEqual(["model1", "model2"]);
    expect(groups[0].photos.map((photo) => photo.name)).toEqual([
      "reference/model1/a1.jpg",
      "reference/model1/a2.jpg",
    ]);
  });

  it("treats a flat folder of images as one group", () => {
    const groups = groupModels([{ name: "m1.png" }, { name: "m2.png" }]);
    expect(groups.map((group) => group.id)).toEqual(["models"]);
    expect(groups[0].photos.map((photo) => photo.name)).toEqual([
      "m1.png",
      "m2.png",
    ]);
  });

  it("treats images that share one parent folder as one group", () => {
    const groups = groupModels([
      { name: "reference/m1.png" },
      { name: "reference/m2.png" },
    ]);
    expect(groups.map((group) => group.id)).toEqual(["reference"]);
  });
});

describe("pairModels", () => {
  it("cycles products across photos in a group", () => {
    const pairs = pairModels(
      [{ name: "a1.jpg" }, { name: "a2.jpg" }, { name: "a3.jpg" }],
      [{ id: "A", photos: [] }, { id: "B", photos: [] }],
    );
    expect(pairs.map((pair) => [pair.model.name, pair.group.id])).toEqual([
      ["a1.jpg", "A"],
      ["a2.jpg", "B"],
      ["a3.jpg", "A"],
    ]);
  });

  it("keeps one row per photo when there are extra products", () => {
    const pairs = pairModels(
      [{ name: "a1.jpg" }, { name: "a2.jpg" }],
      [{ id: "A", photos: [] }, { id: "B", photos: [] }, { id: "C", photos: [] }],
    );
    expect(pairs.map((pair) => [pair.model.name, pair.group.id])).toEqual([
      ["a1.jpg", "A"],
      ["a2.jpg", "B"],
    ]);
  });

  it("uses row assignments", () => {
    const pairs = pairModels(
      [{ name: "a1.jpg" }, { name: "a2.jpg" }],
      [{ id: "A", photos: [] }, { id: "B", photos: [] }, { id: "C", photos: [] }],
      { "0": "C" },
    );
    expect(pairs.map((pair) => [pair.model.name, pair.group.id])).toEqual([
      ["a1.jpg", "C"],
      ["a2.jpg", "B"],
    ]);
  });
});

describe("outputCount", () => {
  it("counts photos in the model group assigned to each logo", () => {
    const modelGroups = [
      { id: "a", photos: [{ name: "a1.jpg" }, { name: "a2.jpg" }] },
      { id: "b", photos: [{ name: "b1.jpg" }] },
    ];
    expect(outputCount(modelGroups, 2)).toBe(3);
    expect(outputCount(modelGroups, 3)).toBe(5);
  });
});
