# Instrucciones: Diccionario de Datos Final

## Objetivo

Construya el diccionario de datos final como referencia formal del esquema
PostgreSQL implementado, sus reglas de integridad y la sensibilidad de la
informacion institucional.

## Fuente de verdad

Use como fuente principal los modelos Django y las migraciones finales. Compare
el resultado con `docs/architecture/initial-data-model.md`, el DER y los
requerimientos; no conserve atributos solo porque aparecian en un modelo inicial.

## Estructura obligatoria por tabla

Para cada tabla incluya:

- Nombre tecnico y nombre funcional.
- Proposito.
- Campo.
- Tipo PostgreSQL y tamano, precision o escala cuando aplique.
- Nulabilidad y valor por defecto.
- Clave primaria, foranea, unica, indice o restriccion.
- Descripcion funcional y regla de validacion.
- Clasificacion de datos: publico, interno, sensible o restringido, cuando
  corresponda.
- Relacion con otras tablas y regla de retencion o historia.

## Cobertura minima

- Personas, cuentas, roles, permisos, scopes y auditoria.
- Estudiantes, encargados, relaciones y contactos de emergencia.
- Institucion, ciclos, niveles, grados, secciones, aulas y asignaciones.
- Matriculas, vigencias, movimientos e historiales.
- Asistencia, evaluacion, resultados, documentos, plantillas y credenciales,
  segun esten presentes en el esquema final.

## Reglas de calidad

- Describa llaves foraneas con tabla y campo de destino.
- Explique restricciones de unicidad e invariantes relevantes, por ejemplo
  matriculas activas incompatibles o cuentas obligatoriamente vinculadas.
- Separe los datos de archivo de los metadatos almacenados en base de datos.
- Mantenga coherencia con la clasificacion definida en
  `docs/architecture/data-classification.md`.

## Criterios de cierre

- Cada tabla y columna efectiva en las migraciones finales aparece una sola vez.
- No incluya valores reales, hashes, secretos ni copias de datos productivos.
- Revise el documento junto con el DER y los scripts de creacion finales.
