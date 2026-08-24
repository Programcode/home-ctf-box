import { expect, test, type Page } from '@playwright/test';

/**
 * Mocked-API journey: open the jeopardy board, inspect a challenge in the
 * detail modal, submit a wrong flag (inline failure), then the right one
 * (toast + subtle Solved badge). All backend calls hit /api/or/... and are
 * intercepted.
 */

const CHALLENGES = [
  {
    slug: 'base64-or-not',
    name: 'Base64 or Not',
    category: 'crypto',
    difficulty: 3,
    scoring: 'static',
    points: 100,
    solve_count: 12,
  },
  {
    slug: 'sqli-101',
    name: 'SQLi 101',
    category: 'web',
    difficulty: 5,
    scoring: 'dynamic',
    points: 180,
    solve_count: 4,
  },
];

const DETAIL = {
  ...CHALLENGES[0],
  description:
    '# Decode me\n\nThe payload hides a **flag**. Wrap it as `flag{...}` before submitting.',
  files: [{ id: 'f1', filename: 'payload.txt', size: 24, sha256: 'deadbeef' }],
  solved_by_me: false,
};

async function mockChallengeApi(
  page: Page,
  submitOutcome: { correct: boolean; already?: boolean },
): Promise<{ submitBody: () => string | null }> {
  let submitPayload: string | null = null;

  await page.route('**/api/or/challenges', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(CHALLENGES),
    }),
  );
  await page.route('**/api/or/challenges/base64-or-not', (route) => {
    if (route.request().method() !== 'GET') {
      return route.continue();
    }
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(DETAIL),
    });
  });
  await page.route('**/api/or/challenges/base64-or-not/submit', (route) => {
    if (route.request().method() !== 'POST') {
      return route.continue();
    }
    submitPayload = route.request().postData();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        correct: submitOutcome.correct,
        already_solved: submitOutcome.already ?? false,
        points: submitOutcome.correct ? 100 : null,
        first_blood: false,
      }),
    });
  });

  return { submitBody: () => submitPayload };
}

async function openModal(page: Page): Promise<void> {
  await page.goto('/challenges', { waitUntil: 'load' });

  // Board groups by category with points and solve counts on each tile.
  const cryptoSection = page.locator('section').filter({ hasText: 'crypto' }).first();
  await expect(cryptoSection.getByRole('heading', { name: /crypto/ })).toBeVisible();
  await expect(
    page.getByRole('button', { name: /Base64 or Not, 100 points, 12 solves/ }),
  ).toBeVisible();

  await page.getByRole('button', { name: /Base64 or Not, 100 points, 12 solves/ }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('heading', { name: 'Decode me' })).toBeVisible();
  await expect(dialog.getByRole('link', { name: 'payload.txt' })).toHaveAttribute(
    'href',
    '/api/or/challenges/base64-or-not/files/f1',
  );
}

test('wrong flag shows inline error without marking solved', async ({ page }) => {
  await mockChallengeApi(page, { correct: false });
  await openModal(page);

  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Flag').fill('flag{wrong-guess}');
  await dialog.getByRole('button', { name: 'Submit flag' }).click();

  await expect(dialog.getByText('That flag is not correct. Try again.')).toBeVisible();
  // The tile must not flip to its solved state.
  await expect(page.locator('body')).not.toContainText('+100 points awarded');
});

test('correct flag awards points, toasts, and marks the tile solved', async ({ page }) => {
  const captured = await mockChallengeApi(page, { correct: true });
  await openModal(page);

  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Flag').fill('flag{b64_decoded}');
  await dialog.getByRole('button', { name: 'Submit flag' }).click();

  await expect(dialog.getByText('+100 points awarded.')).toBeVisible();
  expect(captured.submitBody()).toContain('flag{b64_decoded}');

  // Subtle celebration: toast plus badge, no confetti.
  await expect(page.getByText('Flag accepted')).toBeVisible();
  await expect(dialog.getByText('Solved')).toHaveCount(1);

  // Escape closes the native dialog; the board reflects the solve.
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
  await expect(page.getByText('1 solved by you')).toBeVisible();
  await expect(
    page.getByRole('button', { name: /Base64 or Not, 100 points, 12 solves, solved/ }),
  ).toBeVisible();
});
