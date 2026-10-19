/**
 * Vista previa del identificador que el backend derivara del nombre (RO3).
 * Es solo una pista visual: el `slug` definitivo lo asigna el servidor, que
 * ademas lo numera si ya existe.
 */
export function slugPreview(name) {
  return String(name ?? "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}
