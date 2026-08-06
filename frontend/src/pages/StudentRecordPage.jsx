import { useState } from "react";

import { EmergencyContactsPanel } from "../features/students/EmergencyContactsPanel.jsx";
import { StudentGuardianRelationsPanel } from "../features/students/StudentGuardianRelationsPanel.jsx";

/**
 * Puente PROVISIONAL.
 *
 * No existe ninguna pantalla de listado de Estudiantes en esta rama: la
 * construye en paralelo la rama de un companero (PR #54), con un patron de
 * componentes distinto (`DetailPanel`/modal en vez de rutas), y todavia sin
 * mergear. Mientras tanto, esta pagina solo pide el `public_id` del
 * estudiante a mano -- Django admin lo muestra en el detalle de cada
 * registro -- para poder probar de punta a punta los paneles de Contactos
 * de Emergencia (RF-EXP-005) y Relacion Estudiante-Encargado (RF-EXP-004).
 *
 * No se agrega a `MODULE_NAV`: es una ruta de apoyo para QA/demo, no un
 * modulo terminado. Cuando la rama del companero se mergee, la migracion es
 * minima: retirar esta pagina y montar los dos paneles de abajo dentro de
 * su `DetailPanel` -- ambos solo necesitan `{ public_id }` por prop.
 */
export function StudentRecordPage() {
  const [inputValue, setInputValue] = useState("");
  const [student, setStudent] = useState(null);

  const handleSubmit = (event) => {
    event.preventDefault();
    const trimmed = inputValue.trim();
    setStudent(trimmed ? { public_id: trimmed } : null);
  };

  return (
    <section className="catalogue">
      <header className="panel catalogue-header">
        <div>
          <p className="eyebrow">Expediente estudiantil (provisional)</p>
          <h1>Contactos y encargados de un estudiante</h1>
          <p className="muted">
            Pantalla puente mientras no existe un listado de Estudiantes en esta
            rama. Ingrese el identificador publico del estudiante (visible en
            Django admin, en el detalle de cada registro).
          </p>
        </div>
      </header>

      <form className="panel catalogue-form" onSubmit={handleSubmit}>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="student-public-id">
              Identificador del estudiante
            </label>
            <input
              id="student-public-id"
              onChange={(event) => setInputValue(event.target.value)}
              placeholder="Ejemplo: 3fa85f64-5717-4562-b3fc-2c963f66afa6"
              type="text"
              value={inputValue}
            />
          </div>
        </div>
        <div className="actions">
          <button className="button" type="submit">
            Abrir expediente
          </button>
        </div>
      </form>

      {student ? (
        <>
          <EmergencyContactsPanel
            key={`contacts-${student.public_id}`}
            student={student}
          />
          <StudentGuardianRelationsPanel
            key={`relations-${student.public_id}`}
            student={student}
          />
        </>
      ) : null}
    </section>
  );
}
