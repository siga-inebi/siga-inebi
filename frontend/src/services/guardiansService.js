import { apiClient } from "./apiClient.js";
import { guardians } from "../mocks/guardians.js";

// `apps/students` no expone endpoint REST de `Guardian` todavia. Cambiar a
// `true` cuando `/guardians/` exista y su contrato haya sido confirmado
// contra docs/architecture/api-conventions.md (ver plan T10). El
// interruptor vive aqui, no en `apiClient`, para que activar un dominio no
// afecte a los demas.
const GUARDIANS_API_AVAILABLE = false;

const records = [...guardians];
let nextId = records.length + 1;

function listMock() {
  return Promise.resolve([...records]);
}

function getMock(id) {
  const record = records.find((item) => item.id === Number(id));
  if (!record) {
    const error = new Error("Padre o encargado no encontrado.");
    error.status = 404;
    return Promise.reject(error);
  }
  return Promise.resolve(record);
}

// mock-only: agrega a la lista en memoria, no persiste entre recargas.
// T10 reemplaza este cuerpo por `apiClient.post("/guardians/", data)` real,
// sin cambiar la firma que ya consumen las pantallas.
function createMock(data) {
  const created = { ...data, id: nextId };
  nextId += 1;
  records.push(created);
  return Promise.resolve(created);
}

export const guardiansService = {
  list: () =>
    GUARDIANS_API_AVAILABLE ? apiClient.get("/guardians/") : listMock(),
  get: (id) =>
    GUARDIANS_API_AVAILABLE
      ? apiClient.get(`/guardians/${id}/`)
      : getMock(id),
  create: (data) =>
    GUARDIANS_API_AVAILABLE
      ? apiClient.post("/guardians/", data)
      : createMock(data),
};
