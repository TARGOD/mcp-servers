import arxiv
import json
import os
from typing import List
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

PAPER_DIR = "papers"

# Initialize MCP server
server = Server("arxiv-research")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="search_papers",
            description="Search for papers on arXiv based on a topic and store their information",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The topic to search for"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to retrieve",
                        "default": 5
                    }
                },
                "required": ["topic"]
            }
        ),
        types.Tool(
            name="extract_info",
            description="Search for information about a specific paper across all topic directories",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "The ID of the paper to look for"
                    }
                },
                "required": ["paper_id"]
            }
        ),
        types.Tool(
            name="generate_summary_prompt",
            description="Generate a detailed prompt to summarize arXiv papers on a given topic",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Research topic"
                    },
                    "num_papers": {
                        "type": "integer",
                        "description": "Number of papers to search for",
                        "default": 5
                    }
                },
                "required": ["topic"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
        name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution."""

    if name == "search_papers":
        topic = arguments.get("topic", "")
        max_results = arguments.get("max_results", 5)

        client = arxiv.Client()
        search = arxiv.Search(
            query=topic,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )

        papers = client.results(search)

        path = os.path.join(PAPER_DIR, topic.lower().replace(" ", "_"))
        os.makedirs(path, exist_ok=True)
        file_path = os.path.join(path, "papers_info.json")

        try:
            with open(file_path, "r") as json_file:
                papers_info = json.load(json_file)
        except (FileNotFoundError, json.JSONDecodeError):
            papers_info = {}

        paper_ids = []
        for paper in papers:
            paper_id = paper.get_short_id()
            paper_ids.append(paper_id)
            paper_info = {
                'title': paper.title,
                'authors': [author.name for author in paper.authors],
                'summary': paper.summary,
                'pdf_url': paper.pdf_url,
                'published': str(paper.published.date())
            }
            papers_info[paper_id] = paper_info

        with open(file_path, "w") as json_file:
            json.dump(papers_info, json_file, indent=2)

        result = {
            "paper_ids": paper_ids,
            "count": len(paper_ids),
            "saved_to": file_path
        }

        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]

    elif name == "extract_info":
        paper_id = arguments.get("paper_id", "")

        if not os.path.exists(PAPER_DIR):
            return [types.TextContent(
                type="text",
                text="No papers directory found. Please search for papers first."
            )]

        for item in os.listdir(PAPER_DIR):
            item_path = os.path.join(PAPER_DIR, item)
            file_path = os.path.join(item_path, "papers_info.json")
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r") as json_file:
                        papers_info = json.load(json_file)
                        if paper_id in papers_info:
                            return [types.TextContent(
                                type="text",
                                text=json.dumps(papers_info[paper_id], indent=2)
                            )]
                except (FileNotFoundError, json.JSONDecodeError):
                    continue

        return [types.TextContent(
            type="text",
            text=f"No saved information found for paper ID: {paper_id}."
        )]

    elif name == "generate_summary_prompt":
        topic = arguments.get("topic", "")
        num_papers = arguments.get("num_papers", 5)

        prompt = f"""Search for {num_papers} academic papers about '{topic}' using the `search_papers` tool. Follow these instructions:

1. Use the `search_papers(topic="{topic}", max_results={num_papers})` tool to search for papers.
2. For each paper found, extract and organize the following information:
   - Paper title
   - Authors
   - Publication date
   - Brief summary of the key findings
   - Main contributions or innovations
   - Methodologies used
   - Relevance to the topic '{topic}'

3. Provide a comprehensive summary including:
   - Overview of current research in '{topic}'
   - Common themes and trends across the papers
   - Key research gaps or areas for future investigation
   - Most impactful or influential papers in this area

4. Format your response clearly with headings and bullet points for readability."""

        return [types.TextContent(type="text", text=prompt)]

    else:
        raise ValueError(f"Unknown tool: {name}")


async def run():
    """Run the server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="arxiv-research",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
