# Instrucciones: Manual de Instalacion y Configuracion

## Objetivo

Permita que una persona tecnica prepare SIGA-INEBI de forma reproducible sin
necesitar conocimiento previo del equipo ni acceso a secretos de produccion.

## Audiencia

Desarrolladores, personal de pruebas y responsables tecnicos de ambientes.

## Contenido obligatorio

### Requisitos previos

- Declare versiones compatibles de Git, Docker, Docker Compose, Python, Node.js
  y PostgreSQL cuando se ejecute fuera de Docker.
- Indique los recursos minimos de equipo y puertos utilizados.

### Instalacion

1. Clonar el repositorio.
2. Revisar `AGENTS.md` y `docs/development/onboarding.md`.
3. Crear archivos locales desde `.env.example` sin versionarlos.
4. Levantar el sistema mediante Docker Compose como camino recomendado.
5. Ejecutar migraciones, catalogos o datos demo solo cuando el script oficial lo
   indique.
6. Verificar frontend, backend y base de datos mediante los comandos disponibles.

### Configuracion

- Explique cada grupo de variables por finalidad, no por valores secretos.
- Diferencie configuracion de desarrollo, pruebas y produccion.
- Indique que PostgreSQL es obligatorio para pruebas y validacion final.
- Describa el uso limitado de SQLite, si sigue habilitado, solo para desarrollo
  rapido y nunca como sustituto de la validacion con PostgreSQL.

### Ejecucion local y validacion

- Documente la alternativa sin Docker solo si esta soportada en el repositorio.
- Incluya comandos para lint, pruebas, build, migraciones y verificaciones de
  Docker.
- Indique las URLs locales, cuentas demo y mecanismo de carga inicial cuando
  existan. Nunca publique contrasenas reales.

### Diagnostico

Incluya soluciones verificadas para puertos ocupados, contenedores detenidos,
migraciones pendientes, dependencias faltantes, base de datos no disponible y
variables mal configuradas. Enlace `docs/development/troubleshooting.md` cuando
sea la fuente canonica.

## Criterios de cierre

- Una persona sin conocimiento previo debe poder levantar el ambiente siguiendo
  exclusivamente el manual.
- Todos los comandos deben ejecutarse contra una copia limpia del repositorio.
- No incluya secretos, respaldos, datos reales ni archivos `.env`.
