import { useCallback, useState } from "react";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";

import { peopleService } from "@people/peopleService.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { ActionIconButton } from "@ui/buttons/ActionIconButton.jsx";
import { ConfirmActionButton } from "@ui/buttons/ConfirmActionButton.jsx";
import { ActiveCell, MutedCell } from "@ui/table/cells.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";

// Person has no immutable field (unlike Subject/Level/Campus, which keep
// their code fixed after creation), so create and edit share the same set.
const PERSON_FIELDS = [
  {
    name: "first_name",
    label: "Nombre",
    required: true,
    placeholder: "Ejemplo: Ana",
  },
  {
    name: "last_name",
    label: "Apellido",
    required: true,
    placeholder: "Ejemplo: Gomez",
  },
  {
    name: "email",
    label: "Correo electronico (opcional)",
    placeholder: "correo@ejemplo.com",
  },
  {
    name: "phone_number",
    label: "Telefono (opcional)",
    placeholder: "Ejemplo: 50212345678",
  },
  {
    name: "institutional_identifier",
    label: "Identificador institucional (opcional)",
    help: "Codigo interno opcional.",
  },
];

const EMPTY_VALUES = {
  first_name: "",
  last_name: "",
  email: "",
  phone_number: "",
  institutional_identifier: "",
};

const PERSON_COLUMNS = [
  {
    key: "name",
    label: "Nombre completo",
    render: (row) => `${row.first_name} ${row.last_name}`.trim(),
  },
  {
    key: "email",
    label: "Correo",
    render: (row) => row.email || <MutedCell>Sin registrar</MutedCell>,
  },
  {
    key: "phone_number",
    label: "Telefono",
    render: (row) => row.phone_number || <MutedCell>Sin registrar</MutedCell>,
  },
  {
    key: "institutional_identifier",
    label: "Identificador",
    render: (row) =>
      row.institutional_identifier || <MutedCell>Sin registrar</MutedCell>,
  },
  {
    key: "is_active",
    label: "Estado",
    render: (row) => (
      <ActiveCell active={row.is_active} inactiveLabel="Desactivada" />
    ),
  },
];

/**
 * Registro base de personas institucionales (people-registry).
 *
 * Sostiene otros expedientes (cuentas, estudiantes, encargados) que ya
 * referencian una `Person` por `public_id`, pero no reemplaza ninguno de
 * ellos: no hay ningun RF que pida esta pantalla especificamente, es
 * infraestructura de apoyo para poder administrar el registro que esos
 * flujos ya dan por existente.
 */
export function PersonasPage() {
  const loadPeople = useCallback(
    (params) => peopleService.listPeople(params),
    []
  );
  const list = usePaginatedList(loadPeople);

  const [editing, setEditing] = useState(null);
  const [actionError, setActionError] = useState("");

  const handleCreate = async (payload) => {
    await peopleService.createPerson(payload);
    setEditing(null);
    list.refresh();
  };

  const handleUpdate = async (payload) => {
    await peopleService.updatePerson(editing.person.public_id, payload);
    setEditing(null);
    list.refresh();
  };

  const handleDeactivate = async (person) => {
    setActionError("");
    try {
      await peopleService.deactivatePerson(person.public_id);
      list.refresh();
    } catch (requestError) {
      setActionError(requestError.message);
      throw requestError;
    }
  };

  return (
    <>
      <PageHeader
        breadcrumb="Identidad institucional"
        subtitle="Registro base de personas institucionales. Da soporte a cuentas, estudiantes y encargados; no reemplaza esos expedientes."
        title="Personas"
      />

      <ListSection
        action={
          <Button
            onClick={() => setEditing({ mode: "create" })}
            size="small"
            startIcon={<AddIcon fontSize="small" />}
            variant="contained"
          >
            Nueva persona
          </Button>
        }
        actionError={actionError}
        list={list}
        columns={PERSON_COLUMNS}
        emptyMessage="Todavia no hay personas registradas."
        fillHeight
        getRowKey={(person) => person.public_id}
        renderActions={(person) => (
          <Stack direction="row" gap={0.5} justifyContent="flex-end">
            <ActionIconButton
              label="Editar"
              onClick={() => setEditing({ mode: "edit", person })}
            >
              <EditOutlinedIcon fontSize="small" />
            </ActionIconButton>
            {person.is_active ? (
              <ConfirmActionButton
                confirmLabel="Si, desactivar"
                label="Desactivar"
                onConfirm={() => handleDeactivate(person)}
                question={`Se desactivara a ${person.first_name} ${person.last_name}. Los expedientes que la referencian conservan el vinculo.`}
                title="Desactivar persona"
              />
            ) : null}
          </Stack>
        )}
        subtitle="Personas institucionales"
        title="Personas registradas"
      />

      <EntityFormWindow
        fields={PERSON_FIELDS}
        initialValues={EMPTY_VALUES}
        key={editing?.mode === "create" ? "create-open" : "create-closed"}
        onCancel={() => setEditing(null)}
        onSubmit={handleCreate}
        open={editing?.mode === "create"}
        submitLabel="Crear persona"
        title="Nueva persona"
      />

      {editing?.mode === "edit" ? (
        <EntityFormWindow
          fields={PERSON_FIELDS}
          initialValues={{
            first_name: editing.person.first_name,
            last_name: editing.person.last_name,
            email: editing.person.email || "",
            phone_number: editing.person.phone_number || "",
            institutional_identifier:
              editing.person.institutional_identifier || "",
          }}
          key={editing.person.public_id}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          open
          submitLabel="Guardar cambios"
          title={`Editar ${editing.person.first_name} ${editing.person.last_name}`}
        />
      ) : null}
    </>
  );
}
