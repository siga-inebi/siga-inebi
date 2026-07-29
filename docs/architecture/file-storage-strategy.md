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
- Backups de archivos separados de backups DB.

## Riesgos a evitar

- URLs directas permanentes.
- Guardar archivos en tablas.
- Exponer nombres sensibles en rutas publicas.
- Falta de checksum o verificacion.
