/**
 * miniPdf.js — Generador mínimo de PDF en el navegador, sin dependencias.
 *
 * Mismo enfoque que los documentos del backend (`apps/documents/services.py`,
 * `_assemble_pdf`): el PDF se escribe a mano con lo justo — rectángulos,
 * líneas, texto en las fuentes base Helvetica y una imagen JPEG — en lugar de
 * cargar una librería de cientos de KB para dibujar una tabla.
 *
 * Coordenadas en puntos con origen ARRIBA a la izquierda (como en pantalla);
 * la conversión al origen inferior de PDF ocurre aquí. El texto usa
 * WinAnsiEncoding, que cubre el español (tildes, ñ, ü, ¿, ¡).
 */
import { HELVETICA_BOLD_WIDTHS, HELVETICA_WIDTHS } from "./helveticaMetrics.js";

const FONTS = Object.freeze({
  regular: { resource: "F1", base: "Helvetica", widths: HELVETICA_WIDTHS },
  bold: {
    resource: "F2",
    base: "Helvetica-Bold",
    widths: HELVETICA_BOLD_WIDTHS,
  },
  italic: {
    resource: "F3",
    base: "Helvetica-Oblique",
    widths: HELVETICA_WIDTHS,
  },
});

/** Caracteres fuera de Latin-1 que WinAnsi sí tiene, con su byte. */
const WIN_ANSI_EXTRA = Object.freeze({
  "€": 0x80,
  "‚": 0x82,
  "„": 0x84,
  "…": 0x85,
  "•": 0x95,
  "–": 0x96,
  "—": 0x97,
  "‘": 0x91,
  "’": 0x92,
  "“": 0x93,
  "”": 0x94,
});

/** Byte WinAnsi de un carácter; "?" si la codificación no lo tiene. */
function winAnsiByte(char) {
  const extra = WIN_ANSI_EXTRA[char];
  if (extra !== undefined) return extra;
  const code = char.codePointAt(0);
  if (code >= 0x20 && code <= 0x7e) return code;
  if (code >= 0xa0 && code <= 0xff) return code;
  return 0x3f;
}

/** Texto como literal de cadena PDF, solo ASCII (bytes altos en octal). */
function pdfString(text) {
  let out = "(";
  for (const char of String(text)) {
    const byte = winAnsiByte(char);
    if (byte === 0x28 || byte === 0x29 || byte === 0x5c) out += `\\${char}`;
    else if (byte < 0x80) out += String.fromCharCode(byte);
    else out += `\\${byte.toString(8).padStart(3, "0")}`;
  }
  return `${out})`;
}

const num = (value) => {
  const rounded = Math.round(value * 100) / 100;
  return Object.is(rounded, -0) ? "0" : String(rounded);
};

const color = (rgb) => rgb.map((part) => num(part / 255)).join(" ");

const encoder = new TextEncoder();
const latin1 = (text) => {
  const bytes = new Uint8Array(text.length);
  for (let index = 0; index < text.length; index += 1) {
    bytes[index] = text.charCodeAt(index) & 0xff;
  }
  return bytes;
};

/**
 * Comprime con Flate si el navegador tiene CompressionStream (formato zlib, el
 * que espera /FlateDecode). Si no lo tiene o falla, el flujo va sin comprimir:
 * el PDF sigue siendo válido, solo más grande.
 */
async function deflate(bytes) {
  if (typeof CompressionStream === "undefined") return null;
  try {
    const stream = new Response(bytes).body.pipeThrough(
      new CompressionStream("deflate")
    );
    return new Uint8Array(await new Response(stream).arrayBuffer());
  } catch {
    return null;
  }
}

export class MiniPdf {
  /**
   * @param {{width: number, height: number, title?: string, compress?: boolean}} options
   */
  constructor({ width, height, title = "", compress = true }) {
    this.width = width;
    this.height = height;
    this.title = title;
    this.compress = compress;
    this.pages = [];
    this.current = null;
    this.image = null;
  }

  addPage() {
    this.current = [];
    this.pages.push(this.current);
    return this;
  }

  /** Vuelve a una página ya creada (para numerar al final). 1-based. */
  setPage(number) {
    this.current = this.pages[number - 1];
    return this;
  }

  get pageCount() {
    return this.pages.length;
  }

  #op(command) {
    this.current.push(command);
  }

  #y(top) {
    return this.height - top;
  }

  rect(x, y, width, height, { fill, stroke, lineWidth = 0.5 } = {}) {
    this.#op("q");
    if (fill) this.#op(`${color(fill)} rg`);
    if (stroke) this.#op(`${color(stroke)} RG ${num(lineWidth)} w`);
    this.#op(
      `${num(x)} ${num(this.#y(y + height))} ${num(width)} ${num(height)} re`
    );
    this.#op(fill && stroke ? "B" : fill ? "f" : "S");
    this.#op("Q");
  }

  roundedRect(
    x,
    y,
    width,
    height,
    radius,
    { fill, stroke, lineWidth = 0.5 } = {}
  ) {
    const k = 0.5523 * radius;
    const left = x;
    const right = x + width;
    const top = this.#y(y);
    const bottom = this.#y(y + height);
    const r = radius;
    this.#op("q");
    if (fill) this.#op(`${color(fill)} rg`);
    if (stroke) this.#op(`${color(stroke)} RG ${num(lineWidth)} w`);
    this.#op(
      [
        `${num(left + r)} ${num(top)} m`,
        `${num(right - r)} ${num(top)} l`,
        `${num(right - r + k)} ${num(top)} ${num(right)} ${num(top - r + k)} ${num(right)} ${num(top - r)} c`,
        `${num(right)} ${num(bottom + r)} l`,
        `${num(right)} ${num(bottom + r - k)} ${num(right - r + k)} ${num(bottom)} ${num(right - r)} ${num(bottom)} c`,
        `${num(left + r)} ${num(bottom)} l`,
        `${num(left + r - k)} ${num(bottom)} ${num(left)} ${num(bottom + r - k)} ${num(left)} ${num(bottom + r)} c`,
        `${num(left)} ${num(top - r)} l`,
        `${num(left)} ${num(top - r + k)} ${num(left + r - k)} ${num(top)} ${num(left + r)} ${num(top)} c`,
        "h",
      ].join(" ")
    );
    this.#op(fill && stroke ? "B" : fill ? "f" : "S");
    this.#op("Q");
  }

  line(x1, y1, x2, y2, { stroke, lineWidth = 0.5 }) {
    this.#op(
      `q ${color(stroke)} RG ${num(lineWidth)} w ${num(x1)} ${num(this.#y(y1))} m ${num(x2)} ${num(this.#y(y2))} l S Q`
    );
  }

  /** Ancho en puntos de `text` con la fuente y el tamaño dados. */
  textWidth(text, { font = "regular", size }) {
    const widths = FONTS[font].widths;
    let total = 0;
    for (const char of String(text)) total += widths[winAnsiByte(char)] || 0;
    return (total * size) / 1000;
  }

  /** Parte `text` en líneas que caben en `maxWidth` (por palabras). */
  splitText(text, maxWidth, { font = "regular", size }) {
    const words = String(text ?? "")
      .split(/\s+/)
      .filter(Boolean);
    const lines = [];
    let line = "";
    for (const word of words) {
      const candidate = line ? `${line} ${word}` : word;
      if (!line || this.textWidth(candidate, { font, size }) <= maxWidth) {
        line = candidate;
      } else {
        lines.push(line);
        line = word;
      }
    }
    if (line) lines.push(line);
    return lines.length ? lines : [""];
  }

  /**
   * Texto con su línea base en `y`. `align`: "left" (x es el borde izquierdo),
   * "center" (x es el centro) o "right" (x es el borde derecho).
   */
  text(
    text,
    x,
    y,
    { font = "regular", size, rgb = [0, 0, 0], align = "left" }
  ) {
    const width = align === "left" ? 0 : this.textWidth(text, { font, size });
    const left =
      align === "center" ? x - width / 2 : align === "right" ? x - width : x;
    this.#op(
      `BT /${FONTS[font].resource} ${num(size)} Tf ${color(rgb)} rg ${num(left)} ${num(this.#y(y))} Td ${pdfString(text)} Tj ET`
    );
  }

  /** Registra una imagen JPEG (bytes) para dibujarla con `drawImage`. Una sola por documento. */
  setImage(jpegBytes, pixelWidth, pixelHeight) {
    this.image = { bytes: jpegBytes, width: pixelWidth, height: pixelHeight };
  }

  drawImage(x, y, width, height) {
    if (!this.image) return;
    this.#op(
      `q ${num(width)} 0 0 ${num(height)} ${num(x)} ${num(this.#y(y + height))} cm /Im1 Do Q`
    );
  }

  /** Arma el archivo: objetos, tabla de referencias cruzadas y trailer. */
  async toBlob() {
    const chunks = [];
    const offsets = [];
    let length = 0;
    const push = (bytes) => {
      chunks.push(bytes);
      length += bytes.length;
    };
    const pushText = (text) => push(latin1(text));
    const object = (number, body) => {
      offsets[number] = length;
      pushText(`${number} 0 obj\n${body}\nendobj\n`);
    };
    const streamObject = async (number, dictionary, raw) => {
      const compressed = this.compress ? await deflate(raw) : null;
      const data = compressed ?? raw;
      offsets[number] = length;
      pushText(
        `${number} 0 obj\n<< ${dictionary}${compressed ? " /Filter /FlateDecode" : ""} /Length ${data.length} >>\nstream\n`
      );
      push(data);
      pushText("\nendstream\nendobj\n");
    };

    // 1 catálogo, 2 páginas, 3-5 fuentes, 6 imagen (opcional), 7 info; luego
    // por página: objeto página y su contenido.
    const firstPage = 8;
    const pageNumbers = this.pages.map((_page, index) => firstPage + index * 2);

    pushText("%PDF-1.4\n%âãÏÓ\n");
    object(1, "<< /Type /Catalog /Pages 2 0 R >>");
    object(
      2,
      `<< /Type /Pages /Kids [${pageNumbers.map((n) => `${n} 0 R`).join(" ")}] /Count ${this.pages.length} >>`
    );
    Object.values(FONTS).forEach((font, index) => {
      object(
        3 + index,
        `<< /Type /Font /Subtype /Type1 /BaseFont /${font.base} /Encoding /WinAnsiEncoding >>`
      );
    });
    if (this.image) {
      offsets[6] = length;
      pushText(
        `6 0 obj\n<< /Type /XObject /Subtype /Image /Width ${this.image.width} /Height ${this.image.height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${this.image.bytes.length} >>\nstream\n`
      );
      push(this.image.bytes);
      pushText("\nendstream\nendobj\n");
    } else {
      object(6, "null");
    }
    object(7, `<< /Title ${pdfString(this.title)} /Creator (SIGA) >>`);

    const resources = `<< /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R >>${this.image ? " /XObject << /Im1 6 0 R >>" : ""} >>`;
    for (let index = 0; index < this.pages.length; index += 1) {
      const pageNumber = pageNumbers[index];
      object(
        pageNumber,
        `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${num(this.width)} ${num(this.height)}] /Resources ${resources} /Contents ${pageNumber + 1} 0 R >>`
      );
      await streamObject(
        pageNumber + 1,
        "",
        encoder.encode(this.pages[index].join("\n"))
      );
    }

    const objectCount = firstPage + this.pages.length * 2;
    const xrefStart = length;
    let xref = `xref\n0 ${objectCount}\n0000000000 65535 f \n`;
    for (let number = 1; number < objectCount; number += 1) {
      xref += `${String(offsets[number]).padStart(10, "0")} 00000 n \n`;
    }
    pushText(xref);
    pushText(
      `trailer\n<< /Size ${objectCount} /Root 1 0 R /Info 7 0 R >>\nstartxref\n${xrefStart}\n%%EOF\n`
    );
    return new Blob(chunks, { type: "application/pdf" });
  }
}
