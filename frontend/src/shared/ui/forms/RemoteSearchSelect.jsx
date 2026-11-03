import { useEffect, useState } from "react";

import Autocomplete from "@mui/material/Autocomplete";
import CircularProgress from "@mui/material/CircularProgress";
import TextField from "@mui/material/TextField";

import { useSearchableCatalog } from "@shared/catalogs/useSearchableCatalog.js";

import { MENU_MAX_HEIGHT } from "./SearchableSelect.jsx";

/** Espera tras la ultima tecla antes de pedir al servidor. */
const TYPING_DEBOUNCE_MS = 300;

/**
 * Selector con busqueda en el servidor, para entidades grandes (docs/ux-ui.md
 * 1.3): estudiantes, docentes, matriculas, encargados, personas.
 *
 * A diferencia de `SearchableSelect`, que filtra una lista ya descargada, este
 * pide al backend `?search=` con lo que la persona escribe: nunca descarga el
 * padron completo para llenar un desplegable.
 *
 * Emite el mismo contrato que un input nativo (`{target: {name, value}}`) para
 * que quien lo use trate a todos los selectores igual. La opcion elegida se
 * conserva aunque deje de estar en los resultados de la busqueda actual, y
 * `initialOption` permite mostrar el valor de un registro que se edita sin
 * buscarlo antes.
 *
 * @param {object} props
 * @param {string} props.name
 * @param {string} props.label
 * @param {string} props.value  `value` de la opcion elegida ("" si ninguna).
 * @param {(event: {target: {name: string, value: string}}) => void} props.onChange
 * @param {{name: string, fetchPage: Function, mapResult: Function}} props.search
 * @param {{value: string, label: string}} [props.initialOption]
 */
export function RemoteSearchSelect({
  disabled,
  error,
  helperText,
  initialOption,
  label,
  name,
  onChange,
  placeholder = "Escriba al menos 2 letras para buscar",
  required,
  search,
  value,
  onOptionChange,
}) {
  const [inputValue, setInputValue] = useState("");
  const [term, setTerm] = useState("");
  const [selected, setSelected] = useState(initialOption ?? null);

  useEffect(() => {
    const timer = window.setTimeout(
      () => setTerm(inputValue),
      TYPING_DEBOUNCE_MS
    );
    return () => window.clearTimeout(timer);
  }, [inputValue]);

  useEffect(() => {
    if (!value) setSelected(null);
  }, [value]);

  const catalog = useSearchableCatalog(
    search.name,
    search.fetchPage,
    search.mapResult,
    term
  );

  const options =
    selected &&
    !catalog.options.some((option) => option.value === selected.value)
      ? [selected, ...catalog.options]
      : catalog.options;

  return (
    <Autocomplete
      autoHighlight
      disabled={disabled}
      // El servidor ya filtro: filtrar otra vez en el cliente esconderia
      // coincidencias por apellido o codigo que la etiqueta no muestra igual.
      filterOptions={(candidates) => candidates}
      getOptionLabel={(option) => option.label}
      inputValue={inputValue}
      isOptionEqualToValue={(option, candidate) =>
        option.value === candidate.value
      }
      loading={catalog.loading}
      loadingText="Buscando…"
      noOptionsText={
        catalog.ready
          ? "Ninguna coincidencia"
          : "Escriba al menos 2 letras para buscar"
      }
      onChange={(_event, option) => {
        setSelected(option);
        onOptionChange?.(option);
        onChange({ target: { name, value: option?.value ?? "" } });
      }}
      onInputChange={(_event, nextValue) => setInputValue(nextValue)}
      options={options}
      renderInput={(params) => (
        <TextField
          {...params}
          error={Boolean(error || catalog.error)}
          helperText={catalog.error || helperText}
          label={label}
          name={name}
          placeholder={placeholder}
          required={required}
          InputProps={{
            ...params.InputProps,
            endAdornment: (
              <>
                {catalog.loading ? <CircularProgress size={16} /> : null}
                {params.InputProps?.endAdornment}
              </>
            ),
          }}
        />
      )}
      renderOption={({ key: _labelKey, ...optionProps }, option) => (
        <li key={option.value} {...optionProps}>
          {option.label}
        </li>
      )}
      slotProps={{ listbox: { sx: { maxHeight: MENU_MAX_HEIGHT } } }}
      value={selected}
    />
  );
}
