import { expect, test, type Page } from '@playwright/test';

async function focusedHref(page: Page): Promise<string | null> {
  return page.evaluate(() => {
    const active = document.activeElement;
    if (active instanceof HTMLAnchorElement) {
      return active.getAttribute('href');
    }
    return null;
  });
}

/** Walks the page with a single key until `predicate` matches the focused link. */
async function walkTo(
  page: Page,
  key: 'Tab' | 'Shift+Tab',
  predicate: (href: string | null) => boolean,
  maxSteps = 40,
): Promise<void> {
  for (let step = 0; step < maxSteps; step += 1) {
    await page.keyboard.press(key);
    const href = await focusedHref(page);
    if (predicate(href)) {
      return;
    }
  }
  throw new Error(`keyboard walk did not reach target within ${maxSteps} steps`);
}

test('keyboard-only journey: nav -> catalog card -> room page', async ({ page }) => {
  await page.goto('/', { waitUntil: 'load' });

  // First tab stop is the skip link; it sits off-screen until focused.
  const skipLink = page.getByRole('link', { name: 'Skip to content' });
  await page.keyboard.press('Tab');
  await expect(skipLink).toBeFocused();
  await expect(skipLink).toBeInViewport();

  // Activating it moves focus into main content.
  await page.keyboard.press('Enter');
  await expect(page.locator('#main-content')).toBeFocused();

  // Walk back up to the top navigation and follow the Catalog link.
  await walkTo(page, 'Shift+Tab', (href) => href === '/catalog');
  await page.keyboard.press('Enter');
  await page.waitForURL('**/catalog');

  // On the catalog, tab through the filter controls to the first room card.
  await expect(page.getByRole('heading', { name: 'Room catalog' })).toBeVisible();
  await walkTo(page, 'Tab', (href) => href !== null && href.startsWith('/catalog/'));
  await page.keyboard.press('Enter');
  await page.waitForURL('**/catalog/**');

  // The room detail page renders and its start-lab control explains itself
  // when signed out.
  const heading = page.getByRole('heading', { level: 1 });
  await expect(heading).toBeVisible();
  const startButton = page.getByRole('button', { name: 'Start lab', exact: true });
  await startButton.scrollIntoViewIfNeeded();
  await expect(startButton).toBeDisabled();
});
