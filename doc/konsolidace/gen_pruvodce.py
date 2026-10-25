# -*- coding: utf-8 -*-
"""
Generátor průvodce konsolidovanou databází pro externí spolupracovníky.

Řídí se pravidly v ../TEXT_STYLE.md:
  - vestavěné styly Wordu (Title, Heading 1/2, List Number, List Bullet);
    barva/velikost nadpisů i písmo stylu Název mají explicitní override
    odpovídající základnímu dokumentu — viz TEXT_STYLE.md §3.3;
  - výchozí motiv přepnut na Aptos / Aptos Display (Název navíc na přímé
    Aptos ExtraBold, mimo motiv — viz §3.3);
  - nadpisy 1. úrovně nesou VIDITELNÉ číslo přes SEQ pole obalené záložkou
    (ne skryté, ne ruční číslice) — proto na ně lze odkazovat REF polem
    z libovolného místa v dokumentu (TEXT_STYLE.md §3.4 a §3.7); nadpisy
    2. úrovně dostávají dopočtené „N.M“ jako prostý text, protože se na
    ně nikde neodkazuje;
  - obrázky a tabulky jsou očíslovány přes SEQ pole (Obrazek/Tabulka);
  - veškeré odkazy na kapitoly/obrázky/tabulky v textu jsou REF pole
    tvaru „REF _zalozka_ \\# 0 \\h“, ne ručně vepsaná čísla
    (TEXT_STYLE.md §3.7–3.8);
  - jazyk cs-CZ nastaven na každém běhu textu i v docDefaults (§3.9);
  - identifikátory kódu neproporcionálně (Aptos Mono);
  - text v autorském plurálu, formální styl (viz TEXT_STYLE.md).

Text vychází z autorem schválené verze (Konsolidace-DB-pruvodce.docx).
Výstup jde do *_v02.docx, aby nedošlo k přepsání ruční verze.
"""
import os, re, zipfile
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BASE = r"C:\Users\janpr\OneDrive - Západočeská univerzita v Plzni\NAHYC\DP004 - Vodíkový technologický inkubátor\Pracovní\Architektura databáze\Databáze.Konsolidovaná"
IMG = os.path.join(BASE, "obrazky")
OUT = os.path.join(BASE, "Konsolidace-DB-pruvodce_v02.docx")
MONO = "Aptos Mono"

# ════════════════════════════════════════════════════════════
# Předem daná mapa záložek pro křížové odkazy (viz TEXT_STYLE.md §3.8).
# Klíč → (název záložky, „cache“ číslo zobrazené před přepočtem polí ve
# Wordu). Čísla odpovídají pořadí, ve kterém se dané kapitoly/obrázky/
# tabulky v dokumentu skutečně objevují.
# ════════════════════════════════════════════════════════════
CH_BOOKMARKS = {
    "ucel":     ("_RefKapUcel", 1),
    "kontext":  ("_RefKapKontext", 2),
    "vychozi":  ("_RefKapVychozi", 3),
    "vrstva_a": ("_RefKapVrstvaA", 4),
    "vrstva_b": ("_RefKapVrstvaB", 5),
    "vrstva_c": ("_RefKapVrstvaC", 6),
    "vrstva_d": ("_RefKapVrstvaD", 7),
    "pathway":  ("_RefKapPathway", 8),
    "zasady":   ("_RefKapZasady", 9),
    "kde":      ("_RefKapKde", 10),
    "slovnik":  ("_RefKapSlovnik", 11),
}
FIG_BOOKMARKS = {
    "dve_casti": ("_RefObrDveCasti", 1),
    "vrstvy":    ("_RefObrVrstvy", 2),
    "v01":       ("_RefObrV01", 3),
    "sit":       ("_RefObrSit", 4),
    "uzel":      ("_RefObrUzel", 5),
    "pathway":   ("_RefObrPathway", 6),
}
TAB_BOOKMARKS = {
    "vrstva_a": ("_RefTabVrstvaA", 1),
    "uzly":     ("_RefTabUzly", 2),
    "vazba":    ("_RefTabVazba", 3),
    "hlediska": ("_RefTabHlediska", 4),
    "stav":     ("_RefTabStav", 5),
    "soubory":  ("_RefTabSoubory", 6),
    "slovnik":  ("_RefTabSlovnik", 7),
}

class Ref:
    """Křížový odkaz — v textu se vykreslí jako REF pole na danou záložku."""
    __slots__ = ("bookmark", "cached")
    def __init__(self, bookmark, cached):
        self.bookmark = bookmark
        self.cached = str(cached)

def chref(key):
    name, num = CH_BOOKMARKS[key]
    return Ref(name, num)

def figref(key):
    name, num = FIG_BOOKMARKS[key]
    return Ref(name, num)

def tabref(key):
    name, num = TAB_BOOKMARKS[key]
    return Ref(name, num)

doc = Document()

# ── Stránka A4, okraje 2,5 cm ──
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.5)
sec.top_margin = sec.bottom_margin = Cm(2.5)

# ── Override vestavěných stylů nadpisů (viz TEXT_STYLE.md §3.3) ──
# Úprava na úrovni STYLU, ne jednotlivých runů: tmavší navy (17365D) a větší
# velikosti, přesně dle základního dokumentu Konsolidace-DB-pruvodce.docx.
NAVY = RGBColor(0x17, 0x36, 0x5D)
for _sid, _pt in (("Title", 26), ("Heading 1", 16), ("Heading 2", 14)):
    _st = doc.styles[_sid]
    _st.font.color.rgb = NAVY
    _st.font.size = Pt(_pt)

# Styl Název (Title) používá v základním dokumentu jiný font než nadpisy —
# přímé "Aptos ExtraBold" (ne motivové Aptos Display) — a jemné doladění
# (znakové rozpětí, kerning, barva se značkou motivu). Motivová substituce
# v postprocess() níže mění jen theme1.xml, takže bez tohoto kroku by Název
# zdědil stejný font jako nadpisy (Aptos Display) — proto explicitní override.
_title_style = doc.styles["Title"]
_title_style.font.name = "Aptos ExtraBold"
_title_rpr = _title_style.element.get_or_add_rPr()
# Pozn.: výchozí šablona python-docx už má u stylu Título (Title) nastaveno
# character spacing=5 a kern=28 (standardní hodnoty MS Office stylu Název) —
# NEpřidávat je znovu, jen by vznikl duplicitní element. Doplňujeme pouze
# metadata theme barvy a szCs, které výchozí šablona nemá.
_title_color = _title_rpr.find(qn("w:color"))
if _title_color is not None:
    _title_color.set(qn("w:themeColor"), "text2")
    _title_color.set(qn("w:themeShade"), "BF")
_title_sz = _title_rpr.find(qn("w:sz"))
if _title_sz is not None and _title_rpr.find(qn("w:szCs")) is None:
    _title_szcs = OxmlElement("w:szCs")
    _title_szcs.set(qn("w:val"), _title_sz.get(qn("w:val")))
    _title_sz.addnext(_title_szcs)
_title_style.paragraph_format.space_after = Pt(15)
_title_style.paragraph_format.line_spacing = 1.0
_title_pPr = _title_style.element.get_or_add_pPr()
# Výchozí šablona dává Názvu spodní linku (pBdr) a contextualSpacing už má
# sama od sebe — základní dokument rámeček nemá, takže ho odstraníme;
# contextualSpacing naopak neduplikujeme.
_title_pBdr = _title_pPr.find(qn("w:pBdr"))
if _title_pBdr is not None:
    _title_pPr.remove(_title_pBdr)
if _title_pPr.find(qn("w:contextualSpacing")) is None:
    _title_pPr.find(qn("w:spacing")).addnext(OxmlElement("w:contextualSpacing"))

# ════════════════════════════════════════════════════════════
# Nízkoúrovňové stavební bloky pro pole (SEQ/REF) a záložky.
# Word field = posloupnost runů: begin → instrText → separate → cache → end.
# ════════════════════════════════════════════════════════════
_bookmark_id = [0]
def _next_bookmark_id():
    _bookmark_id[0] += 1
    return _bookmark_id[0]

def _new_run(hidden=False, italic=False, sz=None):
    r = OxmlElement("w:r")
    if hidden or italic or sz:
        rpr = OxmlElement("w:rPr")
        if hidden:
            rpr.append(OxmlElement("w:vanish"))
        if italic:
            rpr.append(OxmlElement("w:i"))
        if sz:
            sz_el = OxmlElement("w:sz")
            sz_el.set(qn("w:val"), str(sz))
            rpr.append(sz_el)
        r.append(rpr)
    return r

def _fldchar(kind):
    fc = OxmlElement("w:fldChar")
    fc.set(qn("w:fldCharType"), kind)
    return fc

def _instr_text(text):
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = text
    return it

def _run_text(text):
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    return t

def _field_runs(instr, cached_text, hidden=False, italic=False, sz=None):
    r1 = _new_run(hidden, italic, sz); r1.append(_fldchar("begin"))
    r2 = _new_run(hidden, italic, sz); r2.append(_instr_text(instr))
    r3 = _new_run(hidden, italic, sz); r3.append(_fldchar("separate"))
    r4 = _new_run(hidden, italic, sz); r4.append(_run_text(cached_text))
    r5 = _new_run(hidden, italic, sz); r5.append(_fldchar("end"))
    return [r1, r2, r3, r4, r5]

def append_field(paragraph, instr, cached_text, hidden=False, italic=False, sz=None):
    """Připojí pole (bez záložky) na konec odstavce — použito pro REF na místě citace."""
    for el in _field_runs(instr, cached_text, hidden, italic, sz):
        paragraph._p.append(el)

def insert_bookmarked_field(paragraph, bookmark_name, instr, cached_text,
                             hidden=False, italic=False, sz=None, at_start=False):
    """Vloží pole obalené záložkou (bookmarkStart/End) — použito u SEQ na místě definice
    (v nadpisu, v popisku obrázku/tabulky), aby na něj šlo REF polem odkazovat."""
    bid = _next_bookmark_id()
    bs = OxmlElement("w:bookmarkStart")
    bs.set(qn("w:id"), str(bid))
    bs.set(qn("w:name"), bookmark_name)
    be = OxmlElement("w:bookmarkEnd")
    be.set(qn("w:id"), str(bid))
    elems = [bs] + _field_runs(instr, cached_text, hidden, italic, sz) + [be]
    p = paragraph._p
    if at_start:
        pPr = p.find(qn("w:pPr"))
        idx = 1 if pPr is not None else 0
        for i, el in enumerate(elems):
            p.insert(idx + i, el)
        return idx + len(elems)  # index, kam vložit případný další obsah (např. oddělovač)
    else:
        for el in elems:
            p.append(el)
        return None

# ── Pomocné funkce pro běžný text (vestavěné styly, žádné ruční formátování) ──
def add_runs(par, segments):
    """segments = seznam (content, fmt); content je buď text, nebo instance Ref."""
    for content, fmt in segments:
        if isinstance(content, Ref):
            append_field(par, " REF %s \\# 0 \\h " % content.bookmark, content.cached)
            continue
        r = par.add_run(content)
        if fmt == "b":
            r.bold = True
        elif fmt == "i":
            r.italic = True
        elif fmt == "mono":
            r.font.name = MONO
    return par

def p(segments, style=None, align=None):
    if isinstance(segments, str):
        segments = [(segments, "")]
    par = doc.add_paragraph(style=style)
    add_runs(par, segments)
    if align:
        par.alignment = align
    return par

_chapter_state = {"num": None}  # číslo aktuální kapitoly 1. úrovně, pro číslování podkapitol

def heading(text, level, ref_key=None):
    """Nadpis 1. úrovně nese VIDITELNÉ číslo — SEQ pole obalené záložkou, aby na ně
    šlo odkazovat REF polem (`\\# 0 \\h`) odjinud v dokumentu (viz TEXT_STYLE.md §3.7).
    Nadpis 2. úrovně dostává dopočtené číslo „N.M“ (M v rámci aktuální kapitoly);
    protože se v textu nikdy neodkazuje, jde o prostý text, ne o pole."""
    if level == 1:
        if not ref_key:
            raise ValueError("nadpis 1. úrovně musí mít ref_key")
        par = doc.add_heading(text, level=1)
        name, num = CH_BOOKMARKS[ref_key]
        idx = insert_bookmarked_field(par, name, " SEQ Kapitola \\* ARABIC ", str(num),
                                       at_start=True)
        sep = OxmlElement("w:r")
        t = OxmlElement("w:t")
        t.set(qn("xml:space"), "preserve")
        t.text = " "  # dělící mezera mezi číslem a textem nadpisu
        sep.append(t)
        par._p.insert(idx, sep)
        _chapter_state["num"] = num
        _chapter_state["sub"] = 0
        return par
    elif level == 2:
        _chapter_state["sub"] = _chapter_state.get("sub", 0) + 1
        prefix = "%s.%s " % (_chapter_state["num"], _chapter_state["sub"])
        return doc.add_heading(prefix + text, level=2)
    else:
        return doc.add_heading(text, level=level)

def bullet(segments):
    return p(segments, style="List Bullet")

def numbered(segments):
    return p(segments, style="List Number")

def picture(fname, width_cm, ref_key, description):
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.space_before = Pt(4)
    par.paragraph_format.space_after = Pt(2)
    par.add_run().add_picture(os.path.join(IMG, fname), width=Cm(width_cm))

    name, num = FIG_BOOKMARKS[ref_key]
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(12)
    r = cap.add_run("Obr. ")
    r.italic = True
    r.font.size = Pt(9.5)
    insert_bookmarked_field(cap, name, " SEQ Obrazek \\* ARABIC ", str(num),
                             italic=True, sz=19)
    r2 = cap.add_run(" — " + description)
    r2.italic = True
    r2.font.size = Pt(9.5)

def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)

def table(headers, rows, widths_cm, ref_key, caption_text, header_fill="DEEAF6"):
    name, num = TAB_BOOKMARKS[ref_key]
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_before = Pt(6)
    cap.paragraph_format.space_after = Pt(4)
    r = cap.add_run("Tabulka ")
    r.italic = True
    r.font.size = Pt(9.5)
    insert_bookmarked_field(cap, name, " SEQ Tabulka \\* ARABIC ", str(num),
                             italic=True, sz=19)
    r2 = cap.add_run(" — " + caption_text)
    r2.italic = True
    r2.font.size = Pt(9.5)

    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for j, (h, w) in enumerate(zip(headers, widths_cm)):
        c = t.rows[0].cells[j]
        c.width = Cm(w)
        run = c.paragraphs[0].add_run(h)
        run.bold = True
        shade(c, header_fill)
    for i, row in enumerate(rows, start=1):
        for j, (val, w) in enumerate(zip(row, widths_cm)):
            c = t.rows[i].cells[j]
            c.width = Cm(w)
            c.paragraphs[0].add_run(val)
    for row in t.rows:
        for c in row.cells:
            for par in c.paragraphs:
                par.paragraph_format.space_after = Pt(2)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t

def footer_pagenum():
    par = sec.footer.paragraphs[0]
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.add_run("Strana ")
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    par._p.append(fld)

footer_pagenum()

# ════════════════════════════════════════════════════════════
# TITULNÍ BLOK  (vestavěný styl Title, žádné ruční fonty)
# ════════════════════════════════════════════════════════════
p("NAHYC DP004 — Vodíkový technologický inkubátor", align=WD_ALIGN_PARAGRAPH.CENTER)
doc.add_paragraph("Konsolidovaná databáze regulačních předpisů a předrealizačních procesů",
                  style="Title")
p("Průvodce strukturou", align=WD_ALIGN_PARAGRAPH.CENTER)
p([("červenec 2026 · pracovní verze", "i")], align=WD_ALIGN_PARAGRAPH.CENTER)

# ════════════════════════════════════════════════════════════
heading("K čemu tento dokument slouží", 1, ref_key="ucel")
p([
    ("Tento průvodce je určen jako základní informace o návrhu a naplňování databázové "
     "architektury dílčího projektu DP004. Neočekává znalost projektových výstupů ani "
     "detailů SQL — jeho cílem je vysvětlit, co databáze eviduje, proč je rozdělena zrovna "
     "do čtyř vrstev a jak spolu jednotlivé komponenty a vrstvy souvisejí. Technické detaily "
     "(přesné definice tabulek, datové typy, migrační skripty) záměrně vynecháváme; ty jsou "
     "k dispozici v souborech uvedených v odstavci ", ""),
    (chref("kde"), ""),
    (".", ""),
])
p([
    ("Doporučený postup čtení: V odstavcích ", ""),
    (chref("kontext"), ""),
    (" a ", ""),
    (chref("vychozi"), ""),
    (" popisujeme výchozí situaci (odkud data pocházejí a proč je třeba databázi předělat), "
     "v odstavcích ", ""),
    (chref("vrstva_a"), ""),
    (" až ", ""),
    (chref("vrstva_d"), ""),
    (" procházíme již zmíněné čtyři vrstvy schématu databáze od nejjednodušší k "
     "nejzajímavější a v odstavci ", ""),
    (chref("pathway"), ""),
    (" ukazujeme na příkladu elektrolyzéru, co bude celek umět poskytnout po dokončení "
     "vývojových prací. V odstavci ", ""),
    (chref("zasady"), ""),
    (" dokumentujeme zásady návrhu konsolidované databáze a průběžně popisujeme aktuální "
     "stav prací. Dokument uzavírá seznam důležitých souborů a slovníček pojmů.", ""),
])

# ════════════════════════════════════════════════════════════
heading("Kontext", 1, ref_key="kontext")
p("Dílčí projekt DP004 „Nástroje a znalostní systém pro inkubaci vodíkových technologií“ "
  "(součást Národního centra vodíkové mobility, TAČR TN02000007) reaguje na praktický "
  "problém: kdo chce v ČR postavit elektrolyzér, vodíkovou plnicí stanici nebo sklad vodíku, "
  "musí se zorientovat v desítkách předpisů z různých právních oblastí a projít řadou "
  "povolovacích řízení, která nikde nejsou popsána jako celek. Jedním z cílů dílčího projektu "
  "je usnadnit tuto orientaci — k tomu vznikly v roce 2026 postupně tři na sebe navazující "
  "výsledky:")
bullet([("V01", "b"),
        (" — Veřejná webová databáze regulačních dokumentů (zákony, vyhlášky, unijní předpisy, "
         "technické normy, metodiky). Běží v produkci na adrese https://nahyc.fel.zcu.cz/h2db/ "
         "a eviduje metadata dokumentů, jejich verze a tematické třídění.", "")])
bullet([("V02", "b"),
        (" — Analytický text, ve kterém identifikujeme a popisujeme sedm klíčových povolovacích "
         "procesů (tzv. procesních uzlů U1 až U7), jimiž vodíkový projekt prochází od záměru po "
         "povolení. Součástí V02 je i návrh, jak tyto procesy uložit do databáze — ten ale zatím "
         "nebyl implementován.", "")])
bullet([
    ("V03", "b"),
    (" — Metodický dokument, jenž popisuje, jak V01 a V02 vznikly, a hlavně jak mají být "
     "propojeny: Požaduje strojově dotazovatelné vazby mezi procesy a předpisy a zavádí "
     "koncept „compliance pathway“ (viz odstavec ", ""),
    (chref("pathway"), ""),
    (").", ""),
])
p("Konsolidovaná databáze, kterou tento průvodce popisuje, je rozšířením původní databáze "
  "regulačních dokumentů. Výsledek V01 se sice oficiálně nazývá „Databáze regulačních předpisů "
  "a předrealizačních procesů“, ale díky nevhodně naplánovanému harmonogramu prací vznikal "
  "souběžně s výsledkem V02 a procesy v databázi dosud reprezentovány vhodným způsobem nejsou — "
  "plnohodnotný návrh reprezentace existuje jen jako text a prozatím nerealizovaný návrh "
  "v rámci V02.")

# ════════════════════════════════════════════════════════════
heading("Výchozí situace a cíl konsolidace", 1, ref_key="vychozi")
p("Dnes tedy existují dva oddělené světy. Na jedné straně máme běžící databázi norem, zákonů "
  "a nařízení souvisejících s vodíkovými instalacemi, na druhé straně pouze ideový návrh "
  "a textový popis reprezentace procesů předcházejících realizaci vodíkových instalací. Jediné, "
  "co tyto komponenty v tento okamžik spojuje, jsou klíčová slova: proces „stavební povolení“ "
  "najde související předpisy jen tak, že se v databázi vyhledají dokumenty se štítkem „stavební "
  "právo“. To pro spolehlivou práci nepostačuje — samotné klíčové slovo nám například neříká, "
  "zda je daný předpis pro proces závazný, okrajový, nebo jen tematicky příbuzný. Víme pouze, "
  "že tento předpis s procesem nějak souvisí.")
picture("img1-dve-casti.png", 15.5, "dve_casti",
        "Výchozí situace: dokumenty a procesy existují odděleně, spojuje je jen tematické "
        "štítkování.")
p("Cílem konsolidace, navrhované v tomto dokumentu, je vytvořit jediné schéma, které oba světy "
  "spojí a doplní to, co požaduje metodika V03. Výsledek si lze představit jako čtyři vrstvy "
  "postavené na sobě:")
picture("img2-vrstvy.png", 13.5, "vrstvy",
        "Čtyři vrstvy konsolidovaného schématu. Spodní dvě vrstvy přebírají existující práci "
        "(V01, návrh V02), horní dvě jsou nové.")
p([("Zásadní praktické omezení k diskusi: ", "b"),
   ("Nad vrstvou A běží produkční webová aplikace, kterou může používat veřejnost. Konsolidace "
    "by proto neměla z existující struktury nic odebrat ani přejmenovat — všechny změny jsou "
    "„aditivní“, tedy pouze přidávají nové sloupce a nové tabulky. Díky tomu bude moci aplikace "
    "běžet beze změny i v průběhu přestavby.", "")])

# ════════════════════════════════════════════════════════════
heading("Vrstva A — dokumenty (převzato z V01)", 1, ref_key="vrstva_a")
p("Základem zůstává osvědčený model databáze V01. Středem je entita DOKUMENT — jeden záznam "
  "pro každý zákon, vyhlášku, unijní nařízení, technickou normu, strategii nebo metodiku. "
  "Kolem dokumentu stojí čtyři pomocné entity:")
picture("img3-v01.png", 15.5, "v01", "Dokumentová vrstva: dokument a jeho čtyři satelity.")
p("Za pozornost stojí dvě věci. Zaprvé, databáze je „metadatová“ — neukládá plné texty "
  "předpisů (u technických norem to ani licenčně nejde), ale jejich popis, zařazení a odkaz "
  "na oficiální zdroj. Zadruhé, klíčová slova nejsou volné štítky: jde o řízený slovník, který "
  "spravuje autorský tým, aby nevznikala synonyma a překlepy.")
p("Konsolidace tuto vrstvu pouze drobně rozšiřuje:")
table(
    ["Co se přidává", "Kam", "Proč"],
    [
        ["Oficiální identifikátor předpisu (např. „č. 283/2021 Sb.“, „EN 17124:2022“)", "Dokument",
         "Jednoznačné rozpoznání předpisu při propojování s procesy a při deduplikaci."],
        ["Typ instituce a jurisdikce (ČR / EU / mezinárodní)", "Zdroj dokumentu",
         "Umožňuje filtrovat podle právní úrovně; jurisdikce je vlastností vydavatele, ne dokumentu."],
        ["Příznak „toto je aktuálně platná verze“", "Verze dokumentu",
         "Výchozí zobrazení aktuálního stavu bez procházení celé historie verzí."],
    ],
    [6.0, 3.2, 6.3],
    ref_key="vrstva_a",
    caption_text="Rozšíření dokumentové vrstvy (V01)",
)

# ════════════════════════════════════════════════════════════
heading("Vrstva B — procesy (podle návrhu V02)", 1, ref_key="vrstva_b")
heading("Sedm procesních uzlů", 2)
p("Jádrem procesní vrstvy je sedm „procesních uzlů“, definovaných v dokumentu V02. Uzel je "
  "ucelené povolovací či schvalovací řízení s jasným výstupem — například územní posouzení, "
  "EIA nebo stavební povolení. Analytici je v dokumentu V02 identifikovali jako páteř přípravy "
  "každého vodíkového projektu:")
table(
    ["Uzel", "Název", "Oč jde (zjednodušeně)"],
    [
        ["U1", "Územní kompatibilita záměru", "Smí takový záměr stát na zvoleném místě?"],
        ["U2", "Environmentální režim projektu", "Vyžaduje záměr posouzení vlivů (EIA), integrované povolení, vodoprávní souhlas?"],
        ["U3", "Stavební povolení", "Klasické stavební řízení včetně dokumentace a stanovisek."],
        ["U4", "Energeticko-provozní oprávnění", "Licence a oprávnění k výrobě/prodeji energie či paliva."],
        ["U5", "Bezpečnostní režim", "Požární ochrana, tlaková zařízení, prevence závažných havárií, ATEX."],
        ["U6", "Připojení k infrastruktuře", "Smlouvy a podmínky připojení k elektřině, plynu, vodě, komunikacím."],
        ["U7", "Certifikační schopnost dle RFNBO", "Připravenost prokázat „zelený“ původ vodíku podle pravidel EU."],
    ],
    [1.4, 5.1, 9.0],
    ref_key="uzly",
    caption_text="Přehled procesních uzlů U1–U7",
)
p("Uzly nejsou izolované — tvoří síť. Některé musí proběhnout před jinými (výstup jednoho je "
  "vstupem druhého), jiné běží souběžně nebo se vzájemně ovlivňují. Síť vazeb je v databázi "
  "uložena explicitně jako hrany grafu:")
picture("img5-sit.png", 16.0, "sit",
        "Procesní síť U1–U7. Plné šipky = přímá návaznost, obousměrné šipky = vzájemné "
        "ovlivňování, čárkované = nepřímý vliv.")
heading("Co všechno o uzlu evidujeme", 2)
p("Každý uzel je v dokumentu V02 popsán jednotnou šablonou o jedenácti bodech (účel, právní "
  "opora, spouštěcí podmínky, vstupy, průběh, subjekty, výstupy, vazby, variabilita, typické "
  "problémy, vazba na databázi). V databázi je tato šablona rozložena do skupiny tabulek — "
  "„satelitů“ kolem uzlu. Zásada zní: hlavní tabulka uzlu zůstává malá a strukturovaná, "
  "všechno ostatní se dohledává vazbou.")
picture("img4-uzel.png", 14.0, "uzel",
        "Procesní uzel a jeho satelity. Každý blok je samostatná tabulka (nebo dvojice "
        "tabulek) napojená na uzel.")
p("Dva satelity si zaslouží vysvětlení:")
bullet([("Větve průběhu. ", "b"),
        ("Některá řízení mají více možných průběhů. Například environmentální uzel U2 se může "
         "odehrát ve větvi „bez posouzení“, „zjišťovací řízení“, „plná EIA“ nebo „integrované "
         "povolení“ — podle povahy záměru. Každá větev má své kroky (krok 1, krok 2, …) a svůj "
         "výstupní dokument.", "")])
bullet([("Matice variability 4×7. ", "b"),
        ("Stejný proces dopadá různě na různé typy instalací. Matice kříží 7 uzlů prozatím se "
         "4 oblastmi (elektrolýza, skladování, čerpací stanice, vozidla) a u každé kombinace uvádí "
         "intenzitu (klíčový ●●● / významný ●●○ / okrajový ●○○) a slovní specifika. Např. územní "
         "posouzení U1 je klíčové pro elektrolyzér, ale okrajové pro samotná vozidla.", "")])
p("Novinkou oproti návrhu V02 je u uzlů dvojice datumů platnosti („platí od — platí do“). "
  "Kdyby zásadní legislativní reforma změnila samotnou strukturu procesů (jako kdysi nový "
  "stavební zákon), starý popis uzlu se neztratí — jen se uzavře jeho platnost a založí se "
  "nová verze.")

# ════════════════════════════════════════════════════════════
heading("Vrstva C — propojení procesů a dokumentů", 1, ref_key="vrstva_c")
p("Toto je patrně nejdůležitější místo celé konsolidace — přitom jde o jedinou tabulku. Vazba "
  "„uzel ↔ dokument“ v této tabulce říká: tento konkrétní předpis (řádek z vrstvy A) je "
  "relevantní pro tento konkrétní proces (uzel z vrstvy B). Každá vazba nese tři doplňující "
  "informace:")
table(
    ["Údaj vazby", "Význam"],
    [
        ["Typ vazby", "„Právní opora“ (předpis proces zakládá nebo reguluje) vs. „pramen“ "
         "(studie či analýza, o kterou se popis uzlu opírá)."],
        ["Primární opora (ano/ne)", "Odlišuje hlavní předpis řízení (např. stavební zákon pro "
         "U3) od předpisů doplňkových."],
        ["Poznámka k relevanci", "Volný text: proč a v čem je dokument pro uzel důležitý."],
    ],
    [4.0, 11.5],
    ref_key="vazba",
    caption_text="Atributy vazby uzel ↔ dokument",
)
p("Díky této tabulce lze klást dotazy oběma směry — a to je přesně požadavek metodiky V03:")
bullet("Od procesu k předpisům: „Chystám se na stavební povolení (U3) — které předpisy a normy "
       "se mne týkají a který je hlavní?“")
bullet("Od předpisu k procesům: „Novelizoval se energetický zákon — které procesy a scénáře "
       "jsou dotčeny a musíme je zkontrolovat?“")
p([("Poznámka pro čtenáře návrhu V02: ", "b"),
   ("Původní návrh, uvedený v dokumentu V02, počítal s vlastními „stínovými“ tabulkami předpisů "
    "a pramenů uvnitř procesní části (", ""),
   ("legal_document", "mono"), (", ", ""), ("source_reference", "mono"),
   (") — dávalo to smysl, dokud měly být V01 a V02 dvě oddělené databáze. Ve společném schématu "
    "by šlo o duplicitní evidenci téhož, proto ji rušíme a vazby vedou přímo na dokumenty "
    "vrstvy A.", "")])

# ════════════════════════════════════════════════════════════
heading("Vrstva D — scénáře, podmínky aktivace a klasifikace", 1, ref_key="vrstva_d")
p("Vrstvy A až C popisují, co existuje (předpisy, procesy, jejich vztah). Vrstva D přidává to, "
  "co z databáze dělá nástroj potřebný pro navazující znalostní systémy: Schopnost odpovědět na "
  "otázku konkrétního investora „co všechno se týká právě mého záměru?“. K tomu slouží tři "
  "stavební kameny — klasifikační hlediska, typové scénáře a podmínky aktivace.")
heading("Čtyři klasifikační hlediska", 2)
p("Metodika V03 třídí vodíkové projekty podle čtyř hledisek. V databázi má každé hledisko svůj "
  "číselník (pevný seznam hodnot):")
table(
    ["Hledisko", "Hodnoty", "Nač odpovídá"],
    [
        ["Funkce v hodnotovém řetězci", "výroba · distribuce a přeprava · skladování · využití",
         "Ve které fázi „života“ vodíku se projekt pohybuje?"],
        ["Typ technologického řešení", "elektrolyzér PEM/alkalický, tlakový zásobník, plnicí "
         "technologie, vozidlo FCEV… (otevřený seznam)",
         "Jaká zařízení projekt obsahuje? (Každé aktivuje jiné požadavky.)"],
        ["Míra integrace", "samostatná instalace · integrovaný systém · komplexní řešení · "
         "ostrovní řešení",
         "Jak moc je projekt provázán s okolím? (Integrace = souběh více režimů.)"],
        ["Aplikační oblast", "mobilita · energetika · průmysl · pilotní projekty",
         "Do kterého sektoru projekt míří? (Sektor přidává vlastní procesy.)"],
    ],
    [3.7, 6.3, 5.5],
    ref_key="hlediska",
    caption_text="Čtyři klasifikační hlediska",
)
heading("Typové scénáře", 2)
p("Scénář je „vzorový projekt“ — např. malý elektrolyzér pro vlastní spotřebu, veřejná plnicí "
  "stanice, vodíková autobusová doprava. Scénáře vzešly z konzultací s praxí (MPO, dopravci, "
  "průmysl) a jsou hlavním vstupním bodem pro uživatele: místo studia paragrafů si vybere scénář "
  "nejbližší svému záměru. V databázi scénář nese hodnoty čtyř hledisek a seznam uzlů, které se "
  "v něm uplatňují, včetně intenzity (stejná stupnice ●●●/●●○/●○○ jako v matici variability).")
heading("Podmínky aktivace procesů", 2)
p("Zatímco scénář je předpřipravená odpověď, aktivační pravidla umožňují odpověď spočítat "
  "z parametrů konkrétního záměru. Pravidlo má tvar „parametr — porovnání — hodnota“, například: "
  "kapacita elektrolyzéru ≥ 0,5 MW → uplatní se licenční větev uzlu U4. Pravidla se dají skládat "
  "(současně platí A a B, nebo alternativně C) a každé může odkazovat na předpis, který daný práh "
  "stanovuje. Text V02 podmínky popisuje jen slovně; jejich převod do strukturované podoby je "
  "jedna z hlavních analytických prací, která nás čeká — a kde bude potřeba spolupráce expertů.")
p([("Důležité upozornění: ", "b"),
   ("Aktivační pravidla nejsou právní výrok. Řada prahů nevyplývá jednoznačně ze zákona, ale "
    "z výkladové praxe úřadů. Pravidla proto vždy nesou i slovní popis s vysvětlivkami a slouží "
    "k orientaci, ne jako závazné rozhodnutí.", "")])

# ════════════════════════════════════════════════════════════
heading("Jak to celé funguje: compliance pathway", 1, ref_key="pathway")
p("„Compliance pathway“ je pojem z metodiky V03: ucelená cesta ke splnění regulatorních "
  "požadavků, vygenerovaná na míru konkrétnímu záměru. Všechny čtyři vrstvy se v ní potkávají:")
picture("img6-pathway.png", 13.0, "pathway",
        "Od záměru investora k sadě relevantních předpisů ve čtyřech krocích.")
p([
    ("Projděme příklad z obrázku ", ""),
    (figref("pathway"), ""),
    (". Investor plánuje elektrolyzér o výkonu 1,2 MW v průmyslové zóně s prodejem vodíku pro "
     "městské autobusy. V databázi tomu odpovídá scénář „výrobna s prodejem vodíku pro "
     "mobilitu“; parametry záměru (kapacita 1,2 MW, prodej třetím stranám, umístění v "
     "průmyslové zóně) vyhodnotí aktivační pravidla: uplatní se všech sedm uzlů — U7 proto, "
     "že prodej paliva pro dopravu vyžaduje certifikaci původu vodíku. V uzlu U2 pravidla "
     "vyberou větev „zjišťovací řízení“ (kapacita nepřekračuje práh plné EIA). Nakonec se přes "
     "vazby vrstvy C ke každému aktivovanému uzlu dohledají předpisy: stavební zákon, zákon "
     "o EIA, energetický zákon, bezpečnostní předpisy, norma EN 17124, delegované akty EU "
     "k RFNBO — každý s poznámkou, proč je relevantní a zda jde o primární oporu.", ""),
])
p("Výsledek není právní stanovisko, ale strukturovaná mapa: investor (nebo poradce) ví, která "
  "řízení ho čekají, v jakém pořadí, u kterých úřadů a o které předpisy se opírají. Přesně to je "
  "transakční náklad, který má projekt DP004 snižovat.")

# ════════════════════════════════════════════════════════════
heading("Zásady návrhu a stav prací", 1, ref_key="zasady")
heading("Pět zásad, které drží návrh pohromadě", 2)
numbered([("Jen aditivní změny. ", "b"),
          ("Produkční aplikace V01 musí běžet beze změny; nic se nemaže ani nepřejmenovává.", "")])
numbered([("Jeden zdroj pravdy. ", "b"),
          ("Každý předpis je v databázi právě jednou (vrstva A); procesy na něj odkazují, "
           "nekopírují ho.", "")])
numbered([("Stabilní logika, dynamický obsah. ", "b"),
          ("Struktura procesů (vrstva B) se mění zřídka; obsah předpisů (vrstva A) průběžně. "
           "Vrstvy jsou oddělené, takže novela zákona nevyžaduje přepis procesů — jen aktualizaci "
           "vazeb.", "")])
numbered([("Strojově dotazovatelné vazby. ", "b"),
          ("Vazby proces ↔ předpis jsou explicitní databázové vztahy, ne shoda klíčových slov. "
           "Klíčová slova zůstávají pro tematické hledání.", "")])
numbered([("Dohledatelnost úsudku. ", "b"),
          ("Vše, co je názor analytika (intenzity, aktivační prahy, poznámky k relevanci), nese "
           "slovní zdůvodnění, aby to šlo revidovat.", "")])
heading("Co je hotovo a co nás čeká", 2)
table(
    ["Hotovo (návrh)", "Čeká nás (společná práce)"],
    [
        ["Kompletní návrh schématu všech čtyř vrstev (dokumentace, UML diagram, DDL skript pro "
         "MariaDB).",
         "Extrakce obsahu z textu V02: větve, kroky, vstupy/výstupy, subjekty, problémy pro "
         "všech 7 uzlů."],
        ["Referenční data: číselníky, uzly U1–U7, procesní síť, matice variability (intenzity).",
         "Vazby uzel ↔ dokument: dohledání všech citovaných předpisů v databázi a založení vazeb."],
        ["Migrační plán v pěti krocích, čistě aditivní.",
         "Formalizace aktivačních pravidel a definice typových scénářů; poté úprava webové "
         "aplikace."],
    ],
    [7.75, 7.75],
    ref_key="stav",
    caption_text="Stav prací — hotovo a co nás čeká",
)

# ════════════════════════════════════════════════════════════
heading("Kde co najdete", 1, ref_key="kde")
p("Všechny podklady jsou ve složce projektu „Architektura databáze“:")
table(
    ["Soubor / složka", "Obsah"],
    [
        ["Databáze.Konsolidovaná/Konsolidace-DB-popis.md", "Technická dokumentace návrhu: "
         "návrhová rozhodnutí, popis tabulek, ukázkové dotazy, migrační plán."],
        ["Databáze.Konsolidovaná/Konsolidace-DB-schema.puml", "Úplné UML (ER) schéma — render "
         "na plantuml.com."],
        ["Databáze.Konsolidovaná/Konsolidace-DB-schema.sql", "DDL skript pro MariaDB včetně "
         "referenčních dat."],
        ["Databáze.Konsolidovaná/obrazky/", "Zdrojové diagramy tohoto průvodce (Graphviz)."],
        ["Databáze.V01/", "Stávající databáze dokumentů (schéma, diagram, SQLite ukázka)."],
        ["Databáze.V02/V02-DB-popis.md", "Podrobný popis procesní vrstvy z návrhu V02."],
        ["Dokumenty/", "Oficiální texty výsledků V01, V02 a V03 (Word)."],
    ],
    [7.2, 8.3],
    ref_key="soubory",
    caption_text="Přehled souborů projektu",
)

# ════════════════════════════════════════════════════════════
heading("Slovníček pojmů", 1, ref_key="slovnik")
table(
    ["Pojem", "Vysvětlení"],
    [
        ["Procesní uzel (U1–U7)", "Ucelené povolovací/schvalovací řízení s jasným výstupem; "
         "základní jednotka procesní vrstvy."],
        ["Větev průběhu", "Jedna z možných variant, jak řízení proběhne (např. zjišťovací řízení "
         "vs. plná EIA)."],
        ["Matice variability 4×7", "Tabulka intenzit: jak silně se každý ze 7 uzlů uplatní pro "
         "4 typy instalací."],
        ["Compliance pathway", "Na míru vygenerovaná cesta záměru: aktivované uzly + relevantní "
         "předpisy."],
        ["Aktivační pravidlo", "Strukturovaná podmínka (parametr–porovnání–hodnota), za níž se "
         "uzel/větev uplatní."],
        ["Typový scénář", "Vzorový projekt (např. veřejná plnicí stanice) s předdefinovaným "
         "procesním profilem."],
        ["Číselník", "Tabulka s pevným seznamem hodnot (typy dokumentů, intenzity…); zaručuje "
         "jednotné vyplňování."],
        ["Řízený slovník", "Klíčová slova spravovaná týmem — nová slova se přidávají řízeně, ne "
         "volně uživateli."],
        ["RFNBO", "„Renewable Fuel of Non-Biological Origin“ — unijní kategorie obnovitelného "
         "vodíku; její prokazování řeší uzel U7."],
        ["EIA / IPPC", "Posouzení vlivů na životní prostředí / integrované povolení pro velké "
         "provozy (uzel U2)."],
        ["Metadatový přístup", "Databáze eviduje popis a zařazení dokumentu, ne jeho plný text."],
        ["Aditivní migrace", "Změny databáze, které pouze přidávají (sloupce, tabulky) — nic "
         "nemažou ani nemění."],
    ],
    [4.3, 11.2],
    ref_key="slovnik",
    caption_text="Slovníček pojmů",
)

def set_lang_everywhere(document):
    """Nastaví jazyk cs-CZ na každém běhu textu v těle dokumentu i v patičce.
    Základní dokument (Konsolidace-DB-pruvodce.docx) má w:lang="cs-CZ" na všech
    bězích — bez toho aplikace nabízí jazyk dle docDefaults (en-US) a text se
    kontroluje/indikuje jako anglický. w:lang je poslední prvek v pořadí
    EG_RPrBase (wml.xsd), takže jeho připojení na konec libovolného w:rPr je
    vždy schema-validní."""
    def process(root_element):
        for r in root_element.iter(qn("w:r")):
            rpr = r.find(qn("w:rPr"))
            if rpr is None:
                rpr = OxmlElement("w:rPr")
                r.insert(0, rpr)
            if rpr.find(qn("w:lang")) is None:
                lang = OxmlElement("w:lang")
                lang.set(qn("w:val"), "cs-CZ")
                lang.set(qn("w:eastAsia"), "cs-CZ")
                lang.set(qn("w:bidi"), "ar-SA")
                rpr.append(lang)
    process(document.element.body)
    for section in document.sections:
        process(section.footer.part.element)

# ── Uložení + post-processing (motivové písmo Aptos, oprava w:zoom,
#    vynucený přepočet polí SEQ/REF při otevření v aplikaci, jazyk cs-CZ) ──
set_lang_everywhere(doc)
doc.save(OUT)

def postprocess(path):
    tmp = path + ".tmp"
    with zipfile.ZipFile(path, "r") as zin, \
         zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/theme/theme1.xml":
                t = data.decode("utf-8")
                t = re.sub(r'(<a:majorFont>\s*<a:latin typeface=")[^"]*(")',
                           r'\g<1>Aptos Display\g<2>', t)
                t = re.sub(r'(<a:minorFont>\s*<a:latin typeface=")[^"]*(")',
                           r'\g<1>Aptos\g<2>', t)
                data = t.encode("utf-8")
            elif item.filename == "word/settings.xml":
                s = data.decode("utf-8")
                s = re.sub(r'<w:zoom\s*/>', '<w:zoom w:percent="100"/>', s)
                s = re.sub(r'(<w:zoom(?![^>]*w:percent)[^>]*?)/>',
                           r'\g<1> w:percent="100"/>', s)
                # Vynutí přepočet SEQ/REF polí při otevření dokumentu.
                # Pořadí v CT_Settings (wml.xsd): updateFields musí být až
                # za savePreviewPicture a před compat/docVars/rsids atd.
                if "<w:updateFields" not in s:
                    s = re.sub(r'(<w:compat>)', r'<w:updateFields w:val="true"/>\1', s, count=1)
                data = s.encode("utf-8")
            elif item.filename == "word/styles.xml":
                # docDefaults jazyk en-US → cs-CZ (viz set_lang_everywhere výše —
                # to řeší jazyk jednotlivých běhů, toto řeší výchozí hodnotu).
                s = data.decode("utf-8")
                s = re.sub(
                    r'<w:lang w:val="en-US" w:eastAsia="en-US" w:bidi="ar-SA"/>',
                    r'<w:lang w:val="cs-CZ" w:eastAsia="cs-CZ" w:bidi="ar-SA"/>',
                    s, count=1)
                data = s.encode("utf-8")
            zout.writestr(item, data)
    os.replace(tmp, path)

postprocess(OUT)
print("OK:", OUT)
