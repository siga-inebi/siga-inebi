import { useCallback, useEffect, useRef, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { studentsService } from "./studentsService.js";
import { RecordCollection } from "./RecordCollection.jsx";
import { RecordForm } from "./RecordForm.jsx";
import { fullName } from "./studentPresentation.js";

function ReplacementPicker({ student, relation, onChoose, onCancel }) {
  const load = useCallback(
    (params) =>
      studentsService.listRecordGuardians(student.public_id, {
        page: params.page,
        replacement_for: relation.id,
      }),
    [student.public_id, relation.id]
  );
  const list = usePaginatedList(load, { canIncludeInactive: false });
  return (
    <Stack gap={2}>
      <Alert severity="info">
        Elija otro vínculo vigente como principal antes de finalizar este. Si no
        hay reemplazos, vincule primero a otro encargado.
      </Alert>
      <RecordCollection
        list={list}
        emptyMessage="No hay vínculos disponibles como reemplazo."
        renderRow={(row) => (
          <Button onClick={() => onChoose(row)}>
            Elegir {fullName(row.guardian_detail)} · {row.relationship_label}
          </Button>
        )}
      />
      <Button onClick={onCancel}>Cancelar</Button>
    </Stack>
  );
}

/** One inline action at a time; the server selects eligible replacements. */
export function GuardianRelationAction({
  student,
  selection,
  onCancel,
  onSaved,
  onBusy,
}) {
  const { relation, kind } = selection;
  const [replacement, setReplacement] = useState(null);
  const heading = useRef(null);
  useEffect(() => {
    heading.current?.focus();
  }, []);
  const name = fullName(relation.guardian_detail);
  const requiresReplacement =
    kind === "end" && relation.actions.requires_replacement;
  const title =
    kind === "edit"
      ? "Editar vínculo"
      : kind === "primary"
        ? "Marcar como principal"
        : "Finalizar vínculo";
  return (
    <Stack gap={2}>
      <Typography component="h2" variant="h6" ref={heading} tabIndex={-1}>
        {title}: {name}
      </Typography>
      {kind !== "edit" ? (
        <Alert severity={kind === "end" ? "warning" : "info"}>
          {kind === "primary"
            ? "Este vínculo será el principal. El anterior conservará su relación con el estudiante."
            : "La finalización se registrará con la fecha de hoy y terminará el acceso asociado a este vínculo. El historial se conservará."}
        </Alert>
      ) : (
        <Typography color="text.secondary">
          Corrija el parentesco o responsabilidad. Las personas y fechas del
          vínculo se conservan.
        </Typography>
      )}
      {requiresReplacement && !replacement ? (
        <ReplacementPicker
          student={student}
          relation={relation}
          onChoose={setReplacement}
          onCancel={onCancel}
        />
      ) : (
        <>
          {replacement ? (
            <Typography>
              Nuevo principal: {fullName(replacement.guardian_detail)}
            </Typography>
          ) : null}
          <RecordForm
            title={title}
            fields={
              kind === "edit"
                ? [
                    {
                      name: "relationship_label",
                      label: "Parentesco o responsabilidad",
                      required: true,
                    },
                  ]
                : []
            }
            initialValues={{ relationship_label: relation.relationship_label }}
            onCancel={onCancel}
            onBusy={onBusy}
            submitLabel={
              kind === "edit"
                ? "Guardar vínculo"
                : kind === "primary"
                  ? "Confirmar principal"
                  : "Confirmar finalización"
            }
            onSubmit={async (values) => {
              if (kind === "edit")
                await studentsService.updateGuardianRelation(relation.id, {
                  relationship_label: values.relationship_label,
                });
              else if (kind === "primary")
                await studentsService.makeGuardianRelationPrimary(relation.id);
              else
                await studentsService.endGuardianRelation(
                  relation.id,
                  replacement ? { replacement_relation: replacement.id } : {}
                );
              onSaved(kind);
            }}
          />
        </>
      )}
    </Stack>
  );
}
