# Brief: the secret that shipped with the code

This room wraps OWASP WrongSecrets in its official local no-vault mode,
which is exactly how upstream publishes it for playing without
Kubernetes or a Vault server. You get the app on port 8080 of the
`target` host.

## Why this matters

Secrets leak in boring ways. The most boring of all: a password written
directly in source code that then ships to every user. WrongSecrets
challenge 1 recreates that mistake on purpose and asks you to find it.
Once you have seen how trivially hardcoded constants fall out of a
shipped artifact, you will never look at a public package the same way.

## Your path

1. Open `http://target/` and pick challenge 1 from the Challenges menu.
2. Read the challenge text and open its hints inside the app. The hints
   tell you where such a secret tends to live.
3. The upstream project is open source, and this exact image was built
   from it. Look at the class named `Challenge1` and follow what its
   answer check compares against.
4. Enter the value you found into the app's answer box until it
   confirms you are right.
5. Submit the same string as your answer for this room.

## Answer convention

WrongSecrets cannot host platform-injected flags, so this room validates
a fixed public constant: the challenge 1 secret itself, which is public
knowledge in the upstream repository.

Credit: OWASP WrongSecrets is an official OWASP project under AGPL-3.0,
published by its maintainers as container images. This room references
the published image and adds original lesson text around it.
