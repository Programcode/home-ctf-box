# Graph Maze

OrbitOps operates satellites and, like every aerospace company, keeps
notes. Your intern account can read the standup minutes for Orbital Ops,
while anything marked restricted is locked behind an object-level
policy in the REST console. A GraphQL gateway added for archive sync
never learned about that policy, and it happily tells strangers what
the schema looks like.

## What you will practice

- Using introspection as a map of fields the interface never mentions.
- Walking relationships across types: users, teams, projects, notes.
- Spotting broken object-level authorization by comparing two doors into the same data.

## Scope

Only the portal at `http://target:8000` is in scope. Nothing outside
your lab instance is a target.
