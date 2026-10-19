# Guía de textos y convenciones de interfaz

Aplica a todo texto que lee una persona: etiquetas, botones, mensajes, menús,
encabezados y mensajes de error del backend. Sale de [docs/ux-ui.md](../ux-ui.md),
sección 1.6. La convención de nombres técnicos en inglés (código, campos de la
API, acciones de auditoría) no cambia: esta guía es para el texto visible.

## 1. Ortografía

- **Siempre con tildes y eñes**: "Código", "Teléfono", "Año del ciclo",
  "Contraseña", "Sesión", "Matrícula", "Evaluación", "Administración".
  Un texto sin tilde junto a otro con tilde en la misma pantalla es un error.
- Signos de apertura en preguntas y exclamaciones: "¿Olvidó su contraseña?".
- Puntos suspensivos con el carácter `…` en estados de carga: "Guardando…".
- Rango con raya: "Mostrando 1–25 de 60".

## 2. Tono

- Tratamiento de **usted**: "Escriba el motivo", "Pídalo a administración".
- Frases cortas, en positivo, que digan qué hacer: "Elija la persona que
  recibirá el acceso" en lugar de "Persona inválida".
- Botones con verbo en infinitivo y objeto cuando hace falta: "Dar acceso al
  sistema", "Reemitir código", "Guardar cambios". La acción destructiva va al
  final y en color de error.
- Confirmaciones: título con la acción ("Desactivar cuenta"), mensaje con la
  consecuencia ("deja de poder entrar; no se borra"), botones "Cancelar" a la
  izquierda y la acción a la derecha.

## 3. Estados y etiquetas

- Estados en femenino o masculino según el sustantivo y siempre traducidos:
  cuenta "Pendiente / Activa / Bloqueada / Desactivada"; asignación de rol
  "Vigente / Por vencer / Programada / Finalizada"; tarea "En ejecución /
  Finalizada / Fallida". Nunca se muestra el valor crudo (`active`).
- El backend devuelve la etiqueta (`status_display`, `TextChoices` en español);
  el frontend la usa y solo cae a su tabla propia si falta.
- Vacíos: "No hay *entidades* registradas" para catálogos, "Sin *cosa*" en
  sublistas y "Sin *entidades* para los filtros seleccionados" con filtros.

## 4. Fechas, horas y números

- Siempre con `formatDate`, `formatDateLong` o `formatDateTime` de
  `frontend/src/shared/utils/format.js` (locale `es-GT`, zona
  `America/Guatemala`). Nunca se pinta una fecha cruda (`2026-03-01`).
- Duraciones y tamaños con los formateadores de la pantalla que los muestra
  (por ejemplo `formatDuration`, `formatBytes` en plataforma).
- Porcentajes con `formatPercent` ("87 %").

## 5. Códigos sugeridos

- Todo código o identificador que el sistema puede derivar se **sugiere** y la
  persona solo lo confirma o corrige: código de estudiante, docente, sede o
  nivel (`next-code/`), usuario de cuenta (`nombre.apellido`,
  `/identity/accounts/username-suggestion/`), identificador de rol (derivado
  del nombre). Si el código queda fijo después de crear, el campo lo dice.

## 6. Errores

- El backend escribe sus mensajes en español (RNF-LOC-002), incluidos los 404 y
  403: "No se encontró la cuenta.", "El actor no tiene el permiso requerido.".
  `backend/tests/api/test_localization_messages.py` falla si reaparece un
  mensaje en inglés en `DomainError`, `FieldValidationError`,
  `ResourceNotFoundError`, `AuthorizationError`, `ValidationError`,
  `PermissionDenied` o `NotFound`.
- Un error de un campo va **junto al campo** (`FieldValidationError` responde
  `{"campo": ["...", "..."]}`); el mensaje general arriba del formulario queda
  para lo que no es de un campo.
- No se usa "Ocurrió un error, verifique los datos": se muestra el motivo real.

## 7. Listados, caché y permisos (convenciones técnicas de la interfaz)

- Listados en servidor con `useServerList` (página, tamaño, búsqueda, orden y
  filtros en la URL; selector "Filas por página" funcional). `DataTable` no
  muestra el selector si la pantalla no entrega `onRowsPerPageChange`.
- Exportación CSV con `ExportCsvButton` / `exportAllToCsv`: todos los registros
  del filtro, con avance y sin tope. `collectAllPages` ya no corta en 1 000
  filas: si no puede terminar, falla con un error explícito.
- Toda escritura invalida lo que muestra: `apiClient` emite `siga:mutation` y
  `registerMutationInvalidation` invalida las keys de la ruta
  (`shared/api/invalidation.js`). Las keys salen de `queryKeys.js`; nunca de
  `fn.name`.
- Entidades grandes en formularios con `type: "search-select"` (búsqueda en el
  servidor).
- Menú, rutas y acciones se filtran con los permisos efectivos de `/auth/me/`
  (`permissions.js`, `<Can>`, `usePermissions`). Es presentación: el backend
  sigue autorizando cada operación. La tabla acción → permiso de cada módulo y
  lo pendiente por dueño está en [permisos-en-ui.md](permisos-en-ui.md).
