import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { EMPTY_VALUE } from "@shared/utils/format.js";

/**
 * Par etiqueta/valor del detalle de una entidad.
 *
 * La etiqueta va arriba, chica y en versalitas; el valor abajo con el peso del
 * cuerpo. Dos textos del mismo tamano uno al lado del otro se leen como una sola
 * frase y el usuario pierde cual es el dato.
 */
export function DetailField({ label, value }) {
  const isEmpty = value == null || value === "" || value === EMPTY_VALUE;

  return (
    <Box>
      <Typography
        component="dt"
        sx={{
          fontSize: "0.6875rem",
          fontWeight: 700,
          color: "text.secondary",
          textTransform: "uppercase",
          letterSpacing: "0.09em",
        }}
      >
        {label}
      </Typography>
      <Typography
        component="dd"
        sx={{
          fontSize: "0.875rem",
          m: 0,
          mt: 0.5,
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
 * Ventana de detalle de una entidad.
 *
 * Los campos se acomodan en dos columnas desde `sm`: en una sola columna un
 * expediente de ocho campos obliga a scrollear para algo que cabe de un vistazo.
 *
 * @param {object}   props
 * @param {boolean}  props.open
 * @param {Function} props.onClose
 * @param {string}   props.title
 * @param {Array<{label:string,value:ReactNode}>} props.fields
 * @param {ReactNode}[props.actions]  Acciones al pie.
 * @param {ReactNode}[props.children] Contenido extra bajo los campos.
 */
export function DetailWindow({ actions, children, fields, onClose, open, title }) {
  return (
    <FloatingWindow
      footer={actions}
      onClose={onClose}
      open={open}
      title={title}
      width={WINDOW_WIDTH.medium}
    >
      <Box
        component="dl"
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
          gap: 2.5,
          m: 0,
        }}
      >
        {fields.map((field) => (
          <DetailField key={field.label} label={field.label} value={field.value} />
        ))}
      </Box>
      {children}
    </FloatingWindow>
  );
}
