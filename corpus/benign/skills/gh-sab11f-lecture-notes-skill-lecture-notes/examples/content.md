---
course: Matematika 1
chapter: 1
title: Logika in množice
institution: Fakulteta za informacijske študije v Novem mestu
source: Prosojnice: K. Bešter Štorgel / J. Povh (2026)
accent: "#1d5c8a"
lang: sl
solutions: inline
videos: astra.si
binding: left
---

# Osnove matematičnega sklepanja

::: idea Zakaj to sploh potrebujemo
Matematika ni kup formul, ampak **sistem sklepanja**: iz nekaj osnovnih, nedokazanih trditev (aksiomov) z logičnimi koraki izpeljemo vse ostalo. To poglavje postavi orodja, s katerimi se to sklepanje sploh lahko zapiše in preveri: izjave, logične operacije, kvantifikatorje in množice.
:::

::: def Aksiom
Aksiom je temeljna resnica izbrane teorije, ki je **ne dokazujemo**. Aksiome si izberemo sami in iz njih zgradimo teorijo.
:::

Aksiome izbiramo tako, da

- **niso protislovni** (iz njih ne moremo izpeljati hkrati trditve in njene negacije),
- **vsebujejo vse »znanje«** (lastnosti), ki nas v teoriji zanima.

::: def Izrek
Izrek je nova trditev, ki jo iz aksiomov (in že dokazanih izrekov) izpeljemo z logičnim sklepanjem. Vse znanje je torej skrito že v aksiomih, izreki ga le razkrijejo.
:::

::: ex Aksiom naravnih števil
Ko govorimo o naravnih številih, je eden od aksiomov: *vsako naravno število $n$ ima svojega naslednika $n+1$.* Pri množicah bomo spoznali celoten sistem – Peanove aksiome.
:::

@@flow Aksiomi | Logično sklepanje | Izreki | Novi rezultati

::: warn Russellov paradoks – kaj se zgodi, če definicija ni dobra
*Brivec Jože brije natanko tiste moške, ki se ne brijejo sami. Kdo brije Jožeta?*
Če se Jože brije sam, potem po definiciji ne sme briti sebe. Če se ne brije sam, ga mora briti brivec – torej on sam. Oboje je protislovno.

Enako v jeziku množic: naj bo $M$ množica vseh množic, ki ne vsebujejo same sebe. Potem $M \in M \Leftrightarrow M \notin M$.

**Razlog:** neustrezna (preohlapna) definicija množice. Zato aksiome in definicije postavljamo previdno.
:::

::: video
- Logika in Russelova antinomija — `youtu.be/XNGKiK4_C5Q` (5:10)
:::

# Logika in izjavni račun

::: idea Kratka zgodovina
*Logos* (gr. λόγος) pomeni razum, um. Rojstni kraj logike je Grčija, največja avtoriteta do novega veka je **Aristotel** (384–322 pr. n. št.). Utemeljitelji moderne (matematične, formalne) logike: **Augustus De Morgan** (1806–1871), **George Boole** (1815–1864), **Georg Cantor** (1845–1918), **Bertrand Russell** (1872–1970).
:::

::: warn Napaka na prosojnicah
Prosojnice navajajo Cantorja z letnicama 1874–1895 – to sta leti njegovih ključnih del, ne življenjski letnici. Cantor je živel 1845–1918.
:::

::: def Izjava
Trdilni ali nikalni stavek je **smiseln**, če lahko nedvoumno in objektivno odločimo, ali je njegova vsebina resnična ali neresnična. Vsi smiselni stavki, ki trdijo isto, določajo eno **enostavno izjavo**.
:::

- Resnične izjave označimo z **1**, neresnične z **0**.
- Osnovne izjave povezujemo v **sestavljene izjave**.
- Posamezne izjave obravnavamo **kot celote** – njihova notranja zgradba nas ne zanima. (Izjavni račun gleda samo, ali je izjava 1 ali 0, ne *zakaj*.)

::: ex Kaj je izjava in kaj ni
| Stavek | Izjava? | Zakaj |
|---|---|---|
| »Zunaj dežuje.« | da | Objektivno preverljivo. |
| »Srečno pot!« | ne | Želja, nima resničnostne vrednosti. |
| »Jutri bom šel na predavanja ali pa ne bom šel.« | da, **vedno 1** | Resnična ne glede na to, kaj se zgodi. |
| »Jutri bom šel na predavanja in ne bom šel.« | da, **vedno 0** | Neresnična ne glede na to, kaj se zgodi. |
:::

Pravilnost izjave ugotavljamo v dveh korakih: (1) ugotovimo natančen smisel stavka, (2) primerjamo, kar stavek pove, z dejanskim stanjem.

::: task Paradoks lažnivca
Analizirajte pravilnost stavka **»Jaz lažem.«** Ali je to izjava?
:::
@@space 3.5
::: sol
Denimo, da je stavek resničen – potem govorec res laže, torej je stavek neresničen. Denimo, da je neresničen – potem govorec ne laže, torej govori resnico in je stavek resničen. Vsaka možnost vodi v svoje nasprotje.

Stavek **nima nedvoumne resničnostne vrednosti**, zato po definiciji **ni izjava**. To je *paradoks lažnivca* – sorodnik Russellovega paradoksa: samonanašanje podre definicijo.
:::

::: video
- Izjave in logika — `youtu.be/hC_WZuwWDmo` (3:28)
- Vrednost izjave 1 — `youtu.be/_4c9bYHxAVQ` (3:34)
- Vrednost izjave 2 — `youtu.be/tTYL7EW3wKI` (5:21)
- Ugotavljanje pravilnosti izjave 1 — `youtu.be/FwJ2u6MjuPw` (1:32)
- Ugotavljanje pravilnosti izjave 2 — `youtu.be/3fF3d7WeNVQ` (1:16)
- Ugotavljanje pravilnosti izjave 3 — `youtu.be/K2z8glgLjmw` (2:21)
:::

# Operacije nad izjavami

::: idea Pet operacij, ena logika
Vse sestavljene izjave gradimo iz petih operacij. Vsako operacijo popolnoma določa njena **pravilnostna tabela**: pove, kakšna je vrednost rezultata za vsako kombinacijo vrednosti vhodov. Če znaš tabele, znaš vse.
:::

## Negacija ¬

::: def Negacija
Negacija izjave $A$ je pravilna natanko tedaj, ko je $A$ nepravilna. Oznaka: $\neg A$ ali $\bar{A}$. Jezikovno: pred izjavo dodamo »Ni res, da …«.
:::

@@truth A; ¬A | 0,1 | 1,0 | cap=Pravilnostna tabela negacije

::: ex
$A$: »Zunaj dežuje.« → $\neg A$: »Ni res, da zunaj dežuje.« = »Zunaj ne dežuje.«
:::

::: task Negacija izjave z »vsi«
$A$: »Vsi vpisani študenti so prišli na predavanja.« Kaj je $\neg A$? Zapišite jo brez »ni res, da«.
:::
@@space 3
::: sol
$\neg A$: »Ni res, da so vsi vpisani študenti prišli na predavanja« = »**Vsaj en** vpisani študent ni prišel na predavanja.«

**Pogosta napaka:** »Nihče ni prišel.« To je premočno – negacija »vsi« je »vsaj en ne«, ne »noben«. (Formalno: $\neg\forall x: A(x) \equiv \exists x: \neg A(x)$, glej poglavje 6.)
:::

## Konjunkcija ∧ (logični IN)

::: def Konjunkcija
Konjunkcija izjav $A$ in $B$ je pravilna natanko tedaj, ko sta **obe** izjavi pravilni. Oznaka: $A \wedge B$.
:::

@@truth A; B; A ∧ B | 0,0,0 | 0,1,0 | 1,0,0 | 1,1,1 | hl=3 | cap=Konjunkcija: resnična samo v zadnji vrstici

::: ex
$A$: »Zunaj dežuje.«, $B$: »Zunaj grmi.« → $A \wedge B$: »Zunaj dežuje in grmi.«
:::

## Disjunkcija ∨ (logični ALI)

::: def Disjunkcija
Disjunkcija izjav $A$ in $B$ je pravilna, če je **vsaj ena** izjava pravilna. Oznaka: $A \vee B$.
:::

@@truth A; B; A ∨ B | 0,0,0 | 0,1,1 | 1,0,1 | 1,1,1 | hl=0 | cap=Disjunkcija: neresnična samo v prvi vrstici

::: warn Ali ni »ali–ali«
Logični ALI je **vključujoč**: $A \vee B$ je resnična tudi, ko veljata obe. Vsakdanji »ali« (»kava ali čaj«) je pogosto izključujoč – v logiki ni.
:::

## Implikacija ⇒

::: def Implikacija
Implikacija se izraža v obliki »**Če** $A$, **potem** $B$.« Oznaka: $A \Rightarrow B$. Neresnična je **samo** v primeru, ko je $A$ resnična in $B$ neresnična.
:::

@@truth A; B; A ⇒ B | 0,0,1 | 0,1,1 | 1,0,0 | 1,1,1 | hl=2 | cap=Implikacija: neresnična samo, ko je A = 1 in B = 0

::: ex Smer je pomembna
$A$: »Število $n$ je deljivo s 3.«, $B$: »Število $n$ je deljivo s 6.«

- $A \Rightarrow B$: »Če je $n$ deljivo s 3, potem je deljivo s 6.« – **neresnična** (protiprimer: $n=9$).
- $B \Rightarrow A$: »Če je $n$ deljivo s 6, potem je deljivo s 3.« – **resnična**.
:::

::: task Obljuba očeta Andreja
Oče reče: »Če moj sin Blaž naredi maturo, potem mu kupim avto.« V katerih primerih oče govori resnico oziroma izpolni obljubo? Obravnavajte vse štiri kombinacije.
:::
@@space 4.5
::: sol
| Matura ($A$) | Avto ($B$) | $A \Rightarrow B$ | Komentar |
|---|---|---|---|
| 1 | 1 | 1 | Obljuba izpolnjena. |
| 1 | 0 | **0** | Edini primer, ko je oče lagal. |
| 0 | 1 | 1 | Obljuba ni bila prelomljena – avto je lahko kupil iz drugega razloga. |
| 0 | 0 | 1 | Obljuba ni bila prelomljena. |

**Ključno:** če pogoj ($A$) ni izpolnjen, implikacija velja ne glede na $B$. Obljuba govori samo o primeru, ko Blaž maturo naredi.
:::

::: warn Najpogostejša napaka pri implikaciji
Iz $0 \Rightarrow$ karkoli sledi 1. »Če je $2+2=5$, potem sem papež« je **resnična** izjava. Implikacija ne trdi, da je $A$ resnična – trdi le, da $B$ ne more biti 0, kadar je $A$ 1.
:::

## Ekvivalenca ⇔

::: def Ekvivalenca
Ekvivalenca se izraža v obliki »$A$ velja **natanko tedaj**, ko velja $B$« oz. »$A$ velja, **če in samo če** velja $B$.« Oznaka: $A \Leftrightarrow B$. Resnična je, ko imata $A$ in $B$ **enako** vrednost.
:::

@@truth A; B; A ⇔ B | 0,0,1 | 0,1,0 | 1,0,0 | 1,1,1 | cap=Ekvivalenca: resnična, ko imata A in B enako vrednost

::: ex
$A$: »$n$ je deljivo s 3 **in** s 5.«, $B$: »$n$ je deljivo s 15.« → $A \Leftrightarrow B$ je **resnična**.

Toda: »$n$ je deljivo s 3 **ali** s 5 natanko tedaj, ko je deljivo s 15« je **neresnična** (protiprimer: $n = 3$).
:::

::: task Obljuba, drugič
Oče reče: »Sinu Blažu kupim avto, **če in samo če** naredi maturo.« V katerih primerih oče govori resnico? V čem se razlikuje od prejšnje naloge?
:::
@@space 4
::: sol
| Matura ($A$) | Avto ($B$) | $A \Leftrightarrow B$ | Komentar |
|---|---|---|---|
| 1 | 1 | 1 | Obljuba izpolnjena. |
| 1 | 0 | **0** | Lagal – matura brez avta. |
| 0 | 1 | **0** | Lagal – avto brez mature (»samo če« to prepoveduje). |
| 0 | 0 | 1 | Obljuba izpolnjena. |

Zdaj oče laže v **dveh** primerih namesto v enem. Ekvivalenca je strožja od implikacije – obljuba velja v **obe smeri**: matura ⇒ avto **in** avto ⇒ matura.
:::

## Prednost logičnih operacij

Prednost označimo z oklepaji. Brez oklepajev velja vrstni red (najvišja prednost se ovrednoti prva):

@@ladder ¬:negacija | ∧:konjunkcija | ∨:disjunkcija | ⇒:implikacija | ⇔:ekvivalenca | left=najvišja prednost (ovrednoti se prva) | right=najnižja prednost (ovrednoti se zadnja)

::: ex
- $A \wedge (B \vee C)$: najprej disjunkcija, nato konjunkcija.
- $A \wedge B \vee C$ = $(A \wedge B) \vee C$: najprej konjunkcija.
- $A \Rightarrow B \wedge C$ = $A \Rightarrow (B \wedge C)$.
:::

::: task Tri kroglice
Ugotovite, ali je na podlagi resničnosti danih predpostavk izjava resnična ali neresnična. Vse izjave se nanašajo na tri kroglice: **A je rdeča, B je rumena, C je modra.**

**(a)** »Ni res, da je A rdeča in C ni rumena.«

**(b)** »A je rumena, če in samo če sta B in C modri.«

**(c)** »Če je A rumena, potem sta B in C rdeči.«
:::
@@space 6
::: sol
Vsak stavek prevedemo v logični izraz, vstavimo vrednosti (A rdeča = 1, A rumena = 0, …) in ovrednotimo po prednosti operacij.

**(a)** $\neg(\underbrace{\text{A rdeča}}_{1} \wedge \neg\underbrace{\text{C rumena}}_{0}) = \neg(1 \wedge 1) = \neg 1 = 0$ → **neresnična**.

**(b)** $\underbrace{\text{A rumena}}_{0} \Leftrightarrow (\underbrace{\text{B modra}}_{0} \wedge \underbrace{\text{C modra}}_{1}) = 0 \Leftrightarrow 0 = 1$ → **resnična** (obe strani neresnični).

**(c)** $\underbrace{\text{A rumena}}_{0} \Rightarrow (0 \wedge 0) = 0 \Rightarrow 0 = 1$ → **resnična** (pogoj ni izpolnjen, implikacija velja avtomatično).
:::

::: task Dodatna naloga: pravilnostna tabela sestavljene izjave
Sestavite pravilnostno tabelo za izjavo $\neg A \vee (A \wedge B)$ in ugotovite, ali je logično ekvivalentna izjavi $A \Rightarrow B$.
:::
@@space 6
::: sol
Stolpce gradimo od notranjih izrazov navzven, po prednosti operacij.

| $A$ | $B$ | $\neg A$ | $A \wedge B$ | $\neg A \vee (A \wedge B)$ | $A \Rightarrow B$ |
|---|---|---|---|---|---|
| 0 | 0 | 1 | 0 | **1** | 1 |
| 0 | 1 | 1 | 0 | **1** | 1 |
| 1 | 0 | 0 | 0 | **0** | 0 |
| 1 | 1 | 0 | 1 | **1** | 1 |

Zadnja dva stolpca se ujemata v vseh vrsticah → izjavi **sta ekvivalentni**: $\neg A \vee (A \wedge B) \equiv A \Rightarrow B$. (Z identitetami: distributivnost da $(\neg A \vee A) \wedge (\neg A \vee B) \equiv 1 \wedge (\neg A \vee B) \equiv \neg A \vee B$, kar je identiteta implikacije.)
:::

::: video
- Negacija — `youtu.be/DSphuRfWV-Q` (2:37)
- Konjunkcija — `youtu.be/HjKsJimNvQ0` (4:53)
- Disjunkcija — `youtu.be/BtlKXI_aIi8` (6:31)
- Implikacija — `youtu.be/UdvXiGRerZ4` (5:32)
- Ekvivalenca — `youtu.be/zvniRIuFPis` (3:57)
- Vrstni red računanja v izjavnem računu — `youtu.be/TSPsDcuVdRQ` (2:41)
- Vrstni red računanja – naloga 1 — `youtu.be/gVnzSwpuJCc` (8:31)
- Vrstni red računanja – naloga 2 — `youtu.be/yf3OEP_vh14` (7:26)
- Vrstni red računanja – naloga 3 — `youtu.be/SK2OqvHfYQQ` (8:33)
:::

# Logične identitete in posebne izjave

::: def Logična identiteta
Če sta izjavi $A$ in $B$ **ekvivalentni** (v vseh situacijah hkrati resnični oz. neresnični), lahko ena nadomesti drugo. Zapišemo $A \equiv B$ in pravimo, da je $A$ logično ekvivalentna $B$.
:::

::: idea Razlika med ≡ in ⇔
$A \Leftrightarrow B$ je **izjava** (lahko je 0 ali 1). $A \equiv B$ je **trditev o izjavah**: pove, da je $A \Leftrightarrow B$ tavtologija. Zato: če v identiteti $\equiv$ zamenjamo z $\Leftrightarrow$, dobimo tavtologijo.
:::

::: thm Pomembne identitete
| Ime | Identiteta |
|---|---|
| Nevtralni/absorpcijski element | $A \vee 0 \equiv A$, $A \wedge 0 \equiv 0$, $A \vee 1 \equiv 1$, $A \wedge 1 \equiv A$ |
| Dvojna negacija | $A \equiv \neg\neg A$ |
| Idempotentnost | $A \equiv A \wedge A$, $A \equiv A \vee A$ |
| 1. De Morganov zakon | $\neg(A \wedge B) \equiv \neg A \vee \neg B$ |
| 2. De Morganov zakon | $\neg(A \vee B) \equiv \neg A \wedge \neg B$ |
| Identiteta implikacije | $A \Rightarrow B \equiv \neg A \vee B$ |
| Identiteta ekvivalence | $A \Leftrightarrow B \equiv (A \Rightarrow B) \wedge (B \Rightarrow A)$ |
| Absorpcija | $A \wedge (A \vee B) \equiv A$, $A \vee (A \wedge B) \equiv A$ |
| Distributivnost disjunkcije | $A \vee (B \wedge C) \equiv (A \vee B) \wedge (A \vee C)$ |
| Distributivnost konjunkcije | $A \wedge (B \vee C) \equiv (A \wedge B) \vee (A \wedge C)$ |
:::

::: idea Kako si zapomniti De Morgana
Negacija »prebije« oklepaj in **obrne** operacijo: $\wedge \leftrightarrow \vee$. »Ni res, da dežuje in grmi« = »ne dežuje **ali** ne grmi«.
:::

::: task Dokaz z identitetami
Z uporabo logičnih identitet pokažite, da sta izjavi $\neg(A \Rightarrow B)$ in $A \wedge \neg B$ logično ekvivalentni. Pri vsakem koraku napišite, katero identiteto ste uporabili.
:::
@@space 4
::: sol
$$\begin{aligned}
\neg(A \Rightarrow B) &\equiv \neg(\neg A \vee B) && \text{(identiteta implikacije)}\\
&\equiv \neg\neg A \wedge \neg B && \text{(2. De Morganov zakon)}\\
&\equiv A \wedge \neg B && \text{(dvojna negacija)}
\end{aligned}$$

**Pomen:** implikacijo ovržemo tako, da pokažemo primer, kjer velja $A$ in ne velja $B$ – to je protiprimer.
:::

::: def Tavtologija in protislovje
**Tavtologija** je sestavljena izjava, ki je **vedno resnična**. **Protislovje** (kontradikcija) je izjava, ki je **vedno neresnična**.
:::

::: ex
- Tavtologija: $A \vee \neg A$ (zakon izključene tretje možnosti).
- Protislovje: $A \wedge \neg A$.
- Negacija tavtologije je protislovje in obratno.
:::

::: task Dodatna naloga: De Morgan s tabelo in v besedah
**(a)** S pravilnostno tabelo dokažite 1. De Morganov zakon $\neg(A \wedge B) \equiv \neg A \vee \neg B$.

**(b)** Zapišite negacijo izjave »Zunaj dežuje in grmi.« brez »ni res, da«.
:::
@@space 6
::: sol
**(a)**

| $A$ | $B$ | $A \wedge B$ | $\neg(A \wedge B)$ | $\neg A$ | $\neg B$ | $\neg A \vee \neg B$ |
|---|---|---|---|---|---|---|
| 0 | 0 | 0 | **1** | 1 | 1 | **1** |
| 0 | 1 | 0 | **1** | 1 | 0 | **1** |
| 1 | 0 | 0 | **1** | 0 | 1 | **1** |
| 1 | 1 | 1 | **0** | 0 | 0 | **0** |

Stolpca $\neg(A \wedge B)$ in $\neg A \vee \neg B$ sta enaka → identiteta velja. $\blacksquare$

**(b)** »Zunaj **ne** dežuje **ali** **ne** grmi.« (Ne: »ne dežuje in ne grmi« – to bi bila negacija disjunkcije.) Dovolj je, da ena od obeh stvari ne velja.
:::

# Sklepanje

::: idea Osnovno vprašanje logike
Kako iz tega, kar vemo, *pravilno* izpeljati novo? Sklepanje formaliziramo kot implikacijo, ki mora biti tavtologija – torej veljati v **vseh** situacijah, ne le v tej konkretni.
:::

::: def Sklep
Naj bodo $A_1, \dots, A_n$ in $B$ izjave. Izjavi
$$(A_1 \wedge \cdots \wedge A_n) \Rightarrow B \qquad (1)$$
priredimo izraz $A_1, \dots, A_n \models B$, ki mu pravimo **sklep**. Izjave $A_i$ so **predpostavke (premise)**, $B$ je **zaključek**.

Sklep je **veljaven**, če je (1) tavtologija; sicer je neveljaven. Če je sklep veljaven, je $B$ **logična posledica** izjav $A_1, \dots, A_n$.
:::

::: thm Klasični sklepi
| Sklep | Shema | Zgled |
|---|---|---|
| **Konjunkcija** | $A,\ B \models A \wedge B$ | 120 je deljivo s 6. 120 je deljivo z 8. Torej je 120 deljivo s 6 in 8. |
| **Modus ponens** (pogojna eliminacija) | $A,\ A \Rightarrow B \models B$ | 120 je deljivo s 6. Če je 120 deljivo s 6, je deljivo s 3. Torej je 120 deljivo s 3. |
| **Resolucija** (sklepanje s protislovjem) | $A \vee B,\ A \vee \neg B \models A$ | 10 je sodo ali praštevilo. 10 je sodo ali ni praštevilo. Torej je 10 sodo. |
:::

::: task Veljavnost modus ponensa
S pomočjo pravilnostne tabele dokažite, da je modus ponens $A,\ A \Rightarrow B \models B$ veljaven sklep.
:::
@@space 6
::: sol
Sklep je veljaven, če je $(A \wedge (A \Rightarrow B)) \Rightarrow B$ **tavtologija**. Zgradimo tabelo po stolpcih, od notranjih izrazov navzven:

| $A$ | $B$ | $A \Rightarrow B$ | $A \wedge (A \Rightarrow B)$ | $(A \wedge (A \Rightarrow B)) \Rightarrow B$ |
|---|---|---|---|---|
| 0 | 0 | 1 | 0 | **1** |
| 0 | 1 | 1 | 0 | **1** |
| 1 | 0 | 0 | 0 | **1** |
| 1 | 1 | 1 | 1 | **1** |

Zadnji stolpec je povsod 1 → tavtologija → sklep je veljaven.
:::

::: warn Veljaven ≠ resničen
Veljavnost sklepa je lastnost **oblike**, ne vsebine. »Vse ribe letijo. Kit je riba. Torej kit leti.« je veljaven sklep (modus ponens) z neresničnima premisama. Logika zagotavlja le: *če* so premise resnične, je resničen tudi zaključek.
:::

::: task Dodatna naloga: je sklep veljaven?
Ugotovite, ali je sklep $A \Rightarrow B,\ B \models A$ veljaven. Če ni, poiščite vrstico pravilnostne tabele, ki to pokaže, in navedite vsakdanji primer.
:::
@@space 5
::: sol
Preverimo, ali je $((A \Rightarrow B) \wedge B) \Rightarrow A$ tavtologija. Vrstica $A = 0$, $B = 1$: $A \Rightarrow B = 1$, $B = 1$, torej je predpostavka $1 \wedge 1 = 1$, zaključek $A = 0$ → implikacija $1 \Rightarrow 0 = 0$. **Ni tavtologija, sklep je neveljaven.**

Vsakdanji primer: »Če dežuje, je cesta mokra. Cesta je mokra. Torej dežuje.« – cesto je lahko zmočil tudi čistilni stroj. Ta napaka se imenuje *potrjevanje posledice*; veljaven je le modus ponens (iz $A$ in $A \Rightarrow B$ sledi $B$), ne obratno.
:::

# Kvantifikatorji

::: idea Od izjav k izjavnim funkcijam
Pravilnost izjave je lahko odvisna od vrednosti parametra $x$: $A(x)$: »$x > 0$« je resnična za pozitivne $x$ in neresnična sicer. Taki »izjavi s parametrom« rečemo **izjavna funkcija**. Pogosto nas ne zanima en konkreten $x$, ampak: ali velja za **vse** $x$ iz domene, ali **obstaja** kak $x$, za katerega velja. To povemo s kvantifikatorji.
:::

::: def Kvantifikatorji
| Kvantifikator | Simbol | Beremo | Pomen | Primer |
|---|---|---|---|---|
| **Univerzalni** | $\forall$ | za vsak | $A(x)$ velja za **vsako** vrednost $x$ iz danega območja | $\forall x \in \mathbb{R}: x^2 \geq 0$ |
| **Eksistenčni** | $\exists$ | obstaja | $A(x)$ velja za **vsaj eno** vrednost $x$ | $\exists x \in \mathbb{R}: x^2 = 1$ |
| **Enolične eksistence** | $\exists!$ | obstaja natanko en | $A(x)$ velja za **natanko eno** vrednost $x$ | $\exists! x \in \mathbb{R}: x^3 = 1$ |
:::

## Združevanje kvantifikatorjev

Kvantifikatorje združujemo: $\forall x\, \exists y: x + y = 0$ pomeni $\forall x: (\exists y: x + y = 0)$.

::: thm Vrstni red kvantifikatorjev
- Dva zaporedna **enaka** kvantifikatorja lahko zamenjamo: $\forall x \forall y: A(x,y) \equiv \forall y \forall x: A(x,y)$, na kratko $\forall x, y: A(x,y)$. Enako za $\exists x \exists y$ = $\exists x, y$.
- Dva zaporedna **različna** kvantifikatorja: vrstni red je **pomemben**.
:::

::: ex Zakaj je vrstni red pomemben
- $\forall x \in \mathbb{R}\ \exists y \in \mathbb{R}: x^2 = y$ – »Za vsak $x$ obstaja $y$, da je $x^2 = y$.« **Resnična**: $y$ je lahko odvisen od $x$ (vzamemo $y = x^2$).
- $\exists y \in \mathbb{R}\ \forall x \in \mathbb{R}: x^2 = y$ – »Obstaja en $y$, da za vsak $x$ velja $x^2 = y$.« **Neresnična**: en sam $y$ bi moral biti hkrati $0^2$ in $1^2$.

**Pravilo za branje:** kar je kvantificirano kasneje, lahko odvisi od tistega, kar je kvantificirano prej. »$\forall x \exists y$« = $y$ si izberemo *potem*, ko poznamo $x$.
:::

@@depend ∀x ∃y : x² = y | ∃y ∀x : x² = y | each=vsak x dobi svoj y (y je odvisen od x) — resnična | one=en sam y za vse x hkrati — neresnična

## Negacija kvantifikatorjev

::: thm Negacija kvantifikatorjev
Zamenjamo vlogi univerzalnega in eksistenčnega kvantifikatorja ter negiramo izjavo:
$$\neg\forall x: A(x) \equiv \exists x: \neg A(x) \qquad\qquad \neg\exists x: A(x) \equiv \forall x: \neg A(x)$$
:::

::: idea Intuicija
»Ni res, da so vsi študenti prišli« = »obstaja študent, ki ni prišel«. »Ni res, da obstaja rešitev« = »vsak kandidat ni rešitev«. Negacija potuje *skozi* kvantifikator in ga obrne – kot De Morgan za neskončno mnogo členov.
:::

::: task Negacija enolične eksistence
Poiščite negacijo kvantifikatorja enolične eksistence $\neg\exists! x: A(x)$. Pomagajte si z identiteto
$$\exists! x: A(x) \equiv \exists x: \big(A(x) \wedge \forall y: (A(y) \Rightarrow x = y)\big).$$
:::
@@space 5
::: sol
Identiteta pravi: »obstaja $x$ z lastnostjo **in** vsak $y$, ki ima lastnost, je enak $x$«. Negiramo po pravilih: kvantifikatorje zamenjamo, notranjost negiramo (De Morgan, negacija implikacije $\neg(P \Rightarrow Q) \equiv P \wedge \neg Q$):
$$\neg\exists! x: A(x) \equiv \forall x: \big(\neg A(x) \vee \exists y: (A(y) \wedge x \neq y)\big)$$

Z besedami: **ali** noben $x$ nima lastnosti, **ali** pa jo imata vsaj dva različna. (»Natanko en« odpove v dveh smereh: nič ali preveč.)
:::

## Identitete s kvantifikatorji

::: thm
$$\forall x: (A(x) \wedge B(x)) \equiv \forall x: A(x) \wedge \forall x: B(x)$$
$$\exists x: (A(x) \vee B(x)) \equiv \exists x: A(x) \vee \exists x: B(x)$$
:::

::: task Ali lahko zamenjamo ∧ z ∨ in obratno?
Premislite, ali lahko v prvi identiteti konjunkcijo zamenjamo z disjunkcijo in v drugi disjunkcijo s konjunkcijo. Če ne, poiščite protiprimer.
:::
@@space 5
::: sol
**Ne.** Protiprimera na $\mathbb{Z}$ z $A(x)$: »$x$ je sodo«, $B(x)$: »$x$ je liho«:

- $\forall x: (A(x) \vee B(x))$ je **resnična** (vsako celo število je sodo ali liho), toda $\forall x: A(x) \vee \forall x: B(x)$ je **neresnična** (niso vsa soda in niso vsa liha).
- $\exists x: A(x) \wedge \exists x: B(x)$ je **resnična**, toda $\exists x: (A(x) \wedge B(x))$ je **neresnična** (nobeno število ni hkrati sodo in liho).

Velja samo šibkejša smer: $\forall x: A \vee \forall x: B \Rightarrow \forall x: (A \vee B)$ in $\exists x: (A \wedge B) \Rightarrow \exists x: A \wedge \exists x: B$.
:::

::: task Dodatna naloga: negacija kvantificiranih izjav v besedah
Zapišite negacijo vsake izjave, najprej simbolno, nato v lepi slovenščini (brez »ni res, da«):

**(a)** »Vsak študent FIŠ zna programirati v Pythonu.«

**(b)** »Obstaja realno število $x$, da je $x^2 = -1$.«

**(c)** $\forall x \in \mathbb{R}\ \exists y \in \mathbb{R}: x < y$
:::
@@space 6
::: sol
Pravilo: $\forall \leftrightarrow \exists$ zamenjamo, notranjo izjavo negiramo.

**(a)** $\neg\forall s: Z(s) \equiv \exists s: \neg Z(s)$ → »**Obstaja** študent FIŠ, ki **ne** zna programirati v Pythonu.« (Ne: »Noben študent ne zna …«.)

**(b)** $\neg\exists x \in \mathbb{R}: x^2 = -1 \equiv \forall x \in \mathbb{R}: x^2 \neq -1$ → »**Za vsako** realno število $x$ velja $x^2 \neq -1$.« (Ta negacija je resnična.)

**(c)** $\neg(\forall x\ \exists y: x < y) \equiv \exists x\ \forall y: x \geq y$ → »Obstaja realno število $x$, ki je večje ali enako **vsem** realnim številom« – torej največje realno število. Izvirna izjava je resnična (vedno obstaja večje število), njena negacija neresnična.
:::

::: video
- Univerzalnostni in eksistencialnostni kvantifikator — `youtu.be/LHv-lpr2a3w` (2:06)
:::

# Množice

::: def Množica
Množica je določena z **elementi**, ki jih vsebuje. Označujemo jo z velikimi tiskanimi črkami. Podamo jo z **naštevanjem** ali s **pravilom**:
$$A = \{1, 2, 3, 4, 5\} \qquad \text{oz.} \qquad A = \{n \in \mathbb{N} : n \leq 5\}$$
:::

::: def Pripadnost, prazna in univerzalna množica
- $x \in A$: element $x$ **pripada** množici $A$; $x \notin A$: ne pripada. Zgled: $A = \{1,2,3\}$, $1 \in A$, $4 \notin A$.
- **Prazna množica** $\emptyset$ ne vsebuje nobenega elementa.
- **Univerzalna množica** $U$ vsebuje vse elemente, ki jih v danem primeru opazujemo.
:::

::: ex Vennov diagram
Množice $A = \{1,2,3,a,b,c\}$, $B = \{1,a,b,4\}$, $C = \{1,4,d\}$ grafično predstavimo z **Vennovim diagramom** – vsaka množica je krog, prekrivanja kažejo skupne elemente.
@@venn3 A=2,3,c | AB=a,b | ABC=1 | BC=4 | C=d
:::

## Operacije z množicami

::: def Komplement
Komplement množice $A$ je množica tistih elementov iz $U$, ki **niso** v $A$. Oznaka: $A^C$ oz. $\bar{A}$.
:::

::: def Presek
Presek množic $A$ in $B$ je množica elementov, ki so **hkrati** v $A$ in v $B$. Oznaka: $A \cap B$. Za več množic: $A_1 \cap A_2 \cap \cdots \cap A_n$. Če je $A \cap B = \emptyset$, sta $A$ in $B$ **disjunktni**.
:::

::: def Unija
Unija množic $A$ in $B$ je množica elementov, ki so v $A$ **ali** v $B$. Oznaka: $A \cup B$. Za več množic: $A_1 \cup A_2 \cup \cdots \cup A_n$.
:::

::: def Razlika
Razlika množic $A$ in $B$ vsebuje elemente, ki so v $A$ **in niso** v $B$. Oznaka: $A \setminus B$ (beremo: $A$ brez $B$).
:::

::: def Podmnožica
$A$ je **podmnožica** $B$, če je vsak element iz $A$ tudi element $B$. Oznaka: $A \subseteq B$.

**Trditev:** če velja $A \subseteq B$ in $B \subseteq A$, potem je $A = B$. (To je standardni način dokazovanja enakosti množic.)
:::

@@venn2 comp:Komplement | inter:Presek | union:Unija | diff:Razlika | subset:Podmnožica | disjoint:Disjunktni | cap=Operacije z množicami – obarvano je, kar operacija vrne

::: task Operacije z množicami
Dana je univerzalna množica $U = \{1,2,3,4,5,6,7,8\}$ ter množice $A = \{1,2,3,4,5\}$, $B = \{2,4,8\}$, $C = \{1,3,5,7\}$. Zapišite množice:
$A \cup B \cup C$, $\quad U \setminus (B \cup C)$, $\quad A \cap C$, $\quad A^C \cup C$, $\quad (A \cup C) \cap A^C$.
:::
@@space 6
::: sol
Delamo od znotraj navzven, vedno najprej izraz v oklepaju.

| Izraz | Postopek | Rezultat |
|---|---|---|
| $A \cup B \cup C$ | zberemo vse | $\{1,2,3,4,5,7,8\}$ |
| $U \setminus (B \cup C)$ | $B \cup C = \{1,2,3,4,5,7,8\}$, ostane | $\{6\}$ |
| $A \cap C$ | skupni elementi | $\{1,3,5\}$ |
| $A^C \cup C$ | $A^C = \{6,7,8\}$ | $\{1,3,5,6,7,8\}$ |
| $(A \cup C) \cap A^C$ | $A \cup C = \{1,2,3,4,5,7\}$, presek s $\{6,7,8\}$ | $\{7\}$ |
:::

## Množice in logika

::: idea Vsaka operacija z množicami je logična operacija
Množice so le »logika, zapakirana v elemente«: presek je $\wedge$, unija je $\vee$, komplement je $\neg$, podmnožica je $\Rightarrow$. Zato vse logične identitete (De Morgan, distributivnost …) veljajo tudi za množice.
:::

::: thm Prevod v logiko
| Množice | Logika (za vsak $x \in U$) |
|---|---|
| $x \in A^C$ | $\Leftrightarrow x \notin A \Leftrightarrow \neg(x \in A)$ |
| $x \in A \cap B$ | $\Leftrightarrow x \in A \wedge x \in B$ |
| $x \in A \cup B$ | $\Leftrightarrow x \in A \vee x \in B$ |
| $x \in A \setminus B$ | $\Leftrightarrow x \in A \wedge x \notin B$ |
| $A \subseteq B$ | $\Leftrightarrow \forall x \in U: (x \in A \Rightarrow x \in B)$ |
| $A = B$ | $\Leftrightarrow A \subseteq B \wedge B \subseteq A$ |
:::

::: task Dokaz z množicami in logiko
Pokažite: če je $A \subseteq B$, potem je $A^C \cup B = U$. Uporabite prevod v logiko in identiteto implikacije.
:::
@@space 6
::: sol
**Načrt:** enakost množic pokažemo z obema vsebovanostma. $A^C \cup B \subseteq U$ velja vedno (vse je v $U$). Pokazati moramo le $U \subseteq A^C \cup B$.

**Dokaz:** izhajamo iz predpostavke in jo z ekvivalencami preoblikujemo v želeno vsebovanost.
$$\begin{aligned}
A \subseteq B &\Leftrightarrow \forall x \in U: (x \in A \Rightarrow x \in B) && \text{(def. podmnožice)}\\
&\Leftrightarrow \forall x \in U: (\neg(x \in A) \vee x \in B) && \text{(identiteta implikacije)}\\
&\Leftrightarrow \forall x \in U: (x \in A^C \vee x \in B) && \text{(def. komplementa)}\\
&\Leftrightarrow \forall x \in U: x \in A^C \cup B && \text{(def. unije)}\\
&\Leftrightarrow U \subseteq A^C \cup B && \text{(def. podmnožice)}
\end{aligned}$$
:::

::: video
- Kaj so množice v matematiki? — `youtu.be/bFmeQvIyLEk` (5:44)
- Osnovni pojmi – Vennov diagram, U, ∅ — `youtu.be/AFHNkBNvtIY` (4:59)
- Podmnožica — `youtu.be/nJmK9EscxjQ` (6:49)
- Enaki množici — `youtu.be/1MfTSFQM4nw` (1:39)
- Komplement množice — `youtu.be/7osBJ01MDu8` (3:00)
- Unija množic — `youtu.be/5HK_bNwQrgk` (2:48)
- Presek množic — `youtu.be/rmyM9nclRaI` (3:06)
- Razlika množic — `youtu.be/itdkV54YxCU` (3:28)
- Množice – naloge 1–8 — `youtu.be/LrcWfA6g8q0`, `GLJ7l4EEp0k`, `r5gWuGzlMBY`, `fmoqXaxxHL0`, `OgvO789zWE4`, `jr9igT7-VUg`, `TKU1_Q141dM`, `crDVMoKFpD4`
:::

# Številske množice

::: idea Zakaj več vrst števil
Vsako novo množico števil uvedemo, ker prejšnja ni **zaprta** za kako operacijo: v $\mathbb{N}$ ne moremo odštevati, v $\mathbb{Z}$ ne deliti, v $\mathbb{Q}$ ne koreniti. Vsaka razširitev vsebuje prejšnjo.
:::

@@nested ℝ; realna števila; zaprta za: + − · ÷, korenjenje, logaritmi; √2, π, e | ℚ; racionalna števila; zaprta za: + − · ÷ (z neničelnimi); ½, −¾, 0,333… | ℤ; cela števila; zaprta za: + − ·; …, −2, −1, 0 | ℕ; naravna števila; zaprta za: + ·; 1, 2, 3, …

## Naravna števila ℕ

::: def Peanovi aksiomi
Naravna števila so števila, s katerimi štejemo. Giuseppe Peano (1858–1932) jih je definiral s petimi aksiomi:

1. $1$ je naravno število.
2. Vsakemu naravnemu številu sledi natanko določeno število – njegov **naslednik**.
3. Različni naravni števili imata različna naslednika.
4. Število $1$ ni naslednik nobenega števila.
5. Vsaka podmnožica naravnih števil, ki vsebuje $1$ in je v njej hkrati s številom $n$ tudi naslednik od $n$, je enaka množici naravnih števil (**načelo popolne indukcije**).

Iz teh aksiomov izpeljemo vse lastnosti naravnih števil. $\mathbb{N}$ je zaprta za **seštevanje in množenje**.
:::

::: warn Ali je 0 naravno število?
V tem predmetu **ne**: $\mathbb{N} = \{1, 2, 3, \dots\}$. V literaturi (zlasti v računalništvu) pogosto $0 \in \mathbb{N}$. Pri nalogah preveri dogovor.
:::

## Popolna (matematična) indukcija

::: def Popolna indukcija
Metoda, s katero dokažemo, da neka lastnost $P$ velja za **vsa** naravna števila od $n_0$ dalje. Dokaz izjave »$P$ velja za vsa $n \geq n_0$« poteka v dveh korakih:

1. **Baza:** pokažemo, da $P$ velja za $n_0$.
2. **Korak:** pokažemo, da iz veljavnosti za **poljuben** $n \geq n_0$ (indukcijska predpostavka) sledi veljavnost za $n + 1$.
:::

@@dominoes base=1. baza | step=2. korak: P(n) ⇒ P(n+1)

::: idea Zakaj to deluje
Baza podre prvo domino; korak zagotavlja, da vsaka domina podre naslednjo. Formalno: množica $\{n : P(n)\}$ vsebuje $n_0$ in je zaprta za naslednika, torej je po 5. Peanovem aksiomu enaka vsem $n \geq n_0$.
:::

::: task Dokaz z indukcijo
Z matematično indukcijo pokažite, da za vsak $n \in \mathbb{N}$ velja
$$1 + 2 + 3 + \cdots + n = \frac{n(n+1)}{2}.$$
:::
@@space 7
::: sol
**Baza** ($n = 1$): leva stran $= 1$, desna stran $= \frac{1 \cdot 2}{2} = 1$. ✓

**Korak:** predpostavimo, da velja za $n$: $1 + \cdots + n = \frac{n(n+1)}{2}$. Pokažimo za $n+1$:
$$1 + \cdots + n + (n+1) = \frac{n(n+1)}{2} + (n+1) = (n+1)\left(\frac{n}{2} + 1\right) = \frac{(n+1)(n+2)}{2}.$$
To je natanko formula za $n + 1$. ✓

Po načelu popolne indukcije formula velja za vsa $n \in \mathbb{N}$. $\blacksquare$
:::

## Cela števila ℤ in deljivost

::: def Cela števila
$\mathbb{Z}$ je množica naravnih števil skupaj s številom $0$ in takimi števili $-n$, da je $n + (-n) = 0$ za vsako naravno število $n$. Zaprta je za **seštevanje, odštevanje in množenje**.
:::

::: def Deljivost
Naj bo $p \in \mathbb{Z} \setminus \{0\}$. Število $q \in \mathbb{N}$ **deli** $p$ (zapišemo $q \mid p$), če obstaja tak $k \in \mathbb{Z}$, $k \neq 0$, da je $p = kq$.

- Če je edini skupni delitelj števil $p$ in $q$ število $1$, sta **tuji** števili.
- $p$ je **praštevilo**, če ima natanko dva delitelja: $1$ in $p$.
:::

::: thm Lastnosti deljivosti
- $\forall x \neq 0: x \mid 0$.
- Če $a \mid b$ in $b \mid c$, potem $a \mid c$ (tranzitivnost).
- Če $a \mid b$ in $a \mid c$, potem $a \mid (b + c)$.
:::

## Racionalna števila ℚ

::: def Racionalna števila
$\mathbb{Q}$ so števila, ki jih lahko zapišemo kot ulomek $\dfrac{p}{q}$, kjer je $p \in \mathbb{Z}$, $q \in \mathbb{N}$ in sta $p, q$ tuji (izjema je $0$). Brez pogoja tujosti ima vsako racionalno število neskončno zapisov: $\frac{1}{2} = \frac{2}{4} = \frac{3}{6} = \cdots$

Zaprta je za seštevanje, odštevanje, množenje in **deljenje z neničelnimi** števili. Racionalna števila imajo **končen ali neskončen periodičen** decimalni zapis.
:::

::: task Dokaz: 1 = 0,999…
Dokažite, da je $1 = 0{,}999\ldots$ (Namig: označite $x = 0{,}999\ldots$ in pomnožite z 10.)
:::
@@space 4
::: sol
Naj bo $x = 0{,}999\ldots$ Potem $10x = 9{,}999\ldots$ Odštejemo:
$$10x - x = 9{,}999\ldots - 0{,}999\ldots = 9 \quad\Rightarrow\quad 9x = 9 \quad\Rightarrow\quad x = 1.$$
Torej $0{,}999\ldots$ ni »malo manj kot 1«, ampak je **isto število**, zapisano drugače.
:::

## Realna števila ℝ

::: task Dokaz: √2 ni racionalno število
Pokažite, da $\sqrt{2}$ ni racionalno število. (Namig: dokaz s protislovjem – predpostavite, da je $\sqrt{2} = \frac{p}{q}$ s tujima $p, q$.)
:::
@@space 6
::: sol
**Dokaz s protislovjem.** Recimo, da je $\sqrt{2} = \frac{p}{q}$ s tujima $p, q$. Kvadriramo: $2q^2 = p^2$, torej je $p^2$ sodo, zato je **$p$ sodo**, $p = 2k$. Vstavimo: $2q^2 = 4k^2 \Rightarrow q^2 = 2k^2$, torej je tudi **$q$ sodo**. Oba sta soda – nista tuja. **Protislovje.** $\blacksquare$
:::

::: def Realna števila
$\mathbb{R}$ so števila s **številske premice**. Zaprta so za seštevanje, odštevanje, množenje in deljenje z neničelnimi števili. V $\mathbb{R}$ lahko tudi potenciramo, korenimo, logaritmiramo.
:::

::: video
- Kaj so naravna števila? — `youtu.be/8Adw0BcGVcE` (3:22)
- Kaj so cela števila? — `youtu.be/9t5nba5DClA` (4:11)
- Periodična decimalna števila — `youtu.be/JQ5KRZ1OhCI` (3:14)
- Periodično decimalno število kot ulomek — `youtu.be/lzc8_U6nAFk` (2:26)
- Kaj so realna števila? — `youtu.be/gszmxr5uB4k` (7:01)
- Realna števila na številski premici — `youtu.be/uZcqrRfWr5Y` (4:51)
:::

# Potenciranje in logaritmi

::: def Potenca in koren
$$a^n = \underbrace{a \cdot a \cdots a}_{n}, \qquad a^{-n} = \frac{1}{a^n}\ (a \neq 0)$$
Naj bo $a \geq 0$ in $n \in \mathbb{N}$. Potenci $a^{1/n}$ rečemo **$n$-ti koren** števila $a$: $a^{1/n} = \sqrt[n]{a}$. To je **pozitivna** rešitev enačbe $x^n = a$ ($a$ – radikand, $n$ – korenski eksponent ali stopnja korena).
$$a^{m/n} = \sqrt[n]{a^m} = \left(\sqrt[n]{a}\right)^m, \quad a > 0$$
:::

::: thm Pravila za potenciranje
| Pravilo | Formula |
|---|---|
| Produkt enakih osnov | $a^n \cdot a^m = a^{n+m}$ |
| Kvocient enakih osnov | $a^n : a^m = a^{n-m}$, zato $a^0 = 1$ za $a \neq 0$ |
| Potenca produkta | $(ab)^n = a^n b^n$ |
| Potenca potence | $(a^n)^m = a^{nm}$ |
| Potenca kvocienta | $\left(\frac{a}{b}\right)^n = \frac{a^n}{b^n}$, $b \neq 0$ |
:::

::: def Logaritem
Logaritem števila $b > 0$ pri osnovi $a > 0$, $a \neq 1$, je tisti **eksponent**, s katerim moramo potencirati osnovo $a$, da dobimo $b$:
$$x = \log_a b \iff a^x = b$$
($b$ – logaritmand.) **Naravni logaritem** $\ln$ ima osnovo $e = 2{,}7182\ldots$, **desetiški logaritem** $\log$ ima osnovo $10$.
:::

::: idea Logaritem je »obrnjeno potenciranje«
Potenciranje: *osnova in eksponent → rezultat*. Logaritem: *osnova in rezultat → eksponent*. »$\log_2 32$« je vprašanje »na katero potenco dvignem 2, da dobim 32?«.
:::

::: task Rešite enačbo $2^x = 32$
:::
@@space 2.5
::: sol
Desno stran zapišemo kot potenco iste osnove: $32 = 2^5$, torej $2^x = 2^5 \Rightarrow x = 5$. Z logaritmom: $x = \log_2 32 = 5$.
:::

::: thm Pravila za logaritmiranje
| Pravilo | Formula |
|---|---|
| Osnovni | $\log_a a^n = n$, $\log_a 1 = 0$ |
| Produkt | $\log_a x + \log_a y = \log_a (xy)$ |
| Kvocient | $\log_a x - \log_a y = \log_a \frac{x}{y}$ |
| Potenca | $\log_a x^r = r \log_a x$ |
| Menjava osnove | $\log_a x = \dfrac{\log_b x}{\log_b a}$ |
:::

::: task Izpeljava pravil za produkt in kvocient
Izpeljite pravili $\log_a x + \log_a y = \log_a(xy)$ in $\log_a x - \log_a y = \log_a \frac{x}{y}$ iz definicije logaritma in pravil za potence. (Domača naloga s prosojnic.)
:::
@@space 5
::: sol
Označimo $u = \log_a x$ in $v = \log_a y$. Po definiciji logaritma je $a^u = x$ in $a^v = y$.

**Produkt:** $xy = a^u \cdot a^v = a^{u+v}$ (pravilo za produkt enakih osnov). Po definiciji logaritma torej $\log_a(xy) = u + v = \log_a x + \log_a y$. $\blacksquare$

**Kvocient:** $\dfrac{x}{y} = \dfrac{a^u}{a^v} = a^{u-v}$, zato $\log_a \dfrac{x}{y} = u - v = \log_a x - \log_a y$. $\blacksquare$

**Ideja:** logaritem prevede množenje v seštevanje, ker potenciranje prevede seštevanje eksponentov v množenje.
:::

::: video
- Kaj je potenca? — `youtu.be/XyL7Ta11AGk` (3:30)
- Pravila za računanje s potencami — `youtu.be/thll_1ZZHb4` (2:01)
- Stopnja korena — `youtu.be/wM-gzSHdbMk` (3:51)
- Pravila za računanje z n-timi koreni — `youtu.be/hM1tcc4PWeY` (3:44)
- Potence z racionalnimi eksponenti — `youtu.be/-uuO2zpzcak` (4:21)
- Kaj je logaritem? — `youtu.be/Y-Dox8tM1Bo` (5:47)
- Desetiški in naravni logaritem — `youtu.be/-B4_QCZD_ts` (1:47)
- Pretvorba eksponentnega v logaritemski zapis — `youtu.be/q39S_oK-npc` (1:19)
- Pravila za logaritmiranje 1 — `youtu.be/fYEbbqZ6oTU` (8:06)
- Pravila za logaritmiranje 2 — `youtu.be/MCYC2TA3tbI` (8:51)
- Prehod na novo osnovo — `youtu.be/H9fcgStCaEA` (5:56)
:::

# Intervali, absolutna vrednost, omejenost

## Intervali

::: def Interval
Interval je podmnožica množice realnih števil.

| Ime | Pogoj | Oznaka |
|---|---|---|
| **Zaprti** interval | $a \leq x \leq b$ | $[a, b]$ |
| **Odprti** interval | $a < x < b$ | $(a, b)$ |
| **Polodprta** intervala | $a \leq x < b$ oz. $a < x \leq b$ | $[a, b)$ oz. $(a, b]$ |
| **$\varepsilon$-okolica** števila $a$ | $a - \varepsilon < x < a + \varepsilon$ | $(a - \varepsilon, a + \varepsilon)$ |
:::

@@intervals [a,b] | (a,b) | [a,b) | (a,b] | note=poln krog = krajišče je v množici, prazen krog = ni v množici

## Absolutna vrednost

::: def Absolutna vrednost
Absolutna vrednost realnega števila $x$ je **razdalja** med $x$ in $0$. Oznaka: $|x|$. Velja $|x| = |-x|$.
$$|x| = \begin{cases} x, & x \geq 0 \\ -x, & x < 0 \end{cases}$$
:::

::: idea Kako rešujemo enačbe in neenačbe z |·|
Ločeno obravnavamo vrednosti $x$, pri katerih je izraz pod absolutno vrednostjo **nenegativen** (absolutno vrednost odstranimo), in tiste, pri katerih je **negativen** (odstranimo in spremenimo predznak). Rešitev vsakega primera **presekamo** z njegovim pogojem, na koncu rešitve **združimo**.
:::

::: task Neenačba z absolutno vrednostjo
Poiščite vsa realna števila $x$, za katera je $x + 2 > |2x - 1|$.
:::
@@space 7
::: sol
Izraz pod absolutno vrednostjo spremeni predznak pri $2x - 1 = 0 \Rightarrow x = \frac{1}{2}$. To je meja med primeroma.

**Primer 1:** $x \geq \frac{1}{2}$ (izraz nenegativen): $x + 2 > 2x - 1 \Rightarrow x < 3$. Skupaj s pogojem: $x \in \left[\frac{1}{2}, 3\right)$.

**Primer 2:** $x < \frac{1}{2}$ (izraz negativen): $x + 2 > -(2x - 1) = 1 - 2x \Rightarrow 3x > -1 \Rightarrow x > -\frac{1}{3}$. Skupaj s pogojem: $x \in \left(-\frac{1}{3}, \frac{1}{2}\right)$.

**Rešitev:** unija obeh primerov: $x \in \left(-\frac{1}{3}, 3\right)$.
:::

## Omejenost množic

::: def Spodnja meja, infimum, minimum
Naj bo $A \subset \mathbb{R}$.
- Število $s \in \mathbb{R}$ je **spodnja meja** množice $A$, če je $s \leq x$ za vsak $x \in A$.
- Število $S$ je **natančna spodnja meja** (**infimum**, $\inf A$), če je **največja** med vsemi spodnjimi mejami.
- Če $A$ nima nobene spodnje meje, je $\inf A = -\infty$.
- Če je infimum **element** množice $A$, mu rečemo **minimum** ($\min A$).
:::

::: def Zgornja meja, supremum, maksimum
- Število $z \in \mathbb{R}$ je **zgornja meja** množice $A$, če je $z \geq x$ za vsak $x \in A$.
- Število $Z$ je **natančna zgornja meja** (**supremum**, $\sup A$), če je **najmanjša** med vsemi zgornjimi mejami.
- Če $A$ nima nobene zgornje meje, je $\sup A = \infty$.
- Če je supremum **element** množice $A$, mu rečemo **maksimum** ($\max A$).
:::

::: idea Razlika med sup in max
Supremum **vedno obstaja** (za navzgor omejeno množico), maksimum pa samo, če množica svojo mejo tudi **doseže**. $(0, 1)$ ima $\sup = 1$, maksimuma pa nima – 1 ni v množici. To razlikovanje je bistvo celotne analize (limite!).
:::

@@numline -4..5 | (-2,3]:A | mark=-2:inf A = −2 (min ne obstaja) | mark=3:sup A = max A = 3 | shade=-4..-2:spodnje meje | shade=3..5:zgornje meje

::: task Infimum, supremum, minimum, maksimum
Dani sta množici $A = \{x \in \mathbb{R} : -2 < x \leq 3\}$ in $B = \{x \in \mathbb{R} : 2 \leq x < 3\}$. Določite $\inf$, $\sup$, $\min$ in $\max$ množic $A$, $B$, $A \cap B$ in $A \cup B$.
:::
@@space 7
::: sol
Najprej množice zapišemo kot intervale in jih narišemo na številsko premico: $A = (-2, 3]$, $B = [2, 3)$. Ker je $B \subseteq A$: $A \cap B = B = [2, 3)$ in $A \cup B = A = (-2, 3]$.

| Množica | $\inf$ | $\min$ | $\sup$ | $\max$ |
|---|---|---|---|---|
| $A = (-2, 3]$ | $-2$ | ne obstaja | $3$ | $3$ |
| $B = [2, 3)$ | $2$ | $2$ | $3$ | ne obstaja |
| $A \cap B = [2, 3)$ | $2$ | $2$ | $3$ | ne obstaja |
| $A \cup B = (-2, 3]$ | $-2$ | ne obstaja | $3$ | $3$ |

**Pravilo:** odprti konec → meja obstaja (inf/sup), ekstrem (min/max) pa ne; zaprti konec → oboje.
:::

::: video
- Kaj je interval? — `youtu.be/Fpi3VXj9Xmw` (5:00)
- Določanje intervala 1 — `youtu.be/79H6Q2lb_mg` (2:04)
- Interval – presek — `youtu.be/G6v2txQcXG8` (1:34)
- Interval – unija — `youtu.be/5xDkJqUVFPs` (1:49)
- Kaj je absolutna vrednost? — `youtu.be/cYt_V31wrZU` (4:18)
- Neenačba z absolutno vrednostjo 1–5 — `youtu.be/xzkOGNmRJeU`, `VlSC2whgL7g`, `xT04YEKT0iQ`, `lKstH7Z_T8E`, `LiP55KTa4j8`
:::

# Povzetek poglavja

::: summary
| Pojem | Bistvo |
|---|---|
| Aksiom / izrek | Nedokazana osnova / iz nje izpeljana trditev |
| Izjava | Stavek z nedvoumno vrednostjo 0 ali 1 |
| $\neg, \wedge, \vee, \Rightarrow, \Leftrightarrow$ | Pet operacij; vsako določa pravilnostna tabela; prednost v tem vrstnem redu |
| $A \Rightarrow B$ | Neresnična **samo** pri $A = 1$, $B = 0$ |
| $A \equiv B$ | Ekvivalentni v vseh situacijah; De Morgan, implikacija $\equiv \neg A \vee B$ |
| Tavtologija / protislovje | Vedno 1 / vedno 0 |
| Sklep $A_1, \dots, A_n \models B$ | Veljaven, če je $(A_1 \wedge \cdots \wedge A_n) \Rightarrow B$ tavtologija |
| $\forall, \exists, \exists!$ | Vrstni red različnih kvantifikatorjev je pomemben; negacija jih zamenja |
| Množice | $\cap = \wedge$, $\cup = \vee$, $^C = \neg$, $\subseteq\ = \Rightarrow$; enakost = obojestranska vsebovanost |
| $\mathbb{N} \subset \mathbb{Z} \subset \mathbb{Q} \subset \mathbb{R}$ | Vsaka širitev zapre novo operacijo |
| Indukcija | Baza + korak ($n \to n+1$) |
| Logaritem | $\log_a b = x \iff a^x = b$ |
| $\lvert x \rvert$ | Razdalja do 0; reši po primerih glede na predznak |
| inf / sup | Vedno obstajata (če je omejena); min / max le, če je meja v množici |
:::
