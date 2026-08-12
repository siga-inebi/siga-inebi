# API Conventions

## Estilo

- API REST con JSON.
- Versionado inicial por prefijo cuando exista implementacion, por ejemplo `/api/v1/`.
- Nombres tecnicos en ingles.
- Mensajes funcionales y documentacion visible en espanol cuando aplique.

## Convenciones base

- Recursos en plural.
- Identificadores opacos hacia cliente cuando convenga seguridad.
- Fechas y horas en ISO 8601.
- Interpretacion de fecha efectiva y eventos en zona horaria local del establecimiento.
- Errores consistentes con codigo, mensaje y detalles validables.

## Seguridad

- Sesion via cookie segura para frontend web.
- No exponer rutas directas a archivos.
- Endpoints sensibles requieren auditoria.
- Autorizacion evaluada por operacion, no solo por menu.

## Operaciones asincronas

- Procesos largos responden con estado aceptado o recurso de job cuando aplique.
- Generacion por lote no debe bloquear request sincrono.

## Borrado

- Evitar delete fisico en recursos historicos.
- Preferir estados, revocacion o desactivacion.

## Provision administrativa de cuentas

- `POST /api/v1/identity/accounts/` provisiona una cuenta pendiente vinculada a una persona.
- La respuesta incluye el codigo de activacion inicial una sola vez y no debe almacenarse en cache.
- `POST /api/v1/identity/accounts/{account_id}/activation-challenges/` revoca el desafio anterior y
  emite uno nuevo.
- Ambos endpoints requieren sesion; los servicios de dominio exigen respectivamente
  `account.create` y `account.activate`.
- `POST /api/v1/identity/accounts/activate/` permite al titular canjear sin sesion previa el codigo
  mediante `username`, `activation_code` y `password`.
- La activacion devuelve una respuesta uniforme ante cuenta inexistente, codigo incorrecto,
  vencido, revocado, agotado o ya utilizado.

## Catalogo de permisos atomicos

- `GET /api/v1/identity/permissions/` devuelve el catalogo paginado de permisos atomicos.
- Requiere sesion y el permiso administrativo logico `role.assign`, representado en Django por
  `role_assign`; los superusuarios tambien pueden consultarlo.
- La respuesta publica usa codigos con punto, por ejemplo `attendance.record_entry`.
- La consulta exitosa y el intento autenticado denegado generan eventos de auditoria.
## Relaciones estudiante-encargado

- `POST /api/v1/students/guardian-relations/` crea una asociacion; `is_primary` es calculado por
  el servicio y no se acepta en el payload.
- `POST /api/v1/students/guardian-relations/{id}/make-primary/` designa una relacion vigente como
  principal.
- `POST /api/v1/students/guardian-relations/{id}/end/` conserva el registro y termina el acceso.
  Debe incluir `replacement_relation` al terminar la relacion principal.
