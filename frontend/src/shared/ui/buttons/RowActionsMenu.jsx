import { useState } from "react";

import IconButton from "@mui/material/IconButton";
import ListItemText from "@mui/material/ListItemText";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Tooltip from "@mui/material/Tooltip";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";

/**
 * Menu "⋯" de acciones de una fila (docs/ux-ui.md U9).
 *
 * Con tres o mas botones de texto por fila la tabla se satura. Las acciones se
 * agrupan aqui, en un orden fijo (consultar, acciones frecuentes, y la
 * destructiva al final), y solo aparecen las que la cuenta puede hacer.
 *
 * @param {object} props
 * @param {string} props.label  Para el nombre accesible: "Acciones de ana.lopez".
 * @param {Array<{key: string, label: string, onClick: Function, disabled?: boolean,
 *   hidden?: boolean, danger?: boolean, hint?: string}>} props.actions
 */
export function RowActionsMenu({ actions, disabled = false, label }) {
  const [anchor, setAnchor] = useState(null);
  const visible = actions.filter((action) => !action.hidden);
  if (visible.length === 0) return null;

  return (
    <>
      <Tooltip title="Acciones">
        <span>
          <IconButton
            aria-haspopup="menu"
            aria-label={`Acciones de ${label}`}
            disabled={disabled}
            onClick={(event) => {
              // La fila tambien es clicable (abre la ficha).
              event.stopPropagation();
              setAnchor(event.currentTarget);
            }}
            size="small"
          >
            <MoreHorizIcon fontSize="small" />
          </IconButton>
        </span>
      </Tooltip>
      <Menu
        anchorEl={anchor}
        onClick={(event) => event.stopPropagation()}
        onClose={() => setAnchor(null)}
        open={Boolean(anchor)}
      >
        {visible.map((action) => (
          <MenuItem
            disabled={action.disabled}
            key={action.key}
            onClick={() => {
              setAnchor(null);
              action.onClick();
            }}
            sx={action.danger ? { color: "error.main" } : undefined}
          >
            <ListItemText primary={action.label} secondary={action.hint} />
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}
