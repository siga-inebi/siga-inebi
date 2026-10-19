import { lazy, Suspense, useState } from "react";

import Button from "@mui/material/Button";

import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";

const GrantAccessWindow = lazy(() =>
  import("./GrantAccessWindow.jsx").then((module) => ({
    default: module.GrantAccessWindow,
  }))
);

/**
 * "Dar acceso al sistema" desde la ficha de una persona ya registrada
 * (docs/ux-ui.md U1): desde un docente o desde Personas. Solo aparece con
 * `account.create`; si la persona ya tiene cuenta, el backend lo dice.
 *
 * @param {object} props
 * @param {{public_id: string, first_name?: string, last_name?: string, email?: string}} props.person
 */
export function GrantAccessButton({
  person,
  size = "small",
  variant = "text",
}) {
  const { can } = usePermissions();
  const [open, setOpen] = useState(false);
  if (!person?.public_id || !can(PERMISSION.ACCOUNT_CREATE)) return null;
  const fullName = [person.first_name, person.last_name]
    .filter(Boolean)
    .join(" ");

  return (
    <>
      <Button onClick={() => setOpen(true)} size={size} variant={variant}>
        Dar acceso al sistema
      </Button>
      {open ? (
        <Suspense fallback={null}>
          <GrantAccessWindow
            onClose={() => setOpen(false)}
            open
            person={{
              public_id: person.public_id,
              full_name: person.full_name ?? fullName,
              email: person.email ?? "",
            }}
          />
        </Suspense>
      ) : null}
    </>
  );
}
