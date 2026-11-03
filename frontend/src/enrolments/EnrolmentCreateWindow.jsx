import { useCallback } from "react";

import { enrolmentsService } from "@enrolments/enrolmentsService.js";
import {
  sectionsForCycle,
  useCycleCatalog,
  useSectionCatalog,
  useStudentCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { SectionOccupancyNotice } from "./SectionOccupancyNotice.jsx";

const EMPTY_ENROLMENT = {
  student_id: "",
  academic_cycle_id: "",
  section_id: "",
  effective_on: "",
};

export function EnrolmentCreateWindow({ onCancel, onCreated }) {
  const students = useStudentCatalog();
  const cycles = useCycleCatalog();
  const sections = useSectionCatalog();
  const enrolmentFields = useCallback(
    (values) => [
      {
        name: "student_id",
        label: "Estudiante",
        type: "select",
        options: students.options,
        loading: students.loading,
        optionsError: students.error,
        emptyHint: "No hay estudiantes registrados.",
        required: true,
        span: "full",
      },
      {
        name: "academic_cycle_id",
        label: "Ciclo escolar",
        type: "select",
        options: cycles.options,
        loading: cycles.loading,
        optionsError: cycles.error,
        emptyHint: "No hay ciclos escolares registrados.",
        required: true,
        resets: ["section_id"],
      },
      {
        name: "section_id",
        label: "Seccion",
        type: "select",
        options: sectionsForCycle(sections.options, values.academic_cycle_id),
        loading: sections.loading,
        optionsError: sections.error,
        emptyHint: values.academic_cycle_id
          ? "Ese ciclo no tiene secciones registradas."
          : "Elija primero el ciclo escolar.",
        help: "El grado y la jornada se toman de la seccion.",
        required: true,
      },
      {
        name: "effective_on",
        label: "Vigente desde",
        type: "date",
        required: true,
        span: "full",
      },
    ],
    [students, cycles, sections]
  );

  const handleSubmit = async (values) => {
    const section = sections.options.find(
      (option) => option.value === values.section_id
    );

    const payload = {
      ...values,
      grade_id: section?.gradeId,
      shift_id: section?.shiftId,
    };

    await enrolmentsService.register(payload);
    onCreated();
  };

  return (
    <EntityFormWindow
      description="El servidor detecta si corresponde una primera matrícula o una reinscripción con historial de otro ciclo. Si reinscribe, cierra la matrícula anterior que siga activa."
      fields={enrolmentFields}
      initialValues={EMPTY_ENROLMENT}
      onCancel={onCancel}
      onSubmit={handleSubmit}
      open
      submitLabel="Confirmar matrícula"
      title="Matricular estudiante"
    >
      {(values, { submitting }) => (
        <SectionOccupancyNotice
          busy={submitting}
          cycleId={values.academic_cycle_id}
          sectionId={values.section_id}
        />
      )}
    </EntityFormWindow>
  );
}
