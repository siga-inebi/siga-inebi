# Requirements Catalogue

La columna `Estado de implementacion` de cada tabla es la fuente autoritativa.
Un requerimiento solo pasa a `Implemented` con pruebas verificables citadas.

## Functional Requirements

| ID | Descripcion original | Prioridad | Dominio | Estado de implementacion | Issue relacionado | Pruebas relacionadas | Observaciones |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RF-ASI-001 | Captura mediada por operador | Debe | attendance-capture | Not implemented | TBD | TBD | Nucleo fundacional |
| RF-ASI-002 | Registro de movimiento por escaneo | Debe | attendance-capture | Not implemented | TBD | TBD | Nucleo fundacional |
| RF-ASI-003 | Confirmacion visual del portador | Debe | attendance-capture | Not implemented | TBD | TBD | Privacidad minima en pantalla |
| RF-ASI-004 | Supresion de duplicados por estudiante | Debe | attendance-capture | Not implemented | TBD | TBD | Requiere idempotencia y reglas temporales |
| RF-ASI-005 | Tipos de movimiento admitidos por punto de control | Deberia | attendance-capture | Not implemented | TBD | TBD | Parametrizacion posterior |
| RF-ASI-006 | Autorizacion por tipo de movimiento y modo de captura | Debe | identity-access | Not implemented | TBD | TBD | Cruza auth y asistencia |
| RF-ASI-007 | Origen y transmision como atributos independientes | Debe | attendance-capture | Not implemented | TBD | TBD | Modelo de evento |
| RF-ASI-008 | Autoridad del reloj y hora de captura | Debe | attendance-governance | Not implemented | TBD | TBD | Zona horaria local obligatoria |
| RF-ASI-009 | Lote de captura recuperable | Debe | attendance-capture | Not implemented | TBD | TBD | Requiere persistencia de lote |
| RF-ASI-010 | Idempotencia de lotes y elementos | Debe | attendance-capture | Not implemented | TBD | TBD | Critico para reintentos |
| RF-ASI-011 | Cierre declarado por seccion | Deberia | attendance-governance | Not implemented | TBD | TBD | Posterior a base de captura |
| RF-ASI-013 | Trazabilidad y confirmacion del cierre por cobertura | Debe | attendance-governance | Not implemented | TBD | TBD | Auditoria obligatoria |
| RF-ASI-012 | Registro manual autorizado | Debe | attendance-capture | Not implemented | TBD | TBD | Requiere permiso explicito |
| RF-ASI-014 | Rendimiento del punto de control | Debe | attendance-capture | Not implemented | TBD | TBD | Atado a RNF-REN |
| RF-JOR-001 | Parametros de jornada configurables | Debe | attendance-governance | Not implemented | TBD | TBD | Configurable, no hardcoded |
| RF-JOR-002 | Derivacion del estado diario | Debe | attendance-governance | Not implemented | TBD | TBD | Regla central |
| RF-JOR-003 | Precedencia entre eventos | Debe | attendance-governance | Not implemented | TBD | TBD | Regla critica |
| RF-JOR-004 | Cierre de jornada | Debe | attendance-governance | Not implemented | TBD | TBD | Operacion sensible |
| RF-JOR-005 | Deteccion de inconsistencias entre fuentes | Deberia | attendance-governance | Not implemented | TBD | TBD | Requiere fuentes multiples |
| RF-JOR-006 | Recalculo ante cambios | Deberia | attendance-governance | Not implemented | TBD | TBD | Importante para correcciones |
| RF-JOR-007 | Alertas de asistencia | Debe | reporting-notifications | Not implemented | TBD | TBD | MVP basico |
| RF-JOR-009 | Porcentaje de asistencia del ciclo | Debe | attendance-governance | Not implemented | TBD | TBD | Indicador con advertencia reglamentaria |
| RF-JOR-010 | Dias no computables | Deberia | attendance-governance | Not implemented | TBD | TBD | Parametro institucional |
| RF-JOR-011 | Advertencia sobre el uso reglamentario del indicador | Deberia | attendance-governance | Not implemented | TBD | TBD | Regla de presentacion |
| RF-JOR-008 | Consulta de presencia en tiempo real | Debe | attendance-governance | Not implemented | TBD | TBD | Nucleo operativo |
| RF-JUS-001 | Solicitud de justificacion por el encargado | Debe | attendance-governance | Not implemented | TBD | TBD | Requiere alcance por estudiante |
| RF-JUS-002 | Alcance del encargado | Debe | identity-access | Not implemented | TBD | TBD | Dependencia de guardian link |
| RF-JUS-003 | Ventana de justificacion | Deberia | attendance-governance | Not implemented | TBD | TBD | Parametrizable |
| RF-JUS-004 | Revision y resolucion | Debe | attendance-governance | Not implemented | TBD | TBD | Operacion auditable |
| RF-JUS-005 | Efecto sobre el estado derivado | Debe | attendance-governance | Not implemented | TBD | TBD | No sobrescribe evento original |
| RF-JUS-006 | Notificacion del cambio de estado | Deberia | reporting-notifications | Not implemented | TBD | TBD | Posterior |
| RF-JUS-008 | Permiso prospectivo de salida anticipada o ingreso tardio | Podria | attendance-governance | Not implemented | TBD | TBD | Postergado |
| RF-JUS-009 | Efecto del permiso sobre el cierre declarado | Podria | attendance-governance | Not implemented | TBD | TBD | Decision pendiente |
| RF-JUS-007 | Confidencialidad de los respaldos | Debe | document-management | Not implemented | TBD | TBD | Dato sensible |
| RF-CRE-001 | Emision de credencial con identificador opaco | Debe | attendance-capture | Not implemented | TBD | TBD | QR sin PII |
| RF-CRE-002 | Contenido visible de la credencial | Debe | student-records | Not implemented | TBD | TBD | Politica visual pendiente |
| RF-CRE-003 | Vigencia y revocacion | Debe | attendance-capture | Not implemented | TBD | TBD | Estado de credencial |
| RF-CRE-004 | Reposicion sin perdida de historial | Debe | attendance-capture | Not implemented | TBD | TBD | Conservacion obligatoria |
| RF-CRE-005 | Persistencia de los movimientos ante revocacion | Debe | attendance-capture | Not implemented | TBD | TBD | Historia inmutable |
| RF-CRE-006 | Resolucion de identificador | Debe | attendance-capture | Not implemented | TBD | TBD | Lookup seguro |
| RF-ARC-001 | Tipos de archivo admitidos | Debe | file-storage | Not implemented | TBD | TBD | Catalogo permitido |
| RF-ARC-002 | Limite de tamaño y normalizacion de imagenes | Debe | file-storage | Not implemented | TBD | TBD | Requiere pipeline controlado |
| RF-ARC-003 | Integridad del archivo | Deberia | file-storage | Not implemented | TBD | TBD | Checksum y verificacion |
| RF-ARC-004 | Versiones del documento | Deberia | document-management | Not implemented | TBD | TBD | Modelo versionado |
| RF-ARC-005 | Consumo de almacenamiento consultable | Deberia | file-storage | Not implemented | TBD | TBD | Para monitoreo |
| RF-ARC-006 | Retencion de adjuntos de justificacion | Deberia | document-management | Not implemented | TBD | TBD | Depende politica legal |
| RF-ARC-007 | Los documentos no se eliminan | Debe | document-management | Not implemented | TBD | TBD | Preferir estados |
| RF-DOC-001 | Vinculacion del documento | Debe | document-management | Not implemented | TBD | TBD | Expediente y procesos |
| RF-DOC-002 | Catalogo de tipos de documento | Debe | document-management | Not implemented | TBD | TBD | Configurable |
| RF-DOC-003 | Los requisitos documentales se declaran en la matricula | Debe | enrollment-lifecycle | Not implemented | TBD | TBD | Cruza matricula y documentos |
| RF-DOC-004 | Acceso segun el alcance | Debe | identity-access | Not implemented | TBD | TBD | Lectura restringida |
| RF-DOC-005 | Descarga controlada | Debe | document-management | Not implemented | TBD | TBD | Enlaces breves |
| RF-DOC-006 | Auditoria de lectura | Debe | audit-compliance | Not implemented | TBD | TBD | Sensible |
| RF-DOC-007 | Digitalizacion desde escaner | Deberia | document-management | Not implemented | TBD | TBD | Posterior |
| RF-DOC-008 | Los documentos generados no se archivan | Debe | document-generation | Not implemented | TBD | TBD | Regla de separacion |
| RF-DOC-009 | Consulta del expediente documental | Debe | document-management | Not implemented | TBD | TBD | Nucleo administrativo |
| RF-DOC-010 | Conservacion del vinculo | Debe | document-management | Not implemented | TBD | TBD | Historia persistente |
| RF-CIC-001 | Registro del ciclo escolar | Debe | school-cycle | Not implemented | TBD | TBD | Nucleo fundacional |
| RF-CIC-002 | Estados del ciclo | Debe | school-cycle | Not implemented | TBD | TBD | Invariante |
| RF-CIC-003 | Apertura del ciclo | Debe | school-cycle | Implemented | TBD | backend/tests/unit/test_cycle_services.py; backend/tests/api/test_academics_catalog_api.py | Apertura con unicidad de ciclo activo por institucion |
| RF-CIC-004 | Cierre del ciclo | Debe | school-cycle | Implemented | TBD | backend/tests/unit/test_cycle_services.py; backend/tests/api/test_academics_catalog_api.py | Cierre congela la estructura del ciclo |
| RF-CIC-005 | Reapertura excepcional | Deberia | school-cycle | Not implemented | TBD | TBD | Ambiguo; controlar |
| RF-CIC-006 | Conservacion de la informacion historica | Debe | school-cycle | Not implemented | TBD | TBD | Historia obligatoria |
| RF-CIC-007 | Clonacion hacia el ciclo siguiente | Deberia | school-cycle | Not implemented | TBD | TBD | Fase posterior |
| RF-EST-001 | Catalogo de grados | Debe | institutional-structure | Implemented | TBD | backend/tests/unit/test_catalog_services.py; backend/tests/unit/test_catalog_update_services.py; backend/tests/api/test_academics_catalog_api.py | Grados ligados a nivel, con orden pedagogico |
| RF-EST-002 | Jornadas del establecimiento | Debe | institutional-structure | Implemented | TBD | backend/tests/unit/test_campus_services.py; backend/tests/api/test_academics_catalog_api.py | Jornadas por sede, con codigo unico por sede |
| RF-EST-003 | Subareas del ciclo | Debe | institutional-structure | Not implemented | TBD | TBD | Base curricular |
| RF-EST-004 | Etiqueta de presentacion configurable | Podria | institutional-structure | Not implemented | TBD | TBD | Postergado |
| RF-EST-005 | Plan de estudios por grado y ciclo | Debe | institutional-structure | Not implemented | TBD | TBD | Nucleo academico |
| RF-EST-006 | Carga horaria de la subarea | Deberia | institutional-structure | Not implemented | TBD | TBD | Cruza horario |
| RF-EST-007 | Secciones | Debe | institutional-structure | Implemented | TBD | backend/tests/unit/test_offering_services.py; backend/tests/api/test_academics_catalog_api.py | Secciones bajo la oferta de grado |
| RF-EST-008 | Cupo declarado y ocupacion consultable | Debe | enrollment-lifecycle | Implemented | TBD | backend/tests/unit/test_offering_services.py; backend/tests/api/test_academics_catalog_api.py; backend/tests/integration/test_concurrency.py | Cupo declarado y ocupacion consultable por seccion |
| RF-EST-009 | Asignacion de docentes a subareas de seccion | Debe | institutional-structure | Not implemented | TBD | TBD | Base de alcance docente |
| RF-EST-010 | Cobertura completa para la activacion del ciclo | Deberia | school-cycle | Not implemented | TBD | TBD | Regla de activacion |
| RF-EST-011 | Mutabilidad de la estructura segun el estado del ciclo | Debe | school-cycle | Implemented | TBD | backend/tests/unit/test_cycle_services.py; backend/tests/unit/test_offering_services.py | Estructura inmutable con ciclo cerrado |
| RF-EST-012 | Desactivacion en lugar de eliminacion | Deberia | institutional-structure | Implemented | TBD | backend/tests/unit/test_campus_services.py; backend/tests/unit/test_catalog_services.py; backend/tests/unit/test_offering_services.py | Desactivacion en lugar de eliminacion |
| RF-EST-013 | Independencia de la estructura entre ciclos | Debe | school-cycle | Implemented | TBD | backend/tests/unit/test_offering_services.py | Oferta y secciones versionadas por ciclo |
| RF-CAL-001 | Registro de la nota de unidad | Debe | academic-evaluation | Not implemented | TBD | TBD | Nucleo academico |
| RF-CAL-002 | Escala y validacion de la nota | Debe | academic-evaluation | Not implemented | TBD | TBD | Regla central |
| RF-CAL-003 | Distincion entre sin calificar y cero | Debe | academic-evaluation | Not implemented | TBD | TBD | Invariante importante |
| RF-CAL-004 | Carga masiva desde archivo | Deberia | academic-evaluation | Not implemented | TBD | TBD | Posterior |
| RF-CAL-005 | Correccion de notas registradas | Debe | academic-evaluation | Not implemented | TBD | TBD | Trazabilidad necesaria |
| RF-CAL-006 | Alcance del docente sobre las notas | Debe | identity-access | Not implemented | TBD | TBD | Asignacion docente |
| RF-CAL-007 | Visibilidad de las notas | Debe | academic-evaluation | Not implemented | TBD | TBD | Segun rol y alcance |
| RF-CAL-008 | Seguimiento de notas pendientes | Deberia | academic-evaluation | Not implemented | TBD | TBD | Posterior |
| RF-EVC-001 | Estructura de unidades del ciclo | Debe | academic-evaluation | Not implemented | TBD | TBD | Nucleo academico |
| RF-EVC-002 | Ventana de captura de notas | Debe | academic-evaluation | Not implemented | TBD | TBD | Regla temporal |
| RF-EVC-003 | Ventana de recuperacion | Debe | academic-evaluation | Not implemented | TBD | TBD | Requiere estados |
| RF-EVC-004 | Brecha excepcional autorizada | Deberia | academic-evaluation | Not implemented | TBD | TBD | Control especial |
| RF-EVC-005 | Configuracion global heredable | Deberia | academic-evaluation | Not implemented | TBD | TBD | Parametrizacion posterior |
| RF-EVC-006 | Clonacion de la configuracion entre ciclos | Podria | academic-evaluation | Not implemented | TBD | TBD | Posterior |
| RF-EVC-007 | Estados de la unidad | Debe | academic-evaluation | Not implemented | TBD | TBD | Invariante |
| RF-RES-001 | Nota final de la subarea | Debe | academic-evaluation | Not implemented | TBD | TBD | Resultado derivado |
| RF-RES-002 | Punto unico de redondeo | Debe | academic-evaluation | Not implemented | TBD | TBD | Regla critica |
| RF-RES-003 | Aprobacion de la subarea | Debe | academic-evaluation | Not implemented | TBD | TBD | Regla de negocio |
| RF-RES-004 | Elegibilidad de recuperacion | Debe | academic-evaluation | Not implemented | TBD | TBD | Regla de negocio |
| RF-RES-005 | Registro de la nota de recuperacion | Debe | academic-evaluation | Not implemented | TBD | TBD | Trazable |
| RF-RES-006 | Promocion al grado siguiente | Debe | enrollment-lifecycle | Not implemented | TBD | TBD | Cruza resultado y matricula |
| RF-RES-007 | Congelamiento al cierre del ciclo | Debe | school-cycle | Not implemented | TBD | TBD | Cruza cierre y resultados |
| RF-RES-008 | Boleta de calificaciones | Debe | document-generation | Not implemented | TBD | TBD | Nucleo documental |
| RF-RES-009 | Trazabilidad del resultado | Deberia | audit-compliance | Not implemented | TBD | TBD | Posterior pero importante |
| RF-EMI-001 | Emision individual | Debe | document-generation | Not implemented | TBD | TBD | Nucleo emision |
| RF-EMI-002 | Fecha y hora de generacion en el documento | Debe | document-generation | Not implemented | TBD | TBD | Metadato obligatorio |
| RF-EMI-003 | Folio correlativo de documentos oficiales | Debe | document-generation | Not implemented | TBD | TBD | Control institucional |
| RF-EMI-004 | Restricciones de emision | Deberia | document-generation | Not implemented | TBD | TBD | Regla posterior detallada |
| RF-EMI-005 | Boletas de un ciclo cerrado | Debe | document-generation | Not implemented | TBD | TBD | Cruza cierre |
| RF-EMI-006 | Emision por lote | Debe | document-generation | Not implemented | TBD | TBD | Requiere worker simple |
| RF-EMI-007 | Registro de las emisiones | Deberia | audit-compliance | Not implemented | TBD | TBD | Historial |
| RF-EMI-008 | Archivo de la emision entregada | Deberia | document-generation | Not implemented | TBD | TBD | Politica pendiente |
| RF-EMI-009 | Codigo de verificacion | Podria | document-generation | Not implemented | TBD | TBD | Verificacion publica futura |
| RF-PLA-001 | Catalogo de plantillas | Debe | document-generation | Not implemented | TBD | TBD | Configurable |
| RF-PLA-002 | Campos disponibles como catalogo cerrado | Debe | document-generation | Not implemented | TBD | TBD | Seguridad |
| RF-PLA-003 | Campos sensibles excluidos por omision | Debe | document-generation | Not implemented | TBD | TBD | Seguridad y privacidad |
| RF-PLA-004 | Encabezado institucional obligatorio | Debe | document-generation | Not implemented | TBD | TBD | Regla documental |
| RF-PLA-005 | Versiones de la plantilla | Podria | document-generation | Not implemented | TBD | TBD | Postergado |
| RF-PLA-006 | Vista previa antes de publicar | Deberia | document-generation | Not implemented | TBD | TBD | UX posterior |
| RF-PLA-007 | Plantilla activa por tipo | Debe | document-generation | Not implemented | TBD | TBD | Regla central |
| RF-AUL-001 | Registro de aulas | Deberia | institutional-structure | Not implemented | TBD | TBD | Fase posterior |
| RF-AUL-002 | Aula habitual de la seccion | Deberia | institutional-structure | Not implemented | TBD | TBD | Fase posterior |
| RF-AUL-003 | Sesiones sin aula asignada | Deberia | institutional-structure | Not implemented | TBD | TBD | Fase posterior |
| RF-AUL-004 | Capacidad del aula como advertencia | Podria | institutional-structure | Not implemented | TBD | TBD | Fase posterior |
| RF-AUL-005 | Aulas fuera de servicio | Podria | institutional-structure | Not implemented | TBD | TBD | Fase posterior |
| RF-AUL-006 | Conservacion de las aulas con historial | Podria | institutional-structure | Not implemented | TBD | TBD | Historia |
| RF-HOR-001 | Rejilla de bloques por jornada | Debe | institutional-structure | Not implemented | TBD | TBD | Base horarios |
| RF-HOR-002 | Los horarios de porton no se definen aqui | Debe | attendance-governance | Not implemented | TBD | TBD | Limite de dominio |
| RF-HOR-003 | La sesion de clase | Debe | institutional-structure | Not implemented | TBD | TBD | Entidad horario |
| RF-HOR-004 | El docente se deriva de la asignacion | Debe | institutional-structure | Not implemented | TBD | TBD | Invariante |
| RF-HOR-005 | Deteccion de cruces | Debe | institutional-structure | Not implemented | TBD | TBD | Regla central |
| RF-HOR-006 | Deteccion de cruces al asignar docentes | Deberia | institutional-structure | Not implemented | TBD | TBD | Posterior si no entra horario |
| RF-HOR-007 | Verificacion de la carga horaria | Deberia | institutional-structure | Not implemented | TBD | TBD | Posterior |
| RF-HOR-008 | Vigencia del horario | Deberia | institutional-structure | Not implemented | TBD | TBD | Posterior |
| RF-HOR-009 | Publicacion y visibilidad | Debe | institutional-structure | Not implemented | TBD | TBD | Consulta controlada |
| RF-HOR-010 | Consulta del horario segun el alcance | Debe | identity-access | Not implemented | TBD | TBD | Cruza auth |
| RF-HOR-011 | Clonacion del horario | Podria | institutional-structure | Not implemented | TBD | TBD | Posterior |
| RF-BIT-001 | Registro de operaciones de escritura | Debe | audit-compliance | Not implemented | TBD | TBD | Transversal |
| RF-BIT-002 | Contenido del asiento | Debe | audit-compliance | Not implemented | TBD | TBD | Modelo obligatorio |
| RF-BIT-003 | Catalogo de lecturas sensibles | Debe | audit-compliance | Not implemented | TBD | TBD | Transversal |
| RF-BIT-004 | Registro de intentos denegados | Deberia | audit-compliance | Not implemented | TBD | TBD | RNF exige varios casos |
| RF-BIT-005 | Inmutabilidad de la bitacora | Debe | audit-compliance | Not implemented | TBD | TBD | Critico |
| RF-BIT-006 | Consulta y exportacion restringidas | Deberia | audit-compliance | Not implemented | TBD | TBD | Rol auditor |
| RF-BIT-007 | Atribucion persistente | Debe | audit-compliance | Not implemented | TBD | TBD | No perder responsable |
| RF-ALC-001 | El alcance acompana siempre al permiso | Debe | identity-access | Not implemented | TBD | TBD | Regla base |
| RF-ALC-002 | Alcance del docente por asignacion | Debe | identity-access | Not implemented | TBD | TBD | Cruza estructura |
| RF-ALC-003 | Asignaciones versionadas | Debe | identity-access | Not implemented | TBD | TBD | Historia de alcance |
| RF-ALC-004 | Alcance de lectura historica | Deberia | identity-access | Not implemented | TBD | TBD | Regla pendiente |
| RF-ALC-005 | Alcance de escritura limitado al ciclo activo | Debe | identity-access | Not implemented | TBD | TBD | Regla base |
| RF-ALC-006 | Alcance del encargado | Debe | identity-access | Not implemented | TBD | TBD | Guardian link |
| RF-ALC-007 | Asociacion principal del estudiante | Deberia | identity-access | Not implemented | TBD | TBD | Ambiguo |
| RF-ALC-008 | Corte total al terminar la asociacion | Debe | identity-access | Not implemented | TBD | TBD | Seguridad |
| RF-ALC-009 | Union de alcances en cuentas con varios roles | Debe | identity-access | Not implemented | TBD | TBD | Regla base |
| RF-PER-001 | Catalogo de permisos atomicos | Debe | identity-access | Not implemented | TBD | TBD | Base authz |
| RF-PER-002 | Roles como agrupacion de permisos | Debe | identity-access | Not implemented | TBD | TBD | Base authz |
| RF-PER-003 | Asignacion de multiples roles | Debe | identity-access | Not implemented | TBD | TBD | Base authz |
| RF-PER-004 | Denegacion por defecto | Debe | identity-access | Not implemented | TBD | TBD | Base authz |
| RF-PER-005 | Evaluacion en cada operacion | Debe | identity-access | Not implemented | TBD | TBD | Base authz |
| RF-PER-006 | Vigencia inmediata de los cambios de autorizacion | Deberia | identity-access | Not implemented | TBD | TBD | Sesiones y cache |
| RF-PER-007 | Roles del sistema protegidos | Debe | identity-access | Not implemented | TBD | TBD | Seguridad |
| RF-AUT-001 | Inicio de sesion | Debe | identity-access | Not implemented | TBD | TBD | Nucleo fundacional |
| RF-AUT-002 | Bloqueo temporal por intentos fallidos | Debe | identity-access | Not implemented | TBD | TBD | Seguridad |
| RF-AUT-003 | Duracion de sesion configurable por rol | Deberia | identity-access | Not implemented | TBD | TBD | Posterior controlable |
| RF-AUT-004 | Cierre de sesion | Debe | identity-access | Not implemented | TBD | TBD | Nucleo fundacional |
| RF-AUT-005 | Cierre del turno de captura | Debe | attendance-capture | Not implemented | TBD | TBD | Operacion de operador |
| RF-AUT-006 | Cambio de contrasena por el titular | Debe | identity-access | Not implemented | TBD | TBD | Seguridad |
| RF-CTA-001 | Creacion exclusivamente administrativa | Debe | identity-access | Not implemented | TBD | TBD | Nucleo fundacional |
| RF-CTA-002 | Vinculacion de la cuenta a una persona registrada | Debe | people-registry | Not implemented | TBD | TBD | Nucleo fundacional |
| RF-CTA-003 | Activacion mediante codigo de un solo uso | Debe | identity-access | Not implemented | TBD | TBD | Seguridad |
| RF-CTA-004 | Politica de contrasenas | Debe | identity-access | Not implemented | TBD | TBD | Seguridad |
| RF-CTA-005 | Restablecimiento asistido | Debe | identity-access | Not implemented | TBD | TBD | Seguridad |
| RF-CTA-006 | Desactivacion con verificacion de dependencias | Debe | identity-access | Not implemented | TBD | TBD | Historia y control |
| RF-CTA-007 | Prohibicion de autoescalamiento | Debe | identity-access | Not implemented | TBD | TBD | Seguridad |
| RF-EXP-001 | Registro del estudiante | Debe | student-records | Not implemented | TBD | TBD | Nucleo fundacional |
| RF-EXP-002 | Codigo estudiantil | Debe | student-records | Not implemented | TBD | TBD | Identificador institucional |
| RF-EXP-003 | Estado del estudiante | Debe | student-records | Not implemented | TBD | TBD | Alimenta modulos |
| RF-EXP-004 | Vinculo con encargados | Debe | student-records | Not implemented | TBD | TBD | Cruza auth |
| RF-EXP-005 | Contactos de emergencia | Debe | student-records | Not implemented | TBD | TBD | Dato sensible moderado |
| RF-EXP-006 | Observaciones y anotaciones disciplinarias | Deberia | student-records | Not implemented | TBD | TBD | Politica de acceso pendiente |
| RF-EXP-007 | Fotografia del estudiante | Debe | student-records | Not implemented | TBD | TBD | Soporte escaneo |
| RF-EXP-008 | Conservacion del expediente | Debe | student-records | Not implemented | TBD | TBD | Historia obligatoria |
| RF-EXP-009 | Notas de salud del estudiante | Deberia | student-records | Not implemented | TBD | TBD | Dato sensible especial |
| RF-MAT-001 | La inscripcion como registro con vigencia | Debe | enrollment-lifecycle | Implemented | TBD | backend/tests/unit/test_enrolment_services.py; backend/tests/api/test_enrolments_api.py | Inscripcion con effective_on/ends_on |
| RF-MAT-002 | Matricula de un estudiante | Debe | enrollment-lifecycle | Implemented | TBD | backend/tests/unit/test_enrolment_services.py; backend/tests/api/test_enrolments_api.py | Matricula en ciclo/grado/seccion |
| RF-MAT-003 | Reinscripcion con datos heredados | Debe | enrollment-lifecycle | Implemented | TBD | backend/tests/unit/test_enrolment_services.py; backend/tests/api/test_enrolments_api.py | Rechaza si ya hay matricula activa en el ciclo destino |
| RF-MAT-004 | Efecto del cupo de la seccion | Debe | enrollment-lifecycle | Implemented | TBD | backend/tests/unit/test_enrolment_services.py | Cupo bloquea nuevas matriculas; fila bloqueada antes de contar |
| RF-MAT-005 | Verificacion documental | Debe | enrollment-lifecycle | Not implemented | TBD | TBD | Cruza documentos |
| RF-MAT-006 | Bloqueo de documentos oficiales por pendientes | Deberia | document-generation | Not implemented | TBD | TBD | Regla posterior |
| RF-MAT-007 | Inscripcion activa como insumo de otras capacidades | Debe | enrollment-lifecycle | Not implemented | TBD | TBD | Regla transversal |
| RF-MAT-008 | Historial de inscripciones | Debe | enrollment-lifecycle | Not implemented | TBD | TBD | Historia obligatoria |
| RF-MOV-001 | Distincion entre cambio de seccion y traslado | Debe | enrollment-lifecycle | Implemented | TBD | backend/tests/unit/test_enrolment_services.py; backend/tests/api/test_enrolments_api.py | Cambio de seccion distinto de retiro |
| RF-MOV-002 | Cambio de seccion sin perdida de informacion | Debe | enrollment-lifecycle | Implemented | TBD | backend/tests/unit/test_enrolment_services.py | Cierra la matricula previa como completed, sin borrarla |
| RF-MOV-003 | Fecha de efecto distinta de la fecha de registro | Debe | enrollment-lifecycle | Not implemented | TBD | TBD | Modelo temporal |
| RF-MOV-004 | Retiro del estudiante | Debe | enrollment-lifecycle | Implemented | TBD | backend/tests/unit/test_enrolment_services.py; backend/tests/api/test_enrolments_api.py | Solo activas; ciclo cerrado lo bloquea; preserva historial |
| RF-MOV-005 | Revocacion de la credencial al cerrar la permanencia | Debe | attendance-capture | Not implemented | TBD | TBD | Cruza matricula y credencial |
| RF-MOV-006 | Promocion y repitencia | Debe | enrollment-lifecycle | Not implemented | TBD | TBD | Cruza resultados |
| RF-MOV-007 | Matricula masiva del ciclo siguiente | Deberia | enrollment-lifecycle | Not implemented | TBD | TBD | Posterior |
| RF-MOV-008 | Correccion de movimientos registrados por error | Deberia | enrollment-lifecycle | Not implemented | TBD | TBD | Requiere auditoria fuerte |

## Non-functional Requirements

| ID | Descripcion original | Prioridad | Dominio | Estado de implementacion | Issue relacionado | Pruebas relacionadas | Observaciones |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RNF-AUD-001 | Los eventos de movimiento son inmutables; las correcciones agregan, no sobrescriben | Debe | audit-compliance | Not implemented | TBD | TBD | Asistencia |
| RNF-AUD-002 | Todo cambio de parametros queda en bitacora con responsable y vigencia | Debe | audit-compliance | Not implemented | TBD | TBD | Transversal |
| RNF-AUD-003 | Auditoria de lectura, no solo de escritura, en notas de salud y documentos del expediente | Debe | audit-compliance | Not implemented | TBD | TBD | Dato sensible |
| RNF-CAP-001 | Dimensionamiento sobre la matricula real del establecimiento; toda meta se mide contra 1 vCPU y 2 GB | Debe | platform | Not implemented | TBD | TBD | Pendiente confirmar matricula |
| RNF-CAP-002 | Crecimiento de almacenamiento estimado en 2 GB por ciclo, con umbral configurable y advertencia | Debe | file-storage | Not implemented | TBD | TBD | Planeacion storage |
| RNF-COM-001 | Operacion en telefonos de gama baja y navegadores vigentes, con acceso a camara para el escaneo | Debe | frontend-platform | Not implemented | TBD | TBD | UX y compatibilidad |
| RNF-COM-002 | Peso de pagina acotado para la conectividad disponible en el municipio | Debe | frontend-platform | Not implemented | TBD | TBD | Pendiente medicion |
| RNF-CON-001 | Un reintento por fallo de red no duplica movimientos | Debe | attendance-capture | Not implemented | TBD | TBD | Idempotencia |
| RNF-CON-002 | Un lote no confirmado se recupera desde cualquier dispositivo | Debe | attendance-capture | Not implemented | TBD | TBD | Persistencia recuperable |
| RNF-DIS-001 | Servicio disponible durante la ventana de jornada en dias lectivos; no se compromete operacion continua | Debe | platform | Not implemented | TBD | TBD | Acuerdo operativo |
| RNF-LEG-001 | Datos de menores: control de acceso por rol, minimizacion y plazos de retencion declarados | Debe | security-compliance | Not implemented | TBD | TBD | Politica pendiente parcial |
| RNF-LOC-001 | Servidor y base de datos fijados en la zona horaria del establecimiento; los eventos y las fechas de efecto se interpretan en hora local | Debe | platform | Not implemented | TBD | TBD | America/Guatemala esperable |
| RNF-LOC-002 | Interfaz, documentos y reportes en espanol | Debe | platform | Not implemented | TBD | TBD | Convencion general |
| RNF-MAN-001 | Ningun catalogo institucional fijado en codigo: tipos de documento, plantillas, parametros de jornada, ponderaciones y etiquetas son configurables | Debe | platform | Not implemented | TBD | TBD | Base de configuracion |
| RNF-MAN-002 | Los textos de los documentos institucionales se editan sin desplegar el sistema | Debe | document-generation | Not implemented | TBD | TBD | Requiere catalogo/plantillas |
| RNF-OPE-001 | Registro de errores y monitoreo minimo del proceso trabajador y de las tareas programadas | Debe | platform | Not implemented | TBD | TBD | Worker simple |
| RNF-PRI-001 | El codigo QR no codifica datos personales | Debe | attendance-capture | Not implemented | TBD | TBD | Privacidad |
| RNF-PRI-002 | La pantalla de escaneo no expone informacion de salud, academica ni de contacto | Debe | attendance-capture | Not implemented | TBD | TBD | Minimizacion visual |
| RNF-PRI-003 | No se almacenan datos personales de menores en el dispositivo del operador | Debe | attendance-capture | Not implemented | TBD | TBD | Seguridad local |
| RNF-PRI-004 | La lectura de documentos de respaldo queda auditada | Debe | audit-compliance | Not implemented | TBD | TBD | Justificaciones |
| RNF-PRI-005 | Revelacion minima en la verificacion publica de documentos: tipo, folio, fecha y vigencia | Debe | document-generation | Not implemented | TBD | TBD | Si se habilita verificacion publica |
| RNF-REN-001 | Percentil 95 de la confirmacion de escaneo en 2 s o menos, sobre la infraestructura objetivo | Debe | attendance-capture | Not implemented | TBD | TBD | Metica clave |
| RNF-REN-002 | Capacidad de pico del porton segun operadores concurrentes y tasa por operador | Debe | attendance-capture | Not implemented | TBD | TBD | Pendiente medicion sitio |
| RNF-REN-003 | Ninguna operacion sincrona excede el tiempo de espera del servidor web; los lotes se encolan | Debe | platform | Not implemented | TBD | TBD | Worker requerido |
| RNF-REN-004 | El proceso trabajador opera con concurrencia de uno y ventana configurable fuera del horario de escaneo | Debe | platform | Not implemented | TBD | TBD | Sin Celery por ahora |
| RNF-RES-001 | El respaldo de la base de datos es independiente del de archivos y se restaura en la infraestructura objetivo | Debe | platform | Not implemented | TBD | TBD | Estrategia recovery |
| RNF-RES-002 | Punto y tiempo objetivo de recuperacion declarados y probados antes de la entrega | Debe | platform | Not implemented | TBD | TBD | Pendiente definir con Direccion |
| RNF-RES-003 | Verificacion periodica de integridad de los archivos almacenados | Debe | file-storage | Not implemented | TBD | TBD | Checksum |
| RNF-SEG-001 | Cookie de sesion con HttpOnly, Secure y SameSite | Debe | identity-access | Not implemented | TBD | TBD | Seguridad web |
| RNF-SEG-002 | TLS obligatorio; sin contexto seguro no hay acceso a la camara | Debe | security-compliance | Not implemented | TBD | TBD | Camara y transporte |
| RNF-SEG-003 | Los intentos rechazados se registran como eventos auditables | Debe | audit-compliance | Not implemented | TBD | TBD | Seguridad |
| RNF-SEG-004 | Sin evaluacion de codigo en plantillas: sustitucion de marcadores contra un catalogo cerrado | Debe | document-generation | Not implemented | TBD | TBD | Seguridad |
| RNF-SEG-005 | Las descargas se resuelven con enlaces de vigencia breve atados al portador; sin rutas directas a archivos | Debe | document-management | Not implemented | TBD | TBD | Seguridad |
| RNF-SEG-006 | Limitacion de tasa en las consultas publicas sin autenticacion | Debe | document-generation | Not implemented | TBD | TBD | Verificacion publica |
| RNF-USA-001 | El permiso de camara se verifica al iniciar el turno, no en el primer escaneo | Debe | attendance-capture | Not implemented | TBD | TBD | UX operativa |
