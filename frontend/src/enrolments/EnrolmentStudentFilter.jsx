import { useEffect, useState } from "react";

import { studentOption } from "@shared/catalogs/academicCatalogs.js";
import { useSearchableCatalog } from "@shared/catalogs/useSearchableCatalog.js";
import { studentsService } from "@students/studentsService.js";
import { SearchableSelect } from "@ui/forms/SearchableSelect.jsx";

const searchStudents = (params) =>
  studentsService.listPage({ ...params, include_inactive: true });
const keepRemoteOptions = (options) => options;

/** Explicit remote lookup, including students needed for historical enrolments. */
export function EnrolmentStudentFilter({ selected, onChange }) {
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(search), 300);
    return () => clearTimeout(timer);
  }, [search]);
  const students = useSearchableCatalog(
    "enrolment-students-with-history",
    searchStudents,
    studentOption,
    debounced
  );
  const options = selected
    ? [
        selected,
        ...students.options.filter((option) => option.value !== selected.value),
      ]
    : students.options;

  return (
    <SearchableSelect
      clearText="Quitar estudiante"
      error={students.error}
      filterOptions={keepRemoteOptions}
      helperText={
        students.error ||
        "Escriba al menos 2 caracteres. Si no aparece, afine la búsqueda."
      }
      label="Estudiante"
      loading={students.loading}
      loadingText="Buscando estudiantes…"
      noOptionsText={
        students.ready
          ? "Sin coincidencias. Afine la búsqueda."
          : "Escriba al menos 2 caracteres"
      }
      onChange={(event) => {
        const value = event.target.value;
        if (!value) setSearch("");
        onChange(options.find((option) => option.value === value) ?? null);
      }}
      onInputChange={(_event, value, reason) => {
        if (reason === "input") setSearch(value);
      }}
      options={options}
      placeholder="Buscar por nombre o código…"
      sx={{ minWidth: { xs: 0, md: 360 } }}
      value={selected?.value ?? ""}
    />
  );
}
