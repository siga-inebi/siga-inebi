import { useCallback, useState } from "react";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { guardiansService } from "@guardians/guardiansService.js";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { RecordCollection } from "./RecordCollection.jsx";
import { RecordForm } from "./RecordForm.jsx";
import { studentsService } from "./studentsService.js";
import {
  STUDENT_FIELDS,
  fullName,
  personPayload,
} from "./studentPresentation.js";

const RELATIONSHIP = {
  name: "relationship_label",
  label: "Parentesco o responsabilidad",
  required: true,
};
const NEW_GUARDIAN_FIELDS = [
  ...STUDENT_FIELDS.filter(
    (field) => !["student_code", "photo"].includes(field.name)
  ),
  RELATIONSHIP,
];

export function GuardianLinkForm({ student, onCancel, onSaved, onBusy }) {
  const [search, setSearch] = useState("");
  const [draft, setDraft] = useState("");
  const [chosen, setChosen] = useState(null);
  const [creating, setCreating] = useState(false);
  const load = useCallback(
    ({ page }) => guardiansService.listPage({ page, search }),
    [search]
  );
  const list = usePaginatedList(load, { canIncludeInactive: false });
  if (creating || chosen)
    return (
      <Stack gap={2}>
        <Typography component="h2" variant="h6">
          {creating
            ? "Crear y vincular encargado"
            : `Encargado: ${fullName(chosen)}`}
        </Typography>
        {creating ? (
          <Typography color="text.secondary">
            Busque primero por nombre o CUI para evitar duplicados. El encargado
            y el vínculo se guardarán juntos.
          </Typography>
        ) : null}
        <RecordForm
          key={creating ? "new" : chosen.id}
          title={creating ? "Crear y vincular encargado" : "Vincular encargado"}
          fields={creating ? NEW_GUARDIAN_FIELDS : [RELATIONSHIP]}
          onBusy={onBusy}
          onCancel={() => {
            setChosen(null);
            setCreating(false);
          }}
          submitLabel={creating ? "Crear y vincular" : "Vincular encargado"}
          onSubmit={async (values) => {
            await studentsService.linkRecordGuardian(student.public_id, {
              ...(creating
                ? { person: personPayload(values) }
                : { guardian_id: chosen.id }),
              relationship_label: values.relationship_label,
            });
            onSaved();
          }}
        />
      </Stack>
    );
  return (
    <Stack gap={2}>
      <Typography component="h2" variant="h6">
        Vincular encargado
      </Typography>
      <Stack
        component="form"
        direction={{ xs: "column", sm: "row" }}
        gap={1}
        onSubmit={(event) => {
          event.preventDefault();
          list.goToPage(1);
          setSearch(draft.trim());
        }}
      >
        <FormTextField
          placeholder="Buscar por nombre o CUI"
          value={draft}
          label="Buscar por nombre o CUI"
          onChange={(event) => setDraft(event.target.value)}
        />
        <Button type="submit">Buscar encargado</Button>
      </Stack>
      <RecordCollection
        list={list}
        emptyMessage="No se encontraron encargados. Puede crear uno aquí."
        renderRow={(row) => (
          <Button onClick={() => setChosen(row)}>Elegir {fullName(row)}</Button>
        )}
      />
      <Stack direction="row" gap={1}>
        <Button variant="outlined" onClick={() => setCreating(true)}>
          Crear encargado
        </Button>
        <Button onClick={onCancel}>Cancelar</Button>
      </Stack>
    </Stack>
  );
}
