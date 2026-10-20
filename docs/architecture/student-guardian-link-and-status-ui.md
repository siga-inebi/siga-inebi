# E8 y E9/D5: vinculación de encargados y estado del expediente

Entrega conjunta del issue #632, desde `develop` con #647–#651 integrados.
RF-EXP-003, RF-EXP-004, RF-ALC-001 y RF-BIT-002; ADR-0004/0005/0006/0008.
Incluye E7 y la base común #630 integrada. No implementa conversión D10.

## Vincular encargado (E8)

En Encargados, Vincular permite buscar por nombre o CUI en el servidor y recorrer
una página por solicitud. Cambiar la búsqueda vuelve a página 1; una respuesta
anterior no sustituye la consulta nueva. No descarga el padrón completo.

Se puede elegir un encargado existente o crear uno sin abandonar el expediente.
Crear solicita los mismos datos institucionales que el alta de encargados y el
parentesco. Un solo POST guarda persona, encargado, vínculo y auditoría en una
transacción. Un error revierte todo y conserva el formulario para corregirlo.
Cancelar no escribe. Durante el envío se bloquean doble envío, cancelación y
navegación interna del expediente. Al terminar se recargan los vínculos del alumno.

Se rechaza un vínculo vigente duplicado y un encargado/persona inactivos. Un CUI
ya registrado no crea otra persona: hay que buscar el encargado existente; convertir
una persona que todavía no tiene perfil de encargado corresponde a D10. Una relación
finalizada se conserva y puede coexistir con un vínculo nuevo. El primer vínculo
vigente conserva la regla existente de encargado principal.

## Cambiar estado (E9/D5)

El formulario general deja de mostrar y enviar `status`. Datos ofrece la acción
Cambiar estado según capacidad del servidor, selector de estados en español,
revisión y confirmación explícita. Conserva los estados ya definidos por el modelo.

Las advertencias se calculan en el dominio: Activo sin matrícula vigente, o un
estado distinto de Activo con matrícula vigente. Se muestran en consulta y revisión;
no impiden confirmar. La escritura reevalúa la información y devuelve los avisos
actuales. No crea, retira, cambia ni elimina matrículas, vínculos, credenciales o
registros históricos. Las restricciones existentes que consultan Student.status
siguen aplicándose; esto no ejecuta un movimiento académico.

Confirmar envía `expected_status`: si otro proceso cambió el estado, se rechaza
sin sobrescribirlo y se solicita recargar. El servicio bloquea la fila y guarda
estado y auditoría juntos. Una falla de auditoría revierte la escritura.
Un perfil desactivado (`is_active=false`) no se reactiva mediante esta acción.
Elegir el estado Inactivo conserva la distinción existente respecto a desactivar
el perfil: solo cambia `status`, no `is_active`.

La ficha muestra el último cambio manual registrado: autor conservado en auditoría,
fecha y estados anterior/nuevo. Reconoce también los eventos antiguos
`students.student.updated` que cambiaron status y las desactivaciones. No inventa
autor/fecha para modificaciones académicas que no tienen ese evento de Student:
en ausencia de evidencia muestra Sin cambios manuales de estado registrados.
No expone la bitácora completa, IP, contexto privado ni datos de otros alumnos.

El PATCH general previo sigue admitiendo status para compatibilidad con clientes
existentes; su escritura/auditoría se hace atómica y con bloqueo de fila, y su evento
sigue siendo visible en la ficha. La UI nueva usa exclusivamente la acción propia.

## Contratos y permisos

Bajo `/api/v1/students/records/{public_id}/`, con UUID de estudiante:

| Ruta | Contrato |
|---|---|
| `guardians/link/` POST | `{guardian_id, relationship_label}` o `{person, relationship_label}`; 201 con relación y encargado, sin CUI/nacimiento en lectura |
| `status/` GET | `?status=...` opcional para revisar un destino; contexto, capacidad, opciones, matrícula vigente, advertencias y último cambio |
| `status/` POST | `{status, expected_status}`; 200 con contexto actualizado |

GET status exige `student.view_basic`; cada POST exige `student.edit_basic` y
alcance sobre el estudiante. Se autoriza antes de validar datos personales o
escribir. Sesión/CSRF existentes; 403 sin permiso, 404 fuera del alcance, 400 para
payload inválido, duplicado, perfil inactivo o confirmación obsoleta. La capacidad
de lectura no audita una escritura no intentada. La búsqueda reutiliza el GET de
encargados existente con `search` y `page`; no amplía su contrato ni retorna CUI.
La ficha añade `actions.link_guardian`, calculada por permiso, alcance y estado;
la interfaz oculta Vincular cuando esa capacidad es falsa. Cada POST revalida acceso.

Las vistas solo adaptan HTTP; queries concentra lecturas y alcance, servicios las
reglas y transacciones, React la presentación. Sin modelos, migraciones, variables,
dependencias ni permisos nuevos. La ruta invalida las cachés de encargados y
personas, además de estudiantes, mediante la base común de #630. El selector
paginado del formulario conserva `usePaginatedList` para recorrer todas las
coincidencias sin guardar nombre/CUI en la URL; el selector remoto común solo
expone la primera página. La migración de padrones principales queda separada.
Datos del formulario solo en memoria; no hay cuenta de encargado, portal ni
almacenamiento persistente de datos personales.

## Validación y límites

Pruebas API cubren autorización, alcance, validación, privacidad, duplicados,
rollback de persona/encargado/vínculo/auditoría, avisos no bloqueantes,
confirmación obsoleta, preservación de matrícula y trazabilidad antigua/nueva.
Pruebas UI cubren búsqueda/página, errores y reintentos, creación y vínculo en una
solicitud, confirmación/cancelación, doble envío y trazabilidad.

Las cuatro pruebas antiguas de studentRecordServices recuperadas por #649 se
alinean con los métodos paginados y la ruta UUID que usa el expediente actual,
igual que en #650. Se conservan sus comprobaciones de página y respuesta.

Los resultados de suites, CI y revisión visual se registran en el PR de esta
entrega. Preview local aislado: frontend 5189, backend 8017, base sintética
`siga_inebi_e8_e9_preview`. No se versionan bases, medios, cookies o logs privados.
Aceptación funcional institucional pendiente; no cierra el epic ni cambia los
estados históricos de los RF en la matriz.

Validación local sobre `develop` integrado (`0d6eeab`, incluye #650/#651):

- PostgreSQL completo: **2105 aprobadas, 23 omitidas, cobertura 95.40%**.
- Frontend completo: **540 pruebas / 69 archivos, cobertura 88.26%**. Después,
  **37 pruebas focalizadas** verifican los ajustes finales de recarga y caché,
  incluida la nueva regresión que no repite POST tras una recarga fallida.
- API final: **37 aprobadas**, con privacidad, alcance, auditoría antigua sin
  falsos cambios y confirmaciones concurrentes. Ruff/formato, ESLint, Prettier,
  Django check y ausencia de migraciones propias aprobados.
- OpenAPI: **0 errores**, 26 avisos (22 únicos) del esquema completo.
- Build: **226123/230000 bytes gzip** inicial; **245410/250000 bytes gzip**
  para la página de mayor tamaño. Herramientas de requerimientos/carga: **69**.
- HTTP real con sesión/CSRF/no-store y Chromium en escritorio/móvil aprobados
  después de integrar la base común. Docker y versiones fijadas se verifican
  separadamente en CI; sus resultados quedan en el PR.

## Reversión

Revertir los commits de esta entrega devuelve los formularios anteriores. No hay
migraciones. No borrar personas, vínculos o eventos ni deshacer estados con SQL;
las correcciones posteriores deben conservar su auditoría.
