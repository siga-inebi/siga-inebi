import Autocomplete from "@mui/material/Autocomplete";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";

/**
 * Cantidad de opciones a partir de la cual el desplegable se vuelve buscable.
 *
 * Por debajo de esto, un buscador estorba: se lee la lista completa de un
 * vistazo y escribir es mas lento que mirar. Por encima, la lista deja de
 * caber en pantalla y recorrerla con la rueda del raton es el peor buscador
 * posible — cien estudiantes no se encuentran mirando.
 */
const SEARCHABLE_FROM = 12;

/** Alto maximo del menu. Sin tope, un catalogo largo tapa la pantalla entera. */
const MENU_MAX_HEIGHT = "18rem";

/**
 * Select de formulario.
 *
 * Mientras el catalogo carga muestra una opcion deshabilitada "Cargando…" en
 * vez de un select vacio: un desplegable sin opciones se lee como "no hay
 * nada", que es una respuesta distinta a "todavia no llega".
 *
 * El contrato de `onChange` es el de un input nativo (`event.target.value`) en
 * las dos variantes, para que las pantallas no tengan que saber cual les toco.
 *
 * @param {object}  props
 * @param {Array<{value:string|number,label:string}>} props.options
 * @param {boolean}[props.loading]
 * @param {string} [props.error]
 * @param {string} [props.placeholder] Opcion vacia inicial.
 */
export function FormSelect({
  error,
  helperText,
  loading = false,
  options,
  placeholder,
  ...rest
}) {
  // `||` y no `??`: un error vacio ("" es el estado "sin error" que usan
  // los catalogos) tiene que dejar pasar el texto de ayuda, y `??` solo
  // descarta null/undefined.
  const resolvedHelperText = error || helperText;

  if (!loading && options.length >= SEARCHABLE_FROM) {
    return (
      <SearchableSelect
        error={error}
        helperText={resolvedHelperText}
        options={options}
        placeholder={placeholder}
        {...rest}
      />
    );
  }

  return (
    <TextField
      error={Boolean(error)}
      helperText={resolvedHelperText}
      select
      slotProps={{
        select: {
          MenuProps: {
            slotProps: { paper: { sx: { maxHeight: MENU_MAX_HEIGHT } } },
          },
        },
      }}
      {...rest}
    >
      {placeholder ? (
        <MenuItem value="">
          <em>{placeholder}</em>
        </MenuItem>
      ) : null}
      {loading ? (
        <MenuItem disabled value="">
          Cargando…
        </MenuItem>
      ) : (
        options.map((option) => (
          <MenuItem key={option.value} value={option.value}>
            {option.label}
          </MenuItem>
        ))
      )}
    </TextField>
  );
}

/**
 * Variante buscable para catalogos largos.
 *
 * Es un `Autocomplete` y no un select con un campo de busqueda encima porque
 * asi el teclado funciona como la gente espera: escribir filtra, las flechas
 * recorren y Enter elige, sin que la pantalla tenga que implementar nada.
 *
 * Traduce su valor al contrato del input nativo: hacia adentro busca la opcion
 * cuyo `value` coincide, y hacia afuera emite `{target: {name, value}}`. Asi
 * `EntityFormWindow` y las pantallas siguen tratando a todos los selectores
 * igual, buscables o no.
 */
function SearchableSelect({
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
        // defecto, y dos personas pueden llamarse igual. Con etiquetas
        // repetidas React descarta filas del listado sin avisar.
        <li key={option.value} {...optionProps}>
          {option.label}
        </li>
      )}
      slotProps={{
        listbox: { sx: { maxHeight: MENU_MAX_HEIGHT } },
      }}
      value={selected}
      {...rest}
    />
  );
}
