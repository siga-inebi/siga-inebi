import { Link } from "react-router-dom";

export function HomePage() {
  return (
    <section className="landing">
      <div className="panel hero hero-primary">
        <p className="eyebrow">Sistema institucional fundacional</p>
        <h1>Control academico, administrativo y operativo en una sola base segura.</h1>
        <p>
          SIGA-INEBI centraliza acceso, estudiantes, estructura academica,
          matricula y trazabilidad inicial con autentificacion institucional y
          API JSON.
        </p>
        <div className="actions">
          <Link className="button" to="/login">
            Ingresar al sistema
          </Link>
          <a
            className="button secondary"
            href="/api/v1/docs/"
            rel="noreferrer"
            target="_blank"
          >
            Ver API
          </a>
        </div>
      </div>
      <div className="grid hero-grid">
        <div className="panel">
          <h2>Base actual</h2>
          <p>
            Monolito modular con Django REST Framework, React, PostgreSQL y
            controles de autorizacion por rol y alcance.
          </p>
        </div>
        <div className="panel">
          <h2>Enfoque</h2>
          <p>
            Denegacion por defecto, cuentas institucionales vinculadas a
            personas, auditoria y compatibilidad de desarrollo local o Docker.
          </p>
        </div>
      </div>
    </section>
  );
}
