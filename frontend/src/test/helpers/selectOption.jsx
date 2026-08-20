import { screen, within } from "@testing-library/react";

/**
 * Elige una opcion en un `Select` de MUI.
 *
 * `userEvent.selectOptions` solo funciona con un `<select>` nativo. El Select de
 * MUI es un boton que abre un `<ul role="listbox">` en un portal, asi que hay que
 * abrirlo y hacer clic en la opcion. Este helper existe para no repetir esos dos
 * pasos —y su explicacion— en cada test.
 *
 * El listado de opciones se busca SIEMPRE en `screen`, incluso con `container`:
 * vive en un portal, fuera del arbol del dialogo o de la tarjeta. `container`
 * acota solo la busqueda del campo, que es donde aparecen los homonimos —
 * "Jornada" existe en tres formularios distintos de la pantalla de asistencia.
 *
 * @param {object} user   Instancia de `userEvent.setup()`.
 * @param {RegExp|string} label Etiqueta del campo.
 * @param {RegExp|string} optionName Texto de la opcion a elegir.
 * @param {HTMLElement} [container] Ambito donde buscar el campo.
 */
export async function selectOption(user, label, optionName, container) {
  const scope = container ? within(container) : screen;
  await user.click(scope.getByLabelText(label));
  const listbox = await screen.findByRole("listbox");
  await user.click(within(listbox).getByRole("option", { name: optionName }));
}
