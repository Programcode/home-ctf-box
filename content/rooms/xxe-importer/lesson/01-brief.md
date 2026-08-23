# XXE Importer

ImportBridge takes XML uploads from legacy partner systems and its
parser still resolves external entities. You will define an entity in
the document's DOCTYPE that points at a file on the service, reference
it in the body, and read the flag out of the import result page.

## What you will practice

- Recognizing parsers that resolve external entities from how they
  treat a DOCTYPE.
- Writing an internal entity with a file:// system identifier.
- Turning a parser into a local file reader and capturing the result.

## Scope

Only ImportBridge at `http://target:8000` is in scope. Nothing outside
your lab instance is a target.
