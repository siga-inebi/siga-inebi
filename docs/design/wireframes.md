# Wireframes

Estructura funcional de las pantallas principales de SIGA-INEBI. Define que
informacion aparece, donde y con que acciones. No define colores, tipografia ni
espaciado: eso corresponde a la fase de diseno visual.

Version navegable: [`prototipo-siga.html`](prototipo-siga.html).
Navegacion y roles: [`navigation-map.md`](navigation-map.md).

## Como leer estos wireframes

| Notacion | Significado |
| --- | --- |
| `[ Texto ]` | Boton o accion |
| `( Texto )` | Campo de entrada |
| `[x]` `[ ]` | Casilla marcada y sin marcar |
| `( o )` | Opcion de seleccion unica |
| `v` | Lista desplegable |
| `<< >>` | Paginacion |
| `# ROL` | Elemento visible solo para los roles indicados |

## Marco comun

Todas las pantallas privadas comparten el mismo marco: barra superior, barra
lateral de modulos recortada por rol y area de contenido. Solo cambia el
contenido.

```text
+---------------------------------------------------------------------------+
| [LOGO] SIGA-INEBI            ( Buscar... )   Ciclo 2026   [Ana L. v]       |
+-------------------+-------------------------------------------------------+
| MODULOS           |  Inicio > Modulo > Detalle                            |
|                   |-------------------------------------------------------|
| > Panel           |                                                       |
| > Estudiantes     |                                                       |
| > Personas        |                  AREA DE CONTENIDO                    |
| > Estructura      |                                                       |
| > Matriculas      |                                                       |
| > Reportes        |                                                       |
| > Usuarios        |                                                       |
|                   |                                                       |
| Rol: Director     |                                                       |
| [ Cerrar sesion ] |                                                       |
+-------------------+-------------------------------------------------------+
```

La barra lateral se genera segun el rol. La matriz completa esta en
[`navigation-map.md`](navigation-map.md#visibilidad-por-rol).

---

## 1. Login

Ruta prototipo `#/login`. Ruta real `/login`. Publica.
Proposito: autenticar a la persona y llevarla a su punto de trabajo.

```text
+---------------------------------------------------------------------------+
|                                                                           |
|                  +--------------------------------------+                 |
|                  |          [ LOGO INEBI ]              |                 |
|                  |            SIGA-INEBI                |                 |
|                  |  Instituto Nacional de Educacion      |                 |
|                  |       Basica de Salcaja               |                 |
|                  |                                      |                 |
|                  |  Usuario                             |                 |
|                  |  (____________________________)      |                 |
|                  |                                      |                 |
|                  |  Contrasena                          |                 |
|                  |  (____________________________) [ojo]|                 |
|                  |                                      |                 |
|                  |  [ ] Mantener sesion iniciada        |                 |
|                  |                                      |                 |
|                  |  [          Ingresar          ]      |                 |
|                  |                                      |                 |
|                  |  Olvido su contrasena?               |                 |
|                  |  Contacte a administracion.          |                 |
|                  +--------------------------------------+                 |
|                                                                           |
|            Uso institucional. Los accesos quedan registrados.             |
+---------------------------------------------------------------------------+
```

Estados de la pantalla:

```text
Credenciales incorrectas          Cuenta bloqueada temporalmente
+---------------------------+     +-------------------------------------+
| ! Usuario o contrasena    |     | ! Cuenta bloqueada por 10 minutos.  |
|   incorrectos.            |     |   Cinco intentos fallidos.          |
|   Intento 2 de 5.         |     |   Contacte a administracion.        |
+---------------------------+     +-------------------------------------+

Sesion expirada
+--------------------------------------------------------------+
| Su sesion expiro. Ingrese de nuevo para continuar donde       |
| estaba: Matriculas > Nueva matricula.                         |
+--------------------------------------------------------------+
```

| Aspecto | Definicion |
| --- | --- |
| Quien la ve | Cualquier persona sin sesion |
| Acciones | Ingresar, mostrar u ocultar contrasena |
| Validacion | Ambos campos obligatorios antes de habilitar `Ingresar` |
| Regla | Cinco intentos fallidos bloquean la cuenta diez minutos |
| Salida | Panel, o la ruta que el usuario intentaba abrir |
| Nota | El mensaje de error no revela si el usuario existe |

---

## 2. Panel

Ruta prototipo `#/app`. Ruta real `/app`.
Proposito: dar contexto del ciclo activo y accesos rapidos a las tareas frecuentes.
Es el nodo de reparto: desde aqui se alcanza cualquier modulo en un clic.

```text
+---------------------------------------------------------------------------+
| Panel                                                                     |
+---------------------------------------------------------------------------+
| Buen dia, Ana Lopez.   Rol: Personal administrativo.  Ciclo 2026 (Abierto) |
+---------------------------------------------------------------------------+
|                                                                           |
|  ACCESOS RAPIDOS                                                          |
|  +-------------------+ +-------------------+ +-------------------+        |
|  | Nueva matricula   | | Buscar estudiante | | Reportes          |        |
|  | [ Abrir ]         | | [ Abrir ]         | | [ Abrir ]         |        |
|  +-------------------+ +-------------------+ +-------------------+        |
|                                                                           |
|  RESUMEN DEL CICLO 2026                                                   |
|  +-------------------+ +-------------------+ +-------------------+        |
|  | Estudiantes       | | Matriculas        | | Secciones         |        |
|  | activos           | | del ciclo         | | abiertas          |        |
|  |       412         | |       398         | |        14         |        |
|  | [ Ver listado ]   | | [ Ver listado ]   | | [ Ver oferta ]    |        |
|  +-------------------+ +-------------------+ +-------------------+        |
|                                                                           |
|  PENDIENTES                                                               |
|  +---------------------------------------------------------------------+  |
|  | - 6 matriculas con requisitos documentales incompletos  [ Revisar ] |  |
|  | - 3 secciones sin docente asignado                      [ Revisar ] |  |
|  | - 2 personas sin cuenta de usuario vinculada            [ Revisar ] |  |
|  +---------------------------------------------------------------------+  |
|                                                                           |
|  ESTADO DEL SISTEMA                                             # ADMIN   |
|  API en linea    Base de datos en linea    Ultima revision 08:12          |
+---------------------------------------------------------------------------+
```

Variante para Docente. El panel muestra su alcance, no el institucional:

```text
+---------------------------------------------------------------------------+
| Panel                                                                     |
+---------------------------------------------------------------------------+
| Buen dia, Carlos Perez.   Rol: Docente.   Ciclo 2026                      |
+---------------------------------------------------------------------------+
|  MIS SECCIONES                                                            |
|  +---------------------------------------------------------------------+  |
|  | Primero Basico "A" | Matematica | 32 estudiantes | [ Ver seccion ]  |  |
|  | Segundo Basico "B" | Matematica | 29 estudiantes | [ Ver seccion ]  |  |
|  +---------------------------------------------------------------------+  |
|                                                                           |
|  No aparecen accesos administrativos porque el rol no los usa.            |
+---------------------------------------------------------------------------+
```

Variante para Encargado o tutor:

```text
+---------------------------------------------------------------------------+
| Mis estudiantes                                                           |
+---------------------------------------------------------------------------+
|  +---------------------------------------------------------------------+  |
|  | Lopez Garcia, Maria Jose   1o Basico "A"   Activa   [ Ver ficha ]   |  |
|  +---------------------------------------------------------------------+  |
|  Consulta unicamente. Para cambios, comuniquese con la institucion.       |
+---------------------------------------------------------------------------+
```

| Aspecto | Definicion |
| --- | --- |
| Quien la ve | Todos los roles, con contenido distinto |
| Acciones | Navegar a los modulos, resolver pendientes |
| Regla | Las tarjetas se arman con datos dentro del alcance del usuario |
| Estado vacio | Sin ciclo activo, muestra aviso y enlace a `Estructura academica` |

---

## 3. Estudiantes

Ruta prototipo `#/estudiantes`. Ruta real `/app/estudiantes`.
Proposito: encontrar un estudiante y llegar a su expediente.

```text
+---------------------------------------------------------------------------+
| Inicio > Estudiantes                                                      |
+---------------------------------------------------------------------------+
| Estudiantes                        [ + Nuevo estudiante ] # ADMIN DIR ADM |
+---------------------------------------------------------------------------+
| ( Buscar por nombre, codigo o documento              )  [ Buscar ]        |
| Ciclo (2026 v)  Grado (Todos v)  Seccion (Todas v)  Estado (Activo v)     |
| [ Limpiar filtros ]                                        [ Exportar ]   |
+---------------------------------------------------------------------------+
| Codigo   | Nombre completo         | Grado      | Seccion | Estado |      |
|----------|-------------------------|------------|---------|--------|------|
| EST-0412 | Lopez Garcia, Maria J.  | 1o Basico  | A       | Activo |[Ver] |
| EST-0413 | Perez Chan, Luis A.     | 1o Basico  | A       | Activo |[Ver] |
| EST-0414 | Ramos Coj, Ana L.       | 2o Basico  | B       | Retiro |[Ver] |
| EST-0415 | Coj Tzoc, Pedro I.      | 2o Basico  | B       | Activo |[Ver] |
+---------------------------------------------------------------------------+
| Mostrando 1-20 de 412             << Anterior | 1 2 3 ... | Siguiente >>  |
+---------------------------------------------------------------------------+
```

Estados:

```text
Sin coincidencias                      Sin alcance vigente
+---------------------------------+    +----------------------------------+
| No hay estudiantes que coincidan|    | No tiene secciones asignadas en  |
| con los filtros aplicados.      |    | el ciclo activo. Solicite la     |
| [ Limpiar filtros ]             |    | asignacion a coordinacion.       |
+---------------------------------+    +----------------------------------+
```

Por rol: Docente ve solo estudiantes de sus secciones y no ve `Nuevo estudiante`.
Encargado ve el modulo rotulado `Mis estudiantes`, limitado a sus vinculados.

---

## 4. Expediente del estudiante

Ruta prototipo `#/estudiantes/expediente`. Ruta real `/app/estudiantes/:id`.
Proposito: reunir la informacion del estudiante en un solo lugar, por pestanas.

```text
+---------------------------------------------------------------------------+
| Inicio > Estudiantes > Lopez Garcia, Maria Jose                           |
+---------------------------------------------------------------------------+
| +--------+  Lopez Garcia, Maria Jose             Estado: Activo           |
| | FOTO   |  Codigo EST-0412                                               |
| | 3x4    |  1o Basico "A" - Ciclo 2026     [ Editar ] # ADMIN DIR ADM     |
| +--------+  Encargada: Rosa Garcia (madre)  [ Credencial ]                |
+---------------------------------------------------------------------------+
| [General] [Encargados] [Salud # ADMIN DIR] [Documentos] [Matriculas]      |
+---------------------------------------------------------------------------+
| PESTANA GENERAL                                                           |
|                                                                           |
| Datos personales                     Datos institucionales                |
| Nombres     Maria Jose               Codigo      EST-0412                 |
| Apellidos   Lopez Garcia             Ingreso     15/01/2024               |
| Nacimiento  03/05/2012               Grado       1o Basico "A"            |
| Sexo        Femenino                 Jornada     Matutina                 |
| CUI         ****-*****-****          Sede        Sede Central             |
|                                                                           |
| Contacto                             Direccion                            |
| Telefono    ****-4512                Zona 2, Salcaja, Quetzaltenango      |
| Correo      no registrado                                                 |
+---------------------------------------------------------------------------+
```

```text
| PESTANA ENCARGADOS                          [ + Vincular encargado ]      |
|                                                                           |
| Nombre          | Parentesco | Telefono  | Vigencia   | Principal |       |
|-----------------|------------|-----------|------------|-----------|-------|
| Rosa Garcia     | Madre      | ****-4512 | Desde 2024 | Si        |[Ver]  |
| Jose Lopez      | Padre      | ****-7788 | Desde 2024 | No        |[Ver]  |
|                                                                           |
| Contactos de emergencia                     [ + Agregar contacto ]        |
| Ana Coj         | Tia        | ****-1122 | Vigente    |           |[Ver]  |
|                                                                           |
| `Ver` abre la ficha en Personas. Es el salto Expediente -> Personas.      |
+---------------------------------------------------------------------------+
```

```text
| PESTANA SALUD                                        # ADMIN DIRECTOR     |
|                                                                           |
| ! Informacion sensible. Su consulta queda registrada en la bitacora.      |
|                                                                           |
| Fecha      | Nota                                | Registro por           |
|------------|-------------------------------------|------------------------|
| 12/02/2026 | Alergia registrada                  | Enfermeria escolar     |
| 03/03/2026 | Restriccion de actividad fisica     | Direccion              |
|                                                                           |
| Las correcciones agregan una nota nueva. No se sobrescribe la historia.   |
+---------------------------------------------------------------------------+
```

```text
| PESTANA DOCUMENTOS                           [ + Subir documento ]        |
|                                                                           |
| Tipo                      | Archivo      | Fecha      | Estado  |         |
|---------------------------|--------------|------------|---------|---------|
| Certificado de nacimiento | cert_nac.pdf | 15/01/2024 | Vigente | [Ver]   |
| Fotografia                | foto.jpg     | 15/01/2024 | Vigente | [Ver]   |
| Constancia de estudios    | pendiente    | -          | Falta   | [Subir] |
|                                                                           |
| Cada descarga queda registrada con usuario, fecha y documento.            |
+---------------------------------------------------------------------------+
```

```text
| PESTANA MATRICULAS                            [ + Matricular ]            |
|                                                                           |
| Ciclo | Grado        | Seccion | Estado    | Movimientos     |            |
|-------|--------------|---------|-----------|-----------------|------------|
| 2026  | 1o Basico    | A       | Activa    | -               | [ Ver ]    |
| 2025  | Preparatoria | B       | Promovido | Cambio seccion  | [ Ver ]    |
|                                                                           |
| `Ver` abre la matricula. Es el salto Expediente -> Matriculas.            |
+---------------------------------------------------------------------------+
```

| Aspecto | Definicion |
| --- | --- |
| Quien la ve | Admin y Director completo; Administrativo sin `Salud`; Coordinador, Docente y Encargado en lectura reducida |
| Acciones | Editar datos basicos, vincular encargados, subir documentos, matricular |
| Regla | La pestana `Salud` requiere permiso especifico y registra la lectura |
| URL | La pestana activa viaja en la URL para poder compartir el enlace |

---

## 5. Personas

Ruta prototipo `#/personas`. Ruta real `/app/personas`.
Proposito: administrar el registro base de identidad que usan cuentas, docentes
y encargados.

```text
+---------------------------------------------------------------------------+
| Inicio > Personas                                                         |
+---------------------------------------------------------------------------+
| Personas                                             [ + Nueva persona ]  |
+---------------------------------------------------------------------------+
| ( Buscar por nombre o documento       )  Tipo (Todos v)   [ Buscar ]      |
| Vinculo: [ ] Estudiante [ ] Docente [ ] Encargado [ ] Personal            |
+---------------------------------------------------------------------------+
| Documento    | Nombre completo     | Vinculos            | Cuenta |       |
|--------------|---------------------|---------------------|--------|-------|
| 2451 88990   | Garcia Coj, Rosa    | Encargada           | No     | [Ver] |
| 1122 33445   | Perez Sam, Carlos   | Docente             | Si     | [Ver] |
| 3344 55667   | Lopez Ic, Jose      | Encargado, Personal | Si     | [Ver] |
+---------------------------------------------------------------------------+
| Mostrando 1-20 de 236             << Anterior | 1 2 3 ... | Siguiente >>  |
+---------------------------------------------------------------------------+
```

Detalle de persona:

```text
+---------------------------------------------------------------------------+
| Inicio > Personas > Perez Sam, Carlos                                     |
+---------------------------------------------------------------------------+
| Perez Sam, Carlos                                        [ Editar ]       |
| Documento 1122 33445 0101                                                 |
+---------------------------------------------------------------------------+
| DATOS DE LA PERSONA                                                       |
| Nombres    Carlos Alberto        Nacimiento  12/07/1988                   |
| Apellidos  Perez Sam             Sexo        Masculino                    |
| Telefono   ****-7788             Correo      c.perez@ejemplo.edu          |
| Direccion  Zona 1, Salcaja                                                |
+---------------------------------------------------------------------------+
| VINCULOS INSTITUCIONALES                                                  |
| Tipo      | Detalle                       | Vigencia    |                 |
|-----------|-------------------------------|-------------|-----------------|
| Docente   | Matematica, 1o y 2o Basico    | Ciclo 2026  | [ Ver ]         |
| Encargado | Lopez Perez, Ana (hija)       | Desde 2025  | [ Ver ]         |
+---------------------------------------------------------------------------+
| CUENTA DE USUARIO                                              # ADMIN    |
| Usuario cperez   Estado Activa   Roles Docente     [ Administrar cuenta ] |
|                                                                           |
| Si la persona no tiene cuenta:      [ + Crear cuenta de usuario ]         |
| Es el salto Personas -> Usuarios.                                         |
+---------------------------------------------------------------------------+
```

| Aspecto | Definicion |
| --- | --- |
| Quien la ve | Admin, Director y Administrativo; los demas roles no ven el modulo |
| Acciones | Crear persona, editar, ver vinculos, crear o abrir la cuenta asociada |
| Regla | Una persona puede tener varios vinculos simultaneos |
| Regla | Toda cuenta de usuario debe apuntar a una persona existente |

---

## 6. Estructura academica

Ruta prototipo `#/academico`. Rutas reales `/app/sedes`, `/app/niveles`,
`/app/cursos`, `/app/ciclos`.
Proposito: mantener los catalogos que sostienen la matricula. El prototipo los
agrupa en una pantalla con pestanas porque comparten patron de uso.

```text
+---------------------------------------------------------------------------+
| Inicio > Estructura academica                                             |
+---------------------------------------------------------------------------+
| [Sedes] [Niveles y grados] [Cursos] [Ciclos]                              |
+---------------------------------------------------------------------------+
| PESTANA SEDES                                          [ + Nueva sede ]   |
| Codigo | Nombre       | Direccion         | Jornadas          | Estado |   |
|--------|--------------|-------------------|-------------------|--------|---|
| CEN    | Sede Central | Zona 1, Salcaja   | Matutina, Vespert.| Activa |[E]|
| ANX    | Anexo Norte  | Zona 4, Salcaja   | Matutina          | Activa |[E]|
+---------------------------------------------------------------------------+
```

```text
| PESTANA NIVELES Y GRADOS                              [ + Nuevo nivel ]   |
| Nivel Basico                                              [ Editar ]      |
|   Grado           | Orden | Oferta 2026 | Acciones                        |
|   ----------------|-------|-------------|---------------------------------|
|   Primero Basico  |   1   | Si          | [ Ver ] [ Editar ]              |
|   Segundo Basico  |   2   | Si          | [ Ver ] [ Editar ]              |
|   Tercero Basico  |   3   | No          | [ Ver ] [ Editar ]              |
|                                                       [ + Nuevo grado ]   |
+---------------------------------------------------------------------------+
```

```text
| PESTANA CURSOS                                        [ + Nuevo curso ]   |
| ( Buscar curso               )  Area (Todas v)             [ Buscar ]     |
| Codigo | Curso                   | Area         | Estado |                |
|--------|-------------------------|--------------|--------|----------------|
| MAT    | Matematica              | Ciencias     | Activo | [ Editar ]     |
| COM    | Comunicacion y Lenguaje | Comunicacion | Activo | [ Editar ]     |
| CCN    | Ciencias Naturales      | Ciencias     | Activo | [ Editar ]     |
+---------------------------------------------------------------------------+
```

```text
| PESTANA CICLOS                                        [ + Nuevo ciclo ]   |
| Ciclo | Inicio     | Fin        | Estado  | Acciones                      |
|-------|------------|------------|---------|-------------------------------|
| 2026  | 15/01/2026 | 31/10/2026 | Abierto | [ Ver oferta ] [ Cerrar ]     |
| 2025  | 15/01/2025 | 31/10/2025 | Cerrado | [ Ver oferta ]                |
|                                                                           |
| OFERTA DEL CICLO 2026                             [ + Agregar oferta ]    |
| Grado          | Jornada   | Secciones | Cupo | Matriculados |            |
|----------------|-----------|-----------|------|--------------|------------|
| Primero Basico | Matutina  | A, B      |  70  |      64      | [ Abrir ]  |
| Segundo Basico | Matutina  | A, B      |  70  |      58      | [ Abrir ]  |
| Tercero Basico | Vespertina| A         |  35  |      31      | [ Abrir ]  |
+---------------------------------------------------------------------------+
```

Confirmacion al cerrar un ciclo:

```text
+-----------------------------------------------------------+
| Cerrar el ciclo 2026?                                     |
|                                                           |
| El cierre impide nuevas matriculas y cambios de estructura|
| La informacion se conserva en historia.                   |
| Escriba el ciclo para confirmar: (__________)             |
|                                                           |
|                        [ Cancelar ]  [ Cerrar ciclo ]     |
+-----------------------------------------------------------+
```

---

## 7. Oferta del ciclo

Ruta prototipo `#/academico/oferta`. Ruta real `/app/ofertas/:offeringId`.
Proposito: administrar secciones y asignaciones docentes de un grado y jornada.
Es tambien un punto de entrada al flujo de matricula.

```text
+---------------------------------------------------------------------------+
| Inicio > Estructura academica > 2026 > Primero Basico, Matutina           |
+---------------------------------------------------------------------------+
| SECCIONES                                            [ + Nueva seccion ]  |
| Seccion | Cupo | Matriculados | Aula | Guia           | Acciones          |
|---------|------|--------------|------|----------------|-------------------|
| A       |  35  |      32      | 101  | Perez Sam, C.  | [Editar] [Ver]    |
| B       |  35  |      32      | 102  | Sin asignar    | [Editar] [Ver]    |
+---------------------------------------------------------------------------+
| ASIGNACIONES DOCENTES DE LA SECCION A            [ + Nueva asignacion ]   |
| Curso                   | Docente       | Horas | Vigencia |              |
|-------------------------|---------------|-------|----------|--------------|
| Matematica              | Perez Sam, C. |   5   | Ciclo    | [ Quitar ]   |
| Comunicacion y Lenguaje | Sin asignar   |   5   | -        | [ Asignar ]  |
+---------------------------------------------------------------------------+
| Cupo disponible en la seccion A: 3   [ Matricular en esta seccion ]       |
+---------------------------------------------------------------------------+
```

| Aspecto | Definicion |
| --- | --- |
| Quien la ve | Admin y Director total; Coordinador edita; Administrativo lectura |
| Acciones | Crear secciones, asignar docentes, matricular sobre la seccion |
| Regla | Un ciclo cerrado bloquea toda escritura de esta pantalla |
| Regla | Las asignaciones docentes tienen vigencia; no se borran, se cierran |

---

## 8. Matriculas

Ruta prototipo `#/matriculas`. Ruta real `/app/matriculas`.

```text
+---------------------------------------------------------------------------+
| Inicio > Matriculas                                                       |
+---------------------------------------------------------------------------+
| Matriculas                                        [ + Nueva matricula ]   |
+---------------------------------------------------------------------------+
| ( Buscar estudiante o codigo   ) Ciclo (2026 v) Estado (Todas v)          |
| Grado (Todos v)  Seccion (Todas v)  Requisitos (Todos v)   [ Buscar ]     |
+---------------------------------------------------------------------------+
| Codigo   | Estudiante         | Grado/Sec | Fecha      | Requisitos |     |
|----------|--------------------|-----------|------------|------------|-----|
| MAT-1204 | Lopez Garcia, M.   | 1o A      | 15/01/2026 | Completos  |[Ver]|
| MAT-1205 | Perez Chan, L.     | 1o A      | 15/01/2026 | 2 faltan   |[Ver]|
| MAT-1206 | Ramos Coj, A.      | 2o B      | 16/01/2026 | Completos  |[Ver]|
+---------------------------------------------------------------------------+
| Mostrando 1-20 de 398             << Anterior | 1 2 3 ... | Siguiente >>  |
+---------------------------------------------------------------------------+
```

Detalle de matricula, ruta real `/app/matriculas/:id`:

```text
+---------------------------------------------------------------------------+
| Inicio > Matriculas > MAT-1204                                            |
+---------------------------------------------------------------------------+
| Matricula MAT-1204                                    Estado: Activa      |
| Lopez Garcia, Maria Jose (EST-0412)                   [ Ver expediente ]  |
+---------------------------------------------------------------------------+
| DATOS                                                                     |
| Ciclo 2026        Grado 1o Basico "A"     Jornada Matutina                |
| Fecha 15/01/2026  Tipo Primer ingreso     Registro por A. Lopez           |
+---------------------------------------------------------------------------+
| REQUISITOS                                                                |
| Certificado de nacimiento   Entregado   15/01/2026        [ Ver ]         |
| Fotografia                  Pendiente   -                 [ Subir ]       |
+---------------------------------------------------------------------------+
| MOVIMIENTOS                                     [ + Registrar cambio ]    |
| Fecha      | Movimiento        | Detalle          | Registro por          |
|------------|-------------------|------------------|-----------------------|
| 15/01/2026 | Matricula creada  | 1o Basico "A"    | A. Lopez              |
| 20/02/2026 | Cambio de seccion | De "B" a "A"     | A. Lopez              |
+---------------------------------------------------------------------------+
| [ Cambiar seccion ]  [ Registrar retiro ]  [ Imprimir constancia ]        |
+---------------------------------------------------------------------------+
```

| Aspecto | Definicion |
| --- | --- |
| Quien la ve | Administrativo, Director y Admin operan; Coordinador lee |
| Regla | No se elimina una matricula: se registra un movimiento que cambia su estado |
| Bloqueos | Ciclo cerrado y seccion sin cupo impiden registrar |

---

## 9. Asistente de matricula

Ruta prototipo `#/matriculas/nueva`. Ruta real `/app/matriculas/nueva`.
Es la unica pantalla que restringe la navegacion mientras esta en curso.
Cancelar no deja registros a medias.

```text
+---------------------------------------------------------------------------+
| Nueva matricula                                            [ Cancelar ]   |
+---------------------------------------------------------------------------+
| (1) Estudiante -> (2) Ubicacion -> (3) Requisitos -> (4) Confirmacion     |
+---------------------------------------------------------------------------+
| PASO 1 DE 4  ESTUDIANTE                                                   |
|                                                                           |
| ( o ) Estudiante ya registrado                                            |
|       ( Buscar por nombre, codigo o documento   )  [ Buscar ]             |
|       +-----------------------------------------------------------------+ |
|       | (o) EST-0412  Lopez Garcia, Maria Jose    Ultimo ciclo 2025     | |
|       | ( ) EST-0455  Lopez Ic, Maria Fernanda    Ultimo ciclo 2025     | |
|       +-----------------------------------------------------------------+ |
|                                                                           |
| (   ) Estudiante nuevo                                                    |
|       Se abrira el formulario de alta antes de continuar.                 |
|                                                                           |
|                                            [ Atras ]  [ Siguiente ]       |
+---------------------------------------------------------------------------+
```

```text
| PASO 2 DE 4  UBICACION ACADEMICA                                          |
|                                                                           |
| Estudiante: Lopez Garcia, Maria Jose (EST-0412)                           |
|                                                                           |
| Ciclo escolar   (2026 - Abierto             v)                            |
| Nivel           (Basico                     v)                            |
| Grado           (Primero Basico             v)                            |
| Jornada         (Matutina                   v)                            |
| Seccion         (A - 32 de 35 ocupados      v)                            |
|                                                                           |
| ! Cupo disponible en la seccion A: 3.                                     |
|                                                                           |
| Tipo de ingreso  (o) Primer ingreso  ( ) Reinscripcion  ( ) Traslado      |
|                                                                           |
|                                            [ Atras ]  [ Siguiente ]       |
+---------------------------------------------------------------------------+
```

```text
| PASO 3 DE 4  REQUISITOS DOCUMENTALES                                      |
|                                                                           |
| Documento                    | Obligatorio | Estado    | Accion           |
|------------------------------|-------------|-----------|------------------|
| Certificado de nacimiento    | Si          | Entregado | [ Ver ]          |
| Fotografia                   | Si          | Pendiente | [ Subir ]        |
| Certificado del grado previo | Si          | Pendiente | [ Subir ]        |
| Constancia de vacunacion     | No          | Pendiente | [ Subir ]        |
|                                                                           |
| [x] Registrar matricula con requisitos pendientes                         |
|     Motivo (Entrega comprometida para el 30/01               )            |
|                                                                           |
|                                            [ Atras ]  [ Siguiente ]       |
+---------------------------------------------------------------------------+
```

```text
| PASO 4 DE 4  CONFIRMACION                                                 |
|                                                                           |
| Revise antes de registrar. La matricula genera historia.                  |
|                                                                           |
| Estudiante   Lopez Garcia, Maria Jose (EST-0412)          [ Cambiar ]     |
| Ciclo        2026                                         [ Cambiar ]     |
| Ubicacion    Primero Basico "A", jornada Matutina         [ Cambiar ]     |
| Ingreso      Primer ingreso                               [ Cambiar ]     |
| Requisitos   2 pendientes, con motivo registrado          [ Cambiar ]     |
|                                                                           |
|                          [ Atras ]  [ Registrar matricula ]               |
+---------------------------------------------------------------------------+
```

Confirmacion de salida:

```text
+-----------------------------------------------------------+
| Cancelar la matricula en curso?                           |
| No se guardara ningun dato capturado en los pasos previos. |
|                     [ Seguir aqui ]  [ Cancelar matricula ]|
+-----------------------------------------------------------+
```

---

## 10. Reportes

Ruta prototipo `#/reportes`. Ruta real `/app/reportes`.

```text
+---------------------------------------------------------------------------+
| Inicio > Reportes                                                         |
+---------------------------------------------------------------------------+
| MATRICULA                                                                 |
|  +---------------------------------+  +---------------------------------+ |
|  | Matricula por grado y seccion   |  | Estudiantes por estado          | |
|  | Conteo del ciclo seleccionado   |  | Activos, retirados, traslados   | |
|  | [ Generar ]                     |  | [ Generar ]                     | |
|  +---------------------------------+  +---------------------------------+ |
|                                                                           |
| ESTRUCTURA                                                                |
|  +---------------------------------+  +---------------------------------+ |
|  | Ocupacion de secciones          |  | Asignaciones docentes           | |
|  | Cupo contra matriculados        |  | Cursos con y sin docente        | |
|  | [ Generar ]                     |  | [ Generar ]                     | |
|  +---------------------------------+  +---------------------------------+ |
|                                                                           |
| CONTROL                                                        # ADMIN    |
|  +---------------------------------+  +---------------------------------+ |
|  | Requisitos pendientes           |  | Bitacora de accesos             | |
|  | Matriculas incompletas          |  | Acciones y lecturas sensibles   | |
|  | [ Generar ]                     |  | [ Generar ]                     | |
|  +---------------------------------+  +---------------------------------+ |
+---------------------------------------------------------------------------+
```

Reporte generado:

```text
+---------------------------------------------------------------------------+
| Inicio > Reportes > Matricula por grado y seccion                         |
+---------------------------------------------------------------------------+
| Ciclo (2026 v)  Sede (Todas v)  Jornada (Todas v)         [ Generar ]     |
+---------------------------------------------------------------------------+
| Generado el 08/08/2026 09:14            [ Exportar CSV ]  [ Imprimir ]    |
+---------------------------------------------------------------------------+
| Grado          | Seccion | Cupo | Matriculados | Ocupacion | Disponibles  |
|----------------|---------|------|--------------|-----------|--------------|
| Primero Basico | A       |  35  |      32      |   91%     |      3       |
| Primero Basico | B       |  35  |      32      |   91%     |      3       |
| Segundo Basico | A       |  35  |      29      |   83%     |      6       |
| Segundo Basico | B       |  35  |      29      |   83%     |      6       |
| Tercero Basico | A       |  35  |      31      |   89%     |      4       |
|----------------|---------|------|--------------|-----------|--------------|
| TOTAL          |    5    | 175  |     153      |   87%     |     22       |
+---------------------------------------------------------------------------+
| El reporte solo incluye datos dentro del alcance del usuario.             |
+---------------------------------------------------------------------------+
```

| Aspecto | Definicion |
| --- | --- |
| Quien la ve | Admin, Director, Coordinador y Docente, con catalogo distinto |
| Regla | El resultado se filtra por el alcance del usuario, sin excepcion |
| Estado vacio | Sin datos para los parametros, se ofrece cambiar el ciclo |

---

## 11. Usuarios y permisos

Ruta prototipo `#/usuarios`. Ruta real `/app/usuarios`.
Visible unicamente para el Administrador del sistema.

```text
+---------------------------------------------------------------------------+
| Inicio > Usuarios y permisos                                              |
+---------------------------------------------------------------------------+
| Usuarios                                             [ + Nuevo usuario ]  |
| ( Buscar usuario o persona   )  Rol (Todos v)  Estado (Todos v)           |
+---------------------------------------------------------------------------+
| Usuario | Persona           | Roles          | Estado    | Ultimo acceso  |
|---------|-------------------|----------------|-----------|----------------|
| admin   | Sistema           | Administrador  | Activa    | Hoy      [Ver] |
| dlopez  | Lopez Ic, Diana   | Director       | Activa    | Hoy      [Ver] |
| cperez  | Perez Sam, Carlos | Docente        | Activa    | Ayer     [Ver] |
| mramos  | Ramos Coj, Maria  | Administrativo | Bloqueada | 05/08    [Ver] |
+---------------------------------------------------------------------------+
```

Detalle de usuario:

```text
+---------------------------------------------------------------------------+
| Inicio > Usuarios y permisos > cperez                                     |
+---------------------------------------------------------------------------+
| cperez                                                  Estado: Activa    |
| Persona: Perez Sam, Carlos                              [ Ver persona ]   |
+---------------------------------------------------------------------------+
| ROLES Y ALCANCES ASIGNADOS                            [ + Asignar rol ]   |
| Rol     | Alcance                        | Vigencia      |                |
|---------|--------------------------------|---------------|----------------|
| Docente | Ciclo 2026, 1o "A", Matematica | 15/01 - 31/10 | [ Quitar ]     |
| Docente | Ciclo 2026, 2o "B", Matematica | 15/01 - 31/10 | [ Quitar ]     |
+---------------------------------------------------------------------------+
| PERMISOS EFECTIVOS                                        Solo lectura    |
| student.view_basic        Alcance: secciones asignadas                    |
| grade.write               Alcance: cursos asignados, ciclo abierto        |
| attendance.record_manual  Alcance: secciones asignadas                    |
|                                                                           |
| Los permisos se derivan de los roles. No se editan uno por uno.           |
+---------------------------------------------------------------------------+
| [ Restablecer contrasena ]   [ Desactivar cuenta ]                        |
+---------------------------------------------------------------------------+
```

Confirmacion de desactivacion:

```text
+-----------------------------------------------------------+
| Desactivar la cuenta cperez?                              |
|                                                           |
| La cuenta no podra iniciar sesion. No se elimina y su      |
| historial se conserva. La accion queda auditada.          |
|                                                           |
|                      [ Cancelar ]  [ Desactivar cuenta ]  |
+-----------------------------------------------------------+
```

---

## 12. Matriz de accesos

Ruta prototipo `#/permisos`. Ruta real `/app/usuarios/permisos`.
Proposito: mostrar en una sola vista que puede hacer cada rol. Es la pantalla
que se usa en la sesion de validacion con la institucion.

```text
+---------------------------------------------------------------------------+
| Inicio > Usuarios y permisos > Matriz de accesos                          |
+---------------------------------------------------------------------------+
| Modulo         | Admin | Direct. | Coord. | Admtvo | Docente | Encargado  |
|----------------|-------|---------|--------|--------|---------|------------|
| Panel          | Total | Total   | Total  | Total  | Propio  | Propio     |
| Estudiantes    | Total | Total   | Lectura| Edicion| Sus sec.| Vinculados |
| Salud          | Total | Lectura | No     | No     | No      | No         |
| Personas       | Total | Total   | No     | Edicion| No      | No         |
| Estructura     | Total | Total   | Edicion| No     | No      | No         |
| Matriculas     | Total | Total   | Lectura| Edicion| No      | No         |
| Reportes       | Total | Total   | Total  | No     | Sus sec.| No         |
| Usuarios       | Total | No      | No     | No     | No      | No         |
+---------------------------------------------------------------------------+
| Leyenda                                                                   |
| Total     ve el modulo y ejecuta sus operaciones dentro de su alcance     |
| Edicion   crea y modifica; no elimina ni cierra periodos                  |
| Lectura   ve el modulo sin acciones de escritura                          |
| No        el modulo no aparece en el menu ni es alcanzable por URL        |
+---------------------------------------------------------------------------+
| [ Exportar matriz ]                                                       |
+---------------------------------------------------------------------------+
```

---

## Pantallas de estado

```text
Acceso denegado                        Pantalla no encontrada
+-----------------------------------+  +-----------------------------------+
|         Acceso denegado           |  |    Pantalla no encontrada         |
|                                   |  |                                   |
| Su rol no tiene permiso para      |  | La direccion no corresponde a     |
| abrir esta pantalla. Solicitelo   |  | ninguna pantalla del sistema.     |
| a administracion.                 |  |                                   |
| El intento quedo registrado.      |  |                                   |
|      [ Volver al panel ]          |  |      [ Volver al panel ]          |
+-----------------------------------+  +-----------------------------------+
```

## Decisiones de diseno adoptadas

1. Una tarea, una pantalla. Las operaciones largas se dividen en pasos visibles.
2. Los listados siempre traen busqueda, filtros y paginacion.
3. Las pantallas de detalle usan pestanas cuando la informacion supera una vista.
4. Lo sensible se separa en su propia pestana y avisa que la lectura se registra.
5. Las acciones no permitidas no se muestran deshabilitadas: no se muestran.
6. Las acciones irreversibles piden confirmacion escrita.
7. El sistema nunca elimina: desactiva, cierra o registra un movimiento.

## Pendientes de definicion

| # | Pantalla | Pregunta abierta | Responde |
| --- | --- | --- | --- |
| P1 | Panel | Que indicadores deben ir en la parte superior | Direccion |
| P2 | Expediente | Que campos son obligatorios al crear el expediente | Institucion |
| P3 | Expediente | Formato y regla del correlativo del codigo de estudiante | Institucion |
| P4 | Estructura academica | Quien autoriza el cierre de un ciclo escolar | Direccion |
| P5 | Estructura academica | Sedes, niveles, cursos y ciclos separados o agrupados en el menu | Institucion |
| P6 | Matriculas | Lista obligatoria oficial de requisitos por tipo de ingreso | Institucion |
| P7 | Matriculas | Si documentos incompletos permiten matricula provisional y quien la autoriza | Direccion |
| P8 | Matriculas | Al exceder el cupo de una seccion, el sistema bloquea o solo advierte | Institucion |
| P9 | Matriculas | Formato oficial y firma de la constancia de matricula | Institucion |
| P10 | Reportes | Formato oficial exigido por el Ministerio para la nomina | Institucion |
| P11 | Expediente | Quien registra y quien consulta datos de salud del estudiante | Direccion |
| P12 | Panel | El portal de encargados entra en esta fase o se pospone | Direccion |

Estas preguntas se llevan a la sesion descrita en
[`prototype-validation.md`](prototype-validation.md) y se siguen en
[`validation-observations.md`](validation-observations.md).
