"""
Aigis Agents — top-level CLI dispatcher.

Usage:
    python -m aigis_agents <command> [args]

Commands:
    init-buyer-profile    Run the interactive Q&A wizard to populate buyer_profile.md
    show-buyer-profile    Print the current buyer profile
    index-dk              Embed and index all domain_knowledge/ files for semantic search
                          (requires AIGIS_EMBEDDING_MODEL env var to be set)
    show-deal-context     Print the deal_context.md for a given deal ID
                          Usage: python -m aigis_agents show-deal-context <deal_id>
"""

from __future__ import annotations

import sys


def main() -> None:
    if len(sys.argv) < 2:
        _print_usage()
        sys.exit(0)

    command = sys.argv[1]

    if command in ("init-buyer-profile", "init_buyer_profile"):
        _cmd_init_buyer_profile()
    elif command in ("show-buyer-profile", "show_buyer_profile"):
        _cmd_show_buyer_profile()
    elif command in ("index-dk", "index_dk"):
        _cmd_index_dk()
    elif command in ("show-deal-context", "show_deal_context"):
        deal_id = sys.argv[2] if len(sys.argv) > 2 else None
        _cmd_show_deal_context(deal_id)
    else:
        print(f"Unknown command: {command!r}")
        _print_usage()
        sys.exit(1)


def _cmd_init_buyer_profile() -> None:
    from aigis_agents.mesh.buyer_profile_manager import BuyerProfileManager
    BuyerProfileManager().run_qa_wizard()


def _cmd_show_buyer_profile() -> None:
    from aigis_agents.mesh.buyer_profile_manager import BuyerProfileManager
    print(BuyerProfileManager().load_as_context())


def _cmd_index_dk() -> None:
    """Embed and index all DK files for semantic search."""
    import os
    from aigis_agents.mesh.semantic_dk_router import SemanticDKRouter

    model = os.getenv("AIGIS_EMBEDDING_MODEL", "")
    if not model:
        print(
            "Error: AIGIS_EMBEDDING_MODEL environment variable not set.\n"
            "Example: set AIGIS_EMBEDDING_MODEL=openai/text-embedding-3-small"
        )
        sys.exit(1)

    print(f"Indexing domain knowledge files with model: {model}")
    router = SemanticDKRouter(embedding_model=model)
    if not router.semantic_enabled:
        print(
            "Error: semantic layer failed to initialise. "
            "Check AIGIS_EMBEDDING_MODEL and relevant API key."
        )
        sys.exit(1)

    n = router.index_dk_files()
    print(f"Done. {n} chunks indexed.")


def _cmd_show_deal_context(deal_id: str | None) -> None:
    if not deal_id:
        print("Usage: python -m aigis_agents show-deal-context <deal_id>")
        sys.exit(1)
    from aigis_agents.mesh.deal_context import DealContextManager
    print(DealContextManager(deal_id=deal_id).load())


def _print_usage() -> None:
    print(__doc__)


if __name__ == "__main__":
    main()
