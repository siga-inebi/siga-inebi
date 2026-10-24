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
import MeetingRoomOutlinedIcon from "@mui/icons-material/MeetingRoomOutlined";
import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import CalendarMonthOutlinedIcon from "@mui/icons-material/CalendarMonthOutlined";
import AssignmentIndOutlinedIcon from "@mui/icons-material/AssignmentIndOutlined";
import HowToRegOutlinedIcon from "@mui/icons-material/HowToRegOutlined";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";
import GradingOutlinedIcon from "@mui/icons-material/GradingOutlined";
import ArticleOutlinedIcon from "@mui/icons-material/ArticleOutlined";
import StorageOutlinedIcon from "@mui/icons-material/StorageOutlined";
import PictureAsPdfOutlinedIcon from "@mui/icons-material/PictureAsPdfOutlined";
import CategoryOutlinedIcon from "@mui/icons-material/CategoryOutlined";
import NotificationsActiveOutlinedIcon from "@mui/icons-material/NotificationsActiveOutlined";
import AdminPanelSettingsOutlinedIcon from "@mui/icons-material/AdminPanelSettingsOutlined";
import ManageAccountsOutlinedIcon from "@mui/icons-material/ManageAccountsOutlined";
import HistoryEduOutlinedIcon from "@mui/icons-material/HistoryEduOutlined";
import MonitorHeartOutlinedIcon from "@mui/icons-material/MonitorHeartOutlined";

import {
  ACCOUNT_ADMIN_PERMISSIONS,
  MODULE_PERMISSIONS,
  canAccessModule,
} from "@auth/permissions.js";

/** Panel principal. Va suelto arriba, sin grupo: es el destino por defecto. */
export const HOME_ITEM = {
  key: "panel",
  label: "Panel",
  description: "Resumen del establecimiento y accesos rápidos.",
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
 * `permissions` lista los permisos atomicos que habilitan el modulo (basta con
 * uno; ver `MODULE_PERMISSIONS`). La UI degrada por permiso, no por error: un
 * modulo que la cuenta no puede usar no aparece en el menu, y su ruta muestra
 * "sin acceso" en vez de fallar con un 403 al entrar (docs/ux-ui.md 1.4). El
 * backend sigue autorizando cada operacion.
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
        permissions: MODULE_PERMISSIONS.alumnos,
        countable: true,
        load: () => import("@students/AlumnosPage.jsx"),
      },
      {
        key: "docentes",
        label: "Docentes",
        description: "Personal docente y administrativo.",
        path: "/app/docentes",
        icon: CoPresentOutlinedIcon,
        countable: true,
        load: () => import("@teachers/DocentesPage.jsx"),
      },
      {
        key: "padres",
        label: "Padres de familia",
        description: "Encargados y su vínculo con estudiantes.",
        path: "/app/padres-de-familia",
        icon: FamilyRestroomOutlinedIcon,
        countable: true,
        load: () => import("@guardians/GuardiansPage.jsx"),
      },
    ],
  },
  {
    key: "academico",
    label: "Estructura académica",
    items: [
      {
        key: "ciclos",
        label: "Ciclo escolar",
        description: "Ciclos, su preparación, activación y cierre.",
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
        load: () => import("@academics/CampusesPage.jsx"),
      },
      {
        key: "aulas",
        label: "Aulas",
        description: "Aulas, laboratorios y espacios de aprendizaje.",
        path: "/app/aulas",
        icon: MeetingRoomOutlinedIcon,
        load: () => import("@academics/RoomsPage.jsx"),
      },
      {
        key: "niveles",
        label: "Niveles",
        description: "Niveles, grados y cursos del nivel.",
        path: "/app/niveles",
        icon: AccountTreeOutlinedIcon,
        load: () => import("@academics/LevelsPage.jsx"),
      },
      {
        key: "cursos",
        label: "Cursos",
        description: "Catálogo de cursos de la institución.",
        path: "/app/cursos",
        icon: MenuBookOutlinedIcon,
        load: () => import("@academics/SubjectsPage.jsx"),
      },
      {
        key: "asignaciones",
        label: "Asignaciones docentes",
        description: "Qué docente da qué curso en qué sección.",
        path: "/app/asignaciones",
        icon: AssignmentIndOutlinedIcon,
        load: () => import("@academics/TeachingAssignmentsPage.jsx"),
      },
    ],
  },
  {
    key: "operacion",
    label: "Operación diaria",
    items: [
      {
        key: "matriculas",
        label: "Matrículas",
        description: "Matrícula, reinscripción e historial por estudiante.",
        path: "/app/matriculas",
        icon: HowToRegOutlinedIcon,
        permissions: MODULE_PERMISSIONS.matriculas,
        load: () => import("@enrolments/EnrolmentsPage.jsx"),
      },
      {
        key: "asistencia",
        label: "Asistencia",
        description: "Movimientos de jornada y estado del día.",
        path: "/app/asistencia",
        icon: FactCheckOutlinedIcon,
        permissions: MODULE_PERMISSIONS.asistencia,
        load: () => import("@attendance/AttendancePage.jsx"),
      },
      {
        key: "evaluacion",
        label: "Evaluación",
        description: "Unidades, ventanas de captura y recuperación.",
        path: "/app/evaluacion",
        icon: GradingOutlinedIcon,
        permissions: MODULE_PERMISSIONS.evaluacion,
        load: () => import("@evaluation/EvaluationPage.jsx"),
      },
      {
        key: "informe-notas",
        label: "Informe de notas",
        description: "Notas en PDF por grado, sección o estudiante.",
        path: "/app/informe-de-notas",
        icon: PictureAsPdfOutlinedIcon,
        permissions: MODULE_PERMISSIONS["informe-notas"],
        load: () => import("@evaluation/GradeReportPage.jsx"),
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
        key: "emision-documental",
        label: "Emisión documental",
        description: "Emisión, lotes, entregas y verificación.",
        path: "/app/emision-documental",
        icon: PictureAsPdfOutlinedIcon,
        permissions: MODULE_PERMISSIONS["emision-documental"],
        load: () => import("@documents/DocumentIssuancePage.jsx"),
      },
      {
        key: "alertas",
        label: "Alertas",
        description: "Alertas de asistencia y su atención.",
        path: "/app/alertas",
        icon: NotificationsActiveOutlinedIcon,
        permissions: MODULE_PERMISSIONS.alertas,
        load: () => import("@reporting/AlertsPage.jsx"),
      },
      {
        key: "almacenamiento-documental",
        label: "Almacenamiento",
        description: "Consumo y capacidad de los expedientes documentales.",
        path: "/app/almacenamiento-documental",
        icon: StorageOutlinedIcon,
        permissions: MODULE_PERMISSIONS["almacenamiento-documental"],
        load: () => import("@documents/DocumentStoragePage.jsx"),
      },
    ],
  },
  {
    // 2.17.6: un solo grupo para la administracion del sistema. Solo lo ve
    // quien tiene alguno de esos permisos.
    key: "administracion",
    label: "Administración",
    items: [
      {
        key: "cuentas",
        label: "Cuentas",
        description: "Acceso al sistema: cuentas, estados, sesiones y roles.",
        path: "/app/cuentas",
        icon: AdminPanelSettingsOutlinedIcon,
        permissions: MODULE_PERMISSIONS.cuentas,
        load: () => import("@auth/AccountsPage.jsx"),
      },
      {
        key: "roles",
        label: "Roles",
        description: "Roles, permisos agrupados y quién los tiene.",
        path: "/app/roles",
        icon: ManageAccountsOutlinedIcon,
        permissions: MODULE_PERMISSIONS.roles,
        load: () => import("@auth/RolesPage.jsx"),
      },
      {
        key: "personas",
        label: "Personas",
        description: "Registro base de las personas de la institución.",
        path: "/app/personas",
        icon: BadgeOutlinedIcon,
        permissions: MODULE_PERMISSIONS.personas,
        load: () => import("@people/PersonasPage.jsx"),
      },
      {
        key: "tipos-documento",
        label: "Tipos de documento",
        description: "Catálogo de tipos de documento de la institución.",
        path: "/app/tipos-documento",
        icon: CategoryOutlinedIcon,
        permissions: MODULE_PERMISSIONS["tipos-documento"],
        load: () => import("@documents/DocumentTypesPage.jsx"),
      },
      {
        key: "auditoria",
        label: "Auditoría",
        description: "Bitácora de operaciones y plazos de retención.",
        path: "/app/auditoria",
        icon: HistoryEduOutlinedIcon,
        permissions: MODULE_PERMISSIONS.auditoria,
        load: () => import("@audit/AuditPage.jsx"),
      },
      {
        key: "plataforma",
        label: "Plataforma",
        description: "Tareas programadas y respaldos.",
        path: "/app/plataforma",
        icon: MonitorHeartOutlinedIcon,
        permissions: MODULE_PERMISSIONS.plataforma,
        load: () => import("@platform/PlatformPage.jsx"),
      },
    ],
  },
];

/**
 * Rutas privadas que no son items del menu: la ficha de una cuenta y "Mi
 * cuenta" (se entra desde el menu de usuario).
 */
export const EXTRA_ROUTES = [
  {
    // C9: detalle del ciclo y tablero de preparacion, con pestañas en `?tab=`.
    key: "ciclo-detalle",
    label: "Detalle del ciclo",
    path: "/app/ciclos/:cycleId",
    load: () => import("@cycles/CycleDetailPage.jsx"),
  },
  {
    key: "cuenta-detalle",
    label: "Ficha de la cuenta",
    path: "/app/cuentas/:accountId",
    permissions: ACCOUNT_ADMIN_PERMISSIONS,
    load: () => import("@auth/AccountDetailPage.jsx"),
  },
  {
    key: "mi-cuenta",
    label: "Mi cuenta",
    path: "/app/mi-cuenta",
    load: () => import("@auth/MyAccountPage.jsx"),
  },
];

/** Todos los modulos en una lista plana, panel incluido. */
export const ALL_MODULES = [
  HOME_ITEM,
  ...NAV_GROUPS.flatMap((group) => group.items),
];

/** ¿Puede la cuenta usar este modulo? Sin `permissions`, basta la sesion. */
export function canViewModule(user, item) {
  return Boolean(user) && canAccessModule(user, item);
}

/** Grupos con sus items filtrados por permiso; se omiten los que quedan vacios. */
export function visibleGroups(user) {
  return NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => canViewModule(user, item)),
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
