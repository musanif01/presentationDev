import re
import logging
import httpx
from config import OLLAMA_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)

LEADING_JUNK_RE = re.compile(r"^[-*\u2022\u25CF\u25E6\u2023\u2043>\s]+")
NUMBERED_RE = re.compile(r"^\d+[\.\)]\s+")
TRAILING_JUNK_RE = re.compile(r"[\s,;\"']+$")


def clean_text(text: str) -> str:
    text = text.replace('\\"', '"')
    text = text.replace("\\'", "'")
    text = text.replace("\\n", "\n")
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    return text.strip()


def clean_line(line: str) -> str:
    line = LEADING_JUNK_RE.sub("", line)
    line = NUMBERED_RE.sub("", line)
    line = TRAILING_JUNK_RE.sub("", line)
    return line.strip()


def parse_items(raw: str, min_len: int = 4) -> list[str]:
    raw = clean_text(raw)
    lines = raw.split("\n")
    items = []
    started = False
    for line in lines:
        line = line.strip()
        if not line:
            if started:
                break
            continue
        if line.startswith("```"):
            continue
        is_item = bool(re.match(r"^[\s]*[-*\u2022\u25CF\u25E6\u2023\u2043>\d]", line))
        if is_item:
            started = True
            cleaned = clean_line(line)
            if cleaned and len(cleaned) >= min_len:
                items.append(cleaned)
        elif started:
            break
    if not items:
        for line in lines:
            line = clean_line(line)
            if line and len(line) > 10 and not line.lower().startswith(
                ("here", "below", "sure", "i'd", "the ", "this ", "these ", "note:")
            ):
                items.append(line)
                if len(items) >= 8:
                    break
    return items[:10]


async def query_ollama(prompt: str, temperature: float = 0.3) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "temperature": temperature,
    }
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(OLLAMA_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")
    except Exception as e:
        logger.error(f"Ollama query failed: {e}")
        return ""


async def suggest_headings(content: str) -> list[str]:
    prompt = (
        f"List 5-8 slide headings for a PowerPoint presentation based on this topic:\n"
        f"{content[:2000]}\n\n"
        "Put each heading on its own line starting with a dash. "
        "Do not add any extra text or numbering."
    )
    raw = await query_ollama(prompt)
    items = parse_items(raw)
    return items if items else ["Overview", "Key Points", "Details", "Summary", "Conclusion"]


async def generate_slide_content(heading: str, context: str) -> list[str]:
    prompt = (
        f"Write 3-5 bullet points for a presentation slide titled \"{heading}\".\n"
        f"Presentation context:\n{context[:1500]}\n\n"
        "Put each bullet on its own line starting with a dash. "
        "Keep each bullet short and clear."
    )
    raw = await query_ollama(prompt)
    items = parse_items(raw)
    return items if items else [f"Key point about {heading}"]


async def generate_search_queries(heading: str, bullets: list[str]) -> list[str]:
    text = "\n".join(bullets[:3])
    prompt = (
        f"Generate 2 short image search queries for a presentation slide.\n"
        f"Slide title: {heading}\n"
        f"Content:\n{text}\n\n"
        "Put each query on its own line starting with a dash. "
        "Example:\n- artificial intelligence concept\n- AI technology abstract"
    )
    raw = await query_ollama(prompt)
    items = parse_items(raw, min_len=3)
    return items[:3] if items else [heading]
