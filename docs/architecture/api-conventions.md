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

## Salud y errores

- `GET /api/v1/health/database/` responde `200` cuando la base contesta y `503`
  con el mismo cuerpo JSON cuando no. Una sonda cuyo trabajo es reportar que una
  dependencia esta caida no debe caerse con ella: dejar escapar el error del
  driver producia un 500 sin manejar y una pagina HTML de depuracion que ningun
  monitoreo puede leer.
- El logger `django.request` esta declarado explicitamente con salida a consola.
  La configuracion por defecto de Django le adjunta `AdminEmailHandler`, que
  renderiza una plantilla de traceback en cada respuesta 4xx y 5xx incluso con
  `ADMINS` vacio.

## Operaciones asincronas

- Procesos largos responden con estado aceptado o recurso de job cuando aplique.
- Generacion por lote no debe bloquear request sincrono.

## Borrado

- Evitar delete fisico en recursos historicos.
- Preferir estados, revocacion o desactivacion.
