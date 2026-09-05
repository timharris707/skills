import urllib.request, re, base64, sys

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

FAMILIES = {
    "Poppins": "https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap",
    "Lora":    "https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;1,400&display=swap",
}

def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read() if binary else r.read().decode("utf-8")

BLOCK = re.compile(r"@font-face\s*\{([^}]*)\}", re.S)
def field(body, name):
    m = re.search(rf"{name}:\s*([^;]+);", body)
    return m.group(1).strip() if m else ""

out = []
total = 0
for fam, css_url in FAMILIES.items():
    css = get(css_url)
    for body in BLOCK.findall(css):
        urange = field(body, "unicode-range")
        if "U+0000-00FF" not in urange:        # keep latin subset only
            continue
        style = field(body, "font-style") or "normal"
        weight = field(body, "font-weight") or "400"
        src = re.search(r"url\((https://[^)]+\.woff2)\)", body).group(1)
        data = get(src, binary=True)
        total += len(data)
        b64 = base64.b64encode(data).decode("ascii")
        out.append(
            "@font-face {\n"
            f"  font-family: '{fam}';\n"
            f"  font-style: {style};\n"
            f"  font-weight: {weight};\n"
            "  font-display: swap;\n"
            f"  src: url(data:font/woff2;base64,{b64}) format('woff2');\n"
            "}\n"
        )
        print(f"  {fam:8} {style:7} {weight}  woff2={len(data)//1024}KB  b64={len(b64)//1024}KB", file=sys.stderr)

dest = "skills/advisory-board/references/plan-fonts.css"
header = ("/* Self-contained Claude brand fonts for the plan view — generated, do not hand-edit.\n"
          "   Poppins (headings/labels) + Lora (body), latin subset, OFL-licensed, base64-embedded.\n"
          "   Regenerate with scripts/_embed_fonts.py. */\n")
with open(dest, "w", encoding="utf-8") as f:
    f.write(header + "\n".join(out))

import os
print(f"\nwrote {dest}  ({os.path.getsize(dest)//1024}KB total, {len(out)} faces, raw woff2 {total//1024}KB)", file=sys.stderr)
