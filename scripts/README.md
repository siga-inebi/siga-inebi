# Scripts Foundation

Espacio reservado para utilidades de desarrollo, validacion, importacion controlada y automatizacion local.

Reglas:

- No incluir secretos.
- No asumir datos reales.
- Documentar entradas, salidas y riesgos antes de agregar script.

## Vincular issues cerrados al Project

`github/link-closed-issues-to-project.sh` compara los issues cerrados del repositorio con los
elementos del GitHub Project y vincula únicamente los faltantes. No modifica estados, fechas,
milestones, responsables ni otros campos.

```sh
# Solo muestra los cambios propuestos.
sh scripts/github/link-closed-issues-to-project.sh

# Aplica los cambios con la cuenta activa de gh.
APPLY=true sh scripts/github/link-closed-issues-to-project.sh
```

Valores predeterminados: `REPO_SLUG=siga-inebi/siga-inebi`, `PROJECT_OWNER=siga-inebi` y
`PROJECT_NUMBER=1`. La ejecución con `APPLY=true` requiere permiso de escritura sobre el Project.
El script limita la consulta a 1000 issues cerrados y 1000 elementos del Project, comprueba los
totales informados por GitHub y falla sin escribir si no puede recuperar cualquiera de las listas
por completo.

## Agregar S1-S8 al Gantt histórico

`github/add-completed-course-weeks-to-project.sh` crea o actualiza ocho borradores resumen basados
en las páginas 3-5 de `Proyectos de Ingeniería en Informática y Sistemas, 2603.pdf`, programa del
curso de la Universidad Rafael Landívar, Facultad de Ingeniería, segundo semestre de 2026, sección
01. Reconcilia su contenido, registra responsables, les asigna fechas históricas y los marca como
`Done`. La evidencia del mensaje denominado «Fase 2» se distribuye según el programa entre S3, S4
y S5. La asignación de desarrollo de Identity, People, Academic, ciclos y frontend corresponde a la
etapa posterior que comienza en S9 y se excluye intencionalmente de S1-S8. En S1, S2 y S6-S8 se
mantiene el resumen oficial y se indica que no se suministró una asignación histórica individual.
El cálculo usa
intervalos de siete días con límites compartidos: S8 termina el 13 de agosto de 2026, cuando
comienza S9.

```sh
# Previsualiza los ocho elementos y sus fechas.
sh scripts/github/add-completed-course-weeks-to-project.sh

# Crea o actualiza los elementos con una cuenta autorizada.
APPLY=true sh scripts/github/add-completed-course-weeks-to-project.sh
```

El script reutiliza `Fecha esperada` como fecha final y crea `Fecha inicio` si el Project todavía
no dispone de ese campo. También reutiliza el campo de texto `Responsables` o lo crea cuando falta;
su nombre se puede configurar mediante `RESPONSIBLES_FIELD_NAME`. No modifica los tickets
funcionales existentes. Limita la consulta a 1000 elementos y 1000 campos del Project, comprueba los
totales informados por GitHub y falla sin escribir si cualquiera de las listas está truncada. Antes
de escribir, comprueba nombres de campo únicos, tipos `DATE`/`TEXT`/selección única, una sola opción
`Done`, permiso de actualización y la marca invisible de propiedad de cada borrador S1-S8 que
reutiliza. Un borrador con el mismo título pero sin la marca correspondiente no se modifica.

La ejecución con `APPLY=true` es reanudable e idempotente, pero las operaciones remotas no tienen
rollback transaccional. Si GitHub devuelve un error de API o límite de tasa después de iniciar las
escrituras, revise los registros y vuelva a ejecutar el comando después de resolver el problema de
acceso o servicio.

Para ejecutar el flujo combinado, primero use `link-closed-issues-to-project.sh` y después
`add-completed-course-weeks-to-project.sh`; así se vinculan los issues cerrados antes de sincronizar
los resúmenes S1-S8. Ambos comandos son simulaciones por defecto y solo escriben con `APPLY=true`.
La etiqueta `size:exception`, cuando se utilice, corresponde exclusivamente a la revisión del PR y
no cambia el comportamiento de estos scripts.
