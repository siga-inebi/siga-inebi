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

export function EnrolmentCreateWindow({ creating, onCancel, onCreated }) {
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

    if (creating === "reenrol") {
      await enrolmentsService.reenrol(payload);
    } else {
      await enrolmentsService.matriculate(payload);
    }
    onCreated();
  };

  return (
    <EntityFormWindow
      description={
        creating === "reenrol"
          ? "Reinscripcion de un estudiante con matricula previa. El backend valida que exista historial y que el ciclo destino este abierto."
          : "Matriculacion nueva. El backend valida cupo de la seccion, jornada y requisitos del ciclo."
      }
      fields={enrolmentFields}
      initialValues={EMPTY_ENROLMENT}
      key={creating}
      onCancel={onCancel}
      onSubmit={handleSubmit}
      open
      submitLabel={creating === "reenrol" ? "Reinscribir" : "Matricular"}
      title={
        creating === "reenrol" ? "Reinscribir estudiante" : "Nueva matricula"
      }
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
