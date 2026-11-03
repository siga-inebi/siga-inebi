# Instrucciones: Manual Tecnico

## Objetivo

Documente como esta construido, validado y mantenido SIGA-INEBI para que un
equipo tecnico pueda comprender la solucion sin inferir decisiones criticas del
codigo fuente.

## Audiencia

Desarrolladores, revisores tecnicos, responsables de despliegue y evaluadores.

## Fuentes obligatorias

- `AGENTS.md`.
- `docs/architecture/`.
- `docs/decisions/`.
- `docs/development/`.
- `docs/requirements/`.
- Configuracion real del repositorio, Docker, CI y pruebas.

No describa capacidades no implementadas como si fueran reales. Identifique las
decisiones pendientes con su ADR o requisito asociado.

## Contenido obligatorio

### 1. Alcance y arquitectura

- Describa el proposito del sistema y sus limites funcionales.
- Explique el monorepo, el monolito modular y la separacion entre frontend,
  backend, documentacion, scripts y automatizacion.
- Incluya un diagrama de componentes y un diagrama de despliegue actualizados.
- Explique los dominios principales y sus dependencias.

### 2. Tecnologias y decisiones

- Justifique React con Vite, Django REST Framework, PostgreSQL, Docker y GitHub
  Actions conforme a los ADR vigentes.
- Enlace los ADR que regulan monorepo, monolito modular, API, base de datos,
  entornos, autorizacion y trabajos diferidos.

### 3. Backend y API

- Describa la estructura por apps de Django.
- Explique los limites entre vistas, serializadores, consultas y servicios.
- Documente el manejo central de errores y el formato de respuestas.
- Incluya convenciones de API, versionado, autenticacion y errores.

### 4. Frontend

- Describa rutas, proteccion de pantallas, sesion por cookies y consumo de API.
- Explique como se evita guardar tokens en memoria persistente del navegador.
- Identifique componentes o flujos principales por dominio.

### 5. Seguridad y auditoria

- Explique denegacion por defecto, roles multiples, permisos atomicos y scopes.
- Documente cuentas vinculadas a personas, cookies seguras, TLS, auditoria y
  minimizacion de datos.
- Describa como se protegen secretos, archivos y datos sensibles.

### 6. Base de datos y calidad

- Incluya modelo conceptual, logico, fisico y diagrama entidad-relacion final.
- Enlace el diccionario de datos y los scripts finales de base de datos.
- Describa migraciones, pruebas unitarias, integracion, API, frontend y Docker.
- Documente CI, checks, estrategia de ramas, Pull Requests y Definition of Done.

### 7. Operacion tecnica

- Incluya comandos utiles y seguros de instalacion, pruebas, migraciones, Docker,
  lint, build, respaldo y recuperacion.
- Enlace las guias existentes; no copie bloques extensos si la fuente canonica ya
  existe.

## Criterios de cierre

- Todo diagrama debe corresponder al codigo y configuracion actuales.
- Todo comando debe ser reproducible y no requerir secretos impresos.
- Toda afirmacion de seguridad debe citar una implementacion, ADR o configuracion
  verificable.
- Ejecute los comandos de validacion documentados antes de aprobar el manual.
