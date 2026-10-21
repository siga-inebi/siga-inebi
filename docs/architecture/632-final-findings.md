# Cierre de hallazgos PE1, PE4, TD2, DO1, DO2, R1 y R2 — issue #632

## Alcance

Esta entrega cierra los siete hallazgos funcionales restantes asignados a Persona 3 en
`docs/ux-ui.md`. Reutiliza los contratos existentes de Personas, expedientes documentales,
almacenamiento y alertas. No añade tablas ni elimina historial.

## Personas

- **PE1:** `include_inactive=true` se conserva como inclusión explícita. La interfaz vuelve a
  consultar el servidor al cambiar «Mostrar desactivados»; por omisión solo muestra personas
  activas. Hay pruebas de API y UI para ambos estados.
- **PE4:** Personas permanece en **Administración** y explica que es el registro base de
  identidad compartido por cuentas y expedientes. Las tareas académicas siguen en sus módulos.
  Se conserva la visibilidad por `person.view`/`person.edit` definida en ADR-0011.

## Documentos

- **TD2:** cada tipo devuelve `template_count` y `active_template_count`, calculados en la
  consulta con agregados de PostgreSQL. La pantalla distingue plantillas activas y el total
  histórico.
- **DO1:** la pestaña Documentos del expediente permite subir un escaneo, reemplazar el archivo
  vigente como una versión nueva y verificar el SHA-256 almacenado. Las cargas solo se muestran
  con `document.upload`; el servidor revalida permiso y alcance. Verificar reutiliza
  `document.read`. Los archivos históricos permanecen descargables y no se sobrescriben.
- **DO2:** `/app/almacenamiento-documental` muestra bytes, cantidad de archivos, conservados,
  umbral, proyección y desglose MIME desde `/documents/storage-consumption/`. El módulo se
  presenta a quien tiene `document.upload`; el endpoint conserva su contrato actual.
- **DO3:** ya estaba cubierto por la pestaña Documentos del expediente; se corrige su estado
  documental sin duplicar implementación.

## Alertas

- **R1:** «Alertas» se describe como el tablero institucional que requiere seguimiento y
  conserva atención. Asistencia llama «alertas operativas» a las señales del día asociadas a
  movimientos. No se mezclan modelos ni ciclos de vida.
- **R2:** cada alerta institucional incluye `student_name` y `student_code`, además del UUID
  existente, y enlaza a `/app/alumnos/{student_id}`. La consulta usa `select_related` para evitar
  una consulta por fila y continúa filtrada por permiso y alcance del estudiante.

## Contratos y compatibilidad

Los cambios de respuesta son aditivos: tipos documentales agregan dos conteos y alertas agregan
nombre y código del estudiante. Se mantienen UUID públicos, paginación, PostgreSQL, archivos
fuera de la base de datos y baja lógica. No hay migraciones ni variables nuevas.

## Reversión

Revertir el PR retira las superficies nuevas y los campos aditivos. Los documentos subidos o
reemplazados durante su vigencia se conservan como registros históricos y no deben borrarse.
