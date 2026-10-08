#!/usr/bin/env python3
"""Cut the site's web fonts from pinned official font files (#319).

The site ships its fonts instead of fetching them from Google Fonts at build
time. Each font starts from a file in its foundry's repository, pinned below
by commit and SHA-256, and is cut down the way Google cut the copies the site
used to download: set to the instance Google served, hinting removed, and
subset to Google's "latin" range plus every other character the site
renders. That character set is recorded in site/src/fonts/fonts.json with
each output's SHA-256, and scripts/check_site_font_coverage.py fails CI when
a page renders a character outside it.

Outputs, all woff2, in site/src/fonts/:
  archivo/Archivo-latin.woff2
      Archivo[wdth,wght].ttf with width set to 100; weight stays variable
      over the source's full 100-900 range with its 600 default, as in the
      file Google served. Trimming or recentering that axis rounds every
      glyph's advance at the site's weights differently from Google's copy,
      enough to move line breaks.
  newsreader/Newsreader-Italic-latin.woff2
      Newsreader-Italic[opsz,wght].ttf at optical size 16, weight 400: the
      instance Google served, with the same advance widths. This source is
      byte-identical to the file Google Fonts publishes.
  JetBrainsMono-latin.woff2
      JetBrainsMono[wght].woff2; weight stays variable, trimmed to 400-700.

The tool versions are pinned so the same inputs give byte-identical files:

  python3 -m pip install fonttools==4.63.0 brotli==1.2.0
  python3 scripts/build_site_fonts.py                  # recut with the recorded set
  python3 scripts/build_site_fonts.py --from-site URL  # rescan a running build first

Per font, that is fontTools.varLib.instancer for the instance, then the
equivalent of: pyftsubset --unicodes=<fonts.json unicodes> --flavor=woff2
--no-hinting --layout-features+=pnum,tnum (Google kept the numeral features).
"""

import argparse
import hashlib
import json
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

from check_site_font_coverage import FONTS_DIR, MANIFEST, parse_unicodes, site_characters

FONTTOOLS, BROTLI = "4.63.0", "1.2.0"

# Google's "latin" subset, the range the site's fonts covered before #319.
LATIN = (
    "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,"
    "U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,"
    "U+FEFF,U+FFFD"
)

FONTS = [
    {
        "out": "archivo/Archivo-latin.woff2",
        "repo": "Omnibus-Type/Archivo",
        "commit": "211127690e8ff106c36c935f7e5e697114cff103",
        "path": "fonts/variable/Archivo[wdth,wght].ttf",
        "sha256": "664bbeb10522dac35c174a3860aaecad7b1ad3a0fc8b0d26888e26c824ec556d",
        "instance": {"wdth": 100},
    },
    {
        "out": "newsreader/Newsreader-Italic-latin.woff2",
        "repo": "productiontype/Newsreader",
        "commit": "cfcb4f7af0e52c25e8df2a2431814c8e5fe2e155",
        "path": "fonts/variable/ttf/Newsreader-Italic[opsz,wght].ttf",
        "sha256": "796668611f80b64d5adf182fde3b6f29ed83b4e7cbec7b96937e84ac01364792",
        "instance": {"opsz": 16, "wght": 400},
    },
    {
        "out": "JetBrainsMono-latin.woff2",
        "repo": "JetBrains/JetBrainsMono",
        "commit": "19371302b95d218af43299bce79ddbddd0bc364d",
        "path": "fonts/webfonts/JetBrainsMono[wght].woff2",
        "sha256": "31ec365b93e4bad6f202ce23352a56d01ca4462b2afc782ed2cf6fa42ca9ac0e",
        "instance": {"wght": (400, 700)},
    },
]


def format_unicodes(points: set[int]) -> str:
    """The set of code points as 'U+0000-00FF,U+2190'-style ranges."""
    ranges: list[list[int]] = []
    for point in sorted(points):
        if ranges and point == ranges[-1][1] + 1:
            ranges[-1][1] = point
        else:
            ranges.append([point, point])
    return ",".join(f"U+{a:04X}" if a == b else f"U+{a:04X}-{b:04X}" for a, b in ranges)


def cut(unicodes: str) -> dict[str, str]:
    """Write each output font; return {output: sha256}."""
    import brotli
    import fontTools
    from fontTools import subset
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    if (fontTools.version, brotli.__version__) != (FONTTOOLS, BROTLI):
        raise SystemExit(f"needs fonttools=={FONTTOOLS} and brotli=={BROTLI}, found "
                         f"{fontTools.version} and {brotli.__version__}")
    options = subset.Options(flavor="woff2", hinting=False)
    options.layout_features += ["pnum", "tnum"]
    files = {}
    with tempfile.TemporaryDirectory() as tmp:
        for font_spec in FONTS:
            url = (f"https://raw.githubusercontent.com/{font_spec['repo']}/{font_spec['commit']}/"
                   f"{urllib.parse.quote(font_spec['path'])}")
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read()
            if hashlib.sha256(data).hexdigest() != font_spec["sha256"]:
                raise SystemExit(f"{url} does not match its pinned SHA-256")
            source = Path(tmp) / Path(font_spec["path"]).name
            source.write_bytes(data)
            font = TTFont(source, recalcTimestamp=False)
            if font_spec["instance"]:
                instancer.instantiateVariableFont(font, font_spec["instance"], inplace=True)
                # Reload: a partial instance's glyph variations are otherwise
                # left incomplete, and the subsetter fails on them.
                font.save(source)
                font = TTFont(source, recalcTimestamp=False)
            subsetter = subset.Subsetter(options)
            subsetter.populate(unicodes=parse_unicodes(unicodes))
            subsetter.subset(font)
            out = FONTS_DIR / font_spec["out"]
            subset.save_font(font, out, options)
            files[font_spec["out"]] = hashlib.sha256(out.read_bytes()).hexdigest()
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from-site", metavar="URL", help="rescan this running site build for the characters to keep")
    args = parser.parse_args()

    if args.from_site:
        used = site_characters(args.from_site.rstrip("/"))
        unicodes = format_unicodes(parse_unicodes(LATIN) | {ord(char) for char in used})
    else:
        unicodes = json.loads(MANIFEST.read_text())["unicodes"]
    files = cut(unicodes)
    manifest = {"generator": "scripts/build_site_fonts.py", "fonttools": FONTTOOLS, "brotli": BROTLI,
                "unicodes": unicodes, "files": files}
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    for name, digest in files.items():
        print(f"{digest}  {name}  {(FONTS_DIR / name).stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
