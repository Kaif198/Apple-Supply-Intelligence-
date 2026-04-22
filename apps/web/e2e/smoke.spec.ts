import { expect, test } from "@playwright/test";

/**
 * End-to-end smoke test.
 *
 * Walks every top-nav destination and asserts the page renders its
 * characteristic hero eyebrow plus a level-1 heading. The synthetic
 * feature store seeded in CI guarantees every API response has data,
 * so these assertions are stable even without real keys.
 *
 * Eyebrow copy is verified via substring so small editorial tweaks
 * (e.g. "Macro" vs "Macro & Causal") don't flake the suite.
 */

const PAGES: { path: string; eyebrow: RegExp }[] = [
  { path: "/", eyebrow: /Apple Supply Chain Intelligence/i },
  { path: "/commodities", eyebrow: /Commodities/i },
  { path: "/suppliers", eyebrow: /Suppliers/i },
  { path: "/network", eyebrow: /Network/i },
  { path: "/events", eyebrow: /Events/i },
  { path: "/valuation", eyebrow: /Valuation/i },
  { path: "/macro", eyebrow: /Macro/i },
];

test.describe("ASCIIP smoke", () => {
  for (const { path, eyebrow } of PAGES) {
    test(`loads ${path}`, async ({ page }) => {
      await page.goto(path);
      // Hero eyebrow is the page's identity strip above the title.
      await expect(page.getByText(eyebrow).first()).toBeVisible();
      // Every page renders exactly one level-1 heading inside PageHero.
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      // TopNav is always present and links to every primary section.
      await expect(
        page.getByRole("link", { name: "Commodities" }),
      ).toBeVisible();
      await expect(
        page.getByRole("link", { name: "Suppliers" }),
      ).toBeVisible();
    });
  }

  test("top-nav navigates between sections", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Valuation" }).click();
    await expect(page).toHaveURL(/\/valuation$/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("health endpoint is reachable", async ({ request }) => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";
    const res = await request.get(`${apiUrl}/health`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.service).toBe("asciip-api");
  });
});
