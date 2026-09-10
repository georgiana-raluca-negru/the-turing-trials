from __future__ import annotations

import httpx
from langchain_core.runnables import RunnableLambda

import legal_grounding.workflow as workflow_module
from legal_grounding.citations import format_source_label, validate_and_clean_citations
from legal_grounding.models import LawSource, LegalContextAssessment
from legal_grounding.retrieval import PortalLegislativSOAPRetriever, _build_search_plan
from legal_grounding.workflow import create_legal_grounding_workflow


TOKEN_RESPONSE = """<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body><GetTokenResponse xmlns="http://tempuri.org/"><GetTokenResult>test-token</GetTokenResult></GetTokenResponse></s:Body>
</s:Envelope>""".encode()

SEARCH_RESPONSE = """<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body><SearchResponse xmlns="http://tempuri.org/">
    <SearchResult xmlns:a="http://schemas.datacontract.org/2004/07/FreeWebService">
      <a:Legi>
        <a:DataVigoare>2010-07-15</a:DataVigoare>
        <a:Emitent>Parlamentul</a:Emitent>
        <a:Numar>134</a:Numar>
        <a:Publicatie>Monitorul Oficial nr. 485</a:Publicatie>
        <a:Text>Articolul 468 (1) Termenul de apel este de 30 de zile de la comunicarea hotărârii. (2) Excepțiile sunt prevăzute de lege.</a:Text>
        <a:TipAct>LEGE</a:TipAct>
        <a:Titlu>&#65279; Codul de procedură civilă EMITENT: Parlamentul</a:Titlu>
        <a:LinkHtml>http://legislatie.just.ro/Public/DetaliiDocument/140271</a:LinkHtml>
      </a:Legi>
    </SearchResult>
  </SearchResponse></s:Body>
</s:Envelope>""".encode()


def _source(*, text: str, article: str = "1") -> LawSource:
    return LawSource(
        id="LAW_1",
        law="Codul penal",
        act_type="COD",
        act_number="286/2009",
        article=article,
        paragraph="1",
        text=text,
        source_url="https://legislatie.just.ro/Public/DetaliiDocument/109855",
    )


def test_soap_retriever_gets_token_searches_and_splits_articles():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = request.content.decode("utf-8")
        return httpx.Response(200, content=TOKEN_RESPONSE if "GetToken" in body else SEARCH_RESPONSE)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    retriever = PortalLegislativSOAPRetriever(client=client, max_sources=8, max_context_chars=16000)

    sources = retriever.retrieve_laws("termen apel comunicarea hotărârii")

    assert len(requests) == 2
    assert "Action" not in requests[0].content.decode("utf-8")
    assert requests[0].headers["SOAPAction"] == '"http://tempuri.org/IFreeWebService/GetToken"'
    assert len(sources) == 2
    assert sources[0].article == "468"
    assert sources[0].law == "Codul de procedură civilă"
    assert {source.paragraph for source in sources} == {"1", "2"}
    assert all(source.source_url.startswith("https://legislatie.just.ro/") for source in sources)


def test_citation_validation_removes_only_unknown_markers():
    source = _source(text="Text oficial")
    result = validate_and_clean_citations("Regula [LAW_1], nu [LAW_9] sau [LAW_X].", [source])

    assert result.cited_ids == ["LAW_1"]
    assert result.invalid_ids == ["LAW_9", "LAW_X"]
    assert "[LAW_1]" in result.text
    assert "LAW_9" not in result.text
    assert "LAW_X" not in result.text
    assert format_source_label(source) == "COD nr. 286/2009, art. 1 alin. (1)"


def test_search_plan_routes_penal_code_to_official_number_and_year():
    plan = _build_search_plan("furt autovehicul cod penal 228 232")

    assert plan.text is None
    assert plan.number == "286"
    assert plan.year == "2009"
    assert plan.expected_title_terms == {"codul", "penal"}


class _ScriptedRetriever:
    def __init__(self):
        self.queries = []

    def retrieve_laws(self, query: str):
        self.queries.append(query)
        if len(self.queries) == 1:
            return [_source(text="Regula generală")]
        return [_source(text="Excepția", article="2")]


class _FakeLLM:
    def __init__(self, response):
        self.response = response
        self.calls = 0
        self.methods = []

    def with_structured_output(self, schema, method=None, include_raw=False):
        self.methods.append(method)

        def invoke(_prompt):
            self.calls += 1
            return {"raw": None, "parsed": self.response, "parsing_error": None}

        return RunnableLambda(invoke)


class _RepeatedSourceRetriever:
    def __init__(self):
        self.queries = []

    def retrieve_laws(self, query: str):
        self.queries.append(query)
        return [_source(text="Aceeași regulă")]


def test_grounding_uses_one_assessment_call_and_at_most_two_searches(monkeypatch):
    retriever = _ScriptedRetriever()
    llm = _FakeLLM(
        LegalContextAssessment(
            sufficient=False,
            missing_information=["excepția"],
            next_search_query="excepție termen apel",
        )
    )
    monkeypatch.setattr(workflow_module, "get_llm", lambda temperature=0.0: llm)
    graph = create_legal_grounding_workflow(
        retriever=retriever,
        max_search_rounds=2,
        max_assessment_calls=1,
    )

    result = graph.invoke(
        {
            "user_prompt": "Pot ataca hotărârea după 40 de zile?",
            "case_summary": {"crime": "", "charges": ["apel civil"]},
            "legal_search_queries": ["termen apel hotărâre civilă"],
            "system_events": [],
        }
    )

    context = result["legal_context"]
    assert retriever.queries == ["termen apel hotărâre civilă", "excepție termen apel"]
    assert llm.calls == 1
    assert llm.methods == ["function_calling"]
    assert context.search_rounds == 2
    assert context.assessment_calls == 1
    assert [source.id for source in context.sources] == ["LAW_1", "LAW_2"]
    assert context.stop_reason == "max_search_rounds"


def test_grounding_stops_when_refined_search_adds_no_sources(monkeypatch):
    retriever = _RepeatedSourceRetriever()
    llm = _FakeLLM(
        LegalContextAssessment(
            sufficient=False,
            missing_information=["excepția"],
            next_search_query="excepție distinctă",
        )
    )
    monkeypatch.setattr(workflow_module, "get_llm", lambda temperature=0.0: llm)
    graph = create_legal_grounding_workflow(
        retriever=retriever,
        max_search_rounds=3,
        max_assessment_calls=1,
    )

    result = graph.invoke(
        {
            "user_prompt": "Care este regula?",
            "case_summary": {"charges": ["apel civil"]},
            "legal_search_queries": ["regulă apel"],
            "system_events": [],
        }
    )

    context = result["legal_context"]
    assert retriever.queries == ["regulă apel", "excepție distinctă"]
    assert llm.calls == 1
    assert context.search_rounds == 2
    assert len(context.sources) == 1
    assert context.stop_reason == "no_new_results"
