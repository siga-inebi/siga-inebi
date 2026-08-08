export function ListToolbar({
  createLabel = "+ Agregar nuevo",
  filterAllLabel = "Todas las secciones/puestos",
  filterOptions,
  filterValue,
  onCreate,
  onExportCsv,
  onFilterChange,
  onSearchChange,
  searchPlaceholder = "Buscar por nombre...",
  searchValue,
}) {
  return (
    <div className="list-toolbar">
      <input
        aria-label={searchPlaceholder}
        className="list-search"
        onChange={(event) => onSearchChange(event.target.value)}
        placeholder={searchPlaceholder}
        type="search"
        value={searchValue}
      />
      {filterOptions ? (
        <select
          aria-label="Filtrar"
          className="list-filter"
          onChange={(event) => onFilterChange(event.target.value)}
          value={filterValue}
        >
          <option value="">{filterAllLabel}</option>
          {filterOptions.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      ) : null}
      <div className="list-toolbar-actions">
        <button
          className="button secondary"
          onClick={onExportCsv}
          type="button"
        >
          Exportar CSV
        </button>
        <button className="button" onClick={onCreate} type="button">
          {createLabel}
        </button>
      </div>
    </div>
  );
}
