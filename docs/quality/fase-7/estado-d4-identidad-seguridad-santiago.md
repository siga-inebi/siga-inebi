# Estado D4 — identidad, autorización y seguridad

Fecha de actualización: 12 de octubre de 2026.
Responsable: Santiago.

## Corrección y regresión

`INC-IDENT-001` tiene corrección técnica y pruebas de regresión en el PR #589.
La solución centraliza la autorización de salud y observaciones en
`can_access_student(...)` y registra los rechazos por `missing_permission` o
`missing_scope` sin alterar el contrato HTTP 403.

Resultados registrados en el PR:

- regresión dirigida: 53 pruebas aprobadas;
- regresión ampliada: 244 pruebas aprobadas;
- `ruff check` y `ruff format --check` sobre los archivos modificados:
  aprobados;
- CI funcional, seguridad, frontend y Docker: aprobados;
- `backend-lint`: falla por errores preexistentes en
  `backend/tests/integration/test_backup_and_recovery.py`, fuera del diff.

## Estado real

D4 está **técnicamente implementado, pendiente de revisión y fusión**. Después
de fusionar #589 debe repetirse la regresión sobre `develop` integrado. El
apoyo y resultado de UAT administrativa dependen de la agenda, el candidato y
los usuarios coordinados por Pablo y Estuardo; no existe evidencia que permita
declararlos ejecutados.

## Condiciones para cerrar D4

1. Aprobar y fusionar el PR #589.
2. Repetir la regresión de `INC-IDENT-001` sobre `develop` integrado y registrar
   el SHA y resultado en `ejecuciones.csv`.
3. Actualizar la incidencia a cerrada únicamente si la repetición confirma los
   eventos de auditoría esperados.
4. Registrar el apoyo o resultado de UAT administrativa, o dejar explícita su
   no ejecución y dependencia externa.
