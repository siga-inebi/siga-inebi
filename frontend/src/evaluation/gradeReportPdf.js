/**
 * gradeReportPdf.js — Dibuja el PDF del informe de calificaciones en el navegador.
 *
 * El servidor ya calculó todo (notas, promedios por curso, por unidad y
 * general); aquí solo se dibujan las páginas. Generar 400 páginas en el
 * backend congelaría la API (un proceso, cuatro hilos) y costaría CPU en cada
 * impresión; en el navegador cuesta un par de segundos de la máquina de quien
 * imprime y nada del servidor.
 *
 * Usa `MiniPdf` (sin dependencias, pocos KB) y se importa de forma diferida al
 * pulsar "Generar", así no pesa en la carga de ninguna pantalla.
 */
import logoUrl from "@shared/assets/logo.webp";
import { MiniPdf } from "@shared/pdf/miniPdf.js";

/** Carta vertical, en puntos (72 por pulgada). */
const PAGE = { width: 612, height: 792 };
const MARGIN = 40;
const CONTENT_WIDTH = PAGE.width - MARGIN * 2;
const HEADER_HEIGHT = 96;

/** Colores de la marca (theme/palette/raw.js): azul marino y dorado. */
const NAVY = [28, 43, 58];
const NAVY_DARK = [15, 27, 38];
const GOLD = [180, 137, 74];
const GOLD_SOFT = [217, 186, 133];
const ROW_TINT = [234, 237, 241];
const AVERAGE_TINT = [246, 240, 228];
const TEXT = [33, 37, 41];
const MUTED = [108, 117, 125];
const RULE = [211, 218, 226];
const WHITE = [255, 255, 255];

/** Estudiantes que se dibujan antes de devolverle el control al navegador. */
const CHUNK = 25;

const EMPTY = "—";

const pause = () => new Promise((resolve) => window.setTimeout(resolve, 0));

const show = (value) =>
  value === null || value === undefined ? EMPTY : String(value);

/**
 * El logo se guarda como WebP con fondo transparente. Se pinta una sola vez
 * sobre el azul de la franja del membrete y se incrusta como JPEG, que el PDF
 * admite tal cual (sin decodificar ni recomprimir en cada página).
 */
async function loadLogo() {
  try {
    const image = new Image();
    image.decoding = "async";
    image.src = logoUrl;
    await image.decode();
    const canvas = document.createElement("canvas");
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    const context = canvas.getContext("2d");
    context.fillStyle = `rgb(${NAVY.join(",")})`;
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(image, 0, 0);
    const base64 = canvas.toDataURL("image/jpeg", 0.92).split(",")[1];
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index);
    }
    return { bytes, width: canvas.width, height: canvas.height };
  } catch {
    // Sin logo el informe sigue siendo válido: solo pierde el escudo.
    return null;
  }
}

function formatDateTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? ""
    : date.toLocaleString("es-GT", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
}

function drawHeader(pdf, report, hasLogo) {
  pdf.rect(0, 0, PAGE.width, HEADER_HEIGHT, { fill: NAVY });
  pdf.rect(0, HEADER_HEIGHT, PAGE.width, 3, { fill: GOLD });

  let textLeft = MARGIN;
  if (hasLogo) {
    pdf.drawImage(MARGIN, 18, 60, 60);
    textLeft = MARGIN + 76;
  }
  const nameLines = pdf
    .splitText(report.institution.name, PAGE.width - textLeft - MARGIN, {
      font: "bold",
      size: 17,
    })
    .slice(0, 2);
  nameLines.forEach((line, index) => {
    pdf.text(line, textLeft, 40 + index * 20, {
      font: "bold",
      size: 17,
      rgb: WHITE,
    });
  });
  pdf.text(
    `Informe de calificaciones · ${report.cycle.name}`,
    textLeft,
    nameLines.length > 1 ? 80 : 62,
    { size: 11, rgb: GOLD_SOFT }
  );
}

function drawStudentCard(pdf, student, top) {
  const height = 54;
  pdf.roundedRect(MARGIN, top, CONTENT_WIDTH, height, 6, {
    fill: ROW_TINT,
    stroke: RULE,
  });
  const field = (label, value, x, width) => {
    pdf.text(label.toUpperCase(), x, top + 20, { size: 8, rgb: MUTED });
    const [line] = pdf.splitText(value, width, { font: "bold", size: 11 });
    pdf.text(line, x, top + 36, { font: "bold", size: 11, rgb: TEXT });
  };
  field("Estudiante", student.student_name, MARGIN + 14, 236);
  field("Código", student.student_code, MARGIN + 262, 76);
  field("Grado y sección", student.section_label, MARGIN + 346, 172);
  return top + height;
}

/**
 * Anchos de columna: la de cursos se queda con lo que dejan las notas, con un
 * mínimo legible; con muchas unidades baja el tamaño de letra en vez de
 * desbordar la página.
 */
function layout(unitCount) {
  const averageWidth = 70;
  const unitWidth = Math.max(
    40,
    Math.min(64, (CONTENT_WIDTH - 180 - averageWidth) / Math.max(unitCount, 1))
  );
  return {
    subjectWidth: CONTENT_WIDTH - averageWidth - unitWidth * unitCount,
    unitWidth,
    averageWidth,
    fontSize: unitCount > 7 ? 8 : 9.5,
  };
}

function drawTable(pdf, report, student, top) {
  const units = report.units;
  const { subjectWidth, unitWidth, averageWidth, fontSize } = layout(
    units.length
  );
  const unitX = (index) => MARGIN + subjectWidth + unitWidth * index;
  const averageX = MARGIN + subjectWidth + unitWidth * units.length;
  const center = (x, width) => x + width / 2;
  const padding = 8;
  const headerHeight = 30;
  let y = top;

  // Encabezado: Curso | unidades | Promedio
  pdf.rect(MARGIN, y, CONTENT_WIDTH, headerHeight, { fill: NAVY_DARK });
  const head = { font: "bold", size: fontSize, rgb: WHITE };
  pdf.text("Curso", MARGIN + padding, y + 19, head);
  units.forEach((unit, index) => {
    const lines = pdf
      .splitText(unit.name, unitWidth - 6, { font: "bold", size: fontSize })
      .slice(0, 2);
    lines.forEach((line, lineIndex) => {
      pdf.text(
        line,
        center(unitX(index), unitWidth),
        y + (lines.length > 1 ? 13 + lineIndex * (fontSize + 1) : 19),
        { ...head, align: "center" }
      );
    });
  });
  pdf.text("Promedio", center(averageX, averageWidth), y + 19, {
    ...head,
    align: "center",
  });
  y += headerHeight;

  // Una fila por curso, con su promedio al final.
  student.subjects.forEach((subject, rowIndex) => {
    const lines = pdf.splitText(subject.name, subjectWidth - padding * 2, {
      size: fontSize,
    });
    const rowHeight = Math.max(22, lines.length * (fontSize + 3) + 10);
    if (rowIndex % 2 === 1) {
      pdf.rect(MARGIN, y, CONTENT_WIDTH, rowHeight, { fill: ROW_TINT });
    }
    pdf.rect(averageX, y, averageWidth, rowHeight, { fill: AVERAGE_TINT });
    lines.forEach((line, lineIndex) => {
      pdf.text(line, MARGIN + padding, y + 14 + lineIndex * (fontSize + 3), {
        size: fontSize,
        rgb: TEXT,
      });
    });
    const middle = y + rowHeight / 2 + fontSize / 3;
    subject.grades.forEach((value, index) => {
      pdf.text(show(value), center(unitX(index), unitWidth), middle, {
        size: fontSize,
        rgb: value === null ? MUTED : TEXT,
        align: "center",
      });
    });
    pdf.text(show(subject.average), center(averageX, averageWidth), middle, {
      font: "bold",
      size: fontSize,
      rgb: subject.average === null ? MUTED : NAVY,
      align: "center",
    });
    pdf.line(MARGIN, y + rowHeight, MARGIN + CONTENT_WIDTH, y + rowHeight, {
      stroke: RULE,
    });
    y += rowHeight;
  });

  if (student.subjects.length === 0) {
    pdf.text(
      "El grado no tiene cursos en el plan de estudios del ciclo.",
      MARGIN + padding,
      y + 16,
      { font: "italic", size: fontSize, rgb: MUTED }
    );
    y += 24;
  }

  // Promedio de cada unidad abajo y promedio general en la esquina inferior derecha.
  const footerHeight = 28;
  pdf.rect(MARGIN, y, CONTENT_WIDTH, footerHeight, { fill: AVERAGE_TINT });
  pdf.text("Promedio de la unidad", MARGIN + padding, y + 18, {
    font: "bold",
    size: fontSize,
    rgb: NAVY,
  });
  student.unit_averages.forEach((value, index) => {
    pdf.text(show(value), center(unitX(index), unitWidth), y + 18, {
      font: "bold",
      size: fontSize,
      rgb: value === null ? MUTED : NAVY,
      align: "center",
    });
  });
  pdf.rect(averageX, y, averageWidth, footerHeight, { fill: NAVY });
  pdf.text(
    show(student.general_average),
    center(averageX, averageWidth),
    y + 19,
    { font: "bold", size: fontSize + 3, rgb: WHITE, align: "center" }
  );
  const bottom = y + footerHeight;

  // Separadores verticales y marco.
  units.forEach((_unit, index) => {
    pdf.line(unitX(index), top + headerHeight, unitX(index), bottom, {
      stroke: RULE,
      lineWidth: 0.4,
    });
  });
  pdf.line(averageX, top + headerHeight, averageX, bottom, {
    stroke: RULE,
    lineWidth: 0.4,
  });
  pdf.rect(MARGIN, top, CONTENT_WIDTH, bottom - top, {
    stroke: NAVY,
    lineWidth: 0.8,
  });
  return bottom;
}

function drawNotes(pdf, top) {
  const lines = pdf.splitText(
    `${EMPTY} sin calificar. Los promedios excluyen las unidades sin nota y se redondean al entero (mitad hacia arriba). El promedio general, en la esquina inferior derecha, considera todas las notas registradas de todos los cursos.`,
    CONTENT_WIDTH,
    { size: 8.5 }
  );
  lines.forEach((line, index) => {
    pdf.text(line, MARGIN, top + 18 + index * 11, { size: 8.5, rgb: MUTED });
  });
}

function drawFooter(pdf, report, pageNumber, pageCount) {
  const y = PAGE.height - 28;
  pdf.line(MARGIN, y - 12, PAGE.width - MARGIN, y - 12, {
    stroke: GOLD,
    lineWidth: 0.8,
  });
  pdf.text(
    `${report.institution.short_name || report.institution.name} · Generado el ${formatDateTime(report.generated_at)}`,
    MARGIN,
    y,
    { size: 8, rgb: MUTED }
  );
  pdf.text(`Página ${pageNumber} de ${pageCount}`, PAGE.width - MARGIN, y, {
    size: 8,
    rgb: MUTED,
    align: "right",
  });
}

/**
 * PDF de una página por estudiante. Cede el control al navegador cada
 * `CHUNK` estudiantes para que la barra de progreso avance y la pestaña no se
 * congele con cientos de páginas.
 *
 * @param {object} report  Respuesta de `getGradeReport`.
 * @param {{onProgress?: (done: number, total: number) => void, logo?: object|null, compress?: boolean}} [options]
 *   `logo` permite inyectar el escudo ya cargado y `compress: false` deja el
 *   contenido legible (pruebas); por defecto se carga el escudo y se comprime.
 * @returns {Promise<Blob>}
 */
export async function buildGradeReportPdf(
  report,
  { onProgress, logo, compress = true } = {}
) {
  const pdf = new MiniPdf({
    width: PAGE.width,
    height: PAGE.height,
    title: `Informe de calificaciones · ${report.cycle.name}`,
    compress,
  });
  const escudo = logo === undefined ? await loadLogo() : logo;
  if (escudo) pdf.setImage(escudo.bytes, escudo.width, escudo.height);
  const total = report.students.length;

  for (let index = 0; index < total; index += 1) {
    const student = report.students[index];
    pdf.addPage();
    drawHeader(pdf, report, Boolean(escudo));
    const cardBottom = drawStudentCard(pdf, student, 118);
    const tableBottom = drawTable(pdf, report, student, cardBottom + 18);
    drawNotes(pdf, tableBottom);
    if ((index + 1) % CHUNK === 0) {
      onProgress?.(index + 1, total);
      await pause();
    }
  }

  for (let page = 1; page <= pdf.pageCount; page += 1) {
    pdf.setPage(page);
    drawFooter(pdf, report, page, pdf.pageCount);
  }
  onProgress?.(total, total);
  return pdf.toBlob();
}

/** Nombre de archivo según el alcance elegido. */
export function gradeReportFilename(report, scopeLabel) {
  const slug = `informe-notas-${report.cycle.year}-${scopeLabel}`
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return `${slug}.pdf`;
}
