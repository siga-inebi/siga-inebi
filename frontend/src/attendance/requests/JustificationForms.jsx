import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  attendanceService,
  SITUATION_TYPE_LABEL,
  withoutBlank,
} from "@attendance/attendanceService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { todayInputValue } from "@shared/utils/format.js";

import { STUDENT_SEARCH } from "../studentSearch.js";

const ACCEPTED_FILES = "application/pdf,image/jpeg,image/png";

/** Adjuntar el respaldo: solo quien presentó, y una sola vez (RF-JUS-007). */
export function AttachWindow({ justification, onCancel, onDone, title }) {
  return (
    <EntityFormWindow
      description="Documento de respaldo en PDF, JPG o PNG. Solo quien presentó la justificación puede adjuntarlo y se admite un único documento."
      fields={[
        {
          name: "file",
          label: "Documento de respaldo",
          type: "file",
          accept: ACCEPTED_FILES,
          required: true,
        },
      ]}
      initialValues={{ file: null }}
      onCancel={onCancel}
      onSubmit={async ({ file }) => {
        await attendanceService.uploadJustificationAttachment(
          justification.public_id,
          file
        );
        onDone();
      }}
      open
      submitLabel="Adjuntar"
      title={title}
    />
  );
}

function useJustificationReasons() {
  const query = useQuery({
    queryKey: queryKeys.attendance("justification-reasons"),
    queryFn: () =>
      attendanceService.listJustificationReasons({ page_size: 100 }),
  });
  return {
    options: (query.data?.results ?? []).map((reason) => ({
      value: reason.public_id,
      label: reason.name,
    })),
    loading: query.isPending,
    error: query.error?.message ?? "",
  };
}

/**
 * Nueva justificación (RF-JUS-001/003) y, enseguida, el adjunto opcional.
 * Registrar una excepción a la ventana solo se ofrece a quien puede resolver.
 */
export function NewJustificationWindow({ canResolve, onCancel, onCreated }) {
  const reasons = useJustificationReasons();
  const [created, setCreated] = useState(null);

  if (created) {
    return (
      <AttachWindow
        justification={created}
        onCancel={() => onCreated(created)}
        onDone={() => onCreated(created)}
        title="Adjuntar respaldo (opcional)"
      />
    );
  }

  return (
    <EntityFormWindow
      description="Se presenta después de la inasistencia, dentro del plazo configurado. Queda pendiente hasta que se resuelva."
      fields={(values) => [
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
          name: "absence_date",
          label: "Fecha de la inasistencia",
          type: "date",
          required: true,
        },
        {
          name: "situation_type",
          label: "Situación",
          type: "select",
          options: Object.entries(SITUATION_TYPE_LABEL).map(
            ([value, label]) => ({ value, label })
          ),
          required: true,
        },
        {
          name: "reason_catalog_id",
          label: "Motivo del catálogo",
          type: "select",
          options: reasons.options,
          loading: reasons.loading,
          optionsError: reasons.error,
          emptyHint: "No hay motivos configurados; describa el motivo abajo.",
          span: "full",
        },
        { name: "reason", label: "Motivo", type: "textarea", required: true },
        ...(canResolve
          ? [
              {
                name: "is_exception",
                label: "Registrar como excepción al plazo",
                type: "checkbox",
              },
            ]
          : []),
        ...(canResolve && values.is_exception
          ? [
              {
                name: "exception_reason",
                label: "Motivo de la excepción",
                type: "textarea",
                required: true,
              },
            ]
          : []),
      ]}
      initialValues={{
        student_id: "",
        absence_date: todayInputValue(),
        situation_type: "absence",
        reason_catalog_id: "",
        reason: "",
        is_exception: false,
        exception_reason: "",
      }}
      onCancel={onCancel}
      onSubmit={async (payload) => {
        const body = withoutBlank(payload);
        if (!body.is_exception) delete body.is_exception;
        setCreated(await attendanceService.createJustification(body));
      }}
      open
      submitLabel="Presentar justificación"
      title="Nueva justificación"
    />
  );
}
