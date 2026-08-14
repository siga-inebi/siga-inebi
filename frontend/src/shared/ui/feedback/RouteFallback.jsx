import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";

import { SectionCard } from "@ui/layout/SectionCard.jsx";

/**
 * Fallback de `Suspense` mientras baja el chunk de una ruta perezosa.
 *
 * Replica la silueta real de una pagina de listado (encabezado, barra de
 * filtros, filas) en vez de un spinner centrado: al montarse la pagina de
 * verdad los bloques ya estan donde el ojo los espera y no hay salto de layout.
 */
export function RouteFallback() {
  return (
    <Stack aria-busy aria-label="Cargando seccion" gap={3}>
      <Stack gap={1}>
        <Skeleton aria-hidden height={32} variant="text" width={220} />
        <Skeleton aria-hidden height={20} variant="text" width={340} />
      </Stack>
      <SectionCard>
        <Stack gap={1.5} sx={{ p: 2 }}>
          <Skeleton aria-hidden height={40} variant="rounded" />
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton aria-hidden height={28} key={index} variant="text" />
          ))}
        </Stack>
      </SectionCard>
    </Stack>
  );
}
