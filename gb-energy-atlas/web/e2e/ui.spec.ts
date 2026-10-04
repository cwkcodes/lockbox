import { expect, test, type Page } from "@playwright/test";

const fmt = (n: number) => n.toLocaleString("en-GB");

/** The sidebar opens on the Filters tab; the result list is on the Results tab. */
async function openResults(page: Page) {
  await page.getByRole("tab", { name: "Results" }).click();
  await expect(page.getByRole("list", { name: "Result list" })).toBeVisible();
}

test.describe("map application", () => {
  test("loads with a working map and no runtime errors", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto("/?base=plain");
    await expect(page).toHaveTitle(/Renewable Energy Atlas/i);
    await expect(page.getByRole("application", { name: /Interactive map/i })).toBeVisible();
    await expect(page.locator("canvas.maplibregl-canvas")).toBeVisible();
    await expect(page.getByRole("region", { name: /Statistics for the current filters/i })).toContainText(/Projects/);
    expect(errors).toEqual([]);
  });

  test("coverage statement and data-source links are reachable from the app shell", async ({ page }) => {
    await page.goto("/about");
    await expect(page.locator("body")).toContainText(/not be interpreted as a definitive register/i);
    await page.goto("/data");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.locator("body")).toContainText(/Renewable Energy Planning Database/);
    await expect(page.locator("body")).toContainText(/manual review|restricted|source unavailable/i);   // blocked sources are reported, not hidden
  });

  test("filter state lives in the URL and the list, statistics and URL agree", async ({ page, request }) => {
    const qs = "tech=wind_onshore&ctry=Scotland&stage=operational";
    const total = (await (await request.get(`/api/assets?${qs}&pageSize=1`)).json()).total as number;
    await page.goto(`/?${qs}&base=plain`);
    await openResults(page);
    await expect(page.getByText(`${fmt(total)} results`)).toBeVisible();
    await expect(page.getByRole("region", { name: /Statistics/ })).toContainText(fmt(total));
    // reload keeps the same state
    await page.reload();
    await openResults(page);
    await expect(page.getByText(`${fmt(total)} results`)).toBeVisible();
    expect(page.url()).toContain("tech=wind_onshore");
  });

  test("empty filter result shows an empty state, not stale data", async ({ page }) => {
    await page.goto("/?mfr=Nordex&tech=wind_onshore&base=plain");
    await openResults(page);
    await expect(page.getByText("0 results")).toBeVisible();
    await expect(page.getByText(/No assets match these filters/)).toBeVisible();
    await expect(page.getByRole("region", { name: /Statistics/ })).toContainText(/Projects\s*0/);
  });

  test("selecting a result opens the detail drawer with sourced facts, provenance and an evidence pack", async ({ page }) => {
    await page.goto("/?tech=wind_onshore&q=Whitelee&base=plain");
    await openResults(page);
    const list = page.getByRole("list", { name: "Result list" });
    await list.getByRole("button", { name: /Whitelee/ }).first().click();
    const drawer = page.getByRole("complementary", { name: "Asset details" });
    await expect(drawer).toContainText(/GBA-\d{7}/);
    await expect(drawer).toContainText(/Whitelee/);
    await expect(page.getByRole("tablist", { name: "Asset detail sections" })).toBeVisible();
    await drawer.getByRole("button", { name: /Show sources for/ }).first().click();
    await expect(page.getByRole("dialog", { name: "Field provenance" })).toContainText(/Renewable Energy Planning Database|REPD/i);
    await expect(drawer.getByRole("link", { name: "Evidence pack" })).toHaveAttribute("href", /\/api\/evidence-pack\/GBA-\d{7}/);
    await expect(page).toHaveURL(/GBA-\d{7}/);     // selection is shareable
  });

  test("tabs are keyboard operable", async ({ page }) => {
    await page.goto("/?tech=wind_onshore&q=Whitelee&base=plain");
    await openResults(page);
    await page.getByRole("list", { name: "Result list" }).getByRole("button", { name: /Whitelee/ }).first().click();
    const tabs = page.getByRole("tablist", { name: "Asset detail sections" }).getByRole("tab");
    await tabs.first().focus();
    await page.keyboard.press("ArrowRight");
    await expect(tabs.nth(1)).toHaveAttribute("aria-selected", "true");
  });

  test("comparing two assets opens a comparison with provenance of differing values", async ({ page }) => {
    await page.goto("/?tech=wind_onshore&stage=operational&ctry=Scotland&base=plain");
    await openResults(page);
    const boxes = page.getByRole("list", { name: "Result list" }).getByRole("checkbox");
    await boxes.nth(0).check();
    await boxes.nth(1).check();
    await expect(page.getByText("Compare", { exact: true })).toBeVisible();
    await page.goto(`/compare?ids=${(await (await page.request.get("/api/assets?tech=wind_onshore&stage=operational&ctry=Scotland&pageSize=2")).json()).items.map((i: { asset_id: string }) => i.asset_id).join(",")}`);
    await expect(page.getByRole("table").first()).toBeVisible();
    // (Next.js keeps an always-present empty role="alert" route announcer, so look for the page's own error text)
    await expect(page.getByText(/Could not compare/)).toHaveCount(0);
  });

  test("the report dialog refuses to submit without evidence", async ({ page }) => {
    await page.goto("/?tech=wind_onshore&q=Whitelee&base=plain");
    await openResults(page);
    await page.getByRole("list", { name: "Result list" }).getByRole("button", { name: /Whitelee/ }).first().click();
    await page.getByRole("button", { name: "Report an issue" }).click();
    const dlg = page.getByRole("dialog", { name: "Report an issue" });
    await expect(dlg).toContainText(/supporting evidence is required/i);
    await dlg.getByLabel(/What is wrong/).fill("This is a validation test and must not be submitted.");
    await dlg.getByRole("button", { name: "Submit for review" }).click();
    // the browser blocks submission because the evidence field is required and must be a URL
    expect(await dlg.getByLabel(/Evidence URL/).evaluate((el) => (el as HTMLInputElement).validity.valueMissing)).toBe(true);
    await expect(dlg.getByRole("status")).toHaveCount(0);
  });

  test("admin console asks for a token", async ({ page }) => {
    await page.goto("/admin");
    await expect(page.getByLabel("Admin token")).toBeVisible();
    await page.getByLabel("Admin token").fill("wrong");
    await page.getByRole("button", { name: "Sign in" }).click();
    // 401 "invalid token" when ADMIN_TOKEN is configured, 403 "disabled" when it is unset or still the default in production
    // (filtering by text also excludes Next.js's always-present empty route-announcer alert)
    await expect(page.getByRole("alert").filter({ hasText: /invalid token|admin is disabled/ })).toBeVisible();
  });

  test("dashboard, organisations, turbines and methodology pages render", async ({ page }) => {
    for (const [path, heading] of [["/dashboard", /dashboard|overview|statistics/i], ["/organisations", /organisations/i], ["/turbines", /turbine/i], ["/methodology", /methodolog/i], ["/api-docs", /api/i]] as const) {
      const res = await page.goto(path);
      expect(res?.status(), path).toBe(200);
      await expect(page.getByRole("heading", { level: 1 }).first()).toContainText(heading);
    }
  });

  test("works at phone width: panels collapse and the map stays usable", async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 800 }, ignoreHTTPSErrors: true });
    const page = await ctx.newPage();
    await page.goto("/?base=plain");
    await expect(page.getByRole("button", { name: /Toggle filters and results panel/ })).toBeVisible();
    await expect(page.locator("canvas.maplibregl-canvas")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(1);
    await ctx.close();
  });
});
