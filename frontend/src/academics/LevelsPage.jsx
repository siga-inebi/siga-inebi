import { useCallback, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import UnfoldMoreOutlinedIcon from "@mui/icons-material/UnfoldMoreOutlined";

import { academicsService, PAGE_SIZE } from "@academics/academicsService.js";
import {
  AT_END,
  currentPosition,
  positionField,
  positionPayload,
} from "@academics/orderPosition.js";
import { useSubjectOptions } from "@academics/useSubjectOptions.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { suggestedOrBlank } from "@shared/crud/suggestion.js";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { ActionIconButton } from "@ui/buttons/ActionIconButton.jsx";
import { ConfirmActionButton } from "@ui/buttons/ConfirmActionButton.jsx";
import {
  ActiveCell,
  BooleanCell,
  CodeCell,
  MutedCell,
} from "@ui/table/cells.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";

const LEVEL_COLUMNS = [
  {
    key: "sequence",
    label: "Orden",
    align: "right",
    render: (row) => row.sequence,
  },
  { key: "name", label: "Nivel", render: (row) => row.name },
  {
    key: "code",
    label: "Codigo",
    render: (row) => <CodeCell value={row.code} />,
  },
  {
    key: "grade_count",
    label: "Grados",
    align: "right",
    render: (row) => row.grade_count,
  },
  {
    key: "subject_count",
    label: "Cursos",
    align: "right",
    render: (row) => row.subject_count,
  },
  {
    key: "is_active",
    label: "Estado",
    render: (row) => <ActiveCell active={row.is_active} />,
  },
];

const NAME_FIELD = {
  name: "name",
  label: "Nombre",
  required: true,
  placeholder: "Ejemplo: Basico",
};

const CODE_FIELD = {
  name: "code",
  label: "Codigo",
  help: "Se genera solo. Cambielo si el nivel ya se conoce por otro codigo.",
};

const createLevelFields = (levels) => [
  NAME_FIELD,
  CODE_FIELD,
  positionField(levels),
];

const editLevelFields = (levels, level) => [
  { name: "name", label: "Nombre", required: true },
  positionField(levels, level.public_id),
];

export function LevelsPage() {
  const loadLevels = useCallback(
    (params) => academicsService.listLevels(params),
    []
  );
  const list = usePaginatedList(loadLevels, { pageSize: PAGE_SIZE });

  const [editing, setEditing] = useState(null);
  const [selectedId, setSelectedId] = useState("");
  const [actionError, setActionError] = useState("");

  const selected =
    list.items.find((level) => level.public_id === selectedId) || null;

  const handleCreate = async ({ insert_after: position, ...payload }) => {
    await academicsService.createLevel({
      ...payload,
      ...positionPayload(position),
    });
    setEditing(null);
    list.refresh();
  };

  const handleUpdate = async ({ insert_after: position, ...payload }) => {
    await academicsService.updateLevel(editing.level.public_id, {
      ...payload,
      ...positionPayload(position),
    });
    setEditing(null);
    list.refresh();
  };

  const handleDeactivate = async (level) => {
    setActionError("");
    try {
      await academicsService.deactivateLevel(level.public_id);
      if (level.public_id === selectedId) setSelectedId("");
      list.refresh();
    } catch (requestError) {
      setActionError(requestError.message);
      throw requestError;
    }
  };

  return (
    <>
      <PageHeader
        breadcrumb="Estructura academica"
        subtitle="Cada nivel ordena su secuencia pedagogica, agrupa sus grados y declara los cursos que se imparten en el."
        title="Niveles, grados y plan de estudios"
      />

      <ListSection
        action={
          <Button
            onClick={async () =>
              setEditing({
                mode: "create",
                values: {
                  name: "",
                  code: await suggestedOrBlank(academicsService.nextLevelCode),
                  insert_after: AT_END,
                },
              })
            }
            size="small"
            startIcon={<AddIcon fontSize="small" />}
            variant="contained"
          >
            Nuevo nivel
          </Button>
        }
        actionError={actionError}
        list={list}
        columns={LEVEL_COLUMNS}
        emptyMessage="Todavia no hay niveles registrados."
        getRowKey={(level) => level.public_id}
        renderActions={(level) => (
          <Stack direction="row" gap={0.5} justifyContent="flex-end">
            <ActionIconButton
              color={level.public_id === selectedId ? "primary" : "default"}
              label={
                level.public_id === selectedId
                  ? "Ocultar detalle"
                  : "Abrir detalle"
              }
              onClick={() =>
                setSelectedId(
                  level.public_id === selectedId ? "" : level.public_id
                )
              }
            >
              <UnfoldMoreOutlinedIcon fontSize="small" />
            </ActionIconButton>
            <ActionIconButton
              label="Editar"
              onClick={() => setEditing({ mode: "edit", level })}
            >
              <EditOutlinedIcon fontSize="small" />
            </ActionIconButton>
            {level.is_active ? (
              <ConfirmActionButton
                confirmLabel="Si, desactivar"
                label="Desactivar"
                onConfirm={() => handleDeactivate(level)}
                question={`Se desactivara "${level.name}" junto con todos sus grados.`}
                title="Desactivar nivel"
              />
            ) : null}
          </Stack>
        )}
        subtitle="Niveles de la institucion"
        title="Niveles registrados"
      />

      {selected ? (
        <LevelGradesSection
          key={`grades-${selected.public_id}`}
          level={selected}
          onChanged={list.refresh}
        />
      ) : null}

      {selected ? (
        <LevelSubjectsSection
          key={`subjects-${selected.public_id}`}
          level={selected}
          onChanged={list.refresh}
        />
      ) : null}

      {editing?.mode === "create" ? (
        <EntityFormWindow
          description="La posicion define el orden pedagogico; los demas niveles se renumeran solos."
          fields={createLevelFields(list.items)}
          initialValues={editing.values}
          onCancel={() => setEditing(null)}
          onSubmit={handleCreate}
          open
          submitLabel="Crear nivel"
          title="Nuevo nivel"
        />
      ) : null}

      {editing?.mode === "edit" ? (
        <EntityFormWindow
          description={`El codigo ${editing.level.code} es inmutable.`}
          fields={editLevelFields(list.items, editing.level)}
          initialValues={{
            name: editing.level.name,
            insert_after: currentPosition(list.items, editing.level.public_id),
          }}
          key={editing.level.public_id}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          open
          submitLabel="Guardar cambios"
          title={`Editar ${editing.level.name}`}
        />
      ) : null}
    </>
  );
}

const GRADE_COLUMNS = [
  {
    key: "sequence",
    label: "Orden",
    align: "right",
    render: (row) => row.sequence,
  },
  { key: "name", label: "Grado", render: (row) => row.name },
  {
    key: "code",
    label: "Codigo",
    render: (row) => <CodeCell value={row.code} />,
  },
  {
    key: "is_active",
    label: "Estado",
    render: (row) => <ActiveCell active={row.is_active} />,
  },
];

const createGradeFields = (grades) => [
  {
    name: "name",
    label: "Nombre",
    required: true,
    placeholder: "Ejemplo: Primero Basico",
  },
  {
    name: "code",
    label: "Codigo",
    help: "Se deriva del codigo del nivel. Cambielo solo si hace falta.",
  },
  positionField(grades),
];

const editGradeFields = (grades, grade) => [
  { name: "name", label: "Nombre", required: true },
  positionField(grades, grade.public_id),
];

function LevelGradesSection({ level, onChanged }) {
  const loadGrades = useCallback(
    (params) => academicsService.listLevelGrades(level.public_id, params),
    [level.public_id]
  );
  const list = usePaginatedList(loadGrades, { pageSize: PAGE_SIZE });

  const [editing, setEditing] = useState(null);
  const [actionError, setActionError] = useState("");

  const afterChange = () => {
    setEditing(null);
    list.refresh();
    onChanged();
  };

  const handleCreate = async ({ insert_after: position, ...payload }) => {
    await academicsService.createGrade(level.public_id, {
      ...payload,
      ...positionPayload(position),
    });
    afterChange();
  };

  const handleUpdate = async ({ insert_after: position, ...payload }) => {
    await academicsService.updateGrade(editing.grade.public_id, {
      ...payload,
      ...positionPayload(position),
    });
    afterChange();
  };

  const handleDeactivate = async (grade) => {
    setActionError("");
    try {
      await academicsService.deactivateGrade(grade.public_id);
      afterChange();
    } catch (requestError) {
      setActionError(requestError.message);
      throw requestError;
    }
  };

  return (
    <>
      <ListSection
        action={
          <Button
            onClick={async () =>
              setEditing({
                mode: "create",
                values: {
                  name: "",
                  code: await suggestedOrBlank(() =>
                    academicsService.nextGradeCode(level.public_id)
                  ),
                  insert_after: AT_END,
                },
              })
            }
            size="small"
            startIcon={<AddIcon fontSize="small" />}
            variant="contained"
          >
            Nuevo grado
          </Button>
        }
        actionError={actionError}
        list={list}
        columns={GRADE_COLUMNS}
        emptyMessage="Este nivel todavia no tiene grados."
        getRowKey={(grade) => grade.public_id}
        renderActions={(grade) => (
          <Stack direction="row" gap={0.5} justifyContent="flex-end">
            <ActionIconButton
              label="Editar"
              onClick={() => setEditing({ mode: "edit", grade })}
            >
              <EditOutlinedIcon fontSize="small" />
            </ActionIconButton>
            {grade.is_active ? (
              <ConfirmActionButton
                confirmLabel="Si, desactivar"
                label="Desactivar"
                onConfirm={() => handleDeactivate(grade)}
                question={`Se desactivara el grado "${grade.name}".`}
                title="Desactivar grado"
              />
            ) : null}
          </Stack>
        )}
        subtitle={level.name}
        title="Grados del nivel"
      />

      {editing?.mode === "create" ? (
        <EntityFormWindow
          description="El codigo del grado es unico en toda la institucion y se deriva del nivel."
          fields={createGradeFields(list.items)}
          initialValues={editing.values}
          onCancel={() => setEditing(null)}
          onSubmit={handleCreate}
          open
          submitLabel="Crear grado"
          title={`Nuevo grado en ${level.name}`}
        />
      ) : null}

      {editing?.mode === "edit" ? (
        <EntityFormWindow
          description="Solo cambian el nombre y el orden; el codigo es inmutable."
          fields={editGradeFields(list.items, editing.grade)}
          initialValues={{
            name: editing.grade.name,
            insert_after: currentPosition(list.items, editing.grade.public_id),
          }}
          key={editing.grade.public_id}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          open
          submitLabel="Guardar cambios"
          title={`Editar ${editing.grade.name}`}
        />
      ) : null}
    </>
  );
}

const LEVEL_SUBJECT_COLUMNS = [
  { key: "subject", label: "Curso", render: (row) => row.subject.name },
  {
    key: "code",
    label: "Codigo",
    render: (row) => <CodeCell value={row.subject.code} />,
  },
  {
    key: "is_required",
    label: "Obligatorio",
    render: (row) => <BooleanCell value={row.is_required} />,
  },
  {
    key: "weekly_hours",
    label: "Horas semanales",
    align: "right",
    render: (row) => row.weekly_hours || <MutedCell>Sin definir</MutedCell>,
  },
];

const LINK_FIELDS = [
  { name: "is_required", label: "Es obligatorio", type: "checkbox" },
  { name: "weekly_hours", label: "Horas semanales", type: "number", min: 0 },
];

/**
 * Plan de estudios del nivel. El endpoint de vinculos no acepta
 * `include_inactive`: desvincular borra el vinculo, no lo desactiva.
 */
function LevelSubjectsSection({ level, onChanged }) {
  const loadLevelSubjects = useCallback(
    (params) => academicsService.listLevelSubjects(level.public_id, params),
    [level.public_id]
  );
  const list = usePaginatedList(loadLevelSubjects, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });
  const { subjects, error: subjectsError } = useSubjectOptions();

  const [editing, setEditing] = useState(null);
  const [actionError, setActionError] = useState("");

  const linkedIds = new Set(list.items.map((link) => link.subject.public_id));
  const available = subjects.filter(
    (subject) => subject.is_active && !linkedIds.has(subject.public_id)
  );

  const afterChange = () => {
    setEditing(null);
    list.refresh();
    onChanged();
  };

  const handleLink = async (payload) => {
    await academicsService.linkSubjectToLevel(level.public_id, payload);
    afterChange();
  };

  const handleUpdate = async (payload) => {
    await academicsService.updateLevelSubject(
      level.public_id,
      editing.link.subject.public_id,
      payload
    );
    afterChange();
  };

  const handleUnlink = async (link) => {
    setActionError("");
    try {
      await academicsService.unlinkSubjectFromLevel(
        level.public_id,
        link.subject.public_id
      );
      afterChange();
    } catch (requestError) {
      setActionError(requestError.message);
      throw requestError;
    }
  };

  return (
    <>
      <ListSection
        action={
          <Button
            disabled={!available.length}
            onClick={() => setEditing({ mode: "create" })}
            size="small"
            startIcon={<AddIcon fontSize="small" />}
            variant="contained"
          >
            Vincular curso
          </Button>
        }
        actionError={actionError || subjectsError}
        list={list}
        columns={LEVEL_SUBJECT_COLUMNS}
        emptyMessage="Este nivel todavia no tiene cursos vinculados."
        getRowKey={(link) => link.public_id}
        renderActions={(link) => (
          <Stack direction="row" gap={0.5} justifyContent="flex-end">
            <ActionIconButton
              label="Editar"
              onClick={() => setEditing({ mode: "edit", link })}
            >
              <EditOutlinedIcon fontSize="small" />
            </ActionIconButton>
            <ConfirmActionButton
              confirmLabel="Si, desvincular"
              label="Desvincular"
              onConfirm={() => handleUnlink(link)}
              question={`Se quitara "${link.subject.name}" del plan de estudios de ${level.name}. El curso sigue existiendo en el catalogo.`}
              title="Desvincular curso"
            />
          </Stack>
        )}
        showInactiveToggle={false}
        subtitle={level.name}
        title="Plan de estudios"
      />

      {!available.length && !list.loading ? (
        <Alert severity="info" variant="outlined">
          Todos los cursos activos ya estan vinculados a este nivel.
        </Alert>
      ) : null}

      <EntityFormWindow
        description="Declara que el curso se imparte en este nivel. 0 horas significa sin definir."
        fields={[
          {
            name: "subject_id",
            label: "Curso",
            type: "select",
            required: true,
            options: available.map((subject) => ({
              value: subject.public_id,
              label: `${subject.name} (${subject.code})`,
            })),
          },
          ...LINK_FIELDS,
        ]}
        initialValues={{ subject_id: "", is_required: true, weekly_hours: 0 }}
        key={
          editing?.mode === "create" ? "link-create-open" : "link-create-closed"
        }
        onCancel={() => setEditing(null)}
        onSubmit={handleLink}
        open={editing?.mode === "create"}
        submitLabel="Vincular"
        title={`Vincular curso a ${level.name}`}
      />

      {editing?.mode === "edit" ? (
        <EntityFormWindow
          fields={LINK_FIELDS}
          initialValues={{
            is_required: editing.link.is_required,
            weekly_hours: editing.link.weekly_hours,
          }}
          key={editing.link.public_id}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          open
          submitLabel="Guardar cambios"
          title={`Editar ${editing.link.subject.name} en ${level.name}`}
        />
      ) : null}
    </>
  );
}
