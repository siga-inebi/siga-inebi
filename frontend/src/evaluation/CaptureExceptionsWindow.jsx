import { useMemo, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";

import { SUBJECT_SEARCH } from "@academics/searchOptions.js";
import { evaluationService } from "@evaluation/evaluationService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import {
  asTeacherPersonOptions,
  labelIndex,
  useSubjectCatalog,
  useTeacherCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { useServerList } from "@shared/crud/useServerList.js";
import { formatDateTime } from "@shared/utils/format.js";
import { teachersService } from "@teachers/teachersService.js";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { DataTable } from "@ui/table/DataTable.jsx";
import { NameCell } from "@ui/table/cells.jsx";

/**
 * Docente como opción con el `public_id` de su PERSONA: una excepción se otorga
 * a la persona que firma la nota, no al perfil docente.
 */
const TEACHER_PERSON_SEARCH = Object.freeze({
  name: "teacher-people",
  fetchPage: (params) => teachersService.listPage(params),
  mapResult: (teacher) => ({
    value: teacher.person?.public_id ?? "",
    label: [
      [teacher.person?.first_name, teacher.person?.last_name]
        .filter(Boolean)
        .join(" "),
      teacher.employee_code,
    ]
      .filter(Boolean)
      .join(" · "),
  }),
});

const EXCEPTION_FIELDS = [
  {
    name: "subject",
    label: "Subárea",
    type: "search-select",
    search: SUBJECT_SEARCH,
    required: true,
  },
  {
    name: "teacher",
    label: "Docente",
    type: "search-select",
    search: TEACHER_PERSON_SEARCH,
    required: true,
  },
  {
    name: "reason",
    label: "Motivo de la excepción",
    required: true,
    span: "full",
    help: "Queda registrado en la bitácora: describa por qué se abre la captura fuera de ventana.",
  },
  {
    name: "expires_at",
    label: "Vence el",
    type: "date",
    required: true,
    help: "La excepción caduca sola en esta fecha; no hay que revocarla a mano.",
  },
];

/**
 * Permisos excepcionales de captura fuera de ventana de una unidad (RF-EVC-004).
 *
 * Solo se otorgan y caducan: no hay revocación manual porque el vencimiento es
 * obligatorio, y no hay edición porque cambiar el motivo después destruiría la
 * evidencia de por qué se autorizó. El listado pagina en el servidor y los
 * selectores del alta buscan en el servidor (docs/ux-ui.md 1.1 y 1.3).
 */
export function CaptureExceptionsWindow({ cycleId, onClose, unit }) {
  // El listado responde solo identificadores: los nombres salen de los
  // catálogos de subáreas y docentes (acotados), no de un padrón de estudiantes.
  const subjects = useSubjectCatalog();
  const teachers = useTeacherCatalog();
  const names = useMemo(
    () => ({
      subjects: labelIndex(subjects.options),
      teachers: labelIndex(asTeacherPersonOptions(teachers.options)),
    }),
    [subjects.options, teachers.options]
  );

  const list = useServerList({
    queryKey: queryKeys.evaluation(cycleId, "exceptions", unit.public_id),
    fetchPage: (params) =>
      evaluationService.listCaptureExceptions(cycleId, unit.public_id, params),
    urlPrefix: "exc_",
  });

  const [granting, setGranting] = useState(false);

  return (
    <>
      <FloatingWindow
        description={`Autorizaciones para capturar notas de «${unit.name}» fuera de su ventana normal. Cada una vence por sí sola.`}
        footer={
          <>
            <Button onClick={onClose} variant="text">
              Cerrar
            </Button>
            <Button
              onClick={() => setGranting(true)}
              startIcon={<AddIcon fontSize="small" />}
              variant="contained"
            >
              Otorgar excepción
            </Button>
          </>
        }
        onClose={onClose}
        open
        title="Permisos excepcionales de captura"
        width={WINDOW_WIDTH.wide}
      >
        <Stack gap={2}>
          {list.error ? <Alert severity="error">{list.error}</Alert> : null}
          <DataTable
            columns={[
              {
                key: "subject",
                label: "Subárea",
                render: (row) => (
                  <NameCell id={row.subject} index={names.subjects} />
                ),
              },
              {
                key: "teacher",
                label: "Docente",
                render: (row) => (
                  <NameCell id={row.teacher} index={names.teachers} />
                ),
              },
              { key: "reason", label: "Motivo", render: (row) => row.reason },
              {
                key: "expires_at",
                label: "Vence",
                render: (row) => formatDateTime(row.expires_at),
              },
              {
                key: "created_at",
                label: "Otorgada",
                render: (row) => formatDateTime(row.created_at),
              },
            ]}
            emptyMessage="Esta unidad no tiene permisos excepcionales otorgados."
            getRowKey={(row) => row.public_id}
            loading={list.loading}
            pagination={list.pagination}
            rows={list.items}
          />
        </Stack>
      </FloatingWindow>

      {granting ? (
        <EntityFormWindow
          description="El motivo y el vencimiento son obligatorios: la excepción es auditable y temporal."
          fields={EXCEPTION_FIELDS}
          initialValues={{
            subject: "",
            teacher: "",
            reason: "",
            expires_at: "",
          }}
          onCancel={() => setGranting(false)}
          onSubmit={async (payload) => {
            await evaluationService.createCaptureException(
              cycleId,
              unit.public_id,
              payload
            );
            setGranting(false);
            list.refresh();
          }}
          open
          submitLabel="Otorgar excepción"
          title="Nueva excepción de captura"
        />
      ) : null}
    </>
  );
}
