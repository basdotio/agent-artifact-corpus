---
name: churn-prevention
description: "Wanneer de gebruiker churn wil verlagen, annuleringsflows wil bouwen, save offers wil instellen, mislukte betalingen wil herstellen of retentiestrategieën wil implementeren. Ook bij 'churn,' 'churn prevention,' 'klantverloop,' 'cancel flow,' 'annuleringsflow,' 'offboarding,' 'save offer,' 'dunning,' 'failed payment recovery,' 'betalingsherstel,' 'win-back,' 'retentie,' 'retention,' 'exit survey,' 'pauze abonnement,' 'pause subscription,' 'involuntary churn,' 'onvrijwillig verloop.' Dekt vrijwillige churn (cancel flows, save offers, exit surveys) en onvrijwillige churn (dunning, betalingsherstel). Voor win-back e-mailsequenties na annulering, zie email-marketing. Voor in-app upgrade paywalls, zie conversion-optimization."
metadata:
  version: 1.0.0
  language: nl-BE
---

# Churn prevention

Je bent een expert in SaaS-retentie en churn prevention. Je doel is om zowel vrijwillige churn (klanten die kiezen om te annuleren) als onvrijwillige churn (mislukte betalingen) te verminderen door goed ontworpen cancel flows, dynamische save offers, proactieve retentie en dunning-strategieën.

## Context laden

Als `.agents/marketing-context.md` bestaat, lees dit eerst.
Gebruik die context voor bestaande productinformatie, doelgroep, pricing en retentiedata.

## Voordat je begint

Verzamel deze context (vraag als het niet gegeven is):

### 1. Huidige churnsituatie
- Wat is het maandelijkse churnpercentage? (Vrijwillig vs. onvrijwillig indien bekend)
- Hoeveel actieve abonnees?
- Wat is de gemiddelde MRR per klant?
- Is er vandaag een cancel flow, of wordt annulering direct verwerkt?

### 2. Billing en platform
- Welke billing provider? (Stripe, Chargebee, Paddle, Recurly, Braintree)
- Maandelijkse, jaarlijkse of beide factureringsintervallen?
- Ondersteuning voor pauzeren of downgraden?
- Bestaande retentietooling? (Churnkey, ProsperStack, Raaft)

### 3. Product en gebruiksdata
- Wordt featuregebruik per gebruiker bijgehouden?
- Kun je engagement-dalingen identificeren?
- Is er annuleringsredendata van eerdere churns?
- Wat is de activatiemetric? (Wat doen behouden gebruikers dat gechurnde gebruikers niet doen?)

### 4. Beperkingen
- B2B of B2C? (Beïnvloedt het flowontwerp)
- Self-serve annulering vereist? (Sommige regelgeving vereist eenvoudig annuleren)
- Merktoon voor offboarding? (Empathisch, direct, speels)

---

## Hoe deze skill werkt

Churn heeft twee types die verschillende strategieën vereisen:

| Type | Oorzaak | Oplossing |
| --- | --- | --- |
| **Vrijwillig** | Klant kiest om te annuleren | Cancel flows, save offers, exit surveys |
| **Onvrijwillig** | Betaling mislukt | Dunning e-mails, smart retries, card updaters |

Vrijwillige churn is doorgaans 50-70% van de totale churn. Onvrijwillige churn is 30-50% maar is vaak makkelijker op te lossen.

Deze skill ondersteunt drie modi:

1. **Cancel flow bouwen**: Ontwerp vanaf nul met survey, save offers en bevestiging
2. **Bestaande flow optimaliseren**: Analyseer annuleringsdata en verbeter save rates
3. **Dunning opzetten**: Herstel van mislukte betalingen met retries en e-mailsequenties

---

## Cancel flow ontwerp

### De cancel flow structuur

Elke cancel flow volgt deze sequentie:

```
Trigger > Survey > Dynamisch aanbod > Bevestiging > Post-annulering
```

**Stap 1: Trigger**
Klant klikt op "Abonnement annuleren" in accountinstellingen.

**Stap 2: Exit survey**
Vraag waarom ze annuleren. Dit bepaalt welk save offer getoond wordt.

**Stap 3: Dynamisch save offer**
Presenteer een gericht aanbod op basis van hun reden (korting, pauze, downgrade, etc.)

**Stap 4: Bevestiging**
Als ze nog steeds willen annuleren, bevestig duidelijk met einde-factureringsperiode messaging.

**Stap 5: Post-annulering**
Stel verwachtingen, bied een eenvoudig reactiveringspad, trigger win-back sequentie.

### Exit survey ontwerp

De exit survey is het fundament. Goede redencategorieën:

| Reden | Wat het je vertelt |
| --- | --- |
| Te duur | Prijsgevoeligheid, reageert mogelijk op korting of downgrade |
| Gebruik het niet genoeg | Lage engagement, reageert mogelijk op pauze of onboarding-hulp |
| Mist een feature | Productgat, toon roadmap of workaround |
| Switcht naar concurrent | Concurrentiedruk, begrijp wat zij bieden |
| Technische problemen / bugs | Productkwaliteit, escaleer naar support |
| Tijdelijk / seizoensgebonden behoefte | Gebruikspatroon, bied pauze aan |
| Bedrijf gestopt / veranderd | Onvermijdelijk, leer ervan en laat gracieus los |
| Anders | Vangnet, inclusief vrij tekstveld |

**Survey best practices:**
- 1 vraag, single-select met optioneel vrij tekstveld
- 5-8 redenopties maximaal (vermijd keuzestress)
- Zet meest voorkomende redenen bovenaan (evalueer kwartaallijks)
- Maak er geen schuldgevoel van
- "Help ons verbeteren" framing werkt beter dan "Waarom vertrek je?"

### Dynamische save offers

Het kerninzicht: **stem het aanbod af op de reden.** Een korting redt niemand die het product niet gebruikt. Een feature roadmap redt niemand die het niet kan betalen.

**Aanbod-naar-reden mapping:**

| Annuleringsreden | Primair aanbod | Fallback aanbod |
| --- | --- | --- |
| Te duur | Korting (20-30% voor 2-3 maanden) | Downgrade naar lager plan |
| Gebruikt het niet genoeg | Pauze (1-3 maanden) | Gratis onboarding-sessie |
| Mist feature | Roadmap preview + tijdlijn | Workaround-gids |
| Switcht naar concurrent | Concurrentievergelijking + korting | Feedbacksessie |
| Technische problemen | Escaleer naar support onmiddellijk | Tegoed + prioriteitsfix |
| Tijdelijk / seizoensgebonden | Pauzeer abonnement | Tijdelijk downgraden |
| Bedrijf gestopt | Sla aanbod over (respecteer de situatie) | - |

### Save offer types

**Korting**
- 20-30% korting voor 2-3 maanden is de sweet spot
- Vermijd 50%+ kortingen (traint klanten om te annuleren voor deals)
- Tijdslimiet op het aanbod ("Dit aanbod vervalt wanneer je deze pagina verlaat")
- Toon het bedrag dat bespaard wordt, niet alleen het percentage

**Abonnement pauzeren**
- 1-3 maanden pauze maximaal (langere pauzes reactiveren zelden)
- 60-80% van pauseerders keert uiteindelijk terug naar actief
- Automatische heractivering met voorafgaande notificatie-e-mail
- Houd hun data en instellingen intact

**Plan downgrade**
- Bied een lager tier aan in plaats van volledige annulering
- Toon wat ze behouden vs. wat ze verliezen
- Positioneer als "pas je plan aan" niet "downgrade"
- Eenvoudig pad terug omhoog wanneer ze klaar zijn

**Feature unlock / verlenging**
- Ontgrendel een premium feature die ze niet hebben geprobeerd
- Verleng proefperiode van een hoger tier
- Werkt het beste voor "krijg er niet genoeg waarde uit" redenen

**Persoonlijk contact**
- Voor high-value accounts (top 10-20% op MRR)
- Routeer naar customer success voor een gesprek
- Persoonlijke e-mail van oprichter voor kleinere bedrijven

### Cancel flow UI-patronen

```
+-----------------------------------------+
|  Het spijt ons dat je vertrekt           |
|                                         |
|  Wat is de voornaamste reden dat je      |
|  annuleert?                             |
|                                         |
|  o Te duur                              |
|  o Gebruik het niet genoeg              |
|  o Mist een feature die ik nodig heb    |
|  o Switcht naar een andere tool         |
|  o Technische problemen                 |
|  o Tijdelijk / heb het nu niet nodig    |
|  o Anders: [____________]              |
|                                         |
|  [Doorgaan]                             |
|  [Laat maar, behoud mijn abonnement]    |
+-----------------------------------------+
         | (selecteert "Te duur")
+-----------------------------------------+
|  Wat als we kunnen helpen?              |
|                                         |
|  We houden je graag aan boord.          |
|  Een speciaal aanbod:                   |
|                                         |
|  +-----------------------------------+ |
|  |  25% korting voor de komende       | |
|  |  3 maanden                         | |
|  |  Bespaar EUR XX/maand              | |
|  |                                    | |
|  |  [Accepteer aanbod]               | |
|  +-----------------------------------+ |
|                                         |
|  Of switch naar [Starter Plan] voor     |
|  EUR X/maand >                          |
|                                         |
|  [Nee bedankt, ga door met annuleren]   |
+-----------------------------------------+
```

**UI-principes:**
- Houd de "ga door met annuleren" optie zichtbaar (geen dark patterns)
- Eén primair aanbod + één fallback, niet een muur van opties
- Toon specifieke eurobedragen, niet abstracte percentages
- Gebruik de naam en accountdata van de klant waar mogelijk
- Mobielvriendelijk (veel annuleringen gebeuren op mobiel)

Zie [references/cancel-flow-patterns.md](references/cancel-flow-patterns.md) voor gedetailleerde cancel flow patronen per industrie en billing provider.

---

## Churnvoorspelling en proactieve retentie

De beste save gebeurt voordat de klant ooit op "Annuleren" klikt.

### Risicosignalen

Volg deze voorlopende indicatoren van churn:

| Signaal | Risiconiveau | Tijdsbestek |
| --- | --- | --- |
| Inlogfrequentie daalt 50%+ | Hoog | 2-4 weken voor annulering |
| Gebruik van kernfeature stopt | Hoog | 1-3 weken voor annulering |
| Supporttickets pieken en stoppen dan | Hoog | 1-2 weken voor annulering |
| E-mail open rates dalen | Medium | 2-6 weken voor annulering |
| Bezoeken aan billing-pagina nemen toe | Hoog | Dagen voor annulering |
| Teamzetels worden verwijderd | Hoog | 1-2 weken voor annulering |
| Data-export gestart | Kritiek | Dagen voor annulering |
| NPS-score daalt onder 6 | Medium | 1-3 maanden voor annulering |

### Health score model

Bouw een eenvoudige health score (0-100) uit gewogen signalen:

```
Health Score = (
  Inlogfrequentie score   x 0.30 +
  Featuregebruik score    x 0.25 +
  Support sentiment       x 0.15 +
  Billing gezondheid      x 0.15 +
  Engagement score        x 0.15
)
```

| Score | Status | Actie |
| --- | --- | --- |
| 80-100 | Gezond | Upsell-mogelijkheden |
| 60-79 | Aandacht nodig | Proactieve check-in |
| 40-59 | At risk | Interventiecampagne |
| 0-39 | Kritiek | Persoonlijk contact |

### Proactieve interventies

**Voordat ze aan annuleren denken:**

| Trigger | Interventie |
| --- | --- |
| Gebruiksdaling >50% gedurende 2 weken | "We merkten dat je [feature] niet hebt gebruikt. Hulp nodig?" e-mail |
| Nadert planlimiet | Upgrade-nudge (geen muur, dat doet conversion-optimization) |
| Geen login gedurende 14 dagen | Re-engagement e-mail met recente productupdates |
| NPS detractor (0-6) | Persoonlijke opvolging binnen 24 uur |
| Supportticket onopgelost >48u | Escalatie + proactieve statusupdate |
| Jaarlijkse verlenging over 30 dagen | Waarde-recap e-mail + verlengingsbevestiging |

---

## Onvrijwillige churn: betalingsherstel

Mislukte betalingen veroorzaken 30-50% van alle churn maar zijn het best herstelbaar.

### De dunning stack

```
Pre-dunning > Smart retry > Dunning e-mails > Grace period > Hard cancel
```

### Pre-dunning (voorkom mislukkingen)

- **Kaartvervaldagwaarschuwingen**: e-mail 30, 15 en 7 dagen voor kaart verloopt
- **Backup betaalmethode**: vraag om een tweede betaalmethode bij registratie
- **Card updater services**: Visa/Mastercard auto-update programma's (vermindert hard declines 30-50%)
- **Pre-facturering notificatie**: e-mail 3-5 dagen voor charge bij jaarplannen

### Smart retry logica

Niet alle mislukkingen zijn gelijk. Retry-strategie per decline type:

| Decline type | Voorbeelden | Retry-strategie |
| --- | --- | --- |
| Soft decline (tijdelijk) | Ontoereikend saldo, processor timeout | Retry 3-5 keer over 7-10 dagen |
| Hard decline (permanent) | Kaart gestolen, account gesloten | Niet retrien. Vraag om nieuwe kaart |
| Authenticatie vereist | 3D Secure, SCA | Stuur klant naar betaling bijwerken |

**Retry timing best practices:**
- Retry 1: 24 uur na mislukking
- Retry 2: 3 dagen na mislukking
- Retry 3: 5 dagen na mislukking
- Retry 4: 7 dagen na mislukking (met dunning e-mail escalatie)
- Na 4 retries: hard cancel met heractiveringspad

**Smart retry tip:** Retry op de dag van de maand dat de betaling oorspronkelijk lukte (als dag 1 eerder werkte, retry op dag 1). Stripe Smart Retries handelt dit automatisch af.

### Dunning e-mailsequentie

| E-mail | Timing | Toon | Inhoud |
| --- | --- | --- | --- |
| 1 | Dag 0 (mislukking) | Vriendelijke alert | "Je betaling is niet gelukt. Werk je kaart bij." |
| 2 | Dag 3 | Behulpzame herinnering | "Even een herinnering: werk je betaling bij om toegang te behouden." |
| 3 | Dag 7 | Urgentie | "Je account wordt over 3 dagen gepauzeerd. Werk nu bij." |
| 4 | Dag 10 | Laatste waarschuwing | "Laatste kans om je account actief te houden." |

**Dunning e-mail best practices:**
- Directe link naar betalingspagina (zonder login indien mogelijk)
- Toon wat ze verliezen (hun data, de toegang van hun team)
- Geef niet de schuld ("je betaling is mislukt" niet "je hebt niet betaald")
- Voeg supportcontact toe voor hulp
- Platte tekst presteert beter dan opgemaakte e-mails voor dunning

### Herstelbenchmarks

| Metric | Slecht | Gemiddeld | Goed |
| --- | --- | --- | --- |
| Soft decline herstel | <40% | 50-60% | 70%+ |
| Hard decline herstel | <10% | 20-30% | 40%+ |
| Totaal betalingsherstel | <30% | 40-50% | 60%+ |
| Pre-dunning preventie | Geen | 10-15% | 20-30% |

Zie [references/dunning-playbook.md](references/dunning-playbook.md) voor het volledige dunning playbook met provider-specifieke setup.

---

## Metrics en meting

### Kernchurnmetrics

| Metric | Formule | Doel |
| --- | --- | --- |
| Maandelijks churnpercentage | Gechurnde klanten / Start-van-maand klanten | <5% B2C, <2% B2B |
| Revenue churn (netto) | (Verloren MRR - Expansie MRR) / Start MRR | Negatief (netto expansie) |
| Cancel flow save rate | Bewaard / Totaal annuleringssessies | 25-35% |
| Aanbod acceptatiepercentage | Geaccepteerde aanbiedingen / Getoonde aanbiedingen | 15-25% |
| Pauze heractiveringspercentage | Gereactiveerd / Totaal gepauzeerd | 60-80% |
| Dunning herstelpercentage | Hersteld / Totaal mislukte betalingen | 50-60% |
| Tijd tot annulering | Dagen van eerste churnsignaal tot annulering | Volg trend |

### Cohortanalyse

Segmenteer churn op:
- **Acquisitiekanaal**: welke kanalen brengen loyalere klanten?
- **Plantype**: welke plannen churnen het meest?
- **Looptijd**: wanneer vinden de meeste annuleringen plaats? (30, 60, 90 dagen?)
- **Annuleringsreden**: welke redenen groeien?
- **Save offer type**: welke aanbiedingen werken het beste voor welke segmenten?

### Cancel flow A/B tests

Test één variabele tegelijk:

| Test | Hypothese | Metric |
| --- | --- | --- |
| Kortingspercentage (20% vs 30%) | Hogere korting bewaart meer | Save rate, LTV impact |
| Pauzeduur (1 vs 3 maanden) | Langere pauze verhoogt terugkeerpercentage | Heractiveringspercentage |
| Survey plaatsing (voor vs na aanbod) | Survey-first personaliseert aanbiedingen | Save rate |
| Aanbod presentatie (modal vs full page) | Full page krijgt meer aandacht | Save rate |
| Copy toon (empathisch vs direct) | Empathisch vermindert frictie | Save rate |

---

## Ehrenberg-Bass compliance

Churn prevention wordt vaak gezien als een loyaliteitsinstrument. Vanuit Ehrenberg-Bass perspectief is de werkelijkheid genuanceerder:

- **Double jeopardy law**: kleinere merken hebben zowel minder klanten als lagere loyaliteit. Churnreductie helpt, maar groei komt primair uit het werven van nieuwe klanten (bereik), niet uit het vasthouden van bestaande.
- **Retentie is noodzakelijk maar niet voldoende**: elke euro bespaard op churn is waardevol, maar investeer niet disproportioneel in retentie ten koste van acquisitie.
- **Mentale beschikbaarheid behouden**: zorg dat ook bestaande klanten regelmatig herinnerd worden aan je waarde via alle Category Entry Points. Niet alleen wanneer ze dreigen te churnen.
- **Light buyers zijn belangrijk**: de meeste churn komt van light buyers (Ehrenberg-Bass' kernbevinding). Je cancel flow moet ook voor hen werken, niet alleen voor power users.
- **Bereik in de cancel flow**: je save offer bereikt een prospect op het moment van maximale aandacht. Gebruik dat moment om mentale beschikbaarheid te herstellen, niet alleen om een korting te geven.

---

## Veelgemaakte fouten

- **Geen cancel flow**: Directe annulering laat geld liggen. Zelfs een simpele survey + één aanbod bewaart 10-15%
- **Annulering moeilijk vindbaar maken**: Verborgen annuleerknoppen zorgen voor frustratie en slechte reviews. Veel jurisdicties vereisen eenvoudige annulering (FTC Click-to-Cancel rule, EU-consumentenrecht)
- **Zelfde aanbod voor elke reden**: Een pauschalkorting adresseert niet "mist feature" of "gebruik het niet"
- **Te diepe kortingen**: 50%+ kortingen trainen klanten om te annuleren-en-terugkeren voor deals
- **Onvrijwillige churn negeren**: Vaak 30-50% van totale churn en het makkelijkst op te lossen
- **Geen dunning e-mails**: Mislukte betalingen stilletjes laten annuleren
- **Schuldgevoel-copy**: "Weet je zeker dat je ons wilt verlaten?" beschadigt merkvertrouwen
- **Save offer LTV niet bijhouden**: Een "bewaarde" klant die 30 dagen later churnt was niet echt bewaard
- **Te lang pauzeren**: Pauzes langer dan 3 maanden reactiveren zelden. Stel limieten in
- **Geen post-annulering pad**: Maak heractivering altijd eenvoudig en trigger win-back e-mails

---

## Tool-integraties

### Retentieplatformen

| Tool | Beste voor | Kernfeature |
| --- | --- | --- |
| **Churnkey** | Volledige cancel flow + dunning | AI-powered adaptive offers, 34% gemiddelde save rate |
| **ProsperStack** | Cancel flows met analytics | Geavanceerde rules engine, Stripe/Chargebee integratie |
| **Raaft** | Eenvoudige cancel flow builder | Simpele setup, goed voor early-stage |
| **Chargebee Retention** | Chargebee-klanten | Native integratie, was Brightback |

### Billing providers (dunning)

| Provider | Smart Retries | Dunning e-mails | Card Updater |
| --- | :---: | :---: | :---: |
| **Stripe** | Ingebouwd (Smart Retries) | Ingebouwd | Automatisch |
| **Chargebee** | Ingebouwd | Ingebouwd | Via gateway |
| **Paddle** | Ingebouwd | Ingebouwd | Managed |
| **Recurly** | Ingebouwd | Ingebouwd | Ingebouwd |
| **Braintree** | Handmatige config | Handmatig | Via gateway |

---

## Complianceopmerkingen

### FTC Click-to-Cancel rule (VS)
- Annulering moet even makkelijk zijn als aanmelden
- Mag geen telefoongesprek vereisen als aanmelding online was
- Mag geen buitensporige stappen toevoegen om annulering te ontmoedigen
- Save offers zijn toegestaan maar "ga door met annuleren" moet duidelijk zijn

### GDPR / dataretentie (EU, inclusief België)
- Informeer gebruikers over dataretentieperiode na annulering
- Bied data-export aan voor accountverwijdering
- Respecteer verwijderingsverzoeken binnen 30 dagen
- Gebruik post-annulering data niet voor marketing zonder toestemming

### Algemene best practices
- Toon altijd een duidelijk pad naar volledige annulering
- Verberg nooit de annuleerknop (dark pattern)
- Verwerk annulering ook als de save flow fouten heeft
- Bevestig annulering met e-mailontvangstbewijs

---

## Gerelateerde skills

- **email-marketing**: voor win-back e-mailsequenties na annulering
- **conversion-optimization**: voor in-app upgrade momenten en trial expiration
- **product-marketing**: voor planstructuur en jaarlijkse kortingsstrategie
- **customer-experience**: voor activatie om vroege churn te voorkomen, NPS-opvolging
- **marketing-analytics**: voor het opzetten van churnsignaal-events en cohortanalyse
- **digital-marketing**: voor website-flows en UX van de cancel experience

---

## Scoring rubric

| Dimensie | 1 (onvoldoende) | 3 (basis) | 5 (goed) | 7 (sterk) | 8 (uitstekend) | 9 (expert) |
|----------|-----------------|-----------|----------|-----------|-----------------|------------|
| **Cancel flow** | Geen flow, directe annulering | Survey aanwezig maar geen save offer | 5-stappen flow met dynamische offers per reden | Offers geoptimaliseerd met A/B tests, UI respectvol en compliant | Cancel flow met real-time data (hun team, hun projecten, hun besparing) | Adaptieve flow die leert van historische save data en offers personaliseert per segment |
| **Save offer design** | Zelfde korting voor elke reden | Twee of drie offer types beschikbaar | Offer-naar-reden mapping met primair + fallback | Offers met concrete eurobedragen, timing en limieten | LTV-gewogen offers: high-value accounts krijgen premium interventie | Dynamisch offer systeem met machine learning op optimale korting en timing |
| **Dunning** | Geen dunning, stilletjes annuleren | Stripe default retries zonder eigen e-mails | Pre-dunning + smart retries + 4-email sequence | Retry-strategie per decline type, e-mails met directe betaallink (geen login) | Volledige dunning stack met card updater, backup betaalmethode en escalatie | Predictive dunning die at-risk betalingen identificeert voor ze mislukken |
| **Proactieve retentie** | Alleen reactief (cancel flow) | Health score concept benoemd | Health score met 5 signalen en drempels | Geautomatiseerde interventies per risico-niveau | Health score gevalideerd tegen historische churn met predictive waarde | Proactief retentie-systeem dat 15-25% van churns voorkomt voor ze bij de cancel-knop komen |
| **Measurement** | Alleen totaal churnpercentage | Vrijwillig vs. onvrijwillig gesplitst | Save rate + offer acceptatie + dunning herstel gemeten | Cohort-analyse per reden, plan, looptijd en save offer type | LTV-impact van saves: 30-60-90 dag retentie na save gemeten | Netto revenue impact: bewaarde MRR minus kortingskosten, vergeleken met acquisitie-alternatief |
| **Compliance en ethiek** | Dark patterns (verborgen annuleerknop) | Annuleerknop vindbaar maar flow is manipulatief | FTC en GDPR compliant, geen schuldgevoel-copy | "Ga door met annuleren" altijd zichtbaar, toon respectvol | Cancel flow als positief merkmoment: klanten vertrekken met respect | Compliance als merkwaarde: transparante annulering bouwt vertrouwen en verbetert win-back |

**Worked examples:** Zie [references/examples.md](references/examples.md) voor een volledige cancel flow, 4-email dunning sequence en health score model voor een B2B SaaS.

## Zelfcheck voor oplevering

Voordat je de output als definitief beschouwt:

1. [ ] Cancel flow bevat alle 5 stappen: trigger, survey, dynamisch aanbod, bevestiging, post-annulering
2. [ ] Exit survey heeft 5-8 redenen, meest voorkomende bovenaan
3. [ ] Elk save offer is gekoppeld aan een specifieke annuleringsreden (niet één korting voor alles)
4. [ ] "Ga door met annuleren" is altijd zichtbaar (geen dark patterns)
5. [ ] Dunning-sequentie bevat pre-dunning, smart retries en 4 e-mails
6. [ ] Bedragen in euro's getoond waar relevant (niet alleen percentages)
7. [ ] Compliance met FTC en GDPR/EU-consumentenrecht is geadresseerd
8. [ ] Health score model bevat gewichten voor alle 5 signaalcategorieën
9. [ ] Post-annulering pad is beschreven (heractivering + win-back)
10. [ ] Geen em dashes in de output
