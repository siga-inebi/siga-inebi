import { useNavigate } from "react-router-dom";

import { useState } from "react";

import Avatar from "@mui/material/Avatar";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import AddIcon from "@mui/icons-material/Add";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";
import PersonOutlineIcon from "@mui/icons-material/PersonOutline";

import {
  STUDENT_FIELDS,
  STATUS_LABEL,
  STATUS_VARIANT,
  fullName,
  personPayload,
} from "./studentPresentation.js";

import { studentsService } from "@students/studentsService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { suggestedOrBlank } from "@shared/crud/suggestion.js";
import { useServerList } from "@shared/crud/useServerList.js";
import { downloadCsv } from "@shared/utils/csv.js";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { SearchField } from "@ui/filters/SearchField.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";
import { ViewDetailButton } from "@ui/table/ViewDetailButton.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";

export function AlumnosPage() {
  // Solo la pagina visible: la busqueda (nombre, codigo o CUI) y la
  // paginacion las resuelve el backend, no el navegador.
  const list = useServerList({
    queryKey: queryKeys.students.all,
    fetchPage: studentsService.listPage,
  });

  const navigate = useNavigate();
  const [creating, setCreating] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");
  const handleSelect = (student) =>
    navigate(`/app/alumnos/${student.public_id}`);

  // La exportacion si recorre todas las paginas, con la busqueda vigente.
  const handleExport = async () => {
    setExporting(true);
    setExportError("");
    try {
      const rows = await studentsService.list(list.exportParams);
      downloadCsv(
        "alumnos.csv",
        [
          { label: "Nombre", value: fullName },
          { label: "Codigo", value: (item) => item.student_code },
          {
            label: "Estado",
            value: (item) => STATUS_LABEL[item.status] ?? item.status,
          },
        ],
        rows
      );
    } catch (requestError) {
      setExportError(requestError.message);
    } finally {
      setExporting(false);
    }
  };

  const handleCreate = async (values) => {
    await studentsService.create({
      person: personPayload(values),
      student_code: values.student_code,
      status: "pre_enrolled",
      photo: values.photo,
    });
    list.refresh();
    setCreating(null);
  };

  const columns = [
    {
      key: "foto",
      label: "Foto",
      render: (student) =>
        student.photo ? (
          <Avatar
            imgProps={{ decoding: "async", loading: "lazy" }}
            src={student.photo}
            sx={{ width: 32, height: 32 }}
            variant="rounded"
          />
        ) : (
          <Avatar sx={{ width: 32, height: 32 }} variant="rounded">
            <PersonOutlineIcon fontSize="small" />
          </Avatar>
        ),
    },
    { key: "nombre", label: "Nombre completo", render: fullName },
    {
      key: "codigo",
      label: "Codigo",
      render: (student) => student.student_code,
    },
    {
      key: "estado",
      label: "Estado",
      render: (student) => (
        <StatusChip
          label={STATUS_LABEL[student.status] ?? student.status}
          variant={STATUS_VARIANT[student.status] ?? "neutral"}
        />
      ),
    },
    {
      key: "detalle",
      label: "Detalle",
      align: "right",
      render: (student) => (
        <ViewDetailButton
          label={`Ver detalle de ${fullName(student)}`}
          onClick={() => handleSelect(student)}
        />
      ),
    },
  ];

  return (
    <>
      <PageHeader
        action={
          <Button
            onClick={async () =>
              setCreating({
                ...EMPTY_STUDENT,
                student_code: await suggestedOrBlank(studentsService.nextCode),
              })
            }
            startIcon={<AddIcon fontSize="small" />}
            variant="contained"
          >
            Nuevo estudiante
          </Button>
        }
        breadcrumb="Comunidad educativa"
        subtitle={`${list.count} registros dentro de tu alcance.`}
        title="Estudiantes"
      />

      <SectionCard fillHeight>
        <FilterBar
          actions={
            <Button
              disabled={exporting}
              onClick={handleExport}
              size="small"
              startIcon={<FileDownloadOutlinedIcon fontSize="small" />}
              variant="outlined"
            >
              {exporting ? "Exportando…" : "Exportar CSV"}
            </Button>
          }
        >
          <SearchField
            onChange={list.setSearch}
            placeholder="Buscar por nombre, codigo o CUI…"
            value={list.search}
          />
        </FilterBar>

        {list.error || exportError ? (
          <Alert
            role="alert"
            severity="error"
            sx={{ mx: { xs: 1.5, md: 2 }, mt: 1.5 }}
          >
            {list.error || exportError}
          </Alert>
        ) : null}

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
            onRowClick={handleSelect}
            pagination={list.pagination}
            rows={list.items}
          />
        </SectionTableArea>
      </SectionCard>

      {creating ? (
        <EntityFormWindow
          description="El codigo se emite solo; el resto es lo que hay que capturar."
          fields={STUDENT_FIELDS}
          initialValues={creating}
          onCancel={() => setCreating(null)}
          onSubmit={handleCreate}
          open
          submitLabel="Crear estudiante"
          title="Nuevo estudiante"
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
  cui: "",
  birth_date: "",
  sex: "",
  nationality: "Guatemalteca",
  address: "",
  department: "",
  municipality: "",
  student_code: "",
  photo: null,
};
