/** Anio propuesto para un ciclo nuevo: el siguiente al de referencia. */
export function nextCycleYear(source) {
  return (source?.year ?? new Date().getFullYear()) + 1;
}

/** Texto que explica por que no se puede volver a borrador (D6). */
export function revertBlockersText(readiness) {
  const blockers = readiness?.revert?.blockers ?? [];
  return blockers.map((blocker) => blocker.message).join(" ");
}

/** Ruta del detalle (tablero de preparacion) de un ciclo. */
export function cyclePath(cycle, tab) {
  const base = `/app/ciclos/${cycle.public_id}`;
  return tab ? `${base}?tab=${tab}` : base;
}
