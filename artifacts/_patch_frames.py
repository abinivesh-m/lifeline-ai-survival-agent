from pathlib import Path
p = Path("make_frames.py")
lines = p.read_text(encoding="utf-8").splitlines()
i = lines.index("    y = 782")
lines[i] = "    y = 776"
lines[i + 1] = "        f.text((M + 28, y), f\"{item['litres']:>3d} L\", font=F_MONO_B, 17, AMBER)"
lines[i + 2] = "        claim = f.wrap(item[\"claim\"], font=F_REG, 470)[0]"
lines[i + 3] = "        f.text((M + 106, y), claim, font=F_REG, 16, TEXT)"
lines[i + 4] = "        f.text((M + 676, y), \",\".join(item[\"because\"]), font=F_MONO, 14, MUTED, anchor=\"ra\")"
lines[i + 5] = "        y += 32"
p.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("patched at", i)
