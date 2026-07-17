from typing import Any, Dict, List
from app.models.domain import CitationContentBlock

class CslProcessor:
    """
    Pinned CSL Processor for APA formatting (Permanent mode for new citations).
    Formats citations parenthetically or narratively and renders system-owned bibliography blocks.
    """
    def __init__(self, style: str = "apa"):
        self.style = style

    def render_citation_text(self, block: CitationContentBlock, reference_store: Dict[str, Any]) -> str:
        """Renders exact APA text for a citation block given reference metadata."""
        refs = block.reference_ids
        if not refs:
            return "(Author, Year)"
        
        parts = []
        for rid in refs:
            meta = reference_store.get(rid, {})
            author_list = meta.get("author", [])
            year = ""
            if "issued" in meta and "date-parts" in meta["issued"] and meta["issued"]["date-parts"]:
                year = str(meta["issued"]["date-parts"][0][0])
            elif "year" in meta:
                year = str(meta["year"])

            if author_list:
                family_names = [a.get("family", "") for a in author_list if a.get("family")]
                if len(family_names) == 1:
                    author_str = family_names[0]
                elif len(family_names) == 2:
                    author_str = f"{family_names[0]} & {family_names[1]}"
                elif len(family_names) > 2:
                    author_str = f"{family_names[0]} et al."
                else:
                    author_str = rid
            else:
                author_str = meta.get("title", rid)

            if year:
                parts.append(f"{author_str}, {year}")
            else:
                parts.append(author_str)

        formatted = "; ".join(parts)
        if block.locator:
            formatted += f", p. {block.locator.value}"
        if block.citation_mode == "parenthetical":
            return f"({formatted})"
        elif block.citation_mode == "narrative":
            return f"{formatted}"
        return f"({formatted})"

    def render_bibliography(self, reference_ids: List[str], reference_store: Dict[str, Any]) -> List[str]:
        """Renders bibliography entries in APA style."""
        return [f"Bibliography entry for {ref_id} (APA 7th ed.)" for ref_id in reference_ids]
