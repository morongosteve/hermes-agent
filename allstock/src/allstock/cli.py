"""Command-line interface for AllStock.

    allstock develop  IN -o OUT --stock portra400 [--exposure +1 --push 2]
    allstock stocks   [--show portra400]
    allstock design   blend portra400 velvia50 -t 0.3 -o my.json
    allstock generate "a neon street at night" --stock cinestill800t -o out.png
    allstock learn    [topic | --search grain]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from . import designer, knowledge, library
from .engine import DevelopOptions, develop_file
from .stock import FilmStock


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _resolve_stock(ref: str) -> FilmStock:
    """Resolve a stock from a built-in key or a path to a JSON file."""
    p = Path(ref)
    if p.suffix.lower() == ".json" and p.is_file():
        return FilmStock.load(p)
    try:
        return library.get_stock(ref)
    except KeyError:
        if p.is_file():
            return FilmStock.load(p)
        raise


def _default_out(in_path: str, stock: FilmStock, suffix: str = ".jpg") -> str:
    stem = Path(in_path).stem
    tag = stock.name.lower().replace(" ", "_").replace("/", "-")
    return f"{stem}__{tag}{suffix}"


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------
def cmd_develop(args) -> int:
    stock = _resolve_stock(args.stock)
    out = args.out or _default_out(args.input, stock)
    opts = DevelopOptions(
        exposure=args.exposure,
        push=args.push,
        seed=args.seed,
        grain=not args.no_grain,
        halation=not args.no_halation,
        optics=not args.no_optics,
        max_side=args.max_side,
    )
    path = develop_file(args.input, out, stock, opts)
    print(f"Developed '{args.input}' on {stock.name} -> {path}")
    return 0


def cmd_stocks(args) -> int:
    if args.show:
        stock = _resolve_stock(args.show)
        print(stock.summary())
        return 0
    print("Built-in film stocks:\n")
    for key in library.list_stocks():
        s = library.get_stock(key)
        print(f"  {key:16s} {s.name}  (ISO {s.iso}, {s.process_family})")
    print("\nShow details:  allstock stocks --show <key>")
    return 0


def cmd_design(args) -> int:
    op = args.op
    if op == "blend":
        a, b = _resolve_stock(args.a), _resolve_stock(args.b)
        result = designer.blend(a, b, args.t, name=args.name)
    elif op == "mix":
        stocks = [_resolve_stock(s) for s in args.stocks]
        weights = args.weights if args.weights else None
        result = designer.mix(stocks, weights, name=args.name)
    elif op == "cross":
        base = _resolve_stock(args.base)
        kw = {}
        for grp in ("curves", "grain", "halation", "optics", "print", "spectral", "development"):
            ref = getattr(args, grp)
            if ref:
                key = "print_" if grp == "print" else grp
                kw[key] = _resolve_stock(ref)
        result = designer.cross(base, name=args.name, **kw)
    elif op == "mutate":
        base = _resolve_stock(args.stock)
        result = designer.mutate(base, amount=args.amount, seed=args.seed, name=args.name)
    else:  # pragma: no cover
        print(f"Unknown design op {op!r}", file=sys.stderr)
        return 2

    print(result.summary())
    if args.out:
        path = result.save(args.out)
        print(f"\nSaved forged stock -> {path}")
    else:
        print("\n(add -o my_stock.json to save this stock)")
    return 0


def cmd_generate(args) -> int:
    try:
        from .generate import DevelopOptions as _DO  # noqa
        from .generate import generate_and_develop
        from .imaging import save_image
        from .imaging import srgb_to_linear
        import numpy as np
    except Exception as e:  # pragma: no cover
        print(f"Generation unavailable: {e}", file=sys.stderr)
        return 1

    stock = _resolve_stock(args.stock)
    width, height = _parse_size(args.size, args.width, args.height)
    try:
        positive, info = generate_and_develop(
            args.prompt, stock,
            provider=args.provider, width=width, height=height, seed=args.seed,
            raw_prompt=args.raw, extra=args.extra,
            develop=DevelopOptions(seed=args.seed) if not args.no_develop else None,
        )
    except RuntimeError as e:
        print(f"{e}\n\nTip: run offline with  --provider null  to test the pipeline, "
              f"or set the provider's API key (e.g. ZAI_API_KEY for Z.ai).",
              file=sys.stderr)
        return 1

    out = args.out or f"generated__{stock.name.lower().replace(' ', '_')}.png"
    if args.no_develop:
        info.image.save(out)
    else:
        save_image(positive, out)
    print(f"[{info.provider}:{info.model}] developed on {stock.name} -> {out}")
    print(f"prompt: {info.prompt}")
    if args.save_raw:
        info.image.save(args.save_raw)
        print(f"raw generation -> {args.save_raw}")
    return 0


def cmd_learn(args) -> int:
    if args.search:
        hits = knowledge.search(args.search)
        if not hits:
            print(f"No matches for {args.search!r}.")
            return 0
        for slug, lines in hits.items():
            print(f"\n## {slug}")
            for ln in lines[:5]:
                print(f"  - {ln}")
        return 0
    if args.topic:
        try:
            print(knowledge.get_topic(args.topic))
        except KeyError as e:
            print(str(e), file=sys.stderr)
            return 1
        return 0
    print("Analog film knowledge base:\n")
    for slug, title in knowledge.list_topics():
        print(f"  {slug:24s} {title}")
    print("\nRead one:   allstock learn <slug>")
    print("Search:     allstock learn --search <query>")
    return 0


def _parse_size(size: Optional[str], width: int, height: int):
    if size:
        try:
            w, h = size.lower().split("x")
            return int(w), int(h)
        except ValueError:
            raise SystemExit(f"--size must look like 1024x768, got {size!r}")
    return width, height


# --------------------------------------------------------------------------
# parser
# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="allstock",
        description="Physically-grounded analog film emulation, a film-stock "
                    "designer, an analog knowledge base, and analog-aware generation.",
    )
    p.add_argument("--version", action="store_true", help="print version and exit")
    sub = p.add_subparsers(dest="command")

    # develop
    d = sub.add_parser("develop", help="develop an image on a film stock")
    d.add_argument("input")
    d.add_argument("-o", "--out", help="output path (default derived from input)")
    d.add_argument("-s", "--stock", default="portra400",
                   help="built-in key or path to a stock .json")
    d.add_argument("-e", "--exposure", type=float, default=0.0,
                   help="exposure compensation in stops")
    d.add_argument("--push", type=float, default=None, help="push/pull in stops")
    d.add_argument("--seed", type=int, default=0, help="grain seed")
    d.add_argument("--no-grain", action="store_true")
    d.add_argument("--no-halation", action="store_true")
    d.add_argument("--no-optics", action="store_true")
    d.add_argument("--max-side", type=int, default=None,
                   help="downscale longest side to N px (preview/speed)")
    d.set_defaults(func=cmd_develop)

    # stocks
    s = sub.add_parser("stocks", help="list or inspect film stocks")
    s.add_argument("--show", help="show details for a stock key or .json")
    s.set_defaults(func=cmd_stocks)

    # design
    de = sub.add_parser("design", help="forge new stocks via combination edits")
    deop = de.add_subparsers(dest="op", required=True)

    b = deop.add_parser("blend", help="interpolate two stocks")
    b.add_argument("a"); b.add_argument("b")
    b.add_argument("-t", type=float, default=0.5, help="0=a, 1=b")
    b.add_argument("-o", "--out"); b.add_argument("--name")
    b.set_defaults(func=cmd_design)

    m = deop.add_parser("mix", help="weighted average of several stocks")
    m.add_argument("stocks", nargs="+")
    m.add_argument("--weights", type=float, nargs="+")
    m.add_argument("-o", "--out"); m.add_argument("--name")
    m.set_defaults(func=cmd_design)

    c = deop.add_parser("cross", help="splice subsystems from different stocks")
    c.add_argument("base")
    for grp in ("curves", "grain", "halation", "optics", "print", "spectral", "development"):
        c.add_argument(f"--{grp}", help=f"take {grp} from this stock")
    c.add_argument("-o", "--out"); c.add_argument("--name")
    c.set_defaults(func=cmd_design)

    mu = deop.add_parser("mutate", help="randomly explore nearby looks")
    mu.add_argument("stock")
    mu.add_argument("--amount", type=float, default=0.15)
    mu.add_argument("--seed", type=int, default=0)
    mu.add_argument("-o", "--out"); mu.add_argument("--name")
    mu.set_defaults(func=cmd_design)

    # generate
    g = sub.add_parser("generate", help="generate an image and develop it on film")
    g.add_argument("prompt")
    g.add_argument("-s", "--stock", default="portra400")
    g.add_argument("-o", "--out")
    g.add_argument("-p", "--provider", default="zai",
                   help="zai (Z.ai/CogView, default), openai, stability, "
                        "huggingface, replicate, or null (offline)")
    g.add_argument("--size", help="WxH, e.g. 1024x768")
    g.add_argument("--width", type=int, default=1024)
    g.add_argument("--height", type=int, default=1024)
    g.add_argument("--seed", type=int, default=0)
    g.add_argument("--raw", action="store_true", help="use prompt verbatim (no film language)")
    g.add_argument("--extra", help="extra prompt text appended")
    g.add_argument("--no-develop", action="store_true", help="skip film engine")
    g.add_argument("--save-raw", help="also save the raw generated image here")
    g.set_defaults(func=cmd_generate)

    # learn
    le = sub.add_parser("learn", help="read the analog film knowledge base")
    le.add_argument("topic", nargs="?", help="topic slug (omit to list)")
    le.add_argument("--search", help="search across notes")
    le.set_defaults(func=cmd_learn)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "version", False):
        from . import __version__
        print(f"allstock {__version__}")
        return 0
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
