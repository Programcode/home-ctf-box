# Image Issues

Container images are built from snapshots of whatever the build context
contains at COPY time. That mechanical fact creates one of the most
common supply-chain exposures in production: a developer with database
credentials in a local .env file runs docker build from the project
root, the .dockerignore misses dotfiles, and the COPY . . step bakes
the secret into a layer forever. Deleting the file in a later commit
does not help, because layers are immutable diffs stacked on top of
each other. Every version of every file that ever entered a layer
stays extractable until the image is rebuilt from scratch.

Reading an image therefore means reading its layer history. The
manifest lists layers as ordered digests, bottom up, matching the
sequence of build steps that produced them. The config history records
each command. History entries that change the filesystem carry a layer
reference; instructions like CMD or ENV add metadata only. When you
know which command introduced a file, you know exactly which digest to
pull apart, and tar listings of each layer show the file tree that diff
added. In this room the evidence bundle gives you the exported manifest
plus per-layer listings and extracted files keyed by digest, which is
exactly how tools like dive or a registry export present them.

The investigation rewards method over guessing. Find the COPY . .
layer first, confirm from its listing that app/.env exists beside the
harmless app/.env.example, then read the extracted file for connection
values. A finding is not proven until impact is demonstrated, so the
room closes only when the recovered credentials actually unlock the
admin db console. That mirrors incident practice: a leaked password in
an image is a curiosity if rotation already happened, and a critical
finding when it still opens the production database.

## Simulation disclosure

The manifest, listings, and env file are synthetic constants served by
the room's Flask target, shaped like real registry exports but touching
no runtime, registry, or database. The admin db console compares the
submitted strings in memory and holds no actual data store.

## What you will practice

- Mapping image config history entries to ordered layer digests.
- Reading tar listings to spot files that should never ship in images.
- Turning an extracted secret into demonstrated impact.

## Scope

Only the case page at `http://target:8000` is in scope. Nothing outside
your lab instance is a target.
