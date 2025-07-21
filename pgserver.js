// ============================================
// MERGED MCP MULTI-TOOL SERVER (CommonJS Version)
// Single file with PostgreSQL connection built-in
// Works without "type": "module" in package.json
// ============================================

const { Server } = require('@modelcontextprotocol/sdk/server/index.js');
const { StdioServerTransport } = require("@modelcontextprotocol/sdk/server/stdio.js");
const {
  CallToolRequestSchema,
  ListToolsRequestSchema
} = require('@modelcontextprotocol/sdk/types.js');
const pg = require('pg');
const dotenv = require('dotenv');

// Load environment variables
dotenv.config();

const { Pool } = pg;

console.log('🎯 [MCP-SERVER] Starting Multi-Tool MCP Server...');

// ============================================
// 🗃️ POSTGRESQL CONNECTION SETUP
// ============================================

console.log('🔗 [POSTGRES] Setting up PostgreSQL connection...');

const pool = new Pool({
  user: process.env.DB_USER || 'youruser',
  host: process.env.DB_HOST || 'localhost',
  database: process.env.DB_NAME || 'yourdb',
  password: process.env.DB_PASSWORD || 'yourpassword',
  port: parseInt(process.env.DB_PORT) || 5432,
});

console.log('✅ [POSTGRES] Connected to PostgreSQL database:', process.env.DB_NAME || 'yourdb');

// PostgreSQL query function
async function runQuery(sql) {
  try {
    console.log('⚡ [POSTGRES] Executing query:', sql.substring(0, 100) + '...');
    const result = await pool.query(sql);
    console.log('✅ [POSTGRES] Query successful, rows:', result.rows.length);
    return result.rows;
  } catch (err) {
    console.error('❌ [POSTGRES] Query error:', err.message);
    throw err;
  }
}

// ============================================
// 🚀 MCP SERVER SETUP
// ============================================

const server = new Server(
  {
    name: 'multi-tool-mcp-server',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {}
    },
  }
);

console.log('✅ [MCP-SERVER] Server instance created');

// ============================================
// 🗃️ TOOL DEFINITIONS
// ============================================

const TOOLS = [
  {
    name: "execute-sql",
    description: "Run a SQL query on the PostgreSQL database",
    inputSchema: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "The SQL query to execute"
        }
      },
      required: ["query"]
    }
  },
  {
    name: "list-tables",
    description: "Get a list of all tables in the PostgreSQL database",
    inputSchema: {
      type: "object",
      properties: {}
    }
  },
  {
    name: "describe-table",
    description: "Get column information for a specific table",
    inputSchema: {
      type: "object",
      properties: {
        tableName: {
          type: "string",
          description: "Name of the table to describe"
        }
      },
      required: ["tableName"]
    }
  },
  {
    name: "test-connection",
    description: "Test the PostgreSQL database connection",
    inputSchema: {
      type: "object",
      properties: {}
    }
  }
];

// ============================================
// 🔧 TOOL HANDLERS
// ============================================

console.log('🔧 [MCP-SERVER] Setting up tool handlers...');

// Handle tool listing
server.setRequestHandler(ListToolsRequestSchema, async () => {
  console.log('📋 [MCP-SERVER] Listing tools...');
  return {
    tools: TOOLS
  };
});

// Handle tool execution
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  console.log(`🔧 [MCP-TOOL] Executing tool: ${name}`);
  console.log('📝 [MCP-TOOL] Arguments:', args);

  try {
    switch (name) {
      case "execute-sql": {
        const { query } = args;
        const results = await runQuery(query);

        if (Array.isArray(results) && results.length > 0) {
          const headers = Object.keys(results[0]);
          const formattedTable = results.map(row =>
            headers.map(h => String(row[h] || '')).join(' | ')
          );
          const tableOutput = [headers.join(' | '), ...formattedTable].join('\n');

          return {
            content: [{
              type: "text",
              text: `✅ Query executed successfully! Found ${results.length} rows:\n\n${tableOutput}`
            }]
          };
        } else {
          return {
            content: [{
              type: "text",
              text: "✅ Query executed successfully! No rows returned."
            }]
          };
        }
      }

      case "list-tables": {
        const query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;";
        const results = await runQuery(query);

        const tableNames = results.map(row => row.table_name);

        return {
          content: [{
            type: "text",
            text: `📚 Available tables (${tableNames.length}):\n${tableNames.map(name => `• ${name}`).join('\n')}`
          }]
        };
      }

      case "describe-table": {
        const { tableName } = args;
        const query = `
          SELECT column_name, data_type, is_nullable, column_default
          FROM information_schema.columns
          WHERE table_name = $1 AND table_schema = 'public'
          ORDER BY ordinal_position;
        `;

        const results = await pool.query(query, [tableName]);

        if (results.rows.length === 0) {
          return {
            content: [{
              type: "text",
              text: `❌ Table '${tableName}' not found.`
            }]
          };
        }

        const tableDesc = results.rows.map(col =>
          `${col.column_name} (${col.data_type}) ${col.is_nullable === 'YES' ? 'NULL' : 'NOT NULL'}${col.column_default ? ` DEFAULT ${col.column_default}` : ''}`
        ).join('\n');

        return {
          content: [{
            type: "text",
            text: `📋 Table '${tableName}' structure:\n\n${tableDesc}`
          }]
        };
      }

      case "test-connection": {
        const query = "SELECT NOW() as current_time, version() as postgres_version;";
        const results = await runQuery(query);

        return {
          content: [{
            type: "text",
            text: `✅ Database connection successful!\n\nServer Time: ${results[0].current_time}\nPostgreSQL Version: ${results[0].postgres_version}`
          }]
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    console.error(`❌ [MCP-TOOL] Error in ${name}:`, error);
    return {
      content: [{
        type: "text",
        text: `❌ Error: ${error.message}`
      }],
      isError: true
    };
  }
});

console.log('✅ [MCP-SERVER] Tool handlers configured');

// ============================================
// 🚀 START SERVER
// ============================================

async function startServer() {
  try {
    console.log('🎯 [MCP-SERVER] Creating transport...');

    const transport = new StdioServerTransport();
    console.log('✅ [MCP-SERVER] Transport created');

    console.log('🔌 [MCP-SERVER] Connecting to transport...');
    await server.connect(transport);

    console.log('🚀 [MCP-SERVER] Multi-Tool MCP Server is running!');
    console.log('📋 [MCP-SERVER] Available tools:');
    TOOLS.forEach(tool => {
      console.log(`   • ${tool.name} - ${tool.description}`);
    });
    console.log('✅ [MCP-SERVER] Server ready to accept connections!');

  } catch (error) {
    console.error('❌ [MCP-SERVER] Failed to start server:', error);
    console.error('🔍 [MCP-SERVER] Stack:', error.stack);
    process.exit(1);
  }
}

// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('\n🛑 [MCP-SERVER] Received SIGINT, shutting down gracefully...');
  try {
    await pool.end();
    console.log('✅ [MCP-SERVER] Database pool closed');
  } catch (error) {
    console.error('❌ [MCP-SERVER] Error closing database pool:', error);
  }
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.log('\n🛑 [MCP-SERVER] Received SIGTERM, shutting down gracefully...');
  try {
    await pool.end();
    console.log('✅ [MCP-SERVER] Database pool closed');
  } catch (error) {
    console.error('❌ [MCP-SERVER] Error closing database pool:', error);
  }
  process.exit(0);
});

// Handle uncaught errors
process.on('uncaughtException', (error) => {
  console.error('💥 [MCP-SERVER] Uncaught exception:', error);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('💥 [MCP-SERVER] Unhandled rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

// Start the server
startServer();