from __future__ import annotations

import os
import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

import httpx

from legal_grounding.models import LawSource


SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
SERVICE_NS = "http://tempuri.org/"
DATA_NS = "http://schemas.datacontract.org/2004/07/FreeWebService"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

DEFAULT_ENDPOINT = "https://legislatie.just.ro/apiws/FreeWebService.svc/SOAP"
DEFAULT_SOURCE_URL = "https://legislatie.just.ro/Public/RezultateCautare"
MAX_EXCERPT_CHARS = 4_000

_ARTICLE_RE = re.compile(r"\b(?:Articolul|ART\.)\s+([0-9]+(?:\^[0-9]+)?)", re.IGNORECASE)
_PARAGRAPH_RE = re.compile(r"(?<!\w)\(([0-9]+(?:\^[0-9]+)?)\)\s*")
_DOCUMENT_ID_RE = re.compile(r"/DetaliiDocument(?:Afis)?/(\d+)", re.IGNORECASE)
_STOP_WORDS = {
    "a", "ai", "ale", "al", "cu", "de", "din", "este", "in", "la", "o", "pe", "pentru",
    "prin", "privind", "sa", "si", "sau", "un", "unei", "unui",
}


class LawRetriever(Protocol):
    def retrieve_laws(self, query: str) -> list[LawSource]:
        ...


@dataclass(frozen=True)
class _PortalLaw:
    title: str
    text: str
    act_type: str | None
    number: str | None
    issuer: str | None
    publication: str | None
    effective_date: str | None
    source_url: str


class PortalLegislativSOAPRetriever:
    """Minimal client for the official Portal Legislativ WCF/SOAP service."""

    def __init__(
        self,
        *,
        endpoint: str | None = None,
        timeout_seconds: float | None = None,
        results_per_page: int = 10,
        max_sources: int | None = None,
        max_context_chars: int | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.endpoint = endpoint or os.getenv("PORTAL_LEGISLATIV_URL", DEFAULT_ENDPOINT)
        self.timeout_seconds = timeout_seconds or float(os.getenv("LEGAL_HTTP_TIMEOUT_SECONDS", "15"))
        self.results_per_page = results_per_page
        self.max_sources = max_sources or int(os.getenv("LEGAL_MAX_SOURCES", "8"))
        self.max_context_chars = max_context_chars or int(os.getenv("LEGAL_MAX_CONTEXT_CHARS", "16000"))
        self._client = client
        self._token: str | None = None

    def retrieve_laws(self, query: str) -> list[LawSource]:
        normalized_query = " ".join(query.split()).strip()
        if not normalized_query:
            return []
        token = self._token or self._get_token()
        self._token = token
        response_root = self._search(query=normalized_query, token=token)
        portal_laws = _parse_search_response(response_root)
        excerpts = [excerpt for law in portal_laws for excerpt in _split_law_into_excerpts(law)]
        return rank_and_limit_sources(
            excerpts,
            normalized_query,
            max_sources=self.max_sources,
            max_context_chars=self.max_context_chars,
        )

    def _get_token(self) -> str:
        operation = ET.Element(f"{{{SERVICE_NS}}}GetToken")
        root = self._post_soap("GetToken", operation)
        token = _find_text(root, "GetTokenResult")
        if not token:
            raise RuntimeError("Portal Legislativ GetToken returned no token.")
        return token

    def _search(self, *, query: str, token: str) -> ET.Element:
        operation = ET.Element(f"{{{SERVICE_NS}}}Search")
        search_model = ET.SubElement(operation, f"{{{SERVICE_NS}}}SearchModel")
        ET.SubElement(search_model, f"{{{DATA_NS}}}NumarPagina").text = "0"
        ET.SubElement(search_model, f"{{{DATA_NS}}}RezultatePagina").text = str(self.results_per_page)
        for name in ("SearchAn", "SearchNumar"):
            node = ET.SubElement(search_model, f"{{{DATA_NS}}}{name}")
            node.set(f"{{{XSI_NS}}}nil", "true")
        ET.SubElement(search_model, f"{{{DATA_NS}}}SearchText").text = query
        title_node = ET.SubElement(search_model, f"{{{DATA_NS}}}SearchTitlu")
        title_node.set(f"{{{XSI_NS}}}nil", "true")
        ET.SubElement(operation, f"{{{SERVICE_NS}}}tokenKey").text = token
        return self._post_soap("Search", operation)

    def _post_soap(self, action_name: str, operation: ET.Element) -> ET.Element:
        envelope = ET.Element(f"{{{SOAP_NS}}}Envelope")
        body = ET.SubElement(envelope, f"{{{SOAP_NS}}}Body")
        body.append(operation)
        payload = ET.tostring(envelope, encoding="utf-8", xml_declaration=True)
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"{SERVICE_NS}IFreeWebService/{action_name}"',
            "User-Agent": "The-Turing-Trials/1.0 (+official-legislation-grounding)",
        }
        if self._client is not None:
            response = self._client.post(self.endpoint, content=payload, headers=headers)
        else:
            response = httpx.post(
                self.endpoint,
                content=payload,
                headers=headers,
                timeout=self.timeout_seconds,
                follow_redirects=True,
            )
        response.raise_for_status()
        root = ET.fromstring(response.content)
        fault = next((node for node in root.iter() if _local_name(node.tag) == "Fault"), None)
        if fault is not None:
            fault_text = " ".join(text.strip() for text in fault.itertext() if text.strip())
            raise RuntimeError(f"Portal Legislativ SOAP fault: {fault_text}")
        return root


def retrieve_laws(query: str, *, retriever: LawRetriever | None = None) -> list[LawSource]:
    return (retriever or PortalLegislativSOAPRetriever()).retrieve_laws(query)


def _parse_search_response(root: ET.Element) -> list[_PortalLaw]:
    laws: list[_PortalLaw] = []
    for node in root.iter():
        if _local_name(node.tag) != "Legi":
            continue
        values = {_local_name(child.tag): _clean_text(child.text or "") for child in node}
        title = _clean_title(values.get("Titlu")) or _fallback_title(values)
        text = values.get("Text", "")
        if not title or not text:
            continue
        source_url = _official_source_url(values.get("LinkHtml"))
        laws.append(
            _PortalLaw(
                title=title,
                text=_clean_text(text),
                act_type=values.get("TipAct") or None,
                number=values.get("Numar") or None,
                issuer=values.get("Emitent") or None,
                publication=values.get("Publicatie") or None,
                effective_date=values.get("DataVigoare") or None,
                source_url=source_url,
            )
        )
    return laws


def _split_law_into_excerpts(law: _PortalLaw) -> list[LawSource]:
    matches = list(_ARTICLE_RE.finditer(law.text))
    if not matches:
        return _to_sources(law, text=law.text)

    excerpts: list[LawSource] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(law.text)
        article_text = law.text[match.start():end].strip()
        article = match.group(1)
        paragraph_matches = list(_PARAGRAPH_RE.finditer(article_text))
        if not paragraph_matches:
            excerpts.extend(_to_sources(law, text=article_text, article=article))
            continue
        prefix = article_text[:paragraph_matches[0].start()].strip()
        for paragraph_index, paragraph_match in enumerate(paragraph_matches):
            paragraph_end = (
                paragraph_matches[paragraph_index + 1].start()
                if paragraph_index + 1 < len(paragraph_matches)
                else len(article_text)
            )
            paragraph_text = article_text[paragraph_match.start():paragraph_end].strip()
            if prefix:
                paragraph_text = f"{prefix} {paragraph_text}"
            excerpts.extend(
                _to_sources(
                    law,
                    text=paragraph_text,
                    article=article,
                    paragraph=paragraph_match.group(1),
                )
            )
    return excerpts


def rank_and_limit_sources(
    sources: list[LawSource],
    query: str,
    *,
    max_sources: int,
    max_context_chars: int,
) -> list[LawSource]:
    query_normalized = _normalize(query)
    query_tokens = set(_tokenize(query))
    ranked: list[tuple[float, LawSource]] = []
    for source in sources:
        title_normalized = _normalize(source.law)
        text_normalized = _normalize(source.text)
        title_tokens = set(_tokenize(source.law))
        text_tokens = set(_tokenize(source.text))
        score = 4.0 * len(query_tokens & title_tokens) + len(query_tokens & text_tokens)
        if query_normalized and query_normalized in title_normalized:
            score += 12.0
        elif query_normalized and query_normalized in text_normalized:
            score += 6.0
        ranked.append((score, source.model_copy(update={"relevance_score": score})))
    ranked.sort(key=lambda item: (-item[0], len(item[1].text)))

    selected: list[LawSource] = []
    used_chars = 0
    seen = set()
    for _, source in ranked:
        key = (source.source_url, source.article, source.paragraph, _normalize(source.text))
        if key in seen:
            continue
        source_size = len(source.text)
        if used_chars + source_size > max_context_chars:
            continue
        selected.append(source.model_copy(update={"id": f"LAW_{len(selected) + 1}"}))
        seen.add(key)
        used_chars += source_size
        if len(selected) >= max_sources or used_chars >= max_context_chars:
            break
    return selected


def _to_source(
    law: _PortalLaw,
    *,
    text: str,
    article: str | None = None,
    paragraph: str | None = None,
) -> LawSource:
    document_match = _DOCUMENT_ID_RE.search(law.source_url)
    return LawSource(
        law=law.title,
        document_id=document_match.group(1) if document_match else None,
        act_type=law.act_type,
        act_number=law.number,
        article=article,
        paragraph=paragraph,
        text=text,
        issuer=law.issuer,
        publication=law.publication,
        effective_date=law.effective_date,
        source_url=law.source_url,
    )


def _to_sources(
    law: _PortalLaw,
    *,
    text: str,
    article: str | None = None,
    paragraph: str | None = None,
) -> list[LawSource]:
    return [
        _to_source(
            law,
            text=chunk,
            article=article,
            paragraph=paragraph,
        )
        for chunk in _chunk_text(text, max_chars=MAX_EXCERPT_CHARS)
    ]


def _official_source_url(value: str | None) -> str:
    if not value:
        return DEFAULT_SOURCE_URL
    candidate = value.strip().replace("http://legislatie.just.ro", "https://legislatie.just.ro", 1)
    parsed = urlparse(candidate)
    if parsed.hostname and parsed.hostname.lower() == "legislatie.just.ro":
        return candidate
    return DEFAULT_SOURCE_URL


def _fallback_title(values: dict[str, str]) -> str:
    return " ".join(part for part in (values.get("TipAct"), values.get("Numar")) if part)


def _find_text(root: ET.Element, local_name: str) -> str | None:
    for node in root.iter():
        if _local_name(node.tag) == local_name and node.text and node.text.strip():
            return node.text.strip()
    return None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\ufeff", " ").replace("\u200b", " ")).strip()


def _clean_title(value: str | None) -> str:
    if not value:
        return ""
    title = re.split(r"\b(?:EMITENT|PUBLICAT\s+\w+)\s*:", value, maxsplit=1, flags=re.IGNORECASE)[0]
    return _clean_text(title)


def _chunk_text(text: str, *, max_chars: int) -> list[str]:
    remaining = _clean_text(text)
    chunks: list[str] = []
    while len(remaining) > max_chars:
        split_at = remaining.rfind(" ", 0, max_chars + 1)
        if split_at <= 0:
            split_at = max_chars
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def _tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", _normalize(text))
        if len(token) > 1 and token not in _STOP_WORDS
    ]
