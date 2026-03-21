from backend.models.schemas import ResearchBrief, ReportDraft, ReportSection
from backend.services.ontology_service import OntologyService
from backend.services.simulation_service import SimulationService
from backend.subagents.critic import CriticSubagent
from backend.subagents.research import ResearchSubagent
from backend.subagents.sim import SimSubagent
from backend.subagents.writer import WriterSubagent


def test_fallback_ontology_has_expected_shape():
    payload = OntologyService._fallback_ontology("supply chain resilience semiconductor export control")

    assert "entity_types" in payload
    assert "edge_types" in payload
    assert payload["analysis_summary"]
    assert len(payload["entity_types"]) >= 3
    assert len(payload["edge_types"]) >= 2


def test_build_profiles_scores_entities_heuristically():
    entities = [
        {
            "uuid": "n1",
            "name": "Alpha Systems",
            "entity_type": "Organization",
            "summary": "Manufactures strategic chips and coordinates suppliers.",
            "degree": 8,
        },
        {
            "uuid": "n2",
            "name": "Trade Office",
            "entity_type": "Organization",
            "summary": "Reviews regulation and external pressure.",
            "degree": 3,
        },
    ]

    profiles = SimulationService._build_profiles(entities)

    assert len(profiles) == 2
    assert profiles[0].influence_score >= profiles[1].influence_score
    assert profiles[0].topics
    assert profiles[0].stance_hint == "Strategic"


def test_build_profiles_backfills_synthetic_agents_when_graph_is_short():
    entities = [
        {
            "uuid": "n1",
            "name": "Joao",
            "entity_type": "Partner",
            "summary": "Joao captou um novo cliente para contrato fixo.",
            "degree": 2,
        },
        {
            "uuid": "n2",
            "name": "Maria",
            "entity_type": "Partner",
            "summary": "Maria captou um novo cliente para servico avulso.",
            "degree": 2,
        },
    ]
    ontology = {
        "entity_types": [
            {"name": "Partner", "description": "Socio captador."},
            {"name": "Client", "description": "Cliente novo do escritorio."},
            {"name": "Contract", "description": "Contrato firmado com o cliente."},
            {"name": "CommissionRule", "description": "Regra da politica de comissionamento."},
            {"name": "CommissionPayment", "description": "Pagamento da comissao."},
        ]
    }

    profiles = SimulationService._build_profiles(
        entities,
        desired_count=5,
        ontology=ontology,
        requirement="commission policy smoke test",
    )

    assert len(profiles) == 5
    assert any(profile.entity_uuid.startswith("synthetic_") for profile in profiles)
    assert len({profile.agent_id for profile in profiles}) == 5


def test_active_agent_selection_penalizes_recent_reuse():
    profiles = SimulationService._build_profiles(
        [
            {
                "uuid": "n1",
                "name": "Alpha Systems",
                "entity_type": "Organization",
                "summary": "Semiconductor supplier focused on export markets and policy.",
                "degree": 8,
            },
            {
                "uuid": "n2",
                "name": "Beta Labs",
                "entity_type": "Organization",
                "summary": "Research-heavy lab following advanced packaging and domestic demand.",
                "degree": 7,
            },
            {
                "uuid": "n3",
                "name": "Gamma Media",
                "entity_type": "Topic",
                "summary": "Public narrative around policy response and investor sentiment.",
                "degree": 5,
            },
        ]
    )
    research = ResearchBrief(topic_map={"General": ["policy", "markets", "narrative"]})

    selected = SimulationService._select_active_agents(
        profiles=profiles,
        active_count=2,
        last_active_rounds={"1": 3},
        round_index=4,
        requirement="policy response and market pressure",
        research_brief=research,
    )

    assert len(selected) == 2
    assert all(profile.agent_id != 1 or profile.name != "Alpha Systems" for profile in selected[:1])


def test_analytics_from_events_counts_rounds_and_sentiment():
    analytics = SimulationService.analytics_from_events(
        [
            {"round_index": 1, "sentiment": "mixed", "event_type": "post", "actor_agent_id": 1},
            {"round_index": 2, "sentiment": "negative", "event_type": "reaction", "actor_agent_id": 1},
            {"round_index": 2, "sentiment": "negative", "event_type": "reply", "actor_agent_id": 2},
        ]
    )

    assert analytics["events_count"] == 3
    assert analytics["rounds_completed"] == 2
    assert analytics["dominant_sentiment"] == "negative"


def test_critic_fallback_requests_revision_when_requirement_missing():
    draft = ReportDraft(
        title="Test Report",
        summary="Summary",
        sections=[
            ReportSection(title="Situation", content="A short situation section."),
            ReportSection(title="Dynamics", content="A short dynamics section."),
        ],
        markdown_content="# Test Report\n\n## Situation\nA short situation section.",
    )

    critique = CriticSubagent._fallback("export controls", draft)

    assert critique.needs_revision is True
    assert critique.issues


def test_normalize_ontology_payload_accepts_entity_extraction_shape():
    payload = {
        "entities": [
            {
                "name": "Maria Santos",
                "entity_type": "Person",
                "description": "Founder of TechNova",
                "attributes": {"role": "Founder", "focus": "AI agriculture"},
            },
            {
                "name": "TechNova",
                "entity_type": "Organization",
                "description": "Brazilian startup",
                "attributes": {"sector": "AI", "region": "Amazon"},
            },
        ],
        "relationships": [
            {
                "source": "Maria Santos",
                "target": "TechNova",
                "relation_type": "founded",
                "description": "Founded the company",
            }
        ],
        "summary": "Startup ecosystem map.",
    }

    normalized = OntologyService._normalize_ontology_payload(
        payload,
        OntologyService._fallback_ontology("brazil startup ai agriculture"),
    )

    assert normalized["analysis_summary"] == "Startup ecosystem map."
    assert any(item["name"] == "Person" for item in normalized["entity_types"])
    assert any(item["name"] == "founded" for item in normalized["edge_types"])


def test_research_normalizer_handles_camel_case_keys():
    fallback = ResearchBrief(
        core_entities=[{"name": "Fallback", "entity_type": "Entity", "summary": "", "degree": 1}],
        key_facts=["fallback fact"],
        relationship_patterns=["fallback pattern"],
        risk_signals=["fallback risk"],
        topic_map={"General": ["fallback"]},
    )

    normalized = ResearchSubagent._normalize_payload(
        {
            "coreEntities": [{"entity": "TechNova", "type": "Organization", "description": "Startup", "degree": 4}],
            "keyFacts": ["New policy pressure"],
            "relationshipPatterns": ["TechNova influences the debate"],
            "riskSignals": ["Capital constraints"],
            "topicMap": {"Organizations": ["capital", "policy"]},
        },
        fallback.model_dump(),
    )

    assert normalized["core_entities"][0]["name"] == "TechNova"
    assert normalized["key_facts"] == ["New policy pressure"]
    assert normalized["topic_map"]["Organizations"] == ["capital", "policy"]


def test_sim_normalizer_accepts_actions_key():
    normalized = SimSubagent._normalize_payload(
        {
            "roundSummary": "A focused round.",
            "actions": [
                {
                    "action": "POST",
                    "actor": "1",
                    "message": "A new public stance emerged.",
                    "tone": "positive",
                    "impact": "0.7",
                }
            ],
        },
        SimSubagent._fallback_events(1, [], "test"),
    )

    assert normalized["summary"] == "A focused round."
    assert normalized["events"][0]["actor_agent_id"] == 1
    assert normalized["events"][0]["content"] == "A new public stance emerged."


def test_writer_normalizer_builds_markdown_when_missing():
    fallback = WriterSubagent._fallback("policy", {"core_entities": [], "risk_signals": []}, {"events_count": 0, "rounds_completed": 0, "dominant_sentiment": "neutral"}, "")

    normalized = WriterSubagent._normalize_payload(
        {
            "headline": "Policy Report",
            "executive_summary": "Summary line",
            "sections": {"Situation": "Current state", "Implications": "Likely next moves"},
        },
        fallback,
    )

    assert normalized["title"] == "Policy Report"
    assert "## Situation" in normalized["markdown_content"]
    assert len(normalized["sections"]) == 2


def test_critic_normalizer_coerces_string_bool_and_issue_string():
    fallback = CriticSubagent._fallback(
        "policy",
        ReportDraft(
            title="Title",
            summary="Summary",
            sections=[ReportSection(title="Situation", content="state"), ReportSection(title="Dynamics", content="moves"), ReportSection(title="Implications", content="effects")],
            markdown_content="# Title",
        ),
    )

    normalized = CriticSubagent._normalize_payload(
        {
            "needsRevision": "yes",
            "issues": "Missing policy linkage",
            "instructions": "Tie the conclusions back to policy.",
        },
        fallback,
    )

    assert normalized["needs_revision"] is True
    assert normalized["issues"] == ["Missing policy linkage"]
