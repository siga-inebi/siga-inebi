import { beforeEach, describe, expect, test, vi } from "vitest";

import { apiClient } from "../services/apiClient.js";
import { peopleService } from "../services/peopleService.js";

const PERSON = "11111111-1111-1111-1111-111111111111";

describe("peopleService", () => {
  beforeEach(() => {
    vi.spyOn(apiClient, "get").mockResolvedValue({ count: 0, results: [] });
    vi.spyOn(apiClient, "post").mockResolvedValue({});
    vi.spyOn(apiClient, "patch").mockResolvedValue({});
    vi.spyOn(apiClient, "del").mockResolvedValue(null);
  });

  describe("query string", () => {
    test("omits empty and false parameters", async () => {
      await peopleService.listPeople({
        page: 1,
        include_inactive: false,
        search: "",
      });

      expect(apiClient.get).toHaveBeenCalledWith("/people/?page=1");
    });

    test("keeps parameters that carry a value", async () => {
      await peopleService.listPeople({ page: 2, include_inactive: true });

      expect(apiClient.get).toHaveBeenCalledWith(
        "/people/?page=2&include_inactive=true"
      );
    });

    test("drops the query string entirely when there is nothing to send", async () => {
      await peopleService.listPeople();

      expect(apiClient.get).toHaveBeenCalledWith("/people/");
    });
  });

  test("maps every person operation to its endpoint", async () => {
    await peopleService.getPerson(PERSON);
    expect(apiClient.get).toHaveBeenCalledWith(`/people/${PERSON}/`);

    await peopleService.createPerson({ first_name: "Ana", last_name: "Gomez" });
    expect(apiClient.post).toHaveBeenCalledWith("/people/", {
      first_name: "Ana",
      last_name: "Gomez",
    });

    await peopleService.updatePerson(PERSON, { phone_number: "50212345678" });
    expect(apiClient.patch).toHaveBeenCalledWith(`/people/${PERSON}/`, {
      phone_number: "50212345678",
    });

    await peopleService.deactivatePerson(PERSON);
    expect(apiClient.del).toHaveBeenCalledWith(`/people/${PERSON}/`);
  });
});
