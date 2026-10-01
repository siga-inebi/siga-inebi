# Instrucciones: Plan Basico de Mantenimiento y Soporte

## Objetivo

Defina como se mantendra SIGA-INEBI despues de la entrega y como se registraran,
priorizaran, corregiran y verificaran incidentes, bugs y solicitudes de cambio.

## Alcance

El plan cubre mantenimiento preventivo, correctivo, adaptativo y de seguridad.
No sustituye la operacion diaria de la institucion ni autoriza cambios directos en
produccion sin revision.

## Contenido obligatorio

### Mantenimiento preventivo

- Revision periodica de dependencias, vulnerabilidades, workflows, logs y
  capacidad de almacenamiento.
- Verificacion de respaldos y simulacros de recuperacion.
- Revision de usuarios, roles, permisos y alcances administrativos.
- Validacion de migraciones, cobertura y checks de CI antes de cada entrega.

### Registro de soporte

Defina GitHub Issues o la herramienta institucional como registro oficial. Cada
incidente debe contener descripcion, fecha, responsable, impacto, evidencia,
estado, relacion con requisito y accion correctiva.

### Clasificacion y atencion

Defina al menos estas severidades:

- Critica: indisponibilidad, perdida de datos o exposicion de informacion.
- Alta: operacion institucional bloqueada sin alternativa razonable.
- Media: funcionalidad afectada con alternativa temporal.
- Baja: mejora, defecto visual o ajuste no bloqueante.

Para cada nivel, indique responsable de primera respuesta, objetivo de tiempo de
respuesta y criterio de escalamiento.

### Flujo de correccion

1. Registrar y reproducir el incidente.
2. Evaluar impacto, seguridad y alcance.
3. Crear issue y rama acotada.
4. Agregar una prueba de regresion.
5. Abrir Pull Request, ejecutar CI y realizar revision.
6. Integrar y verificar en el ambiente correspondiente.
7. Cerrar el issue con evidencia y actualizar trazabilidad.

## Criterios de cierre

- El plan debe identificar canal, responsables y evidencia requerida.
- Debe enlazar `docs/development/git-workflow.md`, la estrategia de pruebas y el
  plan de respaldo y recuperacion.
- No debe establecer compromisos de disponibilidad que la infraestructura actual
  no pueda sostener.
