# Additional rules for Chinese output

Apply the nine cross-language rules in `../../SKILL.md` first. Then apply the
eight rules below. Then run the extra check steps at the end of this file.

The rules are written in English. The examples stay in Chinese, because the
examples are the thing being taught.

## Z1. Write the subject of every sentence, including 我

Chinese allows a speaker to drop the subject. That is why a dropped subject is
the most frequent failure in Chinese agent output. Find the subject of each
sentence you wrote. Write the subject in when no subject exists.

- Not acceptable: `跑完了。`
- Acceptable: `我跑完了这一轮扫描任务。`

Cross-language rule R1 already asks for every argument of the action, and the
subject is one of those arguments. Chinese states the rule again as Z1,
because Chinese loses the subject far more often than English does.

## Z2. Announce your own next action with the full form 「让我……来……」

Do not announce your action with a phrase that has no subject. Do not announce
your action with an imperative sentence. An imperative sentence orders the
reader to act, and you are the one who acts.

- Not acceptable: `先写扫描脚本。`
- Not acceptable: `跑一下。`
- Acceptable: `让我先来写一份扫描脚本。`
- Acceptable: `让我来跑一下上述两个任务。`

## Z3. Never drop the numeral and the measure word

Write the quantity and the measure word in front of a noun. Text without them
turns into telegraphic register, and the reader has to work harder.

- Not acceptable: `我写扫描脚本。`
- Acceptable: `我写一份扫描脚本。`
- Not acceptable: `我改了配置。`
- Acceptable: `我改了这一项配置。`

## Z4. Use 「上述」 or 「前面提到的」 to point at earlier text

A demonstrative may point only at a noun written in the same sentence. To
point at a noun in an earlier sentence, repeat the noun and put 「上述」 or
「前面提到的」 in front of the repeated noun.

- Not acceptable: `我跑一下这两个任务。` (「这」 reaches back to the previous sentence)
- Acceptable: `我跑一下上述两个任务。`
- Acceptable: `ivy 和 joseph 这两个名字对应的任务仍然在排队。` (「这」 points at
  `ivy` and `joseph` inside the same sentence, so the sentence is acceptable)

## Z5. Do not use compressed colloquial speech

Colloquial compression hides the action and the object. Rewrite the
compression as a literal description.

| Compressed | Literal description |
| --- | --- |
| 没轮到 ivy | `ivy` 这个名字对应的任务还未排到队首 |
| 搞定了 | 我已经改完了这一处代码，并且验证脚本报告通过 |
| 打通了 | 上游服务和下游服务之间的调用已经成功返回 |
| 接上了 | 我已经把这一个钩子挂到 `bun install` 上 |
| 跑完了 | 我跑完了这一轮扫描任务 |

## Z6. Use the Chinese word when a Chinese word exists

Words such as 会话, 提示词, 任务, 模式 and 字段 all have ordinary Chinese
forms, so write the Chinese form. Keep code identifiers unchanged, for example
`responseSchema`, `item_id` and `--links`.

One thing carries one name inside one reply. Never alternate between 提示词
and `prompt`.

## Z7. Mark tense with 了, 将, 已 and 可以

A Chinese verb carries no tense of its own, so you have to write the tense
marker. Write 「已经……了」 for a finished action. Write 「我将要」 or
「我接下来要」 for an action that has not started. Write 「可以」 or
「有可能」 for a possibility.

- Not acceptable: `我改这一个字段。`
- Acceptable: `我已经改完了这一个字段。`
- Acceptable: `我接下来要改这一个字段。`

## Z8. Keep a sentence under 40 characters and a paragraph under 6 sentences

Count the characters of the longest sentence. Split that sentence at a clause
boundary when the count is over 40 characters. Give every new sentence its own
subject. Count the sentences of the longest paragraph. Start a new paragraph
when the count is over 6 sentences. Never shorten a sentence by deleting an
argument of the verb.

## Z9. Extra check steps for Chinese

Run the ten steps in section 4 of `../../SKILL.md` first. Then run these five
steps.

1. Read each sentence and find the subject. Write the subject in when the
   sentence has none.
2. Find every phrase that announces your next action. Rewrite each phrase as a
   full 「让我……来……」 sentence.
3. Find every noun. Add the numeral and the measure word.
4. Find every demonstrative. Rewrite it as 「上述」 plus the repeated noun when
   the noun it points at sits in an earlier sentence.
5. Find every colloquial compression. Rewrite each one as a literal
   description.

## Z10. Acceptance cases

`ACCEPTANCE-CASES.md` holds four corrections that the user wrote by hand.
Those four corrections are the acceptance standard for Chinese. Check every
change to this file against those four corrections first.
