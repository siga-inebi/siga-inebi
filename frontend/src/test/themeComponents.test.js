import { describe, expect, it } from "vitest";

import { MuiTooltip } from "@theme/components/MuiSurfaces.js";
import { darkPalette } from "@theme/palette/dark.js";
import { lightPalette } from "@theme/palette/light.js";

describe("MuiTooltip", () => {
  it("usa el color de superficie como texto sobre el fondo de texto", () => {
    const theme = {
      vars: {
        palette: {
          background: { paper: "var(--mui-palette-background-paper)" },
          text: { primary: "var(--mui-palette-text-primary)" },
        },
      },
    };

    const styles = MuiTooltip.styleOverrides.tooltip({ theme });

    expect(styles).toMatchObject({
      backgroundColor: "var(--mui-palette-text-primary)",
      color: "var(--mui-palette-background-paper)",
    });
  });
});

describe("superficie del panel operativo", () => {
  it("define fondo y texto propios para cada modo de color", () => {
    expect(lightPalette.surfaces.dashboardHeroStart).not.toBe(
      darkPalette.surfaces.dashboardHeroStart
    );
    expect(lightPalette.surfaces.dashboardHeroText).not.toBe(
      darkPalette.surfaces.dashboardHeroText
    );
    expect(lightPalette.surfaces.dashboardHeroAction).toBe(
      lightPalette.surfaces.dashboardHeroAccent
    );
    expect(darkPalette.surfaces.dashboardHeroAction).toBe(
      darkPalette.surfaces.dashboardHeroAccent
    );
  });
});
