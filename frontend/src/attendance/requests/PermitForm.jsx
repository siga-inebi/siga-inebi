import {
  attendanceService,
  PERMIT_TYPE_LABEL,
} from "@attendance/attendanceService.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { todayInputValue } from "@shared/utils/format.js";

import { STUDENT_SEARCH } from "../studentSearch.js";

const TYPE_OPTIONS = Object.entries(PERMIT_TYPE_LABEL).map(
  ([value, label]) => ({ value, label })
);

/** Nuevo permiso (RF-JUS-008): se solicita antes del hecho. */
export function NewPermitWindow({ onCancel, onCreated }) {
  return (
    <EntityFormWindow
      description="Un permiso se solicita antes de la salida anticipada o del ingreso tardío. Queda pendiente hasta que se resuelva."
      fields={[
        {
          name: "student_id",
          label: "Estudiante",
          type: "search-select",
          search: STUDENT_SEARCH,
          help: "Escriba el nombre o el código del estudiante.",
          required: true,
          span: "full",
        },
        {
          name: "permit_type",
          label: "Tipo de permiso",
          type: "select",
          options: TYPE_OPTIONS,
          required: true,
        },
        { name: "permit_date", label: "Fecha", type: "date", required: true },
        {
          name: "scheduled_time",
          label: "Hora prevista",
          type: "time",
          required: true,
        },
        { name: "reason", label: "Motivo", type: "textarea", required: true },
      ]}
      initialValues={{
        student_id: "",
        permit_type: "early_exit",
        permit_date: todayInputValue(),
        scheduled_time: "",
        reason: "",
      }}
      onCancel={onCancel}
      onSubmit={async (payload) => {
        onCreated(await attendanceService.createPermit(payload));
      }}
      open
      submitLabel="Solicitar permiso"
      title="Nuevo permiso"
    />
  );
}
