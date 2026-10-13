# Resultado de la primera corrida de expediente

Backend: 150 casos, 150 aprobados, 0 fallidos, 0 omitidos. Exit code 0.
Frontend: 31 casos, 29 aprobados, 2 fallidos, 0 omitidos. Exit code 1.

## RUN-DIA-20261012-01 — backend

Pytest reportó 36,67 segundos y seis advertencias: cuatro `RemovedInDjango60Warning`
por `CheckConstraint.check` en modelos/migraciones de academics y enrolments, y dos
`UnorderedObjectListWarning` en el listado de contactos de emergencia. Las primeras
son de mantenimiento; las segundas se registran como INC-009. Ninguna provocó fallos.

- SHA: `72ea438cd9a2427524346856d850578f6132e715`. Árbol limpio al comenzar (`git-status.txt` vacío).
- Inicio UTC: 2026-10-12T22:41:32Z; fin UTC: 2026-10-12T22:42:47Z.
- Ejecutó: Claude Code para Diana; revisión de Santiago pendiente.
- Entorno: Windows, Docker Desktop/Linux, Python 3.11.17, Django 5.2.17, pytest 8.4.1 y PostgreSQL 16.14. Proyecto Compose aislado `siga_inebi_diana_qa`.
- Datos: factories sintéticas, base de pruebas efímera, sin datos institucionales.
- Alcance: 15 archivos de expediente (7 unitarias, 6 API, 1 integración, 1 permisos) más 17 casos de privacidad (RNF-PRI-001/002/003).
- Sin cobertura global (`--no-cov`), navegador ni aceptación institucional.

## RUN-DIA-20261012-02 — frontend

Vitest 4.1.11 sobre Node 22.23.3, jsdom. Tres archivos: `AlumnosPage`, `GuardiansPage`
y `personasPage`. Duración reportada: 48,64 segundos.

- Inicio UTC: 2026-10-12T22:43:15Z; fin UTC: 2026-10-12T22:45:16Z. Mismo SHA.
- Fallidos, ambos con `Test timed out in 5000ms`:
  - `GuardiansPage > submits the create form against the service`
  - `pantalla de personas > crea una persona y recarga el listado`
- El resultado de esta corrida es **Fallido** y así se conserva.

## RUN-DIA-20261012-03 — diagnóstico

Se repitieron solo los dos archivos con fallos usando `--testTimeout=30000`, para
clasificar la causa. No sustituye a la corrida anterior ni cambia la configuración
versionada.

- Inicio UTC: 2026-10-12T22:45:39Z; fin UTC: 2026-10-12T22:46:11Z. Mismo SHA.
- 16 casos aprobados. Los dos que habían fallado terminaron en 6,54 s y 5,24 s.
- El CI de `develop` aprueba `frontend-tests` sobre este mismo commit.
- Conclusión: las dos pruebas quedan a menos de dos segundos del límite por defecto
  en un equipo lento. Se registra INC-008; no hay evidencia de defecto funcional.

## Lectura del resultado

Los 17 requisitos del catálogo continúan sin aceptación: aprobar pruebas existentes
no demuestra todos los criterios. Persisten las discrepancias y brechas documentadas
en [la guía](README.md). No se modifica la clasificación institucional ni se cierra UAT.

Al terminar se detuvo únicamente `db-test` del proyecto `siga_inebi_diana_qa`. Los
contenedores de ejecución se eliminaron con `--rm`; logs y JUnit permanecen en el
repositorio local, ignorados por Git. No se alteró la base de desarrollo.

[Resultados por prueba](resultados-pruebas.csv) · [Evidencia revisada y hashes](evidencia-revisada.md)
