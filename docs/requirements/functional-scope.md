# Functional Scope

## Objetivo

Definir alcance fundacional de SIGA-INEBI sin asumir cierre total de los 25 modulos descritos funcionalmente.

## Fuente de verdad

- Catalogo RF y RNF recibido en analisis inicial.
- Descripcion funcional general del sistema.
- ADR y decisiones pendientes de este repositorio.

## Principios de alcance

- No implementar aun 25 modulos completos.
- Construir base extensible sin sobrediseño.
- Mantener identificadores originales de requerimientos.
- Diferenciar `Debe`, `Deberia`, `Podria`.
- No inventar reglas no definidas.
- Registrar ambiguedades como decisiones pendientes.

## Nucleo fundacional propuesto

- Identidad, autenticacion, cuentas, roles, permisos y alcances.
- Persona institucional y expediente estudiantil base.
- Ciclos escolares y estructura academica base.
- Matricula, reinscripcion y movimientos esenciales.
- Credencial estudiantil con QR opaco.
- Captura y gobierno de asistencia.
- Gestion documental base y justificaciones.
- Evaluacion academica minima para notas y boletas.
- Bitacora y auditoria transversal.

## Fuera de fase fundacional

- Modulos narrados sin RF cerrados suficientes.
- Inventario y programa de alimentos.
- Agenda y citas.
- Comunicacion institucional completa.
- Dashboard avanzado y reporteria extensa.
- Importaciones generales masivas.
- Automatizaciones no requeridas para nucleo.

## Criterios de inclusion en fase fundacional

- Dependencia fuerte de otros modulos nucleares.
- Impacto transversal sobre autorizacion, historia o trazabilidad.
- Requerimiento marcado como `Debe`.
- Necesidad operativa directa para ciclo, matricula, asistencia o evaluacion.

## Criterios de exclusion o postergacion

- Requerimiento `Deberia` o `Podria` sin bloqueo al nucleo.
- Dependencias aun no cerradas por negocio.
- Riesgo alto por politicas o reglas no definidas.
- Modulo descrito funcionalmente sin especificacion verificable.
