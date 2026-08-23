"""OrbitOps portal: the GraphQL gateway skips the note-level access policy. Room target only."""

import json
import os
from dataclasses import dataclass

from flask import Flask, Response, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

NOTE_1 = {
    "_typename": "Note",
    "id": "N-1",
    "classification": "internal",
    "title": "Standup notes",
    "body": "Antenna rotation service restarts every Tuesday. Log rotation shares that window.",
}
NOTE_2 = {
    "_typename": "Note",
    "id": "N-2",
    "classification": "internal",
    "title": "Retro actions",
    "body": "Telemetry replay moved to the night queue. Owners: Dana, Ravi.",
}
NOTE_3 = {
    "_typename": "Note",
    "id": "N-3",
    "classification": "internal",
    "title": "Access review",
    "body": "Contractor badges expire with the milestone. Mirela renews through Ground Segment.",
}
NOTE_4 = {
    "_typename": "Note",
    "id": "N-4",
    "classification": "restricted",
    "title": "Escrow recovery",
    "body": FLAG,
}
PROJECT_KESTREL = {
    "_typename": "Project",
    "id": "P-1",
    "codename": "KESTREL",
    "notes": [NOTE_1, NOTE_2],
}
PROJECT_LUMEN = {
    "_typename": "Project",
    "id": "P-2",
    "codename": "LUMEN",
    "notes": [NOTE_3, NOTE_4],
}
TEAM_ORBITAL = {"_typename": "Team", "id": 1, "name": "Orbital Ops", "project": PROJECT_KESTREL}
TEAM_GROUND = {"_typename": "Team", "id": 2, "name": "Ground Segment", "project": PROJECT_LUMEN}
USER_ME = {
    "_typename": "User",
    "id": 1,
    "name": "Dana Kovacs",
    "role": "intern",
    "team": TEAM_ORBITAL,
}
USERS = [
    USER_ME,
    {"_typename": "User", "id": 2, "name": "Ravi Patel", "role": "engineer", "team": TEAM_ORBITAL},
    {
        "_typename": "User",
        "id": 3,
        "name": "Mirela Enache",
        "role": "contractor",
        "team": TEAM_GROUND,
    },
]
ALL_NOTES = [NOTE_1, NOTE_2, NOTE_3, NOTE_4]

# The REST console enforces the classification policy below. The GraphQL
# gateway was bolted on for archive sync and trusts every node handler,
# so nothing on that path ever asks whether you may read a note.
SCALARS = ("Int", "String", "Boolean")

FIELD_SPECS: dict[str, dict[str, tuple]] = {
    "Query": {
        "me": (False, "User"),
        "user": (False, "User", {"id": "Int"}),
        "users": (True, "User"),
    },
    "User": {
        "id": (False, "Int"),
        "name": (False, "String"),
        "role": (False, "String"),
        "team": (False, "Team"),
    },
    "Team": {"id": (False, "Int"), "name": (False, "String"), "project": (False, "Project")},
    "Project": {
        "id": (False, "String"),
        "codename": (False, "String"),
        "notes": (True, "Note"),
    },
    "Note": {
        "id": (False, "String"),
        "classification": (False, "String"),
        "title": (False, "String"),
        "body": (False, "String"),
    },
}


class GraphQLError(Exception):
    pass


@dataclass(slots=True)
class FieldNode:
    alias: str | None
    name: str
    args: dict[str, object]
    subsel: list["FieldNode"] | None


def tokenize(text: str) -> list[tuple[str, object]]:
    tokens: list[tuple[str, object]] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n,":
            i += 1
        elif c in "{}():":
            tokens.append((c, c))
            i += 1
        elif c == '"':
            j = i + 1
            buf: list[str] = []
            while j < n and text[j] != '"':
                buf.append(text[j])
                j += 1
            if j >= n:
                raise GraphQLError("unterminated string literal")
            tokens.append(("STRING", "".join(buf)))
            i = j + 1
        elif c.isdigit():
            j = i
            while j < n and text[j].isdigit():
                j += 1
            tokens.append(("INT", int(text[i:j])))
            i = j
        elif c.isalpha() or c == "_":
            j = i
            while j < n and (text[j].isalnum() or text[j] == "_"):
                j += 1
            word = text[i:j]
            if word == "true" or word == "false":
                tokens.append(("BOOL", word == "true"))
            elif word == "null":
                tokens.append(("NULL", None))
            else:
                tokens.append(("NAME", word))
            i = j
        else:
            raise GraphQLError(f"unexpected character {c!r}; this gateway accepts literals only")
    return tokens


class Parser:
    def __init__(self, tokens: list[tuple[str, object]]):
        self.tokens = tokens
        self.pos = 0

    def peek_kind(self):
        return self.tokens[self.pos][0] if self.pos < len(self.tokens) else None

    def take(self):
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def parse_document(self) -> list[FieldNode]:
        if self.peek_kind() == "NAME" and self.tokens[self.pos][1] == "query":
            self.take()
            if self.peek_kind() == "NAME":
                self.take()
        return self.parse_selection_set()

    def parse_selection_set(self) -> list[FieldNode]:
        if self.take()[0] != "{":
            raise GraphQLError("expected '{' at start of selection set")
        fields: list[FieldNode] = []
        while True:
            kind = self.peek_kind()
            if kind is None:
                raise GraphQLError("unterminated selection set")
            if kind == "}":
                self.take()
                return fields
            fields.append(self.parse_field())

    def parse_field(self) -> FieldNode:
        kind, name = self.take()
        if kind != "NAME":
            raise GraphQLError(f"expected a field name, got {name!r}")
        alias = None
        if self.peek_kind() == ":":
            self.take()
            kind2, real = self.take()
            if kind2 != "NAME":
                raise GraphQLError("expected a field name after alias ':'")
            alias, name = str(name), str(real)
        args: dict[str, object] = {}
        if self.peek_kind() == "(":
            self.take()
            while True:
                arg_kind, arg_name = self.take()
                if arg_kind == ")":
                    break
                if arg_kind != "NAME":
                    raise GraphQLError("expected an argument name")
                if self.take()[0] != ":":
                    raise GraphQLError("expected ':' after argument name")
                args[str(arg_name)] = self.parse_value()
        subsel = None
        if self.peek_kind() == "{":
            subsel = self.parse_selection_set()
        return FieldNode(alias=alias, name=str(name), args=args, subsel=subsel)

    def parse_value(self) -> object:
        kind, value = self.take()
        if kind in ("INT", "FLOAT", "STRING", "BOOL", "NULL", "NAME"):
            return value
        raise GraphQLError(f"unsupported value token {kind}")


ROOT = object()


def typename_for(parent: object) -> str:
    if parent is ROOT:
        return "Query"
    if isinstance(parent, dict):
        return str(parent.get("_typename", "Object"))
    return "Object"


def resolve_field(parent: object, name: str, args: dict[str, object]):
    if parent is ROOT:
        if name == "me":
            return USERS[0]
        if name == "users":
            return USERS
        if name == "user":
            wanted = int(str(args.get("id", -1)))
            for user in USERS:
                if user["id"] == wanted:
                    return user
            return None
        raise KeyError(name)
    if isinstance(parent, dict) and name in parent:
        return parent[name]
    raise KeyError(name)


def execute_fields(fields: list[FieldNode], parent: object):
    data: dict[str, object] = {}
    errors: list[str] = []
    for node in fields:
        key = node.alias or node.name
        if node.name == "__typename":
            data[key] = typename_for(parent)
            continue
        try:
            value = resolve_field(parent, node.name, node.args)
        except KeyError:
            errors.append(f"Cannot query field '{node.name}' on type '{typename_for(parent)}'.")
            data[key] = None
            continue
        if node.subsel is None or value is None:
            data[key] = value
        elif isinstance(value, list):
            items: list[object] = []
            for item in value:
                if item is None:
                    items.append(None)
                    continue
                child_data, child_errors = execute_fields(node.subsel, item)
                items.append(child_data)
                errors.extend(child_errors)
            data[key] = items
        else:
            child_data, child_errors = execute_fields(node.subsel, value)
            data[key] = child_data
            errors.extend(child_errors)
    return data, errors


def type_ref(of_name: str, is_list: bool) -> dict[str, object]:
    if is_list:
        inner_kind = "SCALAR" if of_name in SCALARS else "OBJECT"
        return {
            "kind": "LIST",
            "name": None,
            "ofType": {"kind": inner_kind, "name": of_name, "ofType": None},
        }
    kind = "SCALAR" if of_name in SCALARS else "OBJECT"
    return {"kind": kind, "name": of_name, "ofType": None}


def field_entry(fname: str, spec: tuple) -> dict[str, object]:
    is_list, of = spec[0], spec[1]
    entry: dict[str, object] = {"name": fname, "type": type_ref(of, is_list)}
    if len(spec) > 2:
        entry["args"] = [
            {"name": aname, "type": type_ref(aof, False), "defaultValue": None}
            for aname, aof in spec[2].items()
        ]
    return entry


def type_entry(tname: str) -> dict[str, object] | None:
    if tname in SCALARS:
        return {"name": tname, "kind": "SCALAR"}
    if tname not in FIELD_SPECS:
        return None
    return {
        "name": tname,
        "kind": "OBJECT",
        "fields": [field_entry(fn, fs) for fn, fs in FIELD_SPECS[tname].items()],
    }


def schema_object() -> dict[str, object]:
    names = ("Query", "User", "Team", "Project", "Note", *SCALARS)
    return {"queryType": {"name": "Query"}, "types": [type_entry(t) for t in names]}


def prune(value: object, fields: list[FieldNode]):
    if isinstance(value, list):
        return [prune(item, fields) for item in value]
    out: dict[str, object] = {}
    for node in fields:
        raw = value.get(node.name) if isinstance(value, dict) else None
        out[node.alias or node.name] = (
            prune(raw, node.subsel) if node.subsel and raw is not None else raw
        )
    return out


def run_query(query: str) -> dict[str, object]:
    try:
        top = Parser(tokenize(query)).parse_document()
    except GraphQLError as exc:
        return {"errors": [{"message": str(exc)}]}
    data: dict[str, object] = {}
    errors: list[str] = []
    for node in top:
        key = node.alias or node.name
        if node.name == "__schema":
            data[key] = prune(schema_object(), node.subsel or [])
        elif node.name == "__type":
            wanted = str(node.args.get("name", ""))
            entry = type_entry(wanted)
            data[key] = prune(entry, node.subsel or []) if entry else None
        else:
            chunk, chunk_errors = execute_fields([node], ROOT)
            data.update(chunk)
            errors.extend(chunk_errors)
    response: dict[str, object] = {"data": data}
    if errors:
        response["errors"] = [{"message": message} for message in errors]
    return response


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>OrbitOps Ground Portal</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:10vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:32rem; }
h1 { letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
p, li, td { color:#787774; font-size:.9rem; }
code { background:#F7F6F3; border:1px solid #EAEAEA; border-radius:6px; padding:.15rem .4rem; font-size:.82rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
a { color:#346538; }
</style></head><body>%s</body></html>"""


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def console():
    visible = "".join(
        f'<li><a href="/api/notes/{n["id"]}">{n["id"]} {n["title"]}</a> ({n["classification"]})</li>'
        for n in (NOTE_1, NOTE_2)
    )
    return (
        PAGE
        % f"""
<div class="box">
<h1>OrbitOps ground portal</h1>
<p>Signed in as Dana Kovacs (intern, Orbital Ops). Project notes live in
the REST console:</p>
<ul>{visible}</ul>
<p>Classification policy: restricted material is served only through
this console, which checks every note against your project.</p>
<p>The archive sync team talks to the platform over the GraphQL gateway
instead: <code>POST /graphql</code> with {{"query": "..."}}. Batched
requests (a JSON array) are accepted. The gateway predates the
classification policy.</p>
</div>"""
    )


@app.get("/api/notes/<note_id>")
def rest_note(note_id: str):
    note = next((n for n in ALL_NOTES if n["id"] == note_id.upper()), None)
    if note is None:
        return PAGE % "<div class='box'><h1>No such note</h1></div>", 404
    if note["classification"] == "restricted":
        return (
            PAGE
            % """
<div class="box"><h1>403 Restricted</h1><p>Object policy denies access
to restricted material outside the owning console session.</p></div>""",
            403,
        )
    return (
        PAGE
        % f"""
<div class="box"><h1>{note["id"]} {note["title"]}</h1>
<p>({note["classification"]}) {note["body"]}</p></div>"""
    )


@app.post("/graphql")
def graphql_gateway():
    payload = request.get_json(silent=True)
    if isinstance(payload, list):
        batch = [item.get("query", "") if isinstance(item, dict) else "" for item in payload[:25]]
        return Response(json.dumps([run_query(q) for q in batch]), mimetype="application/json")
    query = payload.get("query", "") if isinstance(payload, dict) else ""
    return Response(json.dumps(run_query(query)), mimetype="application/json")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
