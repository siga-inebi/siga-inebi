import { Link } from "react-router-dom";

export function HomePage() {
  return (
    <section className="grid">
      <div className="panel hero">
        <p>Fundacion ejecutable inicial</p>
        <h1>Gestion institucional modular para SIGA-INEBI.</h1>
        <p>
          Base de trabajo con React, Django, PostgreSQL y Docker. Modulos funcionales aun no
          implementados.
        </p>
        <div className="actions">
          <Link className="button" to="/login">
            Probar acceso
          </Link>
          <a
            className="button secondary"
            href="http://localhost:8000/api/v1/docs/"
            rel="noreferrer"
            target="_blank"
          >
            Ver API
          </a>
        </div>
      </div>
    </section>
  );
}
