# Chatbot System with MCP Integration

This project integrates a Python-based AI chatbot with a PostgreSQL database using two MCP-compatible servers — one in Python and one in Node.js. The chatbot leverages Google Generative AI and can query academic papers via arXiv.

---

## 📦 Python Setup

### Required Python Packages

Install the following Python dependencies:

```bash
pip install mcp google-generativeai arxiv python-dotenv
```

These packages include:
* `mcp`: For creating the MCP server and client.
* `google-generativeai`: Enables the chatbot's AI capabilities.
* `arxiv`: Allows interaction with the arXiv API for academic papers.
* `python-dotenv`: Loads environment variables for the Python environment.

## 🟢 Node.js Setup

### Required Node.js Packages

Install the following Node.js dependencies:

```bash
npm install @modelcontextprotocol/sdk pg dotenv
```

These include:
* `@modelcontextprotocol/sdk`: The official MCP SDK for Node.js.
* `pg`: PostgreSQL client for Node.js.
* `dotenv`: Loads environment variables from a `.env` file.

## ⚙️ Environment Variables

Create a `.env` file in the root of your project for the Node.js server with the following content:

```env
DB_USER=youruser
DB_HOST=localhost
DB_NAME=yourdb
DB_PASSWORD=yourpassword
DB_PORT=5432
```

Replace the values with your actual PostgreSQL credentials.

## 🚀 Running the Chatbot System

To run the full system, simply execute the following command:

```bash
python chatbot-client.py
```

This will:
1. Start the Python MCP server (`server.py`)
2. Start the Node.js MCP server (`pgserver.js`)
3. Connect the chatbot client (`chatbot-client.py`) to both servers

Once running, you can chat with the AI via your terminal.

## 🧪 Testing Servers Individually (Optional)

You can also run and test each server separately using the MCP Inspector tool.

### 🐍 Test the Python MCP Server

1. Start the server:
```bash
python server.py
```

2. Inspect with MCP Inspector:
```bash
mcp inspect --stdio "python server.py"
```

### 🟩 Test the Node.js MCP Server

1. Start the server:
```bash
node pgserver.js
```

2. Inspect with MCP Inspector:
```bash
mcp inspect --stdio "node pgserver.js"
```

This lets you see available tools and interact with them manually.

## 📁 Project Structure

```
project-root/
├── chatbot-client.py         # Main client script
├── server.py                 # Python MCP server
├── pgserver.js               # Node.js MCP server
├── .env                      # PostgreSQL credentials (for Node.js)
├── server_config.json        # Configuration file for MCP client
├── README.md                 # Project documentation
```

## 📝 Notes

* Make sure both Python and Node.js are installed.
* Ensure PostgreSQL is running and accessible.
* You may extend the MCP tools in either server to support additional functionality.

## ✅ License

MIT License (or specify another license here)
