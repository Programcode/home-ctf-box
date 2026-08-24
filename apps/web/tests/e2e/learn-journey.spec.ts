import { expect, test, type Page, type Route } from '@playwright/test';

/**
 * Mocked-API journey: enroll -> open path -> read module -> pass quiz ->
 * mark section complete. Every backend call is intercepted at the
 * same-origin proxy (/api/or/...), so no FastAPI instance is needed.
 */

const PATHS = [
  {
    slug: 'web-foundations',
    title: 'Web Foundations',
    version: '1.2.0',
    difficulty: 'beginner',
    estimated_minutes: 90,
    summary: 'HTTP mechanics, cookies, and the first steps of web exploitation.',
    capstones: [],
    certificate: true,
    enrollment_state: null,
  },
  {
    slug: 'net-recon',
    title: 'Network Recon',
    version: '1.0.0',
    difficulty: 'intermediate',
    estimated_minutes: 120,
    summary: 'Mapping networks from the outside in with passive and active tooling.',
    capstones: ['dmz-lab'],
    certificate: true,
    enrollment_state: 'paused',
  },
];

const PATH_DETAIL = {
  ...PATHS[0],
  enrollment_state: null as string | null,
  modules: [
    {
      slug: 'intro-web',
      title: 'How the Web Talks',
      optional_branch: false,
      sections: [
        {
          id: 's1',
          title: 'Requests and responses',
          order_index: 0,
          optional_branch: false,
          prerequisites: [],
          completed: true,
        },
        {
          id: 's2',
          title: 'Check your understanding',
          order_index: 1,
          optional_branch: false,
          prerequisites: [{ module: 'intro-web', section: 's1' }],
          completed: false,
        },
      ],
    },
  ],
};

const MODULE = {
  slug: 'intro-web',
  title: 'How the Web Talks',
  version: '1.0.0',
  summary: 'A short tour of HTTP requests, responses, and state.',
  objectives: [
    'Explain the request lifecycle between browser and origin server.',
    'Identify where session state can leak.',
  ],
  labs: [],
  cheat_sheet: null,
  sections: [
    {
      id: 's1',
      title: 'Requests and responses',
      blocks: [
        { type: 'prose', markdown: 'A browser sends a **request**; the server answers.' },
        { type: 'code', language: 'http', code: 'GET / HTTP/1.1\nHost: example.net' },
      ],
    },
    {
      id: 's2',
      title: 'Check your understanding',
      blocks: [
        {
          type: 'quiz',
          question_id: 'q1',
          question: 'Which method fetches a resource without changing server state?',
          options: [
            { id: 'opt-a', text: 'POST' },
            { id: 'opt-b', text: 'GET' },
            { id: 'opt-c', text: 'DELETE' },
          ],
        },
      ],
    },
  ],
};

async function mockLearningApi(
  page: Page,
  quizOutcome: { passed: boolean },
  langProbeStatus = 404,
): Promise<{ enrollBody: () => string | null; quizBody: () => string | null }> {
  const captured: Record<string, string | null> = { enroll: null, quiz: null };

  await page.route('**/api/or/learning/paths', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(PATHS) }),
  );
  await page.route('**/api/or/learning/paths/web-foundations', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(PATH_DETAIL),
    }),
  );
  await page.route('**/api/or/learning/modules/intro-web*', (route: Route) => {
    if (route.request().method() !== 'GET') {
      return route.fulfill({ status: 405, body: '' });
    }
    // The language probe carries ?lang=<code>; its status decides whether
    // the reading pane shows the switcher at all.
    const url = new URL(route.request().url());
    if (url.searchParams.has('lang')) {
      return route.fulfill({ status: langProbeStatus, body: '' });
    }
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MODULE),
    });
  });
  await page.route('**/api/or/learning/modules/intro-web/sections/s2/complete', (route) =>
    route.request().method() !== 'POST'
      ? route.fulfill({ status: 405, body: '' })
      : route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            enrollment_id: 'e1',
            module_slug: 'intro-web',
            section_id: 's2',
            already_completed: false,
            path_completed: false,
          }),
        }),
  );

  await page.route('**/api/or/learning/paths/web-foundations/enroll', (route) => {
    captured.enroll = route.request().postData();
    // Mirror the real backend: enrollment state persists on later reads.
    PATH_DETAIL.enrollment_state = 'active';
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ enrollment_id: 'e1', path_slug: 'web-foundations', state: 'active' }),
    });
  });

  await page.route('**/api/or/learning/quiz/s2/attempt', (route) => {
    captured.quiz = route.request().postData();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        attempt_id: 'att-1',
        section_id: 's2',
        passed: quizOutcome.passed,
        results: [{ question_id: 'q1', correct: quizOutcome.passed }],
      }),
    });
  });

  return {
    enrollBody: () => captured.enroll ?? null,
    quizBody: () => captured.quiz ?? null,
  };
}

test('enroll -> module -> quiz pass -> section complete', async ({ page }) => {
  const captured = await mockLearningApi(page, { passed: true }, 200);

  await page.goto('/learn', { waitUntil: 'load' });
  await expect(page.getByRole('heading', { name: 'Learning paths' })).toBeVisible();
  const card = page.locator('li').filter({ hasText: 'Web Foundations' }).first();
  await expect(card.getByText('90 min')).toBeVisible();

  // Enrolling flips the card into its in-progress state.
  await card.getByRole('button', { name: 'Enroll' }).click();
  await expect(card.getByText('In progress')).toBeVisible();
  expect(captured.enrollBody()).not.toBeNull();

  // Path outline shows the module tree with per-section completion state.
  await page
    .getByRole('link', { name: /Web Foundations/ })
    .first()
    .click();
  await expect(page.getByRole('heading', { name: 'Web Foundations' })).toBeVisible();
  await expect(page.getByText('1/2 required sections complete')).toBeVisible();
  await expect(page.getByText('Not started')).toHaveCount(1);
  await expect(page.getByText('Requires intro-web/s1')).toBeVisible();

  // Reading pane renders prose, code, and the quiz block.
  await page.getByRole('link', { name: 'How the Web Talks' }).first().click();
  await expect(page.getByRole('heading', { level: 1, name: 'How the Web Talks' })).toBeVisible();
  await expect(page.getByText('A browser sends a request; the server answers.')).toBeVisible();

  // The probe for ?lang=hu answers 200, so the switcher offers both languages.
  const langSelect = page.getByLabel('Language');
  await expect(langSelect).toBeVisible();
  await expect(langSelect.locator('option')).toHaveCount(2);

  const s2 = page.locator('article#s2');
  await s2.getByRole('checkbox', { name: 'GET' }).check();
  await s2.getByRole('button', { name: 'Submit answers' }).click();
  await expect(page.getByText('All questions correct.')).toBeVisible();
  expect(captured.quizBody()).toContain('"answers"');
  expect(captured.quizBody()).toContain('q1');

  // Marking complete reflects immediately in the section header.
  await s2.getByRole('button', { name: 'Mark complete' }).click();
  await expect(s2.getByText('Completed')).toBeVisible();
});

test('quiz failure feedback offers retry without revealing the key', async ({ page }) => {
  await mockLearningApi(page, { passed: false }, 404);

  await page.goto('/learn/web-foundations/intro-web', { waitUntil: 'load' });
  const s2 = page.locator('article#s2');
  await expect(s2).toBeVisible();

  // With the lang probe answering 404 the switcher stays hidden entirely.
  await expect(page.getByLabel('Language')).toHaveCount(0);

  await s2.getByRole('checkbox', { name: 'POST' }).check();
  await s2.getByRole('button', { name: 'Submit answers' }).click();
  await expect(s2.getByText('Some answers are wrong. You can retry.')).toBeVisible();
  await expect(s2.getByText('Not quite. Review the material and try again.')).toBeVisible();
  // The correct option must never be announced by failed feedback.
  await expect(s2.getByText('Correct.')).toHaveCount(0);
});
