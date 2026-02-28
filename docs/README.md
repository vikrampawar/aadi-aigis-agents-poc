# docs/

Business-facing documentation for the Aigis Agents platform.

## Structure

```
docs/
  SPECIFICATION.md              Main specification document (Mermaid diagrams inline)
  diagrams/
    01-aigis-overview.excalidraw        High-level agent mesh overview
    02-agent-01-pipeline.excalidraw     Agent 01 classification pipeline
    03-agent-04-waterfall.excalidraw    Agent 04 cash flow waterfall
    04-architecture.excalidraw          System architecture & integration
  README.md                     This file
```

## Conventions

- **Spec doc** lives at `docs/SPECIFICATION.md` — single source of truth for business audience
- **Mermaid diagrams** are inline in the spec (rendered by GitHub / Obsidian / VS Code)
- **Excalidraw diagrams** live in `docs/diagrams/` with numbered prefixes matching the spec sections
- Excalidraw files use `.excalidraw` extension (JSON format, openable at excalidraw.com)
- Diagram numbering: `NN-short-description.excalidraw` where NN matches the spec section or is sequential
- All diagrams use dark theme (dark background, light text, high-contrast fills)
