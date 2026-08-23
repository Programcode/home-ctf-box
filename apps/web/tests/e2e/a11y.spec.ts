import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const PAGES = ['/', '/catalog', '/login'];
const VIEWPORTS = [
  { width: 320, height: 800, name: '320px' },
  { width: 1280, height: 800, name: '1280px' },
];

for (const viewport of VIEWPORTS) {
  for (const path of PAGES) {
    test(`axe finds no violations on ${path} at ${viewport.name}`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(path, { waitUntil: 'load' });

      const results = await new AxeBuilder({ page })
        // The command palette trigger is hidden below sm breakpoint by design;
        // axe color-contrast skips hidden nodes anyway.
        .analyze();

      expect(
        results.violations,
        `${path} at ${viewport.name}: ${JSON.stringify(
          results.violations.map((v) => ({
            id: v.id,
            impact: v.impact,
            nodes: v.nodes.slice(0, 3).map((n) => n.target),
          })),
        )}`,
      ).toEqual([]);
    });
  }
}
