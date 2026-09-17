---
name: ruoyi-gen
description: RuoYi 交互式代码生成。输入表名，自动从 pm-sql/init/ 查找 DDL，智能生成配置并引导用户确认，调用 CLI 生成脚手架代码，部署到项目目录，并根据自定义描述做精细化定制。当用户提到"生成代码"、"新增模块"、"CRUD"等场景时使用。
argument-hint: "<表名>"
---

# RuoYi 交互式代码生成

你是 RuoYi-Vue 项目的代码生成助手。用户提供表名，你负责从 `pm-sql/init/00_tables_ddl.sql` 查找 DDL，完成从表结构分析到代码落地的全流程。

## 重要文件路径

- **CLI JAR**: `ruoyi-gen-cli/target/ruoyi-gen-cli-3.9.1.jar`（如不存在先执行构建）
- **DDL 数据源**: `pm-sql/init/00_tables_ddl.sql`（所有表的 DDL 统一存放于此）
- **菜单数据**: `pm-sql/init/02_menu_data.sql`（菜单权限 SQL 统一存放于此）
- **规格目录**: `docs/gen-specs/<表名>.yml`（每张表一个规格文件，持久化保存配置）
- **项目 generator.yml**: `ruoyi-generator/src/main/resources/generator.yml`（读取默认 author/packageName/tablePrefix）
- **业务代码目标模块**: `ruoyi-project/`（生成的 Java 代码统一部署到此模块，不放 ruoyi-admin）
- **前端代码目标**: `ruoyi-ui/`（Vue/API 文件部署到前端目录）

---

## 阶段 1：查找 DDL + 关联分析

`$ARGUMENTS` 为表名（如 `pm_project`）。

### 1.1 查找 DDL

1. 读取 `pm-sql/init/00_tables_ddl.sql`
2. 按 `CREATE TABLE` 语句拆分，匹配目标表名
3. **找到** → 提取该表的完整 DDL，进入 1.2
4. **找不到** → 提示用户："在 `pm-sql/init/00_tables_ddl.sql` 中未找到表 `xxx`，请先将 DDL 添加到该文件"，流程终止

### 1.2 外键关联分析

1. 解析主表 DDL 中的 `FOREIGN KEY ... REFERENCES <parent_table>(...)` 约束，记录主表引用了哪些父表
2. 扫描整个 `00_tables_ddl.sql` 中所有表的 DDL，找出哪些表的外键引用了主表（即主表的子表）
3. 记录关联信息，在阶段 3 配置展示时作为参考呈现给用户
4. 关联分析**不**自动为关联表生成代码，只影响主表自身配置的决策参考

### 增量重跑模式
- 如果用户说"重新生成 xxx" 且 `docs/gen-specs/<表名>.yml` 已存在
- 读取已有规格，展示配置，询问是否修改，然后重新走阶段 4-5

---

## 阶段 2：智能生成规格文件

拿到 DDL 后，先读取 `ruoyi-generator/src/main/resources/generator.yml` 获取项目默认值，然后生成完整规格。

### 规格文件结构（`docs/gen-specs/<表名>.yml`）

```yaml
# ============================
# Tab 1: 基本信息
# ============================
basicInfo:
  tableName: <表名>                    # 从 DDL 读取
  tableComment: <表注释>               # 从 DDL COMMENT 读取
  className: <实体类名>                # 去前缀后转 PascalCase
  functionAuthor: <作者>               # 从 generator.yml 读取
  remark: ""

# ============================
# Tab 2: 字段信息
# ============================
columns:
  <列名>:
    columnComment: <字段描述>          # 从 DDL COMMENT 读取
    columnType: <物理类型>             # 如 varchar(100), int(11), decimal(10,2)
    javaType: <Java类型>               # 推断规则见下
    javaField: <java属性>              # 列名转 camelCase
    isInsert: <bool>                   # 默认 true
    isEdit: <bool>                     # 主键和 create_by/create_time/del_flag 为 false
    isList: <bool>                     # 上述 + update_by/update_time 为 false
    isQuery: <bool>                    # 上述 + remark 为 false
    queryType: <查询方式>              # 默认 EQ，*_name 列为 LIKE
    isRequired: <bool>                 # DDL 中 NOT NULL 为 true
    htmlType: <显示类型>               # 推断规则见下
    dictType: ""                       # 需要用户确认

# ============================
# Tab 3: 生成信息
# ============================
genInfo:
  tplCategory: crud                    # crud / tree / sub
  tplWebType: element-plus             # element-ui / element-plus
  packageName: <从generator.yml>       # 如 com.ruoyi.system
  moduleName: <从packageName提取末段>
  businessName: <从tableName提取末段>
  functionName: <从tableComment去除"表"字>
  parentMenuId: 3
  # treeCode / treeParentCode / treeName       (tplCategory=tree)
  # subTableName / subTableFkName              (tplCategory=sub)

# ============================
# 定制需求（超出标准模板的组件/交互/接口需求）
# ============================
customizations:
  # <功能标识>:                    # 语义化命名，如 dept_tree_select
  #   intent: <用户原始意图>
  #   component:
  #     type: <组件名 | "custom">  # 已有组件写组件名，自建写 "custom"
  #     props: { ... }             # 已有组件：关键 props（接口级）
  #     events: { ... }            # 已有组件：关键事件绑定（可选）
  #     spec: <功能描述+关键约束>   # 自建组件：意图+约束
  #   bindTo: <锚点>               # 列名 | 列名数组 | toolbar | form | dialog | page（可选）
  #   service:                     # null 表示纯前端
  #     endpoint: <HTTP method + path>
  #     source: <"复用 XxxService" | "new">
  #     returns: <返回数据描述>     # 可选
  #     newApi: <bool>
  #   notes: <补充说明>             # 可选
```

### 智能推断规则

**Java 类型推断**：
- `char`, `varchar`, `nvarchar`, `varchar2` → `String`
- `tinytext`, `text`, `mediumtext`, `longtext` → `String`
- `datetime`, `time`, `date`, `timestamp` → `Date`
- `decimal(m,n)` 且 n>0 → `BigDecimal`
- `tinyint`, `smallint`, `mediumint`, `int`, `integer`, `bit` 且精度 ≤10 → `Integer`
- `bigint` 或精度 >10 → `Long`
- `float`, `double` → `Double`

**显示类型推断**：
- 列名以 `industry` 结尾 → `select`（下拉框）
- 列名以 `region` 结尾 → `select`（下拉框）
- 列名以 `_category` 结尾 → `select`（下拉框）
- 列名以 `region_code` 结尾 → `select`（下拉框）
- 列名以 `_status` 结尾 → `select`（下拉框）
- 列名以 `_year`  结尾 → `select`（下拉框）
- 列名以 `_type` 或 `sex` 结尾 → `select`（下拉框）
- 列名以 `image` 结尾 → `imageUpload`（图片上传）
- 列名以 `file` 结尾 → `fileUpload`（文件上传）
- 列名以 `content` 结尾 → `editor`（富文本）
- `varchar(500+)` 或 `text` 类型 → `textarea`（文本域）
- `datetime`/`date`/`timestamp` → `datetime`（日期控件）
- 其他 → `input`（文本框）

**查询方式推断**：
- 列名以 `name` 结尾 → `LIKE`
- 其他 → `EQ`

**不参与编辑的列**（isEdit=false）：主键列、`id`、`create_by`、`create_time`、`del_flag`
**不参与列表的列**（isList=false）：上述 + `update_by`、`update_time`
**不参与查询的列**（isQuery=false）：上述 + `remark`

---

## 阶段 3：展示配置，用户确认

以清晰的格式展示三个维度的配置摘要。示例：

```
=== 基本信息 ===
表名称: sys_product    表描述: 产品表
实体类: Product        作者: ruoyi

=== 关联分析 ===
本表外键引用: (无)
被以下表引用: pm_project_approval(project_id), pm_contract(project_id)

=== 生成信息 ===
模板: 单表(crud)       前端: element-plus
包路径: com.ruoyi.system    模块: system
业务名: product             功能名: 产品管理
上级菜单: 3

=== 字段信息 ===
列名            描述      Java类型    插编列查  查询方式 必填 显示类型     字典类型
product_id      产品ID    Long        ✓---      EQ       -    -            -
product_name    产品名称  String      ✓✓✓✓      LIKE     ✓    文本框       -
product_type    产品类型  String      ✓✓✓✓      EQ       -    下拉框       (待确认)
price           价格      BigDecimal  ✓✓✓-      EQ       -    文本框       -
status          状态      String      ✓✓✓✓      EQ       -    单选框       (待确认)
create_by       创建者    String      ✓---      -        -    -            -
create_time     创建时间  Date        ✓---      -        -    -            -
update_by       更新者    String      -✓--      -        -    -            -
update_time     更新时间  Date        --✓-      -        -    -            -
remark          备注      String      ✓✓--      -        -    -            -
```

**特别注意**：
- `dictType` 标记为"(待确认)"的需要问用户：该字段是否关联字典？字典编码是什么？

用户可以：
- 说"OK"直接确认
- 指出需要修改的部分（如"price 的查询方式改成 BETWEEN"、"product_type 的字典是 sys_product_type"）

修改后再次展示确认，直到用户满意。

---

## 阶段 4：持久化 + 生成 + 部署

### 4.1 保存规格文件

将确认后的配置写入 `docs/gen-specs/<表名>.yml`。

### 4.2 构建 CLI（如需要）

检查 `ruoyi-gen-cli/target/ruoyi-gen-cli-3.9.1.jar` 是否存在，不存在则执行：
```bash
mvn clean package -pl ruoyi-gen-cli -am -Dmaven.test.skip=true
```

### 4.3 准备临时文件

从 `pm-sql/init/00_tables_ddl.sql` 中提取目标表的 DDL 写入临时 `.sql` 文件，提取 config 部分转换为 CLI 可用的 `gen-config.yml` 格式：

```yaml
global:
  author: <basicInfo.functionAuthor>
  packageName: <genInfo.packageName>
  tplCategory: <genInfo.tplCategory>
  tplWebType: <genInfo.tplWebType>
  parentMenuId: <genInfo.parentMenuId>
  autoRemovePre: <根据 generator.yml>
  tablePrefix: <根据 generator.yml>

tables:
  <tableName>:
    className: <basicInfo.className>
    functionName: <genInfo.functionName>
    businessName: <genInfo.businessName>
    moduleName: <genInfo.moduleName>
    # tree/sub 相关字段如有
    columns:
      <从规格文件 columns 节转换>
```

### 4.4 调用 CLI

```bash
java -jar ruoyi-gen-cli/target/ruoyi-gen-cli-3.9.1.jar \
  --sql=<tmp>.sql \
  --config=<tmp-config>.yml \
  --output=<tmp>.zip
```

### 4.5 解压部署

将 ZIP 解压后，按以下映射拷贝到项目目录：

| ZIP 内路径 | 项目目标路径 |
|---|---|
| `main/java/com/ruoyi/<module>/domain/` | `ruoyi-project/src/main/java/com/ruoyi/<module>/domain/` |
| `main/java/com/ruoyi/<module>/mapper/` | `ruoyi-project/src/main/java/com/ruoyi/<module>/mapper/` |
| `main/java/com/ruoyi/<module>/service/` | `ruoyi-project/src/main/java/com/ruoyi/<module>/service/` |
| `main/java/com/ruoyi/<module>/controller/` | `ruoyi-project/src/main/java/com/ruoyi/<module>/controller/` |
| `main/resources/mapper/<module>/` | `ruoyi-project/src/main/resources/mapper/<module>/` |
| `vue/api/<module>/` | `ruoyi-ui/src/api/<module>/` |
| `vue/views/<module>/<business>/` | `ruoyi-ui/src/views/<module>/<business>/` |

**注意**：Java 代码全部放入 `ruoyi-project` 模块，该模块已被 `ruoyi-admin` 依赖，Spring Boot 启动时会自动扫描。

**注意**：如果目标文件已存在，询问用户是否覆盖。

展示已部署的文件列表。

### 4.6 菜单SQL管理

**提取菜单SQL**：
- 从生成的 ZIP 中找到 `*Menu.sql` 文件

**对比去重**：
- 读取 `pm-sql/init/02_menu_data.sql`
- 通过权限标识前缀匹配（如 `<module>:<business>:%`），判断该业务的菜单是否已存在
- **不存在** → 将菜单 SQL 追加到 `pm-sql/init/02_menu_data.sql` 末尾，显示"✓ 菜单SQL已追加到 02_menu_data.sql"
- **已存在** → 显示"✓ 检测到菜单已存在于 02_menu_data.sql，跳过写入"

---

## 阶段 5：定制需求探查 + 精细化改造

代码生成部署完成后，进入定制环节。

### 5.1 定制需求探查

1. **主动识别候选字段**：扫描字段列表，找出可能需要定制的字段（外键关联、`_id` 结尾、标准 select/input 可能不够用的），列出告知用户："这些字段可能需要定制：xxx、yyy、zzz，你有哪些定制需求？也可以补充其他的。"
2. **用户描述需求**：用户说需求，可能一次多个或逐个说，也可以补充 AI 未识别的
3. **逐个探查关键决策点**：每个需求只问影响实现方式的关键信息：
   - 数据量级 → 决定前端过滤还是后端搜索
   - 选择行为 → 决定组件配置（如树是否只能选叶子）
   - 现有接口 → 决定 service 是复用还是新建
   - 技术细节（debounce 值、renderAfterExpand 等）由 AI 自行决定，不问用户
4. **展示确认**：全部确认后展示完整 customizations yaml 汇总
5. **循环直到完成**：用户说 OK 或继续补充，不预设轮数
6. **持久化**：将确认后的 customizations 写入 `docs/gen-specs/<表名>.yml`

**已有组件 vs 自建组件**：
- 已有组件（如 el-tree-select、el-autocomplete）：写到 props 级，因为接口已知
- 自建组件（type: custom）：只写意图 + 关键约束

如果用户无定制需求，跳过整个阶段 5。

### 5.1 交互示例

以 `pm_project` 表为例，假设字段中有 `dept_id`、`customer_id`、`project_manager`：

```
=== 定制需求探查 ===

AI: 以下字段可能需要定制组件：dept_id、customer_id、project_manager。
    你有哪些定制需求？也可以补充其他字段或页面级需求。

用户: dept_id 做树形选择关联 dept 表，customer_id 做 autocomplete 关联客户表，
     project_manager 做 autocomplete 关联 manager 表

AI: dept_id 树形选择——部门是分层级的，Element Plus 有 el-tree-select。
    选择时是只能选叶子节点，还是任意层级都能选？

用户: 任意层级

AI: customer_id autocomplete——搜索匹配客户名称，提交 customer_id。
    客户数据量大概多少？几十个前端过滤就够，上千就需要后端搜索。

用户: 上万

AI: project_manager autocomplete——同样按姓名搜索。manager 数据量呢？

用户: 几十个

AI: 好的，完整定制规格如下：

customizations:
  dept_tree_select:
    intent: "部门选择，树形结构，任意层级可选"
    component:
      type: el-tree-select
      props:
        data: "部门树数据"
        checkStrictly: true
        valueKey: "id"
        renderAfterExpand: false
    bindTo: dept_id
    service:
      endpoint: "GET /system/dept/treeselect"
      source: "复用 SysDeptService，RuoYi 自带"
      newApi: false
    notes: null

  customer_autocomplete:
    intent: "客户选择，按客户名称远程模糊搜索，数据量大"
    component:
      type: el-autocomplete
      props:
        fetchSuggestions: "后端远程搜索"
        valueKey: "customerName"
        debounce: 300
        triggerOnFocus: false
    bindTo: customer_id
    service:
      endpoint: "GET /project/customer/search?name={keyword}"
      source: "复用 PmCustomerService，需新增轻量搜索接口返回 id+name"
      returns: "[{ customerId, customerName }]"
      newApi: true
    notes: "提交值为 customerId，显示值为 customerName"

  manager_autocomplete:
    intent: "项目经理选择，按姓名搜索，数据量小前端过滤"
    component:
      type: el-autocomplete
      props:
        fetchSuggestions: "前端过滤"
        valueKey: "managerName"
    bindTo: project_manager
    service:
      endpoint: "GET /project/manager/listAll"
      source: "复用 PmManagerService，需新增返回全量 id+name 的接口"
      returns: "[{ managerId, managerName }]"
      newApi: true
    notes: "页面加载时一次性获取全量数据，前端 filter 匹配"

还有其他定制需求吗？

用户: OK

AI: → 写入 docs/gen-specs/pm_project.yml，进入 5.2 改造
```

### 5.2 精细化改造

读取已部署的 Vue 文件和相关后端文件，理解 CLI 生成的代码结构，然后遍历 `customizations` 中的每个功能条目，按规格执行改造：

- **已有组件**（`type` 非 `custom`）：按 `props`/`events` 配置替换标准组件，添加 import
- **自建组件**（`type: custom`）：根据 `spec` 设计组件接口，创建组件文件，集成到页面
- **后端服务**（`service` 非 null）：
  - `newApi: false` → 直接在前端调用已有接口
  - `newApi: true` → 在 Controller/Service/Mapper 中添加新接口
- **bindTo** 决定改造位置：列名→替换表单/表格中对应字段的组件；toolbar/form/dialog/page→在对应区域添加功能

展示修改的文件清单和变更摘要。

---

## 关键约束

1. **不跳阶段**：即使用户很急，也必须展示配置让用户确认后再生成
2. **规格文件是 Source of Truth**：所有配置改动都体现在 `docs/gen-specs/<表名>.yml` 中
3. **CLI 是脚手架**：CLI 生成的是标准代码，自定义 UI 一定在阶段 5 通过代码修改实现
4. **幂等性**：重新生成时，先备份已有文件（如有自定义修改），再覆盖
5. **字段信息展示**：用紧凑的表格格式，`✓` 和 `-` 表示布尔值，避免刷屏