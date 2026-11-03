# File Storage Strategy

## Principios

- No guardar binarios en base de datos.
- Base de datos guarda metadatos, integridad, vinculos y estados.
- Descargas seguras con token breve ligado al portador.
- Verificacion periodica de integridad.

## Componentes

- `FileObject`: referencia a archivo fisico, hash, tamano, tipo MIME, fecha de carga.
- `DocumentRecord`: relacion funcional con expediente o proceso.
- `DocumentVersion`: versionado cuando requerimiento lo pida.
- `DownloadToken`: acceso breve y auditable.

## Reglas operativas

- Tipos permitidos por catalogo.
- Limite de tamano configurable.
- Normalizacion de imagenes cuando aplique.
- Retencion y no eliminacion segun dominio y decision futura.
- Backups de archivos separados de backups DB: dos artefactos, dos manifiestos y dos
  pares de scripts, cada pila restaurable por su cuenta (RNF-RES-001). Ver
  `docs/architecture/backup-and-recovery.md`.

## Procesamiento de imagenes (RF-ARC-002)

Las imagenes adjuntas se normalizan antes de guardarse. El mecanismo vive una
sola vez en `backend/apps/common/images.py` (Pillow) y lo usan todos los puntos
de carga que reciben imagenes:

| Punto de carga | Entrada | Resultado |
| --- | --- | --- |
| Respaldo de justificacion (`attendance.attach_justification_document`) | PDF, JPG, PNG | Imagen normalizada en su formato declarado; PDF intacto |
| Expediente documental (`documents.upload_document_record`, `replace_document_record`, `register_scanned_document`) | PDF, JPG, PNG | Igual que el anterior |
| Fotografia del estudiante (`students.normalize_student_photo`) | Imagen | Recorte de carne 295x354 en JPEG; decodificacion y orientacion compartidas |

Reglas para JPEG y PNG (`normalize_image_payload`, invocada desde
`documents.services.read_document_payload`):

- Se aplica la orientacion EXIF a los pixeles y luego se descarta.
- Se eliminan EXIF, GPS, XMP, comentarios y bloques de texto. Las fotos llegan
  desde telefonos de encargados de menores y la ubicacion no debe almacenarse.
  Solo se conservan la transparencia de paleta y el perfil de color.
- El lado mayor se limita a `IMAGE_UPLOAD_MAX_DIMENSION_PX` (2048 por defecto,
  sin ampliar imagenes pequenas).
- JPEG se recomprime con calidad `IMAGE_UPLOAD_JPEG_QUALITY` (85 por defecto);
  PNG se reescribe sin perdida con optimizacion. El formato guardado es el
  declarado por la extension, asi extension, `content_type` y bytes coinciden.
- Una imagen que no se puede decodificar se rechaza con `DomainError`
  ("La imagen adjunta esta danada o no es una imagen valida.").
- PDF y cualquier otro tipo pasan sin cambios.

El limite `DOCUMENT_MAX_UPLOAD_SIZE_BYTES` se valida sobre el archivo recibido.
El checksum SHA-256 y `size_bytes` se calculan sobre el binario final almacenado,
de modo que la verificacion de integridad (RF-ARC-003) compara contra lo que
realmente esta en el almacenamiento. Los dos limites de imagen son parametros
operativos de entorno (`backend/config/settings/base.py`), igual que el resto de
los descritos en `docs/architecture/configuration-catalogues.md`.

La foto de docente (`teachers.Teacher.photo`) se escribe hoy por el serializador
del modelo, sin servicio de dominio, y queda fuera de esta normalizacion: debe
encauzarse por un servicio antes de aplicarle estas reglas.

## Nombres de fotografias de perfil

Las nuevas fotografias de perfil se almacenan con un nombre generado por el
sistema, no con el nombre enviado por el dispositivo del usuario:

- estudiante: `student_photos/foto_estudiante_<codigo>_<unico>.jpg`;
- docente: `teacher_photos/foto_docente_<codigo>_<unico>.<extension>`.

El codigo institucional indica el propietario sin publicar nombre, CUI u otro
dato personal. El sufijo aleatorio evita colisiones y permite conservar archivos
anteriores. Esta regla aplica a cargas nuevas y reemplazos; no mueve archivos
historicos porque sus rutas ya pueden estar referenciadas por base de datos,
backups o almacenamiento externo.

## Riesgos a evitar

- URLs directas permanentes.
- Guardar archivos en tablas.
- Exponer nombres sensibles en rutas publicas.
- Falta de checksum o verificacion.
