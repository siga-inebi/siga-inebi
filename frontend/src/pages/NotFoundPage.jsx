import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <section className="panel">
      <h1>404</h1>
      <p>Ruta no encontrada.</p>
      <Link className="button" to="/">
        Volver al inicio
      </Link>
    </section>
  );
}
