import { useEffect, useState } from "react";

import { academicsService } from "../../services/academicsService.js";
import { collectAllPages } from "./collectAllPages.js";

/**
 * Grados y jornadas activos de la institucion, para armar una oferta.
 *
 * La API no publica un listado plano de ninguno de los dos: los grados cuelgan
 * de un nivel y las jornadas de una sede, asi que hay que recorrer el padre.
 * Son pocas filas y se leen una sola vez al abrir el formulario, pero si la
 * institucion creciera mucho conviene un endpoint plano en el backend.
 */
export function useStructureOptions() {
  const [grades, setGrades] = useState([]);
  const [shifts, setShifts] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    const collect = async () => {
      const levels = await collectAllPages((page) =>
        academicsService.listLevels({ page })
      );
      const collectedGrades = [];
      for (const level of levels) {
        const rows = await collectAllPages((page) =>
          academicsService.listLevelGrades(level.public_id, { page })
        );
        collectedGrades.push(...rows);
      }

      const campuses = await collectAllPages((page) =>
        academicsService.listCampuses({ page })
      );
      const collectedShifts = [];
      for (const campus of campuses) {
        const rows = await collectAllPages((page) =>
          academicsService.listCampusShifts(campus.public_id, { page })
        );
        // El listado anidado no repite la sede en cada fila cuando ya se sabe
        // cual es, asi que se anota aqui para poder mostrarla en el selector.
        collectedShifts.push(
          ...rows.map((shift) => ({ ...shift, campusName: campus.name }))
        );
      }

      return { grades: collectedGrades, shifts: collectedShifts };
    };

    collect()
      .then((collected) => {
        if (!active) {
          return;
        }
        setGrades(collected.grades);
        setShifts(collected.shifts);
      })
      .catch((requestError) => {
        if (active) {
          setError(requestError.message);
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  return { grades, shifts, error, loading };
}
