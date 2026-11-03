import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";

/**
 * Cantidad de opciones a partir de la cual un desplegable se vuelve buscable.
 *
 * Por debajo de esto, un buscador estorba: se lee la lista completa de un
 * vistazo y escribir es mas lento que mirar. Por encima, la lista deja de caber
 * en pantalla y recorrerla con la rueda del raton es el peor buscador posible —
 * cien estudiantes no se encuentran mirando.
 */
export const SEARCHABLE_FROM = 12;

/** Alto maximo del menu. Sin tope, un catalogo largo tapa la pantalla entera. */
export const MENU_MAX_HEIGHT = "18rem";

/**
 * Desplegable con buscador, para catalogos largos.
 *
 * Es un `Autocomplete` y no un select con un campo de busqueda encima porque
 * asi el teclado funciona como la gente espera: escribir filtra, las flechas
 * recorren y Enter elige, sin que la pantalla tenga que implementar nada.
 *
 * Traduce su valor al contrato del input nativo: hacia adentro busca la opcion
 * cuyo `value` coincide, y hacia afuera emite `{target: {name, value}}`. Asi
 * quien lo usa sigue tratando a todos los selectores igual, buscables o no.
 */
export function SearchableSelect({
  clearText,
  disabled,
  error,
  helperText,
  label,
  name,
  onChange,
  options,
  placeholder,
  required,
  value,
  ...rest
}) {
  const selected = options.find((option) => option.value === value) ?? null;

  return (
    <Autocomplete
      autoHighlight
      disabled={disabled}
      getOptionLabel={(option) => option.label}
      isOptionEqualToValue={(option, candidate) =>
        option.value === candidate.value
      }
      noOptionsText="Ninguna opcion coincide"
      onChange={(_event, option) =>
        onChange({ target: { name, value: option?.value ?? "" } })
      }
      options={options}
      renderInput={(params) => (
        <TextField
          {...params}
          error={Boolean(error)}
          helperText={helperText}
          label={label}
          name={name}
          placeholder={placeholder}
          required={required}
        />
      )}
      renderOption={({ key: _labelKey, ...optionProps }, option) => (
        // La clave sale del valor y no de la etiqueta: MUI usa la etiqueta por
        // defecto, y dos personas pueden llamarse igual. Con etiquetas repetidas
        // React descarta filas del listado sin avisar.
        <li key={option.value} {...optionProps}>
          {option.label}
        </li>
      )}
      slotProps={{
        listbox: { sx: { maxHeight: MENU_MAX_HEIGHT } },
        clearIndicator: clearText ? { title: clearText } : undefined,
      }}
      value={selected}
      {...rest}
    />
  );
}
