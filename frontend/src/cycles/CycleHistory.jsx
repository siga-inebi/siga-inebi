import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { formatDate } from "@shared/utils/format.js";
import { EmptyState } from "@ui/feedback/EmptyState.jsx";
import { DetailField } from "@ui/layout/DetailWindow.jsx";

/** Bloque con título y conteo, para cada colección del detalle histórico. */
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

/** Lista compacta con tope de alto: un ciclo completo trae decenas de filas. */
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

function refLabel(value) {
  if (value == null) return "—";
  if (typeof value === "string" || typeof value === "number")
    return String(value);
  return value.name ?? value.code ?? "—";
}

/**
 * Estructura registrada del ciclo (detalle histórico, solo consulta).
 *
 * Antes era una ventana aparte; ahora es parte de la pestaña "Resumen" del
 * detalle del ciclo (docs/ux-ui.md C9, 1.5). Los nombres de sección, curso y
 * docente vienen en la respuesta: no se descarga ningún catálogo para
 * traducir identificadores.
 */
export function CycleHistory({ detail }) {
  const offerings = detail?.grade_offerings ?? [];
  const plans = detail?.curriculum_plans ?? [];
  const assignments = detail?.teaching_assignments ?? [];
  const enrolments = detail?.enrolments;

  return (
    <Stack gap={3}>
      {enrolments ? (
        <Box
          component="dl"
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr 1fr", sm: "repeat(4, 1fr)" },
            gap: 2,
            m: 0,
          }}
        >
          <DetailField label="Matrículas" value={enrolments.total} />
          <DetailField label="Activas" value={enrolments.active} />
          <DetailField label="Retiradas" value={enrolments.withdrawn} />
          <DetailField label="Finalizadas" value={enrolments.completed} />
        </Box>
      ) : null}

      <CollectionBlock count={offerings.length} title="Oferta de grados">
        <CompactList
          emptyMessage="Este ciclo no registró oferta de grados."
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
          emptyMessage="Este ciclo no registró plan de estudios."
          items={plans}
          render={(plan) =>
            `${refLabel(plan.grade)} · ${refLabel(plan.subject)} · ${
              plan.is_required ? "obligatorio" : "opcional"
            }`
          }
        />
      </CollectionBlock>

      <CollectionBlock count={assignments.length} title="Asignaciones docentes">
        <CompactList
          emptyMessage="Este ciclo no registró asignaciones docentes."
          items={assignments}
          render={(assignment) =>
            [
              [assignment.section?.grade_name, assignment.section?.name]
                .filter(Boolean)
                .join(" ") || "Sección sin nombre",
              assignment.subject?.name ?? "Curso sin nombre",
              assignment.teacher?.name ?? "Docente sin nombre",
              `desde ${formatDate(assignment.starts_on)}`,
            ].join(" · ")
          }
        />
      </CollectionBlock>
    </Stack>
  );
}
