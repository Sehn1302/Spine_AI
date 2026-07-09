"""Research agent — web search and summarization."""

from __future__ import annotations

import logging

from duckduckgo_search import DDGS

from agents.base import AgentResult, BaseAgent


class ResearchAgent(BaseAgent):
    name = "research"
    description = "Search the web and summarize findings"

    def run(self, task: str) -> AgentResult:
        query = task.strip()
        if not query:
            return AgentResult(self.name, f"No research query provided, {self.user_title}.")

        logging.info("Research agent query: %s", query)

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
        except Exception as exc:
            logging.error("Web search failed: %s", exc)
            return AgentResult(
                self.name,
                f"My apologies, {self.user_title}. Web search is unavailable at the moment.",
            )

        if not results:
            return AgentResult(
                self.name,
                f"No results found for '{query}', {self.user_title}.",
            )

        snippets = []
        for i, hit in enumerate(results, start=1):
            title = hit.get("title", "Untitled")
            body = hit.get("body", "")
            href = hit.get("href", "")
            snippets.append(f"{i}. {title}\n{body}\nSource: {href}")

        raw_context = "\n\n".join(snippets)
        system = (
            f"You are the Research module of Spine. Summarize findings formally for {self.user_title}. "
            "Be concise, cite sources by number, and note uncertainty where appropriate."
        )
        summary = self._ask(
            system,
            f"Research query: {query}\n\nSearch results:\n{raw_context}",
        )

        return AgentResult(
            agent=self.name,
            summary=summary,
            details=raw_context,
        )
