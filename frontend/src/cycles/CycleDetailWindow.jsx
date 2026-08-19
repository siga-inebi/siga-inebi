import { useEffect, useMemo, useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import {
  CYCLE_STATUS_LABEL,
  CYCLE_STATUS_VARIANT,
  cyclesService,
} from "@cycles/cyclesService.js";
import {
  labelIndex,
  useSectionCatalog,
  useSubjectCatalog,
  useTeacherCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { formatDate } from "@shared/utils/format.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { EmptyState } from "@ui/feedback/EmptyState.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { DetailField } from "@ui/layout/DetailWindow.jsx";

/** Bloque con titulo y conteo, para cada coleccion del detalle historico. */
function CollectionBlock({ children, count, title }) {
  return (
    <Box>
      <Stack alignItems="baseline" direction="row" gap={1} sx={{ mb: 1 }}>
        <Typography
          sx={(theme) => ({
            fontFamily: theme.tokens.fonts.display,
            fontSize: "0.9375rem",
            fontWeight: 600,
          })}
        >
          {title}
        </Typography>
        <Typography color="text.secondary" sx={{ fontSize: "0.75rem" }}>
          {count} {count === 1 ? "registro" : "registros"}
        </Typography>
      </Stack>
      {children}
    </Box>
  );
}

/**
 * Lista compacta de texto: el detalle historico es de consulta, no de edicion.
 *
 * Con tope de alto y desplazamiento propio: un ciclo completo trae decenas de
 * asignaciones, y sin tope el bloque empuja a los demas fuera de la ventana y
 * obliga a recorrerla entera para llegar al siguiente.
 */
function CompactList({ emptyMessage, items, render }) {
  if (items.length === 0) {
    return <EmptyState message={emptyMessage} />;
  }

  return (
    <Stack
      sx={{
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 1,
        overflow: "hidden",
        maxHeight: "18rem",
        overflowY: "auto",
      }}
    >
      {items.map((item, index) => (
        <Typography
          key={item.public_id ?? index}
          sx={{
            fontSize: "0.8125rem",
            px: 1.5,
            py: 1,
            borderTop: index === 0 ? "none" : "1px solid",
            borderColor: "divider",
          }}
        >
          {render(item)}
        </Typography>
      ))}
    </Stack>
  );
}

/** Nombre legible de una referencia que el backend puede devolver anidada o plana. */
function refLabel(value) {
  if (value == null) return "—";
  if (typeof value === "string" || typeof value === "number")
    return String(value);
  return value.name ?? value.code ?? value.public_id ?? "—";
}

/**
 * Detalle historico de un ciclo escolar.
 *
 * Es SOLO LECTURA a proposito: un ciclo cerrado no acepta escrituras, y esta
 * ventana existe justamente para consultar como quedo la estructura en su
 * momento. Ofrecer aqui acciones de edicion invitaria a intentar algo que el
 * backend va a rechazar.
 */
export function CycleDetailWindow({ cycle, onClose }) {
  const sections = useSectionCatalog();
  const subjects = useSubjectCatalog();
  const teachers = useTeacherCatalog();

  const names = useMemo(
    () => ({
      sections: labelIndex(sections.options),
      subjects: labelIndex(subjects.options),
      teachers: labelIndex(teachers.options),
    }),
    [sections.options, subjects.options, teachers.options]
  );

  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    cyclesService
      .get(cycle.public_id)
      .then((data) => {
        if (active) setDetail(data);
      })
      .catch((requestError) => {
        if (active) setError(requestError.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [cycle.public_id]);

  const offerings = detail?.grade_offerings ?? [];
  const plans = detail?.curriculum_plans ?? [];
  const assignments = detail?.teaching_assignments ?? [];

  return (
    <FloatingWindow
      busy={loading}
      description="Estructura registrada para este ciclo. Solo consulta."
      onClose={onClose}
      open
      title={cycle.name}
      width={WINDOW_WIDTH.wide}
    >
      {error ? <Alert severity="error">{error}</Alert> : null}

      <Box
        component="dl"
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" },
          gap: 2.5,
          m: 0,
          mb: 3,
        }}
      >
        <DetailField label="Ano" value={cycle.year} />
        <DetailField
          label="Vigencia"
          value={`${formatDate(cycle.starts_on)} — ${formatDate(cycle.ends_on)}`}
        />
        <DetailField
          label="Estado"
          value={
            <StatusChip
              label={CYCLE_STATUS_LABEL[cycle.status] ?? cycle.status}
              variant={CYCLE_STATUS_VARIANT[cycle.status] ?? "neutral"}
            />
          }
        />
      </Box>

      {loading ? (
        <Stack gap={1.5}>
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton aria-hidden height={26} key={index} variant="text" />
          ))}
        </Stack>
      ) : (
        <Stack gap={3}>
          <CollectionBlock count={offerings.length} title="Oferta de grados">
            <CompactList
              emptyMessage="Este ciclo no registro oferta de grados."
              items={offerings}
              render={(offering) =>
                [
                  refLabel(offering.grade),
                  refLabel(offering.shift),
                  refLabel(offering.campus),
                  `${offering.sections?.length ?? 0} secciones`,
                ].join(" · ")
              }
            />
          </CollectionBlock>

          <CollectionBlock count={plans.length} title="Plan de estudios">
            <CompactList
              emptyMessage="Este ciclo no registro plan de estudios."
              items={plans}
              render={(plan) =>
                `${refLabel(plan.grade)} · ${refLabel(plan.subject)} · ${
                  plan.is_required ? "obligatorio" : "opcional"
                }`
              }
            />
          </CollectionBlock>

          <CollectionBlock
            count={assignments.length}
            title="Asignaciones docentes"
          >
            <CompactList
              emptyMessage="Este ciclo no registro asignaciones docentes."
              items={assignments}
              render={(assignment) =>
                [
                  names.sections.get(assignment.section_id) ??
                    "Seccion sin nombre",
                  names.subjects.get(assignment.subject_id) ??
                    "Curso sin nombre",
                  names.teachers.get(assignment.teacher_id) ??
                    "Docente sin nombre",
                  `desde ${formatDate(assignment.starts_on)}`,
                ].join(" · ")
              }
            />
          </CollectionBlock>
        </Stack>
      )}
    </FloatingWindow>
  );
}
