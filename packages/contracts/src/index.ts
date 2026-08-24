/**
 * Typed client for the OpenRange API (FastAPI).
 *
 * Contract notes, derived from apps/api route handlers:
 * - Sessions ride an httpOnly cookie (`openrange_session`); mutating requests
 *   must echo the per-session token in the `x-csrf-token` header.
 * - login/register respond with the CSRF token in the JSON body and also set
 *   a readable `openrange_csrf` cookie so browser clients can recover it.
 * - Errors are RFC 9457 problem details (application/problem+json).
 */

export interface Problem {
  readonly type: string;
  readonly title: string;
  readonly status: number;
  readonly detail?: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly problem: Problem | undefined;

  constructor(status: number, problem: Problem | undefined) {
    const detail = problem?.detail ?? problem?.title ?? 'request failed';
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.problem = problem;
  }
}

export interface AuthSession {
  readonly id: string;
  readonly username: string;
  readonly mfaPending: boolean;
}

export interface AuthSessionWithCsrf extends AuthSession {
  /** Per-session CSRF token; echo it back in `x-csrf-token` on mutations. */
  readonly csrfToken: string;
}

export interface CurrentUser {
  readonly id: string;
  readonly username: string;
  readonly email: string | null;
  readonly displayName: string | null;
  readonly bio: string | null;
  readonly emailVerified: boolean;
  readonly leaderboardOptOut: boolean;
  readonly permissions: readonly string[];
}

export interface UserSessionInfo {
  readonly id: string;
  readonly createdAt: string;
  readonly expiresAt: string;
  readonly ipAddress: string;
  readonly userAgent: string;
  readonly live: boolean;
}

export type LabState =
  | 'requested'
  | 'scheduled'
  | 'starting'
  | 'ready'
  | 'resetting'
  | 'stopping'
  | 'cleaned'
  | 'expired'
  | 'failed';

export interface LabTarget {
  readonly name: string;
  readonly url: string;
}

export interface LabInstance {
  readonly id: string;
  readonly room: string;
  readonly state: LabState;
  readonly expiresAt: string | null;
  readonly targets: readonly LabTarget[];
  readonly createdAt: string;
}

export interface LabDetail extends LabInstance {
  readonly timeRemainingMinutes: number;
}

export interface SetupStatus {
  readonly required: boolean;
}

export interface RegisterInput {
  readonly username: string;
  readonly password: string;
  readonly email?: string;
}

export interface LoginInput {
  readonly username: string;
  readonly password: string;
}

// --- Learning -------------------------------------------------------------

export type EnrollmentState = 'active' | 'paused' | 'completed';

export interface LearningPath {
  readonly slug: string;
  readonly title: string;
  readonly version: string;
  readonly difficulty: string;
  readonly estimated_minutes: number;
  readonly summary: string;
  readonly capstones: readonly string[];
  readonly certificate: boolean;
  readonly enrollment_state?: EnrollmentState | null;
}

export interface PathSectionRef {
  readonly id: string;
  readonly title: string;
  readonly order_index: number;
  readonly optional_branch: boolean;
  readonly prerequisites: readonly { readonly module: string; readonly section: string }[];
  readonly completed: boolean;
}

export interface PathModuleRef {
  readonly slug: string;
  readonly title: string;
  readonly optional_branch: boolean;
  readonly sections: readonly PathSectionRef[];
}

export interface LearningPathDetail extends LearningPath {
  readonly modules: readonly PathModuleRef[];
}

export interface EnrollmentMutationResult {
  readonly path_slug: string;
  readonly state: EnrollmentState;
  readonly enrollment_id?: string;
}

export type CalloutTone = 'info' | 'warning' | 'danger' | 'tip';

export interface ProseBlockView {
  readonly type: 'prose';
  readonly markdown: string;
}

export interface CalloutBlockView {
  readonly type: 'callout';
  readonly tone: CalloutTone;
  readonly markdown: string;
}

export interface CodeBlockView {
  readonly type: 'code';
  readonly language: string;
  readonly code: string;
}

export interface QuizOptionView {
  readonly id: string;
  readonly text: string;
}

/** Client-safe quiz block: the answer key never leaves the server. */
export interface QuizBlockView {
  readonly type: 'quiz';
  readonly question_id: string;
  readonly question: string;
  readonly options: readonly QuizOptionView[];
}

export type SectionBlockView = ProseBlockView | CalloutBlockView | CodeBlockView | QuizBlockView;

export interface ModuleSectionView {
  readonly id: string;
  readonly title: string;
  readonly blocks: readonly SectionBlockView[];
}

export interface LearningModule {
  readonly slug: string;
  readonly title: string;
  readonly version: string;
  readonly summary: string;
  readonly objectives: readonly string[];
  readonly labs: readonly string[];
  readonly cheat_sheet: string | null;
  readonly sections: readonly ModuleSectionView[];
}

export interface QuizAttemptInput {
  /** question_id -> selected option ids */
  readonly answers: Readonly<Record<string, readonly string[]>>;
  readonly module?: string;
}

export interface QuizAttemptResult {
  readonly attempt_id: string;
  readonly section_id: string;
  readonly passed: boolean;
  readonly results: readonly { readonly question_id: string; readonly correct: boolean }[];
}

export interface SectionCompleteResult {
  readonly enrollment_id: string;
  readonly module_slug: string;
  readonly section_id: string;
  readonly already_completed: boolean;
  readonly path_completed: boolean;
}

// --- Challenges -----------------------------------------------------------

export type ChallengeCategory = 'web' | 'crypto' | 'pwn' | 'rev' | 'forensics' | 'misc' | 'osint';

export interface ChallengeSummary {
  readonly slug: string;
  readonly name: string;
  readonly category: ChallengeCategory;
  readonly difficulty: number;
  readonly scoring: 'static' | 'dynamic';
  readonly points: number;
  readonly solve_count: number;
  readonly state?: 'hidden' | 'visible';
}

export interface ChallengeFile {
  readonly id: string;
  readonly filename: string;
  readonly size: number;
  readonly sha256: string;
}

export interface ChallengeDetail extends ChallengeSummary {
  readonly description: string;
  readonly files: readonly ChallengeFile[];
  readonly solved_by_me: boolean;
}

export interface FlagSubmitResult {
  readonly correct: boolean;
  readonly already_solved: boolean;
  readonly points: number | null;
  readonly first_blood: boolean;
}

// --- Notifications --------------------------------------------------------

export interface NotificationItem {
  readonly id: string;
  readonly category: string;
  readonly payload: Readonly<Record<string, unknown>>;
  readonly read_at: string | null;
  readonly created_at: string;
}

export interface NotificationFeed {
  readonly items: readonly NotificationItem[];
  readonly total: number;
  readonly offset: number;
}

export interface NotificationPrefs {
  readonly channel_in_app: boolean;
  readonly channel_email: boolean;
  readonly digest_weekly: boolean;
  readonly muted_categories: readonly string[];
}

export interface ApiClientOptions {
  /** Base URL of the FastAPI server, e.g. http://localhost:8700. */
  readonly baseUrl?: string;
  /** Injectable fetch for tests and server-side callers with custom options. */
  readonly fetchImpl?: typeof fetch;
  /**
   * Returns the current CSRF token. Browser callers usually read the
   * `openrange_csrf` cookie; the client also learns the token from
   * login/register responses automatically.
   */
  readonly getCsrfToken?: () => string | undefined;
}

export class ApiClient {
  private readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;
  private readonly getCsrfToken: (() => string | undefined) | undefined;
  private csrfToken: string | undefined;

  constructor(options: ApiClientOptions = {}) {
    this.baseUrl = (options.baseUrl ?? '').replace(/\/$/, '');
    this.fetchImpl = options.fetchImpl ?? fetch;
    this.getCsrfToken = options.getCsrfToken;
  }

  /** Last CSRF token observed from login/register, if any. */
  currentCsrfToken(): string | undefined {
    return this.csrfToken ?? this.getCsrfToken?.();
  }

  readonly auth = {
    register: (input: RegisterInput): Promise<AuthSessionWithCsrf> =>
      this.postJson('/api/auth/register', input, { expectsCsrf: true, okStatus: 201 }),
    login: (input: LoginInput): Promise<AuthSessionWithCsrf> =>
      this.postJson('/api/auth/login', input, { expectsCsrf: true }),
    logout: (): Promise<{ ok: boolean }> => this.postJson('/api/auth/logout', {}),
    mfaVerify: (code: string): Promise<{ mfaPending: boolean }> =>
      this.postJson('/api/auth/mfa/verify', { code }),
  };

  readonly users = {
    me: (): Promise<CurrentUser> => this.getJson('/api/users/me'),
    sessions: (): Promise<readonly UserSessionInfo[]> => this.getJson('/api/users/me/sessions'),
    revokeSession: (sessionId: string): Promise<{ revoked: boolean }> =>
      this.deleteJson(`/api/users/me/sessions/${encodeURIComponent(sessionId)}`),
  };

  readonly labs = {
    list: (): Promise<readonly LabInstance[]> => this.getJson('/api/labs'),
    start: (room: string): Promise<LabInstance> =>
      this.postJson('/api/labs', { room }, { okStatus: 200 }),
    get: (labId: string): Promise<LabDetail> =>
      this.getJson(`/api/labs/${encodeURIComponent(labId)}`),
    extend: (labId: string, minutes: number): Promise<LabInstance> =>
      this.postJson(`/api/labs/${encodeURIComponent(labId)}/extend`, { minutes }),
    reset: (labId: string): Promise<LabInstance> =>
      this.postJson(`/api/labs/${encodeURIComponent(labId)}/reset`, {}),
    stop: (labId: string): Promise<{ stopped: boolean }> =>
      this.deleteJson(`/api/labs/${encodeURIComponent(labId)}`),
  };

  readonly learning = {
    paths: (): Promise<readonly LearningPath[]> => this.getJson('/api/learning/paths'),
    path: (slug: string): Promise<LearningPathDetail> =>
      this.getJson(`/api/learning/paths/${encodeURIComponent(slug)}`),
    enroll: (slug: string): Promise<EnrollmentMutationResult> =>
      this.postJson(`/api/learning/paths/${encodeURIComponent(slug)}/enroll`, {}),
    pause: (slug: string): Promise<EnrollmentMutationResult> =>
      this.postJson(`/api/learning/paths/${encodeURIComponent(slug)}/pause`, {}),
    resume: (slug: string): Promise<EnrollmentMutationResult> =>
      this.postJson(`/api/learning/paths/${encodeURIComponent(slug)}/resume`, {}),
    module: (slug: string, lang?: string): Promise<LearningModule> => {
      const query = lang === undefined ? '' : `?lang=${encodeURIComponent(lang)}`;
      return this.getJson(`/api/learning/modules/${encodeURIComponent(slug)}${query}`);
    },
    completeSection: (moduleSlug: string, sectionId: string): Promise<SectionCompleteResult> =>
      this.postJson(
        `/api/learning/modules/${encodeURIComponent(moduleSlug)}/sections/${encodeURIComponent(sectionId)}/complete`,
        {},
      ),
    quizAttempt: (sectionId: string, input: QuizAttemptInput): Promise<QuizAttemptResult> =>
      this.postJson(`/api/learning/quiz/${encodeURIComponent(sectionId)}/attempt`, input),
  };

  readonly challenges = {
    list: (): Promise<readonly ChallengeSummary[]> => this.getJson('/api/challenges'),
    get: (slug: string): Promise<ChallengeDetail> =>
      this.getJson(`/api/challenges/${encodeURIComponent(slug)}`),
    submitFlag: (slug: string, flag: string): Promise<FlagSubmitResult> =>
      this.postJson(`/api/challenges/${encodeURIComponent(slug)}/submit`, { flag }),
  };

  readonly notifications = {
    feed: (limit = 50, offset = 0): Promise<NotificationFeed> =>
      this.getJson(`/api/notifications/me?limit=${limit}&offset=${offset}`),
    markRead: (notificationId: string): Promise<{ id: string; read: boolean }> =>
      this.postJson(`/api/notifications/${encodeURIComponent(notificationId)}/read`, {}),
    readAll: (): Promise<{ updated: number }> => this.postJson('/api/notifications/read-all', {}),
    prefs: (): Promise<NotificationPrefs> => this.getJson('/api/notifications/me/prefs'),
    updatePrefs: (input: Partial<NotificationPrefs>): Promise<NotificationPrefs> =>
      this.putJson('/api/notifications/me/prefs', input),
  };

  readonly setup = {
    status: (): Promise<SetupStatus> => this.getJson('/api/setup/status'),
  };

  private async request(path: string, init: RequestInit): Promise<Response> {
    const response = await this.fetchImpl(`${this.baseUrl}${path}`, init);
    if (response.ok) {
      return response;
    }
    throw new ApiError(response.status, await parseProblem(response));
  }

  private async getJson<T>(path: string): Promise<T> {
    const response = await this.request(path, { method: 'GET' });
    return parseJsonBody<T>(response);
  }

  private async postJson<T>(
    path: string,
    body: unknown,
    options: { expectsCsrf?: boolean; okStatus?: number } = {},
  ): Promise<T> {
    const token = this.currentCsrfToken();
    const headers: Record<string, string> = { 'content-type': 'application/json' };
    if (token !== undefined) {
      headers['x-csrf-token'] = token;
    }
    const response = await this.request(path, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });
    const parsed = await parseJsonBody<T>(response);
    if (options.expectsCsrf === true) {
      const csrf = extractCsrfToken(parsed);
      if (csrf !== undefined) {
        this.csrfToken = csrf;
      }
    }
    return parsed;
  }

  private async deleteJson<T>(path: string): Promise<T> {
    const token = this.currentCsrfToken();
    const headers: Record<string, string> = {};
    if (token !== undefined) {
      headers['x-csrf-token'] = token;
    }
    const response = await this.request(path, { method: 'DELETE', headers });
    return parseJsonBody<T>(response);
  }

  private async putJson<T>(path: string, body: unknown): Promise<T> {
    const token = this.currentCsrfToken();
    const headers: Record<string, string> = { 'content-type': 'application/json' };
    if (token !== undefined) {
      headers['x-csrf-token'] = token;
    }
    const response = await this.request(path, {
      method: 'PUT',
      headers,
      body: JSON.stringify(body),
    });
    return parseJsonBody<T>(response);
  }
}

function extractCsrfToken(payload: unknown): string | undefined {
  if (!isRecord(payload)) {
    return undefined;
  }
  const token = payload['csrf_token'];
  return typeof token === 'string' && token.length > 0 ? token : undefined;
}

async function parseProblem(response: Response): Promise<Problem | undefined> {
  const raw: unknown = await response.json().catch(() => undefined);
  if (!isRecord(raw)) {
    return undefined;
  }
  const { type, title, status, detail } = raw;
  return {
    type: typeof type === 'string' ? type : 'about:blank',
    title: typeof title === 'string' ? title : 'Request Failed',
    status: typeof status === 'number' ? status : response.status,
    detail: typeof detail === 'string' ? detail : undefined,
  };
}

async function parseJsonBody<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as T;
  }
  const raw: unknown = await response.json().catch(() => {
    throw new ApiError(response.status, undefined);
  });
  return raw as T;
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
