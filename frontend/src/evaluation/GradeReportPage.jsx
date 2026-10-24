import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import PictureAsPdfOutlinedIcon from "@mui/icons-material/PictureAsPdfOutlined";

import { academicsService } from "@academics/academicsService.js";
import { CYCLE_STATUS_LABEL, cyclesService } from "@cycles/cyclesService.js";
import { evaluationService } from "@evaluation/evaluationService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import {
  studentOption,
  useGradeCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { downloadBlob } from "@shared/utils/download.js";
import { studentsService } from "@students/studentsService.js";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";
import { RemoteSearchSelect } from "@ui/forms/RemoteSearchSelect.jsx";
import { SearchableSelect } from "@ui/forms/SearchableSelect.jsx";
import { EmptyState } from "@ui/feedback/EmptyState.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard } from "@ui/layout/SectionCard.jsx";

const SCOPE = Object.freeze({
  ALL: "all",
  GRADE: "grade",
  STUDENT: "student",
});

const STUDENT_SEARCH = {
  name: "students",
  fetchPage: studentsService.listPage,
  mapResult: studentOption,
};

const OPTIONS_PAGE_SIZE = 100;

/**
 * Informe de calificaciones en PDF (dirección y secretaría, `grade.report`).
 *
 * Se elige el alcance —todos los estudiantes, un grado (y opcionalmente una
 * sección) o un estudiante— y se genera un PDF con una página por estudiante:
 * cursos en filas, unidades en columnas, promedio de cada curso al final de su
 * fila, promedio de cada unidad abajo y el promedio general en la esquina.
 *
 * El backend entrega los datos con los promedios ya calculados en pocas
 * consultas; el PDF se arma en el navegador para no cargar al servidor.
 */
export function GradeReportPage() {
  const [cycleId, setCycleId] = useState("");
  const [scope, setScope] = useState(SCOPE.ALL);
  const [gradeId, setGradeId] = useState("");
  const [sectionId, setSectionId] = useState("");
  const [student, setStudent] = useState(null);
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const cycles = useQuery({
    queryKey: queryKeys.evaluation("", "cycles"),
    queryFn: () => cyclesService.list({ page_size: OPTIONS_PAGE_SIZE }),
    select: (page) => page?.results ?? [],
  });
  const cycleList = cycles.data ?? [];
  const cycle =
    cycleList.find((item) => item.public_id === cycleId) ??
    cycleList.find((item) => item.status === "active") ??
    cycleList[0] ??
    null;

  const grades = useGradeCatalog();
  const sections = useQuery({
    queryKey: queryKeys.academics.list("sections", cycle?.public_id, gradeId),
    queryFn: () =>
      academicsService.listSections({
        academic_cycle_id: cycle.public_id,
        grade_id: gradeId,
        page_size: OPTIONS_PAGE_SIZE,
      }),
    enabled: Boolean(cycle && gradeId),
    select: (page) =>
      (page?.results ?? []).map((section) => ({
        value: section.public_id,
        label: section.shift?.name
          ? `Sección ${section.name} · ${section.shift.name}`
          : `Sección ${section.name}`,
      })),
  });

  const generating = progress !== null;
  const missingFilter =
    (scope === SCOPE.GRADE && !gradeId) ||
    (scope === SCOPE.STUDENT && !student);

  const scopeParams = () => {
    if (scope === SCOPE.GRADE) {
      return { grade_id: gradeId, section_id: sectionId || undefined };
    }
    if (scope === SCOPE.STUDENT) return { student_id: student.value };
    return {};
  };

  const scopeLabel = () => {
    if (scope === SCOPE.GRADE) {
      const grade = grades.options.find((option) => option.value === gradeId);
      const section = (sections.data ?? []).find(
        (option) => option.value === sectionId
      );
      return [grade?.label, section?.label].filter(Boolean).join(" ");
    }
    if (scope === SCOPE.STUDENT) return student?.label ?? "estudiante";
    return "todos";
  };

  const generate = async () => {
    setError("");
    setNotice("");
    setProgress({ done: 0, total: 0, stage: "Consultando notas…" });
    try {
      const report = await evaluationService.getGradeReport(
        cycle.public_id,
        scopeParams()
      );
      if (report.students.length === 0) {
        setNotice(
          "No hay estudiantes con matrícula activa para esa selección."
        );
        return;
      }
      const total = report.students.length;
      setProgress({ done: 0, total, stage: "Armando el PDF…" });
      const { buildGradeReportPdf, gradeReportFilename } =
        await import("./gradeReportPdf.js");
      const blob = await buildGradeReportPdf(report, {
        onProgress: (done) =>
          setProgress({ done, total, stage: "Armando el PDF…" }),
      });
      downloadBlob(gradeReportFilename(report, scopeLabel()), blob);
      setNotice(
        `Se generó el informe de ${total} ${total === 1 ? "estudiante" : "estudiantes"}.`
      );
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setProgress(null);
    }
  };

  const changeScope = (value) => {
    setScope(value);
    setNotice("");
    setError("");
  };

  return (
    <>
      <PageHeader
        breadcrumb="Gestión académica"
        subtitle="Genere en PDF el informe de calificaciones de todos los estudiantes, de un grado o sección, o de un estudiante. Una página por estudiante, con el membrete de la institución."
        title="Informe de notas"
      />
      {cycles.error ? (
        <Alert severity="error">{cycles.error.message}</Alert>
      ) : null}
      <SectionCard sx={{ p: { xs: 2, sm: 3 } }}>
        {!cycle ? (
          cycles.isPending ? (
            <Typography role="status">Cargando ciclos…</Typography>
          ) : (
            <EmptyState message="No hay ciclos escolares registrados." />
          )
        ) : (
          <Stack gap={3} sx={{ maxWidth: 640 }}>
            <FilterSelect
              label="Ciclo escolar"
              loading={cycles.isPending}
              minWidth={260}
              onChange={(value) => {
                setCycleId(value);
                setSectionId("");
              }}
              options={cycleList.map((item) => ({
                value: item.public_id,
                label: `${item.name} · ${CYCLE_STATUS_LABEL[item.status] ?? item.status}`,
              }))}
              value={cycle.public_id}
            />

            <Box>
              <Typography
                component="h2"
                sx={{ fontWeight: 600, mb: 0.5 }}
                variant="subtitle2"
              >
                ¿De quién imprime las notas?
              </Typography>
              <ToggleButtonGroup
                aria-label="Alcance del informe"
                color="primary"
                disabled={generating}
                exclusive
                onChange={(_event, value) => {
                  if (value) changeScope(value);
                }}
                size="small"
                sx={{ flexWrap: "wrap" }}
                value={scope}
              >
                <ToggleButton value={SCOPE.ALL}>
                  Todos los estudiantes
                </ToggleButton>
                <ToggleButton value={SCOPE.GRADE}>
                  Un grado o sección
                </ToggleButton>
                <ToggleButton value={SCOPE.STUDENT}>Un estudiante</ToggleButton>
              </ToggleButtonGroup>
            </Box>

            {scope === SCOPE.GRADE ? (
              <Stack direction={{ xs: "column", sm: "row" }} gap={2}>
                <Box sx={{ flex: 1 }}>
                  <SearchableSelect
                    disabled={generating}
                    helperText={grades.error || "Escriba para buscar el grado."}
                    label="Grado"
                    name="grade"
                    onChange={(event) => {
                      setGradeId(event.target.value);
                      setSectionId("");
                    }}
                    options={grades.options}
                    placeholder={grades.loading ? "Cargando grados…" : ""}
                    required
                    value={gradeId}
                  />
                </Box>
                <Box sx={{ flex: 1 }}>
                  <SearchableSelect
                    disabled={generating || !gradeId}
                    helperText="Opcional: déjelo vacío para todo el grado."
                    label="Sección"
                    name="section"
                    onChange={(event) => setSectionId(event.target.value)}
                    options={sections.data ?? []}
                    value={sectionId}
                  />
                </Box>
              </Stack>
            ) : null}

            {scope === SCOPE.STUDENT ? (
              <RemoteSearchSelect
                disabled={generating}
                label="Estudiante"
                name="student"
                onChange={(event) => {
                  if (!event.target.value) setStudent(null);
                }}
                onOptionChange={setStudent}
                placeholder="Escriba el nombre o el código del estudiante"
                required
                search={STUDENT_SEARCH}
                value={student?.value ?? ""}
              />
            ) : null}

            {generating ? (
              <Stack gap={0.75} role="status">
                <Typography variant="body2">
                  {progress.stage}
                  {progress.total
                    ? ` ${progress.done} de ${progress.total} estudiantes.`
                    : ""}
                </Typography>
                <LinearProgress
                  value={
                    progress.total
                      ? Math.round((progress.done / progress.total) * 100)
                      : 0
                  }
                  variant={progress.total ? "determinate" : "indeterminate"}
                />
              </Stack>
            ) : null}
            {notice ? (
              <Alert role="status" severity="success">
                {notice}
              </Alert>
            ) : null}
            {error ? (
              <Alert role="alert" severity="error">
                {error}
              </Alert>
            ) : null}

            <Box>
              <Button
                disabled={generating || missingFilter}
                onClick={generate}
                size="large"
                startIcon={<PictureAsPdfOutlinedIcon />}
                variant="contained"
              >
                {generating ? "Generando…" : "Generar PDF"}
              </Button>
            </Box>
          </Stack>
        )}
      </SectionCard>
    </>
  );
}
