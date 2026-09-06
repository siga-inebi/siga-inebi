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
- Operacion critica durante jornada escolar.
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

## Capacidad y disponibilidad

- RNF-CAP-001: toda meta de rendimiento y capacidad se mide contra la
  infraestructura objetivo (1 vCPU / 2 GB) y contra la matricula real del
  establecimiento. A falta de una cifra confirmada por el establecimiento,
  las pruebas de capacidad de esta fase usan ~500 estudiantes como
  estimacion de referencia explicita, no como dato medido; se reemplaza en
  cuanto el establecimiento confirme su matricula real. `CONN_MAX_AGE`
  (ver `backend/config/settings/base.py`) reusa conexiones a PostgreSQL para
  no competir por CPU en cada peticion bajo ese perfil.
- RNF-DIS-001: el servicio se opera para estar disponible durante la
  ventana de jornada lectiva en dias de clases; no se compromete operacion
  continua 24/7 ni esquemas de alta disponibilidad (replicas, failover
  automatico). Mantenimiento o reinicios fuera de esa ventana no constituyen
  incumplimiento de este RNF. El healthcheck de `backend` en `compose.yml`
  (`python manage.py check`) es la senal operativa minima de que el
  servicio esta arriba durante la jornada.

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
