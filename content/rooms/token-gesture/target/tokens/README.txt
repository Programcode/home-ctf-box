SIMULATED TOKEN STORE, token-gesture room
=========================================

This directory is a plain-file stand-in for a Windows token cache.
Nothing here is a real access token, handle table entry, or Windows
identity object. Each *.json file models one captured logon token with
faithful field names:

  version          schema version, always 1
  kind             interactive-sim or service-sim
  user             account name the token represents
  domain           simulated domain suffix
  groups           simulated group memberships
  integrity_level  low | medium | high (stands in for process integrity)
  checksum         sha256:<hex> over the JSON body with this key removed,
                   canonicalized as sorted keys and no whitespace:
                     json.dumps(body, sort_keys=True, separators=(",", ":"))

The checksum proves the file was not edited after issuance. It does not
prove who wrote it or where it came from. Keep that distinction in mind
as you work through this room; it is the whole lesson.

These files are training data on a disposable lab container. Never
recreate structures like these on systems you do not own.
