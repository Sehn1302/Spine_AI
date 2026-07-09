"""Study agent — thesis planning, structure, and academic guidance."""

from __future__ import annotations

import logging

from agents.base import AgentResult, BaseAgent


class StudyAgent(BaseAgent):
    name = "study"
    description = "Assist with thesis structure, chapters, and academic writing"

    def run(self, task: str, knowledge_context: str = "") -> AgentResult:
        query = task.strip()
        if not query:
            return AgentResult(self.name, f"No study query provided, {self.user_title}.")

        logging.info("Study agent query: %s", query)

        system = (
            f"You are the Study module of Spine, assisting {self.user_title} with academic work. "
            "Provide structured, formal guidance on thesis planning, chapter outlines, "
            "research methodology, citations, and data analytics concepts. "
            "Be practical and actionable."
        )

        user_message = query
        if knowledge_context:
            user_message += f"\n\nRelevant notes from {self.user_title}'s knowledge base:\n{knowledge_context}"

        summary = self._ask(system, user_message)
        return AgentResult(agent=self.name, summary=summary)
