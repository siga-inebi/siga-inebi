# FASE 7 — Plan integral de pruebas y aseguramiento de la calidad

## 1. Control del documento

| Campo | Valor |
| --- | --- |
| Proyecto | SIGA-INEBI |
| Documento | `tests_plan.md` |
| Versión del plan | 1.1 |
| Fecha de elaboración | 8 de octubre de 2026 |
| Duración | Una semana: cinco jornadas de trabajo, D1–D5 |
| Equipo | Pablo, Santiago, Diana, Josué, Emilio, Estuardo, Roí y Daniel |
| Estado | Plan propuesto; ejecución y aceptación pendientes |
| Responsable del plan | Pablo, coordinación de calidad |
| Revisión | Santiago, Diana, Josué, Emilio, Estuardo, Roí y Daniel; contraparte institucional para alcance y aceptación |
| Fechas de ejecución | Por confirmar; registrar fecha inicial y final en D1 |
| Versión del sistema a evaluar | Por fijar en D1 mediante commit SHA y candidato de entrega |

Este plan concentra la Fase 7 en **una semana**. La revisión del documento, las pruebas, las correcciones, la regresión y los manuales avanzan en paralelo. Los días D1–D5 representan jornadas de trabajo, sin asumir fechas ni numeración de semana académica.

El cronograma anterior de [desarrollo, semanas 9–14](docs/planning/desarrollo-semanas-09-14.md) sirve como antecedente. No se copian sus fechas ni se asume que sus metas estén cumplidas. Para esta fase prevalece la duración solicitada de una semana.

**Este archivo define trabajo y formatos; no certifica resultados.** Ninguna cantidad de pruebas aprobadas, cobertura alcanzada, incidencia cerrada o aceptación institucional se considera real sin ejecución registrada. Los inventarios son referencias del repositorio al elaborar el plan y deben actualizarse contra el SHA seleccionado.

## 2. Objetivo y resultado esperado

Verificar, antes de implementar la versión en el establecimiento, que el sistema integrado cumple los requerimientos incluidos en la entrega, sus criterios de aceptación, las reglas de negocio y las condiciones de calidad aplicables.

Al finalizar D5 debe existir una versión identificable y un expediente de calidad que permita responder:

1. ¿Qué requerimientos y criterios se evaluaron y cuáles quedaron fuera por decisión explícita?
2. ¿Qué pruebas existentes se reutilizaron y qué brechas se cubrieron?
3. ¿Quién ejecutó cada prueba, sobre qué versión y en qué entorno?
4. ¿Qué resultados, evidencias e incidencias respaldan cada conclusión?
5. ¿Qué correcciones se integraron y qué regresiones las verificaron?
6. ¿Qué usuarios validaron los flujos y qué decisión de aceptación emitieron?
7. ¿Qué manuales corresponden a la versión y fueron comprobados?
8. ¿Se autoriza implementar, se acepta con observaciones menores o se rechaza la entrega?

Completar la semana significa entregar un reporte fiel y una decisión sustentada. Si un requisito obligatorio del alcance falla, el resultado correcto es **no apto para implementación**, con pendientes y responsables; el plazo no permite convertir un fallo en aprobado.

## 3. Fuentes y reglas de referencia

| Fuente | Uso en esta fase |
| --- | --- |
| [AGENTS.md](AGENTS.md) | Pruebas junto con cambios, trazabilidad, PostgreSQL, conservación de historia, ausencia de secretos y datos reales; decisión explícita ante ambigüedad material. |
| [Requerimientos estructurados](docs/requirements/requirements.json) | IDs, prioridad, dominio, regla de negocio y criterio de aceptación originales. |
| [Catálogo de requerimientos](docs/requirements/requirements-catalogue.md) | Alcance documentado, issues y referencias de implementación; reconciliar con código. |
| [Alcance funcional](docs/requirements/functional-scope.md) | Núcleo fundacional y exclusiones; no asumir desarrollo de los 25 módulos narrados. |
| [OpenSpec por dominio](docs/requirements/openspec/) | Escenarios y reglas detalladas para casos de prueba. |
| [Matriz canónica](docs/requirements/traceability-matrix.md) | Relación requerimiento → issue → diseño → código → prueba → PR. |
| [Control de cambios](docs/requirements/change-control.md) | Acuerdos sobre alcance, reglas, criterios y excepciones. |
| [ADR](docs/decisions/) y [decisiones pendientes](docs/decisions/pending-decisions.md) | Restricciones arquitectónicas y reglas aún no confirmadas. |
| [Estrategia de pruebas](docs/development/testing-strategy.md), [Docker Testing](docs/development/docker-testing.md), [TDD](docs/development/tdd-guide.md) | Suites, entorno reproducible, cobertura y regresión. |
| [Definition of Done](docs/development/definition-of-done.md) | Cierre verificable de cambios. |
| [Compatibilidad frontend](docs/architecture/frontend-compatibility.md) | Dispositivos, navegadores y presupuestos de recursos. |
| [Contexto del sistema](docs/architecture/system-context.md) | Actores, infraestructura, capacidad y jornada operativa. |
| [Respaldo y recuperación](docs/architecture/backup-and-recovery.md) | Restauración independiente, integridad, RPO y RTO. |
| [Monitoreo operativo](docs/architecture/operations-monitoring.md) | Comandos programados, historial y errores de tareas. |
| [Herramientas de seguridad](docs/development/security-tooling.md) | Análisis estático, dependencias y excepciones documentadas. |
| [Proceso de release](docs/development/release-process.md) | Identificación de entrega; el proceso formal de despliegue figura pendiente. |
| [Instrucciones de manuales](docs/manuals/) | Nueve productos documentales que deben avanzar junto con las pruebas. |

Si fuentes, implementación y criterios difieren, abrir una discrepancia documental o funcional, registrar impacto y solicitar decisión explícita al responsable del requerimiento. No modificar criterios para hacer pasar la implementación ni resolver reglas institucionales por suposición.

## 4. Alcance y línea base

### 4.1 Inventario inicial verificable

El archivo `requirements.json` contiene **230 requerimientos: 195 RF y 35 RNF**. Es el universo para clasificar cobertura y exclusiones; no implica que todos estén implementados ni formen parte de esta entrega.

| Capa | Ubicación | Archivos encontrados | Uso |
| --- | --- | ---: | --- |
| Backend: unitarias | `backend/tests/unit/` | 28 | Servicios, cálculos, reglas, QR, integridad y límites de arquitectura. |
| Backend: API | `backend/tests/api/` | 28 | Contratos DRF, autenticación, endpoints, errores y autorizaciones. |
| Backend: integración | `backend/tests/integration/` | 18 | Persistencia PostgreSQL, relaciones entre dominios, auditoría, asistencia, evaluación y recuperación. |
| Backend: permisos | `backend/tests/permissions/` | 5 | Permisos atómicos, alcances contextuales y derivados. |
| Backend: migraciones | `backend/tests/migrations/` | 4 | Esquema, transformaciones y compatibilidad de datos. |
| Frontend: unitarias y funcionales de componentes | `frontend/src/test/` | 31 | Vitest, Testing Library y jsdom: páginas, formularios, API client, navegación y cámara simulada. |
| Frontend: presupuesto de build | `frontend/scripts/check-build-budget.test.mjs` | 1 | Prueba del verificador de límites estáticos. |
| Herramientas del repositorio | `scripts/requirements/` y `scripts/github/` | Inventariar según impacto | Extracción de requerimientos y automatizaciones; ejecutar si cambian o afectan entrega. |
| Validación continua | `.github/workflows/ci.yml` y otros workflows | Revisar por SHA | Lint, formato, pruebas, cobertura, seguridad, build y arranque Docker. |

Son **83 archivos de pruebas backend**, no 83 casos. Un archivo puede contener múltiples casos y parametrizaciones. La cantidad real se obtiene por colección de pytest y reportes de Vitest; registrar omitidos, fallos de colección y pruebas parametrizadas.

No se identificó configuración de una suite E2E de navegador real en el inventario revisado. Las pruebas de React en jsdom y el smoke HTTP de Docker no demuestran por sí solos un flujo completo de usuario. La prueba E2E de esta semana será manual, contra frontend, API, PostgreSQL y almacenamiento reales del entorno QA. Agregar automatización E2E solo si una brecha y la capacidad disponible lo justifican; no es prerrequisito introducir una herramienta nueva.

### 4.2 Clasificación de cada requerimiento

Pablo y los responsables de dominio completan D1 una fila por cada uno de los 230 IDs:

| Clasificación | Tratamiento |
| --- | --- |
| Incluido e implementado | Ejecutar casos positivos, negativos y de frontera según riesgo. |
| Incluido y parcialmente implementado | Registrar brecha y bloqueo; no aprobar hasta completar y verificar. |
| Incluido sin implementación | Registrar incumplimiento y decisión; no inventar pruebas aprobadas. |
| Diferido por decisión vigente | Citar ADR/acuerdo, impacto, aprobador y fecha; no contar como probado. |
| Fuera de la entrega | Justificación y aprobación explícitas; conservar trazabilidad. |
| Regla o criterio ambiguo | Solicitar decisión explícita; bloquear únicamente casos dependientes. |

La prioridad MoSCoW no autoriza excluir automáticamente un `Debe`. Un `Debería` o `Podría` incluido en la versión también debe evaluarse. Toda exclusión material debe conservar evidencia del acuerdo de alcance.

### 4.3 Dominios que se evaluarán según alcance aprobado

- Identidad, persona institucional, cuentas, sesiones, roles, permisos y alcances.
- Expediente estudiantil, encargados, contactos, salud y observaciones sensibles.
- Ciclos, estructura académica, aulas, horarios y asignaciones docentes.
- Matrícula, reinscripción, movimientos, vigencias y conservación de historia.
- Credenciales QR, captura, lotes, jornadas, justificaciones y consultas de asistencia.
- Configuración de evaluación, calificaciones, resultados y reportes disponibles.
- Archivos, expediente documental, plantillas, emisión y descargas disponibles.
- Bitácora, privacidad, localización, catálogos, monitoreo, capacidad y recuperación.

No se incorporan inventario, alimentación, agenda, comunicación completa ni integraciones externas nuevas por efecto del plan. Si existen funciones adicionales en la versión candidata, inventariarlas y decidir su inclusión con el responsable de alcance.

## 5. Organización de los ocho participantes

El equipo está formado por **Pablo, Santiago, Diana, Josué, Emilio, Estuardo, Roí y Daniel**. La tabla y las tareas individuales siguientes asignan responsables, entregables y revisores por nombre. Estas responsabilidades corresponden al equipo técnico, no a roles ni cuentas del sistema. Los usuarios institucionales que acepten la versión son distintos del equipo técnico.

| Participante | Responsabilidad principal | Pruebas y entregables | Manual en paralelo | Revisor cruzado |
| --- | --- | --- | --- | --- |
| Pablo | Coordinación QA, alcance y trazabilidad | Plan, catálogo consolidado, triage, métricas, reporte final y acta. | Plan de mantenimiento y soporte, junto con Daniel. | Daniel revisa expediente de calidad. |
| Santiago | Identidad y seguridad | Sesiones, cuentas, roles, permisos, alcances, CSRF, privacidad y hallazgos. | Manual de administración. | Diana. |
| Diana | Personas y expediente | Estudiantes, encargados, vínculos, salud, contactos y observaciones; revisión de denegaciones. | Diccionario de datos, con aportes de todos los dominios. | Santiago. |
| Josué | Estructura académica y matrícula | Ciclos, aulas, horarios, asignaciones, matrícula, movimientos y migraciones. | Scripts finales de base de datos y su procedimiento. | Emilio. |
| Emilio | Asistencia y credencial | QR, ingreso/egreso, idempotencia, recuperación de lotes, jornada y justificaciones. | Manual de usuario en video: coordinación del índice y segmentos de asistencia. | Josué. |
| Estuardo | Evaluación y experiencia de uso | Configuración, notas, resultados, reportes; coordinación de usabilidad y sesiones UAT. | Manual de usuario en video: evaluación; integra segmentos que aporten Santiago, Diana, Josué, Emilio, Estuardo y Roí. | Roí. |
| Roí | Documentos y contratos API | Archivos, plantillas, emisión, descargas, integridad, contrato y bitácora transversal. | Documentación de API e integraciones. | Estuardo. |
| Daniel | Entorno, automatización y entrega | PostgreSQL, CI, cobertura, build, carga, respaldo/restauración, manifiesto de versión. | Manual técnico, instalación/configuración y plan final de respaldo/recuperación. | Pablo; Josué verifica instalación. |

Para evitar sobrecargar a Daniel: Josué aporta esquema, migraciones y procedimiento de instalación; Roí aporta almacenamiento y restauración documental; Santiago aporta configuración segura; cada responsable redacta su sección del manual técnico. Daniel integra y verifica, no escribe todos los contenidos desde cero.

### 5.1 Reglas de colaboración

- Cada caso tiene un ejecutor y un revisor. Cada incidencia tiene un responsable de corrección.
- El autor de una corrección no es su único aprobador. El revisor cruzado confirma evidencia y cierre.
- Pablo consolida; los resultados siguen siendo responsabilidad de sus ejecutores.
- Las pruebas de integración entre dominios las ejecuta una pareja de responsables; no basta probar cada módulo aislado.
- Daniel administra entornos y corridas completas. Las corridas de rendimiento y recuperación tienen ventanas exclusivas para evitar interferencia.
- Reunión inicial diaria de 15 minutos: bloqueos, candidato, casos críticos y manuales. Triage diario de 20 minutos; cierre de jornada de 15 minutos con evidencias actualizadas.
- Registrar acuerdos relevantes en documentos o issues. Un mensaje verbal no cierra una incidencia ni acepta una excepción.

### 5.2 Capacidad de referencia y prioridades

Propuesta ajustable en D1: 6 horas efectivas por participante y jornada, **240 horas-persona** totales. No representa disponibilidad confirmada ni una obligación de horas extra.

| Actividad | Reserva propuesta | Distribución |
| --- | ---: | --- |
| Diseño, inventario y trazabilidad | 32 h | Pablo coordina; cada dominio completa sus vínculos. |
| Ejecución y evidencias | 72 h | Suites existentes y flujos manuales en paralelo. |
| Correcciones, revisión y regresión | 56 h | Reserva prioritaria para defectos críticos y altos. |
| Manuales y validación documental | 48 h | Aproximadamente 1,2 h por persona cada día. |
| UAT, consolidación y entrega | 32 h | Pablo y Estuardo coordinan, con apoyo de dominios y Daniel. |

Si la disponibilidad es menor o las brechas superan la reserva, Pablo presenta impacto y solicita decisión de alcance/plazo. No reducir evidencias, omitir regresión obligatoria ni cambiar umbrales para acomodar el calendario.

### 5.3 Tareas y entregables individuales

Cada persona debe **preparar sus casos, ejecutarlos, registrar resultados y evidencias, atender incidencias de su área y verificar la regresión**. La responsabilidad no termina al ejecutar pruebas: debe entregar documentación revisada y vinculada al candidato final. Daniel ejecuta las suites completas; cada dueño de dominio interpreta sus fallos y comprueba sus criterios.

#### Pablo — Coordinación de calidad y cierre

- **D1:** confirmar alcance y fechas; revisar la clasificación de los 230 requerimientos; consolidar catálogo y matriz; registrar decisiones pendientes y confirmar autoridad y agenda de aceptación con Estuardo.
- **D2–D3:** dirigir triage diario; asignar responsable, prioridad y fecha a incidencias; verificar evidencias y cobertura por criterio; escalar bloqueos y actualizar el plan.
- **D4:** consolidar regresión y resultados UAT; comprobar que los fixes tengan revisión y prueba; preparar reporte final y borrador de acta sin anticipar aprobación.
- **D5:** reconciliar matriz final; emitir recomendación QA; presentar resultados a autoridad institucional; registrar decisión y entregar índice completo del expediente.
- **Documentación propia:** expediente en `docs/quality/fase-7/`: `alcance-y-decisiones.md`, catálogo consolidado, `matriz-final.csv`, `reporte-final-pruebas.md`, `acta-aceptacion.md` y plan de mantenimiento/soporte con Daniel.
- **Revisión cruzada:** revisar expediente técnico de Daniel; Daniel revisa consolidación QA de Pablo.

#### Santiago — Identidad, autorización y seguridad

- **D1:** inventariar y vincular pruebas de login, sesiones, cuentas, roles, permisos, alcances y privacidad; preparar cuentas sintéticas permitidas/denegadas con Diana.
- **D2:** ejecutar positivos y negativos de autenticación, CSRF, múltiples roles, permiso sin alcance y acceso a datos ajenos; comprobar persistencia y auditoría de rechazos aplicables.
- **D3:** verificar cookies/TLS en entorno de entrega; revisar hallazgos de dependencias con Daniel; completar informe de seguridad y manual de administración.
- **D4:** corregir incidencias de identidad/seguridad con prueba de regresión; repetir controles y apoyar UAT de administración.
- **D5:** confirmar controles de su área en candidato final, justificar excepciones vigentes y entregar informe y manual revisados.
- **Documentación propia:** casos/ejecuciones/evidencias de seguridad, `informe-seguridad.md` con Daniel y manual de administración; aportar configuración segura al manual técnico e instalación.
- **Revisión cruzada:** revisar resultados y manual de Diana; Diana revisa los suyos. Roí revisa informe de seguridad según matriz documental.

#### Diana — Personas, estudiantes y expediente

- **D1:** vincular criterios y preparar datos de personas, estudiantes, encargados, contactos, salud, observaciones y relaciones vigentes/terminadas.
- **D2:** ejecutar validaciones, duplicidad, vínculos, consultas sensibles y acceso permitido/denegado; probar persona → estudiante → matrícula con Josué.
- **D3:** comprobar pérdida de alcance al terminar vínculos con Santiago; completar diccionario de datos con aportes de todos los dominios y contrastarlo con migraciones.
- **D4:** corregir y repetir casos de expediente; apoyar UAT de secretaría/encargados y revisar manual de administración de Santiago.
- **D5:** entregar resultados finales de expediente y diccionario validado; comprobar que tablas, columnas y restricciones correspondan a versión final.
- **Documentación propia:** casos/ejecuciones/evidencias de expediente, secciones de matriz del dominio y diccionario de datos final. Aportar segmento de video de personas/estudiantes/encargados.
- **Revisión cruzada:** Santiago revisa sus pruebas y documentación; Josué apoya comprobación del esquema.

#### Josué — Ciclos, estructura académica y matrícula

- **D1:** preparar ciclos, secciones, aulas, asignaciones y matrículas sintéticas; vincular criterios y pruebas de migraciones, estados e historia.
- **D2:** ejecutar validaciones de matrícula, movimientos, conflictos, disponibilidad y reasignación; integrar expediente con Diana y asistencia con Emilio.
- **D3:** levantar copia limpia siguiendo manual de instalación de Daniel; verificar PostgreSQL vacío → esquema final, migraciones y seeds; completar procedimiento de scripts de base de datos.
- **D4:** corregir y repetir casos de ciclo/matrícula; verificar efectos sobre asistencia/evaluación/documentos y apoyar aceptación académica.
- **D5:** comprobar historia y esquema del candidato final; entregar procedimientos y evidencia de instalación/migraciones; revisar informe de recuperación.
- **Documentación propia:** casos/ejecuciones/evidencias académicas, scripts finales de base de datos y procedimiento; aportes de esquema/migraciones a instalación y manual técnico. Aportar video de estructura/matrícula.
- **Revisión cruzada:** Emilio revisa sus resultados; Josué revisa asistencia y credencial.

#### Emilio — Asistencia, credencial y captura

- **D1:** preparar credenciales válidas/revocadas, operadores, puntos de control y lotes; vincular criterios QR, ingreso/egreso, jornada y justificaciones.
- **D2:** ejecutar escaneo permitido/denegado, duplicados, idempotencia, reintentos, lote recuperable, estado diario y justificaciones; verificar evento original e historial.
- **D3:** probar cámara real y permisos previos al escaneo; medir lectura → confirmación visual con Daniel; registrar carga y errores; preparar videos de asistencia/credencial e índice de segmentos.
- **D4:** repetir casos corregidos y regresión de asistencia; apoyar UAT de operador/docente y revisar procedimientos académicos de Josué.
- **D5:** verificar captura en candidato final, actualizar segmentos alterados y entregar evidencia, mediciones e índice de videos con Estuardo.
- **Documentación propia:** casos/ejecuciones/evidencias de asistencia, medición visual para `informe-rendimiento.md`, videos de asistencia/credencial e índice con título, módulo, rol y duración.
- **Revisión cruzada:** Josué revisa sus resultados; Estuardo coordina comprobación de experiencia de uso.

#### Estuardo — Evaluación, usabilidad y aceptación con usuarios

- **D1:** vincular criterios de configuración, calificaciones, resultados y reportes; preparar tareas de usabilidad/UAT por perfil y reservar usuarios con Pablo.
- **D2:** ejecutar pesos, fronteras de notas, permisos docentes, estados, cálculos y reportes; probar integración académica con Josué y documental con Roí.
- **D3:** conducir sesiones piloto de usabilidad; registrar tiempos, ayudas, errores y comentarios; comprobar navegación, teclado y móvil; completar informe y videos de evaluación.
- **D4:** facilitar UAT sin ejecutar tareas en lugar del usuario; registrar aprobación/observaciones por escenario y candidato; corregir incidencias de evaluación con pruebas.
- **D5:** gestionar revalidación de cambios por usuarios, entregar informes de usabilidad/UAT y consolidar manual de usuario en video con Emilio.
- **Documentación propia:** casos/ejecuciones/evidencias de evaluación, `informe-usabilidad.md`, `informe-aceptacion-usuarios.md`, videos de evaluación y consolidación de segmentos aportados por compañeros.
- **Revisión cruzada:** Roí revisa evaluación y sus documentos; Estuardo revisa documentos/API de Roí.

#### Roí — Documentos, API y auditoría

- **D1:** vincular criterios de archivos, plantillas, emisión disponible, descarga, hash y bitácora; preparar archivos sintéticos válidos, inválidos y alterados.
- **D2:** ejecutar contratos API, validación de archivos, firmas/expiración/portador, plantillas cerradas y auditoría de lecturas/escrituras; probar flujo documental con Diana/Estuardo.
- **D3:** verificar almacenamiento e integridad y participar en restauración con Daniel; completar documentación de API e integraciones; revisar informe de seguridad.
- **D4:** corregir defectos de su área con regresión; repetir descarga/emisión/auditoría y revisar resultados/documentación de Estuardo.
- **D5:** comprobar contratos y evidencias del candidato final; entregar documentación API y aporte documental al informe y manual de recuperación.
- **Documentación propia:** casos/ejecuciones/evidencias de documentos/API/auditoría, documentación de API e integraciones y aportes a `informe-recuperacion.md`. Aportar video de documentos y auditoría.
- **Revisión cruzada:** Estuardo revisa sus resultados y manual; Daniel valida integración de almacenamiento/recuperación.

#### Daniel — Entornos, automatización, rendimiento y versión

- **D1:** preparar PostgreSQL y entorno aislado; fijar SHA y dataset; ejecutar baseline completo, registrar cobertura y controles; comprobar dispositivos, TLS, recursos y conservación de evidencias.
- **D2:** mantener entorno reproducible, diagnosticar fallos de infraestructura y capturar reportes; revisar dependencias con Santiago; apoyar fixes sin cambiar criterios.
- **D3:** medir capacidad/carga con Emilio, realizar simulacro de recuperación con Roí y entregar comandos a Josué para instalación independiente; identificar RC1.
- **D4:** ejecutar suites completas y controles obligatorios del candidato corregido; capturar regresión/cobertura/build y emitir RC2 si corresponde.
- **D5:** verificar SHA final, ejecutar controles pendientes, consolidar artefactos/checksums e índice de evidencias; entregar manifiesto y revisar expediente QA de Pablo.
- **Documentación propia:** `entorno-y-datos.md`, reportes automatizados/cobertura, `informe-rendimiento.md`, `informe-recuperacion.md`, `indice-evidencias.csv`, `manifiesto-version.md`, manual técnico, instalación/configuración y plan de respaldo/recuperación; soporte con Pablo.
- **Revisión cruzada:** Pablo revisa su entrega; Josué verifica instalación y recuperación. Daniel integra aportes técnicos de compañeros para distribuir carga documental.

### 5.4 Obligaciones comunes y entrega individual

Al cierre de cada jornada, **cada uno de los ocho participantes** debe:

1. Actualizar sus casos con estado real, candidato SHA y criterio exacto.
2. Registrar ejecución/evidencia y las incidencias encontradas; conservar fallos anteriores.
3. Indicar qué corrigió, qué falta, quién revisará y qué bloqueo necesita decisión.
4. Actualizar su sección de trazabilidad y el manual correspondiente.
5. Entregar a Pablo enlaces a resultados y a Daniel evidencia automatizada/técnica para índice.

Para cerrar su trabajo D5, cada participante entrega: lista de criterios/casos propios, resultados del candidato final, incidencias y correcciones con regresión, evidencias accesibles, producto documental actualizado y constancia de revisión cruzada. Si algo falta, se registra pendiente; nadie firma conformidad sin evidencia.

## 6. Cronograma de una semana

| Día | Trabajo principal | Distribución y dependencias | Manuales en paralelo | Salida verificable |
| --- | --- | --- | --- | --- |
| **D1 — Preparación y línea base** | Confirmar alcance, decisiones, participantes y usuarios UAT; inventariar casos existentes, vincular criterios, preparar datos y entorno; correr smoke y suites completas iniciales. | Pablo dirige clasificación; Santiago, Diana, Josué, Emilio, Estuardo y Roí preparan casos por dominio; Daniel fija SHA, entorno y captura línea base. Reservar dispositivos y usuarios desde este día. | Índices, responsables, fuentes y borradores; cada función documentada se vincula a versión y caso. | Plan revisado, catálogo v1, matriz base, primer reporte automatizado, incidencias iniciales, entorno reproducible y agenda UAT. |
| **D2 — Funcional e integración** | Caminos positivos, negativos y fronteras; integraciones entre dominios; seguridad básica y auditoría. Correcciones desde primera incidencia. | Santiago y Diana: alcance y expediente; Josué y Emilio: ciclo, matrícula y asistencia; Estuardo y Roí: notas y documentos; Daniel conserva baseline y apoya diagnóstico. | Procedimientos, ejemplos sintéticos y primer material visual de flujos estables. | Evidencias de flujos críticos; incidencias clasificadas y asignadas; PRs pequeños con pruebas de regresión. |
| **D3 — Calidad transversal y candidato RC1** | Cerrar primera ronda funcional; usabilidad, compatibilidad/cámara, rendimiento aplicable, recuperación e instalación; repetir pruebas de correcciones. | Estuardo conduce usuarios piloto; Emilio mide flujo visual con Daniel; Roí y Daniel prueban recuperación; Josué verifica instalación desde copia limpia. Congelar RC1 al cierre. | Borradores completos de nueve entregables; contraste contra RC1, revisión cruzada y lista de cambios. | Cobertura completa de casos críticos en primera ronda; mediciones y simulacro; manuales revisables; RC1 identificado. |
| **D4 — Regresión y aceptación inicial** | Integrar fixes prioritarios, ejecutar suites completas y regresión de flujos; realizar UAT sobre candidato identificado; corregir y repetir observaciones que bloqueen. | Daniel realiza corrida global; revisores verifican correcciones; Pablo y Estuardo registran aceptación por rol; autores apoyan sin conducir respuestas. | Usuario ajeno a autor sigue manual; corregir pasos y regrabar únicamente segmentos afectados. | RC2 si hay cambios; evidencia UAT; reporte de regresión; manuales casi finales; lista exacta de bloqueos. |
| **D5 — Cierre y entrega** | Congelar candidato final al inicio; completar regresión pendiente y aceptación de cambios; reconciliar matriz; verificar paquete, acta y versión. | Daniel comprueba SHA y artefactos; Pablo consolida; Santiago, Diana, Josué, Emilio, Estuardo y Roí revisan sus resultados y manuales. Revisión de aptitud al mediodía, entrega documental al cierre. | Publicar versiones finales verificadas, índice de videos y fecha/SHA de validación. | Reporte final, matriz final, registro de incidencias y correcciones, evidencias, UAT, acta, manuales y manifiesto de versión. |

### 6.1 Hitos y control del plazo

- **H1, cierre D1:** alcance, entorno y casos críticos listos; dudas materiales registradas con responsable y vencimiento.
- **H2, cierre D2:** todos los flujos críticos tienen primera ejecución o un bloqueo explícito.
- **H3, cierre D3:** RC1 y borradores documentales completos; ninguna brecha crítica sin diagnóstico y decisión de atención.
- **H4, cierre D4:** regresión global y UAT inicial registradas; bloqueos de aceptación identificados.
- **H5, cierre D5:** versión final y expediente entregados; decisión de implementación firmada o rechazo documentado.

Hasta D3 se integran correcciones de alcance aprobado. D4–D5 priorizan defectos bloqueantes; no se agregan funciones nuevas. Toda modificación tras una corrida final genera nuevo candidato y reevaluación de los casos afectados. Si no hay tiempo para demostrar estabilidad del nuevo candidato, no se autoriza implementar.

## 7. Condiciones de entrada, pausa y salida

### 7.1 Entrada

- Código integrado en un commit identificado; PR abierto no equivale a versión entregada.
- Alcance y criterios disponibles; exclusiones y diferimientos revisados.
- Entorno QA aislado, PostgreSQL 16, almacenamiento de archivos separado y datos sintéticos.
- Suites coleccionables, comandos conocidos y evidencia de baseline, incluso si aparecen fallos.
- Cuentas QA con perfiles y alcances definidos; no usar únicamente superusuario.
- Casos, responsables, dispositivos y sesiones con usuarios reservados.
- Índices de manuales y fuentes listos; disponibilidad real de participantes confirmada.

### 7.2 Suspensión y reanudación

Suspender la prueba afectada ante entorno no identificable, datos corruptos, falla de infraestructura que invalide mediciones, exposición de información sensible o ambigüedad material del criterio. Registrar estado **Bloqueado**, causa y responsable. Continuar casos independientes.

Reanudar solo al comprobar entorno/datos restaurados o decisión explícita registrada. Repetir las ejecuciones invalidadas; no reutilizar sus métricas como aprobadas.

### 7.3 Criterios de salida para implementar

Estos son controles propuestos del plan; Pablo y la contraparte institucional los revisan en D1 sin rebajar obligaciones originales.

| Control | Condición exigida |
| --- | --- |
| Requerimientos | Todos los incluidos tienen criterios, casos, resultados y evidencia; ningún `Debe` incluido queda sin verificar. |
| Casos críticos y de aceptación | 100 % ejecutados y aprobados sobre candidato final, incluidos negativos de seguridad e integridad. |
| Casos obligatorios del alcance | 100 % aprobados; no existen fallidos, bloqueados o no ejecutados que comprometan criterios comprometidos. |
| Automatización | Suites completas backend/frontend y controles obligatorios de CI aprobados sobre SHA final. Todo skip/xfail se explica; uno que cubra criterio obligatorio pendiente bloquea. |
| Cobertura | Backend ≥ 70 %; frontend ≥ 60 %, conforme a configuración vigente. Cobertura de código no sustituye cobertura de requerimientos. |
| Incidencias | Cero críticas o altas abiertas. Las menores solo pueden quedar con evaluación de impacto, responsable, fecha y aceptación expresa, sin afectar criterio obligatorio. |
| Seguridad | Sin acceso indebido, exposición sensible o hallazgo explotable con solución disponible sin atender; excepciones justificadas y revisadas. |
| Rendimiento | RNF aplicables medidos en infraestructura y condiciones declaradas. Sin medición requerida no se declara conformidad. |
| Recuperación | Restauración e integridad verificadas; RPO/RTO documentados y contrastados con metas confirmadas o referencia explícitamente aceptada. |
| UAT | Usuarios representativos completan tareas críticas y validan candidato final; firma de autoridad institucional designada. |
| Manuales | Nueve productos aplicables completos, revisados y reproducibles; funcionalidades ausentes se declaran. |
| Entrega | Reporte, matriz, evidencias, incidencias, correcciones, acta y manifiesto enlazados; SHA y artefactos coinciden. |

**Aceptación con observaciones** solo aplica a incidencias menores sin incumplimiento obligatorio. No habilita excepciones para acceso indebido, pérdida de historia, duplicación crítica, falta de recuperación o requisitos obligatorios sin evidencia.

## 8. Entornos, datos y reproducibilidad

### 8.1 Entornos diferenciados

| Entorno | Propósito | Condiciones |
| --- | --- | --- |
| Automatizado | pytest, Vitest y controles CI | PostgreSQL obligatorio; contenedores de pruebas y datos efímeros. |
| QA integrado | Funcionales manuales, E2E y UAT | React + API real + PostgreSQL + storage; datos persistentes durante ronda, aislamiento del resto de ambientes. |
| Rendimiento/recuperación | Medición objetivo y simulacro | Perfil 1 vCPU / 2 GB claramente delimitado; sin ejecución concurrente de suites u otras cargas ajenas. |

`compose.yml` configura desarrollo; no certifica configuración de producción, HTTPS ni límites de recursos. `compose.test.yml` aísla la base de pruebas, pero tampoco fija por sí solo el perfil de rendimiento. Daniel debe documentar configuración efectiva de QA, TLS y recursos; una limitación se registra, no se oculta.

### 8.2 Ficha de entorno obligatoria

Registrar ID, fecha/hora con zona, operador, SHA, rama/tag si existe, versiones efectivas Python/Node/PostgreSQL/Docker, dependencias bloqueadas, configuración no sensible, backend settings, límites de CPU/RAM y su alcance, sistema operativo, dispositivos/navegadores, conectividad, volumen de datos, almacenamiento y comandos utilizados. No adjuntar `.env` ni volcar variables de entorno.

Para localización, usar `America/Guatemala` según configuración del establecimiento; declarar UTC cuando corresponda a manifiestos. Comprobar conversiones y fronteras de fecha, sin confundir almacenamiento de instantes con presentación local.

### 8.3 Conjunto sintético mínimo

- Dos ciclos, activo y cerrado, más estados adicionales necesarios según criterios.
- Dos ámbitos distinguibles: sedes/secciones; usuarios autorizados en uno y ajenos al otro.
- Persona con cuenta y roles; persona sin cuenta; cuenta desactivada; usuario con múltiples roles; permiso sin alcance y permiso/grant vencido.
- Docente con asignación vigente y finalizada; encargado con relación vigente y terminada; estudiante ajeno a ambos.
- Estudiantes con matrícula activa, movimientos e historial; datos válidos e inválidos para invariantes.
- Credencial válida, revocada y código inválido; lotes nuevos, reintentados, parciales y recuperables.
- Asistencia próxima a cambio de día/jornada y casos límite definidos en OpenSpec.
- Evaluaciones/configuraciones válidas e inválidas; valores en frontera, resultados históricos y ciclo cerrado.
- Adjuntos de prueba permitidos, inválidos, faltantes y alterados; plantillas/descargas según alcance.
- Población representativa para capacidad: referencia de ~500 estudiantes hasta confirmar PD-001; escalar historial y adjuntos, no solo tabla de estudiantes.

Factories y seeds existentes son primera opción. Registrar script/fixture, semilla si procede, cantidades y reinicio. No copiar base productiva ni anonimizar registros reales como sustituto de datos sintéticos. Los usuarios institucionales prueban con identidades QA, no expedientes reales.

Cada ronda debe permitir reconstruir el estado inicial. Los datos históricos usados para comprobar inmutabilidad se conservan durante su ejecución; las limpiezas solo afectan entornos QA identificados.

## 9. Diseño y catálogo de casos

### 9.1 Identificadores

- Casos: `CP-<TIPO>-<DOMINIO>-NNN`, por ejemplo `CP-SEG-ALC-001`.
- Tipos: `UNI`, `API`, `FUN`, `INT`, `SEG`, `USA`, `REN`, `REC`, `REG`, `UAT`, `DOC`.
- Ejecuciones: `EJ-D<n>-NNN`; rondas completas: `RUN-D<n>-NN`.
- Incidencias: `INC-NNN`; evidencias: `EV-<ejecución>-NN`.
- Decisiones de fase: `DEC-QA-NNN`, enlazadas a PD/ADR o control de cambios cuando corresponda.

Una prueba automatizada puede cubrir varios criterios y un criterio puede requerir varias pruebas. Registrar relación precisa por función/nodo o escenario; un enlace a una carpeta no demuestra cobertura.

### 9.2 Ficha de caso obligatoria

```text
ID y título:
Requerimiento(s):
Regla(s) de negocio y criterio(s) de aceptación, texto o referencia exacta:
Dominio / tipo / riesgo / prioridad:
Origen: existente | nuevo | ampliado
Referencia automatizada: ruta::función, nombre Vitest o no aplica
Precondiciones y estado inicial:
Rol, permisos y alcance:
Datos sintéticos y fixture:
Pasos numerados o comando reproducible:
Resultado esperado por paso:
Comprobaciones: UI, API, persistencia, auditoría e historial, según corresponda
Limpieza o restauración del estado:
Ejecutor / revisor:
Aplicabilidad y decisión de exclusión, si existe:
```

Evitar resultados vagos como «funciona». Indicar estado observable, validación, error contractual, acceso permitido/denegado, cambios persistidos y evento de auditoría. El resultado esperado proviene del requisito/ADR, no del comportamiento observado.

### 9.3 Técnicas mínimas

Aplicar particiones válidas/inválidas, fronteras, transición de estados, combinaciones de rol/permiso/alcance, fechas de vigencia, reintentos y concurrencia a los casos que lo requieran. Cada operación sensible debe tener al menos camino permitido y denegado; verificar que el rechazo no modifique datos.

No reescribir toda la suite. Revisar pruebas existentes, enlazar escenarios y agregar pruebas solo donde falte un criterio o donde una incidencia requiera regresión.

## 10. Cobertura por tipo y dominio

### 10.1 Matriz de orientación

Los rangos identifican familias de requerimientos existentes; no certifican cobertura individual ni inclusión automática. Expandirlos por ID y criterio en el catálogo y la matriz de D1.

| Área | Requerimientos candidatos | Escenarios mínimos | Referencias existentes para reutilizar | Responsable |
| --- | --- | --- | --- | --- |
| Autenticación y cuentas | RF-AUT-001–006; RF-CTA-001–007; RNF-SEG-001 | Login/logout, bloqueo, timeout, contraseña, sesiones revocadas, vínculo institucional y estados. | `backend/tests/api/test_auth_api.py`, `test_session_lifecycle_api.py`, `test_identity_account_provisioning_api.py`; `frontend/src/test/App.test.jsx`, `ChangePasswordWindow.test.jsx`. | Santiago |
| Autorización | RF-PER-001–007; RF-ALC-001–009 | Denegación por defecto, múltiples roles, permiso sin alcance, grants vigentes, docente/encargado y ciclo cerrado. | `backend/tests/permissions/`; API de roles y catálogo de permisos. | Santiago y Diana |
| Expediente y estudiantes | RF-EST-001–013; RF-EXP-001–009; RNF-AUD-003; RNF-PRI-001–005 | Validaciones, duplicidad, vínculos, salud/observaciones, acceso por ámbito, auditoría de lectura. | API de estudiantes/personas/encargados/salud/observaciones; `test_student_lifecycle.py`; pruebas de Alumnos y Guardians. | Diana |
| Académico y matrícula | RF-CIC-001–007; RF-MAT-001–008; RF-MOV-001–008; RF-AUL-001–006; RF-HOR-001–011 | Estados de ciclo, vigencias, disponibilidad, conflictos, asignación/reasignación, historial y rollback. | `test_academics.py`, `test_enrolments.py`, `test_cycle_state_guardrails.py`, pruebas de aulas, historia y asignaciones; API relacionadas. | Josué |
| Credencial y asistencia | RF-CRE-001–006; RF-ASI-001–014; RF-JOR-001–011; RF-JUS-001–009; RNF-CON-001–002; RNF-REN-001–002; RNF-USA-001 | QR opaco, escaneo permitido/denegado, ingreso/egreso, duplicados, lote/reintento, jornada, justificación y confirmación visual. | `test_qr.py`, `test_attendance_services.py`, `test_attendance.py`, `test_attendance_api.py`, `test_attendance_permissions.py`, `test_attendance_performance.py`; `AttendancePage.test.jsx`, `camera.test.js`, `useBatchSubmit.test.jsx`. | Emilio y Daniel |
| Evaluación y resultados | RF-EVC-001–007; RF-CAL-001–008; RF-RES-001–009 | Configuración, pesos, fronteras de notas, alcance docente, estados, resultados/reportes e historia. | `test_evaluation_services.py`, `test_evaluation.py`, `test_evaluation_api.py`, pruebas de reporting y páginas. | Estuardo |
| Documentos | RF-DOC-001–010; RF-ARC-001–007; RF-PLA-001–007; RF-EMI-001–009; RNF-SEG-004–006; RNF-RES-003 | Validaciones, metadatos/binarios, plantillas cerradas, emisión según alcance, descargas firmadas y hash. | `test_documents_services.py`, `test_documents.py`, `test_documents_api.py`, reportes y pruebas de integridad. | Roí |
| Auditoría transversal | RF-BIT-001–007; RNF-AUD-001–003; RNF-SEG-003 | Responsable/fecha/estado, lectura sensible, rechazo, ajustes sin sobrescritura, acceso a bitácora. | `test_audit_services.py`, `test_audit.py`, `test_audit_api.py`, `test_audit_permissions.py`. | Roí/Santiago |
| Plataforma y recuperación | RNF-CAP-001–002; RNF-DIS-001; RNF-LOC-001–002; RNF-MAN-001–002; RNF-OPE-001; RNF-RES-001–003 | Capacidad/almacenamiento, fecha/idioma, catálogos, tareas exitosas/fallidas, restauración y salud. | Pruebas de capacity, localization, scheduled tasks, monitoring, backup/recovery y migraciones. | Daniel |
| Compatibilidad y privacidad | RNF-COM-001–002; RNF-LEG-001; RNF-PRI-001–005; RNF-SEG-002 | Móvil/escritorio, conectividad, TLS, cámara, minimización, retención y configuración segura. | Cámara/componentes, build budget, clasificación de datos y configuración; completar con pruebas reales. | Estuardo/Santiago/Daniel |
| Procesamiento diferido | RNF-REN-003–004 | Revisar aplicabilidad y decisión vigente; no simular worker ni declarar colas probadas. | ADR-0009 y matriz canónica; implementación diferida según ADR. | Pablo/Daniel |

### 10.2 Unitarias, API y funcionales

- Ejecutar suites existentes completas como línea base y al congelar candidato final.
- Verificar servicios y cálculos por entradas válidas, inválidas y de frontera.
- API: autenticación real según caso, CSRF, contratos de respuesta/error, paginación/filtros, persistencia y restricciones. Una prueba con `force_authenticate` no demuestra login/CSRF real.
- Frontend: carga, vacío/error, validaciones, confirmaciones, filtros, navegación, expiración de sesión y prevención de doble envío.
- Funcional manual: abrir navegador real, operar mediante UI y comprobar efecto en API/datos/auditoría con herramientas autorizadas de QA.
- Reportes/exportaciones disponibles: contenido, idioma, filtros, permisos e historia; no basta recibir HTTP 200.

### 10.3 Integración y E2E manual obligatorios

| Caso propuesto | Flujo y verificaciones | Vínculos iniciales | Pareja |
| --- | --- | --- | --- |
| CP-INT-MAT-001 | Persona → estudiante → estructura/ciclo → matrícula → consulta autorizada; comprobar vigencias y auditoría. | RF-EST, RF-CIC, RF-MAT, RF-ALC; precisar IDs/criterios en D1. | Diana/Josué |
| CP-INT-ASI-001 | Matrícula activa → credencial → escaneo → evento → estado diario → consulta de presencia; comprobar confirmación y denegaciones. | RF-CRE, RF-ASI, RF-JOR; RNF-CON-001. | Josué y Emilio |
| CP-INT-JUS-001 | Encargado vinculado → solicitud → documento → revisión autorizada → efecto en jornada; conservar evento original. | RF-JUS, RF-ALC; RNF-AUD-001. | Diana/Emilio |
| CP-INT-EVA-001 | Asignación docente → configuración → nota → resultado → reporte/boleta disponible; negar estudiante ajeno y escritura en ciclo cerrado. | RF-ALC, RF-EVC, RF-CAL, RF-RES. | Josué/Estuardo |
| CP-INT-DOC-001 | Expediente → archivo/plantilla → emisión disponible → descarga autorizada → auditoría; probar enlace expirado o ajeno. | RF-DOC, RF-ARC, RF-PLA, RF-EMI; RNF-SEG-005. | Diana/Roí |
| CP-INT-MOV-001 | Cambio de asignación, matrícula o vínculo → autorización recalculada → acceso anterior revocado; conservar historia. | RF-ALC-002, RF-ALC-003, RF-ALC-008; RF-MOV. | Santiago/Josué |
| CP-INT-REC-001 | Respaldar DB/archivos por separado → restaurar en destino QA → verificar relaciones, binarios e integridad. | RNF-RES-001–003. | Roí y Daniel |

Para cada flujo seleccionar criterios exactos y caso positivo, negativo y frontera aplicables. Si emisión, un estado o una operación no forman parte del alcance, registrar decisión y ajustar el flujo explícitamente; no omitir el paso silenciosamente.

### 10.4 Seguridad básica

| Control | Prueba requerida | Evidencia |
| --- | --- | --- |
| Autenticación/sesiones | Login inválido, bloqueo según configuración, timeout, logout y revocación; sesión anterior no opera. | Resultado UI/API y auditoría sin contraseñas ni cookies. |
| Permisos y alcance | Acceso anónimo, sin permiso, sin alcance, ámbito ajeno, vínculo/grant expirado y rol múltiple. Cambiar ID en URL/body/listado/exportación. | Rechazo conforme al contrato y ausencia de modificación/fuga. |
| CSRF | Escritura con sesión sin token o token inválido y escritura válida con token. | Respuesta contractual; no guardar token sensible. |
| Cookies/TLS | En entorno QA con perfil de entrega, verificar HttpOnly/Secure/SameSite de sesión y HTTPS efectivo. | Atributos redactados y configuración no sensible. |
| Datos sensibles | Acceso a salud, documentos/observaciones según política; listados, exportaciones, logs, caché y errores no revelan información ajena. | Campos minimizados y evento de lectura cuando corresponda. |
| Archivos y descargas | Archivo inválido, acceso por ruta, firma alterada, expiración y portador ajeno; metadatos/binarios separados. | Rechazo y evento auditado cuando corresponda. |
| Entradas y plantillas | Cadenas de prueba para inyección/XSS, errores sin traceback, catálogo de marcadores cerrado sin evaluación dinámica. | Texto tratado como datos y validación/rechazo previsto. |
| Auditoría | Rechazo de escaneo, cambios sensibles y lectura; intento de alterar/borrar historia. | Registro correspondiente y protección contra modificación. |
| Dependencias/código | Bandit, pip-audit, ESLint y controles CI vigentes; analizar allowlist y dependencias frontend. | Reporte, alcance y análisis de cada hallazgo/excepción. |
| Interfaces públicas | Rate limiting y revelación mínima solo si existen en alcance; ausencia documentada si están diferidas. | Umbral/configuración y respuesta observados. |

Pruebas limitadas al entorno QA propio. Los payloads son sintéticos y controlados. Este alcance básico no equivale a auditoría de seguridad exhaustiva.

La allowlist de `pip-audit` se revisa durante ejecución: justificar paquete/versión, hallazgo, exposición, mitigación, responsable y fecha de revisión. Un exit code 0 con exclusiones no significa «sin vulnerabilidades». Daniel puede ejecutar `npm audit --json` en frontend y registrar exit code/hallazgos; no aplicar `audit fix` automático ni actualizar dependencias sin revisión y regresión.

### 10.5 Usabilidad, accesibilidad práctica y compatibilidad

Estuardo prepara sesiones por tareas; observar sin guiar durante primer intento. Incluir al menos un representante disponible de cada perfil operativo incluido (administración/secretaría, docente, operador, dirección y encargado cuando tengan flujos en entrega). Un usuario puede representar varias responsabilidades si se documenta la limitación; los ocho participantes técnicos no sustituyen validación institucional.

Tareas: iniciar sesión, ubicar estudiante, crear/consultar registro autorizado, detectar error y corregirlo, escanear, consultar asistencia, registrar/consultar nota, descargar documento y terminar sesión, según perfil.

Registrar por tarea: éxito sin ayuda, éxito con ayuda o fallo; tiempo; número de errores; pasos confusos; mensaje no entendido; valoración 1–5 y comentario. No inventar una meta temporal institucional: acordar límites de tareas en D1 cuando sean necesarios. Objetivo de aceptación: cada tarea crítica debe poder completarse por su perfil sin bloqueo; problemas menores se clasifican y acuerdan.

Comprobar teclado/foco, etiquetas de campos, mensajes comprensibles en español, contraste y zoom al 200 % en pantallas principales. Registrar limitaciones; estas comprobaciones no certifican conformidad completa con un estándar de accesibilidad.

Matriz mínima: escritorio Chrome/Edge disponible, Firefox y Safari vigentes; Android Chrome vigente y versión anterior conforme al contrato. Perfil móvil de referencia: 2 GB RAM, viewport 360 × 640. Registrar versiones efectivamente probadas; disponibilidad de Safari/Android es dependencia que debe confirmarse D1. Emulación complementa, pero no sustituye cámara/dispositivo real.

Cámara: contexto seguro, permiso concedido/denegado, ausencia de dispositivo, elección trasera cuando disponible, reintento y cierre/unmount que detiene tracks. El permiso debe verificarse antes del primer escaneo según RNF-USA-001. Probar red interrumpida y recuperación del lote sin duplicados; no asumir soporte offline general.

### 10.6 Rendimiento y capacidad cuando corresponda

En esta versión hay RNF de asistencia, compatibilidad y capacidad: **esas mediciones sí corresponden**. Otras operaciones se seleccionan por riesgo, volumen y alcance; toda decisión de no aplicabilidad lleva justificación.

| Requisito | Meta o referencia vigente | Cómo verificar |
| --- | --- | --- |
| RNF-REN-001 | p95 ≤ 2 s desde lectura QR hasta confirmación visual, infraestructura 1 vCPU / 2 GB. | Medición E2E con navegador/dispositivo real, TLS, red declarada y carga representativa. Separar latencia API y total visible. |
| RNF-REN-002 | Pico = operadores concurrentes × tasa de escaneos por operador. | Confirmar PD-010; medir normal y pico, latencia, fallos, eventos perdidos/duplicados y recursos. Referencia de 3 operadores no es dato institucional confirmado. |
| RNF-CAP-001 | Matrícula real sobre perfil objetivo; referencia provisional ~500 estudiantes. | Confirmar PD-001; generar población e historial sintéticos equivalentes; registrar CPU, RAM, conexiones, duración y límites efectivos. |
| RNF-COM-002 | Inicial ≤ 230.000 bytes gzip; incremento por ruta lazy ≤ 20.000; inicial + una ruta ≤ 250.000; raster ≤ 25.000 bytes sin comprimir. | Build y verificador existentes; comprobar transferencia runtime por separado, ya que API/medios no están incluidos en límites estáticos. |
| RNF-CAP-002 | Proyección de 2 GB/ciclo y advertencia configurable. | Comprobar cálculo, umbral inferior/igual/superior y visibilidad autorizada de advertencia. |
| RNF-DIS-001 | Disponibilidad durante jornada lectiva, sin compromiso 24/7. | Smoke/health y seguimiento de la ventana de prueba; registrar caídas y recuperación. Una semana de pruebas no prueba disponibilidad futura. |

Protocolo propuesto: 2 minutos de calentamiento excluidos de percentiles; al menos 100 confirmaciones medidas por escenario en tres rondas independientes, con volumen normal y pico. Confirmar D1 tasa, duración y recursos; si la muestra no representa operación, declarar limitación. Usar p95 por rango más cercano, posición `ceil(0,95 × N)` en serie ordenada; conservar N y datos de duración sin información personal.

Registrar p50/p95/p99, máximo, throughput, errores por tipo, CPU/RAM y duplicados/perdidos. Los fallos no se excluyen silenciosamente: informar tasa de éxito, timeouts y latencia de respuestas exitosas por separado. No atribuir al backend retrasos de cámara/red sin medición diferenciada.

`backend/tests/integration/test_attendance_performance.py` aporta evidencia direccional: una prueba usa 20 solicitudes y otra usa 3 operadores con 4 ítems por operador, sobre CI/desarrollo. No mide flujo visual real ni certifica perfil objetivo. Reutilizarla como regresión; completar la medición objetivo y no confundir referencias con resultados certificados.

Si no está disponible el perfil objetivo o la tasa real, documentar referencia, limitación y decisión institucional. Un criterio obligatorio sin medición válida queda sin verificar y bloquea aprobación del alcance que depende de él.

### 10.7 Recuperación, migraciones y operación

- Restaurar DB y archivos independientemente en destinos desechables de QA; nunca sobre producción.
- Confirmar PostgreSQL y clientes `pg_dump`/`pg_restore` de la misma versión mayor.
- Verificar checksum y rechazo de artefactos alterados antes de escribir.
- Comprobar recuperación conjunta: relaciones, historial/auditoría, metadatos, binarios y reporte de integridad documental.
- Registrar RPO por cada pila a partir de fecha del manifiesto; referencia 24 h. Registrar RTO del simulacro completo; referencia 4 h. Validar o aceptar explícitamente estas referencias institucionalmente, según PD-002.
- Repetir con volumen sintético representativo. El tiempo histórico de una base pequeña no sirve como resultado de esta entrega.
- Crear esquema final desde PostgreSQL vacío; correr migraciones y seeds idempotentes donde aplique; probar actualización desde estado anterior representativo y conservación de historia.
- Probar comandos programados en éxito/fallo, resumen parcial, código de salida, fila TaskRun y log; consulta solo autorizada.
- Revisar skips de recuperación: cliente PostgreSQL ausente no permite declarar restauración aprobada.

## 11. Ejecución automatizada y captura de evidencia

Los comandos se basan en archivos reales del repositorio. Daniel registra sus versiones efectivas y ejecuta sobre SHA seleccionado. Este plan no exige ejecutar las suites al redactarlo.

### 11.1 Validación integrada disponible

Desde raíz:

```bash
make ci-local
```

Este target construye servicios, ejecuta backend en PostgreSQL de pruebas, lint frontend, cobertura frontend, build, Ruff/formato backend, migraciones, Bandit y pip-audit con exclusiones vigentes. Al concluir usa limpieza de volúmenes del proyecto de pruebas. **Ejecutarlo únicamente contra proyecto de pruebas aislado**, y conservar evidencia antes de limpieza.

No es idéntico a CI: complementar comprobación de formato frontend y `manage.py check`, además de revisar todos los jobs requeridos en GitHub. Si falla una etapa, investigar y ejecutar controles restantes de forma individual; no dejar sus resultados implícitos.

### 11.2 Corrida backend con resultados persistentes

Ejemplo de ronda D1; cambiar carpeta y nombres para cada corrida. El bind mount conserva archivos que normalmente serían eliminados con el contenedor:

```bash
mkdir -p docs/quality/fase-7/evidence/RUN-D1-01/backend

docker compose -p siga_inebi_test -f compose.yml -f compose.test.yml build backend-test
docker compose -p siga_inebi_test -f compose.yml -f compose.test.yml up -d db-test

docker compose -p siga_inebi_test -f compose.yml -f compose.test.yml run --rm \
  -v "$PWD/docs/quality/fase-7/evidence/RUN-D1-01/backend:/evidence" \
  backend-test sh -lc 'python manage.py migrate --noinput && pytest --junitxml=/evidence/junit.xml --cov-report=term-missing --cov-report=xml:/evidence/coverage.xml --cov-report=html:/evidence/htmlcov' \
  > docs/quality/fase-7/evidence/RUN-D1-01/backend/execution.log 2>&1
backend_exit=$?
printf '%s\n' "$backend_exit" > docs/quality/fase-7/evidence/RUN-D1-01/backend/exit-code.txt
```

El script guarda el código de salida de la ejecución inmediatamente después del comando. Si se usa CI, subir reportes aun cuando fallen pruebas. Para scripts que deban fallar globalmente, propagar el código guardado; escribir un log no transforma una falla en éxito.

Mantener el mismo proyecto `siga_inebi_test` en todas las llamadas Compose de la ronda. Registrar errores de construcción/preparación por separado; si la preparación falla, la corrida queda bloqueada.

### 11.3 Subconjuntos para diagnóstico y regresión rápida

Dentro del entorno backend preparado:

```bash
pytest -m unit --no-cov
pytest -m 'integration or api or permissions or migration' --no-cov
pytest tests/permissions --no-cov
pytest tests/integration/test_attendance_performance.py --no-cov
pytest tests/integration/test_backup_and_recovery.py --no-cov
pytest --collect-only -q --no-cov
```

`--no-cov` en subconjuntos evita interpretar el umbral global sobre una muestra parcial; **no sustituye** corrida completa con cobertura. El marcador `security` existe, pero no se asume que cubra todos los controles de seguridad; revisar colección y complementar casos API/permisos y manuales.

Targets locales existentes: `make test-backend`, `make test-backend-unit`, `make test-backend-integration`, `make test-frontend`, `make coverage`, `make security`, `make migrations-check`. Los targets backend locales requieren `.venv` y PostgreSQL configurado; los de seguridad incluyen exclusiones documentadas. No usar SQLite para evidencia final.

### 11.4 Frontend y controles complementarios

En `frontend/`, con dependencias instaladas mediante `npm ci` y SHA seleccionado:

```bash
npm run lint
npm run format:check
npm run test:coverage -- --reporter=default --reporter=junit --outputFile=../docs/quality/fase-7/evidence/RUN-D1-01/frontend-junit.xml
npm run build
npm run test:budget
```

Crear previamente carpeta de evidencia. Conservar logs y códigos de salida de cada comando; copiar reporte de cobertura desde `frontend/coverage/` a almacenamiento de evidencia o publicar como artefacto CI. La configuración vigente exige 60 % en líneas, funciones y statements, y 50 % en branches; registrar valores concretos y no solo salida «passed».

También comprobar `python manage.py check` en backend QA y `makemigrations --check --dry-run` en configuración aplicable. Revisar jobs CI, CodeQL/dependencias y validación de PR que sean requeridos para la rama. Una corrida local no certifica checks remotos que no se ejecutaron.

Los XML/logs nuevos deben revisarse antes de incorporarse a Git. Algunas rutas de cobertura están ignoradas por `.gitignore`; preferir artefactos CI o almacenamiento controlado con índice estable. No forzar incorporación de archivos sensibles ni cambiar controles de CI para hacer pasar evidencia.

## 12. Registro de resultados y evidencias

### 12.1 Estados de ejecución

| Estado | Significado |
| --- | --- |
| No ejecutado | Caso definido sin corrida válida todavía. |
| En ejecución | Corrida iniciada y sin conclusión. |
| Aprobado | Resultado esperado demostrado y evidencia revisable. |
| Fallido | Una o más comprobaciones no coinciden; incidencia vinculada. |
| Bloqueado | No puede obtenerse resultado válido por entorno, dependencia o decisión pendiente. |
| No aplica | Exclusión justificada y aprobada para candidato concreto. |

`skip`, `xfail`, `xpass`, error de colección y prueba cancelada se registran explícitamente. Un fallo esperado de pytest no significa criterio institucional aprobado. Una negativa correctamente rechazada sí puede ser un caso aprobado cuando ese era el resultado esperado.

### 12.2 Ficha de ejecución

```text
ID ejecución / ID corrida / ID caso o nodo automatizado:
Fecha y hora / zona / duración:
Ejecutor y revisor:
Versión del plan/caso / commit SHA / candidato:
Entorno, dispositivo/navegador y dataset:
Comando o pasos ejecutados:
Resultado esperado:
Resultado observado, por comprobación:
Estado / código de salida / métricas si aplica:
Evidencias y ubicación:
Incidencias relacionadas:
Reejecución de / sustituida por:
Revisión: nombre, fecha y observación:
```

Una nueva corrida genera nuevo registro; conservar fallo original y posterior corrección. No sobrescribir capturas/logs para aparentar una primera ejecución exitosa.

### 12.3 Evidencia mínima por tipo

| Tipo | Evidencia requerida |
| --- | --- |
| Automatizada | Comando, SHA, entorno, log, exit code, JUnit/reporte del runner y cobertura cuando aplique. |
| Funcional/E2E | Pasos, datos sintéticos, capturas/video del resultado y comprobación de persistencia/auditoría relevante. |
| Seguridad | Vector de prueba, permisos/alcance, respuesta redactada y prueba de ausencia de acceso/modificación indebida. |
| Usabilidad/UAT | Perfil, tarea, resultado, ayudas/errores, observaciones y aprobación del participante. |
| Rendimiento | Recursos efectivos, datos/carga, muestras de duración, cálculo de percentiles, errores y recursos. |
| Recuperación | Manifiestos sin secretos, integridad, tiempos, destino QA y comprobación posterior; artefactos de respaldo fuera de Git. |
| Corrección/regresión | INC, prueba que reproduce, PR/SHA correctivo, revisión, reejecución y regresión final. |
| Manuales | Versión, revisor independiente, pasos comprobados, resultado y correcciones. |

### 12.4 Gestión de evidencias

Daniel mantiene índice; cada ejecutor entrega evidencia al cierre del día. Nombre recomendado: `EV-EJ-D2-003-01.png` o `RUN-D4-01-backend-junit.xml`. El índice guarda ID, caso/corrida, SHA, tipo, autor, fecha, ruta/enlace, acceso y checksum para paquetes/artefactos entregados.

Guardar Markdown/CSV sanitizados en Git. Publicar reportes grandes, videos y artefactos en ubicación acordada con acceso de revisores e institución; registrar vencimiento de enlaces y exportar copia para entrega si la retención de CI no cubre plazo acordado. Definir responsable y plazo de conservación D1. Nunca usar rutas locales de otra máquina como única evidencia entregable.

Capturas y logs no incluyen contraseñas, cookies/tokens, claves, QR con información personal ni expedientes reales. Los respaldos/dumps quedan fuera de Git incluso cuando se pruebe restauración; el reporte documenta resultado e integridad, no adjunta bases.

## 13. Incidencias, correcciones y regresión

### 13.1 Severidad y prioridad

| Severidad | Ejemplos/impacto | Atención en esta semana | Efecto sobre entrega |
| --- | --- | --- | --- |
| S1 — Crítica | Acceso indebido sensible, pérdida/corrupción de historia, sistema inutilizable, duplicación grave sin control. | Notificación inmediata a Pablo y responsable; contener en QA y atender primero. | Bloquea implementación. |
| S2 — Alta | Flujo esencial incumplido, cálculo/estado incorrecto, recuperación fallida, RNF obligatorio incumplido. | Triage en misma jornada, diagnóstico y corrección prioritaria con revisor. | Bloquea implementación. |
| S3 — Media | Problema acotado con alternativa válida que no incumple criterio obligatorio. | Clasificar y programar; corregir si capacidad permite o solicitar aceptación explícita. | Condicionada a impacto y decisión; si afecta criterio obligatorio, bloquea. |
| S4 — Baja | Texto, detalle visual o documentación menor sin impedir operación ni comprensión crítica. | Agrupar y revisar antes de cierre. | Puede quedar como observación con responsable/fecha. |

Prioridad independiente: P0 inmediata, P1 antes de UAT/final, P2 próxima ventana acordada. Una severidad no se reduce por cercanía al plazo. Discrepancias de severidad las resuelve Pablo con responsable del dominio y contraparte si afectan aceptación.

### 13.2 Ficha de incidencia

```text
ID / título / fecha / reportado por:
Tipo: funcional | integración | seguridad | usabilidad | rendimiento | datos | documentación | entorno
Caso y requerimientos afectados:
SHA/candidato/entorno/rol/alcance/dataset:
Pasos mínimos para reproducir:
Resultado esperado / observado:
Evidencia:
Severidad / prioridad / impacto / alternativa si existe:
Responsable de corrección / revisor / fecha objetivo:
Estado / bloqueos / causa raíz:
PR y SHA correctivo:
Prueba de regresión añadida o ampliada:
Ejecución de verificación y regresión:
Manuales/trazabilidad actualizados:
Decisión de cierre o diferimiento, aprobador y fecha:
```

Registro maestro recomendado: `incidencias.csv`; ficha detallada en issue existente/nuevo si el equipo usa GitHub. El plan no crea issues automáticamente. Relacionar duplicados con incidencia principal y conservar reportes originales.

### 13.3 Flujo de atención

`Nueva → Clasificada → Asignada → En corrección → En revisión → Lista para verificar → Verificada → Cerrada`.

Desvíos: `Bloqueada`, `Reabierta`, `Duplicada` o `Diferida con aprobación`. «No reproducible» requiere evidencia del intento y seguimiento; no equivale a «corregida».

1. Reproducir sobre candidato exacto y aislar causa.
2. Añadir/ampliar prueba que reproduzca fallo antes o junto con cambio, conforme a AGENTS/TDD.
3. Corregir en servicio/capa correspondiente; evitar trasladar reglas de negocio a vista, serializer o componente.
4. Abrir/revisar PR pequeño, documentar contrato si cambia y ejecutar controles.
5. Integrar cambio, identificar nuevo SHA y actualizar candidato.
6. Revisor cruzado reejecuta caso original y prueba de regresión; comprueba datos/auditoría.
7. Ejecutar regresión de dependencias y suite global antes de cierre final.
8. Actualizar registro, manuales y trazabilidad; cerrar con referencias verificables.

### 13.4 Selección de regresión

- Cambio identidad/alcance: sesiones, permisos, listados y operaciones sensibles de todos los dominios afectados.
- Cambio ciclo/matrícula/vigencia: asignaciones, asistencia, evaluación, documentos e historia.
- Cambio asistencia: QR, reintentos, lotes, jornada, justificación, auditoría y rendimiento.
- Cambio evaluación: configuración, cálculos, resultados, reportes y permisos.
- Cambio documentos: subida, plantillas/emisión aplicable, descarga, firma, hash, auditoría y recuperación.
- Cambio migraciones/settings/dependencias: suites completas, schema/check, build y smoke integrado.
- Cambio UI: Vitest afectado, flujo real, navegadores/dispositivos involucrados y manual visual.

Durante corrección usar subconjuntos; al cerrar candidato final ejecutar suites completas y flujos críticos manuales. La evidencia final incluye fixes integrados, no solo pruebas previas al cambio.

## 14. Matriz final de trazabilidad

Mantener [matriz canónica](docs/requirements/traceability-matrix.md) como fuente de relaciones de implementación. Elaborar `docs/quality/fase-7/matriz-final.csv` como **instantánea de validación** del candidato; no crear estados de implementación contradictorios.

Columnas mínimas:

```text
requirement_id, tipo, prioridad, criterio_id_o_referencia, alcance,
issue, diseño_adr, código, prueba_automatizada, caso_manual,
pr, estado_implementación, candidato_sha, ejecución,
resultado_validación, evidencia, incidencia, responsable, revisor,
exclusión_decisión, observaciones
```

Una fila puede representar un criterio/caso; varios registros por requerimiento son válidos si la relación es explícita. El resumen por ID se calcula sin doble conteo. Un requerimiento solo está validado cuando todos sus criterios aplicables están aprobados.

Controles D1 y D5:

- Comparar universo de 230 IDs con matriz: detectar ausentes, IDs desconocidos, duplicados no explicados y filas mal formadas.
- Reconciliar duplicados de la matriz existente: distinguir vínculos complementarios de información contradictoria; conservar historia y referencias.
- Resolver notas iniciales/estados históricos que no correspondan a código y pruebas actuales mediante evidencia, sin declarar «Implemented» por nombre de archivo.
- Validar rutas con mayúsculas/minúsculas exactas y nodos de prueba vigentes; por ejemplo, existen referencias históricas a `app.test.jsx` mientras archivo actual es `App.test.jsx`.
- Separar **estado de implementación** de **resultado de validación**; «Implemented» no significa «Aceptado».
- Enlazar todo criterio incluido con una ejecución del candidato final; si se reutiliza evidencia previa, justificar ausencia de impacto y completar regresión final requerida.
- Documentar diferimientos/exclusiones aprobados sin contarlos como aprobados o probados.
- Registrar ajustes de código/pruebas/PR en matriz canónica cuando se implemente/corrija un RF/RNF; guardar instantánea final y su SHA.

## 15. Documentación de resultados y expediente de entrega

### 15.1 Estructura propuesta

Estos documentos se producirán durante ejecución; redactar el plan no crea resultados ni archivos vacíos de supuesta evidencia.

```text
tests_plan.md
docs/quality/fase-7/
  README.md
  alcance-y-decisiones.md
  entorno-y-datos.md
  catalogo-casos.csv
  ejecuciones.csv
  incidencias.csv
  correcciones-y-regresion.md
  informe-seguridad.md
  informe-usabilidad.md
  informe-rendimiento.md
  informe-recuperacion.md
  informe-aceptacion-usuarios.md
  matriz-final.csv
  indice-evidencias.csv
  seguimiento-manuales.md
  reporte-final-pruebas.md
  acta-aceptacion.md
  manifiesto-version.md
  evidence/
    RUN-D1-01/
    RUN-D4-01/
    RUN-D5-01/
```

`README.md` será el índice único del expediente. Los CSV deben ser UTF-8 con cabecera estable y referencias a fichas detalladas si el campo resulta extenso. Evidencia binaria/grande podrá estar externa; el índice conserva enlaces revisables y checksum cuando corresponda.

### 15.2 Qué documentar, quién y cuándo

| Documento/registro | Contenido obligatorio | Responsable / revisor | Momento |
| --- | --- | --- | --- |
| Plan actualizado | Alcance, cronograma, tipos, roles, riesgos, umbrales y cambios de plan. | Pablo / Daniel | D1 y cada cambio relevante. |
| Alcance/decisiones | Clasificación de 230 IDs, aprobaciones, PD/ADR, exclusiones y limitaciones. | Pablo / responsables | D1; revisar D5. |
| Entorno/datos | Ficha reproducible, recursos, configuración no sensible, versiones y fixtures. | Daniel / Josué | D1 y cambio de entorno. |
| Catálogo de casos | Fichas y vínculos RF/RNF/criterios, reutilización y brechas. | Santiago, Diana, Josué, Emilio, Estuardo y Roí / revisores cruzados | D1–D2; mantener hasta cierre. |
| Ejecuciones | Resultado real por caso/nodo, SHA, entorno, ejecutor, evidencia e incidencia. | Todos / revisor correspondiente | En cada corrida, cierre diario. |
| Incidencias | Clasificación, reproducción, estado, responsable y decisiones. | Reportante + Pablo / revisor | Desde D1, actualizar diariamente. |
| Correcciones/regresión | Causa, INC, prueba reproducible, PR/SHA, retest y alcance de regresión. | Autor + revisor / Pablo | Cada fix; consolidar D5. |
| Seguridad | Controles, vectores, hallazgos, dependencias, excepciones y conclusión por RNF. | Santiago/Daniel / Roí | D2–D4. |
| Usabilidad | Participantes/perfiles, tareas, tiempos, ayudas, errores y recomendaciones. | Estuardo / Emilio | D3–D4. |
| Rendimiento | Aplicabilidad, recursos, carga, muestras, percentiles, errores y contraste con metas. | Daniel/Emilio / Pablo | D3; repetir si fix afecta rendimiento. |
| Recuperación | Destino, volumen, pila, checksum, RPO/RTO, integridad posterior y limitaciones. | Daniel/Roí / Josué | D3. |
| UAT | Agenda, escenarios, perfiles, resultados, observaciones y validación de cambios. | Estuardo/Pablo / usuarios | D4–D5. |
| Matriz final | Cobertura real por criterio y candidato, incidencias y decisiones. | Pablo + dominios / Daniel | Base D1; cierre D5. |
| Manuales | Estado/versiones, revisiones, evidencia de procedimiento y videos. | Dueños de manual / revisor cruzado | Todos los días; cierre D5. |
| Reporte final | Resumen de calidad, cobertura, métricas, limitaciones y recomendación apto/no apto. | Pablo / Santiago, Diana, Josué, Emilio, Estuardo, Roí y Daniel | D5. |
| Acta/reporte de aceptación | Decisión institucional, versión exacta, observaciones y firmas. | Pablo / autoridad designada | D5 después de revisar evidencia. |
| Manifiesto de versión | SHA, identificador, artefactos/checksums, migraciones, configuración, manuales y release notes. | Daniel / Pablo | RC1, RC2 y final. |

Si un tipo no aplica, entregar una sección o informe breve que explique motivo y aprobación; no dejarlo vacío ni confundir ausencia de medición con conformidad.

### 15.3 Formato de informe por tipo

```text
Título / tipo / responsable / revisor / fecha:
Objetivo y requerimientos evaluados:
Candidato SHA / entorno / dataset / herramientas:
Casos y escenarios incluidos y excluidos:
Procedimiento/comandos reproducibles:
Tabla: caso, esperado, observado, resultado, métrica, evidencia, INC
Totales: aprobados, fallidos, bloqueados, no ejecutados, no aplica
Hallazgos y severidad:
Correcciones y reejecuciones:
Limitaciones y decisiones pendientes:
Conclusión por criterio: conforme | incumple | sin verificar | no aplica aprobado
```

### 15.4 Métricas y reporte final

Mantener tablero diario por dominio y tipo. Separar casos manuales, nodos automatizados y criterios para evitar sumar unidades distintas.

- **Ejecución:** `(aprobados + fallidos) / casos aplicables planificados × 100`; bloqueados/no ejecutados quedan visibles y fuera del numerador.
- **Éxito de ejecutados:** `aprobados / (aprobados + fallidos) × 100`; no usarlo solo, porque puede ocultar casos pendientes.
- **Cobertura de diseño:** criterios incluidos con casos / criterios incluidos × 100.
- **Cobertura validada:** criterios incluidos totalmente aprobados con evidencia / criterios incluidos × 100.
- **Cobertura de código:** valores backend/frontend del reporte completo y su configuración.
- **Incidencias:** abiertas/cerradas/reabiertas por severidad, antigüedad y casos afectados.
- **Regresión:** fixes verificados, casos impactados aprobados y corridas globales por SHA.
- **Manuales:** productos completos/revisados/validados y brechas pendientes.
- **UAT:** tareas críticas aprobadas/pendientes por perfil y candidato.

Para denominador cero registrar «No aplica», no 100 %. En reportes agregados considerar última ejecución válida de cada caso sobre candidato, conservando historial de intentos; no inflar éxito sumando reintentos aprobados.

El reporte final contiene resumen ejecutivo, alcance, versión, entorno, resultados por tipo/dominio, cobertura por criterio, defectos y fixes, regresión, UAT, estado de manuales, riesgos residuales y recomendación. Las tablas deben enlazar pruebas, evidencias y decisiones, sin depender de la memoria del equipo.

## 16. Manuales en paralelo

Las instrucciones actuales son guías de elaboración, **no prueba de que los manuales finales existan**. Registrar ubicación real y versión de cada producto en `seguimiento-manuales.md`.

| Producto | Responsable | Fuente | Validación requerida |
| --- | --- | --- | --- |
| Manual de usuario en video | Emilio/Estuardo, segmentos Santiago, Diana, Josué, Emilio, Estuardo y Roí | [01](docs/manuals/01-user-video-manual-instructions.md) | Operaciones disponibles por módulo/rol, al menos rechazo relevante en módulos sensibles, índice con título/módulo/rol/duración; pantalla coincide con versión final. |
| Manual técnico | Daniel, aportes todos | [02](docs/manuals/02-technical-manual-instructions.md) | Arquitectura/ADR, dominios, seguridad, datos, operación y comandos corresponden a código real. |
| Instalación y configuración | Daniel/Josué | [03](docs/manuals/03-installation-and-configuration-instructions.md) | Revisor levanta copia limpia siguiendo únicamente manual, sin secretos impresos. |
| Administración | Santiago | [04](docs/manuals/04-administration-manual-instructions.md) | Pasos con permisos, precondiciones, resultado y auditoría; no promete operaciones ausentes. |
| Diccionario de datos final | Diana, aportes dominios | [05](docs/manuals/05-final-data-dictionary-instructions.md) | Cada tabla/columna efectiva, llaves e invariantes; coherencia con DER/migraciones y clasificación de datos. |
| Scripts finales de base de datos | Josué | [06](docs/manuals/06-final-database-scripts-instructions.md) | Migraciones/scripts identificados; PostgreSQL vacío alcanza esquema final; idempotencia donde aplique; no dumps reales. |
| API e integraciones | Roí | [07](docs/manuals/07-api-integrations-documentation-instructions.md) | Endpoints publicados, sesión/CSRF, permisos, errores y ejemplos sintéticos comprobados contra contrato versionado. |
| Mantenimiento y soporte | Pablo/Daniel | [08](docs/manuals/08-maintenance-and-support-plan-instructions.md) | Canal, responsables, clasificación, escalamiento, corrección/regresión y evidencia; sin promesas operativas ficticias. |
| Respaldo y recuperación | Daniel/Roí | [09](docs/manuals/09-final-backup-and-recovery-plan-instructions.md) | Activos/pilas, frecuencia, retención, metas, responsables, restauración y un simulacro documentado. |

Hitos diarios: D1 índices; D2 procedimientos y ejemplos; D3 borrador completo; D4 revisión independiente y uso durante UAT; D5 versión final.

Ficha de validación de manual: producto, versión/SHA, autor, revisor, procedimiento o segmento, rol, precondición, pasos comprobados, resultado, evidencia, incidencia documental y corrección. Cualquier fix de comportamiento invalida las secciones afectadas hasta revisarlas. Videos estables se graban antes; segmentos alterados se regraban tras congelación.

No redactar políticas de retención, campos de credencial o reglas institucionales pendientes como decisiones aprobadas. Marcar limitación y obtener decisión explícita si afecta operación o aceptación.

## 17. Pruebas de aceptación con usuarios

### 17.1 Preparación D1–D3

Pablo solicita a la institución una autoridad de aceptación y representantes de perfiles incluidos; Estuardo prepara agenda y tareas. Confirmar disponibilidad D1 para no descubrir ausencia en D4. Registrar participantes mediante identificadores/perfiles; conservar firmas o datos de contacto necesarios en acceso controlado.

Cada escenario UAT contiene tarea realista, RF/RNF y criterio, rol/alcance, datos sintéticos, estado inicial, pasos esperados, resultado y evidencia. Usuarios revisan criterios antes de comenzar; no cambiar condiciones al observar un fallo.

### 17.2 Sesiones D4–D5

1. Presentar objetivo, candidato exacto, alcance y limitaciones.
2. Usuario ejecuta tareas de su perfil con cuenta QA y manual disponible.
3. Facilitador registra resultado, dudas, ayudas y observaciones sin sustituir acción del usuario.
4. Verificar también rechazo autorizado relevante: estudiante ajeno, acción no permitida o dato inválido.
5. Registrar incidencia y severidad; una solicitud nueva se separa de un incumplimiento del criterio.
6. Verificar fixes sobre nuevo candidato; solicitar confirmación del usuario para los escenarios afectados.
7. Consolidar decisión por escenario y perfil; autoridad revisa reporte final y emite aceptación/rechazo.

No marcar UAT aprobado por demostración del desarrollador, asistencia a reunión o ausencia de comentarios. Si usuarios no están disponibles, registrar UAT pendiente y no simular aceptación.

### 17.3 Registro UAT

```text
Sesión / fecha / participante o código / perfil:
Facilitador / candidato SHA / entorno:
Escenario / caso / RF-RNF / criterio:
Resultado esperado / observado:
Resultado: aprobado | observado | rechazado | bloqueado
Ayuda requerida / tiempo / comentarios:
Evidencia / incidencias:
Corrección y nueva validación:
Conformidad del usuario y fecha:
```

## 18. Acta o reporte de aceptación para implementación

Plantilla para completar D5; las opciones permanecen pendientes hasta revisión real:

```text
Proyecto: SIGA-INEBI
Fecha/lugar/modalidad:
Autoridad institucional y representantes/perfiles:
Responsable QA y equipo:
Versión candidata/final y commit SHA:
Artefactos y manifiesto:
Alcance y exclusiones aprobadas:
Documentos revisados: plan, reporte, matriz, evidencias, UAT y manuales
Resumen de casos/criterios y resultados:
Incidencias abiertas por severidad e impacto:
Correcciones y regresión verificadas:
Metas de calidad y resultados, incluidas limitaciones:
Decisiones pendientes y riesgos residuales:
Decisión: ACEPTADO | ACEPTADO CON OBSERVACIONES MENORES | NO ACEPTADO
Justificación:
Observaciones autorizadas: INC, impacto, responsable, fecha y seguimiento
Condiciones operativas antes de implementación, si existen:
Referencia a procedimiento de instalación y recuperación:
Firmas o constancia verificable de aprobación institucional y revisión técnica:
```

La recomendación QA y la decisión institucional son campos separados. Un reporte técnico sin aprobación de autoridad no se presenta como acta firmada. Si se entrega reporte en lugar de acta, incluir estado «Aceptación institucional pendiente» cuando corresponda.

No se realiza despliegue por redactar este plan. La aceptación identifica la versión autorizada; cualquier cambio posterior requiere evaluar impacto y actualizar validación/decisión antes de implementar.

## 19. Versión del sistema y paquete final

`frontend/package.json` declara `0.1.0` al preparar este documento. Esa versión de paquete no identifica por sí sola una entrega institucional ni garantiza equivalencia del backend. Daniel y Pablo acuerdan identificador de release en D1; usar candidatos `rc1`, `rc2` y final asociados a SHA, sin inventar tags existentes.

El manifiesto de versión incluye:

- Identificador de release y SHA exacto; rama/tag únicamente si existe y fue verificado.
- Fecha, autor y estado del repositorio; explicar cualquier modificación fuera del commit. Preferir candidato sin cambios sin registrar.
- Versiones backend/frontend, dependencias lock/requirements e imágenes efectivas.
- Artefactos entregables y checksums; build frontend y forma reproducible de obtener backend.
- Migraciones incluidas y requisitos de actualización; configuración necesaria descrita sin secretos.
- Funciones incluidas, RF/RNF vinculados, exclusiones y limitaciones conocidas.
- Notas técnicas y funcionales con incidencias/PRs; cambios de contrato documentados si los hubo.
- IDs de corridas finales, CI y reporte de calidad; UAT/acta de esa misma versión.
- Índice y versiones de manuales, instalación, soporte y recuperación.
- Responsable de entrega y ubicación/acceso del paquete.

No afirmar que existe pipeline formal de despliegue si sigue pendiente en `release-process.md`. La entrega debe poder reconstruirse y revisarse sin depender de cambios locales no identificados.

## 20. Riesgos y decisiones pendientes

| Riesgo/decisión | Impacto | Acción y responsable | Límite de resolución |
| --- | --- | --- | --- |
| PD-001: matrícula real no confirmada | Carga de referencia puede subestimar volumen. | Daniel solicita cifra agregada; Pablo registra acuerdo, sin datos personales. | D1–D2, antes de medición final. |
| PD-010: operadores/tasa pico no medidos | No hay carga de aceptación institucional validada. | Emilio y Daniel solicitan cantidad y tasa; conservar referencia de 3 operadores como provisional. | D2. |
| PD-002: RPO/RTO de referencia | Recuperación probada no equivale a metas institucionales confirmadas. | Pablo solicita confirmación; Daniel mide por pila y simulacro. | D3, antes de aceptar. |
| PD-003/005/006 y demás reglas materiales aplicables | Retención, observaciones, datos visibles o estados pueden carecer de criterio firme. | Pablo + dueño de dominio solicitan decisión y registran casos bloqueados; revisar también PD-004/007/008 según alcance. | D1–D2. |
| ADR-0009 y RNF-REN-003/004 | Worker/colas diferidos; plan anterior los contemplaba. | Pablo concilia ADR vigente y alcance; exige decisión explícita sobre diferimiento en entrega. No incorporar worker dentro de QA. | D1. |
| Matriz/catálogo desalineados | Falsa cobertura o estados incompatibles. | Pablo y responsables de dominio comparan IDs, rutas, estados y criterios con pruebas/código. | Base D1, cierre D5. |
| PD-011: guardia CI de rutas | Puede rechazar archivos legítimos de código/documentación. | Daniel verifica comportamiento actual; registrar bloqueo y tramitar cambio separado si corresponde. No eludir control. | D1. |
| Dispositivos/TLS/perfil objetivo ausentes | Cámara, seguridad o rendimiento quedan sin verificar. | Daniel/Estuardo aseguran disponibilidad o documentan bloqueo y decisión. | D1. |
| Usuarios UAT no disponibles | Sin aceptación institucional. | Pablo y Estuardo reservan sesiones y suplentes institucionales autorizados. | Agenda D1, ejecución D4–D5. |
| Muchos defectos/capacidad insuficiente | No alcanza tiempo para fix y regresión. | Pablo prioriza obligatorios, conserva reserva y solicita decisión ante exceso. | Revisión diaria, alerta D2–D3. |
| Cambios después de congelación | Evidencia/manuales ya no corresponden a candidato. | Daniel emite nuevo SHA/candidato; dominios repiten impacto y Pablo actualiza acta. | Cada cambio. |
| Skips, allowlist y enlaces temporales | Aprobación aparente o evidencia perdida. | Daniel/Santiago revisan exclusiones; exportar evidencia y acordar conservación. | Cada ronda y cierre D5. |

Las fechas relativas son objetivos de atención, no autorizaciones automáticas. Si no se resuelve una decisión material, se mantiene bloqueo de su criterio y se entrega estado real.

## 21. Lista de control de cierre D5

- [ ] Responsabilidades de Pablo, Santiago, Diana, Josué, Emilio, Estuardo, Roí y Daniel, fechas, capacidad y autoridad de aceptación confirmadas.
- [ ] Plan revisado y alcance completo clasificado, con exclusiones aprobadas.
- [ ] Casos por criterio vinculados a pruebas existentes o nuevas.
- [ ] Entorno PostgreSQL, datos sintéticos y versión reproducibles documentados.
- [ ] Funcionales e integraciones críticas aprobadas sobre candidato final.
- [ ] Seguridad básica ejecutada; hallazgos/excepciones revisados.
- [ ] Usabilidad, compatibilidad y cámara real evaluadas y registradas.
- [ ] Rendimiento aplicable medido; referencias/limitaciones explícitas.
- [ ] Recuperación, integridad, RPO/RTO y migraciones verificados.
- [ ] Incidencias clasificadas, fixes enlazados y ninguna crítica/alta abierta.
- [ ] Cada corrección conserva prueba de regresión y revisión independiente.
- [ ] Suites completas, cobertura, build y checks requeridos aprobados en SHA final.
- [ ] Matriz canónica reconciliada e instantánea final por criterio entregada.
- [ ] Evidencias indexadas, sanitizadas, accesibles y con conservación definida.
- [ ] Nueve productos documentales aplicables completos y validados.
- [ ] UAT realizado por perfiles y cambios revalidados cuando corresponde.
- [ ] Reporte final diferencia conformidad, incumplimiento, sin verificar y no aplica aprobado.
- [ ] Acta/reporte indica decisión real y aprobación institucional verificable.
- [ ] Manifiesto de versión identifica artefactos, SHA, migraciones, manuales y limitaciones.
- [ ] Paquete final permite revisar y reconstruir lo entregado.

**Estado al crear el plan:** todas las verificaciones de ejecución y aceptación anteriores quedan pendientes. La revisión de este documento confirma su coherencia y referencias; no sustituye la Fase 7.
