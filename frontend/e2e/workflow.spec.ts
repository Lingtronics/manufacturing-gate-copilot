import { test, expect } from "@playwright/test";

test("clean offline workflow, roles, citations and idempotent publication", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Dashboard", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Run assessment", exact: true }),
  ).toBeEnabled();
  await page
    .getByRole("button", { name: "Run assessment", exact: true })
    .click();
  await expect(
    page.getByText("Assessment generated from the source snapshot.", {
      exact: false,
    }),
  ).toBeVisible();
  await expect(page.getByText("9 of 15 requirements validated")).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/dashboard.png",
    fullPage: true,
  });
  await page
    .locator("nav")
    .getByRole("button", { name: /Evidence Explorer/ })
    .click();
  await page.getByRole("textbox", { name: "Search evidence" }).fill("DOC-004");
  await expect(page.locator(".source-card")).toHaveCount(2);
  await expect(
    page
      .locator(".source-card")
      .first()
      .getByText("CONFLICTING", { exact: true }),
  ).toBeVisible();
  await page.locator(".citation summary").first().click();
  await expect(page.locator("blockquote").first()).toContainText("accepted");
  await page.screenshot({
    path: "../docs/screenshots/evidence.png",
    fullPage: true,
  });
  await page
    .locator("nav")
    .getByRole("button", { name: /Gate Assessment/ })
    .click();
  await expect(
    page.getByRole("button", { name: "Acknowledge review" }),
  ).toBeDisabled();
  await page.getByLabel("Demo identity").selectOption("Reviewer");
  await expect(
    page.getByText("Signed in as demo Reviewer.", { exact: false }),
  ).toBeVisible();
  await page
    .getByLabel("Reviewer note")
    .fill(
      "Synthetic risks acknowledged for review publication. Blockers remain unresolved; no launch authorised.",
    );
  await page.getByRole("button", { name: "Acknowledge review" }).click();
  await expect(
    page.getByText("Human review recorded.", { exact: false }),
  ).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/assessment.png",
    fullPage: true,
  });
  await page
    .locator("nav")
    .getByRole("button", { name: /Miro Workspace/ })
    .click();
  await expect(
    page
      .frameLocator("iframe")
      .getByRole("heading", { name: "Gate 3 · Local board preview" }),
  ).toBeVisible();
  await page.getByLabel("Demo identity").selectOption("Publisher");
  await expect(
    page.getByText("Signed in as demo Publisher.", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "1. Request approval" }).click();
  await expect(
    page.getByText("Publication approval requested.", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "2. Approve this version" }).click();
  await expect(
    page.getByText(
      "This assessment version and scene are approved for publication.",
      { exact: false },
    ),
  ).toBeVisible();
  await page.getByRole("button", { name: "3. Publish to mock" }).click();
  await expect(page.locator(".success-note")).toContainText(
    "Live Miro publication has not occurred.",
  );
  const before = await page.request.get(
    "/api/v1/assessments/" +
      (await (await page.request.get("/api/v1/projects/PRJ-NORTHSTAR")).json())
        .latest_assessment.id +
      "/publication",
  );
  const mappings = (await before.json()).mappings.length;
  await page
    .getByRole("button", { name: "3. Republish unchanged board" })
    .click();
  await expect(page.locator(".success-note")).toContainText('"created":0');
  const project = await (
    await page.request.get("/api/v1/projects/PRJ-NORTHSTAR")
  ).json();
  const after = await (
    await page.request.get(
      `/api/v1/assessments/${project.latest_assessment.id}/publication`,
    )
  ).json();
  expect(after.mappings.length).toBe(mappings);
  await page.screenshot({
    path: "../docs/screenshots/workspace.png",
    fullPage: true,
  });
  await page
    .locator("nav")
    .getByRole("button", { name: /Executive Value Case/ })
    .click();
  await expect(page.locator(".scenario.featured")).toContainText("238.08");
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export executive report" }).click();
  expect((await downloadPromise).suggestedFilename()).toBe(
    "northstar-executive-report.md",
  );
  await page.screenshot({
    path: "../docs/screenshots/value-case.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("responsive navigation and source search", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByLabel("Demo identity")).toBeEnabled();
  await page
    .locator("nav")
    .getByRole("button", { name: /Evidence Explorer/ })
    .click();
  await page
    .getByRole("textbox", { name: "Search evidence" })
    .fill("not-a-document");
  await expect(
    page.getByText("No matching evidence.", { exact: false }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "../docs/screenshots/mobile.png",
    fullPage: true,
  });
});
