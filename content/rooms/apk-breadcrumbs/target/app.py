"""Breadcrumb Labs package desk: synthetic APK static-analysis sim. Room target only.

The archive is assembled at import time with fixed timestamps so every
download is byte-identical. classes.dex is a text manifest describing
smali flows, not bytecode, and no real app or endpoint exists.
"""

import io
import os
import zipfile

from flask import Flask, Response, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

API_ENDPOINT = "https://crumb-sync.breadcrumbs-lab.example/api/v2"
API_KEY = "brk-dev-key-7741"

MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.breadcrumbs.pantry" android:versionCode="14"
    android:versionName="2.3.1" android:debuggable="true">
  <uses-permission android:name="android.permission.INTERNET"/>
  <application android:label="@string/app_name">
    <activity android:name=".MainActivity" android:exported="true">
      <intent-filter>
        <action android:name="android.intent.action.MAIN"/>
        <category android:name="android.intent.category.LAUNCHER"/>
      </intent-filter>
    </activity>
    <service android:name=".SyncService" android:exported="false"/>
  </application>
</manifest>
"""

STRINGS = """<?xml version="1.0" encoding="utf-8"?>
<resources>
  <string name="app_name">Pantry Breadcrumbs</string>
  <string name="api_base_url">https://crumb-sync.breadcrumbs-lab.example/api/v2</string>
  <string name="api_base_url_legacy">https://crumb-api.breadcrumbs-lab.example/api/v1</string>
  <string name="debug_api_key">brk-dev-key-7741</string>
  <string name="sync_interval_seconds">900</string>
</resources>
"""

DEX_STUB = """classes.dex teaching stub (real builds ship dalvik bytecode here)

smali flow notes for com.breadcrumbs.pantry:

MainActivity.onCreate()
  -> setContentView, then SyncClient.sync(context) on a worker thread

SyncClient.sync(context)
  -> url = context.getString(R.string.api_base_url)
  -> reads resource debug_api_key and sends it as X-Debug-Key only when
     BuildConfig.DEBUG is true; the constant ships in resources either way
  -> legacy host api_base_url_legacy is retained but marked deprecated;
     production traffic goes to api_base_url (v2, crumb-sync host)

DebugGate.isDebugBuild(context)
  -> compares Secure.getString(settings_debug_key) against the resource
     value; mismatch logs a warning and returns false

Reviewer note: both strings live in res/values/strings.xml in plain
text, exactly where apktool drops them during `apktool d`.
"""

BUILD_INFO = """build.host=packer-03.breadcrumbs-lab.internal
build.channel=release-candidate
build.date=2026-08-14
vcs.revision=9f31c02
"""

MF = """Manifest-Version: 1.0
Created-By: breadcrumbs-packer 5.1 (simulated)
"""


def build_apk() -> bytes:
    entries = [
        ("AndroidManifest.xml", MANIFEST),
        ("assets/build-info.properties", BUILD_INFO),
        ("classes.dex", DEX_STUB),
        ("res/values/strings.xml", STRINGS),
        ("META-INF/MANIFEST.MF", MF),
    ]
    buf = io.BytesIO()
    stamp = (2026, 8, 14, 9, 0, 0)
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, text in entries:
            info = zipfile.ZipInfo(name, date_time=stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, text)
    return buf.getvalue()


APK_BYTES = build_apk()

PAGE_TMPL = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Breadcrumb Labs package desk</title><style>
body {{ background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:8vh; }}
.wrap {{ width:44rem; padding-bottom:4rem; }}
.box {{ background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:1.5rem 2rem; margin-bottom:.8rem; }}
code, pre {{ background:#F7F6F3; border-radius:6px; padding:.15rem .4rem; font-size:.82rem; overflow-wrap:anywhere; }}
h1 {{ letter-spacing:-0.02em; font-size:1.35rem; }} h2 {{ font-size:1rem; }}
p, li {{ color:#787774; font-size:.9rem; line-height:1.55; }}
.disclosure {{ background:#FDF3E7; border:1px solid #EAD3AE; }}
input {{ width:100%; padding:.45rem; border:1px solid #EAEAEA; border-radius:6px; margin-bottom:.5rem; }}
button {{ background:#111; color:#fff; border:none; border-radius:6px; padding:.5rem 1rem; cursor:pointer; }}
.good {{ color:#346538; }}
</style></head><body><div class="wrap">{}</div></body></html>"""

HOME = """
<div class="box disclosure">
<h2>This is a simulation</h2>
<p>app.apk here is a synthetic zip written by this service with fixed
timestamps. Its classes.dex is a readable text manifest describing the
smali flows instead of real bytecode, and no real application,
developer account, or network endpoint exists behind the names you
will read. The exercise teaches the same first pass that apktool and
jadx enable against genuine packages.</p>
</div>
<div class="box">
<h1>Package desk</h1>
<p>Evidence: <a href="/evidence/app.apk">app.apk</a>, an Android-style
package archive for com.breadcrumbs.pantry, build 2.3.1 candidate.
An APK is an ordinary zip, so any unzip tool opens it; the interesting
entries are AndroidManifest.xml, classes.dex, and
res/values/strings.xml.</p>
<p>The verification desk accepts the two findings reviewers expect
from a release build: the production API endpoint and the leftover
debug API key. Submit both below.</p>
<form method="post" action="/verify">
<input name="api_endpoint" placeholder="api_endpoint">
<input name="api_key" placeholder="api_key">
<button type="submit">Verify findings</button>
</form>
</div>
"""


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return PAGE_TMPL.format(HOME)


@app.get("/evidence/app.apk")
def evidence():
    return Response(
        APK_BYTES,
        mimetype="application/vnd.android.package-archive",
        headers={"Content-Disposition": "attachment; filename=app.apk"},
    )


@app.post("/verify")
def verify():
    endpoint = request.form.get("api_endpoint", "").strip()
    key = request.form.get("api_key", "").strip()
    if endpoint == API_ENDPOINT and key == API_KEY:
        body = """
<div class="box">
<h1 class="good">Findings verified</h1>
<p>Production endpoint and shipped debug credential confirmed against
the package resources. Report filed for build 2.3.1.</p>
<p><code>{}</code></p>
<p>Remediation note: move secrets out of resources into server-side
distribution, and strip debug gates from release builds.</p>
</div>"""
        return PAGE_TMPL.format(body.format(FLAG))
    return PAGE_TMPL.format("""
<div class="box">
<h1>Findings rejected</h1>
<p>The submitted pair does not match the values packaged in the
archive. Re-read res/values/strings.xml and the smali flow notes about
which URL is production.</p>
</div>"""), 403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
