import Box from "@mui/material/Box";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { SectionCard } from "@ui/layout/SectionCard.jsx";

/**
 * Tarjeta de indicador del panel: etiqueta, numero grande y accion opcional.
 *
 * El numero se dimensiona en `rem` (no en `px`) para que siga la escala de
 * accesibilidad del navegador junto con el resto del texto.
 *
 * @param {object}   props
 * @param {string}   props.label
 * @param {ReactNode} props.value
 * @param {string}  [props.hint]
 * @param {ReactNode}[props.action]
 * @param {boolean} [props.loading]
 */
export function StatCard({ action, hint, label, loading = false, value }) {
  return (
    <SectionCard accent={false} sx={{ height: "100%" }}>
      <Stack gap={0.5} sx={{ px: 3, py: 2.5, height: "100%" }}>
        <Typography
          sx={{
            fontSize: "0.6875rem",
            fontWeight: 600,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "text.secondary",
          }}
        >
          {label}
        </Typography>
        {loading ? (
          <Skeleton aria-hidden height={44} variant="text" width={90} />
        ) : (
          <Typography sx={{ fontSize: "2rem", fontWeight: 700, lineHeight: 1.2 }}>
            {value}
          </Typography>
        )}
        {hint ? (
          <Typography color="text.secondary" variant="body2">
            {hint}
          </Typography>
        ) : null}
        {action ? <Box sx={{ mt: "auto", pt: 1.5 }}>{action}</Box> : null}
      </Stack>
    </SectionCard>
  );
}
