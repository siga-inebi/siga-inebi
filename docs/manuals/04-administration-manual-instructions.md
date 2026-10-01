# Instrucciones: Manual de Administracion

## Objetivo

Explique las operaciones funcionales y de gobierno que solo pueden realizar
usuarios administrativos autorizados, sin convertir el manual en una guia para
eludir controles de seguridad.

## Audiencia

Administracion institucional y administradores funcionales autorizados.

## Reglas previas

- Diferencie administracion funcional de administracion de infraestructura.
- Muestre solo operaciones que el rol administrativo puede ejecutar.
- Use datos ficticios y no exponga credenciales, tokens, cookies ni datos reales.
- Indique la auditoria asociada a cada operacion sensible.

## Contenido obligatorio

### Cuentas y autorizacion

- Provision de cuentas siempre vinculadas a una persona institucional.
- Activacion, desactivacion, restablecimiento asistido y cierre administrativo de
  sesiones, cuando existan.
- Asignacion de roles, permisos atomicos y alcances.
- Explicacion de la denegacion por defecto y de por que no se asignan privilegios
  sin justificarlos.

### Configuracion institucional y academica

- Ciclos escolares: creacion, apertura, cierre y reapertura excepcional.
- Institucion, niveles, grados, secciones, aulas, jornadas y horarios.
- Plantillas y configuraciones institucionales autorizadas.

### Operacion y trazabilidad

- Consulta de auditoria, documentos y reportes autorizados.
- Gestion de incidencias administrativas.
- Reglas para conservar historia: preferir estados, vigencias, revocaciones o
  bajas logicas antes que eliminacion fisica.

### Escalamiento

- Indique que hacer ante acceso indebido, perdida de datos, cuenta bloqueada,
  datos inconsistentes o fallo de una operacion sensible.
- Enlace el plan de soporte y el plan de respaldo y recuperacion.

## Criterios de cierre

- Cada procedimiento debe declarar permiso o rol requerido, precondicion,
  resultado esperado y evento de auditoria cuando aplique.
- El manual no debe prometer operaciones que no esten disponibles en la version
  entregada.
