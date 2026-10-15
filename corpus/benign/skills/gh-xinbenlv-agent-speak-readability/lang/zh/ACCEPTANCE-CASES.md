# Chinese acceptance cases

The user wrote the block below by hand. This file keeps the block character
for character. Never rewrite anything inside the block.

The format of each line is: `original` → `the fix the model produced` → `what
the user actually wanted`.

```
先写扫描脚本。       → 我先写扫描脚本。          → 让我先来写一份扫描脚本。

跑一下               → 我跑一下这两个任务        → 让我跑一下上述两个任务。

没轮到 ivy/joseph    → 队列没轮到 ivy 和 joseph  → ivy 和 joseph 这两个名字对应的任务在我们的
                                                   队列任务里仍然在排队，还未排到队首

验证通过。           → 验证脚本报告通过。        → (?哪个被测试的对象及其行为)已经在我们的
                                                   验证脚本中得到成功验证。
```

Those four corrections are the acceptance standard for Chinese output. Check
every change to this skill against the four corrections first.

## What each correction teaches

### Case 1: never drop the measure word

The fix from the model added only the subject 「我」. The fix dropped the
measure word 「一份」. The sentence the user wanted carries the subject, the
「让我……来……」 form and the measure word 「一份」 together.

Related rules: Z1, Z2 and Z3 in `PRINCIPLES.md`.

### Case 2: a demonstrative must not reach back to the previous sentence

The fix from the model added the subject, and then the fix wrote a new 「这」
into the sentence. That 「这」 points at a noun in the previous sentence, which
is exactly what rule Z4 forbids. The model claimed to repair one rule while it
broke another rule. The sentence the user wanted uses 「上述」 in place of
「这」.

Related rule: Z4.

### Case 3: unpack the compression, and name the category of an identifier

The fix from the model kept the colloquial compression 「没轮到」. The fix also
left `ivy` and `joseph` as bare tokens with no category word. The fix never
said what kind of thing `ivy` and `joseph` are.

The sentence the user wanted names the objects (`名字`, `任务`), the relation
(`对应的`), the location (`在我们的队列任务里`) and the state
(`仍然在排队`). That sentence also unpacks the compression into a literal
description (`还未排到队首`).

Related rules: R1, R4 and R8 across languages, and Z5 in Chinese.

### Case 4: the most important one. Never drop the object of the action

The fix from the model named the actor (`验证脚本`) and still left out the
thing that was verified. The user wrote `(?哪个被测试的对象及其行为)` as an
explicit empty slot. That slot demands the tested object and the tested
behaviour.

Naming the actor does not complete the action. That is the reason R1 is the
master rule.

Related rule: R1.

## One conclusion

The model added only the subject in all four attempts. Adding the subject is
the easiest step to take, and adding the subject is also the least sufficient
step. Ask the verb "to what?" before you ask the verb "by whom?".
