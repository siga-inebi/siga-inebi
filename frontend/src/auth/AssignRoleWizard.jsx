import { useMemo, useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { accountsService } from "@auth/accountsService.js";
import { rolesService } from "@auth/rolesService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { useResourceQuery } from "@shared/api/useResourceQuery.js";
import {
  sectionsForCycle,
  studentOption,
  useCycleCatalog,
  useGradeCatalog,
  useSectionCatalog,
  useSubjectCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { formatDate, todayInputValue } from "@shared/utils/format.js";
import { studentsService } from "@students/studentsService.js";
import { DateField } from "@ui/forms/DateField.jsx";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { RemoteSearchSelect } from "@ui/forms/RemoteSearchSelect.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";

import { describeScopeChoice, scopePayload } from "./scopeChoice.js";

const STEPS = ["Rol", "Alcance", "Vigencia"];

const STUDENT_SEARCH = {
  name: "students",
  fetchPage: (params) => studentsService.listPage(params),
  mapResult: studentOption,
};

/** Fecha `YYYY-MM-DD` como instante local, al inicio o al final del dia. */
function dateToIso(value, endOfDay = false) {
  if (!value) return null;
  const date = new Date(`${value}T${endOfDay ? "23:59:59" : "00:00:00"}`);
  return date.toISOString();
}

/**
 * Asistente de asignacion de rol con alcance (docs/ux-ui.md RA3, RA4).
 *
 * 1. Rol, con su descripcion.
 * 2. Alcance: el tipo y luego el ciclo, grado, seccion, curso o estudiante con
 *    selectores; o "Sus asignaciones docentes vigentes" para docentes (RA4).
 *    Todo se envia por `public_id` (RA1).
 * 3. Vigencia: desde y hasta; por defecto, hasta el fin del ciclo elegido.
 *
 * Termina con un resumen en lenguaje natural de lo que la persona podra hacer.
 */
export function AssignRoleWizard({ account, onAssigned, onClose, open }) {
  const [step, setStep] = useState(0);
  const [roleId, setRoleId] = useState("");
  const [choice, setChoice] = useState({ type: "", value: "", cycleId: "" });
  const [startsOn, setStartsOn] = useState(todayInputValue());
  const [endsOn, setEndsOn] = useState("");
  const [studentLabel, setStudentLabel] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const { data: roles, loading: rolesLoading } = useResourceQuery(
    queryKeys.identity.roles({ active: true }),
    () => rolesService.listAll({ include_inactive: "false" }),
    { defaultData: [] }
  );
  const { data: permissions } = useResourceQuery(
    queryKeys.identity.permissions(),
    () => rolesService.permissions(),
    { defaultData: [] }
  );
  const { data: scopeOptions } = useResourceQuery(
    queryKeys.identity.scopeOptions(),
    () => rolesService.scopeOptions()
  );
  const cycles = useCycleCatalog();
  const grades = useGradeCatalog();
  const sections = useSectionCatalog();
  const subjects = useSubjectCatalog();

  const role = roles.find((candidate) => candidate.public_id === roleId);
  const permissionLabels = useMemo(
    () =>
      new Map(
        permissions.map((permission) => [permission.code, permission.name])
      ),
    [permissions]
  );

  const typeOptions = [
    scopeOptions?.institution
      ? { value: "institution", label: "Toda la institución" }
      : null,
    { value: "academic_cycle", label: "Un ciclo escolar" },
    { value: "grade", label: "Un grado" },
    { value: "section", label: "Una sección" },
    { value: "subject", label: "Un curso" },
    { value: "student", label: "Un estudiante" },
    { value: "module", label: "Un módulo del sistema" },
    account?.person?.is_teacher
      ? {
          value: "teaching_assignments",
          label: "Sus asignaciones docentes vigentes",
        }
      : null,
  ].filter(Boolean);

  const moduleOptions = (scopeOptions?.modules ?? []).filter(
    (module) => module.value !== "teaching_assignments"
  );

  const labels = {
    institution: scopeOptions?.institution?.name,
    academic_cycle: cycles.options.find((o) => o.value === choice.value)?.label,
    grade: grades.options.find((o) => o.value === choice.value)?.label,
    section: sections.options.find((o) => o.value === choice.value)?.label,
    subject: subjects.options.find((o) => o.value === choice.value)?.label,
    student: studentLabel,
    module: moduleOptions.find((o) => o.value === choice.value)?.label,
  };
  const scopeText = describeScopeChoice(choice, labels);

  const chosenCycle = cycles.options.find(
    (option) =>
      option.value ===
      (choice.type === "section" ? choice.cycleId : choice.value)
  );

  const setType = (type) => {
    setChoice({ type, value: "", cycleId: "" });
    setStudentLabel("");
  };

  const canAdvance =
    (step === 0 && Boolean(role)) ||
    (step === 1 && Boolean(scopePayload(choice, scopeOptions))) ||
    step === 2;

  const next = () => {
    setError("");
    if (step === 1 && !endsOn && chosenCycle?.endsOn) {
      // Por defecto, la vigencia llega hasta el fin del ciclo (RA3).
      setEndsOn(chosenCycle.endsOn);
    }
    setStep((value) => value + 1);
  };

  const permissionSummary = (role?.permissions ?? [])
    .slice(0, 3)
    .map((code) => (permissionLabels.get(code) ?? code).toLowerCase());
  const morePermissions = Math.max(0, (role?.permissions?.length ?? 0) - 3);

  const submit = async () => {
    setError("");
    if (endsOn && endsOn < startsOn) {
      setError("La fecha final no puede ser anterior a la inicial.");
      return;
    }
    setSubmitting(true);
    try {
      const assignment = await accountsService.assignRole(account.public_id, {
        role: roleId,
        ...(startsOn && startsOn !== todayInputValue()
          ? { starts_at: dateToIso(startsOn) }
          : {}),
        ends_at: dateToIso(endsOn, true),
        scope: scopePayload(choice, scopeOptions),
      });
      onAssigned?.(assignment);
      onClose();
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <FloatingWindow
      busy={submitting}
      description={`Asignar un rol a ${account?.person?.full_name || account?.username}.`}
      footer={
        <>
          <Button disabled={submitting} onClick={onClose} variant="text">
            Cancelar
          </Button>
          {step > 0 ? (
            <Button
              disabled={submitting}
              onClick={() => setStep((value) => value - 1)}
              variant="outlined"
            >
              Atrás
            </Button>
          ) : null}
          {step < STEPS.length - 1 ? (
            <Button disabled={!canAdvance} onClick={next} variant="contained">
              Siguiente
            </Button>
          ) : (
            <Button
              disabled={submitting}
              onClick={submit}
              startIcon={
                submitting ? <CircularProgress size={16} /> : undefined
              }
              variant="contained"
            >
              Asignar rol
            </Button>
          )}
        </>
      }
      onClose={onClose}
      open={open}
      title="Asignar rol"
      width={WINDOW_WIDTH.medium}
    >
      <Stack gap={2.5}>
        <Typography
          aria-live="polite"
          color="text.secondary"
          component="p"
          variant="overline"
        >
          Paso {step + 1} de {STEPS.length}: {STEPS[step]}
        </Typography>

        {error ? (
          <Alert role="alert" severity="error">
            {error}
          </Alert>
        ) : null}

        {step === 0 ? (
          <Stack gap={1.5}>
            <FormSelect
              fullWidth
              label="Rol"
              loading={rolesLoading}
              name="role"
              onChange={(event) => setRoleId(event.target.value)}
              options={roles.map((candidate) => ({
                value: candidate.public_id,
                label: candidate.name,
              }))}
              placeholder="Seleccione un rol"
              value={roleId}
            />
            {role ? (
              <Box>
                <Typography variant="body2">
                  {role.description || "Sin descripción."}
                </Typography>
                <Typography color="text.secondary" variant="caption">
                  {role.permissions.length} permiso(s) · cierre de sesión tras{" "}
                  {role.session_idle_timeout_minutes} min de inactividad
                </Typography>
              </Box>
            ) : null}
          </Stack>
        ) : null}

        {step === 1 ? (
          <Stack gap={2}>
            <FormSelect
              fullWidth
              helperText="El permiso solo aplica dentro de este alcance."
              label="Tipo de alcance"
              name="scope_type"
              onChange={(event) => setType(event.target.value)}
              options={typeOptions}
              placeholder="Seleccione el tipo de alcance"
              value={choice.type}
            />
            {choice.type === "academic_cycle" ? (
              <FormSelect
                fullWidth
                label="Ciclo escolar"
                loading={cycles.loading}
                name="scope_cycle"
                onChange={(event) =>
                  setChoice({ ...choice, value: event.target.value })
                }
                options={cycles.options}
                placeholder="Seleccione el ciclo"
                value={choice.value}
              />
            ) : null}
            {choice.type === "grade" ? (
              <FormSelect
                fullWidth
                label="Grado"
                loading={grades.loading}
                name="scope_grade"
                onChange={(event) =>
                  setChoice({ ...choice, value: event.target.value })
                }
                options={grades.options}
                placeholder="Seleccione el grado"
                value={choice.value}
              />
            ) : null}
            {choice.type === "section" ? (
              <>
                <FormSelect
                  fullWidth
                  label="Ciclo escolar"
                  loading={cycles.loading}
                  name="scope_section_cycle"
                  onChange={(event) =>
                    setChoice({
                      ...choice,
                      cycleId: event.target.value,
                      value: "",
                    })
                  }
                  options={cycles.options}
                  placeholder="Seleccione el ciclo"
                  value={choice.cycleId}
                />
                <FormSelect
                  disabled={!choice.cycleId}
                  fullWidth
                  label="Sección"
                  loading={sections.loading}
                  name="scope_section"
                  onChange={(event) =>
                    setChoice({ ...choice, value: event.target.value })
                  }
                  options={sectionsForCycle(sections.options, choice.cycleId)}
                  placeholder="Seleccione la sección"
                  value={choice.value}
                />
              </>
            ) : null}
            {choice.type === "subject" ? (
              <FormSelect
                fullWidth
                label="Curso"
                loading={subjects.loading}
                name="scope_subject"
                onChange={(event) =>
                  setChoice({ ...choice, value: event.target.value })
                }
                options={subjects.options}
                placeholder="Seleccione el curso"
                value={choice.value}
              />
            ) : null}
            {choice.type === "student" ? (
              <RemoteSearchSelect
                label="Estudiante"
                name="scope_student"
                onChange={(event) =>
                  setChoice({ ...choice, value: event.target.value })
                }
                onOptionChange={(option) =>
                  setStudentLabel(option?.label ?? "")
                }
                search={STUDENT_SEARCH}
                value={choice.value}
              />
            ) : null}
            {choice.type === "module" ? (
              <FormSelect
                fullWidth
                label="Módulo"
                name="scope_module"
                onChange={(event) =>
                  setChoice({ ...choice, value: event.target.value })
                }
                options={moduleOptions}
                placeholder="Seleccione el módulo"
                value={choice.value}
              />
            ) : null}
            {choice.type === "teaching_assignments" ? (
              <Alert severity="info" variant="outlined">
                El rol aplicará a las secciones y cursos que la persona tenga
                asignados en el ciclo activo, y se ajustará solo cuando cambien
                sus asignaciones docentes.
              </Alert>
            ) : null}
          </Stack>
        ) : null}

        {step === 2 ? (
          <Stack gap={2}>
            <Stack direction={{ xs: "column", sm: "row" }} gap={2}>
              <DateField
                fullWidth
                label="Desde"
                name="starts_on"
                onChange={(event) => setStartsOn(event.target.value)}
                value={startsOn}
              />
              <DateField
                fullWidth
                helperText={
                  chosenCycle?.endsOn
                    ? `Sugerido: fin del ciclo (${formatDate(chosenCycle.endsOn)}).`
                    : "Vacío: sin fecha de vencimiento."
                }
                label="Hasta"
                name="ends_on"
                onChange={(event) => setEndsOn(event.target.value)}
                value={endsOn}
              />
            </Stack>
            <Alert severity="success" variant="outlined">
              <strong>{account?.person?.full_name || account?.username}</strong>{" "}
              podrá{" "}
              <strong>
                {permissionSummary.join(", ") || "usar el rol"}
                {morePermissions > 0
                  ? ` y ${morePermissions} permiso(s) más`
                  : ""}
              </strong>{" "}
              como <strong>{role?.name}</strong> en <strong>{scopeText}</strong>{" "}
              {endsOn
                ? `hasta el ${formatDate(endsOn)}`
                : "sin fecha de vencimiento"}
              .
            </Alert>
          </Stack>
        ) : null}
      </Stack>
    </FloatingWindow>
  );
}
