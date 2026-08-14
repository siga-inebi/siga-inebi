import { useEffect, useState } from "react";

/**
 * Conteos por modulo para los badges del menu lateral.
 *
 * Los servicios se importan de forma dinamica dentro del efecto, no arriba del
 * archivo: son la unica razon por la que el shell tendria que conocer los
 * dominios, y un import estatico los arrastraria al chunk inicial para pintar
 * tres numeros que no son criticos para la primera pantalla.
 *
 * Un modulo que falla queda sin badge (`null`), no rompe el menu: el conteo es
 * informativo y su ausencia no debe impedir navegar.
 */
export function useModuleCounts(enabled) {
  const [counts, setCounts] = useState({});

  useEffect(() => {
    if (!enabled) return undefined;

    let active = true;

    const loaders = [
      [
        "alumnos",
        () =>
          import("@students/studentsService.js").then((m) => m.studentsService),
      ],
      [
        "docentes",
        () =>
          import("@teachers/teachersService.js").then((m) => m.teachersService),
      ],
      [
        "padres",
        () =>
          import("@guardians/guardiansService.js").then(
            (m) => m.guardiansService
          ),
      ],
    ];

    Promise.all(
      loaders.map(([key, load]) =>
        load()
          .then((service) => service.list())
          .then((records) => [key, records.length])
          .catch(() => [key, null])
      )
    ).then((entries) => {
      if (active) setCounts(Object.fromEntries(entries));
    });

    return () => {
      active = false;
    };
  }, [enabled]);

  return counts;
}
