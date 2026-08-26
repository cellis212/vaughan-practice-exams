"""Parameterized ("algorithmic") math questions: fresh numbers per exam.

A test-bank row opts in by filling the optional `params` column with
parameter draws (one per line, or separated by `;`):

    F = pick(10000, 20000, 50000)
    p = pick(0.002, 0.005, 0.01)
    prem = F * p * pick(2, 5, 10)

and by embedding `[[expr]]` placeholders in `Text`, the choice columns
`a`..`d`, and/or `b_info`:

    What is the expected underwriting profit if the premium is
    \\$[[num(prem)]]?         choice a: [[dollar(prem - F*p)]]

`[[ ]]` is the placeholder delimiter (not `{ }`) because the cells are full
of LaTeX braces. The `correct` column is unchanged: it names the choice
column holding the correct formula (choice shuffling in rc() then remaps it
as usual, so answer keys stay right for every draw).

Questions sharing a `block_id` are instantiated together in one shared
environment: put the scenario's draws on the block's first row (the one
carrying `b_info`) and every row of the block can reference them, so the
"based on the following information" numbers stay consistent.

Draws use the caller-supplied RNG (the same seeded RNG as question
sampling), so the "Random Seed" box reproduces an entire exam, numbers
included. After each draw the formatted choices of every question are
checked for duplicates (a distractor formula can collide with the correct
answer after rounding); on a collision, or a failed `require(...)`, the
whole group is redrawn. If no valid draw is found the generation fails with
an error naming the question rather than emitting a broken question.

Rows with an empty `params` column and no `[[` markers are returned
untouched and consume no RNG draws, so existing static banks behave — and
reproduce under a seed — exactly as before.

Available inside `params` lines and `[[ ]]` placeholders:
  pick(v1, v2, ...)        draw one of the listed values
  steps(lo, hi, step)      draw from lo, lo+step, ..., hi
  randint(a, b)            draw an integer in [a, b]
  require(cond)            redraw unless cond holds (params lines only)
  sqrt, exp, log, floor, ceil, abs, min, max, round, sum
  dollar(x, nearest=1)     \\$1,234 (rounded half-up to `nearest`)
  num(x, d=0, nearest=None) 1,234.56 with d decimals (commas, half-up)
  pct(x, d=1)              0.05 -> 5.0\\%
Plain arithmetic, comparisons, and `a if cond else b` are supported;
anything else is rejected with an error naming the expression.
"""

import ast
import math
import re
from decimal import Decimal, ROUND_HALF_UP


class RetryDraw(Exception):
    """A constraint failed for this draw; redraw the group's parameters."""


class ParamError(ValueError):
    """A template is malformed (bad expression, unknown name, ...)."""


_PLACEHOLDER_RE = re.compile(r"\[\[(.+?)\]\]", re.DOTALL)
_ASSIGN_RE = re.compile(r"^([A-Za-z_]\w*)\s*=(?![=])\s*(\S.*)$", re.DOTALL)

_FIELDS = ["Text", "a", "b", "c", "d", "b_info"]


def _round_nearest(x, nearest):
    """Round x to the nearest multiple of `nearest`, halves away from zero
    (what students are taught), not Python's round-half-even."""
    if nearest <= 0:
        raise ParamError("rounding step must be positive, got " + str(nearest))
    q = Decimal(repr(float(x))) / Decimal(repr(float(nearest)))
    return float(q.quantize(Decimal(1), rounding=ROUND_HALF_UP)) * nearest


def num(x, d=0, nearest=None):
    """Format a number with commas and d decimals, rounding half-up.
    `nearest` first rounds to that multiple (e.g. nearest=1000)."""
    if nearest is not None:
        x = _round_nearest(x, nearest)
    d = int(d)
    dec = Decimal(repr(float(x))).quantize(
        Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP
    )
    return "{:,.{d}f}".format(dec, d=d)


def dollar(x, nearest=1):
    """Format a dollar amount: dollar(1234.6) -> '\\$1,235' (LaTeX-escaped),
    negative amounts as '-\\$450'. `nearest` rounds to that multiple first
    (dollar(x, 100) matches a "round to nearest 00s" instruction)."""
    v = _round_nearest(x, nearest)
    sign = "-" if v < 0 else ""
    if nearest >= 1:
        return sign + "\\$" + "{:,.0f}".format(abs(v))
    return sign + "\\$" + "{:,.2f}".format(abs(v))


def pct(x, d=1):
    """Format a probability as a percentage: pct(0.05) -> '5.0\\%'."""
    return num(x * 100.0, d) + "\\%"


def _require(cond):
    if not cond:
        raise RetryDraw()
    return True


def _make_funcs(rng):
    """The callable environment; draw functions close over the exam RNG."""

    def pick(*vals):
        if not vals:
            raise ParamError("pick() needs at least one value")
        return vals[int(rng.random() * len(vals)) % len(vals)]

    def steps(lo, hi, step):
        n = int(math.floor((hi - lo) / step + 1e-9)) + 1
        if n < 1:
            raise ParamError("steps(%r, %r, %r) is an empty range" % (lo, hi, step))
        k = int(rng.random() * n) % n
        return round(lo + k * step, 10)

    def randint(a, b):
        return rng.randint(int(a), int(b))

    return {
        "pick": pick, "steps": steps, "randint": randint,
        "require": _require,
        "sqrt": math.sqrt, "exp": math.exp, "log": math.log,
        "floor": math.floor, "ceil": math.ceil,
        "abs": abs, "min": min, "max": max, "round": round, "sum": sum,
        "dollar": dollar, "num": num, "pct": pct,
    }


_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
                   ast.Mod, ast.Pow)
_ALLOWED_CMPOPS = (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq)


def _eval_node(node, env, funcs):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, env, funcs)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, str, bool)):
            return node.value
        raise ParamError("unsupported constant: " + repr(node.value))
    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        raise ParamError("unknown name '" + node.id + "'")
    if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_BINOPS):
        left = _eval_node(node.left, env, funcs)
        right = _eval_node(node.right, env, funcs)
        op = node.op
        if isinstance(op, ast.Add):
            return left + right
        if isinstance(op, ast.Sub):
            return left - right
        if isinstance(op, ast.Mult):
            return left * right
        if isinstance(op, ast.Div):
            return left / right
        if isinstance(op, ast.FloorDiv):
            return left // right
        if isinstance(op, ast.Mod):
            return left % right
        return left ** right
    if isinstance(node, ast.UnaryOp):
        val = _eval_node(node.operand, env, funcs)
        if isinstance(node.op, ast.USub):
            return -val
        if isinstance(node.op, ast.UAdd):
            return +val
        if isinstance(node.op, ast.Not):
            return not val
        raise ParamError("unsupported unary operator")
    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            result = True
            for v in node.values:
                result = _eval_node(v, env, funcs)
                if not result:
                    return result
            return result
        result = False
        for v in node.values:
            result = _eval_node(v, env, funcs)
            if result:
                return result
        return result
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, env, funcs)
        for op, comp in zip(node.ops, node.comparators):
            if not isinstance(op, _ALLOWED_CMPOPS):
                raise ParamError("unsupported comparison")
            right = _eval_node(comp, env, funcs)
            ok = (
                left < right if isinstance(op, ast.Lt) else
                left <= right if isinstance(op, ast.LtE) else
                left > right if isinstance(op, ast.Gt) else
                left >= right if isinstance(op, ast.GtE) else
                left == right if isinstance(op, ast.Eq) else
                left != right
            )
            if not ok:
                return False
            left = right
        return True
    if isinstance(node, ast.IfExp):
        cond = _eval_node(node.test, env, funcs)
        return _eval_node(node.body if cond else node.orelse, env, funcs)
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in funcs:
            raise ParamError("only these functions may be called: "
                             + ", ".join(sorted(funcs)))
        args = [_eval_node(a, env, funcs) for a in node.args]
        kwargs = {}
        for kw in node.keywords:
            if kw.arg is None:
                raise ParamError("** arguments are not supported")
            kwargs[kw.arg] = _eval_node(kw.value, env, funcs)
        return funcs[node.func.id](*args, **kwargs)
    raise ParamError("unsupported expression element: "
                     + type(node).__name__)


def safe_eval(expr, env, funcs):
    try:
        tree = ast.parse(expr.strip(), mode="eval")
    except SyntaxError as e:
        raise ParamError("bad expression '" + expr.strip() + "': " + str(e))
    return _eval_node(tree, env, funcs)


def run_spec(spec, env, funcs, where):
    """Execute a `params` cell: assignments and bare require(...) lines,
    split on newlines and semicolons, evaluated in order into env."""
    for raw in re.split(r"[\n;]", spec):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _ASSIGN_RE.match(line)
        if m:
            env[m.group(1)] = safe_eval(m.group(2), env, funcs)
        else:
            safe_eval(line, env, funcs)


def _format_value(v):
    if isinstance(v, str):
        return v
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float):
        return "%g" % v
    return str(v)


def _substitute(text, env, funcs, where):
    def repl(m):
        return _format_value(safe_eval(m.group(1), env, funcs))

    out = _PLACEHOLDER_RE.sub(repl, text)
    if "[[" in out or "]]" in out:
        raise ParamError("unbalanced [[ ]] placeholder in " + where
                         + ": " + text)
    return out


def _needs_instantiation(rows):
    for row in rows:
        if row.get("params"):
            return True
        for f in _FIELDS:
            v = row.get(f)
            if isinstance(v, str) and "[[" in v:
                return True
    return False


def _group_label(rows):
    ids = [str(row.get("q_id")) for row in rows]
    return ("question q_id=" + ids[0] if len(ids) == 1
            else "block q_id=" + ",".join(ids))


def instantiate_group(rows, rng, max_tries=100):
    """Draw one shared parameter environment for `rows` (a block, or a
    single standalone question) and substitute every placeholder. Redraws
    on require() failures and duplicate formatted choices."""
    funcs = _make_funcs(rng)
    where = _group_label(rows)
    for _ in range(max_tries):
        env = {}
        try:
            for row in rows:
                spec = row.get("params")
                if spec:
                    run_spec(spec, env, funcs, where)
            new_rows = []
            for row in rows:
                new_row = dict(row)
                for f in _FIELDS:
                    v = row.get(f)
                    if isinstance(v, str) and "[[" in v:
                        new_row[f] = _substitute(v, env, funcs, where)
                choices = [new_row.get(k) for k in ("a", "b", "c", "d")]
                choices = [c.strip() for c in choices if c is not None]
                if len(set(choices)) != len(choices):
                    raise RetryDraw()
                new_rows.append(new_row)
        except RetryDraw:
            continue
        except ParamError as e:
            raise ParamError(str(e) + " (in " + where + ")")
        return new_rows
    raise ParamError(
        "Could not draw distinct answer choices for " + where + " after "
        + str(max_tries) + " tries; widen the parameter pools or fix a "
        + "distractor formula that always equals another choice."
    )


def instantiate_bank(bank, rng):
    """Instantiate every parameterized question/block in `bank` (a list of
    row dicts), returning a new list. Rows of a block (same Topic and
    block_id, mirroring create_exam's grouping) share one draw. Static rows
    pass through unchanged, consuming no RNG draws."""
    out = list(bank)
    done = set()
    for i, row in enumerate(bank):
        if i in done:
            continue
        if row.get("block_id") is None:
            idxs = [i]
        else:
            idxs = [
                j for j in range(len(bank))
                if bank[j].get("block_id") == row.get("block_id")
                and bank[j].get("Topic") == row.get("Topic")
            ]
        done.update(idxs)
        group = [bank[j] for j in idxs]
        if _needs_instantiation(group):
            new_rows = instantiate_group(group, rng)
            for j, nr in zip(idxs, new_rows):
                out[j] = nr
    return out
