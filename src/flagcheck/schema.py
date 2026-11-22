"""Explicit command schemas and non-executing argparse source extraction."""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Flag:
    nargs: int | str = 0
    deprecated: bool = False
    replacement: str | None = None


@dataclass(frozen=True)
class Command:
    flags: dict[str, Flag] = field(default_factory=dict)
    subcommands: dict[str, Command] = field(default_factory=dict)
    complete: bool = False
    allow_abbrev: bool = True


def _command(raw: object) -> Command:
    if not isinstance(raw, dict):
        raise ValueError("command must be an object")
    if set(raw) - {"flags", "subcommands", "complete", "allow_abbrev"}:
        raise ValueError("unrecognized command schema keys")
    flags = raw.get("flags", {})
    children = raw.get("subcommands", {})
    if not isinstance(flags, dict) or not isinstance(children, dict):
        raise ValueError("flags and subcommands must be objects")
    for k in ("complete", "allow_abbrev"):
        if k in raw and type(raw[k]) is not bool:
            raise ValueError(f"{k} must be a boolean")
    result = {}
    for name, value in flags.items():
        if not isinstance(name, str) or not name.startswith("-") or name in {"-", "--"}:
            raise ValueError(f"invalid option name: {name!r}")
        if not isinstance(value, dict) or set(value) - {"nargs", "deprecated", "replacement"}:
            raise ValueError(f"invalid flag metadata for {name}")
        n = value.get("nargs", 0)
        if not ((type(n) is int and n >= 0) or n in ("?", "*", "+", "...")):
            raise ValueError(f"invalid nargs for {name}")
        deprecated = value.get("deprecated", False)
        replacement = value.get("replacement")
        if type(deprecated) is not bool or (replacement is not None and not isinstance(replacement, str)):
            raise ValueError(f"invalid deprecation metadata for {name}")
        result[name] = Flag(n, deprecated, replacement)
    return Command(result, {name: _command(value) for name, value in children.items()},
                   raw.get("complete", False), raw.get("allow_abbrev", True))


def load_schema(path: Path) -> dict[str, Command]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not raw:
        raise ValueError("schema must be a non-empty command-name mapping")
    return {name: _command(spec) for name, spec in raw.items()}


def _literal(node: ast.AST, default: object = None) -> object:
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return default


def extract_argparse(source: str, receivers: set[str], *,
                     action_arities: dict[str, int] | None = None,
                     implicit_help: bool = False) -> tuple[dict, list[str]]:
    """Extract literal add_argument calls on explicitly selected receivers.

    Does not import or execute source. Dynamic declarations are reported as
    limitations; mutually exclusive runtime branches are a union.
    """
    tree = ast.parse(source)
    overrides = action_arities or {}
    if any(type(n) is not int or n < 0 for n in overrides.values()):
        raise ValueError("custom action arities must be nonnegative integers")
    flags: dict[str, dict] = {}
    notes: list[str] = []
    no_value = {"store_true", "store_false", "store_const", "append_const", "count", "help", "version"}
    # Direct constructor calls are the only case where we infer implicit help.
    # Indirect factories and wrappers require explicit reviewer confirmation.
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(t, ast.Name) and t.id in receivers for t in targets):
            continue
        call = node.value
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Attribute):
            continue
        if not (isinstance(call.func.value, ast.Name) and call.func.value.id == "argparse"
                and call.func.attr == "ArgumentParser"):
            continue
        kw = {k.arg: _literal(k.value, "<dynamic>") for k in call.keywords}
        if None in kw:
            notes.append(f"line {node.lineno}: dynamic parser configuration")
            continue
        if kw.get("parents") not in (None, [], ()):
            notes.append(f"line {node.lineno}: inherited parent parser options require review")
        help_enabled = kw.get("add_help", True)
        prefix = kw.get("prefix_chars", "-")
        if help_enabled is True and isinstance(prefix, str) and "-" in prefix:
            implicit_help = True
        elif help_enabled not in (True, False) or prefix == "<dynamic>":
            notes.append(f"line {node.lineno}: unresolved automatic help configuration")

    if implicit_help:
        flags.update({"-h": {"nargs": 0}, "--help": {"nargs": 0}})

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "add_argument" or not isinstance(node.func.value, ast.Name):
            continue
        if node.func.value.id not in receivers:
            continue
        names = [_literal(x) for x in node.args]
        if not names or not all(isinstance(x, str) for x in names):
            notes.append(f"line {node.lineno}: non-literal option declaration")
            continue
        if not names[0].startswith("-"):
            continue
        if any(kw.arg is None for kw in node.keywords):
            notes.append(f"line {node.lineno}: dynamic keyword arguments")
            continue
        keywords = {kw.arg: _literal(kw.value, "<dynamic>") for kw in node.keywords}
        action = keywords.get("action", "store")
        action_node = next((kw.value for kw in node.keywords if kw.arg == "action"), None)
        if action == "<dynamic>" and isinstance(action_node, (ast.Name, ast.Attribute)):
            action = ast.unparse(action_node)
        if isinstance(action, str) and action in no_value:
            nargs = 0
        elif (isinstance(action_node, ast.Attribute)
              and isinstance(action_node.value, ast.Name)
              and action_node.value.id == "argparse"
              and action_node.attr == "BooleanOptionalAction"):
            # argparse creates a negative alias for every long option. A
            # custom action with a similar name is not assumed equivalent.
            if any(name.startswith("--no-") for name in names):
                notes.append(f"line {node.lineno}: negative BooleanOptionalAction declaration requires review")
                continue
            names = [alias for name in names for alias in
                     ([name, "--no-" + name[2:]] if name.startswith("--") else [name])]
            nargs = 0
        elif isinstance(action, str) and action in {"store", "append", "extend"}:
            nargs = keywords.get("nargs", 1)
        elif isinstance(action, str) and action in overrides:
            nargs = overrides[action]
        else:
            notes.append(f"line {node.lineno}: unsupported action {action!r}")
            continue
        if not ((type(nargs) is int and nargs >= 0) or nargs in ("?", "*", "+")):
            notes.append(f"line {node.lineno}: unsupported nargs {nargs!r}")
            continue
        meta = {"nargs": nargs}
        if keywords.get("deprecated") is True:
            meta["deprecated"] = True
        for name in names:
            if name in flags and flags[name] != meta:
                notes.append(f"line {node.lineno}: conflicting declarations for {name}")
            flags[name] = meta
    return flags, notes
