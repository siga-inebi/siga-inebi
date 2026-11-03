import { useCallback, useState } from "react";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { DetailWindow } from "@ui/layout/DetailWindow.jsx";
import { studentsService } from "./studentsService.js";
import { StudentRecordList } from "./StudentRecordList.jsx";

const RECORDS = {
  health: {
    title: "Salud",
    label: "Notas de salud",
    empty: "Sin notas de salud",
    list: "listHealthNotes",
    create: "createHealthNote",
    newLabel: "Nueva nota",
    formTitle: "Nueva nota de salud",
    submit: "Registrar nota",
    fields: [
      { name: "content", label: "Información de salud", required: true },
    ],
    initialValues: { content: "" },
    render: (note) => (
      <>
        <Typography fontWeight={600} variant="body2">
          {note.recorded_on} · {note.author}
        </Typography>
        <Typography variant="body2">{note.content}</Typography>
      </>
    ),
  },
  observations: {
    title: "Observaciones",
    label: "Observaciones sensibles",
    empty: "Sin observaciones",
    list: "listObservations",
    create: "createObservation",
    newLabel: "Nueva observación",
    formTitle: "Nueva observación",
    submit: "Registrar observación",
    fields: [{ name: "description", label: "Descripción", required: true }],
    initialValues: { description: "" },
    render: (record) => (
      <>
        <Typography fontWeight={600} variant="body2">
          {record.observed_on} · {record.author}
        </Typography>
        <Typography variant="body2">{record.description}</Typography>
      </>
    ),
  },
  contacts: {
    title: "Contactos",
    label: "Contactos de emergencia",
    empty: "Sin contactos de emergencia",
    list: "listEmergencyContacts",
    create: "createEmergencyContact",
    newLabel: "Nuevo contacto",
    formTitle: "Nuevo contacto de emergencia",
    submit: "Registrar contacto",
    fields: [
      { name: "name", label: "Nombre", required: true },
      { name: "phone_number", label: "Teléfono", required: true },
      { name: "relationship_label", label: "Relación", required: true },
    ],
    initialValues: { name: "", phone_number: "", relationship_label: "" },
    render: (contact) => (
      <>
        <Typography fontWeight={600} variant="body2">
          {contact.name} · {contact.relationship_label}
        </Typography>
        <Typography variant="body2">{contact.phone_number}</Typography>
      </>
    ),
  },
};

export function StudentRecordWindow({ kind, onClose, student }) {
  const config = RECORDS[kind];
  const [creating, setCreating] = useState(false);
  const load = useCallback(
    ({ page }) => studentsService[config.list](student.public_id, { page }),
    [config, student.public_id]
  );
  const list = usePaginatedList(load, { canIncludeInactive: false });

  const handleCreate = async (values) => {
    await studentsService[config.create](student.public_id, values);
    list.goToPage(1);
    list.refresh();
    setCreating(false);
  };

  return (
    <>
      <DetailWindow
        actions={
          <Button onClick={() => setCreating(true)} variant="contained">
            {config.newLabel}
          </Button>
        }
        fields={[]}
        onClose={onClose}
        open
        title={`${config.title} de ${student.person.first_name} ${student.person.last_name}`}
      >
        <Typography component="h2" variant="subtitle2" sx={{ mb: 1 }}>
          {config.label}
        </Typography>
        <StudentRecordList
          emptyMessage={config.empty}
          list={list}
          renderItem={config.render}
        />
      </DetailWindow>
      {creating ? (
        <EntityFormWindow
          fields={config.fields}
          initialValues={config.initialValues}
          onCancel={() => setCreating(false)}
          onSubmit={handleCreate}
          open
          submitLabel={config.submit}
          title={config.formTitle}
        />
      ) : null}
    </>
  );
}
