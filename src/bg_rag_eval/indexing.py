import re
from pathlib import Path

import yaml
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings


load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
SOURCES_PATH = ROOT / "data" / "rulebooks" / "sources.yaml"
INDEX_PATH = ROOT / "data" / "index" / "sea-salt-and-paper.json"

embedding = OpenAIEmbeddings(model="text-embedding-3-large")

HEADING = re.compile(r"^(#{1,6}) (.+)")

def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def chunk_markdown(md_path: str | Path, game: str) -> list[Document]:
    """Split a rulebook into one chunk per heading, keeping the heading path."""
    path: list[str] = []
    lines: list[str] = []
    chunks: list[Document] = []

    def flush() -> None:
        body = "\n".join(lines).strip()
        lines.clear()
        if not body:
            return
        section = " > ".join(path)
        chunks.append(Document(
            id=f"{game}/{slugify(' '.join(path[1:]))}",
            page_content=f"{section}\n\n{body}",
            metadata={"game": game, "section": section},
        ))

    for line in Path(md_path).read_text(encoding="utf-8").splitlines():
        if match := HEADING.match(line):
            flush()
            level = len(match[1])
            path[:] = path[: level - 1] + [match[2].strip()]
        else:
            lines.append(line)
    flush()
    return chunks


def chunk_rulebooks() -> list[Document]:
    """Chunk every rulebook listed in sources.yaml."""
    sources = yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8"))
    return [chunk for s in sources for chunk in chunk_markdown(ROOT / s["markdown"], s["game"])]


def get_index() -> InMemoryVectorStore:
    """Load the saved index, or embed all rulebooks and save it if none exists.

    Delete INDEX_PATH to rebuild after changing the Markdown, chunking or model.
    """
    if INDEX_PATH.exists():
        print(f"loaded index from {INDEX_PATH.relative_to(ROOT)}")
        return InMemoryVectorStore.load(str(INDEX_PATH), embedding)

    chunks = chunk_rulebooks()
    vector_store = InMemoryVectorStore(embedding)
    vector_store.add_documents(chunks)
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    vector_store.dump(str(INDEX_PATH))
    print(f"embedded {len(chunks)} chunks, saved to {INDEX_PATH.relative_to(ROOT)}")
    return vector_store


if __name__ == "__main__":
    get_index()