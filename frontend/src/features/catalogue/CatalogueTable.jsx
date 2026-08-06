/**
 * Tabla de lectura del catalogo. Recibe columnas declarativas para que cada
 * pantalla solo describa que muestra, no como se pinta.
 */
export function CatalogueTable({
  caption,
  columns,
  rows,
  rowKey,
  renderActions,
  loading,
  emptyMessage = "No hay registros para mostrar.",
}) {
  if (loading) {
    return <p className="muted">Cargando registros...</p>;
  }

  if (!rows.length) {
    return <p className="muted">{emptyMessage}</p>;
  }

  return (
    <div className="table-scroll">
      <table className="data-table">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} scope="col">
                {column.header}
              </th>
            ))}
            {renderActions ? <th scope="col">Acciones</th> : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)}>
              {columns.map((column) => (
                <td key={column.key}>{column.render(row)}</td>
              ))}
              {renderActions ? (
                <td className="row-actions">{renderActions(row)}</td>
              ) : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function StatusBadge({ active }) {
  return (
    <span className={active ? "badge badge-active" : "badge badge-inactive"}>
      {active ? "Activo" : "Desactivado"}
    </span>
  );
}
