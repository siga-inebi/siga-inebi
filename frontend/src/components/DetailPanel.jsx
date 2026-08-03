import { useBodyScrollLock } from "../hooks/useBodyScrollLock.js";

export function DetailPanel({ fields, onClose, title }) {
  useBodyScrollLock();

  return (
    <>
      <button
        aria-label="Cerrar"
        className="overlay-backdrop"
        onClick={onClose}
        type="button"
      />
      <aside aria-label={`Detalle de ${title}`} className="detail-panel">
        <div className="detail-panel-header">
          <h2>{title}</h2>
          <button
            aria-label="Cerrar detalle"
            className="detail-close"
            onClick={onClose}
            type="button"
          >
            x
          </button>
        </div>
        <dl className="info-list">
          {fields.map((field) => (
            <div key={field.label}>
              <dt>{field.label}</dt>
              <dd>{field.value ?? "Sin dato"}</dd>
            </div>
          ))}
        </dl>
      </aside>
    </>
  );
}
