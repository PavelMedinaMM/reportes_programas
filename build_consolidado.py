#!/usr/bin/env python3
"""Reporte consolidado de programas Canal 6.

Un consolidado por día hábil (Consolidado/Consolidado_Programas_<AAAA-MM-DD>.pdf) con:
  - los programas diarios que tienen reporte de ese mismo día (si no lo tienen, no se incluyen),
  - los programas de fin de semana con su emisión del sáb/dom de la misma semana (lunes a
    domingo); si aún no existe, la del fin de semana anterior; si tampoco, no se incluyen.
Arma un solo PDF con:
  - portada,
  - índice con share de franja y lugar por plaza (cada fila es un enlace al programa),
  - los reportes completos, con marcadores (programa > página) y un enlace de
    regreso al índice en la franja superior de cada página.

Uso:  python3 build_consolidado.py --elaborado <HOY>      todos los días desde DESDE; solo
                                                         regenera los que cambiaron (manifest.json)
      python3 build_consolidado.py --fecha 2026-11-19 --force
Solo lee los PDF de la carpeta; no consulta datos ni modifica los reportes.
"""
import argparse, datetime as dt, glob, io, os, re, sys

import pypdf
from pypdf.annotations import Link
from pypdf.generic import Fit
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, "Consolidado")

# Orden de la parrilla (subcarpeta, nombre corto en el índice)
PROGRAMAS = [
    ("Telediario_Matutino", "TDM"),
    ("Vivalavi", "VLV"),
    ("Telediario_Vespertino", "TDV"),
    ("Tocando_al_Corazon", "TAC"),
    ("C4_en_Alerta", "C4"),
    ("Telediario_Nocturno", "TDN"),
    ("Cuando_los_Angeles_Caen", "CLAC"),
    ("Rumbo_al_Campeonato", "RAC"),
]
PLAZAS = ["CDMX", "Monterrey", "Guadalajara"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

DRIVE_URL = "https://drive.google.com/drive/folders/1qgFsuxKbj7mmx99L0nS-kKLXwDvHUQ1i?usp=sharing"

RED = HexColor("#D7262B"); INK = HexColor("#1E1E1E"); GREY = HexColor("#6B6B6B")
LINE = HexColor("#BDBDBD"); BG = HexColor("#F2F2F2"); ROWALT = HexColor("#E9E9E9")

FONT_DIRS = ["/usr/share/fonts/truetype/crosextra", "/usr/share/fonts/truetype/carlito",
             os.path.expanduser("~/.fonts"), os.path.expanduser("~/.local/share/fonts")]


def register_fonts():
    for d in FONT_DIRS:
        r, b = os.path.join(d, "Carlito-Regular.ttf"), os.path.join(d, "Carlito-Bold.ttf")
        if os.path.exists(r) and os.path.exists(b):
            pdfmetrics.registerFont(TTFont("F", r)); pdfmetrics.registerFont(TTFont("FB", b))
            return "F", "FB"
    return "Helvetica", "Helvetica-Bold"


def fecha_larga(d):
    return f"{DIAS[d.weekday()].capitalize()} {d.day} de {MESES[d.month-1]} de {d.year}"


def fecha_corta(d):
    return f"{DIAS[d.weekday()][:3]} {d.day} {MESES[d.month-1][:3]}"


def page_title(text):
    """Título de una página interna: la línea que sigue al encabezado '… · CANAL 6 …'."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for i, l in enumerate(lines[:-1]):
        if "· CANAL 6" in l and l.upper() == l:
            t = lines[i + 1]
            return t if len(t) <= 80 else t[:77] + "…"
    return None


def parse_report(path):
    r = pypdf.PdfReader(path)
    cover = [l.strip() for l in r.pages[0].extract_text().split("\n") if l.strip()]
    nombre = cover[1] if len(cover) > 1 else os.path.basename(path)
    sub = cover[2] if len(cover) > 2 else ""
    m = re.search(r"(\d{4}-\d{2}-\d{2})\.pdf$", path)
    fecha = dt.date.fromisoformat(m.group(1))
    resumen = r.pages[1].extract_text() if len(r.pages) > 1 else ""
    plazas = {}
    for p in PLAZAS:
        mm = re.search(rf"^{p}\n([\d.]+%)\n(\d+)\.° lugar", resumen, re.M)
        if mm:
            plazas[p] = (mm.group(1), mm.group(2) + ".°")
    nota = None
    if not plazas:  # formato semanal (Rumbo al Campeonato, solo CDMX)
        mm = re.search(r"(\w+) \((\d+) domingos?\): ([\d.]+%), (\d+)\.° lugar", resumen)
        if mm:
            plazas["CDMX"] = (mm.group(3), mm.group(4) + ".°")
            nota = f"{mm.group(1)} ({mm.group(2)} dom.)"
    titles = [page_title(pg.extract_text() or "") for pg in r.pages]
    return dict(path=path, nombre=nombre, sub=sub, fecha=fecha, plazas=plazas,
                nota=nota, n=len(r.pages), titles=titles)


def draw_frame(c, W, H, F, FB, elaborado, label):
    c.setFillColor(BG); c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setFillColor(RED); c.rect(0, 0, 11, H, stroke=0, fill=1)
    c.setFillColor(RED); c.setFont(FB, 10); c.drawString(38, H - 34, label)
    c.setStrokeColor(LINE); c.setLineWidth(0.8); c.line(38, 54, W - 38, 54)
    c.setFillColor(GREY); c.setFont(F, 8)
    c.drawString(38, 40, "Documento de uso interno · Multimedios · Información confidencial")
    c.drawRightString(W - 38, 40, f"Elaborado el {elaborado.day} de {MESES[elaborado.month-1]} de {elaborado.year}")


def boton_drive(c, x, y, w, h, F, FB, titulo, accion):
    """Botón rojo con enlace a la carpeta de Drive de reportes individuales."""
    c.setFillColor(RED); c.roundRect(x, y, w, h, 6, stroke=0, fill=1)
    c.setFillColor(HexColor("#FFFFFF"))
    if titulo:
        c.setFont(F, 9); c.drawString(x + 14, y + h - 17, titulo)
        c.setFont(FB, 13); c.drawString(x + 14, y + 11, accion)
    else:
        c.setFont(FB, 10); c.drawCentredString(x + w / 2, y + (h - 7) / 2, accion)
    return (x, y, x + w, y + h)


def pie_drive(W, H, F, FB):
    """Overlay de una página: franja inferior con el enlace a Drive. Devuelve (pdf, rect)."""
    buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=(W, H))
    txt1 = "¿Solo te interesa un programa? Reportes individuales en Drive: "
    txt2 = "Clic aquí"
    w1 = pdfmetrics.stringWidth(txt1, F, 7.5); w2 = pdfmetrics.stringWidth(txt2, FB, 7.5)
    x1 = W - 40 - w1 - w2
    c.setFillColor(GREY); c.setFont(F, 7.5); c.drawString(x1, 4.5, txt1)
    c.setFillColor(RED); c.setFont(FB, 7.5); c.drawString(x1 + w1, 4.5, txt2)
    c.setStrokeColor(RED); c.setLineWidth(0.5); c.line(x1 + w1, 3.5, x1 + w1 + w2, 3.5)
    c.showPage(); c.save()
    return buf.getvalue(), (x1 - 2, 1, W - 38, 13)


def build_front(reps, W, H, elaborado, F, FB, first_pages, dia, omitidos):
    buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=(W, H))
    corte = dia

    # ---- Portada
    c.setFillColor(BG); c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setFillColor(RED); c.rect(0, 0, 11, H, stroke=0, fill=1)
    c.setFillColor(RED); c.setFont(FB, 10)
    c.drawString(58, H - 72, "CANAL 6 · MULTIMEDIOS · ANÁLISIS DE DESEMPEÑO")
    c.setFillColor(INK); c.setFont(FB, 40); c.drawString(58, H - 128, "Reporte consolidado de programas")
    c.setFillColor(GREY); c.setFont(F, 13)
    c.drawString(58, H - 156, f"{len(reps)} programa{'s' if len(reps) != 1 else ''} · CDMX · Monterrey · Guadalajara · Fuente: HR Media")
    c.setStrokeColor(INK); c.setLineWidth(1); c.line(58, H - 190, W - 58, H - 190)
    y = H - 222
    c.setFillColor(RED); c.setFont(FB, 9); c.drawString(58, y, "CORTE")
    c.setFillColor(INK); c.setFont(FB, 16); c.drawString(58, y - 22, fecha_larga(corte))
    c.setFillColor(GREY); c.setFont(F, 9)
    c.drawString(58, y - 38, "Reportes de este día; programas de fin de semana: última emisión vigente.")
    c.setFillColor(RED); c.setFont(FB, 9); c.drawString(58, y - 80, "ELABORÓ")
    c.setFillColor(INK); c.setFont(FB, 16); c.drawString(58, y - 102, "Pavel Medina")
    c.setFillColor(GREY); c.setFont(F, 10); c.drawString(58, y - 118, "Dirección Data Analytics · Multimedios")
    c.setFillColor(RED); c.setFont(FB, 10); c.drawString(58, y - 132, "pavel.medina@multimedios.com")
    x2 = 452
    c.setFillColor(RED); c.setFont(FB, 9); c.drawString(x2, y, "CÓMO USAR ESTE DOCUMENTO")
    notas = [
        ("Índice", "En la página 2. Cada fila lleva a la portada del programa."),
        ("Regresar", "Haz clic en el encabezado rojo de cualquier página para volver al índice."),
        ("Marcadores", "Panel lateral del lector: programa > página."),
        ("Contenido", "Cada sección es el reporte completo, sin cambios, tal como lo genera"),
        ("", "su tarea programada (diario L–V; Rumbo al Campeonato, semanal)."),
        ("Individuales", "Cada programa por separado está en Drive (botón de abajo y pie de página)."),
    ]
    yy = y - 24
    for k, v in notas:
        c.setFillColor(INK); c.setFont(FB, 9); c.drawString(x2, yy, k)
        c.setFont(F, 9); c.drawString(x2 + 80, yy, v); yy -= 17
    links = [boton_drive(c, x2, yy - 52, 330, 48, F, FB, "¿Solo te interesa un programa? Consulta los reportes individuales",
                         "Clic aquí para abrirlos en Drive  →")]
    c.setStrokeColor(LINE); c.setLineWidth(0.8); c.line(58, 54, W - 58, 54)
    c.setFillColor(GREY); c.setFont(F, 8)
    c.drawString(58, 40, "Documento de uso interno · Multimedios · Información confidencial")
    c.drawRightString(W - 58, 40, f"Elaborado el {elaborado.day} de {MESES[elaborado.month-1]} de {elaborado.year}")
    c.showPage()

    # ---- Índice
    draw_frame(c, W, H, F, FB, elaborado, f"REPORTE CONSOLIDADO · CANAL 6 · CORTE AL {corte.day} {MESES[corte.month-1][:3].upper()} {corte.year}")
    c.setFillColor(INK); c.setFont(FB, 24); c.drawString(38, H - 66, "Índice")
    c.setFillColor(GREY); c.setFont(F, 9)
    c.drawString(130, H - 62, "Share de franja del mes en curso · lugar por rating · haz clic en un programa para ir a su reporte")
    links.append(boton_drive(c, W - 38 - 250, H - 72, 250, 26, F, FB, None, "Reportes individuales en Drive · Clic aquí  →"))
    c.setStrokeColor(INK); c.setLineWidth(1); c.line(38, H - 80, W - 38, H - 80)

    cols = {"n": 38, "prog": 66, "dato": 446, "CDMX": 560, "Monterrey": 660, "Guadalajara": 770, "pag": W - 38}
    yh = H - 98
    c.setFillColor(GREY); c.setFont(FB, 8)
    c.drawString(cols["prog"], yh, "PROGRAMA"); c.drawString(cols["dato"], yh, "ÚLTIMO DATO")
    for p in PLAZAS:
        c.drawRightString(cols[p] + 70, yh, p.upper())
    c.drawRightString(cols["pag"], yh, "PÁG.")
    row_h = 43; y0 = yh - 10
    rects = []
    for i, r in enumerate(reps):
        top = y0 - i * row_h; bot = top - row_h
        if i % 2 == 0:
            c.setFillColor(ROWALT); c.rect(38, bot, W - 76, row_h, stroke=0, fill=1)
        c.setFillColor(RED); c.setFont(FB, 16); c.drawString(cols["n"] + 4, bot + 15, f"{i+1:02d}")
        c.setFillColor(INK); c.setFont(FB, 13); c.drawString(cols["prog"] + 8, bot + 23, r["nombre"])
        c.setFillColor(GREY); c.setFont(F, 8)
        sub = re.sub(r"\s+·\s+En la franja desde.*$", "", r["sub"]).replace("  ", " ")
        if len(sub) > 82: sub = sub[:80] + "…"
        c.drawString(cols["prog"] + 8, bot + 10, sub)
        c.setFillColor(INK); c.setFont(FB, 10); c.drawString(cols["dato"], bot + 23, fecha_corta(r["fecha"]))
        c.setFillColor(GREY); c.setFont(F, 8)
        c.drawString(cols["dato"], bot + 10, r["nota"] or ("semanal" if "Domingo" in r["sub"] else "mes en curso"))
        for p in PLAZAS:
            v = r["plazas"].get(p)
            if v:
                c.setFillColor(INK); c.setFont(FB, 13); c.drawRightString(cols[p] + 70, bot + 22, v[0])
                c.setFillColor(GREY); c.setFont(F, 8); c.drawRightString(cols[p] + 70, bot + 10, f"{v[1]} lugar")
            else:
                c.setFillColor(LINE); c.setFont(F, 12); c.drawRightString(cols[p] + 70, bot + 20, "—")
        c.setFillColor(RED); c.setFont(FB, 12); c.drawRightString(cols["pag"] - 4, bot + 16, str(first_pages[i] + 1))
        rects.append((38, bot, W - 38, top))
    c.setStrokeColor(LINE); c.setLineWidth(0.6); c.line(38, y0 - len(reps) * row_h, W - 38, y0 - len(reps) * row_h)
    c.setFillColor(GREY); c.setFont(F, 8)
    c.drawString(38, 64, "Fuente: HR Media. Share = % sobre TV abierta en los minutos del programa. Rumbo al Campeonato: solo CDMX, share del mes en curso (domingos). "
                 "— = la plaza no aplica al programa.")
    if omitidos:
        c.setFillColor(RED); c.setFont(FB, 8)
        c.drawString(38, 76, "Sin reporte para este día (no incluidos): " + ", ".join(omitidos) + ".")
    c.showPage(); c.save()
    return buf.getvalue(), rects, corte, links


DESDE = dt.date(2026, 11, 1)  # primer día con consolidado
MANIFEST = os.path.join(OUT_DIR, "manifest.json")


def sha256(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def inventario():
    """{carpeta: {fecha: ruta}} en orden de parrilla; programas nuevos al final."""
    known = [d for d, _ in PROGRAMAS]
    extra = sorted(d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d))
                   and d not in known and not d.startswith(".") and d != "Consolidado")
    inv = {}
    for d in known + extra:
        fechas = {}
        for f in glob.glob(os.path.join(ROOT, d, "*_Desempeno_*.pdf")):
            m = re.search(r"(\d{4}-\d{2}-\d{2})\.pdf$", f)
            if m:
                fechas[dt.date.fromisoformat(m.group(1))] = f
        if fechas:
            inv[d] = fechas
    return inv


def es_fin_de_semana(fechas):
    return sum(f.weekday() >= 5 for f in fechas) > len(fechas) / 2


def seleccion(inv, dia):
    """Reportes que entran al consolidado de `dia` y programas omitidos.
    Diarios: solo si tienen reporte de ese mismo día.
    Fin de semana (semana de lunes a domingo): su emisión del sáb/dom de la misma semana de `dia`;
    si aún no existe, la del fin de semana anterior; si tampoco existe, se omite."""
    domingo = dia + dt.timedelta(days=6 - dia.weekday())
    misma = {domingo, domingo - dt.timedelta(days=1)}
    anterior = {f - dt.timedelta(days=7) for f in misma}
    incl, omit = [], []
    for d, fechas in inv.items():
        if es_fin_de_semana(fechas):
            ok = sorted(f for f in fechas if f in misma) or sorted(f for f in fechas if f in anterior)
            (incl.append(fechas[ok[-1]]) if ok else omit.append(d))
        else:
            (incl.append(fechas[dia]) if dia in fechas else omit.append(d))
    return incl, omit


def nombre_programa(carpeta, inv):
    try:
        cov = pypdf.PdfReader(sorted(inv[carpeta].values())[-1]).pages[0].extract_text().split("\n")
        return [l.strip() for l in cov if l.strip()][1]
    except Exception:
        return carpeta.replace("_", " ")


def build(paths, omitidos, dia, elaborado, out):
    F, FB = register_fonts()
    reps = [parse_report(p) for p in paths]
    W, H = (float(x) for x in pypdf.PdfReader(reps[0]["path"]).pages[0].mediabox[2:4])
    FRONT = 2
    first_pages, p = [], FRONT
    for r in reps:
        first_pages.append(p); p += r["n"]
    front_pdf, rects, _, links = build_front(reps, W, H, elaborado, F, FB, first_pages, dia, omitidos)

    w = pypdf.PdfWriter()
    for pg in pypdf.PdfReader(io.BytesIO(front_pdf)).pages:
        w.add_page(pg)
    for r in reps:
        for pg in pypdf.PdfReader(r["path"]).pages:
            w.add_page(pg)
    w.add_outline_item("Portada", 0, fit=Fit.fit())
    w.add_outline_item("Índice", 1, fit=Fit.fit())
    for r, fp in zip(reps, first_pages):
        parent = w.add_outline_item(f"{r['nombre']} · {fecha_corta(r['fecha'])}", fp, fit=Fit.fit())
        for j, t in enumerate(r["titles"]):
            w.add_outline_item(t or ("Portada" if j == 0 else f"Página {j+1}"), fp + j, parent=parent, fit=Fit.fit())
    for rect, fp in zip(rects, first_pages):
        w.add_annotation(page_number=1, annotation=Link(rect=rect, target_page_index=fp, fit=Fit.fit()))
    for pg_i, rect in zip((0, 1), links):
        w.add_annotation(page_number=pg_i, annotation=Link(rect=rect, url=DRIVE_URL))
    pies = {}
    for i in range(len(w.pages)):
        pw, ph = (float(x) for x in w.pages[i].mediabox[2:4])
        if (pw, ph) not in pies:
            pies[(pw, ph)] = pie_drive(pw, ph, F, FB)
        pie, prect = pies[(pw, ph)]
        if i >= FRONT:
            w.pages[i].merge_page(pypdf.PdfReader(io.BytesIO(pie)).pages[0])
            w.add_annotation(page_number=i, annotation=Link(rect=(0, ph - 46, pw, ph), target_page_index=1, fit=Fit.fit()))
            w.add_annotation(page_number=i, annotation=Link(rect=prect, url=DRIVE_URL))
    w.add_metadata({"/Title": f"Reporte consolidado de programas Canal 6 — {dia.isoformat()}",
                    "/Author": "Pavel Medina · Dirección Data Analytics · Multimedios"})
    w.page_mode = "/UseOutlines"
    with open(out, "wb") as f:
        w.write(f)
    return reps, first_pages, len(w.pages)


def main():
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument("--elaborado", default=dt.date.today().isoformat())
    ap.add_argument("--fecha", help="solo este día (AAAA-MM-DD)")
    ap.add_argument("--desde", default=DESDE.isoformat())
    ap.add_argument("--force", action="store_true", help="regenerar aunque no haya cambios")
    a = ap.parse_args()
    elaborado = dt.date.fromisoformat(a.elaborado)
    inv = inventario()
    diarios = sorted({f for d, fs in inv.items() if not es_fin_de_semana(fs) for f in fs})
    dias = [dt.date.fromisoformat(a.fecha)] if a.fecha else \
        [f for f in diarios if f >= dt.date.fromisoformat(a.desde) and f.weekday() < 5]
    os.makedirs(OUT_DIR, exist_ok=True)
    man = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
    nombres = {d: nombre_programa(d, inv) for d in inv}
    gen = 0
    for dia in dias:
        paths, omit = seleccion(inv, dia)
        if not any(not es_fin_de_semana(inv[os.path.basename(os.path.dirname(p))]) for p in paths):
            print(f"{dia}: sin reportes diarios, no se genera"); continue
        firma = {os.path.relpath(p, ROOT): sha256(p) for p in paths}
        out = os.path.join(OUT_DIR, f"Consolidado_Programas_{dia.isoformat()}.pdf")
        prev = man.get(dia.isoformat(), {}).get("entradas")
        if not a.force and prev == firma and os.path.exists(out):
            continue
        omit_n = [nombres[d] for d in omit]
        reps, fps, n = build(paths, omit_n, dia, elaborado, out)
        man[dia.isoformat()] = {"archivo": os.path.relpath(out, ROOT), "entradas": firma,
                                "omitidos": omit_n, "paginas": n, "elaborado": elaborado.isoformat()}
        gen += 1
        print(f"{dia}: {os.path.relpath(out, ROOT)} ({n} págs., {len(reps)} programas)"
              + (f" · omitidos: {', '.join(omit_n)}" if omit_n else ""))
    with open(MANIFEST, "w") as f:
        json.dump(dict(sorted(man.items())), f, ensure_ascii=False, indent=1)
    print(f"generados/actualizados: {gen}")


if __name__ == "__main__":
    main()
