"""Card generator — turns research output into markdown+YAML card files and concept files."""

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml


CONTENT_DIR = Path(__file__).parent.parent / "content"


def generate_cards(research: dict, output_dir: str) -> list[str]:
    """Generate markdown card files from research output.

    Args:
        research: Output from research_concept() with keys:
            concept, fundamentals, examples, probes, connections_discovered
        output_dir: Directory to write card files to.

    Returns:
        List of file paths created.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    concept_slug = research.get("concept", "unknown")
    connections = [c["slug"] for c in research.get("connections_discovered", [])]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    created_files = []
    card_num = 1

    # Card 1: The Idea card (fundamentals)
    idea_path = _write_card(
        out,
        slug=concept_slug,
        num=card_num,
        title=_title_from_slug(concept_slug),
        topic=research.get("cluster", ""),
        depth=1,
        connections=connections,
        source={"type": "pipeline"},
        created=today,
        idea=research.get("fundamentals", ""),
        example=_format_example(research.get("examples", [{}])[0]) if research.get("examples") else "",
        probe=_format_probe(research.get("probes", [{}])[0]) if research.get("probes") else "",
    )
    created_files.append(str(idea_path))
    card_num += 1

    # Additional cards for remaining examples/probes (deeper depth)
    examples = research.get("examples", [])[1:]
    probes = research.get("probes", [])[1:]

    for i, (example, probe) in enumerate(_zip_longest_dicts(examples, probes)):
        card_path = _write_card(
            out,
            slug=concept_slug,
            num=card_num,
            title=example.get("title", f"{_title_from_slug(concept_slug)} — Angle {card_num}"),
            topic=research.get("cluster", ""),
            depth=min(card_num, 3),
            connections=connections,
            source={"type": "pipeline"},
            created=today,
            idea=research.get("fundamentals", "")[:200] + "..." if card_num > 1 else research.get("fundamentals", ""),
            example=_format_example(example) if example else "",
            probe=_format_probe(probe) if probe else "",
        )
        created_files.append(str(card_path))
        card_num += 1

    # Generate/update concept YAML
    concept_path = _write_concept_yaml(concept_slug, research, connections, today)
    created_files.append(str(concept_path))

    return created_files


def _write_card(
    out: Path, slug: str, num: int, title: str, topic: str,
    depth: int, connections: list, source: dict, created: str,
    idea: str, example: str, probe: str,
) -> Path:
    """Write a single card markdown file with YAML frontmatter."""
    filename = f"{slug}-{num:03d}.md"
    path = out / filename

    frontmatter = {
        "concept": slug,
        "title": title,
        "topic": topic,
        "depth": depth,
        "connections": connections,
        "source": source,
        "created": created,
    }

    lines = ["---"]
    lines.append(yaml.dump(frontmatter, default_flow_style=None, sort_keys=False).strip())
    lines.append("---")
    lines.append("")
    lines.append("## Idea")
    lines.append(idea.strip())
    lines.append("")
    lines.append("## Example")
    lines.append(example.strip())
    lines.append("")
    lines.append("## Probe")
    lines.append(probe.strip())
    lines.append("")

    path.write_text("\n".join(lines))
    return path


def _write_concept_yaml(slug: str, research: dict, connections: list, today: str) -> Path:
    """Write or update a concept YAML file in content/concepts/."""
    concepts_dir = CONTENT_DIR / "concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)
    path = concepts_dir / f"{slug}.yaml"

    # Merge with existing if present
    existing = {}
    if path.exists():
        existing = yaml.safe_load(path.read_text()) or {}

    data = {
        "name": existing.get("name") or _title_from_slug(slug),
        "slug": slug,
        "cluster": existing.get("cluster") or research.get("cluster", ""),
        "depth": existing.get("depth", 1),
        "description": research.get("fundamentals", "")[:300],
        "connections": [
            {"to": c["slug"], "weight": 1.0, "relationship": c.get("relationship", "")}
            for c in research.get("connections_discovered", [])
        ],
        "created": existing.get("created", today),
        "updated": today,
    }

    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    return path


def _title_from_slug(slug: str) -> str:
    """Convert kebab-case slug to title case."""
    return slug.replace("-", " ").title()


def _format_example(example: dict) -> str:
    if not example:
        return ""
    title = example.get("title", "")
    body = example.get("body", "")
    if title:
        return f"**{title}** — {body}"
    return body


def _format_probe(probe: dict) -> str:
    if not probe:
        return ""
    question = probe.get("question", "")
    hint = probe.get("hint", "")
    if hint:
        return f"{question}\n\n*Hint: {hint}*"
    return question


def _zip_longest_dicts(a: list, b: list) -> list[tuple]:
    """Zip two lists, padding the shorter one with empty dicts."""
    length = max(len(a), len(b))
    result = []
    for i in range(length):
        result.append((
            a[i] if i < len(a) else {},
            b[i] if i < len(b) else {},
        ))
    return result
