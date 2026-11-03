import { describe, expect, it } from "vitest";
import {
  markersInDocument,
  plainToRich,
  suggestTemplateCode,
} from "@documents/templateContent.js";

describe("contenido de plantillas ricas", () => {
  it("sugiere un código estable y compatible desde el nombre", () => {
    expect(suggestTemplateCode("Constancia de inscripción 2026")).toBe(
      "CONSTANCIA_DE_INSCRIPCION_2026"
    );
  });

  it("convierte texto plano sin perder párrafos y detecta etiquetas", () => {
    const document = plainToRich("Hola {{student.full_name}}\nSegundo párrafo");
    expect(document.content).toHaveLength(2);
    expect(markersInDocument(document)).toEqual(["student.full_name"]);
  });
});
