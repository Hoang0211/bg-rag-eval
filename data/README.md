# Data

The eval corpus is the English rulebook of **Sea Salt & Paper** and its two expansions, **Extra Pepper** and **Extra Salt**, published by Bombyx.

```
data/
├── rulebooks/          the 3 source PDFs (not committed) + sources.yaml
├── processed/          their Markdown conversions (not committed): what gets indexed
└── index/              saved vector store (not committed, rebuilt from processed/)
```

## Getting the rulebooks

The PDFs are copyrighted, so they are not in the repository. [`rulebooks/sources.yaml`](rulebooks/sources.yaml) lists, for each one, the publisher URL, the SHA-256 of the exact version used, and its Markdown file.

1. Download each `url` into `data/rulebooks/`, keeping the original filename.
2. Check the file matches the recorded `sha256` (`sha256sum data/rulebooks/*.pdf`). If it doesn't, the publisher has updated the rulebook and the Markdown no longer matches it.

## The Markdown files

The PDFs are not indexed directly. Their layouts (multi-panel leaflets, card boxes, icons, example pictures) don't extract cleanly, so each one was transcribed by hand to the `markdown` path in `sources.yaml`, following the rules below. Keep to them when editing these files: the chunker in [`indexing.py`](../src/bg_rag_eval/indexing.py) relies on this structure. **Every heading starts a new chunk**, and the chunk ID is built from the heading path.

### Structure

1. **Line 1 is the only `#` heading: the rulebook title**, exactly as `title` in `sources.yaml`. It is left out of chunk IDs.
2. **`##` for each section of the rulebook** (Components, Game Setup, Card Details, …), in reading order: panel by panel, left to right, top to bottom within a panel.
3. **`###` for subsections** (a numbered turn step, a card category, an event card), **`####` for individual cards** inside a category. Don't go deeper than `####`.
4. **Write all-caps banners in title case**: `END OF THE ROUND` → `## End of the Round`.
5. **Heading paths must be unique**: two headings with the same parent can't have the same text, or their chunks get the same ID.
6. **No empty headings**: every heading needs text under it or child headings.

### Text

7. **Copy rules text verbatim.** Don't paraphrase, summarize, merge or fix sentences, and keep typos as printed (e.g. Extra Pepper's `**Effect:** :`). The eval grades answers against this text.
8. **Keep emphasis that carries meaning**: bold keywords and card names (`**STOP**`, `**crab**`), italics for reminder text.
9. **Lists**: numbered steps as `1.`, `2.`, …; arrow (▶) bullets as `-`, nesting sub-bullets with two spaces.
10. **A note goes under the heading it applies to.** A note about a whole group goes directly under the group's heading, before its first child (e.g. the duo-cards note under `### Duo cards`, not under the last duo card).

### Things that are not plain text in the PDF

11. **Card counts** printed as badges (`x9`) go in the card heading: `#### Crab (x9)`.
12. **Icons that carry rules meaning** are written as a short bracketed description where they appear: `[Trophy with "+"]`.
13. **Example pictures** get their own heading, one level below the section they illustrate, named `Example: <topic>`. Captions are copied verbatim inside a `>` blockquote. Describe the pictured cards only as far as the picture shows them; if something is unclear, leave it vague rather than guess.
14. **Only add what the PDF shows.** Card counts and example descriptions must be readable from the PDF's graphics. Never add rules from other sources, FAQs or general knowledge.

### Left out

15. Decoration and marketing: cover art, logos, "learn to play" banners, QR codes, app-store badges, page numbers.
16. Credits are kept as a final `## Credits` section (someone may ask who designed the game).

### After editing

17. List the chunks without calling the embedding API and read through them:
    ```python
    from bg_rag_eval.indexing import chunk_rulebooks
    for c in chunk_rulebooks():
        print(c.id)
    ```
    Check that every chunk is one self-contained rule, card or example, and that all IDs are unique.
18. **Changing a heading changes its chunk ID**, so anything that refers to chunks by ID must be updated too. Delete `data/index/sea-salt-and-paper.json` after any change; the next run of `indexing.py` rebuilds it.
