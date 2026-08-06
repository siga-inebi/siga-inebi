/**
 * Paginador de los listados del catalogo. El backend pagina con
 * `PageNumberPagination`, asi que solo hacen falta anterior y siguiente.
 */
export function CataloguePager({ page, pageCount, count, onChange }) {
  if (pageCount <= 1) {
    return null;
  }

  return (
    <nav aria-label="Paginacion" className="pager">
      <button
        className="button secondary"
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
        type="button"
      >
        Anterior
      </button>
      <span className="muted">
        Pagina {page} de {pageCount} ({count} registros)
      </span>
      <button
        className="button secondary"
        disabled={page >= pageCount}
        onClick={() => onChange(page + 1)}
        type="button"
      >
        Siguiente
      </button>
    </nav>
  );
}
