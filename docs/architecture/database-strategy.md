# Database Strategy

## Motores por ambiente

| Ambiente | Motor | Estado |
| --- | --- | --- |
| Desarrollo rapido local | SQLite | Opcional |
| Desarrollo recomendado | PostgreSQL | Recomendado |
| Pruebas automatizadas | PostgreSQL | Obligatorio |
| Staging | PostgreSQL | Obligatorio |
| Produccion | PostgreSQL | Obligatorio |

## Motivo

- SQLite acelera arranque y exploracion local.
- PostgreSQL es referencia de comportamiento objetivo, integridad y compatibilidad.

## Reglas

- No depender de SQLite en CI.
- No usar SQLite en staging o produccion.
- Validar migraciones y pytest sobre PostgreSQL.
- Mantener modelos y consultas compatibles con ambos solo donde aplica a desarrollo.

## Zona horaria

- El cluster de PostgreSQL se fija explicitamente en la zona horaria del establecimiento
  (`timezone` y `log_timezone`), y el contenedor recibe `TZ` y `PGTZ`. La zona se configura una
  sola vez con la variable `TIME_ZONE`; ver `.env.example`.
- Los instantes se almacenan como `timestamptz`, es decir de forma absoluta. La zona del
  establecimiento interpreta al leer, no altera lo guardado.
- La sesion de Django habla UTC a proposito: con `USE_TZ` activo el ORM fija la conexion en UTC y
  convierte usando `TIME_ZONE`. Fijar el reloj del cluster sirve para lo que entra por fuera de
  Django -- `psql`, `pg_dump`, cron, las lineas del log -- que es donde un servidor en UTC
  enganaria a quien lee.
- Las fechas de efecto y los dias escolares se derivan del reloj local. Un movimiento capturado a
  las 23:30 pertenece a su dia local, no al dia siguiente en UTC.
