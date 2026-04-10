"""Concept researcher — uses Claude to extract and deepen concepts from signals."""

import json
import os
import re

import anthropic

MODEL = "claude-sonnet-4-6"


def _get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def _call_llm(system: str, user: str) -> str:
    client = _get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


def _parse_json_response(text: str) -> dict | list:
    """Extract JSON from LLM response, handling markdown code fences."""
    # Try to find JSON in code fences first
    match = re.search(r"```(?:json)?\s*\n([\s\S]*?)\n```", text)
    if match:
        return json.loads(match.group(1))
    # Try parsing the whole response
    return json.loads(text)


def extract_concepts(signals: list[dict]) -> list[dict]:
    """Take raw signals and extract the transferable concepts beneath them.

    Returns list of: {name, slug, cluster, depth, connections, description}
    """
    signal_texts = []
    for i, s in enumerate(signals):
        hint = f" (topics: {', '.join(s['topics_hint'])})" if s.get("topics_hint") else ""
        signal_texts.append(f"[{i + 1}] {s['text'][:1000]}{hint}")

    signals_block = "\n\n".join(signal_texts)

    system = """You are a concept extraction engine for a learning system.

Your job is to look at a set of bookmarks, notes, and highlighted passages and find
the TRANSFERABLE CONCEPTS beneath the surface content.

Rules:
- Don't extract topics (e.g. "machine learning") — extract the underlying mental model
  or principle (e.g. "gradient descent is hill-climbing with calculus").
- Think from first principles. What is the user actually interested in understanding?
- Find connections between seemingly unrelated signals.
- Each concept should be teachable in a 30-second card.
- Assign a cluster (broad theme) and depth level (1=fundamental, 2=intermediate, 3=advanced).
- Suggest connections between concepts you extract.

Return valid JSON — an array of objects with these fields:
- name: human-readable concept name
- slug: kebab-case identifier
- cluster: broad theme/cluster name
- depth: 1, 2, or 3
- connections: array of slugs this concept connects to (from the same batch)
- description: 1-2 sentence description of the transferable insight"""

    user = f"""Extract the transferable concepts from these signals:

{signals_block}

Return a JSON array of concept objects."""

    raw = _call_llm(system, user)
    concepts = _parse_json_response(raw)
    if isinstance(concepts, dict):
        concepts = concepts.get("concepts", [concepts])
    return concepts


def research_concept(concept: dict) -> dict:
    """Take a concept and produce deep teaching material at multiple levels.

    Returns: {concept, fundamentals, examples, probes, connections_discovered}
    """
    system = """You are a learning researcher preparing material for a microlearning card system.

Given a concept, produce deep teaching content at three levels:

1. FUNDAMENTALS — Explain the concept from first principles. No jargon.
   Ask: what is the simplest version of this idea? What would you need to know
   if you'd never encountered it before? Use concrete analogies.

2. EXAMPLES — 2-3 vivid, concrete examples that demonstrate the concept.
   At least one should be from an unexpected domain (cross-pollination).
   Each example should make the reader go "oh, THAT'S what this means."

3. PROBES — 2-3 questions that push the concept further. These should create
   productive discomfort — reveal edge cases, paradoxes, or deeper layers.
   The best probe makes the learner realize they don't understand as well as
   they thought.

Also discover connections — what other concepts does this one naturally link to?
Think across disciplines. The best connections are surprising.

Return valid JSON with these fields:
- concept: the concept slug
- fundamentals: string (the first-principles explanation, 2-3 paragraphs)
- examples: array of {title, body} objects
- probes: array of {question, hint} objects
- connections_discovered: array of {slug, name, relationship} objects"""

    user = f"""Research this concept deeply:

Name: {concept.get('name', '')}
Slug: {concept.get('slug', '')}
Cluster: {concept.get('cluster', '')}
Description: {concept.get('description', '')}
Known connections: {json.dumps(concept.get('connections', []))}

Produce teaching material at multiple depth levels."""

    raw = _call_llm(system, user)
    return _parse_json_response(raw)
