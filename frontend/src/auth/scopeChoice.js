/**
 * Traduccion entre lo que se elige en el asistente de rol (RA3) y el contrato
 * de alcance del backend, que nombra cada dimension por `public_id` (RA1).
 *
 * `choice`: `{type, value, cycleId}`. `type` es la dimension elegida; `value`
 * su `public_id` (o el modulo); `cycleId` acompana a la seccion.
 */

/**
 * Cuerpo `scope` del POST de asignacion, o `null` si la eleccion esta incompleta.
 *
 * @param {{type: string, value: string, cycleId?: string}} choice
 * @param {{institution?: {public_id: string}}} [scopeOptions]
 */
export function scopePayload(choice, scopeOptions) {
  switch (choice?.type) {
    case "institution":
      return scopeOptions?.institution
        ? { institution: scopeOptions.institution.public_id }
        : null;
    case "academic_cycle":
    case "grade":
    case "subject":
    case "student":
      return choice.value ? { [choice.type]: choice.value } : null;
    case "section":
      return choice.value
        ? {
            section: choice.value,
            ...(choice.cycleId ? { academic_cycle: choice.cycleId } : {}),
          }
        : null;
    case "module":
      return choice.value ? { module_key: choice.value } : null;
    case "teaching_assignments":
      return { teaching_assignments: true };
    default:
      return null;
  }
}

/** Texto del alcance para el resumen ("la sección 1.º Básico A"). */
export function describeScopeChoice(choice, labels = {}) {
  const label = labels[choice?.type] ?? "";
  switch (choice?.type) {
    case "institution":
      return label ? `toda la institución (${label})` : "toda la institución";
    case "academic_cycle":
      return `el ciclo ${label}`.trim();
    case "grade":
      return `el grado ${label}`.trim();
    case "section":
      return `la sección ${label}`.trim();
    case "subject":
      return `el curso ${label}`.trim();
    case "student":
      return `el expediente de ${label || "el estudiante elegido"}`;
    case "module":
      return `el módulo «${label}»`;
    case "teaching_assignments":
      return "sus asignaciones docentes vigentes";
    default:
      return "";
  }
}

/** Etiqueta legible de un alcance ya guardado (dimensiones del backend). */
export function scopeDimensionsText(scope) {
  return (scope?.dimensions ?? []).map((part) => part.label).join(" · ");
}
