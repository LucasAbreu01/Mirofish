from __future__ import annotations

import json

from app.models.schemas import EntityEdge, EntityNode, KnowledgeGraph
from app.utils.llm_client import llm_client
from app.utils.logger import get_logger

logger = get_logger("mirofish.entity_extractor")

_SYSTEM_PROMPT = """\
You extract entities and relationships from text. Be concise.

Rules:
- Extract 5-10 entities (people, organizations, concepts).
- Extract 5-15 relationships.
- Keep descriptions under 20 words each.
- Keep attributes minimal (2-3 key-value pairs max).
- Return ONLY valid JSON, no markdown.

Format:
{"entities":[{"name":"","entity_type":"","description":"","attributes":{}}],"relationships":[{"source":"","target":"","relation_type":"","description":""}]}
"""


async def extract_entities(document_text: str, scenario: str) -> KnowledgeGraph:
    """Analyse *document_text* with the LLM and return a :class:`KnowledgeGraph`.

    A single LLM call is made using the *heavy* model with JSON mode enabled.
    If the response cannot be parsed, an empty graph is returned.
    """
    user_prompt = (
        f"Scenario:\n{scenario}\n\n"
        f"Document:\n{document_text[:20000]}"
    )

    try:
        raw = await llm_client.achat(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            model="heavy",
            json_mode=True,
            max_tokens=4096,
        )

        data = json.loads(raw)
        entities = [
            EntityNode(
                name=e["name"],
                entity_type=e.get("entity_type", "Unknown"),
                description=e.get("description", ""),
                attributes=e.get("attributes", {}),
            )
            for e in data.get("entities", [])
        ]
        relationships = [
            EntityEdge(
                source=r["source"],
                target=r["target"],
                relation_type=r.get("relation_type", "related_to"),
                description=r.get("description", ""),
            )
            for r in data.get("relationships", [])
        ]

        logger.info(
            "Extracted %d entities and %d relationships",
            len(entities),
            len(relationships),
        )
        return KnowledgeGraph(entities=entities, relationships=relationships)

    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.error("Failed to parse entity extraction response: %s", exc)
        return KnowledgeGraph(entities=[], relationships=[])
    except Exception as exc:
        logger.error("Entity extraction LLM call failed: %s", exc)
        return KnowledgeGraph(entities=[], relationships=[])
