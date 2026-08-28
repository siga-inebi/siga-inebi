# System Context

## Proposito

Describir limites de sistema, actores y restricciones operativas de SIGA-INEBI.

## Actores principales

- System Administrator
- Director
- Academic Coordinator
- Administrative Staff
- Teacher
- Attendance Operator
- Parent or Guardian
- Read-only Auditor
- Student, como sujeto de datos, no como usuario confirmado por RF actuales

## Limites del sistema

SIGA-INEBI centraliza informacion academica, administrativa y operativa del establecimiento. En fase fundacional no depende de microservicios ni de plataformas externas obligatorias.

## Contexto operacional

- Institucion unica inicial.
- Zona horaria local del establecimiento, fijada explicitamente en el servidor y en la base de datos mediante `TIME_ZONE`; ver `docs/architecture/database-strategy.md`.
- Uso en escritorio y telefonos de gama baja.
- Operacion critica durante jornada escolar. El trabajo diferido (RNF-REN-003) se drena fuera
  de ese horario: el proceso trabajador corre con concurrencia de uno y dentro de una ventana
  configurable en hora local (`WORKER_WINDOW_START` y `WORKER_WINDOW_END`, RNF-REN-004), para
  no competir por el host mientras el porton escanea.
- Escaneo QR requiere camara en contexto seguro.

## Fronteras de confianza

- Cliente web autenticado.
- API REST autenticada.
- Almacenamiento de archivos gestionado por servidor.
- Base de datos relacional.
- Verificacion publica de documentos, si se implementa despues, con revelacion minima y rate limiting.

## Integraciones actuales

- Ninguna obligatoria en fase fundacional.
- Servicios externos quedan prohibidos salvo necesidad demostrada y decision explicita.

## Restricciones fuertes

- No datos personales dentro de QR.
- No archivos binarios en DB.
- No eliminacion fisica de registros historicos relevantes.
- Auditoria obligatoria en operaciones sensibles.
- Lecturas sensibles auditables segun RF/RNF.

## Vista de alto nivel

```text
Usuarios autorizados
        |
        v
Frontend web (React/Vite)
        |
        v
API REST (Django + DRF)
        |
        +--> PostgreSQL / SQLite local
        |
        +--> Storage de archivos
        |
        +--> Worker simple para tareas diferidas
```
