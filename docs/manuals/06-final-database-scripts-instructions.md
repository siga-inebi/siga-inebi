# Instrucciones: Scripts Finales de Base de Datos

## Objetivo

Organice y documente los artefactos necesarios para crear, migrar, verificar y
preparar una base PostgreSQL de SIGA-INEBI de manera reproducible.

## Estructura recomendada

Mantenga los scripts versionados bajo `scripts/database/` cuando sean necesarios
fuera de Django. Las migraciones Django permanecen en cada app y son la fuente
principal de evolucion del esquema.

## Artefactos que se deben identificar

- Migraciones Django finales, ordenadas y aplicables desde una base limpia.
- Scripts de catalogos minimos o carga inicial, si existen.
- Scripts de datos demo, separados y rotulados como no productivos.
- Comandos de verificacion de migraciones.
- Procedimientos de respaldo y restauracion referenciados, sin duplicar sus
  scripts canonicos.

## Instrucciones de ejecucion

Para cada artefacto documente:

1. Proposito.
2. Ambiente permitido.
3. Precondiciones.
4. Comando de ejecucion.
5. Resultado esperado.
6. Riesgo o impacto sobre los datos.
7. Forma de verificar que termino correctamente.

## Reglas obligatorias

- Priorice migraciones de Django y ORM sobre SQL manual.
- Pruebe contra PostgreSQL; SQLite no valida la entrega final.
- No versionar volcados, bases locales, archivos `.sql` con datos reales,
  contrasenas ni secretos.
- No use scripts destructivos sin una confirmacion explicita y un procedimiento
  de respaldo y recuperacion documentado.
- Mantenga los scripts idempotentes cuando su naturaleza lo permita.

## Criterios de cierre

- Una base PostgreSQL vacia puede alcanzar el esquema final con los comandos
  documentados.
- `makemigrations --check --dry-run` y las pruebas de migracion aplicables se
  ejecutan sin cambios pendientes.
- Los catalogos y datos demo no contaminan produccion.
