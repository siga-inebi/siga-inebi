import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";

import { EmptyState } from "@ui/feedback/EmptyState.jsx";
import { RemoteSearchSelect } from "@ui/forms/RemoteSearchSelect.jsx";
import { SectionCard } from "@ui/layout/SectionCard.jsx";

import { STUDENT_SEARCH } from "../studentSearch.js";
import { StudentCardPanel } from "../StudentCardPanel.jsx";

/**
 * Carnés (AS2): se busca al estudiante en el servidor y se trabaja su carné.
 * El estudiante elegido va en la URL (`?estudiante=`); el QR emitido, no.
 */
export function CardsTab() {
  const [params, setParams] = useSearchParams();
  const studentId = params.get("estudiante") ?? "";
  const [option, setOption] = useState(null);

  return (
    <SectionCard
      subtitle="Emisión, impresión y revocación del carné con QR"
      title="Carné del estudiante"
    >
      <Stack gap={2.5} sx={{ px: { xs: 2, md: 3 }, py: 2.5 }}>
        <Box sx={{ maxWidth: 480 }}>
          <RemoteSearchSelect
            helperText="Escriba el nombre o el código del estudiante."
            label="Estudiante"
            name="student_id"
            onChange={(event) =>
              setParams((current) => {
                const next = new URLSearchParams(current);
                if (event.target.value)
                  next.set("estudiante", event.target.value);
                else next.delete("estudiante");
                return next;
              })
            }
            onOptionChange={setOption}
            search={STUDENT_SEARCH}
            value={studentId}
          />
        </Box>
        {studentId ? (
          <StudentCardPanel
            key={studentId}
            studentId={studentId}
            studentName={option?.label}
          />
        ) : (
          <EmptyState message="Elija un estudiante para consultar o emitir su carné." />
        )}
      </Stack>
    </SectionCard>
  );
}
