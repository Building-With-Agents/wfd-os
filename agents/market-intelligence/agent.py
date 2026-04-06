"""
Market Intelligence Agent — Waifinder / WFD OS
Answers labor market questions using Lightcast data from Dataverse.
First deployment: Workforce Solutions Borderplex (El Paso, TX)
"""
import os
import json
import sys
sys.path.insert(0, os.path.dirname(__file__))

import anthropic
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"), override=True)

from tools.skills import get_top_skills, compare_skills_to_market
from tools.jobs import search_jobs, get_skills_from_jobs
from tools.wages import get_wage_trends
from tools.employers import get_top_employers
from tools.summary import get_market_summary
from tools.semantic_skills import find_related_skills, find_skills_for_concept

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are the Market Intelligence Agent for Waifinder, a workforce development
platform built by Computing for All (CFA).

Your job is to answer labor market questions using real job posting and skills demand data
from Lightcast — a leading labor market analytics provider. Data is current as of Q3 2024
(Aug 2023 – Jul 2024 timeframe, Washington state focus).

You serve workforce boards, employers, colleges, and career services staff who need
real answers, not generalities. Be specific and quantitative. Always cite data.

Current deployment: Workforce Solutions Borderplex — serving the El Paso, TX /
Ciudad Juárez border region workforce development system.

Tools available:
- get_market_summary: High-level market snapshot (start here for overview questions)
- get_top_skills: Skills ranked by employer demand, with supply/demand gap analysis
- search_jobs: Search job postings by title, skill, company, or location
- get_skills_from_jobs: Extract most common skills across job postings
- get_wage_trends: Monthly advertised wage data and trend analysis
- get_top_employers: Companies ranked by hiring volume
- compare_skills_to_market: Match a person's skills against market demand
- find_related_skills: Semantic search — find skills related to a given skill using vector embeddings (5,061 skills, 1536 dimensions)
- find_skills_for_concept: Semantic search — find skills for any concept or role description (generates embedding via AI)

When answering:
- Lead with numbers ("Based on 2,670 Lightcast job postings...")
- Flag when data may be dated (Q3 2024 dataset)
- If a question needs data you don't have, say so clearly
- Format lists and comparisons as clean, readable output"""

TOOLS = [
    {
        "name": "get_market_summary",
        "description": "Returns a high-level labor market snapshot: total postings, top skills, top employers, median wage, fastest growing skill, and biggest supply/demand gap. Use this for overview or 'give me a picture of the market' questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": "Region to analyze. Default: 'Washington'",
                    "default": "Washington",
                }
            },
        },
    },
    {
        "name": "get_top_skills",
        "description": "Returns skills ranked by employer demand (posting count). Includes supply/demand gap (positive = shortage), growth trend, and projected growth. Use for 'what skills are in demand?' or 'what skills are employers looking for?' questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "region": {"type": "string", "default": "Washington"},
                "experience_level": {
                    "type": "string",
                    "description": "Experience filter. Use '0 years - 3 years' for entry-level.",
                    "default": "0 years - 3 years",
                },
                "limit": {"type": "integer", "default": 20},
                "skill_category": {
                    "type": "string",
                    "description": "Filter by category: 'Top Software Skills', 'Top Specialized Skills', etc.",
                },
                "growth_filter": {
                    "type": "string",
                    "description": "Filter by growth trend: 'Rapidly Growing' or 'Lagging'",
                },
            },
        },
    },
    {
        "name": "search_jobs",
        "description": "Search Lightcast job postings by title, required skills, company, or location. Returns job summaries with skills lists. Use for 'show me jobs for X' or 'what do X jobs require?' questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term for job title or description"},
                "skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of required skills to filter by",
                },
                "company": {"type": "string"},
                "location": {"type": "string"},
                "onet_code": {"type": "string", "description": "O*NET occupation code"},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "get_skills_from_jobs",
        "description": "Extracts the most common skills across job postings, optionally filtered to specific job titles. Use for 'what skills do X roles require?' questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_titles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Job titles to filter by (e.g. ['QA Tester', 'Quality Assurance'])",
                },
                "limit": {"type": "integer", "default": 25},
            },
        },
    },
    {
        "name": "get_wage_trends",
        "description": "Returns monthly advertised wage data including median, min, max, annual equivalent, and trend direction. Use for 'what does this role pay?' questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "region": {"type": "string", "default": "Washington"},
                "experience_level": {"type": "string", "default": "0 years - 3 years"},
            },
        },
    },
    {
        "name": "get_top_employers",
        "description": "Returns companies ranked by job posting volume with median posting duration. Use for 'who is hiring?' or 'which companies post the most jobs?' questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "region": {"type": "string", "default": "Washington"},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "compare_skills_to_market",
        "description": "Takes a list of skills and compares them against market demand. Returns matched skills with demand data, missing high-demand skills, and an alignment score. Use for 'how do my skills match the market?' questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of skills to compare (e.g. ['Python', 'SQL', 'Excel'])",
                },
                "region": {"type": "string", "default": "Washington"},
            },
            "required": ["skills"],
        },
    },
    {
        "name": "find_related_skills",
        "description": "Finds skills semantically related to a given skill using vector embeddings (1536-dim, 5,061 skills). Returns ranked results with cosine similarity scores. Use for 'what skills are related to X?', 'what else should someone who knows X learn?', or 'what skills are similar to X?' questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "skill": {
                    "type": "string",
                    "description": "The skill to find related skills for (e.g. 'Python', 'Cybersecurity', 'Agile')",
                },
                "limit": {"type": "integer", "default": 15},
            },
            "required": ["skill"],
        },
    },
    {
        "name": "find_skills_for_concept",
        "description": "Finds skills related to an arbitrary concept or job description using AI-generated embeddings. Use for broader queries like 'what skills do I need for cloud engineering?', 'skills for healthcare data analysis', or 'what should a junior DevOps engineer know?'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "concept": {
                    "type": "string",
                    "description": "A concept, role, or description to find relevant skills for",
                },
                "limit": {"type": "integer", "default": 15},
            },
            "required": ["concept"],
        },
    },
]

TOOL_MAP = {
    "get_market_summary": get_market_summary,
    "get_top_skills": get_top_skills,
    "search_jobs": search_jobs,
    "get_skills_from_jobs": get_skills_from_jobs,
    "get_wage_trends": get_wage_trends,
    "get_top_employers": get_top_employers,
    "compare_skills_to_market": compare_skills_to_market,
    "find_related_skills": find_related_skills,
    "find_skills_for_concept": find_skills_for_concept,
}


def run_agent(user_message: str, verbose: bool = False) -> str:
    """Run the Market Intelligence Agent on a single question."""
    messages = [{"role": "user", "content": user_message}]

    while True:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Collect text blocks for streaming-style output
        text_blocks = [b.text for b in response.content if b.type == "text"]
        tool_uses = [b for b in response.content if b.type == "tool_use"]

        if verbose and text_blocks:
            print("\n[Agent thinking]:", " ".join(text_blocks))

        # If no tool calls, we're done
        if response.stop_reason == "end_turn" or not tool_uses:
            return " ".join(text_blocks) if text_blocks else ""

        # Execute tool calls
        tool_results = []
        for tool_use in tool_uses:
            tool_name = tool_use.name
            tool_input = tool_use.input

            if verbose:
                print(f"\n[Tool call]: {tool_name}({json.dumps(tool_input, indent=2)})")

            try:
                fn = TOOL_MAP[tool_name]
                result = fn(**tool_input)
                result_str = json.dumps(result, default=str)
                if verbose:
                    print(f"[Tool result preview]: {result_str[:300]}...")
            except Exception as e:
                result_str = json.dumps({"error": str(e)})
                if verbose:
                    print(f"[Tool error]: {e}")

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result_str,
            })

        # Add assistant response and tool results to message history
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})


def chat():
    """Interactive chat loop for the Market Intelligence Agent."""
    print("\n" + "="*60)
    print("  Waifinder — Market Intelligence Agent")
    print("  Powered by Lightcast Q3 2024 data")
    print("  Type 'quit' to exit")
    print("="*60 + "\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye.")
            break
        if not user_input:
            continue

        print("\nAgent: ", end="", flush=True)
        response = run_agent(user_input)
        print(response)
        print()


if __name__ == "__main__":
    chat()
