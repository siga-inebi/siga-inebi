import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@mui/material/styles";
import { vi } from "vitest";

import { enrolmentsService } from "@enrolments/enrolmentsService.js";
import { SectionOccupancyNotice } from "@enrolments/SectionOccupancyNotice.jsx";
import { theme } from "@theme/theme.js";

vi.mock("@enrolments/enrolmentsService.js", () => ({
  enrolmentsService: { listSectionOccupancy: vi.fn() },
}));

const ROW = {
  public_id: "s1",
  academic_cycle_id: "c1",
  capacity: 30,
  occupied_seats: 12,
  available_seats: 18,
};
const page = (row = ROW) => ({ count: 1, results: [row] });
const props = { cycleId: "c1", sectionId: "s1" };
function setup(initial = props) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const wrapper = ({ children }) => (
    <QueryClientProvider client={client}>
      <ThemeProvider theme={theme}>{children}</ThemeProvider>
    </QueryClientProvider>
  );
  return {
    ...render(<SectionOccupancyNotice {...initial} />, { wrapper }),
    wrapper,
  };
}

describe("cupo visible de la sección M7", () => {
  beforeEach(() =>
    enrolmentsService.listSectionOccupancy.mockReset().mockResolvedValue(page())
  );

  it("espera la selección y consulta solo ciclo y sección elegidos", async () => {
    const { rerender } = setup({ cycleId: "c1", sectionId: "" });
    expect(screen.getByText(/Seleccione una sección/)).toBeInTheDocument();
    expect(enrolmentsService.listSectionOccupancy).not.toHaveBeenCalled();
    rerender(<SectionOccupancyNotice {...props} />);
    expect(await screen.findByText("18")).toBeInTheDocument();
    expect(screen.getByText("30")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(
      enrolmentsService.listSectionOccupancy
    ).toHaveBeenCalledExactlyOnceWith({
      academic_cycle_id: "c1",
      section_id: "s1",
    });
  });

  it("presenta cero vacantes como sección llena", async () => {
    enrolmentsService.listSectionOccupancy.mockResolvedValue(
      page({ ...ROW, occupied_seats: 30, available_seats: 0 })
    );
    setup();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Sección sin vacantes"
    );
    expect(screen.getByText("0")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "se confirma al guardar"
    );
  });

  it("distingue una sección sin límite de una sección llena", async () => {
    enrolmentsService.listSectionOccupancy.mockResolvedValue(
      page({ ...ROW, capacity: 0, occupied_seats: 55, available_seats: null })
    );
    setup();
    expect(await screen.findAllByText("Sin límite declarado")).toHaveLength(2);
    expect(screen.getByText("55")).toBeInTheDocument();
    expect(screen.queryByText(/Sección sin vacantes/)).not.toBeInTheDocument();
  });

  it("no convierte una respuesta vacía en cero vacantes", async () => {
    enrolmentsService.listSectionOccupancy.mockResolvedValue({
      count: 0,
      results: [],
    });
    setup();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No hay información de cupo"
    );
    expect(screen.queryByText("Vacantes disponibles")).not.toBeInTheDocument();
  });

  it("no presenta datos de otra sección o ciclo", async () => {
    enrolmentsService.listSectionOccupancy.mockResolvedValue(
      page({ ...ROW, academic_cycle_id: "other" })
    );
    setup();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No hay información de cupo"
    );
    expect(screen.queryByText("18")).not.toBeInTheDocument();
  });

  it("muestra el error sin reintento automático y permite reintentar", async () => {
    enrolmentsService.listSectionOccupancy.mockRejectedValueOnce(
      new Error("Consulta no autorizada.")
    );
    const user = userEvent.setup();
    setup();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Consulta no autorizada."
    );
    expect(enrolmentsService.listSectionOccupancy).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole("button", { name: "Reintentar cupo" }));
    expect(await screen.findByText("18")).toBeInTheDocument();
  });

  it("actualiza a pedido y oculta datos anteriores si la actualización falla", async () => {
    const user = userEvent.setup();
    setup();
    await screen.findByText("18");
    enrolmentsService.listSectionOccupancy.mockRejectedValueOnce(
      new Error("Sin conexión.")
    );
    await user.click(screen.getByRole("button", { name: "Actualizar cupo" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Sin conexión.");
    expect(screen.queryByText("18")).not.toBeInTheDocument();
  });

  it("ignora respuestas tardías después de elegir otra sección", async () => {
    let resolveOld;
    enrolmentsService.listSectionOccupancy.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveOld = resolve;
        })
    );
    const { rerender } = setup();
    enrolmentsService.listSectionOccupancy.mockResolvedValue(
      page({ ...ROW, public_id: "s2", available_seats: 7 })
    );
    rerender(<SectionOccupancyNotice cycleId="c1" sectionId="s2" />);
    await screen.findByText("7");
    await act(async () => resolveOld(page()));
    expect(screen.queryByText("18")).not.toBeInTheDocument();
  });

  it("consulta de nuevo al reabrir aunque exista caché de la sección", async () => {
    const { unmount, wrapper } = setup();
    await screen.findByText("18");
    unmount();
    enrolmentsService.listSectionOccupancy.mockResolvedValue(
      page({ ...ROW, occupied_seats: 30, available_seats: 0 })
    );
    render(<SectionOccupancyNotice {...props} />, { wrapper });
    expect(await screen.findByText(/Sección sin vacantes/)).toBeInTheDocument();
    expect(enrolmentsService.listSectionOccupancy).toHaveBeenCalledTimes(2);
  });

  it("relee al terminar una operación y no muestra el cupo anterior mientras consulta", async () => {
    const { rerender } = setup();
    await screen.findByText("18");
    rerender(<SectionOccupancyNotice {...props} busy />);
    expect(
      screen.getByRole("button", { name: "Actualizar cupo" })
    ).toBeDisabled();
    expect(enrolmentsService.listSectionOccupancy).toHaveBeenCalledTimes(1);
    let resolveNew;
    enrolmentsService.listSectionOccupancy.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveNew = resolve;
        })
    );
    rerender(<SectionOccupancyNotice {...props} />);
    await waitFor(() =>
      expect(enrolmentsService.listSectionOccupancy).toHaveBeenCalledTimes(2)
    );
    expect(screen.queryByText("18")).not.toBeInTheDocument();
    await act(async () =>
      resolveNew(page({ ...ROW, available_seats: 0, occupied_seats: 30 }))
    );
    expect(await screen.findByText(/Sección sin vacantes/)).toBeInTheDocument();
  });
});
