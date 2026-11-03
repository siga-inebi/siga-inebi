# Security Policy

## Principios

- Acceso denegado por defecto.
- Minimizacion de datos de menores.
- Auditoria para operaciones sensibles y lecturas sensibles requeridas.
- Compatibilidad con PostgreSQL como objetivo obligatorio.
- Archivos binarios fuera de base de datos.

## Reporte de vulnerabilidades

No publicar vulnerabilidades en issues publicos. Mientras no exista canal institucional formal, reportar hallazgos por canal privado definido por responsable propietario del repositorio.

## Alcance inicial de seguridad

- No almacenar secretos en repositorio.
- No almacenar datos reales.
- No codificar informacion personal en QR.
- No exponer descargas por rutas directas.
- No introducir dependencias o servicios externos sin necesidad demostrada y decision explicita.

## Endurecimiento pendiente

- Gestion de secretos por ambiente.
- Politica formal de retencion.
- Procedimiento de rotacion de credenciales.
- Politica de respuesta a incidentes.
- Reglas de proteccion remota en plataforma Git.
