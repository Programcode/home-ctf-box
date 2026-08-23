# Pickle Jar

PickleJar keeps session state as pickled Python objects and restores
whatever a client posts to /load. Pickle streams are executable, so
you will craft one whose reduce hook makes the service evaluate an
expression that reads its own flag file.

## What you will practice

- Seeing pickle as a bytecode format that runs code during load.
- Writing an **reduce** payload that calls back into the interpreter.
- Capturing the value the service echoes back after the restore.

## Scope

Only PickleJar at `http://target:8000` is in scope. Nothing outside
your lab instance is a target.
