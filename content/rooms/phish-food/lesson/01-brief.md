# Phish Food

Phishing is still the front door for most intrusions, and the strange
thing about it is how much of the attack happens in plain sight. The
message that fools nobody in the body can fool everybody in the header
pane, because mail clients show you a display name and hide everything
that would contradict it. In this room the Meridian Archive operations
mailbox received a quota warning that the real service desk never sent,
and the mail team preserved it exactly as delivered: one raw .eml file
with every transport header intact. You will read that file the way a
mail server reads it, name three indicators, and file them with the
indicator desk.

## What is real here, and what is simulated

Nothing here touches a live mailbox or resolves a real domain. The .eml
is a hand-written synthetic message sitting inside your lab container,
the domains in it were invented for this exercise, and the link goes
nowhere because there is no network behind it. What is faithful is the
structure of the deception, which copies the patterns analysts see every
week. Real spoofed messages really do borrow a trusted display identity
in the From header while sending from unrelated infrastructure, the
Return-Path really does point at bounce handling on networks that have
nothing to do with the claimed brand, and body links really do tuck the
trusted name into a subdomain so the eye slides over the part that
matters. Learning to see those three seams in a synthetic file builds
exactly the reflex you need when the message is real and the click
already happened.

## Reading headers like a parser

A mail client renders a story; a parser prints evidence. Start with the
From header and split off the address inside the angle brackets, because
the display name before it is free text anyone can set to anything. Then
read Return-Path, the envelope sender that receiving servers use for
bounces, and compare its domain with the From domain. Legitimate bulk
and transactional senders often differ slightly here, which is why you
treat mismatch as a question rather than a verdict, but a consumer brand
claiming to be your own company while routing bounces through a stranger
relay is not a mailing-list quirk. Finish with the body: pull out the
https URL, take its hostname, and strip labels from the left until two
remain. That last pair is the registrable domain, and it, not the
decorative text in front of it, says who receives the connection. A host
like trusted-brand.attacker-domain.example belongs entirely to
attacker-domain.example no matter how convincing the prefix looks.
Answer all three questions at the quiz endpoint and the case closes.

## What you will practice

- Parsing raw RFC 5322 headers without trusting the display pane.
- Separating envelope identity from claimed identity.
- Reducing any URL to its registrable domain before judging it.

## Scope

Only the case page at `http://target:8000` is in scope. Nothing
outside your lab instance is a target.
