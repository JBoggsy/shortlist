"""Research pipeline — general research about companies, salaries, industries."""

import logging

from ..micro_agents import ResearchQueryAgent, ResearchSynthesizerAgent
from ..pipeline_base import Pipeline, ToolResult
from ..prompts import RESEARCH_QUERY_PROMPT, RESEARCH_SYNTHESIZER_PROMPT
from ..schemas import ResearchParams

logger = logging.getLogger(__name__)


class ResearchPipeline(Pipeline):
    params_schema = ResearchParams

    def execute(self):
        p = self.params

        if not p.topic:
            yield self.text("What would you like me to research?")
            return

        # Step 1: Generate search queries
        company_context = ""
        if p.company:
            company_context = f"Company: {p.company}"
        if p.role:
            company_context += f"\nRole: {p.role}"

        system_prompt = RESEARCH_QUERY_PROMPT.format(
            topic=p.topic, research_type=p.research_type, company_context=company_context,
        )

        queries = []
        try:
            agent = ResearchQueryAgent(self.model)
            result = agent.run(system_prompt, f"Generate search queries for: {p.topic}")
            if hasattr(result, "queries"):
                queries = result.queries
        except Exception as e:
            logger.warning("Research query generation failed: %s", e)
            queries = [p.topic]

        if not queries:
            queries = [p.topic]

        yield self.text("\n\nResearching...")

        # Step 2: Execute web searches
        all_results = []
        for query in queries[:4]:
            query_str = query if isinstance(query, str) else str(query)
            tr = ToolResult()
            yield from self.exec_tool(
                "web_search", {"query": query_str, "num_results": 5}, tr,
            )
            if not tr.is_error:
                search_results = tr.data.get("results", [])
                all_results.extend(search_results)
                if tr.data.get("answer"):
                    all_results.append({"title": "AI Summary", "content": tr.data["answer"]})

        if not all_results:
            yield self.text("\n\nI couldn't find relevant information. Could you refine your research question?")
            return

        # Step 3: Synthesize results
        yield self.text("\n\n")
        profile = self.ctx.ensure_profile()

        results_text = ""
        for r in all_results[:15]:
            results_text += f"\n**{r.get('title', '?')}**"
            if r.get("url"):
                results_text += f" ({r['url']})"
            results_text += f"\n{r.get('content', '')[:300]}\n"

        system_prompt = RESEARCH_SYNTHESIZER_PROMPT.format(
            topic=p.topic, results=results_text, profile=profile,
        )

        agent = ResearchSynthesizerAgent(self.model)
        for chunk in agent.run(system_prompt, f"Synthesize research on: {p.topic}"):
            yield self.text(chunk)


def run(model, params, ctx):
    yield from ResearchPipeline(model, params, ctx).execute()
