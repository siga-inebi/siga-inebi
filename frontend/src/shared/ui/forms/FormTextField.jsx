import TextField from "@mui/material/TextField";

/**
 * Campo de texto de formulario.
 *
 * Normaliza el contrato de error: el dominio pasa un string (o nada), no un
 * booleano mas un texto. Eso evita el bug clasico de `error` en true con
 * `helperText` vacio, que pinta el campo en rojo sin decir por que.
 *
 * @param {object}  props
 * @param {string} [props.error]        Mensaje de error; si viene, pinta el campo.
 * @param {string} [props.helperText]   Ayuda cuando no hay error.
 * @param {number} [props.maxLength]    Activa contador de caracteres.
 */
export function FormTextField({
  error,
  helperText,
  maxLength,
  value,
  ...rest
}) {
  const counter =
    maxLength != null
      ? `${String(value ?? "").length}/${maxLength} caracteres`
      : null;

  return (
    <TextField
      error={Boolean(error)}
      helperText={error ?? helperText ?? counter}
      slotProps={maxLength != null ? { htmlInput: { maxLength } } : undefined}
      value={value}
      {...rest}
    />
  );
}
