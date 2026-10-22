import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";

export function StudentDocumentUploadWindow({ onCancel, onSubmit }) {
  return (
    <EntityFormWindow
      description="El archivo se valida, se almacena fuera de la base de datos y queda vinculado a este expediente."
      fields={[
        {
          name: "file",
          label: "Documento escaneado",
          type: "file",
          accept: ".pdf,.jpg,.jpeg,.png",
          required: true,
        },
      ]}
      initialValues={{ file: null }}
      onCancel={onCancel}
      onSubmit={onSubmit}
      open
      submitLabel="Subir documento"
      title="Subir documento escaneado"
    />
  );
}

export default StudentDocumentUploadWindow;
