"""
LegalGraphify — Módulo de Conversión y Normalización de Documentos a Markdown Canónico (doc2md)
Transforma textos jurídicos desestructurados, PDFs y documentos en Markdown canónico token-optimizado
siguiendo estrictamente las normas ortotipográficas RAE/ASALE y el estándar de Derecho Continental de Chile.
"""
from __future__ import annotations

import os
import re
import zipfile
try:
    import defusedxml.ElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET  # nosec B405
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple


def extract_text_from_source(source: str | Path) -> str:
    """
    Extrae texto crudo a partir de una ruta de archivo (PDF, DOCX, TXT, MD) o devuelve el texto directamente.
    Para DOCX utiliza descompresión XML pura de la biblioteca estándar (cero dependencias).
    Para PDF utiliza PyMuPDF (fitz) si está disponible, o emite un error instructivo.
    """
    if isinstance(source, Path):
        source = str(source)

    if os.path.exists(source) and os.path.isfile(source):
        ext = os.path.splitext(source)[1].lower()

        if ext in (".txt", ".md"):
            try:
                with open(source, "r", encoding="utf-8") as f:
                    return f.read()
            except UnicodeDecodeError:
                with open(source, "r", encoding="latin-1", errors="ignore") as f:
                    return f.read()

        elif ext == ".docx":
            # Extracción pura con zipfile y xml.etree (sin dependencias externas)
            try:
                with zipfile.ZipFile(source) as docx_zip:
                    xml_content = docx_zip.read("word/document.xml")
                    tree = ET.fromstring(xml_content)  # nosec B314
                    # Espacios de nombres de WordprocessingML
                    namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                    paragraphs = []
                    for p in tree.findall(".//w:p", namespaces):
                        texts = [t.text for t in p.findall(".//w:t", namespaces) if t.text]
                        if texts:
                            paragraphs.append("".join(texts))
                    return "\n\n".join(paragraphs)
            except Exception as e:
                raise RuntimeError(f"Error al extraer texto de archivo DOCX '{source}': {e}")

        elif ext == ".pdf":
            try:
                import fitz  # type: ignore # PyMuPDF
                doc = fitz.open(source)
                pages_text = [page.get_text() for page in doc]
                return "\n\n".join(pages_text)
            except ImportError:
                # Fallback: intentar pypdf si estuviera instalado
                try:
                    import pypdf  # type: ignore
                    reader = pypdf.PdfReader(source)
                    return "\n\n".join([page.extract_text() or "" for page in reader.pages])
                except ImportError:
                    raise RuntimeError(
                        f"Para procesar archivos PDF ('{source}'), instala PyMuPDF ejecutando:\n"
                        f"pip install pymupdf"
                    )
        else:
            # Archivo genérico: intentar leer como texto UTF-8
            try:
                with open(source, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                with open(source, "r", encoding="latin-1", errors="ignore") as f:
                    return f.read()

    # Si no es un archivo existente, se asume que es el contenido de texto en sí
    return str(source)


def clean_unwanted_hyphens_and_breaks(text: str) -> str:
    """
    Limpia saltos de línea quebrados y une palabras divididas por guion al final de línea
    (ej. 'obli-\\n   gaciones' -> 'obligaciones').
    """
    if not text:
        return ""

    # 1. Unir palabras divididas por guion al final de línea
    # Busca palabra- seguida de salto de línea y continuación de palabra
    text = re.sub(r"([a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+)-\s*\n\s*([a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+)", r"\1\2", text)

    # 2. Suprimir numeración de páginas flotante o encabezados comunes
    text = re.sub(r"\n\s*(?:Página|Pág\.?)\s*\d+\s*(?:de\s*\d+)?\s*\n", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"\n\s*---\s*\d+\s*---\s*\n", "\n\n", text)

    # 3. Unir líneas huérfanas dentro de un mismo párrafo preservando saltos dobles
    lines = text.split("\n")
    cleaned_lines: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            cleaned_lines.append("")
            i += 1
            continue

        # Si la línea actual no termina en puntuación de cierre (. : ? !) ni en encabezado (#)
        # y la siguiente línea existe y no empieza por encabezado o viñeta
        if (
            not line.endswith((".", ":", ";", "?", "!", "»", '""'))
            and not line.startswith(("#", "*", "-", "•", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9."))
            and i + 1 < len(lines)
            and lines[i + 1].strip()
            and not lines[i + 1].strip().startswith(("#", "*", "-", "•"))
            and not re.match(r"^\d+\.", lines[i + 1].strip())
        ):
            # Unir con la siguiente
            line = line + " " + lines[i + 1].strip()
            i += 1

        cleaned_lines.append(line)
        i += 1

    joined = "\n".join(cleaned_lines)
    # Reducir múltiples saltos triples o más a saltos dobles
    return re.sub(r"\n{3,}", "\n\n", joined).strip()


def apply_ortotipografia_rae_chile(text: str) -> str:
    """
    Aplica estrictamente las normas de la RAE, ASALE y la Academia Chilena de la Lengua:
    1. Comillas primarias angulares o latinas (« »); comillas dobles inglesas (" ") solo dentro de citas.
    2. Puntuación SIEMPRE fuera de las comillas de cierre: «ejemplo», «ejemplo».
    3. Signos de apertura obligatorios: ¿ y ¡.
    4. Cifras con coma decimal en Chile (12,5 %) y espacio obligatorio antes de %.
    5. RUT con puntos en millares y guion antes del dígito verificador (12.345.678-9).
    6. Abreviaturas oficiales: N.° para número, Art. para artículo, inc. para inciso.
    """
    if not text:
        return ""

    res = text

    # 1. Espacio antes de porcentaje: '100%' -> '100 %', '25.5%' -> '25.5 %'
    res = re.sub(r"(\d+)%", r"\1 %", res)

    # 2. Coma decimal en Chile para porcentajes y decimales habituales
    res = re.sub(r"(\d+)\.(\d+)\s*%", r"\1,\2 %", res)

    # 3. Normalizar comillas dobles inglesas a latinas « » si no están ya en latinas
    # Reemplaza pares de comillas "texto" por «texto»
    res = re.sub(r'(?<!\w)"([^"\n]+?)"(?!\w)', r'«\1»', res)

    # 4. Puntuación fuera de las comillas de cierre: «ejemplo.» -> «ejemplo».
    res = re.sub(r'([«“"])([^»”"]+?)([,\.;:])([»”"])', r'\1\2\4\3', res)

    # 5. Normalizar abreviaturas: N° -> N.° | No. -> N.°
    res = re.sub(r"\bN°\s*", "N.° ", res)
    res = re.sub(r"\bNo\.\s*(\d+)", r"N.° \1", res)

    # 6. Normalizar Art. / Arts.
    res = re.sub(r"\b[Aa]rt(?:[ií]culo)?\s*(\d+)", r"Art. \1", res)
    res = re.sub(r"\b[Aa]rt(?:[ií]culos)?\s*(\d+)", r"Arts. \1", res)
    res = re.sub(r"\b[Ii]nciso\s*(\d+)", r"inc. \1", res)

    # 7. Normalizar formato de RUT chileno: XX.XXX.XXX-Y
    def _format_rut(match: re.Match) -> str:
        raw_num = match.group(1).replace(".", "").replace(" ", "")
        dv = match.group(2).upper()
        if len(raw_num) in (7, 8):
            num = int(raw_num)
            formatted = f"{num:,}".replace(",", ".")
            return f"{formatted}-{dv}"
        return match.group(0)

    res = re.sub(r"\b(\d{1,2}(?:\.?\d{3}){2})-?([0-9kK])\b", _format_rut, res)

    return res


def standardize_legal_citations(text: str) -> str:
    """
    Detecta menciones a cuerpos legales, Códigos de la República y jurisprudencia
    y las transforma al estándar de citación oficial entre corchetes de Open Legal Chile:
    - [BCN - Código Civil, Art. 1545]
    - [BCN - Ley N° 21.643, Art. 2]
    - [CS - Rol N° 12.345-2023, Fecha: ...]
    - [Dictamen DT N° 1234/15 de 2024]
    - [Dictamen CGR N° E123456 (2024)]
    """
    if not text:
        return ""

    res = text

    # 1. Códigos Fundamentales de Chile
    codigos_map = [
        (r"\b(?:del\s+)?Código Civil\b", "Código Civil"),
        (r"\b(?:del\s+)?Código del Trabajo\b", "Código del Trabajo"),
        (r"\b(?:del\s+)?Código de Procedimiento Civil\b", "Código de Procedimiento Civil"),
        (r"\b(?:del\s+)?Código Penal\b", "Código Penal"),
        (r"\b(?:del\s+)?Código de Comercio\b", "Código de Comercio"),
        (r"\b(?:del\s+)?Código Tributario\b", "Código Tributario"),
        (r"\b(?:del\s+)?Código Procesal Penal\b", "Código Procesal Penal"),
        (r"\b(?:del\s+)?Código Orgánico de Tribunales\b", "Código Orgánico de Tribunales"),
        (r"\b(?:del\s+)?Código de Aguas\b", "Código de Aguas"),
        (r"\b(?:del\s+)?Código de Minería\b", "Código de Minería"),
    ]

    # Reemplazar menciones: 'Art. 1545 del Código Civil' -> '[BCN - Código Civil, Art. 1545]'
    for pattern, nombre_codigo in codigos_map:
        res = re.sub(
            rf"\b(Arts?\.?\s*\d+(?:\s*(?:bis|ter|quater))?(?:\s*(?:inc\.?\s*\d+|N\.?°?\s*\d+))*)\s+{pattern}",
            rf"[BCN - {nombre_codigo}, \1]",
            res,
            flags=re.IGNORECASE,
        )
        # Formato inverso: 'Código Civil, Art. 1545'
        res = re.sub(
            rf"\b{nombre_codigo},?\s+(Arts?\.?\s*\d+(?:\s*(?:bis|ter|quater))?(?:\s*(?:inc\.?\s*\d+|N\.?°?\s*\d+))*)",
            rf"[BCN - {nombre_codigo}, \1]",
            res,
            flags=re.IGNORECASE,
        )

    # Siglas breves: CC, CPC, CPP, CP, CT, COT
    siglas_map = {
        "CC": "Código Civil",
        "CPC": "Código de Procedimiento Civil",
        "CPP": "Código Procesal Penal",
        "CP": "Código Penal",
        "CT": "Código del Trabajo",
        "COT": "Código Orgánico de Tribunales",
    }
    for sigla, nombre_codigo in siglas_map.items():
        res = re.sub(
            rf"\b(Arts?\.?\s*\d+(?:\s*(?:bis|ter|quater))?(?:\s*(?:inc\.?\s*\d+|N\.?°?\s*\d+))*)\s+del\s+{sigla}\b",
            rf"[BCN - {nombre_codigo}, \1]",
            res,
        )
        res = re.sub(
            rf"\b(Arts?\.?\s*\d+(?:\s*(?:bis|ter|quater))?(?:\s*(?:inc\.?\s*\d+|N\.?°?\s*\d+))*)\s+{sigla}\b(?!\w)",
            rf"[BCN - {nombre_codigo}, \1]",
            res,
        )

    # 2. Leyes de la República: 'Ley N° 21.643', 'Ley 19.886'
    def _format_ley(m: re.Match) -> str:
        num = m.group(1).replace(".", "")
        art_part = f", {m.group(2).strip()}" if m.group(2) else ""
        return f"[BCN - Ley N° {num}{art_part}]"

    res = re.sub(
        r"\bLey\s*(?:N\.?°?|número)?\s*(\d{1,2}(?:\.?\d{3}))(?:\s*,?\s*(Arts?\.?\s*\d+(?:\s*(?:bis|ter))?(?:\s*inc\.?\s*\d+)?))?\b",
        _format_ley,
        res,
        flags=re.IGNORECASE,
    )

    # 3. Constitución Política: 'Art. 19 N° 24 de la Constitución'
    res = re.sub(
        r"\b(Arts?\.?\s*\d+(?:\s*N\.?°?\s*\d+)?(?:\s*inc\.?\s*\d+)?)\s+(?:de\s+la\s+)?(?:Constitución|CPR|Constitución Política)\b",
        r"[CPR 1980 - \1]",
        res,
        flags=re.IGNORECASE,
    )

    # 4. Roles de la Corte Suprema y Cortes de Apelaciones: 'Rol N° 12.345-2023'
    def _format_rol(m: re.Match) -> str:
        rol_num = m.group(1)
        tribunal = m.group(2) or "CS"
        trib_code = "CS" if any(t in tribunal.upper() for t in ["SUPREMA", "CS"]) else tribunal
        return f"[{trib_code} - Rol N° {rol_num}]"

    res = re.sub(
        r"\bRol\s*(?:N\.?°?|número)?\s*(\d+[\.\d]*-\d{4})\s*(?:(?:de\s+la\s+)?(Corte Suprema|CS|C\.?A\.?\s+de\s+[A-Za-z]+))?\b",
        _format_rol,
        res,
        flags=re.IGNORECASE,
    )

    # 5. Dictámenes DT y CGR
    res = re.sub(
        r"\bDictamen\s*(?:DT)?\s*(?:N\.?°?|número)?\s*(\d+/\d{2,4})\b",
        r"[Dictamen DT N° \1]",
        res,
        flags=re.IGNORECASE,
    )
    res = re.sub(
        r"\bDictamen\s*(?:CGR)?\s*(?:N\.?°?|número)?\s*([E]?\d{5,8}(?:/\d{2,4})?)\b",
        r"[Dictamen CGR N° \1]",
        res,
        flags=re.IGNORECASE,
    )

    # Evitar duplicaciones de corchetes como [[BCN - ...]]
    res = re.sub(r"\[\[(.*?)\]\]", r"[\1]", res)

    return res


def segment_institutions(clean_text: str) -> List[Dict[str, Any]]:
    """
    Segmenta un texto dogmático o procesal en instituciones jurídicas individuales,
    extrayendo definición, requisitos, operativa procesal, concordancias y precedentes.
    """
    institutions: List[Dict[str, Any]] = []

    # Intentar división por encabezados de nivel 2 o secciones numéricas
    raw_sections = re.split(r"\n(?=##\s+|###\s+|(?:\d+\.|\bI{1,3}\.|\bIV\.|\bV\.|\bVI\.)\s+[A-ZÁÉÍÓÚÑ])", clean_text)

    for sec in raw_sections:
        sec_str = sec.strip()
        if not sec_str or len(sec_str) < 30:
            continue

        lines = [l.strip() for l in sec_str.split("\n") if l.strip()]
        if not lines:
            continue

        # Determinar título
        header_candidate = lines[0]
        header_clean = re.sub(r"^(?:#+|\d+\.|\bI{1,3}\.|\bIV\.|\bV\.|\bVI\.)\s*", "", header_candidate).strip()
        header_clean = re.sub(r"^🏛️\s*", "", header_clean).strip()

        if len(header_clean) < 3 or header_clean.lower().startswith(("capítulo", "introducción", "bibliografía", "índice")):
            continue

        body = "\n".join(lines[1:]) if len(lines) > 1 else ""

        # 1. Definición Canónica
        def_match = re.search(r"(?:Definición(?:\s*Canónica)?|Concepto|Noción):\s*(.*?)(?=\n\n|\n\*\*|\n\*|\Z)", body, re.DOTALL | re.IGNORECASE)
        if def_match:
            definicion = def_match.group(1).strip()
        else:
            # Tomar el primer párrafo significativo
            first_p = lines[1] if len(lines) > 1 else body[:250]
            definicion = first_p.strip()

        # 2. Requisitos / Elementos
        req_match = re.search(r"(?:Requisitos(?:\s*Copulativos)?|Elementos|Condiciones|Clasificación):\s*(.*?)(?=\n\n(?:Operativa|Concordancias|Criterio)|\n\*\*Operativa|\Z)", body, re.DOTALL | re.IGNORECASE)
        requisitos = req_match.group(1).strip() if req_match else ""

        # 3. Operativa Procesal Forense
        proc_match = re.search(r"(?:Operativa\s*Procesal\s*Forense|Vía\s*Procesal|Efectos\s*Procesales|Titularidad\s*y\s*Plazos):\s*(.*?)(?=\n\n(?:Concordancias|Criterio)|\n\*\*Concordancias|\Z)", body, re.DOTALL | re.IGNORECASE)
        operativa = proc_match.group(1).strip() if proc_match else ""

        # 4. Concordancias BCN
        concordancias = re.findall(r"\[BCN\s*-\s*[^\]]+\]", body)
        if not concordancias:
            # Buscar menciones directas como Art. 1545 CC
            concordancias = re.findall(r"(?:Arts?\.?\s*\d+(?:\s*(?:bis|ter|quater))?(?:\s*(?:inc\.?\s*\d+|N\.?°?\s*\d+))*\s*(?:del\s*)?(?:Código Civil|Código del Trabajo|CPC|CPP|CP|COT|CPR|Ley\s*\d+[\.\d]*))", body)

        # 5. Criterios Jurisprudenciales
        criterios = re.findall(r"\[(?:CS|C\.?A\.?)\s*-\s*Rol\s*[^\]]+\]", body)
        if not criterios:
            criterios = re.findall(r"Rol\s*N\.?°?\s*\d+[\.\d]*-\d{4}", body)

        institutions.append({
            "titulo": header_clean,
            "definicion": definicion,
            "requisitos": requisitos,
            "operativa": operativa,
            "concordancias": list(dict.fromkeys(concordancias)),
            "criterios": list(dict.fromkeys(criterios)),
            "contenido_crudo": sec_str
        })

    # Si no se detectaron secciones específicas, crear una sola institución global
    if not institutions and len(clean_text.strip()) > 30:
        concordancias = re.findall(r"\[BCN\s*-\s*[^\]]+\]", clean_text)
        criterios = re.findall(r"\[(?:CS|C\.?A\.?)\s*-\s*Rol\s*[^\]]+\]", clean_text)
        institutions.append({
            "titulo": "Institución Principal",
            "definicion": clean_text[:400].strip(),
            "requisitos": "",
            "operativa": "",
            "concordancias": list(dict.fromkeys(concordancias)),
            "criterios": list(dict.fromkeys(criterios)),
            "contenido_crudo": clean_text.strip()
        })

    return institutions


def convert_text_to_canonical_markdown(
    raw_text: str,
    metadata: Optional[Dict[str, str]] = None
) -> str:
    """
    Transforma un texto desestructurado en un documento Markdown Canónico token-optimizado
    para LegalGraphify y Open Legal Chile.
    """
    metadata = metadata or {}
    obra = metadata.get("obra", "Tratado de Doctrina Jurídica").strip()
    autor = metadata.get("autor", "Doctrina Nacional").strip()
    area = metadata.get("area", "Derecho Civil").strip()
    materia = metadata.get("materia", obra).strip()

    # 1. Limpieza estructural de saltos y guiones
    cleaned = clean_unwanted_hyphens_and_breaks(raw_text)

    # 2. Ortotipografía RAE/ASALE
    orto = apply_ortotipografia_rae_chile(cleaned)

    # 3. Estandarización de Citas
    standardized = standardize_legal_citations(orto)

    # 4. Segmentación en instituciones
    institutions = segment_institutions(standardized)

    # 5. Generación del encabezado canónico
    output_lines = [
        f"# {obra.upper()}",
        f"**Tratadista:** {autor} | **Área:** {area} | **Materia:** {materia}",
        "> 💡 *Base Doctrinal Canónica (Token-Optimized) para LegalGraphify y Open Legal Chile.*",
        "",
        "---",
        ""
    ]

    for inst in institutions:
        titulo = inst["titulo"]
        definicion = inst["definicion"]
        requisitos = inst["requisitos"]
        operativa = inst["operativa"]
        concordancias = inst["concordancias"]
        criterios = inst["criterios"]

        output_lines.append(f"## 🏛️ {titulo}")
        output_lines.append("**Definición Canónica:**  ")
        output_lines.append(definicion or "Institución jurídica del ordenamiento nacional.")
        output_lines.append("")

        if requisitos:
            output_lines.append("**Requisitos y Clasificación:**")
            output_lines.append(requisitos)
            output_lines.append("")

        output_lines.append("**Operativa Procesal Forense:**")
        if operativa:
            output_lines.append(operativa)
        else:
            output_lines.append("Se hace valer en juicio ordinario o especial respectivo mediante acción o excepción procesal oportuna conforme a las reglas generales.")
        output_lines.append("")

        concord_str = " ".join([f"`{c}`" if not c.startswith("`") else c for c in concordancias]) if concordancias else "`[BCN - Código Civil, Art. 1]`"
        output_lines.append(f"**Concordancias Legales:** {concord_str}  ")

        criterios_str = " ".join([f"`{c}`" if not c.startswith("`") else c for c in criterios]) if criterios else "`[CS - Jurisprudencia Unificada]`"
        output_lines.append(f"**Criterio Jurisprudencial Rector:** {criterios_str}")
        output_lines.append("")
        output_lines.append("---")
        output_lines.append("")

    return "\n".join(output_lines).strip() + "\n"
