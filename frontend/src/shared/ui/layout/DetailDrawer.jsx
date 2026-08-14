import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { BaseDrawer, DRAWER_WIDTH } from "@ui/layout/BaseDrawer.jsx";
import { EMPTY_VALUE } from "@shared/utils/format.js";

/**
 * Par etiqueta/valor del detalle de una entidad.
 *
 * La etiqueta va arriba y pequena, el valor abajo y con el peso del cuerpo: en
 * una columna angosta, dos textos del mismo tamano lado a lado se leen como una
 * sola frase.
 */
export function DetailField({ label, value }) {
  const isEmpty = value == null || value === "" || value === EMPTY_VALUE;

  return (
    <Box>
      <Typography
        component="dt"
        sx={{
          fontSize: "0.75rem",
          color: "text.secondary",
          textTransform: "uppercase",
          letterSpacing: "0.04em",
        }}
      >
        {label}
      </Typography>
      <Typography
        component="dd"
        sx={{
          fontSize: "0.875rem",
          m: 0,
          mt: 0.25,
          color: isEmpty ? "text.disabled" : "text.primary",
          wordBreak: "break-word",
        }}
      >
        {isEmpty ? EMPTY_VALUE : value}
      </Typography>
    </Box>
  );
}

/**
 * Panel lateral de detalle de una entidad.
 *
 * @param {object}   props
 * @param {boolean}  props.open
 * @param {Function} props.onClose
 * @param {string}   props.title
 * @param {Array<{label:string,value:ReactNode}>} props.fields
 * @param {ReactNode}[props.actions] Acciones al pie.
 * @param {ReactNode}[props.children] Contenido extra bajo los campos.
 */
export function DetailDrawer({ actions, children, fields, onClose, open, title }) {
  return (
    <BaseDrawer
      footer={actions}
      onClose={onClose}
      open={open}
      title={title}
      width={DRAWER_WIDTH.compact}
    >
      <Stack component="dl" gap={2.5} sx={{ m: 0 }}>
        {fields.map((field) => (
          <DetailField key={field.label} label={field.label} value={field.value} />
        ))}
      </Stack>
      {children}
    </BaseDrawer>
  );
}
