import { lazy, Suspense, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import Alert from "@mui/material/Alert";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";

import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { studentsService } from "@students/studentsService.js";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { DetailField } from "@ui/layout/DetailWindow.jsx";
import { SectionCard } from "@ui/layout/SectionCard.jsx";
import { ImageDialog } from "@ui/display/ImageDialog.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { formatDateTime } from "@shared/utils/format.js";
import { RecordForm } from "./RecordForm.jsx";
import { StudentDeactivationForm } from "./StudentDeactivationForm.jsx";
import {
  STUDENT_EDIT_FIELDS,
  STATUS_LABEL,
  STATUS_VARIANT,
  fullName,
} from "./studentPresentation.js";

const panel = (name) =>
  lazy(() =>
    import("./StudentRecordPanels.jsx").then((module) => ({
      default: module[name],
    }))
  );
const GuardiansPanel = panel("GuardiansPanel");
const RelatedRecordsPanel = panel("RelatedRecordsPanel");
const EnrolmentsPanel = panel("EnrolmentsPanel");
const DocumentsPanel = panel("DocumentsPanel");
const AttendancePanel = panel("AttendancePanel");
// AS2 (#631): el carné se trabaja con el mismo panel de Asistencia → Carnés.
const StudentCardPanel = lazy(() =>
  import("@attendance/StudentCardPanel.jsx").then((module) => ({
    default: module.StudentCardPanel,
  }))
);
const TABS = [
  ["data", "Datos"],
  ["guardians", "Encargados"],
  ["health", "Salud"],
  ["observations", "Observaciones"],
  ["contacts", "Contactos"],
  ["enrolments", "Matrículas"],
  ["documents", "Documentos"],
  ["attendance", "Asistencia"],
  ["card", "Carné", PERMISSION.ATTENDANCE_CREDENTIAL_ISSUE],
];

function DataPanel({ student, onSaved, onBusy, onDeactivated }) {
  const [editing, setEditing] = useState(false);
  const [deactivating, setDeactivating] = useState(false);
  const [photo, setPhoto] = useState(false);
  if (deactivating)
    return (
      <StudentDeactivationForm
        student={student}
        onCancel={() => setDeactivating(false)}
        onBusy={onBusy}
        onCompleted={onDeactivated}
      />
    );
  if (editing)
    return (
      <RecordForm
        title="Editar estudiante"
        fields={STUDENT_EDIT_FIELDS}
        initialValues={{
          ...student.person,
          student_code: student.student_code,
          status: student.status,
          photo: null,
        }}
        onBusy={onBusy}
        onCancel={() => setEditing(false)}
        submitLabel="Guardar cambios"
        onSubmit={async (values) => {
          const { student_code, status, photo: file } = values;
          const person = Object.fromEntries(
            [
              "first_name",
              "last_name",
              "email",
              "phone_number",
              "sex",
              "nationality",
              "address",
              "department",
              "municipality",
            ].map((name) => [name, values[name] ?? ""])
          );
          const updated = await studentsService.update(student.id, {
            person: { public_id: student.person.public_id, ...person },
            student_code,
            status,
            photo: file,
          });
          onSaved(updated);
          setEditing(false);
        }}
      />
    );
  const fields = [
    ["Nombre completo", fullName(student)],
    ["Código de estudiante", student.student_code],
    ["Correo", student.person.email],
    ["Teléfono", student.person.phone_number],
    [
      "Sexo",
      {
        female: "Femenino",
        male: "Masculino",
        not_specified: "No especificado",
      }[student.person.sex] ?? "—",
    ],
    ["Nacionalidad", student.person.nationality],
    ["Dirección", student.person.address],
    ["Departamento", student.person.department],
    ["Municipio", student.person.municipality],
    ["Registrado", formatDateTime(student.created_at)],
    ["Última actualización", formatDateTime(student.updated_at)],
  ];
  return (
    <Stack gap={2}>
      <Stack direction="row" gap={1} useFlexGap flexWrap="wrap">
        <Button
          sx={{ alignSelf: "flex-start" }}
          variant="outlined"
          onClick={() => setEditing(true)}
        >
          Editar
        </Button>
        {student.actions?.deactivate ? (
          <Button color="error" onClick={() => setDeactivating(true)}>
            Desactivar estudiante
          </Button>
        ) : null}
      </Stack>
      <Box
        component="dl"
        sx={{
          m: 0,
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
          gap: 3,
        }}
      >
        {fields.map(([label, value]) => (
          <DetailField key={label} label={label} value={value} />
        ))}
      </Box>
      {student.photo ? (
        <Button sx={{ alignSelf: "flex-start" }} onClick={() => setPhoto(true)}>
          <Avatar
            src={student.photo}
            alt={fullName(student)}
            variant="rounded"
            sx={{ width: 80, height: 96, mr: 2 }}
          />
          Ver foto
        </Button>
      ) : (
        <Typography color="text.secondary">Sin foto</Typography>
      )}
      <ImageDialog
        open={photo}
        src={student.photo}
        alt={fullName(student)}
        onClose={() => setPhoto(false)}
      />
    </Stack>
  );
}

function StudentRecord({ publicId }) {
  const { can } = usePermissions();
  const tabs = TABS.filter(([, , code]) => !code || can(code));
  const [params, setParams] = useSearchParams();
  const tab = tabs.some(([id]) => id === params.get("tab"))
    ? params.get("tab")
    : "data";
  const [visited, setVisited] = useState([tab]);
  const [student, setStudent] = useState(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  const [busy, setBusy] = useState(false);
  const [success, setSuccess] = useState("");
  useEffect(() => {
    setVisited((current) =>
      current.includes(tab) ? current : [...current, tab]
    );
  }, [tab]);
  useEffect(() => {
    let active = true;
    setError("");
    setStudent(null);
    studentsService
      .getRecord(publicId)
      .then((data) => {
        if (active) setStudent(data);
      })
      .catch((err) => {
        if (active) setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [publicId, version]);
  return (
    <>
      <PageHeader
        title={student ? fullName(student) : "Expediente del estudiante"}
        breadcrumb="Comunidad educativa"
        subtitle={
          student?.student_code ?? "Consulta del expediente institucional"
        }
        action={
          <Button component={Link} to="/app/alumnos" disabled={busy}>
            Volver a estudiantes
          </Button>
        }
      />
      {success ? (
        <Alert severity="success" sx={{ mb: 2 }}>
          {success}
        </Alert>
      ) : null}
      {error ? (
        <Alert severity="error">
          {error}
          <Button onClick={() => setVersion((value) => value + 1)}>
            Reintentar
          </Button>
        </Alert>
      ) : !student ? (
        <Typography role="status">Cargando expediente…</Typography>
      ) : (
        <SectionCard sx={{ p: { xs: 2, sm: 3 } }}>
          <Stack gap={2}>
            <StatusChip
              sx={{ alignSelf: "flex-start" }}
              label={STATUS_LABEL[student.status] ?? student.status}
              variant={STATUS_VARIANT[student.status] ?? "neutral"}
            />
            <Tabs
              value={tab}
              variant="scrollable"
              scrollButtons="auto"
              allowScrollButtonsMobile
              aria-label="Secciones del expediente"
              onChange={(_event, next) => {
                if (!busy) setParams({ tab: next });
              }}
            >
              {tabs.map(([id, label]) => (
                <Tab
                  disabled={busy}
                  key={id}
                  id={`record-tab-${id}`}
                  aria-controls={`record-panel-${id}`}
                  label={label}
                  value={id}
                />
              ))}
            </Tabs>
            <Suspense
              fallback={
                <Typography role="status">Cargando sección…</Typography>
              }
            >
              {[...new Set([...visited, tab])].map((id) => (
                <Box
                  key={id}
                  role="tabpanel"
                  id={`record-panel-${id}`}
                  aria-labelledby={`record-tab-${id}`}
                  hidden={id !== tab}
                >
                  {id === "data" ? (
                    <DataPanel
                      student={student}
                      onSaved={(updated) =>
                        setStudent((current) => ({
                          ...updated,
                          actions: current.actions,
                        }))
                      }
                      onBusy={setBusy}
                      onDeactivated={() => {
                        setSuccess(
                          "Estudiante desactivado. El historial se conserva."
                        );
                        setStudent(null);
                        setVersion((value) => value + 1);
                      }}
                    />
                  ) : id === "guardians" ? (
                    <GuardiansPanel student={student} onBusy={setBusy} />
                  ) : ["health", "observations", "contacts"].includes(id) ? (
                    <RelatedRecordsPanel
                      student={student}
                      kind={id}
                      onBusy={setBusy}
                    />
                  ) : id === "enrolments" ? (
                    <EnrolmentsPanel student={student} />
                  ) : id === "documents" ? (
                    <DocumentsPanel student={student} />
                  ) : id === "card" ? (
                    <StudentCardPanel
                      studentId={student.public_id}
                      studentName={fullName(student)}
                    />
                  ) : (
                    <AttendancePanel student={student} />
                  )}
                </Box>
              ))}
            </Suspense>
          </Stack>
        </SectionCard>
      )}
    </>
  );
}

export function StudentRecordPage() {
  const { studentId } = useParams();
  return <StudentRecord key={studentId} publicId={studentId} />;
}
