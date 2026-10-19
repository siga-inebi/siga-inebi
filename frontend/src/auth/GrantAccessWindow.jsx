import { useEffect, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import {
  accountsService,
  activationLink,
  candidateOption,
} from "@auth/accountsService.js";
import { formatDateTime } from "@shared/utils/format.js";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { RemoteSearchSelect } from "@ui/forms/RemoteSearchSelect.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";

import { SecretHandoverDialog } from "./SecretHandoverDialog.jsx";

const CANDIDATE_SEARCH = {
  name: "account-candidates",
  fetchPage: (params) => accountsService.candidates(params),
  mapResult: candidateOption,
};

/**
 * "Dar acceso al sistema" (docs/ux-ui.md U1, D10).
 *
 * 1. Se busca a la persona ya registrada, por nombre o CUI, entre las que
 *    todavia no tienen cuenta: asi no se crea una segunda persona ni una
 *    segunda cuenta.
 * 2. Se propone el usuario `nombre.apellido` (lo sugiere el backend) y el
 *    correo de la persona; ambos se pueden corregir.
 * 3. Al crear, el codigo de activacion se muestra UNA vez con su vencimiento,
 *    para copiarlo o imprimir las instrucciones.
 *
 * No se ofrecen cuentas de encargado: el portal de padres queda fuera del
 * alcance actual (D9).
 *
 * @param {object} props
 * @param {boolean} props.open
 * @param {Function} props.onClose
 * @param {Function} [props.onCreated] Recibe la cuenta creada.
 * @param {{public_id: string, full_name: string, email?: string}} [props.person]
 *   Persona ya elegida (desde la ficha de un docente o de Personas).
 */
export function GrantAccessWindow({ onClose, onCreated, open, person }) {
  const presetOption = person
    ? {
        value: person.public_id,
        label: person.full_name,
        email: person.email,
        fullName: person.full_name,
      }
    : null;
  const [selected, setSelected] = useState(presetOption);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState(person?.email ?? "");
  const [suggesting, setSuggesting] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [created, setCreated] = useState(null);

  const suggestFor = async (option) => {
    if (!option) return;
    setSuggesting(true);
    try {
      const suggestion = await accountsService.suggestUsername(option.value);
      setUsername(suggestion.username);
    } catch {
      // Sin sugerencia la persona escribe el usuario a mano.
    } finally {
      setSuggesting(false);
    }
  };

  const presetId = person?.public_id;
  useEffect(() => {
    if (!open || !presetId) return;
    let active = true;
    setSuggesting(true);
    accountsService
      .suggestUsername(presetId)
      .then((suggestion) => {
        if (active) setUsername(suggestion.username);
      })
      .catch(() => {})
      .finally(() => {
        if (active) setSuggesting(false);
      });
    return () => {
      active = false;
    };
  }, [open, presetId]);

  const reset = () => {
    setSelected(presetOption);
    setUsername("");
    setEmail(person?.email ?? "");
    setError("");
  };

  const close = () => {
    reset();
    onClose();
  };

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    if (!selected) {
      setError("Elija a la persona que recibirá el acceso.");
      return;
    }
    if (!username.trim()) {
      setError("Escriba el usuario de la cuenta.");
      return;
    }
    setSubmitting(true);
    try {
      const account = await accountsService.provision({
        personPublicId: selected.value,
        username: username.trim(),
        email: email.trim(),
      });
      setCreated({ ...account, personName: selected.fullName });
      onCreated?.(account);
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <FloatingWindow
        busy={submitting}
        description="Crea la cuenta de una persona ya registrada. La persona la activa con un código de un solo uso."
        footer={
          <>
            <Button disabled={submitting} onClick={close} variant="text">
              Cancelar
            </Button>
            <Button
              disabled={submitting}
              form="grant-access-form"
              startIcon={
                submitting ? <CircularProgress size={16} /> : undefined
              }
              type="submit"
              variant="contained"
            >
              {submitting ? "Creando…" : "Crear cuenta"}
            </Button>
          </>
        }
        onClose={close}
        open={open && !created}
        title="Dar acceso al sistema"
        width={WINDOW_WIDTH.medium}
      >
        <Stack
          component="form"
          gap={2.5}
          id="grant-access-form"
          noValidate
          onSubmit={submit}
        >
          {error ? (
            <Alert role="alert" severity="error">
              {error}
            </Alert>
          ) : null}
          {person ? (
            <Typography variant="body2">
              Persona: <strong>{person.full_name}</strong>
            </Typography>
          ) : (
            <RemoteSearchSelect
              helperText="Busque por nombre, apellido, CUI o correo. Solo aparecen personas sin cuenta."
              label="Persona"
              name="person"
              onChange={() => {}}
              onOptionChange={(option) => {
                setSelected(option);
                setEmail(option?.email ?? "");
                setUsername("");
                suggestFor(option);
              }}
              required
              search={CANDIDATE_SEARCH}
              value={selected?.value ?? ""}
            />
          )}
          <FormTextField
            disabled={submitting || suggesting}
            fullWidth
            helperText="Sugerido como nombre.apellido. Puede cambiarlo antes de crear la cuenta."
            label="Usuario"
            name="username"
            onChange={(event) => setUsername(event.target.value)}
            required
            value={username}
          />
          <FormTextField
            disabled={submitting}
            fullWidth
            helperText="Si lo deja vacío se usa el correo registrado de la persona."
            label="Correo"
            name="email"
            onChange={(event) => setEmail(event.target.value)}
            type="email"
            value={email}
          />
        </Stack>
      </FloatingWindow>

      <SecretHandoverDialog
        details={
          created
            ? [
                { label: "Persona", value: created.personName },
                { label: "Usuario", value: created.username },
                {
                  label: "Vence",
                  value: formatDateTime(created.activation_expires_at),
                },
              ]
            : []
        }
        instructions={`Ingrese a ${activationLink()} con su usuario y este código para definir su contraseña. El código es de un solo uso.`}
        onClose={() => {
          setCreated(null);
          close();
        }}
        open={Boolean(created)}
        secret={created?.activation_code ?? ""}
        secretLabel="Código de activación"
        title="Cuenta creada"
      />
    </>
  );
}
