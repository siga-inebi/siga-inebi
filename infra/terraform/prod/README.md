# Producción en Google Cloud

Configuración para el proyecto **existente** `precise-blend-428821-e0`, región `us-central1`. No crea proyectos ni vincula facturación. Los valores iniciales preparan infraestructura; `deploy_jobs` y `deploy_service` están desactivados hasta disponer de imágenes reales fijadas por digest. El presupuesto mensual queda pendiente: `monthly_budget_usd = null` no crea alertas.

Diferencias deliberadas con QA (`../qa`): **no existe job de siembra ni datos de demostración** — la base de producción queda vacía (solo esquema, vía migraciones) y la institución la llena. El único dato que se provisiona es el superusuario inicial, mediante el job `siga-inebi-prod-createadmin` (comando `create_initial_admin`: crea persona, cuenta y rol `system-administrator` con todo el catálogo atómico; correo en `admin_email`). El despliegue continuo se dispara desde `main`, no desde `develop`.

## Recursos y límites

- Un servicio Cloud Run con Nginx/React en 8080 y Django/Gunicorn en 8081, mismo origen HTTPS y arranque del backend antes del frontend. Concurrencia 8, mínimo 0 y máximo 1 instancia. Perfil total de **2 CPU y 2.125 GiB** (backend 1 CPU/2 GiB; frontend 1 CPU/128 MiB).
- PostgreSQL 16, Cloud SQL Enterprise `db-f1-micro`, una zona, HDD 10 GB, sin ampliación automática. Usa IP pública sin redes cliente autorizadas y el conector autenticado de Cloud SQL montado en `/cloudsql`; no se ofrece acceso público directo a PostgreSQL. Backups diarios a las 07:00 UTC, 3 copias retenidas, sin recuperación puntual. **Pendiente antes de operar con datos reales:** definir la política institucional de respaldo y RPO/RTO; producción debería valorar recuperación puntual (`point_in_time_recovery_enabled`), más copias retenidas y un tipo de instancia con SLA.
- Bucket de archivos privado, acceso uniforme, prohibición de acceso público, versiones de objetos y sin borrado forzado. Versionar objetos conserva historia, pero no demuestra por sí solo un respaldo independiente ni una restauración verificable.
- Tres secretos (base, Django y contraseña del admin inicial), generados por Terraform. Los valores se conservan en el **estado sensible**; nunca se imprimen ni se exportan como outputs. Cloud Run consume versiones fijas. `ADMIN_PASSWORD` solo llega al job `createadmin`: ni la web ni el job de migraciones lo reciben.
- Repositorio de imágenes Docker con limpieza automática: conserva siempre las 10 versiones más recientes de cada imagen y borra las que superan 7 días de antigüedad. Verificar que la revisión activa no quede fuera de esa ventana antes de confiar en una reversión antigua.
- Exclusión de logging para entradas de solicitud de Cloud Run con `token=` en la URL (descargas firmadas).
- Cuenta de servicio sin llaves descargables: conexión SQL, acceso a esos secretos, objetos del bucket y firma sobre su propia cuenta, con concesiones específicas. El job no tiene IAM público. La web permite invocación pública para presentar la pantalla de login; la autorización de Django protege los datos.

## Preparación y comprobaciones

Se requieren Terraform ≥1.9, credenciales Google del operador, permisos para los recursos e IAM declarados y facturación habilitada. El estado remoto requiere un bucket **privado independiente** revisado y creado previamente por el operador, con acceso restringido, versiones y cifrado de Google. No almacenar estado en el bucket de medios. La creación del bucket de estado no forma parte de este módulo y debe revisarse antes de efectuarla.

```bash
terraform -chdir=infra/terraform/prod init -backend=false
terraform -chdir=infra/terraform/prod fmt -check
terraform -chdir=infra/terraform/prod validate
```

Requisito previo, una sola vez por proyecto: `gcloud services enable serviceusage.googleapis.com cloudresourcemanager.googleapis.com --project=PROJECT_ID`. Terraform necesita Service Usage para activar las demás APIs y Resource Manager para leer el proyecto del presupuesto; ninguna de las dos puede activarse desde el mismo plan.

Copiar `terraform.tfvars.example` a `terraform.tfvars` y `backend.hcl.example` a `backend.hcl`, completar el bucket **real** de estado, después inicializar con `terraform init -backend-config=backend.hcl`. Las credenciales se obtienen por ADC o credenciales del proceso, nunca desde un archivo dentro del repositorio. No incluir planes binarios, estado, variables privadas, `.terraform/` ni claves en Git. Un plan puede contener datos sensibles aunque la salida humana los oculte.

## Secuencia de despliegue tras revisar y aprobar el plan

1. Revisar `terraform plan` con ambos flags en `false`, incluyendo los costos de SQL, almacenamiento, backups, imágenes y logs. Aplicar solo el plan aprobado. Activar APIs puede tardar; los recursos dependen explícitamente de su habilitación.
2. Construir los targets `backend` y `frontend` de `Dockerfile.cloud`, subirlos al repositorio indicado por `image_repository` y registrar sus digests junto al SHA y pruebas de la versión. No usar etiquetas flotantes ni imágenes de ejemplo para desplegar.
3. Configurar `backend_image` real, `admin_email` real y `deploy_jobs = true`, mantener `deploy_service = false`, revisar y aplicar ese plan. Ejecutar `siga-inebi-prod-migrate` y verificar éxito: la base queda con el esquema y **sin datos**. Ejecutar después `siga-inebi-prod-createadmin` **una sola vez** y verificar éxito: crea únicamente el superusuario inicial. Terraform crea los jobs pero **no los ejecuta**. No migrar automáticamente al arrancar la web.
4. Configurar `frontend_image` real y `deploy_service = true` después de ambos jobs, revisar y aplicar el plan. Verificar health, login del superusuario, permisos, carga de archivo privado, recuperación por URL firmada y QR desde Android con HTTPS. Guardar evidencias reales y registrar el URL de `service_url`.

Los jobs se ejecutan de forma explícita con `gcloud run jobs execute JOB --region=us-central1 --project=precise-blend-428821-e0 --wait`. Si fallan, la web permanece desactivada; conservar los logs sin secretos y corregir antes de habilitar tráfico. No existe una dependencia Terraform que certifique que esos comandos terminaron con éxito: la habilitación de la web es un paso operativo deliberado.

Entrega de la contraseña inicial: se lee **una sola vez** con `gcloud secrets versions access latest --secret=siga-inebi-prod-admin-password`, se envía a la institución por un canal acordado y se instruye cambiarla en el primer ingreso. «Una sola vez» es un procedimiento, no una garantía técnica: el valor persiste en Secret Manager y en el estado de Terraform, ambos de acceso restringido; si la institución no la cambia, rotarla editando el secreto fuera de banda y reejecutando `createadmin` (el comando es idempotente: restablece la clave sin borrar la cuenta ni su historial auditable).

## Despliegue continuo desde GitHub Actions

Tras la puesta en marcha inicial, `.github/workflows/deploy-prod.yml` (CI/CD producción) despliega en cada push a `main`. Replica el flujo de QA (`deploy-qa.yml`): el job `plan` compara el commit con el que corre producción, el `gate` acepta la corrida de CI del PR fusionado hacia `main` (o ci.yml completo como respaldo), se construyen solo las imágenes que cambiaron, se actualiza la imagen de `siga-inebi-prod-migrate` y de `siga-inebi-prod-createadmin` (el flujo **nunca ejecuta** este último), se ejecuta la migración con `--wait` cuando corresponde y se actualiza el servicio con ambos digests. Cierra con una comprobación de `/api/v1/health/database/` y un resumen del job. Las ejecuciones se encolan (`concurrency: deploy-prod`).

Autenticación sin llaves ni secretos de GitHub, mediante Workload Identity Federation (`deploy.tf`):

- Pool `siga-inebi-prod-github` y proveedor OIDC `github-actions` (`https://token.actions.githubusercontent.com`). La condición de confianza exige `assertion.repository == github_repository` **y** `assertion.ref == refs/heads/<deploy_branch>` (por defecto `siga-inebi/siga-inebi` y `main`). Las PR, otras ramas y los forks no obtienen credenciales.
- Cuenta `siga-inebi-prod-deployer`, suplantable solo desde ese repositorio. Permisos mínimos: `roles/artifactregistry.writer` sobre el repositorio de imágenes; `roles/run.developer` a nivel de proyecto (gcloud espera operaciones de Cloud Run con alcance de proyecto); `roles/iam.serviceAccountUser` únicamente sobre la cuenta runtime. Sin acceso a secretos, al bucket de estado Terraform ni a la administración de Cloud SQL.
- El proveedor y la cuenta aparecen como valores literales en el workflow; no son secretos y provienen de los outputs `github_workload_identity_provider` y `github_deployer_service_account`.

Terraform **ignora los cambios de imagen** del servicio y del job (`lifecycle.ignore_changes`), además de `client`/`client_version` que escribe gcloud y los montajes de volumen. `backend_image` y `frontend_image` quedan como imágenes iniciales; una vez activado el flujo, las actualizaciones de imagen pasan por GitHub Actions y Terraform conserva el resto de la configuración.

Orden de puesta en marcha: revisar y aplicar con `terraform apply` el plan que crea el pool, el proveedor, la cuenta deployer y sus permisos **antes** de fusionar el workflow en `main`; de lo contrario la primera ejecución falla al autenticarse. Confirmar que los valores literales del workflow coinciden con los outputs.

Reversión: volver a ejecutar el workflow no sirve para desplegar un commit anterior, porque siempre construye la cabeza de `main`. Para regresar a una revisión previa del servicio:

```bash
gcloud run revisions list --service=siga-inebi-prod --region=us-central1 --project=precise-blend-428821-e0
gcloud run services update-traffic siga-inebi-prod --to-revisions=REVISION=100 --region=us-central1 --project=precise-blend-428821-e0
```

La migración ya aplicada no se revierte con el tráfico; evaluar compatibilidad del esquema antes de regresar. Mientras el tráfico esté fijado, las revisiones nuevas no lo reciben; el workflow ejecuta `update-traffic --to-latest` después de cada despliegue para devolverlo a la revisión nueva.

Control de acceso: quien puede fusionar en `main` puede desplegar en producción. Como medida opcional, un *environment* de GitHub con revisores obligatorios añade una aprobación manual; requiere permisos de administración del repositorio y ajustar la condición de confianza (el `sub` del token cambia a `repo:...:environment:...`, aunque `repository` y `ref` se mantienen).

## Cambio de proyecto (traslado a infraestructura institucional)

El módulo nunca crea proyectos; para mover producción a un proyecto de la institución basta:

1. Obtener el `project_id` nuevo con facturación habilitada y permisos de operador.
2. Crear el bucket privado de estado en ese proyecto y actualizar `backend.hcl`.
3. Cambiar `project_id` (y la cuenta de facturación) en `terraform.tfvars` y aplicar la secuencia de despliegue completa.
4. Actualizar el bloque `env` de `.github/workflows/deploy-prod.yml` (`PROJECT_ID`, `REGISTRY`, `WIF_PROVIDER`, `DEPLOYER_SA`) con los outputs del nuevo proyecto.
5. Migrar los datos (respaldos de Cloud SQL y objetos del bucket de medios) por procedimiento aparte; este módulo no copia datos.

## Costos, alertas y retiro

Cloud SQL factura mientras la instancia existe aunque Cloud Run escale a cero. Para `us-central1`, el precio de referencia `db-f1-micro` es aproximadamente **USD 0.0105/h ≈ 7.67/730 h de cómputo**, más disco HDD, backups y otros consumos; confirmar el importe vigente en [precios oficiales de Cloud SQL](https://cloud.google.com/sql/pricing) y la calculadora antes de aplicar. El tipo compartido no incluye la garantía SLA de los tipos dedicados. [Cloud Run](https://cloud.google.com/run/pricing), [Storage](https://cloud.google.com/storage/pricing), Artifact Registry, Secret Manager y logs pueden añadir cargos.

El presupuesto opcional usa la cuenta de facturación existente y alertas al 50 %, 90 % y 100 % con los destinatarios de facturación predeterminados. Una alerta **no corta el gasto**. Definir importe y permisos de Billing Budgets antes de activarlo. El filtro cubre el proyecto, por lo que incluirá cualquier otro recurso presente allí (incluido QA, mientras compartan proyecto).

SQL tiene protección contra borrado en Terraform y en el servicio; Cloud Run y el job también están protegidos. Un bucket no vacío no se elimina. El retiro requiere una decisión posterior que conserve respaldos, versiones y evidencia, revise el estado y desactive protecciones explícitamente; no usar `terraform destroy` como limpieza.

Referencias: [servicio Cloud Run v2 en Terraform](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloud_run_v2_service), [contrato de contenedores](https://cloud.google.com/run/docs/container-contract), [secretos Cloud Run](https://cloud.google.com/run/docs/configuring/services/secrets), [CPU Cloud Run](https://cloud.google.com/run/docs/configuring/services/cpu).
