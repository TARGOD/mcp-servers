import asyncio
import json
import subprocess
import sys
from typing import Dict, List, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import google.generativeai as genai
from contextlib import AsyncExitStack

GEMINI_API_KEY = 'AIzaSyCgWYGWiJ07fsIUOIMSdZZjAlUAm2hE4v0'
genai.configure(api_key=GEMINI_API_KEY)


class GeminiMCPChatbot:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.exit_stack = AsyncExitStack()
        self.sessions: List[ClientSession] = []
        self.available_tools = {}
        self.tool_to_session: Dict[str, ClientSession] = {}

    async def connect_to_server(self, server_name: str, config: dict):
        try:
            server_params = StdioServerParameters(**config)
            read, write = await self.exit_stack.enter_async_context(stdio_client(server_params))
            session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()

            self.sessions.append(session)
            response = await session.list_tools()

            print(f"🔌 Connected to {server_name}, Tools: {[tool.name for tool in response.tools]}")
            for tool in response.tools:
                self.available_tools[tool.name] = tool
                self.tool_to_session[tool.name] = session
        except Exception as e:
            print(f"❌ Failed to connect to {server_name}: {e}")

    async def connect_to_servers(self, config_path="server_config.json"):
        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)

            servers = config_data.get("mcpServers", {})
            for name, cfg in servers.items():
                await self.connect_to_server(name, cfg)
        except Exception as e:
            print(f"❌ Could not load server config: {e}")
            sys.exit(1)

    def create_tools_context(self) -> str:
        context = "Available tools:\n"
        for name, tool in self.available_tools.items():
            context += f"- {name}: {tool.description}\n"
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                params = tool.inputSchema.get("properties", {})
                context += "  Parameters: " + ", ".join([f"{k} ({v.get('type', 'unknown')})" for k, v in params.items()]) + "\n"
        return context

    async def process_with_ai(self, user_input: str, history: List[str]):
        tools_context = self.create_tools_context()

        analysis_prompt = f"""
You are a smart chatbot with access to tools via APIs.
- Reply directly if tools are unnecessary.
- Use tools if needed, based on the user's intent.
- Ask for missing input if required.

{tools_context}

User message: "{user_input}"
Recent history: {history[-3:] if history else 'None'}

Reply in JSON format:
{{
    "intent": "brief user goal",
    "actions": [
        {{
            "tool": "tool_name",
            "parameters": {{"param1": "value"}},
            "reasoning": "why this tool helps"
        }}
    ],
    "needs_user_input": {{
        "param": "What question to ask"
    }}
}}
"""

        try:
            print("🤔 Gemini Thinking...\n")
            response = self.model.generate_content(analysis_prompt)
            raw_text = response.text.strip()

            print(f"📥 Gemini Response:\n{raw_text}\n")
            start, end = raw_text.find('{'), raw_text.rfind('}') + 1
            decision = json.loads(raw_text[start:end])

            if decision.get("needs_user_input"):
                for param, question in decision["needs_user_input"].items():
                    answer = input(f"❓ {question}: ").strip()
                    user_input += f" ({param}: {answer})"
                    await self.process_with_ai(user_input, history)
                return

            actions = decision.get("actions", [])
            if not actions:
                direct_reply = self.model.generate_content(user_input).text.strip()
                print(f"🤖 Gemini: {direct_reply}")
                return

            for action in actions:
                tool = action["tool"]
                params = action.get("parameters", {})
                reason = action.get("reasoning", "")

                session = self.tool_to_session.get(tool)
                if not session:
                    print(f"⚠️ Tool '{tool}' not found.")
                    continue

                print(f"🔧 Executing '{tool}' - {reason}")
                await self.execute_tool(session, tool, params)

            history.append(f"User: {user_input}")
            history.append(f"AI used tools: {[a['tool'] for a in actions]}")

        except Exception as e:
            print(f"❌ Gemini error: {e}")

    async def execute_tool(self, session: ClientSession, tool_name: str, params: Dict[str, Any]):
        try:
            print(f"⏳ Tool '{tool_name}' with params: {params}")
            result = await session.call_tool(tool_name, params)
            for content in result.content or []:
                print(content.text if hasattr(content, "text") else content)
        except Exception as e:
            print(f"❌ Tool execution error: {e}")

    def check_dependencies(self) -> bool:
        missing = []
        try:
            import mcp
        except ImportError:
            missing.append("mcp")
        try:
            import google.generativeai
        except ImportError:
            missing.append("google-generativeai")
        try:
            subprocess.run(["uv", "--version"], check=True, capture_output=True)
        except Exception:
            missing.append("uv")

        if missing:
            print("🔧 Missing dependencies:")
            for dep in missing:
                cmd = "curl -LsSf https://astral.sh/uv/install.sh | sh" if dep == "uv" else f"pip install {dep}"
                print(f"- {dep}: {cmd}")
            return False
        return True

    async def chat_loop(self):
        print("💬 Gemini Chatbot Started! Type 'exit' to quit.")
        history = []
        while True:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in ["exit", "quit"]:
                break
            await self.process_with_ai(user_input, history)

    async def cleanup(self):
        await self.exit_stack.aclose()


async def main():
    bot = GeminiMCPChatbot()
    if not bot.check_dependencies():
        return
    await bot.connect_to_servers()
    await bot.chat_loop()
    await bot.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Exiting Gemini Chatbot...")
