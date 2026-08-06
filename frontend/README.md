# Frontend Foundation

Espacio reservado para aplicacion React + Vite + JavaScript.

Estado actual:

- Fundacion ejecutable inicial creada.
- Rutas publicas, privadas y auth base incluidas.
- Cliente HTTP centralizado y pruebas Vitest incluidas.
- Catalogo academico completo sobre `apps.academics`: sedes y jornadas
  (`/app/sedes`), niveles, grados y plan de estudios (`/app/niveles`) y cursos
  (`/app/cursos`).
- Navegacion lateral colapsable (`AppNav`) con acceso a Alumnos, Docentes y
  Administrativos, y Padres de familia; visible solo con sesion iniciada.
- Pantallas de listado (busqueda, filtro, paginacion, exportar CSV, detalle
  lateral, alta via modal) para esos 3 dominios, contra servicios con
  interruptor mock/real (`studentsService`, `teachersService`,
  `guardiansService`) — hoy en modo mock porque el backend aun no expone
  esos endpoints REST.

Restricciones:

- Interfaz en espanol.
- Sin datos reales.
- Compatible con navegadores vigentes y telefonos de gama baja.
