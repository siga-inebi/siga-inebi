import { beforeEach, describe, expect, test, vi } from "vitest";

import { academicsService } from "@academics/academicsService.js";
import { apiClient } from "@shared/api/apiClient.js";

const CAMPUS = "11111111-1111-1111-1111-111111111111";
const SHIFT = "22222222-2222-2222-2222-222222222222";
const LEVEL = "33333333-3333-3333-3333-333333333333";
const GRADE = "44444444-4444-4444-4444-444444444444";
const SUBJECT = "55555555-5555-5555-5555-555555555555";

describe("academicsService", () => {
  beforeEach(() => {
    vi.spyOn(apiClient, "get").mockResolvedValue({ count: 0, results: [] });
    vi.spyOn(apiClient, "post").mockResolvedValue({});
    vi.spyOn(apiClient, "patch").mockResolvedValue({});
    vi.spyOn(apiClient, "del").mockResolvedValue(null);
  });

  describe("query string", () => {
    test("omits empty and false parameters", async () => {
      await academicsService.listCampuses({
        page: 1,
        include_inactive: false,
        search: "",
      });

      expect(apiClient.get).toHaveBeenCalledWith("/academics/campuses/?page=1");
    });

    test("keeps parameters that carry a value", async () => {
      await academicsService.listCampuses({ page: 2, include_inactive: true });

      expect(apiClient.get).toHaveBeenCalledWith(
        "/academics/campuses/?page=2&include_inactive=true"
      );
    });

    test("drops the query string entirely when there is nothing to send", async () => {
      await academicsService.listCampuses();

      expect(apiClient.get).toHaveBeenCalledWith("/academics/campuses/");
    });
  });

  describe("campuses and shifts", () => {
    test("maps every campus operation to its endpoint", async () => {
      await academicsService.getCampus(CAMPUS);
      expect(apiClient.get).toHaveBeenCalledWith(
        `/academics/campuses/${CAMPUS}/`
      );

      await academicsService.createCampus({ name: "Central", code: "CEN" });
      expect(apiClient.post).toHaveBeenCalledWith("/academics/campuses/", {
        name: "Central",
        code: "CEN",
      });

      await academicsService.updateCampus(CAMPUS, { name: "Nueva" });
      expect(apiClient.patch).toHaveBeenCalledWith(
        `/academics/campuses/${CAMPUS}/`,
        { name: "Nueva" }
      );

      await academicsService.deactivateCampus(CAMPUS);
      expect(apiClient.del).toHaveBeenCalledWith(
        `/academics/campuses/${CAMPUS}/`
      );
    });

    test("nests shift creation under its campus but details under shifts", async () => {
      await academicsService.listCampusShifts(CAMPUS, { page: 1 });
      expect(apiClient.get).toHaveBeenCalledWith(
        `/academics/campuses/${CAMPUS}/shifts/?page=1`
      );

      await academicsService.createShift(CAMPUS, { name: "Matutina" });
      expect(apiClient.post).toHaveBeenCalledWith(
        `/academics/campuses/${CAMPUS}/shifts/`,
        { name: "Matutina" }
      );

      await academicsService.getShift(SHIFT);
      expect(apiClient.get).toHaveBeenCalledWith(`/academics/shifts/${SHIFT}/`);

      await academicsService.updateShift(SHIFT, { name: "Vespertina" });
      expect(apiClient.patch).toHaveBeenCalledWith(
        `/academics/shifts/${SHIFT}/`,
        { name: "Vespertina" }
      );

      await academicsService.deactivateShift(SHIFT);
      expect(apiClient.del).toHaveBeenCalledWith(`/academics/shifts/${SHIFT}/`);
    });
  });

  describe("levels and grades", () => {
    test("maps every level operation to its endpoint", async () => {
      await academicsService.listLevels({ include_inactive: true });
      expect(apiClient.get).toHaveBeenCalledWith(
        "/academics/levels/?include_inactive=true"
      );

      await academicsService.getLevel(LEVEL);
      expect(apiClient.get).toHaveBeenCalledWith(`/academics/levels/${LEVEL}/`);

      await academicsService.createLevel({ name: "Basico", sequence: 3 });
      expect(apiClient.post).toHaveBeenCalledWith("/academics/levels/", {
        name: "Basico",
        sequence: 3,
      });

      await academicsService.updateLevel(LEVEL, { sequence: 4 });
      expect(apiClient.patch).toHaveBeenCalledWith(
        `/academics/levels/${LEVEL}/`,
        { sequence: 4 }
      );

      await academicsService.deactivateLevel(LEVEL);
      expect(apiClient.del).toHaveBeenCalledWith(`/academics/levels/${LEVEL}/`);
    });

    test("nests grade creation under its level but details under grades", async () => {
      await academicsService.listLevelGrades(LEVEL);
      expect(apiClient.get).toHaveBeenCalledWith(
        `/academics/levels/${LEVEL}/grades/`
      );

      await academicsService.createGrade(LEVEL, { name: "Primero" });
      expect(apiClient.post).toHaveBeenCalledWith(
        `/academics/levels/${LEVEL}/grades/`,
        { name: "Primero" }
      );

      await academicsService.getGrade(GRADE);
      expect(apiClient.get).toHaveBeenCalledWith(`/academics/grades/${GRADE}/`);

      await academicsService.updateGrade(GRADE, { name: "Segundo" });
      expect(apiClient.patch).toHaveBeenCalledWith(
        `/academics/grades/${GRADE}/`,
        { name: "Segundo" }
      );

      await academicsService.deactivateGrade(GRADE);
      expect(apiClient.del).toHaveBeenCalledWith(`/academics/grades/${GRADE}/`);
    });
  });

  describe("subjects and their link to a level", () => {
    test("maps every subject operation to its endpoint", async () => {
      await academicsService.listSubjects({ page: 3 });
      expect(apiClient.get).toHaveBeenCalledWith("/academics/subjects/?page=3");

      await academicsService.getSubject(SUBJECT);
      expect(apiClient.get).toHaveBeenCalledWith(
        `/academics/subjects/${SUBJECT}/`
      );

      await academicsService.createSubject({ name: "Matematica" });
      expect(apiClient.post).toHaveBeenCalledWith("/academics/subjects/", {
        name: "Matematica",
      });

      await academicsService.updateSubject(SUBJECT, { name: "Matematicas" });
      expect(apiClient.patch).toHaveBeenCalledWith(
        `/academics/subjects/${SUBJECT}/`,
        { name: "Matematicas" }
      );

      await academicsService.deactivateSubject(SUBJECT);
      expect(apiClient.del).toHaveBeenCalledWith(
        `/academics/subjects/${SUBJECT}/`
      );
    });

    test("addresses the link by the level and subject pair", async () => {
      await academicsService.listLevelSubjects(LEVEL);
      expect(apiClient.get).toHaveBeenCalledWith(
        `/academics/levels/${LEVEL}/subjects/`
      );

      await academicsService.linkSubjectToLevel(LEVEL, {
        subject_id: SUBJECT,
        weekly_hours: 5,
      });
      expect(apiClient.post).toHaveBeenCalledWith(
        `/academics/levels/${LEVEL}/subjects/`,
        { subject_id: SUBJECT, weekly_hours: 5 }
      );

      await academicsService.updateLevelSubject(LEVEL, SUBJECT, {
        is_required: false,
      });
      expect(apiClient.patch).toHaveBeenCalledWith(
        `/academics/levels/${LEVEL}/subjects/${SUBJECT}/`,
        { is_required: false }
      );

      await academicsService.unlinkSubjectFromLevel(LEVEL, SUBJECT);
      expect(apiClient.del).toHaveBeenCalledWith(
        `/academics/levels/${LEVEL}/subjects/${SUBJECT}/`
      );
    });
  });
});
