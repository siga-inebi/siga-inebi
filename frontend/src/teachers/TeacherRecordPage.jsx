import { lazy, Suspense, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ButtonBase from "@mui/material/ButtonBase";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { GrantAccessButton } from "@auth/GrantAccessButton.jsx";
import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { teachersService } from "@teachers/teachersService.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { queryKeys } from "@shared/api/queryKeys.js";
import { formatDate } from "@shared/utils/format.js";
import { ImageDialog } from "@ui/display/ImageDialog.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { DetailField } from "@ui/layout/DetailWindow.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard } from "@ui/layout/SectionCard.jsx";
import {
  TEACHER_EDIT_FIELDS,
  buildTeacherPayload,
  fullName,
} from "./teacherPresentation.js";

// "Qué imparte" trae el servicio académico: se descarga solo si se muestra.
const TeacherAssignments = lazy(() =>
  import("@teachers/TeacherAssignments.jsx").then((module) => ({
    default: module.TeacherAssignments,
  }))
);

// Los documentos solo se consultan a demanda: fuera del chunk de la ruta.
const TeacherDocumentsWindow = lazy(() =>
  import("@teachers/TeacherDocumentsWindow.jsx").then((module) => ({
    default: module.TeacherDocumentsWindow,
  }))
);

const TeacherDeactivationDialog = lazy(() =>
  import("@teachers/TeacherDeactivationDialog.jsx").then((module) => ({
    default: module.TeacherDeactivationDialog,
  }))
);

/**
 * Ficha propia del docente (mismo patron que el expediente del estudiante):
 * todo lo que antes apilaba el modal de detalle vive en esta vista, y la
 * edicion abre un unico modal encima de la pagina, no un modal sobre otro.
 *
 * La ruta usa el id numerico porque `GET /teachers/<id>/` responde al `pk`
 * (TeacherDetailView no define `lookup_field`).
 */
function TeacherRecord({ teacherId }) {
  const { can } = usePermissions();
  // "Qué imparte" consulta un listado que exige administrar asignaciones.
  const canSeeAssignments = can(PERMISSION.SCOPE_ASSIGN);
  const location = useLocation();
  const candidate = location.state?.teacherListLocation;
  const returnTo =
    typeof candidate === "string" && /^\/app\/docentes(?:\?|$)/.test(candidate)
      ? candidate
      : "/app/docentes";

  const positions = useQuery({
    queryKey: [...queryKeys.teachers.all, "positions"],
    queryFn: teachersService.listPositions,
  });
  const positionOptions = positions.data ?? [];
  const positionsReady =
    !positions.isPending && !positions.isError && positionOptions.length > 0;
  const positionLabel = (value) =>
    positionOptions.find((option) => option.value === value)?.label ?? value;
  const editFields = TEACHER_EDIT_FIELDS.map((field) =>
    field.name === "position" ? { ...field, options: positionOptions } : field
  );

  const [teacher, setTeacher] = useState(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  const [notice, setNotice] = useState("");
  const [editing, setEditing] = useState(false);
  const [deactivating, setDeactivating] = useState(false);
  const [documentsOpen, setDocumentsOpen] = useState(false);
  const [viewingPhoto, setViewingPhoto] = useState(false);

  // La ficha ya cargada se conserva mientras se refresca: la pantalla no
  // parpadea al volver de editar o desactivar.
  useEffect(() => {
    let active = true;
    setError("");
    teachersService
      .get(teacherId)
      .then((data) => {
        if (active) setTeacher(data);
      })
      .catch((err) => {
        if (active) setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [teacherId, version]);

  const handleUpdate = async (values) => {
    const updated = await teachersService.update(teacher.id, {
      ...buildTeacherPayload(values),
      person: {
        public_id: teacher.person.public_id,
        first_name: values.first_name,
        last_name: values.last_name,
        email: values.email,
        phone_number: values.phone_number,
        sex: values.sex,
        nationality: values.nationality,
        address: values.address,
        department: values.department,
        municipality: values.municipality,
      },
    });
    // Los permisos de accion (p. ej. desactivar) no viajan en la respuesta del
    // PUT: se conservan los de la ficha cargada.
    setTeacher((current) => ({ ...updated, actions: current.actions }));
    setNotice("Cambios guardados.");
    setEditing(false);
  };

  return (
    <>
      <PageHeader
        action={
          <Button component={Link} to={returnTo}>
            Volver a docentes
          </Button>
        }
        breadcrumb="Comunidad educativa"
        subtitle={
          teacher
            ? `${teacher.employee_code} · Consulta de la ficha institucional`
            : "Consulta de la ficha institucional"
        }
        title={teacher ? fullName(teacher) : "Ficha del docente"}
      />

      {notice ? (
        <Alert severity="success" sx={{ mb: 2 }}>
          {notice}
        </Alert>
      ) : null}
      {error ? (
        <Alert severity="error">
          {error}
          <Button onClick={() => setVersion((value) => value + 1)}>
            Reintentar
          </Button>
        </Alert>
      ) : !teacher ? (
        <Typography role="status">Cargando ficha…</Typography>
      ) : (
        <SectionCard sx={{ p: { xs: 2, sm: 3 } }}>
          <Stack gap={2}>
            <StatusChip
              sx={{ alignSelf: "flex-start" }}
              label={teacher.is_active === false ? "Desactivado" : "Activo"}
              variant={teacher.is_active === false ? "neutral" : "success"}
            />
            <Stack direction="row" gap={1} useFlexGap flexWrap="wrap">
              <Button
                disabled={!positionsReady}
                onClick={() => setEditing(true)}
                variant="contained"
              >
                Editar
              </Button>
              <Button onClick={() => setDocumentsOpen(true)} variant="outlined">
                Documentos
              </Button>
              <GrantAccessButton person={teacher.person} />
              {teacher.actions?.deactivate === true ? (
                <Button color="error" onClick={() => setDeactivating(true)}>
                  Desactivar docente
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
              <DetailField label="Nombre completo" value={fullName(teacher)} />
              <DetailField label="Especialidad" value={teacher.specialty} />
              <DetailField
                label="Puesto"
                value={
                  <StatusChip
                    label={positionLabel(teacher.position)}
                    variant="primary"
                  />
                }
              />
              <DetailField
                label="Código de empleado"
                value={teacher.employee_code}
              />
              <DetailField
                label="Fecha de nombramiento"
                value={
                  teacher.appointment_date
                    ? formatDate(teacher.appointment_date)
                    : null
                }
              />
              <DetailField label="Correo" value={teacher.person.email} />
              <DetailField
                label="Teléfono"
                value={teacher.person.phone_number}
              />
            </Box>
            {teacher.photo ? (
              <ButtonBase
                onClick={() => setViewingPhoto(true)}
                sx={(theme) => ({
                  borderRadius: theme.tokens.radii.chip,
                  alignSelf: "flex-start",
                })}
              >
                <Box
                  alt={`Foto de ${fullName(teacher)}`}
                  component="img"
                  src={teacher.photo}
                  sx={(theme) => ({
                    width: 112,
                    height: 112,
                    objectFit: "cover",
                    borderRadius: theme.tokens.radii.chip,
                    border: "1px solid",
                    borderColor: "divider",
                  })}
                />
              </ButtonBase>
            ) : (
              <Typography color="text.secondary">Sin foto</Typography>
            )}
            {canSeeAssignments ? (
              <Suspense
                fallback={
                  <Typography role="status">Cargando asignaciones…</Typography>
                }
              >
                <TeacherAssignments
                  key={teacher.public_id}
                  teacherId={teacher.public_id}
                />
              </Suspense>
            ) : null}
          </Stack>
        </SectionCard>
      )}

      {teacher && editing ? (
        <EntityFormWindow
          fields={editFields}
          initialValues={{
            first_name: teacher.person.first_name,
            last_name: teacher.person.last_name,
            sex: teacher.person.sex ?? "",
            nationality: teacher.person.nationality ?? "",
            email: teacher.person.email ?? "",
            phone_number: teacher.person.phone_number ?? "",
            address: teacher.person.address ?? "",
            department: teacher.person.department ?? "",
            municipality: teacher.person.municipality ?? "",
            specialty: teacher.specialty,
            position: teacher.position,
            appointment_date: teacher.appointment_date ?? "",
            employee_code: teacher.employee_code,
            photo: null,
          }}
          key={teacher.id}
          onCancel={() => setEditing(false)}
          onSubmit={handleUpdate}
          open
          submitLabel="Guardar cambios"
          title={`Editar ${fullName(teacher)}`}
        />
      ) : null}

      {teacher && deactivating ? (
        <Suspense fallback={<p role="status">Preparando confirmación…</p>}>
          <TeacherDeactivationDialog
            teacher={teacher}
            onCancel={() => setDeactivating(false)}
            onCompleted={() => {
              setDeactivating(false);
              setNotice("Docente desactivado. El historial se conserva.");
              setVersion((value) => value + 1);
            }}
          />
        </Suspense>
      ) : null}

      {teacher && documentsOpen ? (
        <Suspense fallback={<p role="status">Cargando documentos…</p>}>
          <TeacherDocumentsWindow
            key={teacher.public_id}
            onClose={() => setDocumentsOpen(false)}
            teacher={teacher}
            teacherName={fullName(teacher)}
          />
        </Suspense>
      ) : null}

      {teacher && teacher.photo ? (
        <ImageDialog
          alt={fullName(teacher)}
          downloadName={teacher.photo.split("/").pop()}
          onClose={() => setViewingPhoto(false)}
          open={viewingPhoto}
          src={teacher.photo}
        />
      ) : null}
    </>
  );
}

export function TeacherRecordPage() {
  const { teacherId } = useParams();
  return <TeacherRecord key={teacherId} teacherId={teacherId} />;
}
