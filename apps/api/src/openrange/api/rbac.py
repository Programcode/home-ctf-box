"""RBAC permission catalogue.

Endpoints guard on permission strings, never on role names. Adding a
role means composing these strings; adding a permission means teaching
an endpoint about it here first.
"""

from __future__ import annotations

from dataclasses import dataclass, field

LEARNER = "learner"
AUTHOR = "author"
REVIEWER = "reviewer"
INSTRUCTOR = "instructor"
SUPPORT = "support"
OPERATOR = "operator"
ADMIN = "admin"


@dataclass(frozen=True)
class Permission:
    id: str
    description: str


@dataclass(frozen=True)
class RoleDefinition:
    name: str
    description: str
    permissions: tuple[str, ...] = field(default_factory=tuple)


P = Permission

PERMISSIONS: dict[str, Permission] = {
    p.id: p
    for p in [
        P("content:read", "View published catalog and content"),
        P("content:draft", "Create and edit own drafts in the studio"),
        P("content:submit", "Submit drafts for review"),
        P("content:review-technical", "Technical review of submissions"),
        P("content:review-instructional", "Instructional review of submissions"),
        P("content:review-security", "Security review of submissions"),
        P("content:publish", "Approve and publish approved content"),
        P("content:manage", "Version pinning, rollback, retirement"),
        P("lab:start", "Start personal lab instances"),
        P("lab:manage-own", "Extend/reset/stop own instances"),
        P("lab:manage-any", "Operate any instance (operators)"),
        P("vpn:issue", "Issue and revoke own VPN device configs"),
        P("progress:own", "Track own progress, notes, bookmarks"),
        P("scores:read", "Read leaderboards and scores"),
        P("events:compete", "Join events and competitions"),
        P("teams:join", "Join and leave teams"),
        P("orgs:manage", "Manage organizations they administer"),
        P("cohorts:assign", "Assign curriculum to learners"),
        P("reports:read", "Instructor reporting dashboards"),
        P("users:support", "Look up accounts for support, redacted"),
        P("moderation:queue", "Work the moderation queue"),
        P("system:operate", "Maintenance mode, drains, feature flags"),
        P("audit:read", "Read audit log"),
        P("settings:write", "Change system settings"),
    ]
}

ROLE_DEFINITIONS: dict[str, RoleDefinition] = {
    d.name: d
    for d in [
        RoleDefinition(
            LEARNER,
            "Default role for every account",
            (
                "content:read",
                "lab:start",
                "lab:manage-own",
                "vpn:issue",
                "progress:own",
                "scores:read",
                "events:compete",
                "teams:join",
            ),
        ),
        RoleDefinition(AUTHOR, "Creates and submits content", ("content:draft", "content:submit")),
        RoleDefinition(
            REVIEWER,
            "Reviews content submissions",
            ("content:review-technical", "content:review-instructional"),
        ),
        RoleDefinition(INSTRUCTOR, "Teaches cohorts", ("cohorts:assign", "reports:read")),
        RoleDefinition(SUPPORT, "Supports users with redacted access", ("users:support",)),
        RoleDefinition(
            OPERATOR,
            "Runs the installation",
            (
                "lab:manage-any",
                "system:operate",
                "audit:read",
                "moderation:queue",
                "content:manage",
            ),
        ),
        RoleDefinition(
            ADMIN,
            "Full control including publishing and settings",
            tuple(PERMISSIONS),
        ),
    ]
}

SECURITY_REVIEW_PERMISSION = PERMISSIONS["content:review-security"].id


def permissions_for_role(name: str) -> list[str]:
    return list(ROLE_DEFINITIONS[name].permissions)


def all_permissions() -> list[Permission]:
    return list(PERMISSIONS.values())
