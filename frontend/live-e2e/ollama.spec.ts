import { test, expect } from "@playwright/test";

test("actual local Ollama output reaches the assessment UI and is cached", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Run assessment", exact: true }),
  ).toBeEnabled();
  const generated = page.waitForResponse(
    (r) => r.url().endsWith("/explanation") && r.status() === 200,
    { timeout: 60000 },
  );
  await page
    .getByRole("button", { name: "Run assessment", exact: true })
    .click();
  const explanation = await (await generated).json();
  expect(explanation.provider).toBe("llm");
  expect(explanation.runtime_status).toBe("model_used");
  expect(explanation.fallback_reason).toBeNull();
  await page
    .locator("nav")
    .getByRole("button", { name: /Gate Assessment/ })
    .click();
  await expect(
    page.getByText("validated model output", { exact: false }),
  ).toBeVisible();
  await page
    .getByText("Model-selected review sequence", { exact: true })
    .click();
  await expect(
    page.getByText("AI interpretation", { exact: true }),
  ).toBeVisible();
  const project = await (
    await page.request.get("/api/v1/projects/PRJ-NORTHSTAR")
  ).json();
  const result = await (
    await page.request.get(
      `/api/v1/assessments/${project.latest_assessment.id}/explanation`,
    )
  ).json();
  expect(result).toEqual(explanation);
  await page.screenshot({
    path: "../docs/screenshots/ollama-live.png",
    fullPage: true,
  });
});
