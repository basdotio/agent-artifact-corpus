---
title: Vítej — jak AgentVault funguje
category: Guide
type: hub
tags: [guide, start, meta]
---

Toto je **AgentVault** — tvé přenosné poznámky (Markdown), které spolu odkazují a jdou
prohledávat sémanticky. Demo klidně smaž a nahraď vlastními soubory.

## Jak to funguje
- **Jedna poznámka = jedna myšlenka.** Linkuj přes `[[název]]`.
- **Kategorie** = složka nahoře (nebo pole `category:`).
- **Hledání** je hybridní (význam + klíčová slova).
- **Agenti** používají CLI `./av search` nebo MCP nástroje `vault_search` / `vault_get` /
  `vault_neighbors` / `vault_write`.

## Co je v demu
- **[[Books]]**, **[[Authors]]**, **[[Quotes]]** — ukázková síť odkazů.

Začni třeba u [[Man's Search for Meaning]] nebo [[Meditations]].
