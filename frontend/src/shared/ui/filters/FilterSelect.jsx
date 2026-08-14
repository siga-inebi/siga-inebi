import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";

/**
 * Select compacto para la barra de filtros de un listado.
 *
 * Es un `TextField select` y no un `Select` suelto porque asi hereda label
 * flotante, tamano y anillo de foco del tema sin configuracion extra.
 *
 * @param {object} props
 * @param {string} props.label
 * @param {string} props.value
 * @param {Function} props.onChange   Recibe el valor ya desempaquetado.
 * @param {Array<{value:string,label:string}>} props.options
 * @param {number} [props.minWidth=140]
 */
export function FilterSelect({
  label,
  minWidth = 140,
  onChange,
  options,
  value,
}) {
  return (
    <TextField
      fullWidth={false}
      label={label}
      onChange={(event) => onChange(event.target.value)}
      select
      slotProps={{ inputLabel: { shrink: true } }}
      sx={{ minWidth }}
      value={value}
    >
      {options.map((option) => (
        <MenuItem key={option.value} value={option.value}>
          {option.label}
        </MenuItem>
      ))}
    </TextField>
  );
}
