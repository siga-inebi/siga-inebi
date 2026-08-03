import { apiClient } from "./apiClient.js";
import { students } from "../mocks/students.js";

// `apps/students` no expone endpoint REST todavia (config/api/urls.py solo
// tiene auth/health). Cambiar a `true` cuando `/students/` exista y su
// contrato haya sido confirmado contra docs/architecture/api-conventions.md
// (ver plan T10). El interruptor vive aqui, no en `apiClient`, para que
// activar un dominio no afecte a los demas.
const STUDENTS_API_AVAILABLE = false;

const records = [...students];
let nextId = records.length + 1;

function listMock() {
  return Promise.resolve([...records]);
}

function getMock(id) {
  const record = records.find((item) => item.id === Number(id));
  if (!record) {
    const error = new Error("Alumno no encontrado.");
    error.status = 404;
    return Promise.reject(error);
  }
  return Promise.resolve(record);
}

// mock-only: agrega a la lista en memoria, no persiste entre recargas.
// T10 reemplaza este cuerpo por `apiClient.post("/students/", data)` real,
// sin cambiar la firma que ya consumen las pantallas.
function createMock(data) {
  const created = { ...data, id: nextId };
  nextId += 1;
  records.push(created);
  return Promise.resolve(created);
}

export const studentsService = {
  list: () =>
    STUDENTS_API_AVAILABLE ? apiClient.get("/students/") : listMock(),
  get: (id) =>
    STUDENTS_API_AVAILABLE ? apiClient.get(`/students/${id}/`) : getMock(id),
  create: (data) =>
    STUDENTS_API_AVAILABLE
      ? apiClient.post("/students/", data)
      : createMock(data),
};
