// Aun no existe un endpoint de permisos consultable desde el frontend, asi
// que estas funciones retornan `true` siempre. El backend sigue siendo la
// autoridad de autorizacion real; cuando exista el endpoint, reemplazar el
// cuerpo de cada funcion por la verificacion contra `user` (y sus permisos)
// sin duplicar la regla de negocio en el cliente.

export function canViewAlumnos(_user) {
  return true;
}

export function canViewDocentes(_user) {
  return true;
}

export function canViewPadres(_user) {
  return true;
}
