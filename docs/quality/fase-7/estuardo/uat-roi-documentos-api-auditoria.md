# UAT parcial â€” documentos, API y auditorÃ­a de RoÃ­

**Ejecutor:** Estuardo, usando su cuenta QA de GestiÃ³n documental con alcance institucional QA.
**Candidato indicado:** PR [#591](https://github.com/siga-inebi/siga-inebi/pull/591), rama `docs/roi-phase7-closeout`, SHA de PR `19f9312620247da85c1aa92fd6a0030031b43da7`.
**Estado de despliegue:** Estuardo confirmÃ³ que QA servÃ­a el candidato, pero el SHA/revisiÃ³n exacto observado en el entorno no quedÃ³ anotado; la relaciÃ³n entre despliegue y SHA debe confirmarse antes de atribuir todos los resultados a esa revisiÃ³n.
**Datos:** los escenarios se probaron con registros/archivos sintÃ©ticos. No incluir credenciales, cookies, tokens ni cuerpos de respuesta con datos personales.

## Resultados por escenario

| ID | Escenario | Estado | Evidencia comunicada por el ejecutor / paso necesario |
| --- | --- | --- | --- |
| UAT-ROI-DOC-01 | Consulta autorizada | **Aprobado** | La vista â€œExpediente documentalâ€ abriÃ³ y cargÃ³ la tabla; no se adjuntÃ³ captura ni cÃ³digo HTTP. |
| UAT-ROI-DOC-02 | Consulta denegada | **Bloqueado** | Estuardo dispone de una sola cuenta con permiso documental. Se necesita un perfil QA sin permiso o un registro fuera de alcance autorizado para probar la denegaciÃ³n. |
| UAT-ROI-DOC-03 | Carga vÃ¡lida | **Observado** | El documento aparece como â€œVigenteâ€; falta confirmar nÃºmero de versiÃ³n y metadatos/checksum observados. |
| UAT-ROI-DOC-04 | Carga invÃ¡lida | **Aprobado** | El archivo `.txt` fue rechazado, segÃºn correcciÃ³n del ejecutor. No se identificÃ³ si el rechazo fue del selector, cliente o servidor ni se aportÃ³ evidencia adjunta. |
| UAT-ROI-DOC-05 | Descarga con token vÃ¡lido | **Bloqueado** | El manual no identifica el flujo aprobado para emitir el token. |
| UAT-ROI-DOC-06 | Descarga con token expirado | **Bloqueado** | Depende del flujo QA de emisiÃ³n/expiraciÃ³n del token, aÃºn no identificado en el manual. |
| UAT-ROI-DOC-07 | Descarga con token alterado | **Bloqueado** | Depende del flujo QA para obtener un token sintÃ©tico y modificarlo en la solicitud. |
| UAT-ROI-DOC-08 | Reemplazo e historial | **Aprobado** | Estuardo reportÃ³ HTTP 201 y confirmÃ³ que la versiÃ³n anterior se conservÃ³ en el historial. |
| UAT-ROI-DOC-09 | Integridad de archivo intacto | **Aprobado** | Estuardo reportÃ³ HTTP 204 en `POST /api/v1/documents/records/{public_id}/verify/` para el PDF sintÃ©tico intacto. |
| UAT-ROI-DOC-10 | AuditorÃ­a de lectura | **Aprobado** | Estuardo reportÃ³ HTTP 200 y confirmÃ³ un evento reciente `documents.document.read`. |
| UAT-ROI-DOC-11 | AuditorÃ­a de escritura | **Aprobado** | Estuardo confirmÃ³ los eventos `documents.document.uploaded` y `documents.document.version_created` despuÃ©s de las acciones de carga/reemplazo. |
| UAT-ROI-DOC-12 | AuditorÃ­a de denegaciÃ³n | **Bloqueado** | Depende de completar el escenario de consulta denegada y revisar su evento de auditorÃ­a. |

No se adjuntaron capturas ni cuerpos de respuesta. Los estados reflejan lo reportado por el ejecutor y no certifican escenarios bloqueados ni vinculan por sÃ­ solos la sesiÃ³n al SHA servido.

## Cierre de la revisiÃ³n documental

Estuardo registrÃ³ **Requiere cambios** en la revisiÃ³n del PR #591 para `roi-cierre.md` y el Manual 07. Entre los puntos seÃ±alados estÃ¡n la discrepancia del conteo automatizado y la precisiÃ³n del contrato/paginaciÃ³n, ruta histÃ³rica, permisos, respuesta de carga y emisiÃ³n de tokens; tambiÃ©n pidiÃ³ retirar valores con apariencia de datos personales en el ejemplo de `/auth/me/`.

El PR permanece abierto en SHA `19f9312620247da85c1aa92fd6a0030031b43da7`; cuando RoÃ­ suba cambios, Estuardo debe volver a revisar el cierre y el manual. La corrida automatizada de RoÃ­ (116 aprobadas, 23 omitidas) es evidencia distinta de esta UAT manual.
