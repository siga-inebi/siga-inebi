# Requirements Catalogue

Estado de implementacion inicial para todos requerimientos: `Not implemented`.

## Functional Requirements

| ID | Descripcion original | Prioridad | Dominio | Estado de implementacion | Issue relacionado | Pruebas relacionadas | Observaciones |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RF-ASI-001 | Captura mediada por operador | Debe | attendance-capture | Not implemented | #85 | TBD | Nucleo fundacional |
| RF-ASI-002 | Registro de movimiento por escaneo | Debe | attendance-capture | Not implemented | #86 | TBD | Nucleo fundacional |
| RF-ASI-003 | Confirmacion visual del portador | Debe | attendance-capture | Not implemented | #87 | TBD | Privacidad minima en pantalla |
| RF-ASI-004 | Supresion de duplicados por estudiante | Debe | attendance-capture | Not implemented | #88 | TBD | Requiere idempotencia y reglas temporales |
| RF-ASI-005 | Tipos de movimiento admitidos por punto de control | Deberia | attendance-capture | Not implemented | #89 | TBD | Parametrizacion posterior |
| RF-ASI-006 | Autorizacion por tipo de movimiento y modo de captura | Debe | identity-access | Not implemented | #90 | TBD | Cruza auth y asistencia |
| RF-ASI-007 | Origen y transmision como atributos independientes | Debe | attendance-capture | Not implemented | #91 | TBD | Modelo de evento |
| RF-ASI-008 | Autoridad del reloj y hora de captura | Debe | attendance-governance | Not implemented | #92 | TBD | Zona horaria local obligatoria |
| RF-ASI-009 | Lote de captura recuperable | Debe | attendance-capture | Not implemented | #93 | TBD | Requiere persistencia de lote |
| RF-ASI-010 | Idempotencia de lotes y elementos | Debe | attendance-capture | Not implemented | #94 | TBD | Critico para reintentos |
| RF-ASI-011 | Cierre declarado por seccion | Deberia | attendance-governance | Not implemented | #95 | TBD | Posterior a base de captura |
| RF-ASI-013 | Trazabilidad y confirmacion del cierre por cobertura | Debe | attendance-governance | Not implemented | #97 | TBD | Auditoria obligatoria |
| RF-ASI-012 | Registro manual autorizado | Debe | attendance-capture | Not implemented | #96 | TBD | Requiere permiso explicito |
| RF-ASI-014 | Rendimiento del punto de control | Debe | attendance-capture | Not implemented | #98 | TBD | Atado a RNF-REN |
| RF-JOR-001 | Parametros de jornada configurables | Debe | attendance-governance | Not implemented | #205 | TBD | Configurable, no hardcoded |
| RF-JOR-002 | Derivacion del estado diario | Debe | attendance-governance | Not implemented | #206 | TBD | Regla central |
| RF-JOR-003 | Precedencia entre eventos | Debe | attendance-governance | Not implemented | #207 | TBD | Regla critica |
| RF-JOR-004 | Cierre de jornada | Debe | attendance-governance | Not implemented | #208 | TBD | Operacion sensible |
| RF-JOR-005 | Deteccion de inconsistencias entre fuentes | Deberia | attendance-governance | Not implemented | #209 | TBD | Requiere fuentes multiples |
| RF-JOR-006 | Recalculo ante cambios | Deberia | attendance-governance | Not implemented | #210 | TBD | Importante para correcciones |
| RF-JOR-007 | Alertas de asistencia | Debe | reporting-notifications | Not implemented | #211 | TBD | MVP basico |
| RF-JOR-009 | Porcentaje de asistencia del ciclo | Debe | attendance-governance | Not implemented | #213 | TBD | Indicador con advertencia reglamentaria |
| RF-JOR-010 | Dias no computables | Deberia | attendance-governance | Not implemented | #214 | TBD | Parametro institucional |
| RF-JOR-011 | Advertencia sobre el uso reglamentario del indicador | Deberia | attendance-governance | Not implemented | #215 | TBD | Regla de presentacion |
| RF-JOR-008 | Consulta de presencia en tiempo real | Debe | attendance-governance | Not implemented | #212 | TBD | Nucleo operativo |
| RF-JUS-001 | Solicitud de justificacion por el encargado | Debe | attendance-governance | Not implemented | #216 | TBD | Requiere alcance por estudiante |
| RF-JUS-002 | Alcance del encargado | Debe | identity-access | Not implemented | #217 | TBD | Dependencia de guardian link |
| RF-JUS-003 | Ventana de justificacion | Deberia | attendance-governance | Not implemented | #218 | TBD | Parametrizable |
| RF-JUS-004 | Revision y resolucion | Debe | attendance-governance | Not implemented | #219 | TBD | Operacion auditable |
| RF-JUS-005 | Efecto sobre el estado derivado | Debe | attendance-governance | Not implemented | #220 | TBD | No sobrescribe evento original |
| RF-JUS-006 | Notificacion del cambio de estado | Deberia | reporting-notifications | Not implemented | #221 | TBD | Posterior |
| RF-JUS-008 | Permiso prospectivo de salida anticipada o ingreso tardio | Podria | attendance-governance | Not implemented | #223 | TBD | Postergado |
| RF-JUS-009 | Efecto del permiso sobre el cierre declarado | Podria | attendance-governance | Not implemented | #224 | TBD | Decision pendiente |
| RF-JUS-007 | Confidencialidad de los respaldos | Debe | document-management | Not implemented | #222 | TBD | Dato sensible |
| RF-CRE-001 | Emision de credencial con identificador opaco | Debe | attendance-capture | Not implemented | #133 | TBD | QR sin PII |
| RF-CRE-002 | Contenido visible de la credencial | Debe | student-records | Not implemented | #134 | TBD | Politica visual pendiente |
| RF-CRE-003 | Vigencia y revocacion | Debe | attendance-capture | Not implemented | #135 | TBD | Estado de credencial |
| RF-CRE-004 | Reposicion sin perdida de historial | Debe | attendance-capture | Not implemented | #136 | TBD | Conservacion obligatoria |
| RF-CRE-005 | Persistencia de los movimientos ante revocacion | Debe | attendance-capture | Not implemented | #137 | TBD | Historia inmutable |
| RF-CRE-006 | Resolucion de identificador | Debe | attendance-capture | Not implemented | #138 | TBD | Lookup seguro |
| RF-ARC-001 | Tipos de archivo admitidos | Debe | file-storage | Not implemented | #78 | TBD | Catalogo permitido |
| RF-ARC-002 | Limite de tamaño y normalizacion de imagenes | Debe | file-storage | Not implemented | #79 | TBD | Requiere pipeline controlado |
| RF-ARC-003 | Integridad del archivo | Deberia | file-storage | Not implemented | #80 | TBD | Checksum y verificacion |
| RF-ARC-004 | Versiones del documento | Deberia | document-management | Not implemented | #81 | TBD | Modelo versionado |
| RF-ARC-005 | Consumo de almacenamiento consultable | Deberia | file-storage | Not implemented | #82 | TBD | Para monitoreo |
| RF-ARC-006 | Retencion de adjuntos de justificacion | Deberia | document-management | Not implemented | #83 | TBD | Depende politica legal |
| RF-ARC-007 | Los documentos no se eliminan | Debe | document-management | Not implemented | #84 | TBD | Preferir estados |
| RF-DOC-001 | Vinculacion del documento | Debe | document-management | Not implemented | #146 | TBD | Expediente y procesos |
| RF-DOC-002 | Catalogo de tipos de documento | Debe | document-management | Not implemented | #147 | TBD | Configurable |
| RF-DOC-003 | Los requisitos documentales se declaran en la matricula | Debe | enrollment-lifecycle | Not implemented | #148 | TBD | Cruza matricula y documentos |
| RF-DOC-004 | Acceso segun el alcance | Debe | identity-access | Not implemented | #149 | TBD | Lectura restringida |
| RF-DOC-005 | Descarga controlada | Debe | document-management | Not implemented | #150 | TBD | Enlaces breves |
| RF-DOC-006 | Auditoria de lectura | Debe | audit-compliance | Not implemented | #151 | TBD | Sensible |
| RF-DOC-007 | Digitalizacion desde escaner | Deberia | document-management | Not implemented | #152 | TBD | Posterior |
| RF-DOC-008 | Los documentos generados no se archivan | Debe | document-generation | Not implemented | #153 | TBD | Regla de separacion |
| RF-DOC-009 | Consulta del expediente documental | Debe | document-management | Not implemented | #154 | TBD | Nucleo administrativo |
| RF-DOC-010 | Conservacion del vinculo | Debe | document-management | Not implemented | #155 | TBD | Historia persistente |
| RF-CIC-001 | Registro del ciclo escolar | Debe | school-cycle | Implemented | #126 | backend/tests/unit/test_academics_services.py; backend/tests/api/test_academics_api.py; backend/tests/integration/test_academics.py | Registro en preparacion, fechas validas y no solapadas por institucion |
| RF-CIC-002 | Estados del ciclo | Debe | school-cycle | In progress | #127 | backend/tests/unit/test_academics_services.py; backend/tests/unit/test_enrolments_services.py; backend/tests/unit/test_teaching_assignment_services.py; backend/tests/api/test_teaching_assignments_api.py; backend/tests/integration/test_academics.py; backend/tests/integration/test_cycle_state_guardrails.py | Estados explicitos, un solo ciclo activo y bloqueo de matriculas y asignaciones docentes en ciclos cerrados; visibilidad por portal y cobertura de futuros dominios consumidores pendientes |
| RF-CIC-003 | Apertura del ciclo | Debe | school-cycle | Not implemented | #128 | TBD | Operacion sensible |
| RF-CIC-002 | Estados del ciclo | Debe | school-cycle | In progress | #127 | backend/tests/unit/test_academics_services.py; backend/tests/integration/test_academics.py | Estados explicitos y un solo ciclo activo; visibilidad por portal y bloqueo transversal de escritura cerrada pendientes |
| RF-CIC-003 | Apertura del ciclo | Debe | school-cycle | In Progress | #128 | backend/tests/unit/test_academics_services.py | Valida grados ofertados, secciones y plan por grado; unidades de evaluacion pendientes de modelo |
| RF-CIC-004 | Cierre del ciclo | Debe | school-cycle | Not implemented | #129 | TBD | Congelamiento relacionado |
| RF-CIC-005 | Reapertura excepcional | Deberia | school-cycle | Not implemented | #130 | TBD | Ambiguo; controlar |
| RF-CIC-006 | Conservacion de la informacion historica | Debe | school-cycle | Not implemented | #131 | TBD | Historia obligatoria |
| RF-CIC-007 | Clonacion hacia el ciclo siguiente | Deberia | school-cycle | Implemented | #132 | backend/tests/unit/test_academics_services.py; backend/tests/api/test_academics_api.py | Copia independiente de ofertas, jornadas, secciones, planes y docentes opcionales hacia ciclo preparado |
| RF-CIC-006 | Conservacion de la informacion historica | Debe | school-cycle | In Progress | #131 | backend/tests/api/test_academics_api.py; backend/tests/integration/test_academics.py | Consulta historica de estructura y resumen de matricula; resultados de evaluacion pendientes de dominio |
| RF-CIC-007 | Clonacion hacia el ciclo siguiente | Deberia | school-cycle | Not implemented | #132 | TBD | Fase posterior |
| RF-EST-001 | Catalogo de grados | Debe | institutional-structure | Not implemented | #165 | TBD | Nucleo fundacional |
| RF-EST-002 | Jornadas del establecimiento | Debe | institutional-structure | Not implemented | #166 | TBD | Base de horarios y asistencia |
| RF-EST-003 | Subareas del ciclo | Debe | institutional-structure | Not implemented | #167 | TBD | Base curricular |
| RF-EST-004 | Etiqueta de presentacion configurable | Podria | institutional-structure | Not implemented | #168 | TBD | Postergado |
| RF-EST-005 | Plan de estudios por grado y ciclo | Debe | institutional-structure | Not implemented | #169 | TBD | Nucleo academico |
| RF-EST-006 | Carga horaria de la subarea | Deberia | institutional-structure | Not implemented | #170 | TBD | Cruza horario |
| RF-EST-007 | Secciones | Debe | institutional-structure | Not implemented | #171 | TBD | Nucleo fundacional |
| RF-EST-008 | Cupo declarado y ocupacion consultable | Debe | enrollment-lifecycle | Not implemented | #172 | TBD | Afecta matricula |
| RF-EST-009 | Asignacion de docentes a subareas de seccion | Debe | institutional-structure | Not implemented | #173 | TBD | Base de alcance docente |
| RF-EST-010 | Cobertura completa para la activacion del ciclo | Deberia | school-cycle | Not implemented | #174 | TBD | Regla de activacion |
| RF-EST-011 | Mutabilidad de la estructura segun el estado del ciclo | Debe | school-cycle | Not implemented | #175 | TBD | Regla transversal |
| RF-EST-012 | Desactivacion en lugar de eliminacion | Deberia | institutional-structure | Not implemented | #176 | TBD | Linea con historia |
| RF-EST-013 | Independencia de la estructura entre ciclos | Debe | school-cycle | Not implemented | #177 | TBD | Versionado por ciclo |
| RF-CAL-001 | Registro de la nota de unidad | Debe | academic-evaluation | Not implemented | #118 | TBD | Nucleo academico |
| RF-CAL-002 | Escala y validacion de la nota | Debe | academic-evaluation | Not implemented | #119 | TBD | Regla central |
| RF-CAL-003 | Distincion entre sin calificar y cero | Debe | academic-evaluation | Not implemented | #120 | TBD | Invariante importante |
| RF-CAL-004 | Carga masiva desde archivo | Deberia | academic-evaluation | Not implemented | #121 | TBD | Posterior |
| RF-CAL-005 | Correccion de notas registradas | Debe | academic-evaluation | Not implemented | #122 | TBD | Trazabilidad necesaria |
| RF-CAL-006 | Alcance del docente sobre las notas | Debe | identity-access | Not implemented | #123 | TBD | Asignacion docente |
| RF-CAL-007 | Visibilidad de las notas | Debe | academic-evaluation | Not implemented | #124 | TBD | Segun rol y alcance |
| RF-CAL-008 | Seguimiento de notas pendientes | Deberia | academic-evaluation | Not implemented | #125 | TBD | Posterior |
| RF-EVC-001 | Estructura de unidades del ciclo | Debe | academic-evaluation | Not implemented | #178 | TBD | Nucleo academico |
| RF-EVC-002 | Ventana de captura de notas | Debe | academic-evaluation | Not implemented | #179 | TBD | Regla temporal |
| RF-EVC-003 | Ventana de recuperacion | Debe | academic-evaluation | Not implemented | #180 | TBD | Requiere estados |
| RF-EVC-004 | Brecha excepcional autorizada | Deberia | academic-evaluation | Not implemented | #181 | TBD | Control especial |
| RF-EVC-005 | Configuracion global heredable | Deberia | academic-evaluation | Not implemented | #182 | TBD | Parametrizacion posterior |
| RF-EVC-006 | Clonacion de la configuracion entre ciclos | Podria | academic-evaluation | Not implemented | #183 | TBD | Posterior |
| RF-EVC-007 | Estados de la unidad | Debe | academic-evaluation | Not implemented | #184 | TBD | Invariante |
| RF-RES-001 | Nota final de la subarea | Debe | academic-evaluation | Not implemented | #255 | TBD | Resultado derivado |
| RF-RES-002 | Punto unico de redondeo | Debe | academic-evaluation | Not implemented | #256 | TBD | Regla critica |
| RF-RES-003 | Aprobacion de la subarea | Debe | academic-evaluation | Not implemented | #257 | TBD | Regla de negocio |
| RF-RES-004 | Elegibilidad de recuperacion | Debe | academic-evaluation | Not implemented | #258 | TBD | Regla de negocio |
| RF-RES-005 | Registro de la nota de recuperacion | Debe | academic-evaluation | Not implemented | #259 | TBD | Trazable |
| RF-RES-006 | Promocion al grado siguiente | Debe | enrollment-lifecycle | Not implemented | #260 | TBD | Cruza resultado y matricula |
| RF-RES-007 | Congelamiento al cierre del ciclo | Debe | school-cycle | Not implemented | #261 | TBD | Cruza cierre y resultados |
| RF-RES-008 | Boleta de calificaciones | Debe | document-generation | Not implemented | #262 | TBD | Nucleo documental |
| RF-RES-009 | Trazabilidad del resultado | Deberia | audit-compliance | Not implemented | #263 | TBD | Posterior pero importante |
| RF-EMI-001 | Emision individual | Debe | document-generation | Not implemented | #156 | TBD | Nucleo emision |
| RF-EMI-002 | Fecha y hora de generacion en el documento | Debe | document-generation | Not implemented | #157 | TBD | Metadato obligatorio |
| RF-EMI-003 | Folio correlativo de documentos oficiales | Debe | document-generation | Not implemented | #158 | TBD | Control institucional |
| RF-EMI-004 | Restricciones de emision | Deberia | document-generation | Not implemented | #159 | TBD | Regla posterior detallada |
| RF-EMI-005 | Boletas de un ciclo cerrado | Debe | document-generation | Not implemented | #160 | TBD | Cruza cierre |
| RF-EMI-006 | Emision por lote | Debe | document-generation | Not implemented | #161 | TBD | Requiere worker simple |
| RF-EMI-007 | Registro de las emisiones | Deberia | audit-compliance | Not implemented | #162 | TBD | Historial |
| RF-EMI-008 | Archivo de la emision entregada | Deberia | document-generation | Not implemented | #163 | TBD | Politica pendiente |
| RF-EMI-009 | Codigo de verificacion | Podria | document-generation | Not implemented | #164 | TBD | Verificacion publica futura |
| RF-PLA-001 | Catalogo de plantillas | Debe | document-generation | Implemented | #248 | backend/tests/unit/test_documents_services.py; backend/tests/api/test_documents_api.py; backend/tests/integration/test_documents.py | Configurable; crea la app `documents` con codigo unico por institucion y baja logica |
| RF-PLA-002 | Campos disponibles como catalogo cerrado | Debe | document-generation | Implemented | #249 | backend/tests/unit/test_documents_services.py; backend/tests/api/test_documents_api.py | Seguridad; catalogo fijo en `apps/documents/field_catalog.py`, sin campo de contenido en DocumentTemplate todavia |
| RF-PLA-003 | Campos sensibles excluidos por omision | Debe | document-generation | Implemented | #250 | backend/tests/unit/test_documents_services.py; backend/tests/api/test_documents_api.py | Seguridad y privacidad; mecanismo de exclusion por marca `sensitive` + permiso `student.view_sensitive`, sin campos medicos reales todavia |
| RF-PLA-004 | Encabezado institucional obligatorio | Debe | document-generation | Implemented | #251 | backend/tests/unit/test_documents_services.py; backend/tests/api/test_documents_api.py | Regla documental; encabezado derivado (no almacenado) de Institution, logo_url pendiente del dominio file-storage |
| RF-PLA-005 | Versiones de la plantilla | Podria | document-generation | Implemented | #252 | backend/tests/unit/test_documents_services.py; backend/tests/api/test_documents_api.py; backend/tests/integration/test_documents.py | Historial inmutable via DocumentTemplateVersion; snapshot automatico en creacion y en cada update con cambios |
| RF-PLA-006 | Vista previa antes de publicar | Deberia | document-generation | Not implemented | #253 | TBD | UX posterior |
| RF-PLA-007 | Plantilla activa por tipo | Debe | document-generation | Not implemented | #254 | TBD | Regla central |
| RF-AUL-001 | Registro de aulas | Deberia | institutional-structure | Not implemented | #99 | TBD | Fase posterior |
| RF-AUL-002 | Aula habitual de la seccion | Deberia | institutional-structure | Not implemented | #100 | TBD | Fase posterior |
| RF-AUL-003 | Sesiones sin aula asignada | Deberia | institutional-structure | Not implemented | #101 | TBD | Fase posterior |
| RF-AUL-004 | Capacidad del aula como advertencia | Podria | institutional-structure | Not implemented | #102 | TBD | Fase posterior |
| RF-AUL-005 | Aulas fuera de servicio | Podria | institutional-structure | Not implemented | #103 | TBD | Fase posterior |
| RF-AUL-006 | Conservacion de las aulas con historial | Podria | institutional-structure | Not implemented | #104 | TBD | Historia |
| RF-HOR-001 | Rejilla de bloques por jornada | Debe | institutional-structure | Not implemented | #194 | TBD | Base horarios |
| RF-HOR-002 | Los horarios de porton no se definen aqui | Debe | attendance-governance | Not implemented | #195 | TBD | Limite de dominio |
| RF-HOR-003 | La sesion de clase | Debe | institutional-structure | Not implemented | #196 | TBD | Entidad horario |
| RF-HOR-004 | El docente se deriva de la asignacion | Debe | institutional-structure | Not implemented | #197 | TBD | Invariante |
| RF-HOR-005 | Deteccion de cruces | Debe | institutional-structure | Not implemented | #198 | TBD | Regla central |
| RF-HOR-006 | Deteccion de cruces al asignar docentes | Deberia | institutional-structure | Not implemented | #199 | TBD | Posterior si no entra horario |
| RF-HOR-007 | Verificacion de la carga horaria | Deberia | institutional-structure | Not implemented | #200 | TBD | Posterior |
| RF-HOR-008 | Vigencia del horario | Deberia | institutional-structure | Not implemented | #201 | TBD | Posterior |
| RF-HOR-009 | Publicacion y visibilidad | Debe | institutional-structure | Not implemented | #202 | TBD | Consulta controlada |
| RF-HOR-010 | Consulta del horario segun el alcance | Debe | identity-access | Not implemented | #203 | TBD | Cruza auth |
| RF-HOR-011 | Clonacion del horario | Podria | institutional-structure | Not implemented | #204 | TBD | Posterior |
| RF-BIT-001 | Registro de operaciones de escritura | Debe | audit-compliance | Implemented | #111 | backend/tests/unit/test_audit_services.py; backend/tests/api/test_audit_api.py; backend/tests/permissions/test_audit_permissions.py; backend/tests/integration/test_audit.py | Transversal; auditoria de escrituras verificada en las ~65 funciones de escritura del backend, unico hueco real cerrado en authenticate_account |
| RF-BIT-002 | Contenido del asiento | Debe | audit-compliance | Not implemented | #112 | TBD | Modelo obligatorio |
| RF-BIT-003 | Catalogo de lecturas sensibles | Debe | audit-compliance | Not implemented | #113 | TBD | Transversal |
| RF-BIT-004 | Registro de intentos denegados | Deberia | audit-compliance | Not implemented | #114 | TBD | RNF exige varios casos |
| RF-BIT-005 | Inmutabilidad de la bitacora | Debe | audit-compliance | Not implemented | #115 | TBD | Critico |
| RF-BIT-006 | Consulta y exportacion restringidas | Deberia | audit-compliance | Not implemented | #116 | TBD | Rol auditor |
| RF-BIT-007 | Atribucion persistente | Debe | audit-compliance | Implemented | #117 | backend/tests/unit/test_audit_services.py; backend/tests/api/test_audit_api.py; backend/tests/integration/test_audit.py | No perder responsable; mecanismo (actor SET_NULL + actor_label snapshot) ya existia, ticket formaliza cobertura con docente real |
| RF-ALC-001 | El alcance acompana siempre al permiso | Debe | identity-access | Implemented | #69 | backend/tests/permissions/test_identity_permissions.py; backend/tests/unit/test_identity_services.py | Evaluacion y filtrado compartidos; grant sin dimension rechazado |
| RF-ALC-002 | Alcance del docente por asignacion | Debe | identity-access | Not implemented | #70 | TBD | Cruza estructura |
| RF-ALC-003 | Asignaciones versionadas | Debe | identity-access | Not implemented | #71 | TBD | Historia de alcance |
| RF-ALC-004 | Alcance de lectura historica | Deberia | identity-access | Not implemented | #72 | TBD | Regla pendiente |
| RF-ALC-005 | Alcance de escritura limitado al ciclo activo | Debe | identity-access | Implemented | #73 | backend/tests/permissions/test_identity_permissions.py; backend/tests/unit/test_identity_services.py | Restringe escrituras al ciclo activo y deniega modificaciones en ciclos cerrados |
| RF-ALC-006 | Alcance del encargado | Debe | identity-access | Not implemented | #74 | TBD | Guardian link |
| RF-ALC-007 | Asociacion principal del estudiante | Deberia | identity-access | Not implemented | #75 | TBD | Ambiguo |
| RF-ALC-008 | Corte total al terminar la asociacion | Debe | identity-access | Not implemented | #76 | TBD | Seguridad |
| RF-ALC-009 | Union de alcances en cuentas con varios roles | Debe | identity-access | Not implemented | #77 | TBD | Regla base |
| RF-PER-001 | Catalogo de permisos atomicos | Debe | identity-access | Implemented | #241 | backend/tests/unit/test_identity_services.py; backend/tests/api/test_identity_permission_catalog_api.py | Catalogo administrativo auditable con acciones atomicas diferenciadas |
| RF-PER-002 | Roles como agrupacion de permisos | Debe | identity-access | Implemented | #242 | backend/tests/unit/test_identity_services.py; backend/tests/api/test_identity_roles_api.py | Composicion configurable y auditable |
| RF-PER-003 | Asignacion de multiples roles | Debe | identity-access | Implemented | #243 | backend/tests/permissions/test_identity_permissions.py; backend/tests/api/test_identity_roles_api.py | Union de roles vigentes expuesta por API |
| RF-PER-004 | Denegacion por defecto | Debe | identity-access | Implemented | #244 | backend/tests/permissions/test_identity_permissions.py; backend/tests/api/test_identity_roles_api.py | Sin permiso o scope explicitos se deniega |
| RF-PER-005 | Evaluacion en cada operacion | Debe | identity-access | Implemented | #245 | backend/tests/api/test_identity_roles_api.py; backend/tests/unit/test_identity_services.py | Clase DRF y servicios compartidos auditan denegaciones directas |
| RF-PER-006 | Vigencia inmediata de los cambios de autorizacion | Deberia | identity-access | Implemented | #246 | backend/tests/unit/test_identity_services.py; backend/tests/api/test_identity_roles_api.py | Composicion y revocacion evaluadas por operacion |
| RF-PER-007 | Roles del sistema protegidos | Debe | identity-access | Implemented | #247 | backend/tests/unit/test_identity_services.py | Protege ultimo rol, permiso y cuenta administradora |
| RF-AUT-001 | Inicio de sesion | Debe | identity-access | Not implemented | #105 | TBD | Nucleo fundacional |
| RF-AUT-002 | Bloqueo temporal por intentos fallidos | Debe | identity-access | Implemented | #106 | backend/tests/{unit/test_identity_services.py,api/test_identity_api.py,api/test_auth_api.py,permissions/test_identity_permissions.py,integration/test_identity.py}; frontend/src/test/App.test.jsx | Bloqueo configurable tras 5 intentos fallidos y levantamiento automatico |
| RF-AUT-003 | Duracion de sesion configurable por rol | Deberia | identity-access | Not implemented | #107 | TBD | Posterior controlable |
| RF-AUT-004 | Cierre de sesion | Debe | identity-access | Not implemented | #108 | TBD | Nucleo fundacional |
| RF-AUT-005 | Cierre del turno de captura | Debe | attendance-capture | Not implemented | #109 | TBD | Operacion de operador |
| RF-AUT-006 | Cambio de contrasena por el titular | Debe | identity-access | Implemented | #110 | backend/tests/{unit/test_identity_services.py,api/test_identity_api.py,permissions/test_identity_permissions.py,integration/test_identity.py}; frontend/src/test/ChangePasswordWindow.test.jsx | Exige confirmacion de vigente, cierra demas sesiones y audita |
| RF-CTA-001 | Creacion exclusivamente administrativa | Debe | identity-access | Implemented | #139 | backend/tests/permissions/test_identity_permissions.py; backend/tests/api/test_identity_account_provisioning_api.py | Provision protegida por account.create y ausencia de ruta publica de autorregistro verificadas |
| RF-CTA-002 | Vinculacion de la cuenta a una persona registrada | Debe | people-registry | Not implemented | #140 | TBD | Nucleo fundacional |
| RF-CTA-003 | Activacion mediante codigo de un solo uso | Debe | identity-access | Not implemented | #141 | TBD | Seguridad |
| RF-CTA-004 | Politica de contrasenas | Debe | identity-access | Implemented | #142 | backend/tests/unit/test_identity_services.py | Longitud minima configurable y rechazo de comunes; no exige mayusculas ni simbolos |
| RF-CTA-005 | Restablecimiento asistido | Debe | identity-access | Not implemented | #143 | TBD | Seguridad |
| RF-CTA-006 | Desactivacion con verificacion de dependencias | Debe | identity-access | Not implemented | #144 | TBD | Historia y control |
| RF-CTA-007 | Prohibicion de autoescalamiento | Debe | identity-access | Implemented | #145 | backend/tests/unit/test_identity_services.py; backend/tests/permissions/test_identity_permissions.py | Prohibicion estricta y auditada de autoasignacion/revocacion de roles, autodesactivacion y autoactivacion |
| RF-CTA-006 | Desactivacion con verificacion de dependencias | Debe | identity-access | Implemented | #144 | backend/tests/unit/test_identity_services.py | Desactivacion advierte asignaciones vigentes; eventos historicos sobreviven |
| RF-CTA-007 | Prohibicion de autoescalamiento | Debe | identity-access | Not implemented | #145 | TBD | Seguridad |
| RF-EXP-001 | Registro del estudiante | Debe | student-records | Not implemented | #185 | TBD | Nucleo fundacional |
| RF-EXP-002 | Codigo estudiantil | Debe | student-records | Not implemented | #186 | TBD | Identificador institucional |
| RF-EXP-003 | Estado del estudiante | Debe | student-records | Not implemented | #187 | TBD | Alimenta modulos |
| RF-EXP-004 | Vinculo con encargados | Debe | student-records | Not implemented | #188 | TBD | Cruza auth |
| RF-EXP-005 | Contactos de emergencia | Debe | student-records | Not implemented | #189 | TBD | Dato sensible moderado |
| RF-EXP-006 | Observaciones y anotaciones disciplinarias | Deberia | student-records | In Progress | #190 | TBD | Flujo protegido implementado; asignacion exacta de roles pendiente en PD-005 |
| RF-EXP-007 | Fotografia del estudiante | Debe | student-records | Not implemented | #191 | TBD | Soporte escaneo |
| RF-EXP-008 | Conservacion del expediente | Debe | student-records | Not implemented | #192 | TBD | Historia obligatoria |
| RF-EXP-009 | Notas de salud del estudiante | Deberia | student-records | Not implemented | #193 | TBD | Dato sensible especial |
| RF-MAT-001 | La inscripcion como registro con vigencia | Debe | enrollment-lifecycle | Not implemented | #225 | TBD | Nucleo fundacional |
| RF-MAT-002 | Matricula de un estudiante | Debe | enrollment-lifecycle | Not implemented | #226 | TBD | Nucleo fundacional |
| RF-MAT-003 | Reinscripcion con datos heredados | Debe | enrollment-lifecycle | Not implemented | #227 | TBD | Nucleo fundacional |
| RF-MAT-004 | Efecto del cupo de la seccion | Debe | enrollment-lifecycle | Not implemented | #228 | TBD | Regla central |
| RF-MAT-005 | Verificacion documental | Debe | enrollment-lifecycle | Not implemented | #229 | TBD | Cruza documentos |
| RF-MAT-006 | Bloqueo de documentos oficiales por pendientes | Deberia | document-generation | Not implemented | #230 | TBD | Regla posterior |
| RF-MAT-007 | Inscripcion activa como insumo de otras capacidades | Debe | enrollment-lifecycle | Not implemented | #231 | TBD | Regla transversal |
| RF-MAT-008 | Historial de inscripciones | Debe | enrollment-lifecycle | Not implemented | #232 | TBD | Historia obligatoria |
| RF-MOV-001 | Distincion entre cambio de seccion y traslado | Debe | enrollment-lifecycle | Not implemented | #233 | TBD | Regla de movilidad |
| RF-MOV-002 | Cambio de seccion sin perdida de informacion | Debe | enrollment-lifecycle | Not implemented | #234 | TBD | Historia obligatoria |
| RF-MOV-003 | Fecha de efecto distinta de la fecha de registro | Debe | enrollment-lifecycle | Not implemented | #235 | TBD | Modelo temporal |
| RF-MOV-004 | Retiro del estudiante | Debe | enrollment-lifecycle | Not implemented | #236 | TBD | Regla de permanencia |
| RF-MOV-005 | Revocacion de la credencial al cerrar la permanencia | Debe | attendance-capture | Not implemented | #237 | TBD | Cruza matricula y credencial |
| RF-MOV-006 | Promocion y repitencia | Debe | enrollment-lifecycle | Not implemented | #238 | TBD | Cruza resultados |
| RF-MOV-007 | Matricula masiva del ciclo siguiente | Deberia | enrollment-lifecycle | Not implemented | #239 | TBD | Posterior |
| RF-MOV-008 | Correccion de movimientos registrados por error | Deberia | enrollment-lifecycle | Not implemented | #240 | TBD | Requiere auditoria fuerte |

## Non-functional Requirements

| ID | Descripcion original | Prioridad | Dominio | Estado de implementacion | Issue relacionado | Pruebas relacionadas | Observaciones |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RNF-AUD-001 | Los eventos de movimiento son inmutables; las correcciones agregan, no sobrescriben | Debe | audit-compliance | Not implemented | #264 | TBD | Asistencia |
| RNF-AUD-002 | Todo cambio de parametros queda en bitacora con responsable y vigencia | Debe | audit-compliance | Not implemented | #265 | TBD | Transversal |
| RNF-AUD-003 | Auditoria de lectura, no solo de escritura, en notas de salud y documentos del expediente | Debe | audit-compliance | Not implemented | #266 | TBD | Dato sensible |
| RNF-CAP-001 | Dimensionamiento sobre la matricula real del establecimiento; toda meta se mide contra 1 vCPU y 2 GB | Debe | platform | Not implemented | #267 | TBD | Pendiente confirmar matricula |
| RNF-CAP-002 | Crecimiento de almacenamiento estimado en 2 GB por ciclo, con umbral configurable y advertencia | Debe | file-storage | Not implemented | #268 | TBD | Planeacion storage |
| RNF-COM-001 | Operacion en telefonos de gama baja y navegadores vigentes, con acceso a camara para el escaneo | Debe | frontend-platform | Not implemented | #269 | TBD | UX y compatibilidad |
| RNF-COM-002 | Peso de pagina acotado para la conectividad disponible en el municipio | Debe | frontend-platform | Not implemented | #270 | TBD | Pendiente medicion |
| RNF-CON-001 | Un reintento por fallo de red no duplica movimientos | Debe | attendance-capture | Not implemented | #271 | TBD | Idempotencia |
| RNF-CON-002 | Un lote no confirmado se recupera desde cualquier dispositivo | Debe | attendance-capture | Not implemented | #272 | TBD | Persistencia recuperable |
| RNF-DIS-001 | Servicio disponible durante la ventana de jornada en dias lectivos; no se compromete operacion continua | Debe | platform | Not implemented | #273 | TBD | Acuerdo operativo |
| RNF-LEG-001 | Datos de menores: control de acceso por rol, minimizacion y plazos de retencion declarados | Debe | security-compliance | Not implemented | #274 | TBD | Politica pendiente parcial |
| RNF-LOC-001 | Servidor y base de datos fijados en la zona horaria del establecimiento; los eventos y las fechas de efecto se interpretan en hora local | Debe | platform | Not implemented | #275 | TBD | America/Guatemala esperable |
| RNF-LOC-002 | Interfaz, documentos y reportes en espanol | Debe | platform | Not implemented | #276 | TBD | Convencion general |
| RNF-MAN-001 | Ningun catalogo institucional fijado en codigo: tipos de documento, plantillas, parametros de jornada, ponderaciones y etiquetas son configurables | Debe | platform | Not implemented | #277 | TBD | Base de configuracion |
| RNF-MAN-002 | Los textos de los documentos institucionales se editan sin desplegar el sistema | Debe | document-generation | Not implemented | #278 | TBD | Requiere catalogo/plantillas |
| RNF-OPE-001 | Registro de errores y monitoreo minimo del proceso trabajador y de las tareas programadas | Debe | platform | Not implemented | #279 | TBD | Worker simple |
| RNF-PRI-001 | El codigo QR no codifica datos personales | Debe | attendance-capture | Not implemented | #280 | TBD | Privacidad |
| RNF-PRI-002 | La pantalla de escaneo no expone informacion de salud, academica ni de contacto | Debe | attendance-capture | Not implemented | #281 | TBD | Minimizacion visual |
| RNF-PRI-003 | No se almacenan datos personales de menores en el dispositivo del operador | Debe | attendance-capture | Not implemented | #282 | TBD | Seguridad local |
| RNF-PRI-004 | La lectura de documentos de respaldo queda auditada | Debe | audit-compliance | Not implemented | #283 | TBD | Justificaciones |
| RNF-PRI-005 | Revelacion minima en la verificacion publica de documentos: tipo, folio, fecha y vigencia | Debe | document-generation | Not implemented | #284 | TBD | Si se habilita verificacion publica |
| RNF-REN-001 | Percentil 95 de la confirmacion de escaneo en 2 s o menos, sobre la infraestructura objetivo | Debe | attendance-capture | Not implemented | #285 | TBD | Metica clave |
| RNF-REN-002 | Capacidad de pico del porton segun operadores concurrentes y tasa por operador | Debe | attendance-capture | Not implemented | #286 | TBD | Pendiente medicion sitio |
| RNF-REN-003 | Ninguna operacion sincrona excede el tiempo de espera del servidor web; los lotes se encolan | Debe | platform | Not implemented | #287 | TBD | Worker requerido |
| RNF-REN-004 | El proceso trabajador opera con concurrencia de uno y ventana configurable fuera del horario de escaneo | Debe | platform | Not implemented | #288 | TBD | Sin Celery por ahora |
| RNF-RES-001 | El respaldo de la base de datos es independiente del de archivos y se restaura en la infraestructura objetivo | Debe | platform | Not implemented | #289 | TBD | Estrategia recovery |
| RNF-RES-002 | Punto y tiempo objetivo de recuperacion declarados y probados antes de la entrega | Debe | platform | Not implemented | #290 | TBD | Pendiente definir con Direccion |
| RNF-RES-003 | Verificacion periodica de integridad de los archivos almacenados | Debe | file-storage | Not implemented | #291 | TBD | Checksum |
| RNF-SEG-001 | Cookie de sesion con HttpOnly, Secure y SameSite | Debe | identity-access | Not implemented | #292 | TBD | Seguridad web |
| RNF-SEG-002 | TLS obligatorio; sin contexto seguro no hay acceso a la camara | Debe | security-compliance | Not implemented | #293 | TBD | Camara y transporte |
| RNF-SEG-003 | Los intentos rechazados se registran como eventos auditables | Debe | audit-compliance | Not implemented | #294 | TBD | Seguridad |
| RNF-SEG-004 | Sin evaluacion de codigo en plantillas: sustitucion de marcadores contra un catalogo cerrado | Debe | document-generation | Not implemented | #295 | TBD | Seguridad |
| RNF-SEG-005 | Las descargas se resuelven con enlaces de vigencia breve atados al portador; sin rutas directas a archivos | Debe | document-management | Not implemented | #296 | TBD | Seguridad |
| RNF-SEG-006 | Limitacion de tasa en las consultas publicas sin autenticacion | Debe | document-generation | Not implemented | #297 | TBD | Verificacion publica |
| RNF-USA-001 | El permiso de camara se verifica al iniciar el turno, no en el primer escaneo | Debe | attendance-capture | Not implemented | #298 | TBD | UX operativa |
