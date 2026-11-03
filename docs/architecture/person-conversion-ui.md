# #632: Personas, perfiles y conversión D10

## Comportamiento

Personas consulta una página del servidor con búsqueda por nombre o CUI, tamaño
de página y estado en la URL. Cada fila muestra si la persona ya tiene perfil
de estudiante, docente, encargado o cuenta. «Convertir» ofrece solo los perfiles
que aún no existen. Los formularios de alta de los tres dominios también ofrecen
buscar una persona registrada antes de crearla; esta búsqueda requiere acceso al
registro de Personas. La fecha de nacimiento y el CUI nunca se devuelven en el
listado: quien convierte confirma esos datos en el formulario.

## Contrato HTTP

- `GET /api/v1/people/?search=...&page=...&page_size=...&include_inactive=...`
  requiere `person.view` o `person.edit` con alcance `identity`. La respuesta
  agrega `profiles: {student, teacher, guardian, account}` (booleanos). No agrega
  CUI ni fecha de nacimiento a la respuesta.
- `POST /api/v1/people/` y `PATCH/DELETE /api/v1/people/{public_id}/` requieren
  `person.edit` con alcance `identity`. Las denegaciones se auditan mediante
  `ScopedAtomicPermission`.
- `POST /api/v1/students/`, `POST /api/v1/teachers/` y
  `POST /api/v1/students/guardians/` conservan el alta con `person` anidada.
  Como alternativa aceptan `person_public_id` y, opcionalmente, `person` con
  datos institucionales para completar. En conversión se requiere además
  `person.edit` con alcance `identity`; estudiantes sigue exigiendo
  `student.edit_basic` con alcance `students`. El `person_public_id` solo se
  acepta al crear. El servidor rechaza una persona inactiva, incompleta o que ya
  tenga perfil de ese tipo. La persona y la cuenta existentes conservan su ID.

La actualización de campos de persona, el alta del perfil y ambos asientos de
auditoría forman una transacción. Si falla la creación o la auditoría, no se
guardan campos parcialmente. Un CUI que pertenezca a otra persona se rechaza.
La comprobación de nombre en la interfaz ayuda a identificar posibles
duplicados; nombres iguales no se bloquean porque no son una clave única.

## Evidencia y límites

`test_person_conversion_api.py` cubre los tres perfiles, reutilización del ID,
actualización, duplicado, permisos, búsqueda e indicadores. Las pruebas de
Personas y conversión comprueban la búsqueda y el flujo visible.
Este cambio aplica `person.view/edit` a Personas según ADR-0011. Las brechas de
autorización restantes de otros endpoints siguen en #643.
