import { useId, useState } from "react";

import AddIcon from "@mui/icons-material/Add";
import Button from "@mui/material/Button";
import ListItemText from "@mui/material/ListItemText";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";

/** Acceso único; los casos de uso y las reglas pertenecen a cada flujo. */
export function EnrolmentEntryMenu({
  onIndividual,
  onInitialBulk,
  onReenrolBulk,
}) {
  const [anchor, setAnchor] = useState(null);
  const menuId = useId();
  const buttonId = useId();
  const choose = (action) => {
    setAnchor(null);
    action();
  };

  return (
    <>
      <Button
        aria-controls={anchor ? menuId : undefined}
        aria-expanded={anchor ? "true" : undefined}
        aria-haspopup="menu"
        id={buttonId}
        onClick={(event) => setAnchor(event.currentTarget)}
        startIcon={<AddIcon fontSize="small" />}
        variant="contained"
      >
        Matricular
      </Button>
      <Menu
        anchorEl={anchor}
        id={menuId}
        slotProps={{ list: { "aria-labelledby": buttonId } }}
        onClose={() => setAnchor(null)}
        open={Boolean(anchor)}
      >
        <MenuItem onClick={() => choose(onIndividual)}>
          <ListItemText
            primary="Un estudiante"
            secondary="Primera matrícula o reinscripción automática según historial."
          />
        </MenuItem>
        <MenuItem onClick={() => choose(onInitialBulk)}>
          <ListItemText
            primary="Altas iniciales por lotes"
            secondary="Seleccionar varios estudiantes para el ciclo."
          />
        </MenuItem>
        {onReenrolBulk ? (
          <MenuItem onClick={() => choose(onReenrolBulk)}>
            <ListItemText
              primary="Reinscribir por lotes"
              secondary="Continuar matrículas de otro ciclo con revisión previa."
            />
          </MenuItem>
        ) : null}
      </Menu>
    </>
  );
}
