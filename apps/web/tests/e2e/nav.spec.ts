import { expect, test } from '@playwright/test';

test('desktop nav marks the active route', async ({ page }) => {
  await page.goto('/challenges', { waitUntil: 'load' });

  const challengesLink = page.getByRole('link', { name: 'Challenges' }).first();
  await expect(challengesLink).toHaveAttribute('aria-current', 'page');
  // Neighbouring links stay unmarked.
  await expect(page.getByRole('link', { name: 'Learn' }).first()).not.toHaveAttribute(
    'aria-current',
    'page',
  );
});

test('mobile disclosure menu opens, navigates, and closes', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 720 });
  await page.goto('/', { waitUntil: 'load' });

  const toggle = page.getByRole('button', { name: 'Menu' });
  await toggle.click();
  const panel = page.getByRole('navigation', { name: 'Mobile navigation' });
  await expect(panel).toBeVisible();
  await expect(toggle).toHaveAttribute('aria-expanded', 'true');

  // Escape closes the panel and returns focus to the toggle.
  await page.keyboard.press('Escape');
  await expect(panel).not.toBeVisible();
  await expect(toggle).toBeFocused();

  await toggle.click();
  await panel.getByRole('link', { name: 'Learn' }).click();
  await page.waitForURL('**/learn');
  await expect(panel).not.toBeVisible();
});
