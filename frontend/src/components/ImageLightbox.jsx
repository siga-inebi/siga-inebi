import { useBodyScrollLock } from "../hooks/useBodyScrollLock.js";

export function ImageLightbox({ alt = "", downloadName, onClose, src }) {
  useBodyScrollLock();

  return (
    <>
      <button
        aria-label="Cerrar"
        className="overlay-backdrop lightbox-backdrop"
        onClick={onClose}
        type="button"
      />
      <div aria-label={alt || "Imagen"} className="lightbox" role="dialog">
        <div className="lightbox-toolbar">
          <a
            className="button secondary"
            download={downloadName || "foto"}
            href={src}
          >
            Descargar
          </a>
          <button
            aria-label="Cerrar imagen"
            className="detail-close"
            onClick={onClose}
            type="button"
          >
            x
          </button>
        </div>
        <img alt={alt} className="lightbox-image" src={src} />
      </div>
    </>
  );
}
