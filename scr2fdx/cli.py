"""CLI entry point for scr2fdx converter."""

import argparse
import sys
from pathlib import Path

from .parser import parse_scr
from .fdx_writer import write_fdx


def main():
    parser = argparse.ArgumentParser(
        description="Convert ScriptWare (.SCR) files to Final Draft XML (.fdx)",
    )
    parser.add_argument("input", nargs="+", help="Input .SCR file(s)")
    parser.add_argument(
        "-o", "--output-dir",
        default="converted",
        help="Output directory (default: converted/)",
    )
    parser.add_argument(
        "--dump", action="store_true",
        help="Print parsed elements to stdout instead of writing FDX",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print progress info",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if not args.dump:
        output_dir.mkdir(parents=True, exist_ok=True)

    success = 0
    failed = 0

    for input_path in args.input:
        path = Path(input_path)
        if not path.exists():
            print(f"ERROR: {path} not found", file=sys.stderr)
            failed += 1
            continue

        try:
            if args.verbose:
                print(f"Parsing {path.name}...")

            script = parse_scr(path)

            if args.dump:
                _dump_script(script, path.name)
            else:
                out_path = output_dir / path.with_suffix(".fdx").name
                write_fdx(script, out_path)
                if args.verbose:
                    print(f"  -> {out_path} ({len(script.elements)} elements)")
            success += 1

        except Exception as e:
            print(f"ERROR: {path.name}: {e}", file=sys.stderr)
            failed += 1

    if len(args.input) > 1:
        print(f"\nConverted {success}/{success + failed} files")

    return 1 if failed > 0 else 0


def _dump_script(script, filename):
    """Print parsed script elements for debugging."""
    print(f"=== {filename} (v{script.metadata.version}) ===")
    print(f"Characters: {list(script.metadata.characters.values())}")
    print()
    for elem in script.elements:
        type_name = elem.element_type.name
        text = elem.text[:70] + "..." if len(elem.text) > 70 else elem.text
        print(f"  [{type_name:20s}] {text}")
    print()


if __name__ == "__main__":
    sys.exit(main())
