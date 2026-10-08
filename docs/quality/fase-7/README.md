# Expediente de calidad — Fase 7

Este directorio conserva evidencia de la Fase 7 para una versión identificable de SIGA-INEBI. Pablo coordina su consolidación; cada responsable de dominio entrega sus resultados, evidencias y regresiones.

## Estado al inicio

- Candidato evaluado inicialmente: pendiente de fijar en `manifiesto-version.md`.
- Aceptación institucional: pendiente. Ningún documento de este directorio equivale a una aceptación firmada.
- Datos: solo sintéticos. No guardar secretos, cookies, tokens, expedientes reales, respaldos ni volcados de base de datos.
- Resultados de pruebas: usar `ejecuciones.csv`; no sustituir un resultado real por una afirmación de conformidad en Markdown.

## Índice

| Archivo | Propósito | Responsable |
| --- | --- | --- |
| `alcance-y-decisiones.md` | Alcance, dependencias y decisiones que bloquean validación. | Pablo |
| `catalogo-casos.csv` | Universo de requisitos, clasificación inicial y vínculos de caso/ejecución. | Pablo + responsables de dominio |
| `matriz-final.csv` | Instantánea de validación por requisito sobre candidato final. | Pablo |
| `ejecuciones.csv` | Registro inmutable de cada corrida o caso manual. | Ejecutores; Pablo consolida |
| `incidencias.csv` | Registro y clasificación de defectos y bloqueos. | Reportante; Pablo hace triage |
| `correcciones-y-regresion.md` | Correcciones aprobadas y regresión posterior. | Pablo + autor/revisor |
| `informe-seguridad.md` | Resultado de controles de seguridad y dependencias disponibles. | Pablo coordina; Santiago/Daniel resuelven |
| `reporte-final-pruebas.md` | Informe de estado y recomendación QA. | Pablo |
| `acta-aceptacion.md` | Borrador de acta o reporte de aceptación institucional. | Pablo + autoridad institucional |
| `seguimiento-manuales.md` | Estado de manuales y verificación por versión. | Pablo + responsables |
| `../manuals/08-maintenance-and-support-plan.md` | Plan operativo de mantenimiento y soporte. | Pablo + Daniel |

## Actualización reproducible

Regenerar catálogo y matriz base después de cambios de requerimientos o catálogo:

```bash
python3 scripts/quality/generate_phase7_catalog.py
```

El generador no marca requisitos como aprobados: crea filas con resultado `No ejecutado` hasta que cada responsable agregue caso, corrida y evidencia reales.
