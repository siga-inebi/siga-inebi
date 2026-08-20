import { act, renderHook } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { useBatchSubmit } from "@shared/crud/useBatchSubmit.js";

const describeItem = (item) => `item ${item}`;

describe("useBatchSubmit", () => {
  test("que una falle no cancela las demas", async () => {
    // Cortar en el primer error dejaria la mitad del lote cargada sin decir
    // cual mitad, y quien captura tendria que adivinar por donde retomar.
    const createOne = vi
      .fn()
      .mockResolvedValueOnce({})
      .mockRejectedValueOnce(new Error("Cupo de seccion alcanzado."))
      .mockResolvedValueOnce({});

    const { result } = renderHook(() =>
      useBatchSubmit(createOne, describeItem)
    );

    let summary;
    await act(async () => {
      summary = await result.current.run(["a", "b", "c"]);
    });

    expect(createOne).toHaveBeenCalledTimes(3);
    expect(summary.created).toEqual(["a", "c"]);
    expect(summary.failed).toEqual([
      { label: "item b", message: "Cupo de seccion alcanzado." },
    ]);
  });

  test("las altas van en serie, no en paralelo", async () => {
    // Sesenta altas simultaneas competirian por el mismo cupo de seccion; en
    // serie el guard del backend ve un estado consistente y el rechazo cae en el
    // item que sobra, no en uno al azar.
    const enCurso = [];
    const createOne = vi.fn(async (item) => {
      enCurso.push(item);
      expect(enCurso).toHaveLength(1);
      await Promise.resolve();
      enCurso.pop();
    });

    const { result } = renderHook(() =>
      useBatchSubmit(createOne, describeItem)
    );

    await act(async () => {
      await result.current.run(["a", "b", "c"]);
    });

    expect(createOne.mock.calls.map(([item]) => item)).toEqual(["a", "b", "c"]);
  });

  test("expone el resumen en el estado y lo devuelve", async () => {
    // Devolverlo ademas de guardarlo importa: quien llama necesita saber que se
    // creo para refrescar su tabla sin esperar un render.
    const { result } = renderHook(() =>
      useBatchSubmit(vi.fn().mockResolvedValue({}), describeItem)
    );

    let summary;
    await act(async () => {
      summary = await result.current.run(["a"]);
    });

    expect(summary.created).toEqual(["a"]);
    expect(result.current.result.created).toEqual(["a"]);
    expect(result.current.submitting).toBe(false);
  });

  test("reset limpia el resumen anterior", async () => {
    // Cambiar de ciclo o de seccion invalida el resumen: dejarlo en pantalla
    // haria parecer que esas altas pertenecen a la seleccion nueva.
    const { result } = renderHook(() =>
      useBatchSubmit(vi.fn().mockResolvedValue({}), describeItem)
    );

    await act(async () => {
      await result.current.run(["a"]);
    });
    expect(result.current.result).not.toBeNull();

    act(() => result.current.reset());

    expect(result.current.result).toBeNull();
  });

  test("un lote vacio no llama al backend", async () => {
    const createOne = vi.fn();
    const { result } = renderHook(() =>
      useBatchSubmit(createOne, describeItem)
    );

    let summary;
    await act(async () => {
      summary = await result.current.run([]);
    });

    expect(createOne).not.toHaveBeenCalled();
    expect(summary).toEqual({ created: [], failed: [] });
  });
});
