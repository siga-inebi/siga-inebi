import { lazy, Suspense, useState } from "react";
import { useSearchParams } from "react-router-dom";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";

import { academicsService } from "@academics/academicsService.js";
import {
  CatalogFilters,
  DetailToggleButton,
} from "@academics/CatalogFilters.jsx";
import { SEQUENCE_ORDERING } from "@academics/catalogOrdering.js";
import {
  AT_END,
  currentPosition,
  positionField,
  positionPayload,
} from "@academics/orderPosition.js";
import { SUBJECT_SEARCH } from "@academics/searchOptions.js";
import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { useResourceQuery } from "@shared/api/useResourceQuery.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { suggestedOrBlank } from "@shared/crud/suggestion.js";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { useServerList } from "@shared/crud/useServerList.js";
import { ActionIconButton } from "@ui/buttons/ActionIconButton.jsx";
import { ConfirmActionButton } from "@ui/buttons/ConfirmActionButton.jsx";
import {
  ActiveCell,
  BooleanCell,
  CodeCell,
  MutedCell,
} from "@ui/table/cells.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";

const BulkLevelSubjectsWindow = lazy(() =>
  import("./BulkLevelSubjectsWindow.jsx").then((module) => ({
    default: module.BulkLevelSubjectsWindow,
  }))
);

/**
 * Hermanos para el campo "Posición": una sola página, en orden pedagógico.
 * Los niveles y los grados de un nivel son pocos; el listado visible puede
 * estar buscado, reordenado o paginado y no sirve para ubicar uno nuevo.
 */
const SIBLINGS_PAGE = { page: 1, page_size: 100, ordering: "sequence" };

async function loadSiblings(fetchPage) {
  try {
    const page = await fetchPage(SIBLINGS_PAGE);
    return page?.results ?? [];
  } catch {
    // Sin hermanos el formulario igual abre: "Al final" siempre es válido.
    return [];
  }
}

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
    label: "Código",
    render: (row) => <CodeCell value={row.code} />,
  },
  {
    key: "subject_count",
    label: "Cursos del nivel",
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
  placeholder: "Ejemplo: Básico",
};

const CODE_FIELD = {
  name: "code",
  label: "Código",
  help: "Se genera solo. Cámbielo si el nivel ya se conoce por otro código.",
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

/** Cambia el elemento elegido en la URL y limpia la vista de su detalle. */
function useSelectedParam(name, detailPrefixes) {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedId = searchParams.get(name) ?? "";
  const setSelectedId = (id) =>
    setSearchParams(
      (current) => {
        const next = new URLSearchParams(current);
        for (const key of [...next.keys()]) {
          if (detailPrefixes.some((prefix) => key.startsWith(prefix))) {
            next.delete(key);
          }
        }
        if (id) next.set(name, id);
        else next.delete(name);
        return next;
      },
      { replace: true }
    );
  return [selectedId, setSelectedId];
}

/**
 * Niveles, sus grados y sus cursos (N1–N3). Los tres listados se piden por
 * página al servidor; el nivel elegido vive en la URL (`?nivel=<id>`).
 *
 * "Cursos del nivel" es el vínculo nivel ↔ curso con sus horas semanales. NO es
 * el plan de estudios de un ciclo, que se define por grado dentro de cada ciclo
 * escolar y es el que exige la activación (N2).
 */
export function LevelsPage() {
  const { can } = usePermissions();
  const canEdit = can(PERMISSION.SCOPE_ASSIGN);
  const list = useServerList({
    queryKey: queryKeys.academics.list("levels"),
    fetchPage: (params) => academicsService.listLevels(params),
    defaultOrdering: "sequence",
    canIncludeInactive: true,
  });

  const [editing, setEditing] = useState(null);
  const [actionError, setActionError] = useState("");
  const [selectedId, setSelectedId] = useSelectedParam("nivel", [
    "grades_",
    "level_subjects_",
  ]);
  const toggle = (level) =>
    setSelectedId(level.public_id === selectedId ? "" : level.public_id);

  const inPage =
    list.items.find((level) => level.public_id === selectedId) || null;
  const fallback = useResourceQuery(
    queryKeys.academics.list("level", selectedId),
    () => academicsService.getLevel(selectedId),
    { enabled: Boolean(selectedId) && !inPage && !list.loading }
  );
  const selected = inPage ?? (selectedId ? fallback.data : null) ?? null;

  const siblings = () => loadSiblings(academicsService.listLevels);

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
        breadcrumb="Estructura académica"
        subtitle="Cada nivel ordena su secuencia pedagógica, agrupa sus grados y declara los cursos que se imparten en él."
        title="Niveles, grados y cursos del nivel"
      />

      <ListSection
        action={
          canEdit ? (
            <Button
              onClick={async () => {
                const [code, levels] = await Promise.all([
                  suggestedOrBlank(academicsService.nextLevelCode),
                  siblings(),
                ]);
                setEditing({
                  mode: "create",
                  siblings: levels,
                  values: { name: "", code, insert_after: AT_END },
                });
              }}
              size="small"
              startIcon={<AddIcon fontSize="small" />}
              variant="contained"
            >
              Nuevo nivel
            </Button>
          ) : null
        }
        actionError={actionError}
        list={list}
        columns={LEVEL_COLUMNS}
        emptyMessage={
          list.search
            ? "Sin niveles para los filtros seleccionados."
            : "Todavía no hay niveles registrados."
        }
        filters={
          <CatalogFilters
            list={list}
            orderingOptions={SEQUENCE_ORDERING}
            placeholder="Buscar nivel por nombre o código"
          />
        }
        getRowKey={(level) => level.public_id}
        onRowClick={toggle}
        renderActions={(level) => (
          <Stack
            alignItems="center"
            direction="row"
            gap={0.5}
            justifyContent="flex-end"
          >
            <DetailToggleButton
              count={level.grade_count}
              noun="grados"
              onToggle={() => toggle(level)}
              open={level.public_id === selectedId}
            />
            {canEdit ? (
              <ActionIconButton
                label="Editar"
                onClick={async () =>
                  setEditing({
                    mode: "edit",
                    level,
                    siblings: await siblings(),
                  })
                }
              >
                <EditOutlinedIcon fontSize="small" />
              </ActionIconButton>
            ) : null}
            {canEdit && level.is_active ? (
              <ConfirmActionButton
                confirmLabel="Sí, desactivar"
                label="Desactivar"
                onConfirm={() => handleDeactivate(level)}
                question={`Se desactivará "${level.name}" junto con todos sus grados.`}
                title="Desactivar nivel"
              />
            ) : null}
          </Stack>
        )}
        subtitle="Elija «Ver grados» o haga clic en un nivel para ver sus grados y los cursos del nivel."
        title="Niveles registrados"
      />

      {selected ? (
        <LevelGradesSection
          canEdit={canEdit}
          key={`grades-${selected.public_id}`}
          level={selected}
          onChanged={list.refresh}
        />
      ) : null}

      {selected ? (
        <LevelSubjectsSection
          canEdit={canEdit}
          key={`subjects-${selected.public_id}`}
          level={selected}
          onChanged={list.refresh}
        />
      ) : null}

      {editing?.mode === "create" ? (
        <EntityFormWindow
          description="La posición define el orden pedagógico; los demás niveles se renumeran solos."
          fields={createLevelFields(editing.siblings)}
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
          description={`El código ${editing.level.code} no se puede cambiar.`}
          fields={editLevelFields(editing.siblings, editing.level)}
          initialValues={{
            name: editing.level.name,
            insert_after: currentPosition(
              editing.siblings,
              editing.level.public_id
            ),
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
    label: "Código",
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
    placeholder: "Ejemplo: Primero Básico",
  },
  {
    name: "code",
    label: "Código",
    help: "Se deriva del código del nivel. Cámbielo solo si hace falta.",
  },
  positionField(grades),
];

const editGradeFields = (grades, grade) => [
  { name: "name", label: "Nombre", required: true },
  positionField(grades, grade.public_id),
];

function LevelGradesSection({ canEdit, level, onChanged }) {
  const list = useServerList({
    queryKey: queryKeys.academics.list("grades", level.public_id),
    fetchPage: (params) =>
      academicsService.listLevelGrades(level.public_id, params),
    defaultOrdering: "sequence",
    canIncludeInactive: true,
    urlPrefix: "grades_",
  });

  const [editing, setEditing] = useState(null);
  const [actionError, setActionError] = useState("");

  const siblings = () =>
    loadSiblings((params) =>
      academicsService.listLevelGrades(level.public_id, params)
    );

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
          canEdit ? (
            <Button
              onClick={async () => {
                const [code, grades] = await Promise.all([
                  suggestedOrBlank(() =>
                    academicsService.nextGradeCode(level.public_id)
                  ),
                  siblings(),
                ]);
                setEditing({
                  mode: "create",
                  siblings: grades,
                  values: { name: "", code, insert_after: AT_END },
                });
              }}
              size="small"
              startIcon={<AddIcon fontSize="small" />}
              variant="contained"
            >
              Nuevo grado
            </Button>
          ) : null
        }
        actionError={actionError}
        list={list}
        columns={GRADE_COLUMNS}
        emptyMessage={
          list.search
            ? "Sin grados para los filtros seleccionados."
            : "Este nivel todavía no tiene grados."
        }
        filters={
          <CatalogFilters
            list={list}
            orderingOptions={SEQUENCE_ORDERING}
            placeholder="Buscar grado por nombre o código"
          />
        }
        getRowKey={(grade) => grade.public_id}
        renderActions={
          canEdit
            ? (grade) => (
                <Stack direction="row" gap={0.5} justifyContent="flex-end">
                  <ActionIconButton
                    label="Editar"
                    onClick={async () =>
                      setEditing({
                        mode: "edit",
                        grade,
                        siblings: await siblings(),
                      })
                    }
                  >
                    <EditOutlinedIcon fontSize="small" />
                  </ActionIconButton>
                  {grade.is_active ? (
                    <ConfirmActionButton
                      confirmLabel="Sí, desactivar"
                      label="Desactivar"
                      onConfirm={() => handleDeactivate(grade)}
                      question={`Se desactivará el grado "${grade.name}".`}
                      title="Desactivar grado"
                    />
                  ) : null}
                </Stack>
              )
            : undefined
        }
        subtitle={level.name}
        title={`Grados de ${level.name}`}
      />

      {editing?.mode === "create" ? (
        <EntityFormWindow
          description="El código del grado es único en toda la institución y se deriva del nivel."
          fields={createGradeFields(editing.siblings)}
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
          description="Solo cambian el nombre y el orden; el código no se puede cambiar."
          fields={editGradeFields(editing.siblings, editing.grade)}
          initialValues={{
            name: editing.grade.name,
            insert_after: currentPosition(
              editing.siblings,
              editing.grade.public_id
            ),
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
    label: "Código",
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

const LINK_CREATE_FIELDS = [
  {
    name: "subject_id",
    label: "Curso",
    type: "search-select",
    required: true,
    search: SUBJECT_SEARCH,
    help: "Escriba el nombre o el código del curso.",
    span: "full",
  },
  ...LINK_FIELDS,
];

/**
 * Cursos del nivel (antes "Plan de estudios", N2): que cursos se imparten en
 * el nivel y con cuantas horas semanales. El endpoint de vinculos no acepta
 * `include_inactive`: desvincular borra el vinculo, no lo desactiva.
 *
 * El curso se elige con busqueda en el servidor: ya no se descarga el catalogo
 * completo de cursos. Si el curso ya estaba vinculado, el backend lo rechaza y
 * el motivo se muestra en el formulario.
 */
function LevelSubjectsSection({ canEdit, level, onChanged }) {
  const list = useServerList({
    queryKey: queryKeys.academics.list("level-subjects", level.public_id),
    fetchPage: (params) =>
      academicsService.listLevelSubjects(level.public_id, params),
    urlPrefix: "level_subjects_",
  });

  const [editing, setEditing] = useState(null);
  const [batching, setBatching] = useState(false);
  const [actionError, setActionError] = useState("");

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
      <Alert severity="info" variant="outlined">
        «Cursos del nivel» dice qué cursos se imparten en {level.name} y con
        cuántas horas. El plan de estudios que exige la activación se define por
        grado en cada ciclo: Ciclo escolar → detalle del ciclo → pestaña «Plan
        de estudios».
      </Alert>

      <ListSection
        action={
          canEdit ? (
            <Stack direction="row" gap={1}>
              <Button
                onClick={() => setBatching(true)}
                size="small"
                startIcon={<AddIcon fontSize="small" />}
                variant="contained"
              >
                Vincular por lote
              </Button>
              <Button
                onClick={() => setEditing({ mode: "create" })}
                size="small"
              >
                Vincular curso
              </Button>
            </Stack>
          ) : null
        }
        actionError={actionError}
        list={list}
        columns={LEVEL_SUBJECT_COLUMNS}
        emptyMessage="Este nivel todavía no tiene cursos vinculados."
        getRowKey={(link) => link.public_id}
        renderActions={
          canEdit
            ? (link) => (
                <Stack direction="row" gap={0.5} justifyContent="flex-end">
                  <ActionIconButton
                    label="Editar"
                    onClick={() => setEditing({ mode: "edit", link })}
                  >
                    <EditOutlinedIcon fontSize="small" />
                  </ActionIconButton>
                  <ConfirmActionButton
                    confirmLabel="Sí, desvincular"
                    label="Desvincular"
                    onConfirm={() => handleUnlink(link)}
                    question={`Se quitará "${link.subject.name}" de los cursos de ${level.name}. El curso sigue existiendo en el catálogo.`}
                    title="Desvincular curso"
                  />
                </Stack>
              )
            : undefined
        }
        showInactiveToggle={false}
        subtitle={level.name}
        title="Cursos del nivel"
      />

      {editing?.mode === "create" ? (
        <EntityFormWindow
          description="Declara que el curso se imparte en este nivel. 0 horas significa sin definir."
          fields={LINK_CREATE_FIELDS}
          initialValues={{
            subject_id: "",
            is_required: true,
            weekly_hours: 0,
          }}
          onCancel={() => setEditing(null)}
          onSubmit={handleLink}
          open
          submitLabel="Vincular"
          title={`Vincular curso a ${level.name}`}
        />
      ) : null}

      {batching ? (
        <Suspense fallback={null}>
          <BulkLevelSubjectsWindow
            level={level}
            onCancel={() => setBatching(false)}
            onCreated={() => {
              setBatching(false);
              afterChange();
            }}
          />
        </Suspense>
      ) : null}

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
