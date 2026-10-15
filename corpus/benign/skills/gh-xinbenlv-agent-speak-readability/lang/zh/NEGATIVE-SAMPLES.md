# Chinese negative samples, taken from a real session

A model wrote every sentence below during one real working session. The reader
found all of them hard to understand. Treat the sentences as negative samples
and do not write anything like them.

## 1. The subject is missing

`跑完了`　`改完之后密度一点没动`　`查了一遍`　`接上了`　`验证通过`
`先看 sources 的当前定义`　`顺带发现一个小问题`　`看扫描进度`

Among those eight samples, `改完之后密度一点没动` does the most damage. The
sample runs to nine characters, and two different actors hide inside those
nine characters. The first actor is the agent, and the agent edited the
prompt. The second actor is the model under test, and that model produced the
density value. The sample names neither actor.

An acceptable version takes two sentences:
`我改完了这一份提示词。被测模型产出的密度数值和改动之前完全一样。`

## 2. Invented words, metaphors and puns

`挤气球`　`墓志铭`　`租一台推土机来种花`　`幻觉工厂`　`气球一定往那边鼓`

A literal phrase already exists for every one of those five, so write the
literal phrase. The literal reading of `挤气球`, for example, is
`我压低一个指标以后，另一个指标就升高`.

## 3. One thing carrying several names in one document

- `提示词` and `prompt`
- `复核`, `审阅` and `QA reviewer`
- `死链` and `dead link`

Choose one name at the start of a reply. Use that one name for the whole
reply.

## 4. Short connective fragments

`先写扫描脚本。`　`看扫描进度。`　`跑一下`

All three fragments announce the next action of the model. All three are
compressed renderings of the English habit `Now let me check the scan.`

Full sentences did not produce the same failure. So the correct repair bans
the fragment register. The correct repair does not try harder inside the
fragment register.
