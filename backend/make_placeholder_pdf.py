import sys
from pathlib import Path


def build(title: str) -> str:
    lines = [title, "Placeholder file - replace with the final product PDF.", "NOVA DIGITAL"]
    content = "BT /F1 22 Tf 72 720 Td (%s) Tj 0 -40 Td /F1 12 Tf (%s) Tj 0 -24 Td (%s) Tj ET" % tuple(lines)
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        "<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content),
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = "%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += "%d 0 obj\n%s\nendobj\n" % (i, o)
    xref = len(out)
    out += "xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += "".join("%010d 00000 n \n" % off for off in offsets)
    out += "trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return out


if __name__ == "__main__":
    folder = Path(__file__).parent / "files"
    folder.mkdir(exist_ok=True)
    for slug in sys.argv[1:]:
        path = folder / f"{slug}.pdf"
        if not path.exists():
            path.write_text(build(slug.replace("-", " ").upper()), encoding="latin-1")
            print("written", path)
