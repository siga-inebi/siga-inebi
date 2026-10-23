import { useCallback, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Link from "@mui/material/Link";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import { Link as RouterLink } from "react-router-dom";

import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDate } from "@shared/utils/format.js";
import { ActionIconButton } from "@ui/buttons/ActionIconButton.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { RemoteSearchSelect } from "@ui/forms/RemoteSearchSelect.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";
import { MutedCell } from "@ui/table/cells.jsx";
import { ReplacementPicker } from "@students/GuardianRelationAction.jsx";
import { fullName } from "@students/studentPresentation.js";
import { studentsService } from "@students/studentsService.js";
import { guardiansService } from "./guardiansService.js";

const studentLabel = (row) =>
  `${row.student.full_name} · ${row.student.student_code}`;

const stateLabel = (row) =>
  row.ends_at
    ? `Finalizado ${formatDate(row.ends_at)}`
    : row.is_active
      ? "Vigente"
      : "Desactivado";

/**
 * Estudiantes vinculados dentro de la ficha del encargado: relaciones actuales
 * e históricas dentro del alcance de quien consulta. Agregar crea el vínculo;
 * quitar lo finaliza con la fecha de hoy y conserva el historial.
 *
 * @param {object}   props
 * @param {object}   props.guardian
 * @param {Function} [props.onBusy] Recibe `true` mientras hay una escritura.
 */
export function GuardianStudentsSection({ guardian, onBusy }) {
  const queryClient = useQueryClient();
  const [actions, setActions] = useState({});
  const load = useCallback(
    async ({ page }) => {
      const payload = await guardiansService.linkedStudents(guardian.id, {
        page,
      });
      setActions(payload.actions ?? {});
      return payload;
    },
    [guardian.id]
  );
  const list = usePaginatedList(load, { canIncludeInactive: false });
  const [linking, setLinking] = useState(false);
  const [ending, setEnding] = useState(null);
  // `undefined`: aún no se decide; `null`: quitar sin nuevo principal.
  const [replacement, setReplacement] = useState(undefined);
  const [student, setStudent] = useState("");
  const [relationship, setRelationship] = useState("");
  const [busy, setBusy] = useState(false);
  const pending = useRef(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const search = useMemo(
    () => ({
      name: `guardian-${guardian.id}-student-candidates`,
      fetchPage: (params) =>
        guardiansService.studentCandidates(guardian.id, params),
      mapResult: (row) => ({
        value: row.public_id,
        label: `${row.full_name} · ${row.student_code}`,
      }),
    }),
    [guardian.id]
  );

  const setWriting = (value) => {
    pending.current = value;
    setBusy(value);
    onBusy?.(value);
  };
  const closePanels = () => {
    if (pending.current) return;
    setLinking(false);
    setEnding(null);
    setReplacement(undefined);
    setStudent("");
    setRelationship("");
    setError("");
  };
  const reload = (message) => {
    closePanels();
    setNotice(message);
    list.goToPage(1);
    list.refresh();
  };
  const write = async (request) => {
    if (pending.current) return false;
    setWriting(true);
    setError("");
    try {
      await request();
    } catch (failure) {
      setError(failure.message);
      setWriting(false);
      return false;
    }
    setWriting(false);
    // Each guardian has an isolated picker cache; a link change alters eligibility.
    void queryClient.invalidateQueries({
      predicate: (query) =>
        query.queryKey[0] === "search" && query.queryKey[1] === search.name,
    });
    return true;
  };

  const submitLink = async (event) => {
    event.preventDefault();
    if (!student || !relationship.trim()) {
      setError(
        "Seleccione un estudiante y complete el parentesco o responsabilidad."
      );
      return;
    }
    const saved = await write(() =>
      guardiansService.linkStudent(guardian.id, {
        student_public_id: student,
        relationship_label: relationship.trim(),
      })
    );
    if (saved) reload("Estudiante vinculado. El historial se conserva.");
  };
  const confirmEnd = async () => {
    const saved = await write(() =>
      studentsService.endGuardianRelation(
        ending.id,
        replacement ? { replacement_relation: replacement.id } : {}
      )
    );
    if (saved) reload("Vínculo finalizado. El historial se conserva.");
  };

  const canLink = actions.link_student === true && !list.error && !list.loading;
  const columns = [
    {
      key: "estudiante",
      label: "Estudiante",
      render: (row) =>
        busy ? (
          studentLabel(row)
        ) : (
          <Link
            component={RouterLink}
            to={`/app/alumnos/${row.student.public_id}`}
          >
            {studentLabel(row)}
          </Link>
        ),
    },
    {
      key: "parentesco",
      label: "Parentesco",
      render: (row) => row.relationship_label,
    },
    {
      key: "tipo",
      // "Principal" es por estudiante: este encargado puede serlo de varios.
      label: "Rol del encargado",
      // Un vínculo finalizado ya no es principal ni secundario de nadie.
      render: (row) =>
        row.ends_at ? (
          <MutedCell>—</MutedCell>
        ) : row.is_primary ? (
          "Principal"
        ) : (
          "Secundario"
        ),
    },
    {
      key: "desde",
      label: "Desde",
      render: (row) => (
        <Box component="span" sx={{ whiteSpace: "nowrap" }}>
          {formatDate(row.starts_at)}
        </Box>
      ),
    },
    {
      key: "estado",
      label: "Estado",
      render: (row) => (
        <StatusChip
          label={stateLabel(row)}
          variant={!row.ends_at && row.is_active ? "success" : "neutral"}
        />
      ),
    },
    {
      key: "acciones",
      label: "",
      align: "right",
      render: (row) =>
        row.actions?.end ? (
          <ActionIconButton
            disabled={busy}
            label={`Quitar vínculo con ${row.student.full_name}`}
            onClick={() => {
              closePanels();
              setNotice("");
              setEnding(row);
            }}
          >
            <DeleteOutlineIcon fontSize="small" />
          </ActionIconButton>
        ) : null,
    },
  ];

  return (
    <Box aria-label="Estudiantes vinculados" component="section" sx={{ mt: 3 }}>
      <Stack
        alignItems="center"
        direction="row"
        gap={1}
        justifyContent="space-between"
        sx={{ mb: 1 }}
      >
        <Box>
          <Typography
            component="h3"
            sx={{ fontSize: "0.9375rem", fontWeight: 600 }}
          >
            Estudiantes vinculados
          </Typography>
          <Typography color="text.secondary" variant="body2">
            Relaciones actuales e históricas dentro de su alcance.
          </Typography>
        </Box>
        {canLink && !linking ? (
          <Button
            disabled={busy}
            onClick={() => {
              closePanels();
              setNotice("");
              setLinking(true);
            }}
            size="small"
            startIcon={<AddIcon fontSize="small" />}
            variant="contained"
          >
            Agregar estudiante
          </Button>
        ) : null}
      </Stack>

      <Stack gap={2}>
        {notice ? (
          <Alert role="status" severity="success">
            {notice}
          </Alert>
        ) : null}

        {linking ? (
          <Stack
            aria-label="Vincular estudiante"
            component="form"
            gap={2}
            noValidate
            onSubmit={submitLink}
            sx={panelSx}
          >
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", sm: "3fr 2fr" },
                gap: 2,
              }}
            >
              <RemoteSearchSelect
                disabled={busy}
                helperText="Busque por nombre o código. Solo se ofrecen estudiantes que puede consultar y editar."
                key={guardian.id}
                label="Estudiante"
                name="student"
                onChange={(event) => setStudent(event.target.value)}
                required
                search={search}
                value={student}
              />
              <FormTextField
                disabled={busy}
                label="Parentesco o responsabilidad"
                onChange={(event) => setRelationship(event.target.value)}
                required
                value={relationship}
              />
            </Box>
            {error ? <Alert severity="error">{error}</Alert> : null}
            <Stack direction="row" gap={1} justifyContent="flex-end">
              <Button disabled={busy} onClick={closePanels}>
                Cancelar vínculo
              </Button>
              <Button disabled={busy} type="submit" variant="contained">
                Vincular estudiante
              </Button>
            </Stack>
          </Stack>
        ) : null}

        {ending ? (
          <Stack aria-label="Quitar vínculo" gap={2} sx={panelSx}>
            <Typography sx={{ fontWeight: 600 }}>
              Quitar vínculo con {ending.student.full_name}
            </Typography>
            {ending.actions?.offers_replacement && replacement === undefined ? (
              <ReplacementPicker
                onCancel={closePanels}
                onChoose={setReplacement}
                onSkip={() => setReplacement(null)}
                relation={ending}
                student={ending.student}
              />
            ) : (
              <>
                <Alert severity="warning">
                  El vínculo se finalizará con la fecha de hoy y terminará el
                  acceso asociado. El historial se conservará.
                  {replacement
                    ? ` Nuevo principal: ${fullName(replacement.guardian_detail)}.`
                    : ending.is_primary
                      ? " El estudiante quedará sin encargado principal."
                      : ""}
                </Alert>
                {error ? <Alert severity="error">{error}</Alert> : null}
                <Stack direction="row" gap={1} justifyContent="flex-end">
                  <Button disabled={busy} onClick={closePanels}>
                    Cancelar
                  </Button>
                  <Button
                    color="error"
                    disabled={busy}
                    onClick={confirmEnd}
                    variant="contained"
                  >
                    Quitar vínculo
                  </Button>
                </Stack>
              </>
            )}
          </Stack>
        ) : null}

        {list.error ? (
          <Alert role="alert" severity="error">
            {list.error}
            <Button disabled={busy} onClick={list.refresh}>
              Reintentar
            </Button>
          </Alert>
        ) : (
          <DataTable
            columns={columns}
            emptyMessage="No hay relaciones con estudiantes dentro de su alcance."
            getRowKey={(row) => row.id}
            loading={list.loading}
            pagination={
              list.count > list.pageSize
                ? {
                    ...list.pagination,
                    onPageChange: busy
                      ? () => {}
                      : list.pagination.onPageChange,
                  }
                : undefined
            }
            rows={list.items}
          />
        )}
      </Stack>
    </Box>
  );
}

const panelSx = {
  p: 2,
  border: "1px solid",
  borderColor: "divider",
  borderRadius: 1,
};
