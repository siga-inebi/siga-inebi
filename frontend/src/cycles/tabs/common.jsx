import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Tooltip from "@mui/material/Tooltip";
import AddIcon from "@mui/icons-material/Add";

import { CYCLE_STATUS_LABEL } from "@cycles/cyclesService.js";

/**
 * Aviso de solo consulta para la estructura de un ciclo que ya no es borrador
 * (RF-EST-011): secciones y plan de estudios solo cambian antes de activar.
 */
export function PlanningOnlyNotice({ cycle, what }) {
  if (cycle.status === "draft") return null;
  const status = (
    CYCLE_STATUS_LABEL[cycle.status] ?? cycle.status
  ).toLowerCase();
  return (
    <Alert severity="info" sx={{ mb: 2 }}>
      El ciclo está {status}: {what} se consulta pero no se modifica. La
      estructura solo cambia con el ciclo en borrador
      {cycle.status === "active"
        ? " (un ciclo activo sin actividad puede volver a borrador desde Resumen)."
        : "."}
    </Alert>
  );
}

/** Botón de alta que explica en un tooltip por qué está deshabilitado. */
export function AddButton({ disabled, hint, label, onClick }) {
  return (
    <Tooltip title={disabled && hint ? hint : ""}>
      <span>
        <Button
          disabled={disabled}
          onClick={onClick}
          size="small"
          startIcon={<AddIcon fontSize="small" />}
          variant="contained"
        >
          {label}
        </Button>
      </span>
    </Tooltip>
  );
}
