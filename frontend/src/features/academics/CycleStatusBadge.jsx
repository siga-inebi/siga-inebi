const CYCLE_STATUS = {
  draft: { label: "Borrador", className: "badge badge-draft" },
  active: { label: "Activo", className: "badge badge-active" },
  closed: { label: "Cerrado", className: "badge badge-closed" },
};

/**
 * Estado del ciclo. No es el `is_active` del resto del catalogo: un ciclo tiene
 * su propio ciclo de vida, y "cerrado" significa congelado, no dado de baja.
 */
export function CycleStatusBadge({ status }) {
  const state = CYCLE_STATUS[status] || {
    label: status,
    className: "badge badge-inactive",
  };

  return <span className={state.className}>{state.label}</span>;
}
