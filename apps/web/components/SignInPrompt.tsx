import { ButtonLink } from '@openrange/ui';

/** Inline panel shown where data needs a session and the visitor has none. */
export function SignInPrompt({ what }: { what: string }) {
  return (
    <div className="mt-10 rounded-lg border border-edge bg-panel px-6 py-10 text-center">
      <h2 className="m-0 text-lg font-semibold">Sign in to {what}</h2>
      <p className="mx-auto mt-2 mb-0 max-w-[48ch] text-sm leading-relaxed text-muted">
        This area tracks your personal progress, so it needs an account. Everything else on the
        range stays browsable while signed out.
      </p>
      <div className="mt-5">
        <ButtonLink href="/login" variant="secondary">
          Sign in
        </ButtonLink>
      </div>
    </div>
  );
}
