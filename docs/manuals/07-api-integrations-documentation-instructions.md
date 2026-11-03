# Instrucciones: Documentacion de API e Integraciones

## Objetivo

Documente los contratos consumibles de la API REST y cualquier integracion real,
sin exponer secretos ni prometer endpoints inexistentes.

## Formato de entrega

Mantenga una especificacion OpenAPI o Swagger generable desde la implementacion,
acompanada de una guia Markdown que explique decisiones y ejemplos. La guia no
debe sustituir el contrato versionado.

## Contenido obligatorio

### Informacion general

- URL base y versionado de API.
- Formato JSON, fechas ISO 8601 y zona horaria institucional cuando aplique.
- Convenciones de nombres, paginacion, filtros y codigos HTTP.

### Autenticacion y seguridad

- Sesion mediante cookies y requisitos de contexto seguro.
- Prohibicion de exponer o persistir tokens en frontend.
- Denegacion por defecto, permisos atomicos y scopes por operacion sensible.
- Formato de errores y manejo de 400, 401, 403, 404 y 409 cuando corresponda.

### Endpoints

Agrupe endpoints por dominio. Para cada uno indique:

- Metodo y ruta.
- Finalidad.
- Autenticacion, permiso y alcance requeridos.
- Parametros y cuerpo de solicitud.
- Respuesta exitosa y errores esperados.
- Efectos de auditoria, estado o historial.
- Ejemplos sanitizados de request y response.

### Integraciones

- Documente solo servicios externos que realmente se utilicen.
- Defina responsable, datos intercambiados, fallos previsibles y limites.
- Si no existe una integracion externa, declare expresamente que la solucion no
  depende de servicios externos para su operacion base.

## Referencias obligatorias

- `docs/architecture/api-conventions.md`.
- ADR de API y autorizacion.
- Requerimientos funcionales y no funcionales correspondientes.

## Criterios de cierre

- Todo endpoint publicado debe poder verificarse contra la aplicacion.
- Los ejemplos no deben incluir personas, documentos, secretos ni credenciales
  reales.
- El contrato debe explicar cambios incompatibles, si existieran.
