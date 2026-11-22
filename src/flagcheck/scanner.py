"""Conservative shell scanning. Never executes a scanned command."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml
from yaml.nodes import MappingNode, ScalarNode, SequenceNode

from flagcheck.schema import Command, Flag


@dataclass(frozen=True)
class Finding:
    source: str
    line: int
    command: str
    flag: str
    code: str
    severity: str
    message: str
    suggestion: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScanStats:
    """Partial coverage counters; unsupported file contexts are not enumerated."""
    logical_commands: int = 0
    matched_invocations: int = 0
    unmatched_segments: int = 0
    checked_long_options: int = 0
    lexer_failures: int = 0
    incomplete_invocations: int = 0


@dataclass(frozen=True)
class Token:
    value: str
    dynamic: bool = False
    operator: bool = False


_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_NEGATIVE = re.compile(r"^-\d+(?:\.\d+)?$")


def _lex(text: str) -> list[Token] | None:
    """Recognize simple shell words, quoted words and control operators.

    Variable expansions remain opaque; unsupported constructs are skipped.
    """
    tokens: list[Token] = []
    buf: list[str] = []
    quote = ""
    dynamic = started = False
    i = 0

    def flush() -> None:
        nonlocal dynamic, started
        if started:
            tokens.append(Token("".join(buf), dynamic))
            buf.clear()
        dynamic = started = False

    while i < len(text):
        c = text[i]
        if quote == "'":
            if c == "'":
                quote = ""
            else:
                buf.append(c)
            i += 1
            continue
        if c == "\\" and i + 1 < len(text):
            nxt = text[i + 1]
            if not quote or nxt in '\\"$`\n':
                if nxt != "\n":
                    buf.append(nxt)
                    started = True
                i += 2
                continue
        if c == quote:
            quote = ""
            i += 1
            continue
        if not quote and c in "'\"":
            quote = c
            started = True
            i += 1
            continue
        if c in "$`":
            dynamic = True
            # Keep $(...), ${...} and Make substitutions as a single opaque word.
            if c == "$" and i + 1 < len(text) and text[i + 1] in "({":
                opener = text[i + 1]
                closer = ")" if opener == "(" else "}"
                # This subset intentionally skips nested quotes/parentheses
                # inside complex shell substitutions if they are unbalanced.
                j = i + 2
                depth = 1
                while j < len(text) and depth:
                    if text[j] == opener:
                        depth += 1
                    elif text[j] == closer:
                        depth -= 1
                    j += 1
                if depth:
                    return None
                buf.append(text[i:j])
                started = True
                i = j
                continue
            if c == "`":
                j = text.find("`", i + 1)
                if j < 0:
                    return None
                buf.append(text[i:j + 1])
                started = True
                i = j + 1
                continue
        if not quote:
            if c.isspace():
                flush()
                i += 1
                continue
            if c == "#" and not started:
                break
            if c in ";&|<>()":
                flush()
                j = i + 1
                if j < len(text) and text[i:j + 1] in {"&&", "||", ">>", "<<", "|&", ">&", "<&"}:
                    j += 1
                tokens.append(Token(text[i:j], operator=True))
                i = j
                continue
            if c in "*?[]~":
                dynamic = True
        started = True
        buf.append(c)
        i += 1
    if quote:
        return None
    flush()
    return tokens


def _segments(tokens: list[Token]):
    current: list[Token] = []
    redirected = False
    for token in tokens:
        if token.operator:
            if token.value in {";", "&&", "||", "|", "|&", "&"}:
                if current:
                    yield current
                current = []
                redirected = False
            else:
                # Do not guess operands after redirections or compound syntax.
                redirected = True
        elif not redirected:
            current.append(token)
    if current:
        yield current


def _basename(value: str) -> str:
    return value.rsplit("/", 1)[-1]


def _consume(args: list[Token], index: int, spec: Flag, attached: bool) -> int | None:
    if spec.nargs == "?":
        if attached or index + 1 >= len(args):
            return index + 1
        following = args[index + 1]
        if following.dynamic:
            return None
        if following.value.startswith("-") and following.value != "-" and not _NEGATIVE.fullmatch(following.value):
            return index + 1
        return index + 2
    if type(spec.nargs) is not int:
        return None  # variadic values cannot be inferred safely
    remaining = max(0, spec.nargs - int(attached))
    return index + remaining + 1


def _inspect(tokens: list[Token], schemas: dict[str, Command], source: str, line: int,
             depth: int, stats: ScanStats | None = None) -> list[Finding]:
    i = 0
    while i < len(tokens) and (_ASSIGN.match(tokens[i].value) or tokens[i].value in {"env", "command", "exec", "time", "sudo", "do", "then", "else"}):
        i += 1
    if i >= len(tokens) or tokens[i].dynamic:
        if stats is not None:
            stats.unmatched_segments += 1
        return []
    command = _basename(tokens[i].value)
    args = tokens[i + 1:]
    # Narrow literal forms of commonly used project runners. Do not attempt to
    # interpret arbitrary runner options or dynamically selected executables.
    if depth < 4 and command in {"pipenv", "uv"} and len(args) >= 2 and args[0].value == "run" and not args[1].dynamic and not args[1].value.startswith("-"):
        return _inspect(args[1:], schemas, source, line, depth + 1, stats)
    if depth < 4 and command == "uvx" and args:
        first = 2 if len(args) >= 3 and args[0].value == "--from" and not args[1].dynamic else 0
        if not args[first].dynamic and not args[first].value.startswith("-"):
            return _inspect(args[first:], schemas, source, line, depth + 1, stats)
    if command in {"python", "python3"} and len(args) >= 2 and args[0].value == "-m" and not args[1].dynamic:
        command = args[1].value
        args = args[2:]
    if command in {"bash", "sh"} and depth < 2 and len(args) >= 2 and re.fullmatch(r"-[a-zA-Z]*c[a-zA-Z]*", args[0].value):
        return scan_command(args[1].value, schemas, source, line, depth + 1, stats=stats)
    spec = schemas.get(command)
    if spec is None:
        if stats is not None:
            stats.unmatched_segments += 1
        return []
    if stats is not None:
        stats.matched_invocations += 1
    incomplete = False
    i = 0
    results: list[Finding] = []
    while i < len(args):
        token = args[i]
        word = token.value
        if word == "--":
            break
        if word.startswith("--"):
            flag, sep, value = word.partition("=")
            if token.dynamic and (not sep or any(c in flag for c in "$`*?[]~")):
                incomplete = True
                break
            known = spec.flags.get(flag)
            if known is not None:
                if stats is not None:
                    stats.checked_long_options += 1
                if known.deprecated:
                    results.append(Finding(source, line, command, flag, "deprecated", "warning", f"{flag} is deprecated", known.replacement))
            elif not spec.complete:
                incomplete = True
                break
            else:
                if stats is not None:
                    stats.checked_long_options += 1
                matches = sorted(f for f in spec.flags if f.startswith(flag) and f.startswith("--"))
                if len(matches) == 1 and spec.allow_abbrev:
                    canonical = matches[0]
                    known = spec.flags[canonical]
                    results.append(Finding(source, line, command, flag, "abbreviation", "warning", f"Use the full option {canonical}", canonical))
                elif len(matches) > 1 and spec.allow_abbrev:
                    results.append(Finding(source, line, command, flag, "ambiguous", "error", "Matches " + ", ".join(matches)))
                    incomplete = i + 1 < len(args)
                    break
                else:
                    results.append(Finding(source, line, command, flag, "unknown", "error", f"Unknown option {flag}", matches[0] if len(matches) == 1 else None))
                    incomplete = i + 1 < len(args)
                    break
            nxt = _consume(args, i, known, bool(sep))
            if nxt is None:
                incomplete = True
                break
            i = nxt
            continue
        if token.dynamic:
            incomplete = True
            break
        if word.startswith("-") and word != "-" and not _NEGATIVE.fullmatch(word):
            # Only long options are linted. Known short options are consumed
            # to avoid interpreting their values as options.
            known = spec.flags.get(word)
            if known is not None:
                nxt = _consume(args, i, known, False)
                if nxt is None:
                    incomplete = True
                    break
                i = nxt
                continue
            # Argparse-style clusters: exact short spelling takes priority,
            # otherwise consume known switches and any attached final value.
            # We never diagnose an unrecognized short switch.
            nxt = i + 1
            for position, char in enumerate(word[1:], 1):
                short = spec.flags.get("-" + char)
                if short is None:
                    nxt = None
                    break
                if short.nargs != 0:
                    nxt = _consume(args, i, short, position < len(word) - 1)
                    break
            if nxt is not None:
                i = nxt
                continue
            incomplete = True
            break
        if spec.subcommands:
            child = spec.subcommands.get(word)
            if child is None:
                incomplete = True
                break
            spec = child
            command += " " + word
        i += 1
    if stats is not None and incomplete:
        stats.incomplete_invocations += 1
    return results


def scan_command(text: str, schemas: dict[str, Command], source: str = "<command>",
                 line: int = 1, depth: int = 0, *, stats: ScanStats | None = None) -> list[Finding]:
    tokens = _lex(text.strip())
    if tokens is None:
        if stats is not None:
            stats.lexer_failures += 1
        return []
    if tokens and stats is not None:
        stats.logical_commands += 1
    results: list[Finding] = []
    for segment in _segments(tokens):
        results.extend(_inspect(segment, schemas, source, line, depth, stats))
    return results


def _logical_lines(lines):
    parts: list[str] = []
    start = 0
    heredocs: list[tuple[str, bool]] = []
    for number, line in lines:
        if heredocs:
            delimiter, strip_tabs = heredocs[0]
            if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                heredocs.pop(0)
            continue
        if not parts:
            start = number
        trailing = len(line) - len(line.rstrip("\\"))
        if trailing % 2:
            parts.append(line[:-1])
        else:
            parts.append(line)
            logical = "".join(parts)
            yield start, logical
            tokens = _lex(logical) or []
            for index, token in enumerate(tokens[:-1]):
                if token.operator and token.value == "<<":
                    following = tokens[index + 1]
                    if following.operator:
                        continue
                    delimiter = following.value
                    strip_tabs = delimiter.startswith("-")
                    if strip_tabs:
                        delimiter = delimiter[1:]
                    heredocs.append((delimiter, strip_tabs))
            parts = []
    # An unfinished continuation is not a complete command.


def _make(text: str):
    continuation = False
    for number, line in enumerate(text.splitlines(), 1):
        if not continuation and not line.startswith("\t"):
            continue
        body = line.removeprefix("\t")
        if not continuation:
            body = body.lstrip("@+-")
        # GNU Make's single-dollar automatic variables denote target or
        # prerequisite filenames. Do not rewrite escaped shell variables ($$).
        body = re.sub(r"(?<!\$)\$[@<^+?*%|]", "__MAKE_PATH__", body)
        yield number, body
        continuation = (len(body) - len(body.rstrip("\\"))) % 2 == 1


def _markdown(text: str):
    fence = None
    language = ""
    block: list[tuple[int, str]] = []
    for number, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if fence is None and m:
            fence = m[1]
            names = m[2].strip().lower().split()
            language = names[0] if names else ""
            block = []
        elif fence and m and m[1][0] == fence[0] and len(m[1]) >= len(fence) and not m[2].strip():
            if language in {"bash", "sh", "shell", "zsh", "console"}:
                yield from _logical_lines(block)
            fence = None
        elif fence and (language in {"bash", "sh", "shell", "zsh"} or (language == "console" and re.match(r"^\s*\$ ", line))):
            block.append((number, re.sub(r"^\s*\$ ", "", line)))


def _mapping(node, key):
    if isinstance(node, MappingNode):
        return next((v for k, v in node.value if isinstance(k, ScalarNode) and k.value == key), None)
    return None


def _workflow(text: str):
    root = yaml.compose(text, Loader=yaml.SafeLoader)
    jobs = _mapping(root, "jobs")
    if not isinstance(jobs, MappingNode):
        return
    for _, job in jobs.value:
        steps = _mapping(job, "steps")
        if not isinstance(steps, SequenceNode):
            continue
        for step in steps.value:
            run = _mapping(step, "run")
            shell = (_mapping(step, "shell") or _mapping(_mapping(job, "defaults"), "run")
                     or _mapping(_mapping(root, "defaults"), "run"))
            if isinstance(shell, MappingNode):
                shell = _mapping(shell, "shell")
            if isinstance(shell, ScalarNode) and shell.value not in {"bash", "sh"}:
                continue
            if shell is None:
                runner = _mapping(job, "runs-on")
                if not isinstance(runner, ScalarNode) or not runner.value.startswith(("ubuntu-", "macos-")):
                    continue  # default shell depends on the operating system
            if not isinstance(run, ScalarNode) or run.style == ">":
                continue  # folded source mapping is intentionally unsupported
            start = run.start_mark.line + (2 if run.style == "|" else 1)
            yield from _logical_lines(enumerate(run.value.splitlines(), start))


def scan_text(text: str, schemas: dict[str, Command], kind: str = "shell", source: str = "<stdin>", *, stats: ScanStats | None = None) -> list[Finding]:
    if kind == "make":
        commands = _logical_lines(_make(text))
    elif kind == "markdown":
        commands = _markdown(text)
    elif kind == "workflow":
        commands = _workflow(text)
    else:
        commands = _logical_lines(enumerate(text.splitlines(), 1))
    return [f for number, command in commands for f in scan_command(command, schemas, source, number, stats=stats)]


def file_kind(path: Path) -> str | None:
    if path.name.lower() in {"makefile", "gnumakefile"} or path.suffix == ".mk":
        return "make"
    if path.suffix.lower() in {".md", ".markdown"}:
        return "markdown"
    if path.suffix.lower() in {".sh", ".bash", ".zsh"}:
        return "shell"
    if path.suffix.lower() in {".yml", ".yaml"} and ".github" in path.parts and "workflows" in path.parts:
        return "workflow"
    return None
