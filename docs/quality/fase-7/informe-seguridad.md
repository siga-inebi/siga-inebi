# Informe de seguridad — línea base D1

## Alcance y limitaciones

Pablo ejecutó la revisión disponible del frontend sobre el SHA
`0c8f0d396231f46809b95cc088d5f2c557cb919f`. Las pruebas de permisos,
CSRF, cookies, TLS, auditoría y análisis backend no pudieron realizarse:
Docker no está disponible y el entorno Python local es incompatible. Por tanto,
este informe no certifica seguridad de la versión.

## Resultado de dependencias frontend

`npm audit --json` informó 8 vulnerabilidades en el lockfile: 2 críticas,
4 altas y 2 moderadas.

| Componente | Severidad reportada | Hallazgo | Acción |
| --- | --- | --- | --- |
| `vitest` / `tinypool` | Crítica | Gadgets de contaminación de prototipo/RCE en opciones de worker de pruebas. | INC-003: Santiago y Daniel deben evaluar actualización mayor a Vitest 5.0.3 y ejecutar regresión completa. |
| `brace-expansion` | Alta | Denegación de servicio por expansión/recursión no acotada. | Trazar cadena transitiva y actualizar lockfile con revisión. |
| `js-yaml` | Alta | Uso excesivo de CPU mediante fuentes de combinación vacías. | Trazar cadena transitiva y actualizar lockfile con revisión. |
| `nanoid` | Alta | Generador personalizado puede iterar indefinidamente con tamaño cero. | Trazar cadena transitiva y actualizar lockfile con revisión. |
| `source-map-js` | Alta | Denegación de servicio por offsets de secciones de source maps. | Trazar cadena transitiva y actualizar lockfile con revisión. |
| `@vitest/coverage-v8` / `@vitest/mocker` | Moderada | Dependencias de la cadena de Vitest. | Resolver junto con actualización de Vitest. |

El audit no demuestra exposición en producción: los paquetes señalados pertenecen
principalmente a herramientas de desarrollo/prueba. Aun así, hay correcciones
disponibles y la política del repositorio exige atender hallazgos explotables
con fix disponible antes de PR. No se aplicó `npm audit fix` automático porque
ofrece actualización mayor y requiere revisión, lockfile controlado y regresión.

## Controles ejecutados

| Control | Resultado | Evidencia |
| --- | --- | --- |
| ESLint frontend | Aprobado | EJ-D1-003 |
| Pruebas frontend | 283 aprobadas; dos advertencias de `src=""` | EJ-D1-003, INC-004 |
| Build y presupuesto estático | Aprobado | EJ-D1-003 |
| `npm audit --json` | Fallido: 8 vulnerabilidades | EJ-D1-004, INC-003 |
| Bandit, pip-audit y pruebas de seguridad backend | Bloqueado por INC-001/INC-002 | EJ-D1-001/EJ-D1-002 |
| CSRF, cookies, TLS y autorización integrada | No ejecutado | Requiere entorno QA integrado |

## Conclusión

INC-003 permanece abierta con prioridad P0. La seguridad del candidato no es
aceptable hasta contar con triage de dependencias, corrección o excepción
explícita sustentada, y repetir controles sobre entorno backend integrado.
