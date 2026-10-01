# Instrucciones: Plan Final de Respaldo y Recuperacion

## Objetivo

Formalice la proteccion y recuperacion de los datos y archivos criticos de
SIGA-INEBI mediante procedimientos comprobables, independientes y seguros.

## Fuente de verdad

Parta de `docs/architecture/backup-and-recovery.md`, los scripts bajo
`scripts/backup/`, la estrategia de almacenamiento de archivos y la
configuracion real de PostgreSQL. No redefina valores ni comandos sin verificar
la implementacion.

## Contenido obligatorio

### Activos protegidos

- Base de datos PostgreSQL.
- Archivos y documentos persistidos fuera de la base de datos.
- Configuraciones de despliegue y secretos gestionados fuera del repositorio.
- Repositorio de codigo y documentacion versionada.

### Estrategia de respaldo

- Mantenga respaldos de base de datos y archivos como pilas independientes.
- Indique frecuencia, retencion, ubicacion externa al host, cifrado y controles
  de acceso.
- Documente manifiestos, checksums e integridad antes de restaurar.
- Declare RPO y RTO, indicando si son valores institucionales confirmados o
  referencias tecnicas pendientes de aprobacion.

### Procedimiento de recuperacion

1. Identificar y aislar el incidente.
2. Determinar si se restaura base de datos, archivos o ambas pilas.
3. Verificar checksum, versiones compatibles y alcance del respaldo.
4. Restaurar en el ambiente objetivo siguiendo los scripts aprobados.
5. Ejecutar verificaciones de integridad funcional y documental.
6. Registrar el incidente, tiempo real de recuperacion y acciones preventivas.

### Pruebas del plan

- Ejecute simulacros de recuperacion en recursos desechables, nunca sobre
  produccion.
- Mida el tiempo real de restauracion y comparelo con el RTO.
- Compruebe que restaurar una pila no modifique accidentalmente la otra.
- Documente fecha, responsable, resultado y acciones derivadas de cada
  simulacro.

## Reglas de seguridad

- Nunca almacene respaldos, dumps, archivos de datos reales o secretos en Git.
- No imprima variables sensibles en comandos, evidencias o logs.
- Restrinja el acceso a respaldos a personal autorizado.

## Criterios de cierre

- El plan identifica activos, frecuencia, retencion, RPO, RTO, responsables y
  pasos de restauracion verificables.
- Todos los comandos referenciados existen y fueron validados en un ambiente
  controlado.
- El resultado de al menos un simulacro queda documentado sin incluir datos
  sensibles.
