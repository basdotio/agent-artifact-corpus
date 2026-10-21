import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { ConsoleLogger, LogLevel } from './logger.js';
import { Neo4jKnowledgeGraphManager } from './manager.js';
import { EntityObject, ObservationObject, RelationObject } from './types.js';
import { extractError } from './utils.js';

// 创建MCP服务器
const server = new McpServer({
  name: 'neo4j-memory-server',
  version: '1.0.0',
});

// 创建日志记录器，并设置为仅输出错误信息
const logger = new ConsoleLogger();
logger.setLevel(LogLevel.ERROR);

// 创建知识图谱管理器
const knowledgeGraphManager = new Neo4jKnowledgeGraphManager(
  /**
   * 根据环境变量获取Neo4j配置
   * @returns Neo4j配置
   */
  () => {
    return {
      uri: process.env.NEO4J_URI || 'bolt://localhost:7687',
      user: process.env.NEO4J_USER || 'neo4j',
      password: process.env.NEO4J_PASSWORD || 'password',
      database: process.env.NEO4J_DATABASE || 'neo4j',
    };
  },
  logger
);

// 注册创建实体工具
server.tool(
  'create_entities',
  'Create multiple new entities in the knowledge graph',
  {
    entities: z.array(EntityObject),
  },
  async ({ entities }) => ({
    content: [
      {
        type: 'text',
        text: JSON.stringify(
          await knowledgeGraphManager.createEntities(entities),
          null,
          2
        ),
      },
    ],
  })
);

// 注册创建关系工具
server.tool(
  'create_relations',
  'Create multiple new relations between entities in the knowledge graph. Relations should be in active voice',
  {
    relations: z.array(RelationObject),
  },
  async ({ relations }) => ({
    content: [
      {
        type: 'text',
        text: JSON.stringify(
          await knowledgeGraphManager.createRelations(relations),
          null,
          2
        ),
      },
    ],
  })
);

// 注册添加观察工具
server.tool(
  'add_observations',
  'Add new observations to existing entities in the knowledge graph',
  {
    observations: z.array(ObservationObject),
  },
  async ({ observations }) => ({
    content: [
      {
        type: 'text',
        text: JSON.stringify(
          await knowledgeGraphManager.addObservations(observations),
          null,
          2
        ),
      },
    ],
  })
);

// 注册删除实体工具
server.tool(
  'delete_entities',
  'Delete multiple entities and their associated relations from the knowledge graph',
  {
    entityNames: z
      .array(z.string())
      .describe('An array of entity names to delete'),
  },
  async ({ entityNames }) => {
    await knowledgeGraphManager.deleteEntities(entityNames);
    return {
      content: [{ type: 'text', text: 'Entities deleted successfully' }],
    };
  }
);

// 注册删除观察工具
server.tool(
  'delete_observations',
  'Delete specific observations from entities in the knowledge graph',
  {
    deletions: z.array(
      z.object({
        entityName: z
          .string()
          .describe('The name of the entity containing the observations'),
        contents: z
          .array(z.string())
          .describe('An array of observations to delete'),
      })
    ),
  },
  async ({ deletions }) => {
    await knowledgeGraphManager.deleteObservations(deletions);
    return {
      content: [{ type: 'text', text: 'Observations deleted successfully' }],
    };
  }
);

// 注册删除关系工具
server.tool(
  'delete_relations',
  'Delete multiple relations from the knowledge graph',
  {
    relations: z
      .array(
        z.object({
          from: z
            .string()
            .describe('The name of the entity where the relation starts'),
          to: z
            .string()
            .describe('The name of the entity where the relation ends'),
          relationType: z.string().describe('The type of the relation'),
        })
      )
      .describe('An array of relations to delete'),
  },
  async ({ relations }) => {
    await knowledgeGraphManager.deleteRelations(relations);
    return {
      content: [{ type: 'text', text: 'Relations deleted successfully' }],
    };
  }
);

// 注册搜索节点工具
server.tool(
  'search_nodes',
  'Search for nodes in the knowledge graph based on a query',
  {
    query: z
      .string()
      .describe(
        'The search query to match against entity names, types, and observation content'
      ),
  },
  async ({ query }) => ({
    content: [
      {
        type: 'text',
        text: JSON.stringify(
          await knowledgeGraphManager.searchNodes(query),
          null,
          2
        ),
      },
    ],
  })
);

// 注册打开节点工具
server.tool(
  'open_nodes',
  'Open specific nodes in the knowledge graph by their names',
  {
    names: z.array(z.string()).describe('An array of entity names to retrieve'),
  },
  async ({ names }) => ({
    content: [
      {
        type: 'text',
        text: JSON.stringify(
          await knowledgeGraphManager.openNodes(names),
          null,
          2
        ),
      },
    ],
  })
);

// 主函数
const main = async () => {
  try {
    // 初始化知识图谱管理器
    await knowledgeGraphManager.initialize();
    
    // 创建传输层
    const transport = new StdioServerTransport();
    
    // 连接服务器
    await server.connect(transport);
    
    // 使用logger代替console.info
    logger.info('Neo4j Knowledge Graph MCP Server running on stdio');
  } catch (error) {
    // 使用logger代替console.error
    logger.error('Failed to start server:', extractError(error));
    process.exit(1);
  }
};

// 启动服务器
main().catch((error) => {
  // 使用logger代替console.error
  logger.error('Error during server startup:', extractError(error));
  process.exit(1);
});