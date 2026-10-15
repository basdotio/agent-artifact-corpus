# Voices

Real ElevenLabs voice ids, checked on 27 Sep 2026. Pick from these lists
only. Never write an id from memory, and never pick from everything
`ELEVENLABS_GET_VOICES` returns.

That list mixes accents. On a typical account, 75 voices say they can speak
French, but many aren't from France:
- **American and British voices** are marked "can speak French", and they read
  it with an English accent.
- **Canadian voices:** some are Québécois (`quebec`, locale `fr-CA`) and some
  Acadian (`acadian`).

A voice with the wrong accent is the most noticeable mistake a video can make.

## Rules

- **Only native voices:** a voice reads only its own language, with the accent
  the audience expects.
  - French for France: a voice whose `labels.accent` is `parisian` or
    `standard`, and whose `verified_languages` include `fr-FR` for the model
    you use.
  - English: the default voices below.
- **Model:** French and every language other than English use
  `eleven_multilingual_v2`, the model these voices are checked on. On other
  models the accent drifts. `eleven_v3` is for English lines that use audio
  tags such as `[excited]`.
- **Always set `model_id`:** the text-to-speech tool defaults to an
  English-only model.
- **Same settings throughout:** one voice per speaker, with the same id, model
  and settings for every line. Characters get clearly different voices, and a
  narrator gets a warm, steady one.
- **Adding a missing voice:** a voice from the lists below that the account
  lacks is added with `ELEVENLABS_ADD_SHARING_VOICE` (`public_user_id`,
  `voice_id`, `new_name`).

## French (France): native voices, verified fr-FR on eleven_multilingual_v2

| Voice | voice_id | public_user_id | Sounds like | Good for |
|---|---|---|---|---|
| Julia | `mNu8EQcIlFZdOJs7yfhe` | `29953a0c704089a7251918e3bac7696c96c21e47bb5986e11993f670629cad45` | Female, young, Parisian, warm | Narratrice |
| Victoria | `WeAAwKYcS06VmXw086yZ` | `e092f85cb7961adee2d248867d9dd185b3e890dff12b5d91c4fed26991b00c2f` | Female, mature, Parisian, warm and calm | Narratrice posée |
| Aurore | `ucMmKRQbfDEYyb2IIGax` | `560236f8bd84bf1c323a911b351afdc3f24b7caf18686d4d6b48229109791977` | Female, mature, Parisian, calm | Explications, bien-être |
| Anna B | `nVPCtAFzgyMX3FZKNzH0` | `aca2e213c5a59a5d2804c3ab7f4dbfb041d5a64df3694b39dc1c74402c811bba` | Female, mature, Parisian | Personnage adulte |
| Emilie | `i6ke7jvmGEVUyV4zjSaT` | `c96a60f175f9cda55b0d4f08cebf47fc72a91a94188b461522707055362ee021` | Female, young, Parisian, clear and professional | Personnage pro |
| Chloé | `Hy28BjVfgieDVMiyQpQe` | `35872a3bbdcf2ab5c31f372e17a9de68e06558dc42a401f6aa9b4f946dd07ca9` | Female, standard French, warm and friendly | Réseaux sociaux |
| Mr. Laurent | `necQJzI1X0vLpdnJteap` | `f608ab06bc2fb58783b818fea280ed87db55a53a14cb8776def13d607c3a4a8d` | Male, mature, Parisian, podcast | Narrateur |
| Simon | `mvhJVdVoTWVUtL4keT7W` | `fa7924e0ceac79b7d7e1f995a0be2312c2db6fe08dd809fe2e574c60499c7308` | Male, young, Parisian, radio | Narrateur dynamique |
| Martin Dupont | `wyZnrAs18zdIj8UgFSV8` | `e9a6840c69b79812b77ea81fa11d55aaf80dcf1938fa0137bf7f514f67f75c99` | Male, mature, standard French, deep | Personnage âgé |
| Léo | `jsScnYkNNda9Q1NES5nn` | `b93a441072478a6c07e14c6b5d7dc7b6f42425247e3687d71473dc8d840140d3` | Male, young, standard French, energetic | Personnage dynamique |
| Hugo | `IbbR6Av0dWuQJS0b8JVT` | `2eff6bde584aa6471c181410ab4bb82907fd07a91c7daf2d6f90fd262282a900` | Male, young, standard French, grounded | Personnage jeune |
| Kael | `yG4Uc56cLYQyZFnWaYv2` | `1d0fc0a5dde1dae0864c6ca869acc4e686f61a178c8c3c8560e3d752df40bb9e` | Male, young, Parisian narrator (paid plans only) | Narrateur |
| Sébastien | `BUJMBsQ3Oq4cEeWSb48y` | `a0bdfd7ee0a5f2af6ab593a5d7235be2c86f4b7d43cb8abd55b95a982b2d3aa8` | Male, 35, standard French (paid plans only) | Personnage posé |

## English: default voices (every account has them), for English only

| Voice | voice_id | Sounds like | Good for |
|---|---|---|---|
| George | `JBFqnCBsd6RMkjVDRZzb` | Male, British, warm storyteller | Narrator |
| Alice | `Xb7hH8MSUJpSbSDYk0k2` | Female, British, clear educator | Narrator, explainers |
| Daniel | `onwK4e9ZLuTAKqWW03F9` | Male, British, steady broadcaster | Announcements |
| Sarah | `EXAVITQu4vr4xnSDxMaL` | Female, American, reassuring | Product, support |
| Brian | `nPczCjzI2devNBz1zQrb` | Male, American, deep and comforting | Calm narration |
| Jessica | `cgSgspJ2msm6clMCkdW9` | Female, young, American, playful | Cheerful character |
| Laura | `FGY2WhTYpPnrIDTdsKH5` | Female, young, American, quirky | Funny character |
| Lily | `pFZP5JQG7iQjIQuC4Bku` | Female, British, velvety | Elegant character |
| Liam | `TX3LPaxmHKxFdv7VOQHJ` | Male, young, American, energetic | Hype, social media |
| Charlie | `IKne3meq5aSn9XLyUdCD` | Male, young, Australian, hyped | Energetic character |
| Chris | `iP95p4xoKVk53GoZ742B` | Male, American, casual | Friendly character |
| Bill | `pqHfZKP75CvOlQylNhV4` | Male, older, American, wise | Mentor, grandpa |

## Another language, or a voice not listed here

Check it before using it: `ELEVENLABS_GET_VOICE` with its id. Use it only
when:
- its `labels.accent` is the accent the audience expects, not `american`,
  `british` or another language's region;
- its `verified_languages` include the target locale (for example `fr-FR`,
  `es-ES`, `de-DE`) for the model you use.

## Models

| model_id | When |
|---|---|
| `eleven_multilingual_v2` | French and every non-English language; the default for English too. |
| `eleven_v3` | English lines that use audio tags like `[excited]`, `[whispers]`, `[giggles]`. |
