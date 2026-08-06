/**
 * Modulos privados disponibles en la barra de navegacion y en el panel.
 * Vive fuera de los componentes para que ambos muestren siempre lo mismo.
 */
export const MODULE_NAV = [
  {
    to: "/app",
    label: "Panel",
    description: "Estado de la sesion y del backend.",
    end: true,
  },
  {
    to: "/app/personas",
    label: "Personas",
    description: "Registro base de personas institucionales.",
  },
  {
    to: "/app/sedes",
    label: "Sedes",
    description: "Sedes del establecimiento y sus jornadas.",
  },
  {
    to: "/app/niveles",
    label: "Niveles",
    description: "Niveles, grados y plan de estudios.",
  },
  {
    to: "/app/cursos",
    label: "Cursos",
    description: "Catalogo de cursos de la institucion.",
  },
];
