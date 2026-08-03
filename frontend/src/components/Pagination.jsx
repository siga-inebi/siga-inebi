export function Pagination({ onPageChange, page, pageSize, total }) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);

  return (
    <div className="pagination">
      <p className="muted">
        {total === 0
          ? "Mostrando 0 registros"
          : `Mostrando ${start}-${end} de ${total} registros`}
      </p>
      <div className="pagination-controls">
        <button
          className="button secondary"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          type="button"
        >
          Anterior
        </button>
        <span>
          Pagina {page} de {totalPages}
        </span>
        <button
          className="button secondary"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          type="button"
        >
          Siguiente
        </button>
      </div>
    </div>
  );
}
