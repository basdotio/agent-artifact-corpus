import { z } from "zod";

// 实体对象模式
export const EntityObject = z.object({
  name: z.string().describe("The name of the entity"),
  entityType: z.string().describe("The type of the entity"),
  observations: z.array(z.string()).describe("An array of observation contents associated with the entity")
});

// 关系对象模式
export const RelationObject = z.object({
  from: z.string().describe("The name of the entity where the relation starts"),
  to: z.string().describe("The name of the entity where the relation ends"),
  relationType: z.string().describe("The type of the relation")
});

// 观察对象模式
export const ObservationObject = z.object({
  entityName: z.string().describe("The name of the entity to add the observations to"),
  contents: z.array(z.string()).describe("An array of observation contents to add")
});

// 实体类型
export type Entity = z.infer<typeof EntityObject>;

// 关系类型
export type Relation = z.infer<typeof RelationObject>;

// 观察类型
export type Observation = z.infer<typeof ObservationObject>;

// 知识图谱类型
export interface KnowledgeGraph {
  entities: Entity[];
  relations: Relation[];
}

// 删除观察类型
export interface ObservationDeletion {
  entityName: string;
  contents: string[];
}