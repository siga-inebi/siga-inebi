export const emptyRichDocument = () => ({
  type: "doc",
  version: 1,
  content: [
    { type: "paragraph", align: "left", content: [{ type: "text", text: "" }] },
  ],
});

export function plainToRich(value = "") {
  return {
    type: "doc",
    version: 1,
    content: value.split(/\n+/).map((text) => ({
      type: "paragraph",
      align: "left",
      content: [{ type: "text", text }],
    })),
  };
}

export function suggestTemplateCode(name = "") {
  return name
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 30);
}

export function markersInDocument(document) {
  const text =
    document?.content
      ?.flatMap((block) => block.content ?? [])
      .map((node) => node.text ?? "")
      .join("\n") ?? "";
  return [...text.matchAll(/{{\s*([^{}]+?)\s*}}/g)].map((match) => match[1]);
}
