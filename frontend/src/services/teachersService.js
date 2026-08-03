import { apiClient } from "./apiClient.js";
import { teachers } from "../mocks/teachers.js";

// No existe un modelo dedicado de docente/staff ni endpoint REST todavia
// (un "docente" es hoy solo `people.Person` referenciado desde
// `academics.TeachingAssignment.teacher`). Cambiar a `true` cuando el
// backend publique el endpoint real y su contrato haya sido confirmado
// (ver plan T10). El interruptor vive aqui, no en `apiClient`, para que
// activar un dominio no afecte a los demas.
const TEACHERS_API_AVAILABLE = false;

const records = [...teachers];
let nextId = records.length + 1;

function listMock() {
  return Promise.resolve([...records]);
}

function getMock(id) {
  const record = records.find((item) => item.id === Number(id));
  if (!record) {
    const error = new Error("Docente no encontrado.");
    error.status = 404;
    return Promise.reject(error);
  }
  return Promise.resolve(record);
}

// mock-only: agrega a la lista en memoria, no persiste entre recargas.
// T10 reemplaza este cuerpo por `apiClient.post("/teachers/", data)` real,
// sin cambiar la firma que ya consumen las pantallas.
function createMock(data) {
  const created = { ...data, id: nextId };
  nextId += 1;
  records.push(created);
  return Promise.resolve(created);
}

export const teachersService = {
  list: () =>
    TEACHERS_API_AVAILABLE ? apiClient.get("/teachers/") : listMock(),
  get: (id) =>
    TEACHERS_API_AVAILABLE ? apiClient.get(`/teachers/${id}/`) : getMock(id),
  create: (data) =>
    TEACHERS_API_AVAILABLE
      ? apiClient.post("/teachers/", data)
      : createMock(data),
};
