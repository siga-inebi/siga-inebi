import { useCallback, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { studentsService } from "@students/studentsService.js";
import { guardiansService } from "@guardians/guardiansService.js";
import {
  enrolmentsService,
  ENROLMENT_STATUS_LABEL,
} from "@enrolments/enrolmentsService.js";
import { documentsService } from "@documents/documentsService.js";
import {
  attendanceService,
  MOVEMENT_LABEL,
  ORIGIN_LABEL,
} from "@attendance/attendanceService.js";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDate, formatDateTime } from "@shared/utils/format.js";
import { RecordCollection } from "./RecordCollection.jsx";
import { RecordForm } from "./RecordForm.jsx";
import { GuardianRelationAction } from "./GuardianRelationAction.jsx";
import { fullName } from "./studentPresentation.js";

const RELATED = {
  health: {
    load: "listHealthNotesPage",
    create: "createHealthNote",
    title: "Nueva nota de salud",
    submit: "Registrar nota",
    empty: "Sin notas de salud",
    fields: [
      {
        name: "content",
        label: "Información de salud",
        type: "textarea",
        required: true,
      },
    ],
  },
  observations: {
    load: "listObservationsPage",
    create: "createObservation",
    title: "Nueva observación",
    submit: "Registrar observación",
    empty: "Sin observaciones",
    fields: [
      {
        name: "description",
        label: "Descripción",
        type: "textarea",
        required: true,
      },
    ],
  },
  contacts: {
    load: "listEmergencyContactsPage",
    create: "createEmergencyContact",
    title: "Nuevo contacto",
    submit: "Registrar contacto",
    empty: "Sin contactos de emergencia",
    fields: [
      { name: "name", label: "Nombre", required: true },
      { name: "phone_number", label: "Teléfono", required: true },
      { name: "relationship_label", label: "Relación", required: true },
    ],
  },
};

export function RelatedRecordsPanel({ student, kind, onBusy }) {
  const config = RELATED[kind];
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);
  const load = useCallback(
    (params) => studentsService[config.load](student.public_id, params),
    [config, student.public_id]
  );
  const list = usePaginatedList(load, { canIncludeInactive: false });
  const setProcessing = (value) => {
    setBusy(value);
    onBusy(value);
  };
  return (
    <Stack gap={2}>
      {!creating ? (
        <Button
          sx={{ alignSelf: "flex-start" }}
          onClick={() => setCreating(true)}
          variant="outlined"
        >
          {config.title}
        </Button>
      ) : (
        <>
          <Typography component="h2" variant="h6">
            {config.title}
          </Typography>
          <RecordForm
            title={config.title}
            fields={config.fields}
            onCancel={() => setCreating(false)}
            onBusy={setProcessing}
            submitLabel={config.submit}
            onSubmit={async (values) => {
              await studentsService[config.create](student.public_id, values);
              list.goToPage(1);
              list.refresh();
              setCreating(false);
            }}
          />
        </>
      )}
      <RecordCollection
        list={list}
        busy={busy}
        emptyMessage={config.empty}
        renderRow={(row) =>
          kind === "contacts" ? (
            <>
              <Typography fontWeight={600}>
                {row.name} · {row.relationship_label}
              </Typography>
              <Typography>{row.phone_number}</Typography>
            </>
          ) : (
            <>
              <Typography color="text.secondary">
                {formatDate(row.recorded_on ?? row.observed_on)} · {row.author}
              </Typography>
              <Typography
                sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}
              >
                {row.content ?? row.description}
              </Typography>
            </>
          )
        }
      />
    </Stack>
  );
}

function GuardianLinkForm({ student, onCancel, onSaved, onBusy }) {
  const load = useCallback(
    (params) => guardiansService.listPage({ page: params.page }),
    []
  );
  const list = usePaginatedList(load, { canIncludeInactive: false });
  const [chosen, setChosen] = useState(null);
  return (
    <Stack gap={2}>
      <Typography component="h2" variant="h6">
        Vincular encargado
      </Typography>
      {!chosen ? (
        <>
          <RecordCollection
            list={list}
            emptyMessage="No hay encargados registrados."
            renderRow={(row) => (
              <Button onClick={() => setChosen(row)}>
                Elegir {fullName(row)}
              </Button>
            )}
          />
          <Button onClick={onCancel}>Cancelar</Button>
        </>
      ) : (
        <>
          <Typography>Encargado: {fullName(chosen)}</Typography>
          <RecordForm
            title="Vincular encargado"
            fields={[
              {
                name: "relationship_label",
                label: "Parentesco o responsabilidad",
                required: true,
              },
            ]}
            onCancel={onCancel}
            onBusy={onBusy}
            submitLabel="Vincular encargado"
            onSubmit={async (values) => {
              await studentsService.createGuardianRelation({
                student: student.id,
                guardian: chosen.id,
                ...values,
              });
              onSaved();
            }}
          />
        </>
      )}
    </Stack>
  );
}

export function GuardiansPanel({ student, onBusy }) {
  const [linking, setLinking] = useState(false);
  const [selection, setSelection] = useState(null);
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(
    (params) => studentsService.listRecordGuardians(student.public_id, params),
    [student.public_id]
  );
  const list = usePaginatedList(load, { canIncludeInactive: false });
  const setProcessing = (value) => {
    setBusy(value);
    onBusy(value);
  };
  const saved = (kind) => {
    setSelection(null);
    setSuccess(
      kind === "end"
        ? "Vínculo finalizado. El historial se conserva."
        : kind === "primary"
          ? "Encargado principal actualizado."
          : "Vínculo actualizado."
    );
    list.goToPage(1);
    list.refresh();
  };
  return (
    <Stack gap={2}>
      {success ? <Alert severity="success">{success}</Alert> : null}
      {selection ? (
        <GuardianRelationAction
          key={`${selection.kind}-${selection.relation.id}`}
          student={student}
          selection={selection}
          onCancel={() => setSelection(null)}
          onBusy={setProcessing}
          onSaved={saved}
        />
      ) : linking ? (
        <GuardianLinkForm
          student={student}
          onCancel={() => setLinking(false)}
          onBusy={(value) => {
            setBusy(value);
            onBusy(value);
          }}
          onSaved={() => {
            setLinking(false);
            list.goToPage(1);
            list.refresh();
          }}
        />
      ) : (
        <Button
          sx={{ alignSelf: "flex-start" }}
          variant="outlined"
          onClick={() => {
            setSuccess("");
            setLinking(true);
          }}
        >
          Vincular encargado
        </Button>
      )}
      <RecordCollection
        list={list}
        busy={busy}
        emptyMessage="Sin encargados vinculados"
        renderRow={(row) => (
          <>
            <Typography fontWeight={600}>
              {row.guardian_detail
                ? fullName(row.guardian_detail)
                : "Encargado"}
            </Typography>
            <Typography>
              {row.relationship_label}
              {row.is_primary ? " · Principal" : ""}
            </Typography>
            <Typography color="text.secondary">
              {row.is_active && !row.ends_at
                ? "Relación vigente"
                : "Relación finalizada"}{" "}
              · Desde {formatDate(row.starts_at)}
              {row.ends_at ? ` · Hasta ${formatDate(row.ends_at)}` : ""}
            </Typography>
            <Typography>{row.guardian_detail?.person?.phone_number}</Typography>
            {!selection && !linking ? (
              <Stack direction="row" gap={1} useFlexGap flexWrap="wrap">
                {[
                  ["edit", "edit", "Editar vínculo"],
                  ["primary", "make_primary", "Marcar como principal"],
                  ["end", "end", "Finalizar vínculo"],
                ]
                  .filter(([, capability]) => row.actions?.[capability])
                  .map(([kind, , label]) => (
                    <Button
                      key={kind}
                      disabled={busy}
                      onClick={() => {
                        setSuccess("");
                        setSelection({ kind, relation: row });
                      }}
                    >
                      {label}
                    </Button>
                  ))}
              </Stack>
            ) : null}
          </>
        )}
      />
    </Stack>
  );
}

export function EnrolmentsPanel({ student }) {
  const load = useCallback(
    (params) => enrolmentsService.listStudentRecord(student.public_id, params),
    [student.public_id]
  );
  const list = usePaginatedList(load, { canIncludeInactive: false });
  return (
    <RecordCollection
      list={list}
      emptyMessage="Sin matrículas registradas"
      renderRow={(row) => (
        <>
          <Typography fontWeight={600}>
            {row.cycle_name} · {row.grade_name} · Sección {row.section_name} ·{" "}
            {row.shift_name}
          </Typography>
          <Typography>
            {ENROLMENT_STATUS_LABEL[row.status] ?? row.status}
            {row.is_current ? " · Matrícula vigente" : ""}
          </Typography>
          <Typography>
            Desde {formatDate(row.effective_on)}
            {row.ends_on ? ` · Hasta ${formatDate(row.ends_on)}` : ""}
          </Typography>
        </>
      )}
    />
  );
}

function DocumentRow({ row }) {
  const [download, setDownload] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return (
    <>
      <Typography fontWeight={600}>
        {row.filename} · Versión {row.version_number}
      </Typography>
      <Typography>
        {formatDateTime(row.created_at)} ·{" "}
        {row.is_active ? "Activo" : "Histórico"}
      </Typography>
      {error ? <Alert severity="error">{error}</Alert> : null}
      {download ? (
        <Button
          component="a"
          href={download.download_url}
          target="_blank"
          rel="noopener noreferrer"
        >
          Descargar {row.filename}
        </Button>
      ) : (
        <Button
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            setError("");
            try {
              setDownload(
                await documentsService.issueDownloadToken(row.public_id)
              );
            } catch (err) {
              setError(err.message);
            } finally {
              setBusy(false);
            }
          }}
        >
          Preparar descarga
        </Button>
      )}
      {download ? (
        <Button onClick={() => setDownload(null)}>
          Renovar enlace de descarga
        </Button>
      ) : null}
    </>
  );
}

export function DocumentsPanel({ student }) {
  const load = useCallback(
    (params) => documentsService.listStudentRecords(student.public_id, params),
    [student.public_id]
  );
  const list = usePaginatedList(load, { canIncludeInactive: false });
  return (
    <RecordCollection
      list={list}
      emptyMessage="Sin archivos en el expediente"
      renderRow={(row) => <DocumentRow row={row} />}
    />
  );
}

export function AttendancePanel({ student }) {
  const load = useCallback(
    (params) =>
      attendanceService.listEvents({
        page: params.page,
        student_id: student.public_id,
      }),
    [student.public_id]
  );
  const list = usePaginatedList(load, { canIncludeInactive: false });
  return (
    <RecordCollection
      list={list}
      emptyMessage="Sin movimientos de asistencia"
      renderRow={(row) => (
        <>
          <Typography fontWeight={600}>
            {formatDate(row.event_date)} ·{" "}
            {MOVEMENT_LABEL[row.movement_type] ?? row.movement_type}
          </Typography>
          <Typography>
            {formatDateTime(row.captured_at)} ·{" "}
            {ORIGIN_LABEL[row.origin] ?? row.origin}
            {row.is_active === false ? " · Suprimido por duplicado" : ""}
          </Typography>
        </>
      )}
    />
  );
}
