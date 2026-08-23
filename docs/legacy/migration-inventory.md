# Legacy migration inventory

The original stack (Flask scoreboard plus twenty always-on rooms on
fixed loopback ports) is preserved as the `legacy-v0` Compose profile.
Proof that it still works: `docs/evidence/2026-08-22-legacy-solve.txt`
(20/20 solves, 2975 points, exit 0).

Each room maps to a versioned bundle under `content/rooms/` in the new
platform. Behavioral equivalence means: same service behavior, same
exploit path, same points; the flag mechanism changes from static to
per-session derivation (ADR 0007), so solver expectations change
accordingly.

| #   | Legacy name         | Port | Points | Technique                | New slug            | New track |
| --- | ------------------- | ---- | ------ | ------------------------ | ------------------- | --------- |
| 1   | Busted Login        | 8081 | 100    | SQL login bypass         | busted-login        | A/001     |
| 2   | Nosy Files          | 8082 | 150    | Path traversal           | nosy-files          | A/002     |
| 3   | Ping of Doom        | 8083 | 200    | Command injection        | ping-of-doom        | A/003     |
| 4   | SSTI Greeting       | 8084 | 150    | Jinja SSTI               | ssti-greeting       | A/004     |
| 5   | Token Forger        | 8085 | 250    | JWT alg:none             | token-forger        | A/005     |
| 6   | IDOR Invoices       | 8086 | 125    | Missing object authz     | idor-invoices       | A/006     |
| 7   | Open Panels         | 8087 | 50     | Exposed debug panel      | open-panels         | A/007     |
| 8   | Cookie Shapeshifter | 8088 | 100    | Unsigned cookie forgery  | cookie-shapeshifter | A/008     |
| 9   | Regex Doom          | 8089 | 125    | Regex injection          | regex-doom          | A/009     |
| 10  | Mass Assign         | 8090 | 150    | Mass assignment          | mass-assign         | A/010     |
| 11  | XXE Importer        | 8091 | 225    | XXE                      | xxe-importer        | A/011     |
| 12  | Pickle Jar          | 8092 | 275    | Unsafe deserialization   | pickle-jar          | A/012     |
| 13  | Trusted Proxy       | 8093 | 75     | XFF spoofing             | trusted-proxy       | A/013     |
| 14  | Wrong Method        | 8094 | 75     | Verb tampering           | wrong-method        | A/014     |
| 15  | Open Closet         | 8095 | 50     | Directory listing        | open-closet         | A/015     |
| 16  | Predictable Reset   | 8096 | 175    | Time-derived reset token | predictable-reset   | A/016     |
| 17  | Double Trouble      | 8097 | 150    | Parameter pollution      | double-trouble      | A/017     |
| 18  | Fetch Boy           | 8098 | 200    | SSRF                     | fetch-boy           | A/018     |
| 19  | Union Vault         | 8099 | 225    | UNION SQLi               | union-vault         | A/019     |
| 20  | Brace Yourself      | 8100 | 125    | Format string injection  | brace-yourself      | A/020     |

Flag mechanisms in the legacy stack: rooms receive their flag via env at
build/run (`FLAG_N`) and compare submissions against it on the platform;
the demo solver extracts flags by exploiting each service. In the new
platform the runner injects an HMAC-derived per-instance flag (ADR 0007)
and solvers assert against the instance's expected value.

Retirement rule (plan section 13): the legacy profile stays until all
twenty migrated bundles prove solver parity and one release of burn-in,
then `legacy/platform` and `legacy/rooms` move out of release scope.
