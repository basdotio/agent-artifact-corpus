import Fuse from 'fuse.js';
import neo4j, { Driver, Session } from 'neo4j-driver';
import { ConsoleLogger, Logger } from './logger.js';
import { Entity, KnowledgeGraph, Observation, ObservationDeletion, Relation } from './types.js';
import { extractError } from './utils.js';

/**
 * Neo4j知识图谱管理器
 */
export class Neo4jKnowledgeGraphManager {
  private driver: Driver | null = null;
  private fuse: Fuse<Entity>;
  private initialized = false;
  private logger: Logger;
  private uri: string;
  private user: string;
  private password: string;
  private database: string;

  /**
   * 构造函数
   * @param configResolver 配置解析器函数
   * @param logger 可选的日志记录器
   */
  constructor(
    configResolver: () => { 
      uri: string; 
      user: string; 
      password: string; 
      database: string;
    },
    logger?: Logger
  ) {
    const config = configResolver();
    this.uri = config.uri;
    this.user = config.user;
    this.password = config.password;
    this.database = config.database;
    this.logger = logger || new ConsoleLogger();

    this.fuse = new Fuse([], {
      keys: ['name', 'entityType', 'observations'],
      includeScore: true,
      threshold: 0.4, // 搜索严格度（越接近0越严格）
    });
  }

  /**
   * 获取会话
   * @returns Neo4j会话
   */
  private async getSession(): Promise<Session> {
    if (!this.driver) {
      await this.initialize();
    }
    return this.driver!.session({ database: this.database });
  }

  /**
   * 初始化数据库
   */
  public async initialize(): Promise<void> {
    if (this.initialized) return;

    try {
      if (!this.driver) {
        this.driver = neo4j.driver(
          this.uri,
          neo4j.auth.basic(this.user, this.password),
          { maxConnectionLifetime: 3 * 60 * 60 * 1000 } // 3小时
        );
      }

      const session = await this.getSession();
      try {
        // 创建约束和索引
        await session.run(`
          CREATE CONSTRAINT entity_name_unique IF NOT EXISTS
          FOR (e:Entity) REQUIRE e.name IS UNIQUE
        `);

        await session.run(`
          CREATE INDEX entity_type_index IF NOT EXISTS
          FOR (e:Entity) ON (e.entityType)
        `);

        // 使用新的语法创建全文索引
        await session.run(`
          CREATE FULLTEXT INDEX entity_fulltext IF NOT EXISTS
          FOR (e:Entity)
          ON EACH [e.name, e.entityType]
        `);

        // 加载所有实体到Fuse.js
        const entities = await this.getAllEntities();
        this.fuse.setCollection(entities);
        
        this.initialized = true;
      } finally {
        await session.close();
      }
    } catch (error) {
      this.logger.error('Failed to initialize database', extractError(error));
      throw error;
    }
  }

  /**
   * 获取所有实体
   * @returns 所有实体数组
   */
  private async getAllEntities(): Promise<Entity[]> {
    const session = await this.getSession();
    try {
      const result = await session.run(`
        MATCH (e:Entity)
        OPTIONAL MATCH (e)-[r:HAS_OBSERVATION]->(o)
        RETURN e.name AS name, e.entityType AS entityType, collect(o.content) AS observations
      `);

      const entities: Entity[] = result.records.map(record => {
        return {
          name: record.get('name'),
          entityType: record.get('entityType'),
          observations: record.get('observations').filter(Boolean)
        };
      });

      return entities;
    } catch (error) {
      this.logger.error('Error getting all entities', extractError(error));
      return [];
    } finally {
      await session.close();
    }
  }

  /**
   * 创建实体
   * @param entities 要创建的实体数组
   * @returns 创建的实体数组
   */
  public async createEntities(entities: Entity[]): Promise<Entity[]> {
    if (entities.length === 0) return [];

    const session = await this.getSession();
    try {
      const createdEntities: Entity[] = [];
      const tx = session.beginTransaction();

      try {
        // 获取现有实体名称
        const existingEntitiesResult = await tx.run(
          'MATCH (e:Entity) RETURN e.name AS name'
        );
        const existingNames = new Set(
          existingEntitiesResult.records.map(record => record.get('name'))
        );

        // 过滤出新实体
        const newEntities = entities.filter(
          entity => !existingNames.has(entity.name)
        );

        // 创建新实体
        for (const entity of newEntities) {
          await tx.run(
            `
            CREATE (e:Entity {name: $name, entityType: $entityType})
            WITH e
            UNWIND $observations AS observation
            CREATE (o:Observation {content: observation})
            CREATE (e)-[:HAS_OBSERVATION]->(o)
            RETURN e
            `,
            {
              name: entity.name,
              entityType: entity.entityType,
              observations: entity.observations
            }
          );
          createdEntities.push(entity);
        }

        await tx.commit();
        
        // 更新Fuse.js集合
        const allEntities = await this.getAllEntities();
        this.fuse.setCollection(allEntities);
        
        return createdEntities;
      } catch (error) {
        await tx.rollback();
        this.logger.error('Error creating entities', extractError(error));
        throw error;
      }
    } finally {
      await session.close();
    }
  }

  /**
   * 创建关系
   * @param relations 要创建的关系数组
   * @returns 创建的关系数组
   */
  public async createRelations(relations: Relation[]): Promise<Relation[]> {
    if (relations.length === 0) return [];

    const session = await this.getSession();
    try {
      const tx = session.beginTransaction();
      try {
        // 获取所有实体名称
        const entityNamesResult = await tx.run(
          'MATCH (e:Entity) RETURN e.name AS name'
        );
        const entityNames = new Set(
          entityNamesResult.records.map(record => record.get('name'))
        );

        // 过滤出有效关系（源实体和目标实体都存在）
        const validRelations = relations.filter(
          relation => entityNames.has(relation.from) && entityNames.has(relation.to)
        );

        // 获取现有关系
        const existingRelationsResult = await tx.run(`
          MATCH (from:Entity)-[r]->(to:Entity)
          RETURN from.name AS fromName, to.name AS toName, type(r) AS relationType
        `);
        
        const existingRelations = existingRelationsResult.records.map(record => {
          return {
            from: record.get('fromName'),
            to: record.get('toName'),
            relationType: record.get('relationType')
          };
        });

        // 过滤出新关系
        const newRelations = validRelations.filter(
          newRel => !existingRelations.some(
            existingRel => 
              existingRel.from === newRel.from && 
              existingRel.to === newRel.to && 
              existingRel.relationType === newRel.relationType
          )
        );

        // 创建新关系
        for (const relation of newRelations) {
          await tx.run(
            `
            MATCH (from:Entity {name: $fromName})
            MATCH (to:Entity {name: $toName})
            CREATE (from)-[r:${relation.relationType}]->(to)
            RETURN r
            `,
            {
              fromName: relation.from,
              toName: relation.to
            }
          );
        }

        await tx.commit();
        return newRelations;
      } catch (error) {
        await tx.rollback();
        this.logger.error('Error creating relations', extractError(error));
        throw error;
      }
    } finally {
      await session.close();
    }
  }

  /**
   * 添加观察
   * @param observations 要添加的观察数组
   * @returns 添加的观察数组
   */
  public async addObservations(observations: Observation[]): Promise<Observation[]> {
    if (observations.length === 0) return [];

    const session = await this.getSession();
    try {
      const addedObservations: Observation[] = [];
      const tx = session.beginTransaction();

      try {
        for (const observation of observations) {
          // 检查实体是否存在
          const entityResult = await tx.run(
            'MATCH (e:Entity {name: $name}) RETURN e',
            { name: observation.entityName }
          );

          if (entityResult.records.length > 0) {
            // 获取现有观察
            const existingObservationsResult = await tx.run(
              `
              MATCH (e:Entity {name: $name})-[:HAS_OBSERVATION]->(o:Observation)
              RETURN o.content AS content
              `,
              { name: observation.entityName }
            );

            const existingObservations = new Set(
              existingObservationsResult.records.map(record => record.get('content'))
            );

            // 过滤出新观察
            const newContents = observation.contents.filter(
              content => !existingObservations.has(content)
            );

            if (newContents.length > 0) {
              // 添加新观察
              await tx.run(
                `
                MATCH (e:Entity {name: $name})
                UNWIND $contents AS content
                CREATE (o:Observation {content: content})
                CREATE (e)-[:HAS_OBSERVATION]->(o)
                `,
                {
                  name: observation.entityName,
                  contents: newContents
                }
              );

              addedObservations.push({
                entityName: observation.entityName,
                contents: newContents
              });
            }
          }
        }

        await tx.commit();
        
        // 更新Fuse.js集合
        const allEntities = await this.getAllEntities();
        this.fuse.setCollection(allEntities);
        
        return addedObservations;
      } catch (error) {
        await tx.rollback();
        this.logger.error('Error adding observations', extractError(error));
        throw error;
      }
    } finally {
      await session.close();
    }
  }

  /**
   * 删除实体
   * @param entityNames 要删除的实体名称数组
   */
  public async deleteEntities(entityNames: string[]): Promise<void> {
    if (entityNames.length === 0) return;

    const session = await this.getSession();
    try {
      const tx = session.beginTransaction();
      try {
        // 删除实体及其关联的观察和关系
        await tx.run(
          `
          UNWIND $names AS name
          MATCH (e:Entity {name: name})
          OPTIONAL MATCH (e)-[:HAS_OBSERVATION]->(o:Observation)
          DETACH DELETE e, o
          `,
          { names: entityNames }
        );

        await tx.commit();
        
        // 更新Fuse.js集合
        const allEntities = await this.getAllEntities();
        this.fuse.setCollection(allEntities);
      } catch (error) {
        await tx.rollback();
        this.logger.error('Error deleting entities', extractError(error));
        throw error;
      }
    } finally {
      await session.close();
    }
  }

  /**
   * 删除观察
   * @param deletions 要删除的观察数组
   */
  public async deleteObservations(deletions: ObservationDeletion[]): Promise<void> {
    if (deletions.length === 0) return;

    const session = await this.getSession();
    try {
      const tx = session.beginTransaction();
      try {
        for (const deletion of deletions) {
          if (deletion.contents.length > 0) {
            await tx.run(
              `
              MATCH (e:Entity {name: $name})-[:HAS_OBSERVATION]->(o:Observation)
              WHERE o.content IN $contents
              DETACH DELETE o
              `,
              {
                name: deletion.entityName,
                contents: deletion.contents
              }
            );
          }
        }

        await tx.commit();
        
        // 更新Fuse.js集合
        const allEntities = await this.getAllEntities();
        this.fuse.setCollection(allEntities);
      } catch (error) {
        await tx.rollback();
        this.logger.error('Error deleting observations', extractError(error));
        throw error;
      }
    } finally {
      await session.close();
    }
  }

  /**
   * 删除关系
   * @param relations 要删除的关系数组
   */
  public async deleteRelations(relations: Relation[]): Promise<void> {
    if (relations.length === 0) return;

    const session = await this.getSession();
    try {
      const tx = session.beginTransaction();
      try {
        for (const relation of relations) {
          await tx.run(
            `
            MATCH (from:Entity {name: $fromName})-[r:${relation.relationType}]->(to:Entity {name: $toName})
            DELETE r
            `,
            {
              fromName: relation.from,
              toName: relation.to
            }
          );
        }

        await tx.commit();
      } catch (error) {
        await tx.rollback();
        this.logger.error('Error deleting relations', extractError(error));
        throw error;
      }
    } finally {
      await session.close();
    }
  }

  /**
   * 搜索节点
   * @param query 搜索查询
   * @returns 包含匹配实体和关系的知识图谱
   */
  public async searchNodes(query: string): Promise<KnowledgeGraph> {
    if (!query || query.trim() === '') {
      return { entities: [], relations: [] };
    }

    const session = await this.getSession();
    try {
      // 使用Neo4j全文搜索
      const searchResult = await session.run(
        `
        CALL db.index.fulltext.queryNodes("entity_fulltext", $query)
        YIELD node, score
        RETURN node
        `,
        { query }
      );

      // 获取所有实体用于Fuse.js搜索
      const allEntities = await this.getAllEntities();
      this.fuse.setCollection(allEntities);
      
      // 使用Fuse.js进行模糊搜索
      const fuseResults = this.fuse.search(query);
      
      // 合并搜索结果
      const uniqueEntities = new Map<string, Entity>();
      
      // 添加Neo4j搜索结果
      for (const record of searchResult.records) {
        const node = record.get('node');
        const name = node.properties.name;
        
        if (!uniqueEntities.has(name)) {
          const entity = allEntities.find(e => e.name === name);
          if (entity) {
            uniqueEntities.set(name, entity);
          }
        }
      }
      
      // 添加Fuse.js搜索结果
      for (const result of fuseResults) {
        if (!uniqueEntities.has(result.item.name)) {
          uniqueEntities.set(result.item.name, result.item);
        }
      }
      
      const entities = Array.from(uniqueEntities.values());
      const entityNames = entities.map(entity => entity.name);
      
      if (entityNames.length === 0) {
        return { entities: [], relations: [] };
      }
      
      // 获取关系
      const relationsResult = await session.run(
        `
        MATCH (from:Entity)-[r]->(to:Entity)
        WHERE from.name IN $names OR to.name IN $names
        RETURN from.name AS fromName, to.name AS toName, type(r) AS relationType
        `,
        { names: entityNames }
      );
      
      const relations: Relation[] = relationsResult.records.map(record => {
        return {
          from: record.get('fromName'),
          to: record.get('toName'),
          relationType: record.get('relationType')
        };
      });
      
      return {
        entities,
        relations
      };
    } catch (error) {
      this.logger.error('Error searching nodes', extractError(error));
      return { entities: [], relations: [] };
    } finally {
      await session.close();
    }
  }

  /**
   * 打开节点
   * @param names 要打开的节点名称数组
   * @returns 包含匹配实体和关系的知识图谱
   */
  public async openNodes(names: string[]): Promise<KnowledgeGraph> {
    if (names.length === 0) {
      return { entities: [], relations: [] };
    }

    const session = await this.getSession();
    try {
      // 获取实体及其观察
      const entitiesResult = await session.run(
        `
        MATCH (e:Entity)
        WHERE e.name IN $names
        OPTIONAL MATCH (e)-[:HAS_OBSERVATION]->(o:Observation)
        RETURN e.name AS name, e.entityType AS entityType, collect(o.content) AS observations
        `,
        { names }
      );
      
      const entities: Entity[] = entitiesResult.records.map(record => {
        return {
          name: record.get('name'),
          entityType: record.get('entityType'),
          observations: record.get('observations').filter(Boolean)
        };
      });
      
      const entityNames = entities.map(entity => entity.name);
      
      if (entityNames.length > 0) {
        // 获取关系
        const relationsResult = await session.run(
          `
          MATCH (from:Entity)-[r]->(to:Entity)
          WHERE from.name IN $names OR to.name IN $names
          RETURN from.name AS fromName, to.name AS toName, type(r) AS relationType
          `,
          { names: entityNames }
        );
        
        const relations: Relation[] = relationsResult.records.map(record => {
          return {
            from: record.get('fromName'),
            to: record.get('toName'),
            relationType: record.get('relationType')
          };
        });
        
        return {
          entities,
          relations
        };
      } else {
        return {
          entities,
          relations: []
        };
      }
    } catch (error) {
      this.logger.error('Error opening nodes', extractError(error));
      return { entities: [], relations: [] };
    } finally {
      await session.close();
    }
  }

  /**
   * 关闭连接
   */
  public async close(): Promise<void> {
    if (this.driver) {
      await this.driver.close();
      this.driver = null;
    }
  }
}