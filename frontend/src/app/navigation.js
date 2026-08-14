/**
 * navigation.js — Registro unico de los modulos privados de la aplicacion.
 *
 * Es la unica fuente de verdad de tres cosas que antes se repetian: los items
 * del menu lateral, las rutas perezosas y los accesos rapidos del panel. Si las
 * tres listas viven en archivos distintos, tarde o temprano una ruta existe sin
 * item de menu (o al reves).
 *
 * `load` es la MISMA funcion de import que consume `React.lazy` en `routes.jsx`.
 * Por eso el prefetch al pasar el mouse por un item calienta exactamente el
 * chunk que se va a necesitar, y no una copia distinta del modulo.
 *
 * Agregar un modulo = agregar una entrada aqui. Nada mas.
 */

import DashboardOutlinedIcon from "@mui/icons-material/DashboardOutlined";
import SchoolOutlinedIcon from "@mui/icons-material/SchoolOutlined";
import CoPresentOutlinedIcon from "@mui/icons-material/CoPresentOutlined";
import FamilyRestroomOutlinedIcon from "@mui/icons-material/FamilyRestroomOutlined";
import BadgeOutlinedIcon from "@mui/icons-material/BadgeOutlined";
import ApartmentOutlinedIcon from "@mui/icons-material/ApartmentOutlined";
import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import CalendarMonthOutlinedIcon from "@mui/icons-material/CalendarMonthOutlined";
import AssignmentIndOutlinedIcon from "@mui/icons-material/AssignmentIndOutlined";
import HowToRegOutlinedIcon from "@mui/icons-material/HowToRegOutlined";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";
import GradingOutlinedIcon from "@mui/icons-material/GradingOutlined";
import ArticleOutlinedIcon from "@mui/icons-material/ArticleOutlined";
import NotificationsActiveOutlinedIcon from "@mui/icons-material/NotificationsActiveOutlined";

import {
  canViewAlumnos,
  canViewCursos,
  canViewDocentes,
  canViewNiveles,
  canViewPadres,
  canViewSedes,
} from "@auth/permissions.js";

/** Panel principal. Va suelto arriba, sin grupo: es el destino por defecto. */
export const HOME_ITEM = {
  key: "panel",
  label: "Panel",
  description: "Resumen del establecimiento y accesos rapidos.",
  path: "/app",
  end: true,
  icon: DashboardOutlinedIcon,
  load: () => import("@dashboard/DashboardPage.jsx"),
};

/**
 * Grupos del menu lateral, en orden de aparicion.
 *
 * El orden refleja el flujo real de trabajo del establecimiento: primero la
 * gente, despues como se organiza el ano, despues la operacion diaria, y al
 * final lo que se emite y se vigila.
 *
 * `canView` recibe el usuario de sesion. La UI degrada por permiso, no por
 * error: un modulo que el usuario no puede ver simplemente no aparece, en vez
 * de aparecer y fallar al entrar.
 */
export const NAV_GROUPS = [
  {
    key: "comunidad",
    label: "Comunidad educativa",
    items: [
      {
        key: "alumnos",
        label: "Estudiantes",
        description: "Listado y expediente de estudiantes.",
        path: "/app/alumnos",
        icon: SchoolOutlinedIcon,
        canView: canViewAlumnos,
        countable: true,
        load: () => import("@students/AlumnosPage.jsx"),
      },
      {
        key: "docentes",
        label: "Docentes",
        description: "Personal docente y administrativo.",
        path: "/app/docentes",
        icon: CoPresentOutlinedIcon,
        canView: canViewDocentes,
        countable: true,
        load: () => import("@teachers/DocentesPage.jsx"),
      },
      {
        key: "padres",
        label: "Padres de familia",
        description: "Encargados y su vinculo con estudiantes.",
        path: "/app/padres-de-familia",
        icon: FamilyRestroomOutlinedIcon,
        canView: canViewPadres,
        countable: true,
        load: () => import("@guardians/GuardiansPage.jsx"),
      },
      {
        key: "personas",
        label: "Personas",
        description: "Registro base de identidad institucional.",
        path: "/app/personas",
        icon: BadgeOutlinedIcon,
        load: () => import("@people/PersonasPage.jsx"),
      },
    ],
  },
  {
    key: "academico",
    label: "Estructura academica",
    items: [
      {
        key: "ciclos",
        label: "Ciclo escolar",
        description: "Registro, activacion y clonado de ciclos.",
        path: "/app/ciclos",
        icon: CalendarMonthOutlinedIcon,
        load: () => import("@cycles/CyclesPage.jsx"),
      },
      {
        key: "sedes",
        label: "Sedes",
        description: "Sedes del establecimiento y sus jornadas.",
        path: "/app/sedes",
        icon: ApartmentOutlinedIcon,
        canView: canViewSedes,
        load: () => import("@academics/CampusesPage.jsx"),
      },
      {
        key: "niveles",
        label: "Niveles",
        description: "Niveles, grados y plan de estudios.",
        path: "/app/niveles",
        icon: AccountTreeOutlinedIcon,
        canView: canViewNiveles,
        load: () => import("@academics/LevelsPage.jsx"),
      },
      {
        key: "cursos",
        label: "Cursos",
        description: "Catalogo de cursos de la institucion.",
        path: "/app/cursos",
        icon: MenuBookOutlinedIcon,
        canView: canViewCursos,
        load: () => import("@academics/SubjectsPage.jsx"),
      },
      {
        key: "asignaciones",
        label: "Asignaciones docentes",
        description: "Que docente da que curso en que seccion.",
        path: "/app/asignaciones",
        icon: AssignmentIndOutlinedIcon,
        canView: canViewDocentes,
        load: () => import("@academics/TeachingAssignmentsPage.jsx"),
      },
    ],
  },
  {
    key: "operacion",
    label: "Operacion diaria",
    items: [
      {
        key: "matriculas",
        label: "Matriculas",
        description: "Matricula, reinscripcion e historial por estudiante.",
        path: "/app/matriculas",
        icon: HowToRegOutlinedIcon,
        canView: canViewAlumnos,
        load: () => import("@enrolments/EnrolmentsPage.jsx"),
      },
      {
        key: "asistencia",
        label: "Asistencia",
        description: "Movimientos de jornada y estado del dia.",
        path: "/app/asistencia",
        icon: FactCheckOutlinedIcon,
        canView: canViewAlumnos,
        load: () => import("@attendance/AttendancePage.jsx"),
      },
      {
        key: "evaluacion",
        label: "Evaluacion",
        description: "Unidades, ventanas de captura y recuperacion.",
        path: "/app/evaluacion",
        icon: GradingOutlinedIcon,
        load: () => import("@evaluation/EvaluationPage.jsx"),
      },
    ],
  },
  {
    key: "control",
    label: "Documentos y control",
    items: [
      {
        key: "plantillas",
        label: "Plantillas",
        description: "Plantillas de constancias y reportes.",
        path: "/app/plantillas",
        icon: ArticleOutlinedIcon,
        load: () => import("@documents/TemplatesPage.jsx"),
      },
      {
        key: "alertas",
        label: "Alertas",
        description: "Alertas de asistencia y su atencion.",
        path: "/app/alertas",
        icon: NotificationsActiveOutlinedIcon,
        load: () => import("@reporting/AlertsPage.jsx"),
      },
    ],
  },
];

/** Todos los modulos en una lista plana, panel incluido. */
export const ALL_MODULES = [
  HOME_ITEM,
  ...NAV_GROUPS.flatMap((group) => group.items),
];

/** Grupos con sus items filtrados por permiso; se omiten los que quedan vacios. */
export function visibleGroups(user) {
  return NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => !item.canView || item.canView(user)),
  })).filter((group) => group.items.length > 0);
}

/**
 * Descarga anticipada del chunk de un modulo.
 *
 * Se dispara al pasar el mouse o al enfocar el item: cuando el usuario
 * realmente hace clic, el modulo ya esta en memoria y la navegacion no muestra
 * el esqueleto. Si el import falla se ignora a proposito — es una optimizacion,
 * y el `React.lazy` de la ruta volvera a intentarlo y ahi si reportara el error.
 */
export function prefetchModule(item) {
  if (!item?.load) return;
  item.load().catch(() => {});
}
