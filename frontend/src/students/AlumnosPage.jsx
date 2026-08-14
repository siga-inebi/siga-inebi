import { useCallback, useState } from "react";

import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ButtonBase from "@mui/material/ButtonBase";
import AddIcon from "@mui/icons-material/Add";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";
import PersonOutlineIcon from "@mui/icons-material/PersonOutline";

import { studentsService } from "@students/studentsService.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { useLocalList } from "@shared/crud/useLocalList.js";
import { downloadCsv } from "@shared/utils/csv.js";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { SearchField } from "@ui/filters/SearchField.jsx";
import { ImageDialog } from "@ui/display/ImageDialog.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";
import { MutedCell } from "@ui/table/cells.jsx";
import { DetailWindow } from "@ui/layout/DetailWindow.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";

const STUDENT_FIELDS = [
  { name: "first_name", label: "Nombres", required: true },
  { name: "last_name", label: "Apellidos", required: true },
  { name: "email", label: "Correo (opcional)", type: "email" },
  { name: "phone_number", label: "Telefono (opcional)", type: "tel" },
  { name: "student_code", label: "Codigo de estudiante", required: true },
  { name: "photo", label: "Foto (opcional)", type: "file", accept: "image/*" },
];

/** Estados de expediente del estudiante -> variante semantica de chip. */
const STATUS_VARIANT = {
  enrolled: "success",
  pre_enrolled: "primary",
  withdrawn: "danger",
  suspended: "warning",
  graduated: "purple",
};

function fullName(student) {
  return `${student.person.first_name} ${student.person.last_name}`.trim();
}

export function AlumnosPage() {
  const loadStudents = useCallback(() => studentsService.list(), []);
  const matches = useCallback(
    (student, query) => fullName(student).toLowerCase().includes(query),
    []
  );
  const list = useLocalList(loadStudents, { matches });

  const [selected, setSelected] = useState(null);
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);
  const [viewingPhoto, setViewingPhoto] = useState(null);

  const handleExport = () => {
    downloadCsv(
      "alumnos.csv",
      [
        { label: "Nombre", value: fullName },
        { label: "Codigo", value: (item) => item.student_code },
        { label: "Estado", value: (item) => item.status },
      ],
      list.filtered
    );
  };

  const handleCreate = async (values) => {
    const created = await studentsService.create({
      person: {
        first_name: values.first_name,
        last_name: values.last_name,
        email: values.email,
        phone_number: values.phone_number,
      },
      student_code: values.student_code,
      status: "pre_enrolled",
      photo: values.photo,
    });
    list.addItem(created);
    setCreating(false);
  };

  const handleUpdate = async (values) => {
    const updated = await studentsService.update(editing.id, {
      person: {
        id: editing.person.id,
        first_name: values.first_name,
        last_name: values.last_name,
        email: values.email,
        phone_number: values.phone_number,
      },
      student_code: values.student_code,
      photo: values.photo,
    });
    list.replaceItem(updated, (item) => item.id === updated.id);
    setSelected(updated);
    setEditing(null);
  };

  const columns = [
    {
      key: "foto",
      label: "Foto",
      render: (student) =>
        student.photo ? (
          <Avatar src={student.photo} sx={{ width: 32, height: 32 }} variant="rounded" />
        ) : (
          <Avatar sx={{ width: 32, height: 32 }} variant="rounded">
            <PersonOutlineIcon fontSize="small" />
          </Avatar>
        ),
    },
    { key: "nombre", label: "Nombre completo", render: fullName },
    { key: "codigo", label: "Codigo", render: (student) => student.student_code },
    {
      key: "estado",
      label: "Estado",
      render: (student) => (
        <StatusChip
          label={student.status}
          variant={STATUS_VARIANT[student.status] ?? "neutral"}
        />
      ),
    },
  ];

  return (
    <>
      <PageHeader
        action={
          <Button
            onClick={() => setCreating(true)}
            startIcon={<AddIcon fontSize="small" />}
            variant="contained"
          >
            Nuevo estudiante
          </Button>
        }
        breadcrumb="Comunidad educativa"
        subtitle={`${list.filtered.length} de ${list.all.length} registros dentro de tu alcance.`}
        title="Estudiantes"
      />

      <SectionCard fillHeight>
        <FilterBar
          actions={
            <Button
              onClick={handleExport}
              size="small"
              startIcon={<FileDownloadOutlinedIcon fontSize="small" />}
              variant="outlined"
            >
              Exportar CSV
            </Button>
          }
        >
          <SearchField
            onChange={list.setSearch}
            placeholder="Buscar por nombre…"
            value={list.search}
          />
        </FilterBar>

        <SectionTableArea>
          <DataTable
            columns={columns}
            emptyMessage={
              list.search
                ? "Sin resultados para la busqueda."
                : "Todavia no hay estudiantes registrados."
            }
            fillHeight
            loading={list.loading}
            onRowClick={setSelected}
            pagination={list.pagination}
            rows={list.items}
          />
        </SectionTableArea>
      </SectionCard>

      <DetailWindow
        actions={
          selected ? (
            <Button onClick={() => setEditing(selected)} variant="contained">
              Editar
            </Button>
          ) : null
        }
        fields={
          selected
            ? [
                { label: "Nombre completo", value: fullName(selected) },
                { label: "Codigo de estudiante", value: selected.student_code },
                {
                  label: "Estado",
                  value: (
                    <StatusChip
                      label={selected.status}
                      variant={STATUS_VARIANT[selected.status] ?? "neutral"}
                    />
                  ),
                },
                { label: "Correo", value: selected.person.email },
                { label: "Telefono", value: selected.person.phone_number },
                {
                  label: "Foto",
                  value: selected.photo ? (
                    <ButtonBase
                      onClick={() => setViewingPhoto(selected.photo)}
                      sx={(theme) => ({ borderRadius: theme.tokens.radii.chip, mt: 0.5 })}
                    >
                      <Box
                        alt={`Foto de ${fullName(selected)}`}
                        component="img"
                        src={selected.photo}
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
                    <MutedCell>Sin foto</MutedCell>
                  ),
                },
              ]
            : []
        }
        onClose={() => {
          setSelected(null);
          setViewingPhoto(null);
        }}
        open={Boolean(selected)}
        title={selected ? fullName(selected) : ""}
      />

      <ImageDialog
        alt={selected ? fullName(selected) : ""}
        downloadName={viewingPhoto?.split("/").pop()}
        onClose={() => setViewingPhoto(null)}
        open={Boolean(viewingPhoto)}
        src={viewingPhoto ?? ""}
      />

      <EntityFormWindow
        fields={STUDENT_FIELDS}
        initialValues={EMPTY_STUDENT}
        key={creating ? "create-open" : "create-closed"}
        onCancel={() => setCreating(false)}
        onSubmit={handleCreate}
        open={creating}
        submitLabel="Crear estudiante"
        title="Nuevo estudiante"
      />

      {editing ? (
        <EntityFormWindow
          fields={STUDENT_FIELDS}
          initialValues={{
            first_name: editing.person.first_name,
            last_name: editing.person.last_name,
            email: editing.person.email ?? "",
            phone_number: editing.person.phone_number ?? "",
            student_code: editing.student_code,
            photo: null,
          }}
          key={editing.id}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          open
          submitLabel="Guardar cambios"
          title={`Editar ${fullName(editing)}`}
        />
      ) : null}
    </>
  );
}

const EMPTY_STUDENT = {
  first_name: "",
  last_name: "",
  email: "",
  phone_number: "",
  student_code: "",
  photo: null,
};
