# Manual de Usuario en Video — Segmento: Documentos y Auditoría

Este documento formaliza el guion técnico, la locución en audio español (TTS) y la ficha de registro del segmento audiovisual correspondiente al dominio de **Documentos y Auditoría** de SIGA-INEBI, aportado por Roí en el marco de la Fase 7.

---

## 1. Ficha de registro para el expediente

| Campo | Detalle registrado |
| :--- | :--- |
| **Producto** | Manual de usuario en video — Documentos y auditoría |
| **Título del segmento** | Documentos y auditoría — carga, consulta, descarga e historial |
| **Responsable** | Roí Rosales (`1Roy1` / Desarrollador y responsable de Documentos y Auditoría) |
| **Revisor** | Estuardo (Evaluación y usabilidad) / Emilio (Coordinación de manual audiovisual) |
| **Rol utilizado** | 1. Secretaría / documentos (carga, consulta, historial y descarga).<br>2. Docente sin alcance (demostración de denegación por menor privilegio).<br>3. Auditor institucional (consulta de bitácora y eventos). |
| **Candidato SHA** | `19f9312620247da85c1aa92fd6a0030031b43da7` |
| **Entorno** | QA / Staging local controlado (Base de datos de prueba sintética, sin acceso a producción) |
| **Fecha y zona horaria** | 2026-10-12 23:45 CST (America/Guatemala UTC-6) |
| **Duración** | **06:34** (394.61 segundos acumulados en 11 escenas sincronizadas en el sistema real) |
| **Ubicación o enlace controlado** | **Video MP4 (Sistema Real):** `docs/manuals/video-manual-documentos-auditoria-sistema-real.mp4`<br>**Pistas de audio TTS:** `docs/manuals/locucion-documentos-auditoria/` |
| **Checksum maestro** | **Video MP4 Sistema Real:** `SHA-256: 7e2c7e45b96df28f653ef382d7e464f4b4fe9dc49ddb9f502fc3e6928fe90745`<br>**Audio MP3 Maestro:** `SHA-256: c06d98b300361fee4ec0fb89650e3cd50f8693f2cea265488905288938cfd201` |
| **Datos sintéticos utilizados** | - **Estudiante:** Ana Demo Sintética<br>- **Código institucional:** `QA-DOC-001`<br>- **Documento válido:** `constancia-demo.pdf`<br>- **Contenido:** *Documento sintético para pruebas de aseguramiento de calidad*<br>- **Archivo inválido:** `archivo-invalido.exe`<br>- **Archivo excedido:** `archivo-excedido.pdf` (~11 MB)<br>- **Usuario sin alcance:** `docente.sin.alcance@inebi.edu.gt`<br>- **Documento alterado:** `documento-alterado.pdf` |
| **Operaciones demostradas** | 1. Autenticación con rol institucional de secretaría sin revelar credenciales.<br>2. Localización de expediente documental del estudiante.<br>3. Carga de respaldo PDF con verificación de tipo MIME y cálculo de hash SHA-256.<br>4. Almacenamiento desacoplado fuera de la base de datos relacional.<br>5. Consulta del registro y transición de estado del requisito a "Entregado".<br>6. Historial de versiones y política de inmutabilidad (v1 vigente, retención de versiones previas).<br>7. Descarga autorizada por streaming seguro sin exposición de cookies, tokens ni URLs internas.<br>8. Inspección de bitácora y eventos con rol de Auditor Institucional. |
| **Rechazos demostrados** | 1. **Rechazo por formato inválido:** Bloqueo inmediato de archivo ejecutable `.exe` (HTTP 400/415).<br>2. **Rechazo por tamaño excedido:** Bloqueo de archivo de 11 MB que supera la cuota máxima permitida.<br>3. **Rechazo por falta de alcance:** Usuario autenticado sin asignación sobre la sede/sección recibe denegación estricta (HTTP 403 / menor privilegio).<br>4. **Auditoría del rechazo:** Confirmación de que el intento denegado queda asentado de forma inmutable en la bitácora con IP, actor, recurso y motivo. |
| **Resultado** | **Conforme / Verificado**. Todas las escenas cumplen los estándares de seguridad, privacidad y trazabilidad institucional. |
| **Incidencias** | Ninguna. La demostración se ejecuta 100% sobre datos sintéticos; no se muestran contraseñas, variables de entorno, dumps ni tokens de almacenamiento. |
| **Fecha de revisión** | 2026-10-12 |
| **Constancia del revisor** | Segmento auditado y aprobado técnicamente para su ensamblado en el Manual de Usuario en Video institucional consolidado. |

---

## 2. Guion técnico y locución audiovisual (11 Escenas)

### Escena 1: Presentación del objetivo y roles autorizados
- **Duración de locución:** 00:43 (43.13 s)
- **Audio TTS:** `escena-01.mp3` (`fb305b5ffa3ed7115c1416c0f9cef99e5012b463ac373efee45a6ec2b30d942f`)
- **Acción visual en pantalla:**
  - Carátula institucional con el logotipo de SIGA-INEBI.
  - Título: *Manual de Usuario — Documentos y Auditoría*.
  - Muestra en pantalla los roles involucrados: Secretaría (gestión documental) y Auditoría (supervisión y bitácora).
  - Cintillo inferior: *Entorno de aseguramiento de calidad (QA). Todos los datos son ficticios y sintéticos.*
- **Texto de locución (Audio en español):**
  > "Bienvenidos al manual de usuario de SIGA-INEBI. En este segmento demostraremos el ciclo completo de documentos y auditoría: desde la carga, validación, consulta e historial de versiones, hasta la descarga segura y la verificación de eventos en la bitácora institucional. Participaremos con dos roles autorizados: primero, el rol de Secretaría de Documentos, responsable de la gestión documental de expedientes; y posteriormente, el rol de Auditor institucional, facultado para la supervisión y trazabilidad del sistema."

---

### Escena 2: Inicio de sesión con cuenta QA ficticia
- **Duración de locución:** 00:35 (35.50 s)
- **Audio TTS:** `escena-02.mp3` (`0cd9918df3b73bbac020bb2e0e4ffef01e0ea54f88184de3c5ed0426535be6ef`)
- **Acción visual en pantalla:**
  - Formulario de inicio de sesión de SIGA-INEBI.
  - Se ingresa con el usuario sintético `secretaria.qa@inebi.edu.gt`.
  - El campo de contraseña muestra caracteres enmascarados (`••••••••`).
  - La barra de navegación y las herramientas de desarrollo no muestran cookies, variables ni tokens de sesión.
  - Al ingresar, el panel muestra únicamente los módulos asignados al rol: Matrículas y Expediente Documental.
- **Texto de locución (Audio en español):**
  > "Para esta demostración utilizaremos un entorno controlado de pruebas de aseguramiento de la calidad, con credenciales y cuentas estrictamente ficticias. Iniciamos sesión con la cuenta de secretaría técnica documental. Nótese que el sistema no revela contraseñas, tokens de sesión ni parámetros sensibles en pantalla. Una vez autenticados, el menú lateral despliega únicamente las opciones autorizadas para este perfil: Gestión de Matrículas y Expediente Documental."

---

### Escena 3: Carga de documento PDF sintético válido
- **Duración de locución:** 00:38 (38.45 s)
- **Audio TTS:** `escena-03.mp3` (`860187d103dd7d31a956a558df051d3f29f8bcfafb6d95f05091eaf1e3a0446a`)
- **Acción visual en pantalla:**
  - En la lista de estudiantes, se localiza a la estudiante ficticia: **Ana Demo Sintética** (`QA-DOC-001`).
  - Se abre la ventana flotante *Expediente documental*.
  - En la lista de requisitos, el documento aparece inicialmente como `Pendiente`.
  - Se hace clic en el botón *Adjuntar respaldo*.
  - En el selector de archivos se escoge `constancia-demo.pdf`.
  - Se presiona *Adjuntar archivo*.
- **Texto de locución (Audio en español):**
  > "Ingresamos al expediente de la estudiante de prueba, Ana Demo Sintética, identificada con el código de control QA-DOC-001. En la pestaña de Requisitos y Respaldo Documental, seleccionamos la opción 'Adjuntar respaldo'. Para esta operación, seleccionamos el archivo sintético 'constancia-demo.pdf'. Este documento contiene únicamente datos ficticios de prueba. Al presionar 'Adjuntar archivo', el sistema recibe el flujo de datos para su procesamiento inmediato."

---

### Escena 4: Validación y resultado exitoso
- **Duración de locución:** 00:37 (37.15 s)
- **Audio TTS:** `escena-04.mp3` (`35eb5ff3f34770c6044bc1c9eea4f4c99d8170b337565c487e157d3e63a9cfea`)
- **Acción visual en pantalla:**
  - El sistema muestra un indicador de carga y una notificación de éxito: *"Archivo adjunto registrado correctamente"*.
  - El estado del requisito cambia de `Pendiente` a `Entregado` con badge de color verde.
  - El panel superior actualiza el banner de elegibilidad: *"Esta matrícula puede emitir documentos oficiales"*.
- **Texto de locución (Audio en español):**
  > "El backend de SIGA-INEBI ejecuta de inmediato las validaciones de seguridad: verifica la firma MIME real del archivo, calcula su suma de verificación criptográfica SHA-256 para garantizar inmutabilidad, y almacena el binario en el sistema de almacenamiento externo, manteniendo la base de datos libre de archivos pesados. Como observamos en pantalla, el sistema confirma la carga exitosa y actualiza el estado del requisito a 'Entregado'."

---

### Escena 5: Consulta del documento y su historial
- **Duración de locución:** 00:34 (34.54 s)
- **Audio TTS:** `escena-05.mp3` (`b112050b288ea84bba6a288567bdd6f6b6ba85fc14055fb7fa47220b837e8a8c`)
- **Acción visual en pantalla:**
  - Enfoque sobre la tabla inferior *Archivos adjuntos e historial*.
  - Se observan las columnas: Archivo (`constancia-demo.pdf`), Versión (`v1`), Estado (`Vigente`) y Fecha de registro.
  - Se explica cómo las nuevas versiones no sobreescriben ni borran el archivo original.
- **Texto de locución (Audio en español):**
  > "En la tabla de archivos adjuntos podemos consultar el registro generado. Vemos el nombre del archivo, su número de versión uno y su estado como 'Vigente'. Si en el futuro se adjunta una actualización o reemplazo del documento, el sistema no sobrescribe físicamente el archivo anterior; en su lugar, incrementa la versión a versión dos y marca la versión previa como histórica, garantizando la trazabilidad histórica completa del expediente de la estudiante."

---

### Escena 6: Descarga autorizada sin enseñar tokens ni URLs internas
- **Duración de locución:** 00:31 (31.44 s)
- **Audio TTS:** `escena-06.mp3` (`9a3f7481a87745f607f823f60bc34a68de7b10a43ca92bc853f5a25c177937d3`)
- **Acción visual en pantalla:**
  - Clic en el botón o enlace de descarga junto al documento `constancia-demo.pdf`.
  - La descarga inicia inmediatamente a través del navegador.
  - Se verifica que la barra de descargas recibe el archivo con su nombre legítimo.
  - En ningún momento la barra de direcciones o la interfaz revelan claves pre-firmadas de S3, rutas locales `C:\...` ni cookies sensibles.
- **Texto de locución (Audio en español):**
  > "Procedemos a realizar la descarga autorizada del documento. Al presionar el botón de descarga, el servidor valida los permisos del rol y transmite el archivo directamente mediante un flujo seguro. Observen que en ningún momento se exponen en la interfaz cookies de autenticación, tokens temporales ni rutas físicas de los servidores o almacenamiento interno. La transferencia se completa de forma transparente y segura."

---

### Escena 7: Intento de cargar archivo inválido o excedido y rechazo
- **Duración de locución:** 00:39 (39.26 s)
- **Audio TTS:** `escena-07.mp3` (`8e02ec0562ae50bb451df45309fd1244869c57a96f6a2c756ce2ca2ea6b139a5`)
- **Acción visual en pantalla:**
  - Se abre nuevamente el modal de adjuntar respaldo.
  - Se intenta seleccionar `archivo-invalido.exe`. El sistema bloquea el envío y muestra alerta de error: *"Extensión o tipo de archivo no permitido. Solo se admiten formatos PDF e imágenes (.pdf, .jpg, .jpeg, .png)"*.
  - A continuación, se intenta subir `archivo-excedido.pdf` (11 MB).
  - El sistema muestra una alerta de rechazo: *"El archivo supera el tamaño máximo permitido por la institución"*.
- **Texto de locución (Audio en español):**
  > "Demostremos ahora los mecanismos de defensa y rechazo del sistema. Intentamos primero adjuntar un archivo ejecutable, 'archivo-invalido.exe'. El sistema rechaza inmediatamente la carga con un error claro: 'Tipo de archivo no permitido; únicamente se admiten formatos PDF e imágenes autorizadas'. De igual forma, si intentamos adjuntar 'archivo-excedido.pdf', cuyo tamaño supera la cuota máxima permitida, el sistema bloquea la carga antes de consumir recursos del servidor."

---

### Escena 8: Cambio a usuario sin alcance e intento de consulta ajena
- **Duración de locución:** 00:33 (33.82 s)
- **Audio TTS:** `escena-08.mp3` (`9024a69408517454613fc1cbebcefab80da000e549da4c421bbc98b3ba325f18`)
- **Acción visual en pantalla:**
  - Cierre de sesión de la cuenta de secretaría.
  - Inicio de sesión con una cuenta de prueba sin alcance institucional sobre ese grado (`docente.sin.alcance@inebi.edu.gt`).
  - El usuario intenta ingresar directamente al expediente o descargar el registro mediante el UUID de la matrícula.
  - La pantalla despliega una alerta de denegación: *"403 Prohibido: No tiene alcance asignado para consultar este expediente"*.
- **Texto de locución (Audio en español):**
  > "Ahora cerramos la sesión y cambiamos a un usuario sin alcance sobre este grado o sede institucional. Al intentar consultar o descargar el expediente de la estudiante QA-DOC-001 mediante su identificador, el sistema aplica la política de denegación por defecto. La interfaz muestra un mensaje de acceso no autorizado, denegando completamente la visualización del contenido. Ningún dato sensible es expuesto."

---

### Escena 9: Demostración de que la operación denegada queda auditada
- **Duración de locución:** 00:32 (32.02 s)
- **Audio TTS:** `escena-09.mp3` (`5b2bb115851a962e0084a4431446cd116817d19edd1c2ea8a74aeb4b27897914`)
- **Acción visual en pantalla:**
  - Diagrama o texto explicativo sobre el funcionamiento de la bitácora transversal de SIGA-INEBI.
  - Se enfatiza que tanto las operaciones exitosas como los intentos denegados quedan grabados en tablas de auditoría inmutables (registro transversal append-only).
- **Texto de locución (Audio en español):**
  > "Toda operación sensible en SIGA-INEBI, incluyendo tanto las lecturas como los intentos denegados de acceso, queda registrada de manera inmutable en la bitácora transversal de auditoría. Este registro captura la fecha y hora exacta, la dirección IP de origen, el identificador del usuario, el recurso solicitado y el motivo del rechazo, impidiendo cualquier intento de manipulación no advertida."

---

### Escena 10: Ingreso con rol de auditor autorizado y consulta de bitácora
- **Duración de locución:** 00:36 (36.19 s)
- **Audio TTS:** `escena-10.mp3` (`447ebf0df4f724580d7c2bfbb870802a04da96a076fe422a607672f0877bbd71`)
- **Acción visual en pantalla:**
  - Cierre de sesión y nuevo inicio con la cuenta `auditor.general@inebi.edu.gt`.
  - Acceso al módulo *Bitácora y Eventos de Auditoría* (`/audit/events`).
  - Se filtra por módulo `Documentos`.
  - Se muestran en la grilla los eventos ordenados cronológicamente:
    1. Evento de carga exitosa: usuario `secretaria.qa`, recurso `QA-DOC-001`, acción `DOCUMENT_UPLOAD`, resultado `SUCCESS (201)`.
    2. Evento de intento denegado: usuario `docente.sin.alcance`, acción `DOCUMENT_READ`, resultado `DENIED_SCOPE (403)`.
  - Se despliega el detalle con marca de tiempo, dirección IP de origen y hash.
- **Texto de locución (Audio en español):**
  > "Iniciamos sesión ahora con una cuenta que posee el rol de Auditor Institucional. Ingresamos al módulo de Bitácora y Eventos de Auditoría. Aquí podemos filtrar por tipo de evento documental y revisar la bitácora en tiempo real. En pantalla observamos el evento registrado: la carga exitosa realizada por secretaría y, justo después, el evento de acceso denegado generado por el usuario sin alcance, con su respectivo código de estado y sello temporal verificado."

---

### Escena 11: Cierre explicando resultado y siguientes pasos
- **Duración de locución:** 00:33 (33.12 s)
- **Audio TTS:** `escena-11.mp3` (`bd6e59e08b6593dc5f7f9d3469c7feebdb903e2c69fb9c8943434e611bc877c8`)
- **Acción visual en pantalla:**
  - Pantalla de resumen final con viñetas de validación:
    - [x] Carga de documento PDF sintético.
    - [x] Versionado inmutable e integridad criptográfica.
    - [x] Descarga segura sin tokens expuestos.
    - [x] Bloqueo de archivos maliciosos y excedidos.
    - [x] Menor privilegio y auditoría de accesos denegados.
  - Créditos institucionales y cierre: enlace al siguiente módulo de Evaluación y Asistencia.
- **Texto de locución (Audio en español):**
  > "Con esto concluimos la demostración del ciclo de documentos y auditoría en SIGA-INEBI. Hemos comprobado la carga válida, el versionado inmutable, la descarga segura sin fuga de credenciales, el bloqueo de archivos no autorizados y la trazabilidad integral en la bitácora. Para consultar otros flujos como evaluación o asistencia, continúe con los siguientes módulos de este manual audiovisual. Muchas gracias."

---

## 3. Catálogo de archivos de audio generados

Los audios han sido sintetizados en español neutro latinoamericano con locución clara y cadencia adecuada para sincronización de pantalla:

| Escena | Archivo | Duración | Tamaño | SHA-256 |
| :--- | :--- | :--- | :--- | :--- |
| **01** | [`escena-01.mp3`](locucion-documentos-auditoria/escena-01.mp3) | 00:43 | 345,024 bytes | `fb305b5ffa3ed7115c1416c0f9cef99e5012b463ac373efee45a6ec2b30d942f` |
| **02** | [`escena-02.mp3`](locucion-documentos-auditoria/escena-02.mp3) | 00:35 | 283,968 bytes | `0cd9918df3b73bbac020bb2e0e4ffef01e0ea54f88184de3c5ed0426535be6ef` |
| **03** | [`escena-03.mp3`](locucion-documentos-auditoria/escena-03.mp3) | 00:38 | 307,584 bytes | `860187d103dd7d31a956a558df051d3f29f8bcfafb6d95f05091eaf1e3a0446a` |
| **04** | [`escena-04.mp3`](locucion-documentos-auditoria/escena-04.mp3) | 00:37 | 297,216 bytes | `35eb5ff3f34770c6044bc1c9eea4f4c99d8170b337565c487e157d3e63a9cfea` |
| **05** | [`escena-05.mp3`](locucion-documentos-auditoria/escena-05.mp3) | 00:34 | 276,288 bytes | `b112050b288ea84bba6a288567bdd6f6b6ba85fc14055fb7fa47220b837e8a8c` |
| **06** | [`escena-06.mp3`](locucion-documentos-auditoria/escena-06.mp3) | 00:31 | 251,520 bytes | `9a3f7481a87745f607f823f60bc34a68de7b10a43ca92bc853f5a25c177937d3` |
| **07** | [`escena-07.mp3`](locucion-documentos-auditoria/escena-07.mp3) | 00:39 | 314,112 bytes | `8e02ec0562ae50bb451df45309fd1244869c57a96f6a2c756ce2ca2ea6b139a5` |
| **08** | [`escena-08.mp3`](locucion-documentos-auditoria/escena-08.mp3) | 00:33 | 270,528 bytes | `9024a69408517454613fc1cbebcefab80da000e549da4c421bbc98b3ba325f18` |
| **09** | [`escena-09.mp3`](locucion-documentos-auditoria/escena-09.mp3) | 00:32 | 256,128 bytes | `5b2bb115851a962e0084a4431446cd116817d19edd1c2ea8a74aeb4b27897914` |
| **10** | [`escena-10.mp3`](locucion-documentos-auditoria/escena-10.mp3) | 00:36 | 289,536 bytes | `447ebf0df4f724580d7c2bfbb870802a04da96a076fe422a607672f0877bbd71` |
| **11** | [`escena-11.mp3`](locucion-documentos-auditoria/escena-11.mp3) | 00:33 | 264,960 bytes | `bd6e59e08b6593dc5f7f9d3469c7feebdb903e2c69fb9c8943434e611bc877c8` |
| **Pista Maestra** | [`audio-completo-documentos-auditoria.mp3`](locucion-documentos-auditoria/audio-completo-documentos-auditoria.mp3) | **06:34** | 3,156,864 bytes | `c06d98b300361fee4ec0fb89650e3cd50f8693f2cea265488905288938cfd201` |

---

## 4. Recursos sintéticos de demostración generados

Todos los recursos se encuentran disponibles en `docs/manuals/recursos-demostracion/`:

1. **`constancia-demo.pdf`**
   - Propósito: Archivo sintético válido para carga de expediente.
   - Tamaño: 2,429 bytes.
   - SHA-256: `703150b63c84d77ffa1ee12c14644152e8a529c44a127db3cc02d389ddeb2a5a`
2. **`archivo-invalido.exe`**
   - Propósito: Demostración de rechazo de tipo MIME / ejecutable.
   - Tamaño: 101 bytes.
   - SHA-256: `f06cbc6efe8877e5117fa2f9fa4c59d2e359fed10b922d3dcdd4edd1f18a4a3c`
3. **`archivo-excedido.pdf`**
   - Propósito: Demostración de rechazo por tamaño superior a cuota máxima institucional (~11 MB).
   - Tamaño: 11,534,401 bytes.
   - SHA-256: `e2f6b09ae10bafecfadebc24279a8ee8dd19aa4c3efaaf9dd4bece9914472f64`
4. **`documento-alterado.pdf`**
   - Propósito: Demostración de detección de alteración de integridad por divergencia de hash.
   - Tamaño: 2,468 bytes.
   - SHA-256: `654f7eb47d9b16a6109654a2d850eb46e6bcb90344d89a5a3e743d524da0f486`

---

## 5. Instrucciones de grabación y checklist de seguridad

Para el operador de captura (utilizando OBS Studio, Clipchamp o Loom):

### Antes de grabar:
- [x] Confirmar que la versión en ejecución corresponde al SHA `19f9312620247da85c1aa92fd6a0030031b43da7`.
- [x] Verificar que el entorno apunte a la base de datos de pruebas (QA local / staging), nunca a producción.
- [x] Cerrar ventanas de correo, mensajería y pestañas ajenas al sistema.
- [x] Desactivar gestores de contraseñas, autocompletado del navegador y notificaciones emergentes del sistema operativo.
- [x] Verificar que la resolución del monitor esté configurada en 1920x1080 (16:9).
- [x] Probar los primeros 15 segundos para confirmar que la pista de audio (`escena-01.mp3` o el micrófono) esté balanceada con la captura de pantalla.

### Reglas estrictas de privacidad durante la grabación:
- **No mostrar contraseñas** en texto plano.
- **No inspeccionar cookies** de sesión ni cabeceras en herramientas de desarrollo.
- **No enseñar tokens temporales** ni URLs internas de almacenamiento de archivos.
- **No usar nombres reales de estudiantes**, números de DPI reales ni información personal clasificada.
- **No mostrar variables de entorno**, secretos `.env` ni cadenas de conexión a base de datos.
- **No enseñar respaldos físicos ni rutas de directorios del servidor**.
