---
name: kotlin-oo-fundamental
description: |
  Orientar modelagem orientada a objetos em Kotlin para APIs robustas, evolutivas e interoperáveis com Java 8. Use when: o agente precisa projetar, refatorar ou justificar decisões de OO em Kotlin.
---

# kotlin-oo-fundamental

Overview
Kotlin fornece construções OO modernas (classes, interfaces com implementações, propriedades, delegação). Esta skill apresenta práticas pragmáticas para projetar hierarquias e APIs que sejam fáceis de manter e interoperáveis com Java 8.

When to Use
- Modelagem de domínio rico com invariantes e comportamento associado ao estado.
- Encapsulamento de estado mutável localizado (caches, adaptadores I/O).
- Módulos que requerem injeção de dependências e testes de unidade robustos.

Best Practices
- Privilegia a Composição em vez da Herança; use Class Delegation (`by`) para reutilização comportamental.
- Favor `private` + `val` para invariantes internos; exponha contratos via interfaces imutáveis.
- Use `internal` para delimitar módulos e reduzir superfície pública.
- Aplique SOLID adaptado a Kotlin: responsabilidades únicas, interfaces coesas e inversão de dependência.
- Use Data Classes para value-objects e Sealed Classes para hierarquias fechadas; mantenha lógica de negócio fora de DTOs.
- Documente contratos de visibilidade, thread-safety e invariantes na API pública.

Pitfalls and Corrections
- Heranças profundas: prefira delegação e composição de objetos pequenos.
- Companion objects como depósito de utilitários: mover utilitários para objetos bem nomeados ou pacotes utilitários.
- Expor campos mutáveis: expor apenas interfaces imutáveis (List em vez de MutableList).
- Abrir classes (`open`) sem contrato: declarar intenções de extensão e documentar invariantes.

Reference Routing
- Ler references/classes_and_hierarchies.md para detalhes sobre data classes, sealed classes, delegation e design de hierarquias.
- Ler references/objects_and_java8_interop.md para object/companion patterns e uso de anotações @Jvm* para compatibilidade com Java 8.
- Regra prática: aplicar Best Practices em PRs; consultar referências para interoperabilidade e hierarquias complexas.

How to design extensible domain models
1. Modelar entidades com comportamento coeso e responsabilidades única por classe.
2. Definir interfaces explícitas para acoplamento e testes; fornecer implementações via injeção.
3. Usar sealed classes para estados finitos e when exaustivo.

How to expose Kotlin OO patterns to Java 8
1. Fornecer overloads e anotações @Jvm* para ergonomia Java.
2. Oferecer factory methods estáticos (@JvmStatic) e builders quando parâmetros default não são triviais para Java.
3. Documentar no KDoc como consumidores Java devem usar a API.
