"""Shared resolution of a technical standard's issuing body ("Gestor").

User finding / doc/PLAN.md §16 (2026-09-16): `backfill_puvodce.py`'s
reduction of the raw `gestor` lists to one institution was right for
national CZ/SK acts, and `backfill_eu_gestor.py` resolved EU acts against
EUR-Lex/Cellar — but neither covers documents of type `Norma`, which are
89 % of the corpus. Only 5 of 1 104 standards had any `source_id`, and
`DocumentSource` held no standard-setting body at all, even though
`doc/REQUIREMENTS.md` R1.6 names them explicitly.

No lookup was needed to fix that: a standard's designation already names
its publisher. `norm_title.py` (2026-09-15) had just moved that
designation to the front of every `Norma` title, and `Document.identifier`
carries it verbatim — "ČSN EN 17124" is published by the Czech agency,
"STN EN 61982-4" by the Slovak one, "ISO 21010" by ISO.

STANDARDS_BODY_MAP is keyed on the designation's FIRST whitespace-
delimited token, which is unambiguous in this corpus (verified against
all 98 distinct first tokens, 2026-09-16: "ISO/AWI", "CSA/ANSI" and
"VDI/VDE" are their own tokens, never prefixes shadowed by "ISO", "CSA"
or "VDI"). Entries were curated by reading the actual records behind each
token, not assumed from the abbreviation — see the grouped comments
below for the ones that needed evidence. A token that isn't in the map
resolves to None and the record keeps no Gestor, the same never-guess
rule `norm_title.is_real_designation()` already applies.
"""
import re
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from norm_title import designation_core

_SLOVAK = "Úrad pre normalizáciu, metrológiu a skúšobníctvo SR (ÚNMS SR)"
_CZECH = "Česká agentura pro standardizaci (ČAS)"
_DVGW = "Deutscher Verein des Gas- und Wasserfaches (DVGW)"
_ISO = "International Organization for Standardization (ISO)"
_IEC = "International Electrotechnical Commission (IEC)"
_CEN = "Evropský výbor pro normalizaci (CEN/CENELEC)"
_EIGA = "European Industrial Gases Association (EIGA)"
_CSA = "CSA Group"
_BAUA = "Bundesanstalt für Arbeitsschutz und Arbeitsmedizin (BAuA)"
_NIST = "National Institute of Standards and Technology (NIST)"
_IMO = "International Maritime Organization (IMO)"

STANDARDS_BODY_MAP = {
    # National standards institutes. A national adoption of a European or
    # international norm ("STN EN ISO 1234") is published BY that national
    # institute, so the leading token is the right signal — the same
    # reading `parse_sinay_norms.classify_jurisdikce()` already applies to
    # decide SK/DE/CZ.
    "STN": _SLOVAK,
    # TNI: Slovak "technická normalizačná informácia" — all 14 records
    # carry jurisdikce=SK and Slovak titles, so this is the Slovak series,
    # not the identically-named Czech one.
    "TNI": _SLOVAK,
    "ČSN": _CZECH,
    "DIN": "Deutsches Institut für Normung (DIN)",
    "BS": "British Standards Institution (BSI)",
    "AFNOR": "Association française de normalisation (AFNOR)",

    # International / European.
    "ISO": _ISO, "ISO/AWI": _ISO, "ISO/CD": _ISO, "ISO/DIS": _ISO,
    "ISO/FDIS": _ISO, "ISO/PWI": _ISO, "ISO/TR": _ISO, "ISO/TS": _ISO,
    "ISO/WD": _ISO,
    "IEC": _IEC, "IEC/TR": _IEC, "IEC/TS": _IEC,
    "EN": _CEN, "prEN": _CEN, "FprEN": _CEN, "CEN/TS": _CEN,
    "CEN/CLC/JTC": _CEN,
    "OIML": "International Organization of Legal Metrology (OIML)",
    "IMO": _IMO,
    # IGF Code / MSC resolutions and circulars are IMO instruments.
    "IGF": _IMO, "MSC.420(97)": _IMO, "MSC.1/Circ.1647": _IMO,
    "ES-TRIN": "Evropský výbor pro vypracování norem v oblasti vnitrozemské plavby (CESNI)",

    # DVGW. Confirmed from the records themselves rather than the letter:
    # the G-series titles cite the "DVGW-Regelwerk" and "DVGW-TRGI"
    # directly, and the whole family uses DVGW's own (A)=Arbeitsblatt /
    # (M)=Merkblatt suffix convention. GW (Gas+Wasser), C (CO2) and the
    # ZP "Zertifizierungsprogramm" and "Gas-Information" series are the
    # same publisher's other imprints.
    "G": _DVGW, "GW": _DVGW, "C": _DVGW, "ZP": _DVGW, "G269": _DVGW,
    "Gas-Information": _DVGW, "Gas": _DVGW,

    # Other German bodies.
    "VDI": "Verein Deutscher Ingenieure (VDI)",
    "VDI/VDE": "Verein Deutscher Ingenieure (VDI)",
    "VDE-AR-N": "VDE Verband der Elektrotechnik Elektronik Informationstechnik (VDE)",
    "VDA": "Verband der Automobilindustrie (VDA)",
    "PTB": "Physikalisch-Technische Bundesanstalt (PTB)",
    "PTB-A": "Physikalisch-Technische Bundesanstalt (PTB)",
    "DGUV": "Deutsche Gesetzliche Unfallversicherung (DGUV)",
    "DASt": "Deutscher Ausschuss für Stahlbau (DASt)",
    "DWA-M": "Deutsche Vereinigung für Wasserwirtschaft, Abwasser und Abfall (DWA)",
    "AD": "Arbeitsgemeinschaft Druckbehälter (AD)",
    "AD-Merkblatt": "Arbeitsgemeinschaft Druckbehälter (AD)",
    # TRGS/TRBS and the legacy TRB/TRG pressure-vessel and gas rules are
    # all published by BAuA for their respective committees.
    "TRGS": _BAUA, "TRBS": _BAUA, "TRB": _BAUA, "TRG16": _BAUA, "TRG19": _BAUA,

    # Industry associations / US bodies.
    # EIGA and IGC are the same organisation before and after its
    # renaming — an equivalence deduplicate_db.py's `_EIGA_IGC_PREFIX_RE`
    # already encodes; "Doc NNN/YY" is EIGA's own bare document form.
    "EIGA": _EIGA, "IGC": _EIGA, "Doc": _EIGA,
    "ASTM": "ASTM International",
    "ASME": "American Society of Mechanical Engineers (ASME)",
    "SAE": "SAE International",
    "SAE/USCAR-5-5": "SAE International", "SAE/USCAR-7-2": "SAE International",
    "API": "American Petroleum Institute (API)",
    "CGA": "Compressed Gas Association (CGA)",
    "NFPA": "National Fire Protection Association (NFPA)",
    "NACE": "NACE International", "ANSI/NACE": "NACE International",
    "UL": "UL Solutions",
    "OSHA": "Occupational Safety and Health Administration (OSHA)",
    "NASA": "National Aeronautics and Space Administration (NASA)",
    "NIST": _NIST, "FIPS": _NIST,
    "Sandia": "Sandia National Laboratories",
    "ARAMCO": "Saudi Aramco",
    "DNV/RP": "DNV",
    "IGEM/TD/1": "Institution of Gas Engineers and Managers (IGEM)",
    # CSA publishes the CHMC hydrogen-materials series alongside its own
    # and the joint ANSI ones.
    "CSA": _CSA, "CSA/ANSI": _CSA, "ANSI/CSA": _CSA, "CHMC": _CSA,
    "ANSI/AIAA": "American Institute of Aeronautics and Astronautics (AIAA)",
    # "known as the SAA Anhydrous Ammonia Code" in the records' own titles
    # — the Standards Association of Australia, now Standards Australia.
    "AS": "Standards Australia", "AS/NZS": "Standards Australia",
}

# Deliberately NOT mapped, after reading each one (2026-09-16): "MB"
# (3 German Merkblätter whose issuing body isn't identifiable from the
# record), "SEP", "AR", "TPP", "TB.", "PP", "PAS", "H2.22:2022",
# "A-A-59874", "FBETEM-007", "Publikation", "Mitteilung", and the parse
# artefacts "Part", "Band", "A1" and the empty token. ~20 records, left
# without a Gestor rather than guessed at.


_LOWERCASE_MAP = {k.lower(): v for k, v in STANDARDS_BODY_MAP.items()}

# Some designations glue the number straight onto the publisher prefix
# with no space ("ZP-5101", "ZP-8106"), so the first whitespace token is
# not itself a key. Falling back to the token's leading alphabetic run
# resolves those without widening the map. Checked against the whole
# corpus (2026-09-16): it changes the answer only for those two records
# and never turns a previously-unmapped token into a wrong body.
_ALPHA_PREFIX_RE = re.compile(r"^[A-Za-zÁ-Žá-ž]+")


def resolve_standards_body(identifier):
    """Returns the issuing body for a standard's designation, or None
    when the designation is missing or its leading token isn't one this
    module recognizes (never guessed — see the module docstring)."""
    core = designation_core(identifier)
    tokens = core.split() if core else []
    if not tokens:
        return None
    first = tokens[0]
    body = STANDARDS_BODY_MAP.get(first) or _LOWERCASE_MAP.get(first.lower())
    if body:
        return body
    m = _ALPHA_PREFIX_RE.match(first)
    if m and m.group(0) != first:
        prefix = m.group(0)
        return STANDARDS_BODY_MAP.get(prefix) or _LOWERCASE_MAP.get(prefix.lower())
    return None


# doc/PLAN.md §41, 2026-09-18: `Document.jurisdikce` for a `Norma` record
# whose issuing body is already known (via `resolve_standards_body()`
# above) — the same "national institute publishes it, so that's its
# jurisdikce" reading `resolve_prokop_jurisdikce()`/`parse_sinay_norms.
# classify_jurisdikce()` already apply elsewhere, generalized to every
# body this module knows. "mezinárodní" for a body whose own standing is
# international rather than any one country's (ISO, IEC, IMO/IGF, OIML,
# DNV — a classification society whose Recommended Practice documents
# are used worldwide, the same reading applied to ISO/IEC themselves
# despite their Swiss/US registered offices). Every value below is
# checked against `STANDARDS_BODY_MAP`'s own values by
# `tests/test_standards_body.py` — a body added there with no jurisdikce
# entry here returns `None`, never a silent guess.
_JURISDIKCE_BY_BODY = {
    _SLOVAK: "SK",
    _CZECH: "CZ",
    "Deutsches Institut für Normung (DIN)": "DE",
    "British Standards Institution (BSI)": "UK",
    "Association française de normalisation (AFNOR)": "FR",
    _ISO: "mezinárodní",
    _IEC: "mezinárodní",
    _CEN: "EU",
    "International Organization of Legal Metrology (OIML)": "mezinárodní",
    _IMO: "mezinárodní",
    "Evropský výbor pro vypracování norem v oblasti vnitrozemské plavby (CESNI)": "mezinárodní",
    _DVGW: "DE",
    "Verein Deutscher Ingenieure (VDI)": "DE",
    "VDE Verband der Elektrotechnik Elektronik Informationstechnik (VDE)": "DE",
    "Verband der Automobilindustrie (VDA)": "DE",
    "Physikalisch-Technische Bundesanstalt (PTB)": "DE",
    "Deutsche Gesetzliche Unfallversicherung (DGUV)": "DE",
    "Deutscher Ausschuss für Stahlbau (DASt)": "DE",
    "Deutsche Vereinigung für Wasserwirtschaft, Abwasser und Abfall (DWA)": "DE",
    "Arbeitsgemeinschaft Druckbehälter (AD)": "DE",
    _BAUA: "DE",
    _EIGA: "EU",
    "ASTM International": "US",
    "American Society of Mechanical Engineers (ASME)": "US",
    "SAE International": "US",
    "American Petroleum Institute (API)": "US",
    "Compressed Gas Association (CGA)": "US",
    "National Fire Protection Association (NFPA)": "US",
    "NACE International": "US",
    "UL Solutions": "US",
    "Occupational Safety and Health Administration (OSHA)": "US",
    "National Aeronautics and Space Administration (NASA)": "US",
    _NIST: "US",
    "Sandia National Laboratories": "US",
    "Saudi Aramco": "SA",
    "DNV": "mezinárodní",
    "Institution of Gas Engineers and Managers (IGEM)": "UK",
    _CSA: "CA",
    "American Institute of Aeronautics and Astronautics (AIAA)": "US",
    "Standards Australia": "AU",
}


def resolve_norma_jurisdikce(identifier):
    """Returns the jurisdikce implied by a `Norma` record's OWN
    designation, via the same issuing-body resolution
    `resolve_standards_body()` already uses — never derived any other
    way. `None` when the body isn't recognized at all, or is recognized
    but not yet in `_JURISDIKCE_BY_BODY` (never assumed)."""
    body = resolve_standards_body(identifier)
    if not body:
        return None
    return _JURISDIKCE_BY_BODY.get(body)
