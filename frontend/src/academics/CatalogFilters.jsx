import Button from "@mui/material/Button";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";

import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";
import { SearchField } from "@ui/filters/SearchField.jsx";

/**
 * Buscador y orden de un catalogo academico (docs/ux-ui.md 1.1).
 *
 * Ambos viven en la URL a traves de `useServerList`: el backend busca por
 * nombre y codigo y ordena con `ordering` (api-conventions, "Búsqueda y orden
 * en catálogos"). La primera opcion de `orderingOptions` es el orden por
 * defecto del listado.
 *
 * @param {object} props
 * @param {object} props.list  Resultado de `useServerList`.
 * @param {string} props.placeholder
 * @param {Array<{value: string, label: string}>} [props.orderingOptions]
 */
export function CatalogFilters({ list, orderingOptions, placeholder }) {
  const hasFilters = Boolean(list.search);
  return (
    <FilterBar onClear={hasFilters ? () => list.setSearch("") : undefined}>
      <SearchField
        debounceMs={0}
        onChange={list.setSearch}
        placeholder={placeholder}
        value={list.search}
      />
      {orderingOptions ? (
        <FilterSelect
          label="Ordenar por"
          onChange={list.setOrdering}
          options={orderingOptions}
          value={list.ordering || orderingOptions[0].value}
        />
      ) : null}
    </FilterBar>
  );
}

/**
 * Pista visible del maestro-detalle (A3, N3): "Ver jornadas (2)". Antes era un
 * icono sin texto y nada decía que la fila abría otra tabla.
 *
 * @param {object} props
 * @param {boolean} props.open
 * @param {string} props.noun  "jornadas", "grados"…
 * @param {number} [props.count]
 * @param {Function} props.onToggle
 */
export function DetailToggleButton({ count, noun, onToggle, open }) {
  const suffix = typeof count === "number" ? ` (${count})` : "";
  return (
    <Button
      aria-pressed={open}
      endIcon={
        open ? (
          <ExpandLessIcon fontSize="small" />
        ) : (
          <ChevronRightIcon fontSize="small" />
        )
      }
      onClick={(event) => {
        event.stopPropagation();
        onToggle();
      }}
      size="small"
      variant={open ? "contained" : "outlined"}
    >
      {open ? `Ocultar ${noun}` : `Ver ${noun}${suffix}`}
    </Button>
  );
}
