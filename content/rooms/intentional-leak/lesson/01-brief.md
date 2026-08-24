# Intentional Leak

Android component attacks reward people who read the component model
before touching anything, and this room drills exactly that habit.
Pantryview's developer build publishes its activity stack over a
simulated intent router. One exported activity renders attacker
controlled note extras through a WebView-style template that can read
the settings store, and the internal diagnostics desk trusts whoever
presents the debug token. Your chain: enumerate, deny yourself the
shortcut, craft the intent, read the leak out of renderer output,
redeem it.

Honesty first. There is no device, emulator, or real application here.
The activity manager behavior you will see, exported flags enforced and
intent filters matched, is a Flask route consulting Python
dictionaries, built so every hop of the chain stays inspectable. The
debug token exists only inside this container, and nothing you do can
affect anything beyond it. What transfers to a real assessment is the
order of operations: enumerate components before touching them, test
the boundaries with deliberately wrong intents, and read every error
message, because Android's exceptions name exactly which check stopped
you.

## The component model as an attack surface

Android starts components through intents, and the manifest decides
what outside callers may reach. An exported activity is callable by any
other app; a non-exported one throws SecurityException from outside no
matter how it is addressed. Intent filters add resolution on top:
when you start by action rather than explicit class name, the system
picks a handler whose filter matches. Both facts are attack surface.
An exported activity that was meant for developers only hands strangers
a reachable entry point, and filters that are broader than needed let
callers arrive with extras the developer never audited. This room's
stack shows all three states at once: an ordinary launcher activity, an
exported notes renderer guarded only by its action string, and an
internal diagnostics screen that is correctly non-exported but whose
token can be stolen elsewhere.

The second ingredient is the bridge. WebViews become powerful when
code calls addJavascriptInterface, exposing native objects to page
content, and dangerous when the content flowing through them is
attacker controlled. Pantryview's renderer models this with a tiny
template language: in webview mode, {{settings.KEY}} expressions read
the app's settings store, while plain mode leaves text untouched. That
mode switch matters. It teaches you to ask which code path actually
processes your input, because the same extra is harmless in one mode
and a data exposure in the other, exactly how real WebView bugs differ
from their inert cousins.

## Running the chain and defending against it

Start with enumeration the way dumpsys or a manifest decode would:
/api/activities prints exported flags, actions, and accepted extras.
Probe the boundary first, sending an intent at the internal activity
and reading the SecurityException, then send a wrong action to the
renderer to see filter resolution fail. Only then craft the payload:
action matching the filter, render_mode webview, and the note set to
{{settings.debug_token}}. The render-log endpoint plays logcat; your
leaked token sits in the newest line. Presenting it at
/internal/debug completes the chain because the desk authenticates
possession of the token rather than identity of the caller.

Every hop has a standing fix worth naming in a report. Exported
surface shrinks with android:exported defaults and narrow filters.
Extras get validated like any other untrusted input before reaching
privileged contexts. Bridges allowlist what page content may read,
ideally never exposing settings at all. And secrets stay out of logs
and renderer output, since possession-based checks collapse the moment
the secret leaks into a place attackers can read.
