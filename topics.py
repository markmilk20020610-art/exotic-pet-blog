# -*- coding: utf-8 -*-
"""
topics.py — the editorial topic pool.

`generate.py --grow N` pulls N unpublished topics out of `TOPIC_POOL`, assigns
them the next free `pet-00N` ids and writes them into `library.json`. This is
what stops the content factory from rewriting the same six guides forever: the
pool is the queue, `library.json` is what has already shipped, and the two
together are the anti-duplication record.

A topic is only eligible once its photograph exists on disk. That is deliberate:
an article whose image is missing renders a card with no animal on it, which is
worse than not publishing at all. Add the JPEG, and the next run picks it up.

Each entry carries:

  slug             stable identity used for de-duplication, never reused
  title            the <h1> and the card headline
  target_keyword   what the article is optimised for
  topic            short human label, injected into the prompt as context
  category         one of the three editorial topics
  group            one of the species classes
  species / sci    common name and binomial
  image / alt / caption
  facts            the parameters panel beside the article
  kit              (product_id, why, heading_hint) — ids must exist in affiliate.PRODUCTS
  body_html        hand-written fallback, used when the API key is absent or the
                   model draft is rejected. Must satisfy the same four-beat brief.

`GROUP_ROTATION` is the breadth guard: `grow()` walks it in order so a batch of
four articles cannot come back as four reptiles.
"""

GROUP_ROTATION = ["Reptiles", "Amphibians", "Invertebrates", "Exotic Mammals", "Birds"]

# Editorial topics stay within the classes the site already publishes. Adding a
# new one here is safe — taxonomy() derives the nav and the index page from the
# posts — but it changes the shape of the magazine, so it is a deliberate edit.
#
# "Birds" was added late and on purpose. In the UK and EU the working definition
# of an exotic pet is any animal kept as a companion that is not a cat, a dog or
# farmed livestock — which puts parrots and finches squarely inside it, next to
# reptiles and small mammals. The site was publishing three of the five classes
# and calling the scope complete.
TOPIC_POOL = [

    # ------------------------------------------------------------------ #
    # 1. Reptiles — a refusal that is seasonal, not pathological
    # ------------------------------------------------------------------ #
    {
        "slug": "corn-snake-winter-refusal",
        "title": "Why Your Corn Snake Refuses Food in Winter — and When It Is Not Brumation",
        "dek": "A four-month winter fast is normal biology. Losing a tenth of the body weight is not — here is how to tell them apart before you intervene.",
        "target_keyword": "corn snake not eating in winter",
        "topic": "Corn Snake winter feeding and brumation",
        "category": "Troubleshooting",
        "group": "Reptiles",
        "species": "Corn Snake",
        "sci": "Pantherophis guttatus",
        "author": "nell",
        "image": "corn-snake.jpg",
        "alt": "Adult corn snake (Pantherophis guttatus) with red-orange saddles edged in black, coiled on moss and leaf litter with its head raised clear of the body.",
        "caption": "An adult Pantherophis guttatus. A four-month winter fast is normal; losing more than a tenth of the body weight is not.",
        "facts": [
            ("Species", "Pantherophis guttatus"),
            ("Adult length", "120–150 cm"),
            ("Warm spot", "30–32 °C / 86–90 °F"),
            ("Cool end", "24–26 °C / 75–79 °F"),
            ("Brumation", "12–15 °C, 8–12 weeks"),
            ("Humidity", "40–60 %"),
        ],
        "kit": [
            ("heat-mat", "A thermostat-controlled mat is the only reliable way to hold a 30–32 °C hot spot without dragging the cool end up with it.", "warm spot"),
            ("ir-thermometer", "Measure the surface the snake actually sits on, not the air above it — a 6 °C error is normal between the two.", "measure"),
            ("kitchen-scale", "The 10 % weight rule is the single most useful number in this article, and it needs a scale that reads to 1 g.", "weight"),
        ],
        "tags": ["corn snake", "brumation", "refusal", "Pantherophis guttatus", "reptile"],
        "body_html": """
<p>A corn snake (<em>Pantherophis guttatus</em>) that refuses food in November is usually not ill — it is answering a photoperiod and thermal cue, and the whole diagnosis turns on two numbers: a warm spot of 30–32 °C (86–90 °F) and a body weight you have actually written down. Lose more than 10 % of that weight and the fast has stopped being brumation and started being a problem. Everything below is about telling those two states apart before you intervene, because intervening in the first one is how keepers cause the second.</p>

<h2>The winter I force-fed a snake that was not sick</h2>

<p>She was a nine-year-old female, 480 g in October, and by the first week of December she had refused three feeds in a row. I did what a worried keeper does: I raised the hot spot to 34 °C, left a warmed weaner in overnight, and covered the glass with a towel so she would feel private. She took it at 2 a.m. and regurgitated by morning. The smell in that room is something I can still call up. What it cost her was eleven days of an empty gut, a course of electrolytes, and a shed that came off in three pieces. What it cost me was the lesson that a refusal is information, not an emergency. She was 471 g — nine grams down, about 2 % — and she went on to brumate for ten weeks and eat in March like nothing had happened.</p>

<h2>What a drop in temperature does to a digestive tract</h2>

<p>Snakes do not chew and they do not grind. Digestion is a chemical process run by stomach acid and a gut flora that only work inside a narrow thermal window — broadly 26–30 °C for this species. Below roughly 18 °C that machinery stops, but the prey in the stomach does not. It sits there, it putrefies, and the animal's only defence is to reverse the peristalsis and eject it. Regurgitation is therefore not a sign of illness; it is a sign that food and temperature were mismatched. The danger is what follows: each regurgitation costs water, electrolytes and the gut lining's recovery time, and a snake that regurgitates three times in a season can develop oesophagitis and a permanent aversion to prey.</p>

<p>The same logic runs the other way in spring. A snake brought out of brumation is not ready to eat on the day you raise the thermostat — the gut needs seven to ten days back at full operating temperature before it can handle a meal, and the first meal should be smaller than usual.</p>

<h2>The parameters that decide which state you are in</h2>

<table>
  <thead>
    <tr><th>Signal</th><th>Normal winter fast</th><th>Worth a vet</th></tr>
  </thead>
  <tbody>
    <tr><td>Weight change over 8 weeks</td><td>0–8 % loss</td><td>Over 10 % loss</td></tr>
    <tr><td>Body condition</td><td>Round, spine not visible</td><td>Spine sharp, skin tents</td></tr>
    <tr><td>Behaviour when handled</td><td>Alert, tongue-flicks</td><td>Lethargic, no tongue-flick</td></tr>
    <tr><td>Hot spot</td><td>30–32 °C maintained</td><td>Below 28 °C, or unmeasured</td></tr>
    <tr><td>Droppings</td><td>None, or one urate</td><td>Mucus, blood, foul discharge</td></tr>
  </tbody>
</table>

<p>Note what is missing from that table: appetite. A snake that is brumating will often still strike at a warmed prey item, and a snake with a gut infection will sometimes take one too. Appetite is the least diagnostic signal available, which is why the weight column does the work.</p>

<h2>Reading the refusal, in order</h2>

<ol>
  <li><strong>Weigh the snake.</strong> Grams, same day of the week, before feeding. Two readings two weeks apart tell you more than any behaviour.</li>
  <li><strong>Measure the surface, not the air.</strong> An infrared thermometer on the hot-spot hide; 30–32 °C is the target, and a 3 °C drift downward is enough to stop digestion.</li>
  <li><strong>Check the cool end is actually cool.</strong> A single mat in a small vivarium can raise the whole gradient to 28 °C, which removes the thermal choice the snake needs to regulate itself.</li>
  <li><strong>Check the prey temperature.</strong> A thawed rodent at room temperature reads as carrion. Warm it to 35–37 °C in a bag in hot water and offer it at dusk.</li>
  <li><strong>Leave it alone for a week.</strong> No handling, no re-offering, no covering the glass. Repeated disturbance is the most common cause of a refusal that outlasts the season.</li>
</ol>

<p>If the weight holds and the parameters are right, the correct intervention is no intervention. If the weight is falling, stop treating it as brumation and get a faecal check — the two most common findings in a winter refusal that is not seasonal are flagellates and a low-grade respiratory infection, and neither is visible from outside the glass.</p>

<h2>Frequently asked questions</h2>

<h3>Should I brumate my corn snake every year?</h3>
<p>No. Brumation is a breeding tool, not a health requirement. A healthy adult can be kept at normal temperatures all winter and simply fed less often — every 14 to 21 days rather than every 7. Only brumate if you intend to breed, and only after a veterinary check and a full gut clearance of at least two weeks.</p>

<h3>How long can a corn snake go without food before it is dangerous?</h3>
<p>An adult in good body condition can go eight to twelve weeks without meaningful risk, provided fresh water is available and the weight loss stays under 10 %. Hatchlings are a different animal entirely: two weeks of refusal in a 15 g hatchling is an emergency, because they have no fat reserve to draw on.</p>

<h3>My snake ate, then regurgitated two days later. What now?</h3>
<p>Wait ten to fourteen days before offering anything — the gut lining needs that long to recover — then offer a prey item half the usual size with the hot spot verified at 30–32 °C. If a second regurgitation follows, stop feeding entirely and get a vet involved; repeated regurgitation in corn snakes is more often infectious or obstructive than husbandry-related.</p>
""",
    },

    # ------------------------------------------------------------------ #
    # 2. Amphibians — the skin as an absorptive organ
    # ------------------------------------------------------------------ #
    {
        "slug": "pacman-frog-substrate-toxicity",
        "title": "Pacman Frog Setup: Why the Substrate Is a Chemical Filter, Not Decoration",
        "dek": "An amphibian drinks through its skin, so the substrate is not decoration. It is the water supply, the filter and the infection risk in one layer.",
        "target_keyword": "pacman frog substrate setup humidity",
        "topic": "Pacman Frog habitat and substrate chemistry",
        "category": "Habitat Setup",
        "group": "Amphibians",
        "species": "Pacman Frog",
        "sci": "Ceratophrys cranwelli",
        "author": "idris",
        "image": "pacman-frog.jpg",
        "alt": "Pale yellow morph of Cranwell's horned frog (Ceratophrys cranwelli) sitting on damp moss against the wall of a clear plastic tub, its wide mouth closed and its eyes level with the substrate.",
        "caption": "Ceratophrys cranwelli spends most of its life buried to the eyes. The substrate is in contact with its skin twenty-four hours a day.",
        "facts": [
            ("Species", "Ceratophrys cranwelli"),
            ("Adult size", "10–15 cm SVL"),
            ("Day temperature", "24–28 °C / 75–82 °F"),
            ("Night drop", "21–23 °C / 70–73 °F"),
            ("Humidity", "70–85 %"),
            ("Substrate depth", "8–10 cm"),
        ],
        "kit": [
            ("coco-fibre", "The only substrate that holds 70–85 % humidity without waterlogging, and it can be changed weekly without costing a fortune.", "substrate"),
            ("hygrometer", "Amphibian skin does not negotiate. A digital hygrometer at substrate level is the difference between 60 % and 80 %.", "humidity"),
            ("heat-mat", "A mat on a thermostat, mounted to one side — never under the whole tub, or the frog has no cool retreat.", "temperature"),
        ],
        "tags": ["pacman frog", "Ceratophrys cranwelli", "substrate", "amphibian", "humidity"],
        "body_html": """
<p>A Pacman frog (<em>Ceratophrys cranwelli</em>) has no diaphragm, no chest cavity worth the name, and skin that absorbs water and dissolved ions directly from whatever it is sitting on. That single fact turns the substrate question from a matter of taste into a matter of chemistry: at 70–85 % relative humidity and 24–28 °C, a waterlogged 8–10 cm layer of coconut fibre is a functioning biological filter, and a sour, compacted one is a bath of ammonia in direct contact with an animal that drinks through its belly. Most of the "mystery" deaths in this species happen in the second kind of tub.</p>

<h2>The tub that smelled like a pond</h2>

<p>I kept a juvenile in a 45 × 45 × 30 cm tub on 10 cm of coco-fibre, misting twice a day because every care sheet said twice a day. By week three the frog had stopped burrowing, sat in the corner with its hind legs splayed, and had a faintly sweet smell I could not place. I changed the substrate and it came back within four days — then went off again a week later. What I had built was not a humid enclosure, it was a swamp: the bottom four centimetres were anaerobic, the drainage was nonexistent, and the ammonia reading at substrate level was somewhere north of 4 ppm. The fix was unglamorous. A 2 cm leca drainage layer, a mesh divider, 8 cm of fresh fibre, and misting measured with a hygrometer instead of a schedule. He has burrowed every night since.</p>

<h2>How amphibian skin turns a dirty substrate into a systemic problem</h2>

<p>Amphibian skin is not a barrier; it is an exchange surface, densely supplied with capillaries and used for respiration, osmoregulation and ion uptake. Nitrogenous waste — ammonia from the frog's own urine and from uneaten prey rotting in the fibre — dissolves in the film of water on the skin and crosses it. Ammonia at low concentrations burns the epidermis; at higher ones it drives the systemic load that presents as lethargy, splayed posture and the reddening of the hind limbs that keepers call red-leg, which is usually a <em>Aeromonas</em> or <em>Pseudomonas</em> septicaemia riding on top of a husbandry failure. This is why a Pacman frog can look perfectly healthy and be sitting in the cause of its own decline for a fortnight.</p>

<p>The same absorptive surface is why the water bowl matters more than its size suggests. Dechlorinated water, changed daily, deep enough to cover the vent but shallow enough to stand in — 2–3 cm for an adult. Chlorinated tap water left to stand overnight is not dechlorinated; chloramine does not off-gas, and a dechlorinator is a two-pound bottle that removes the whole question.</p>

<h2>The parameters, and where to measure them</h2>

<table>
  <thead>
    <tr><th>Parameter</th><th>Target</th><th>Measured where</th><th>Failure mode</th></tr>
  </thead>
  <tbody>
    <tr><td>Humidity</td><td>70–85 %</td><td>At substrate surface, under the lid</td><td>Drying → dysecdysis, lethargy</td></tr>
    <tr><td>Day temperature</td><td>24–28 °C</td><td>Warm third of the tub, 2 cm above substrate</td><td>Below 22 °C → refusal, slow digestion</td></tr>
    <tr><td>Night drop</td><td>21–23 °C</td><td>Same point</td><td>No drop → chronic stress, poor feeding response</td></tr>
    <tr><td>Substrate depth</td><td>8–10 cm</td><td>Vertical, uncompressed</td><td>Too shallow → cannot bury, feels exposed</td></tr>
    <tr><td>Ammonia (substrate water)</td><td>Under 0.25 ppm</td><td>Squeezed sample from the bottom layer</td><td>Rising → skin lesions, red-leg</td></tr>
  </tbody>
</table>

<p>The ammonia row is the one nobody tests and the one that explains most of the failures. A cheap aquarium ammonia test on water squeezed from the bottom of the substrate, once a week, tells you when to change it far more reliably than a calendar.</p>

<h2>Building the tub so it stays clean</h2>

<ol>
  <li><strong>Drainage first.</strong> 2 cm of leca or gravel, then a mesh divider. Without it the fibre sits in its own runoff and goes anaerobic within a fortnight.</li>
  <li><strong>Eight to ten centimetres of coco-fibre</strong>, damp enough to clump in the fist without a drop coming out. That is roughly 60 % water by weight and it is the whole humidity trick.</li>
  <li><strong>One side warm, one side cool.</strong> A thermostat-controlled mat under a third of the base, never the whole thing, so the frog can choose 24 °C or 27 °C.</li>
  <li><strong>Full substrate change every four to six weeks</strong>, spot-clean daily. A bioactive setup with springtails can stretch that, but only if the drainage layer is real.</li>
  <li><strong>Feed out of the substrate.</strong> Tong-feed or use a smooth feeding dish. A cricket that dies buried in damp fibre is an ammonia source you will never see.</li>
</ol>

<p>Do those five things and the species becomes almost boringly hardy, which is the reputation it deserves and rarely gets.</p>

<h2>Frequently asked questions</h2>

<h3>Can I use potting soil instead of coco-fibre?</h3>
<p>Only if it is guaranteed free of fertiliser, perlite and wetting agents, which most retail compost is not. The risk is not worth the saving: a single bag with slow-release fertiliser beads will kill an amphibian through its skin within days. Coco-fibre is cheap, consistent and inert, and there is no strong reason to look further.</p>

<h3>My frog has not burrowed for a week. Is that normal?</h3>
<p>Sometimes — a frog that is about to shed or that has just eaten heavily will sit out. But if it is sitting exposed, splayed and dull, check the substrate temperature first and the ammonia second. Both push a Ceratophrys out of the substrate, and both are fixable within an hour.</p>

<h3>How often should I mist?</h3>
<p>When the hygrometer says so, not on a schedule. In a sealed tub with a mesh vent, 70–85 % typically holds for two to three days after a heavy misting. Mist the substrate, not the frog, and never to the point where water pools at the bottom.</p>
""",
    },

    # ------------------------------------------------------------------ #
    # 3. Invertebrates — ecdysis and the humidity window
    # ------------------------------------------------------------------ #
    {
        "slug": "emperor-scorpion-molt-failure",
        "title": "Emperor Scorpion Molt Failure: The Humidity Window You Have About Six Hours to Hit",
        "dek": "A scorpion has roughly six hours to finish moulting before its new shell hardens. Humidity is the only variable you actually control.",
        "target_keyword": "emperor scorpion molt problems humidity",
        "topic": "Emperor Scorpion ecdysis and moult failure",
        "category": "Troubleshooting",
        "group": "Invertebrates",
        "species": "Emperor Scorpion",
        "sci": "Pandinus imperator",
        "author": "mara",
        "image": "emperor-scorpion.jpg",
        "alt": "Emperor scorpion (Pandinus imperator) with a glossy black carapace and heavy granular claws, walking across pale sand with its tail curled up over its back.",
        "caption": "Pandinus imperator. A mismoult is almost always a humidity event, not a genetic one.",
        "facts": [
            ("Species", "Pandinus imperator"),
            ("Adult size", "15–20 cm"),
            ("Temperature", "24–28 °C / 75–82 °F"),
            ("Humidity", "70–80 %"),
            ("Premoult fast", "2–4 weeks"),
            ("Post-moult hardening", "10–14 days"),
        ],
        "kit": [
            ("coco-fibre", "Deep, damp fibre is what holds 70–80 % through a moult; a dry substrate is the single most common cause of a stuck exoskeleton.", "humidity"),
            ("hygrometer", "A mismoult happens in a six-hour window. Without a hygrometer you cannot know you are inside it.", "measure"),
            ("snug-hides", "A sealed, dark retreat is where the animal moults. Without one it moults in the open and aborts.", "hide"),
        ],
        "tags": ["emperor scorpion", "Pandinus imperator", "moult", "ecdysis", "invertebrate"],
        "body_html": """
<p>An emperor scorpion (<em>Pandinus imperator</em>) moults by splitting its old cuticle along the carapace and drawing an entirely soft body out of it, and that body has roughly six hours before the new cuticle starts to harden whether or not the animal has finished emerging. The parameter that decides the outcome is humidity, held at 70–80 % at 24–28 °C, and it has to be right before the process starts — misting a scorpion that is already half out of its old skin does nothing. This is the one husbandry number in the hobby where being late is indistinguishable from being wrong.</p>

<h2>The night I misted too late</h2>

<p>A subadult female, seven centimetres, had been fasting for nineteen days and had gone the dull, dusty grey that means premoult. I knew the schedule. What I did not do was check the hygrometer, because the substrate looked damp and I had misted on Sunday. She started at some point in the small hours; by the time I looked in at eight she had her carapace and four legs out and the two rear legs were still inside the old exoskeleton, which had dried and clamped. She lived. She also lost the tarsus on one rear leg and dragged it for the next two moults. The reading that night, when I finally looked, was 54 %. The surface was damp; the air two centimetres up, where she had chosen to moult, was not. I have kept a hygrometer taped at substrate level ever since, and I mist the evening before the expected date rather than on the day.</p>

<h2>What ecdysis actually requires</h2>

<p>The old cuticle is digested from underneath by an moulting fluid that the epidermis secretes, and the new cuticle laid down beneath it is soft, wrinkled and highly permeable until it sclerotises. Two things have to happen in sequence: the old shell must be soft enough at the seams to split, and the new one must stay hydrated long enough for the animal to complete its exit and expand to the new size. Low humidity attacks both ends of that. The seams dry and resist splitting; the emerged cuticle loses water faster than the animal can replace it, and the limbs that are still inside get stuck as the surrounding shell hardens around them.</p>

<p>This is why the damage is always distal. The animal gets its body out, then its legs, then fails at the last segment — a claw, a tarsus, the tip of the metasoma. A stuck claw is not cosmetic: it constricts, the tissue necroses, and the scorpion often self-amputates at the next joint. And because the exoskeleton is also the respiratory surface's housing and the main water barrier, a botched moult leaves the animal more vulnerable to the next one.</p>

<h2>The moult timeline, and what to do at each point</h2>

<table>
  <thead>
    <tr><th>Stage</th><th>Duration</th><th>What you see</th><th>Action</th></tr>
  </thead>
  <tbody>
    <tr><td>Premoult</td><td>2–4 weeks</td><td>Refuses food, dull colour, hides sealed</td><td>Raise humidity to 75–80 %, stop feeding</td></tr>
    <tr><td>Ecdysis</td><td>15–60 minutes</td><td>Carapace splits, body draws out</td><td>Do nothing. No misting, no handling</td></tr>
    <tr><td>Expansion</td><td>6–24 hours</td><td>New cuticle pale, soft, stretched</td><td>Keep humidity high, leave the exuvia in place</td></tr>
    <tr><td>Sclerotisation</td><td>10–14 days</td><td>Colour darkens, shell hardens</td><td>No food until fully dark</td></tr>
  </tbody>
</table>

<p>The "leave the exuvia in place" instruction is not sentiment. A freshly moulted scorpion will often return to its own shed skin and eat part of it, recovering water and minerals it cannot get any other way. Remove it after a week if it is untouched.</p>

<h2>Preventing the next one</h2>

<ol>
  <li><strong>Measure at substrate level, not at the lid.</strong> Humidity stratifies hard in a shallow tub; the difference between the surface and 3 cm up is routinely 20 points.</li>
  <li><strong>Deepen the substrate to 10–12 cm.</strong> A scorpion that can seal itself into a chamber dug in damp fibre creates its own microclimate and stops depending on yours.</li>
  <li><strong>Provide one hide that holds moisture</strong> — cork bark over damp fibre, or a moss-filled cavity. That is where ecdysis will happen.</li>
  <li><strong>Stop feeding at the first sign of premoult.</strong> A live cricket in the enclosure during a moult will chew on a soft scorpion, and the resulting injury is usually fatal.</li>
  <li><strong>Do not disturb.</strong> Opening the lid to check progress drops humidity at exactly the wrong moment and is the second most common cause of a stuck moult after dry substrate.</li>
</ol>

<h2>Frequently asked questions</h2>

<h3>My scorpion lost a claw during its moult. Will it grow back?</h3>
<p>Partially, over two or three subsequent moults, and only if it is still eating and the humidity is corrected. Regeneration is never complete — a regrown claw is usually smaller and less robust — but a captive emperor with one reduced claw lives a normal lifespan. The immediate risk is infection at the stump, so keep the substrate clean and do not handle it.</p>

<h3>How do I know a moult is imminent?</h3>
<p>Three signs together: a fast that has run past two weeks, a colour that has gone from glossy black to dull grey-brown, and a sealed hide. The dullness is the reliable one, because it is the old cuticle separating from the new one underneath. When you see all three, raise humidity and stop feeding.</p>

<h3>Can I handle my scorpion while it is moulting?</h3>
<p>No, and not for two weeks afterwards either. A newly moulted emperor is soft enough that a fingernail leaves a permanent dent, and the stress of being lifted frequently aborts the expansion phase. Leave it entirely alone until the colour has returned to full black.</p>
""",
    },

    # ------------------------------------------------------------------ #
    # 4. Exotic mammals — torpor, obesity and mineral balance
    # ------------------------------------------------------------------ #
    {
        "slug": "hedgehog-torpor-obesity-calcium",
        "title": "Hedgehog Torpor, Obesity and the Calcium-to-Phosphorus Ratio That Causes Both",
        "dek": "Torpor, obesity and a lopsided calcium-to-phosphorus ratio are the same welfare problem caught at three different stages.",
        "target_keyword": "african pygmy hedgehog diet calcium phosphorus",
        "topic": "African Pygmy Hedgehog nutrition and torpor risk",
        "category": "Feeding Guide",
        "group": "Exotic Mammals",
        "species": "African Pygmy Hedgehog",
        "sci": "Atelerix albiventris",
        "author": "idris",
        "image": "hedgehog.jpg",
        "alt": "African pygmy hedgehog (Atelerix albiventris) with banded spines and a cream face, walking on red-brown earth with its snout lowered.",
        "caption": "Atelerix albiventris. Below about 20 °C it will attempt torpor, and a hedgehog that torpors repeatedly does not do so without cost.",
        "facts": [
            ("Species", "Atelerix albiventris"),
            ("Adult weight", "300–600 g"),
            ("Ambient temperature", "24–27 °C / 75–81 °F"),
            ("Dietary protein", "30–35 %"),
            ("Dietary fat", "Under 15 %"),
            ("Ca:P target", "1.5–2 : 1"),
        ],
        "kit": [
            ("kitchen-scale", "A hedgehog's whole health picture is a weight curve. Weigh weekly to 1 g and write it down.", "weight"),
            ("heat-mat", "A thermostat-controlled mat under part of the cage holds 24–27 °C without turning the whole vivarium into an oven.", "temperature"),
            ("calcium-d3", "The supplement that fixes a diet built on mealworms — but only when it is dusted by weight, not by eye.", "calcium"),
        ],
        "tags": ["hedgehog", "Atelerix albiventris", "torpor", "obesity", "calcium phosphorus"],
        "body_html": """
<p>An African pygmy hedgehog (<em>Atelerix albiventris</em>) has a body temperature it cannot defend below roughly 20 °C, and its answer to a cold night is not to shiver but to shut down — a torpor state that drops metabolism by up to 80 %. That is a wild survival trick, and in a centrally heated flat it is almost always a husbandry accident. The numbers that keep it from happening are a cage held at 24–27 °C, an adult weight between 300 and 600 g, and a diet with a calcium-to-phosphorus ratio of 1.5–2 : 1. Miss the third and you get the obesity and the wobbly gait that get misdiagnosed as wobbly hedgehog syndrome for months.</p>

<h2>The hedgehog that went cold in a warm room</h2>

<p>She came in at 240 g, small for an adult but not alarming, and the owner's complaint was that she had "gone quiet". I asked the one question that mattered — what temperature is that room at night — and got a shrug. The overnight reading in the spare bedroom was 17 °C. She had torpored four nights running, and every time she came out of it she ate less. By the time I weighed her she was 198 g, the spines along her flank were sparse, and she swayed when she walked. The owner had already read about wobbly hedgehog syndrome and had convinced herself of the worst. I told her it was not WHS; it was four cold nights, a bowl of mealworms and a scale nobody owned. We moved the cage into a 25 °C room, I cut the mealworms down to a garnish, and she was 372 g five months later. The sway went with the weight.</p>

<h2>Why repeated torpor is not free</h2>

<p>Torpor is a controlled metabolic depression: heart rate falls from around 250 beats per minute to under 20, core temperature tracks ambient, and the immune system largely stops. Coming out of it costs a large burst of thermogenesis, which is paid for in brown adipose tissue and, in a captive animal with limited reserves, in muscle. Repeated arousal cycles — which is what happens when a hedgehog torpors every night and is woken every morning by a warm room — deplete glycogen, suppress immune function and are associated with fatty liver change. The animal does not die of cold. It dies of the metabolic debt of going in and out of it.</p>

<p>The dietary half is separate and additive. Mealworms and waxworms are the two things every new keeper feeds and the two worst things to feed freely: their calcium-to-phosphorus ratio is around 0.1 : 1, which means they actively pull calcium out of the body to be metabolised. A diet anchored on them produces a growing animal with soft bones, tremors and a swaying gait — nutritional secondary hyperparathyroidism, the same mechanism as metabolic bone disease in reptiles. It looks like a neurological disease because it is one, downstream.</p>

<h2>What a correct diet actually looks like</h2>

<table>
  <thead>
    <tr><th>Component</th><th>Share of diet</th><th>Ca:P</th><th>Notes</th></tr>
  </thead>
  <tbody>
    <tr><td>Complete hedgehog kibble</td><td>60–70 %</td><td>1.2–1.5 : 1</td><td>Protein 30–35 %, fat under 15 %</td></tr>
    <tr><td>Cooked lean meat or egg</td><td>20–25 %</td><td>0.1–0.2 : 1</td><td>Always dusted, never the base</td></tr>
    <tr><td>Insects (mealworm, cricket)</td><td>Under 10 %</td><td>0.1 : 1</td><td>Treat only, dusted with calcium</td></tr>
    <tr><td>Vegetable matter</td><td>5 %</td><td>—</td><td>Mostly ignored; do not rely on it</td></tr>
  </tbody>
</table>

<p>The dusting instruction is where most keepers go wrong in the other direction. Calcium with D3 should be applied so the insect looks lightly frosted, roughly 0.1 g per mealworm, and the supplement should be a reptile-grade powder with a known calcium content rather than a crushed human tablet. Over-supplementation causes its own problems — soft tissue calcification, constipation — which is why the ratio matters more than the absolute amount.</p>

<h2>The weekly routine that catches problems early</h2>

<ol>
  <li><strong>Weigh every Sunday, same time, before food.</strong> A 5 % change in a month is noise; 10 % is a veterinary appointment.</li>
  <li><strong>Hold the room at 24–27 °C overnight.</strong> A thermostat on a heat mat under a third of the cage, plus a thermometer at hedgehog height, not at the top of the vivarium.</li>
  <li><strong>Feed once, at dusk.</strong> Hedgehogs are crepuscular; a bowl left all day is a bowl the animal grazes on and a weight you cannot interpret.</li>
  <li><strong>Track the wheel.</strong> A hedgehog that stops running is a hedgehog that is either cold, ill or obese, and the wheel is the earliest signal you will get.</li>
  <li><strong>Dust, do not drench.</strong> Every insect meal gets calcium powder, and no meal is insects alone.</li>
</ol>

<h2>Frequently asked questions</h2>

<h3>Is torpor the same as hibernation?</h3>
<p>No. Hibernation is a planned, seasonal, multi-week state; torpor is an emergency short-term shutdown that an African pygmy hedgehog should never need in captivity. This species does not hibernate in the wild, and a captive one that goes cold is a husbandry failure, not a natural cycle.</p>

<h3>My hedgehog is 780 g. Is that obese?</h3>
<p>Almost certainly, unless it is a very large male at the top of the range. Above 700 g the risks are fatty liver, arthritis and difficulty self-anointing. Cut the insect component out entirely, reduce the kibble by a fifth, and increase out-of-cage time before changing anything else.</p>

<h3>Can I use a reptile calcium supplement?</h3>
<p>Yes, and it is usually the better choice, because reptile powders are formulated for an animal that also needs D3 and are dosed by weight. Avoid anything with added phosphorus — the point of the supplement is to correct a ratio, and a calcium-plus-phosphorus product does not move it.</p>
""",
    },

    # ------------------------------------------------------------------ #
    # Second wave — the four that were queued for artwork. Their JPEGs are now
    # in static/images/, so grow() will publish them on the next run.
    # ------------------------------------------------------------------ #
    {
        "slug": "gargoyle-gecko-handling-stress",
        "title": "Gargoyle Gecko Handling: Reading Stress Before It Becomes a Tail Drop",
        "dek": "A dropped tail never grows back. Here is what a gargoyle gecko tells you before it gets that far.",
        "target_keyword": "gargoyle gecko handling stress tail drop",
        "topic": "Gargoyle Gecko handling and stress behaviour",
        "category": "Troubleshooting",
        "group": "Reptiles",
        "species": "Gargoyle Gecko",
        "sci": "Rhacodactylus auriculatus",
        "author": "nell",
        "image": "gargoyle-gecko.jpg",
        "alt": "Gargoyle gecko (Rhacodactylus auriculatus) gripping a branch, its grey-brown skin banded with dark chevrons and one large lidless eye catching the light.",
        "caption": "Rhacodactylus auriculatus. The tail regrows, but never as the original — a dropped tail comes back short and smooth.",
        "facts": [
            ("Species", "Rhacodactylus auriculatus"),
            ("Adult size", "20–25 cm total"),
            ("Temperature", "22–26 °C / 72–79 °F"),
            ("Humidity", "60–80 %"),
            ("Tail regeneration", "None — dropped tails do not regrow"),
        ],
        "kit": [("coco-fibre", "A deep, damp substrate is the difference between a gecko that feels covered and one that stays braced.", "substrate")],
        "tags": ["gargoyle gecko", "Rhacodactylus auriculatus", "handling", "stress"],
    },
    {
        "slug": "axolotl-nitrogen-cycle",
        "title": "Axolotl Water Chemistry: The Nitrogen Cycle That Kills Them Quietly",
        "dek": "Ammonia, then nitrite, then nitrate — the three numbers that decide whether an axolotl thrives or quietly burns.",
        "target_keyword": "axolotl water parameters ammonia nitrite",
        "topic": "Axolotl water chemistry and cycling",
        "category": "Habitat Setup",
        "group": "Amphibians",
        "species": "Axolotl",
        "sci": "Ambystoma mexicanum",
        "author": "idris",
        "image": "axolotl.jpg",
        "alt": "Leucistic axolotl (Ambystoma mexicanum) resting on gravel, its pale pink body ending in a long finned tail and three pairs of red feathery external gills.",
        "caption": "Ambystoma mexicanum. The gills are the readout: filaments that shrink and lose colour are the first sign of bad water.",
        "facts": [
            ("Species", "Ambystoma mexicanum"),
            ("Water temperature", "16–18 °C / 61–64 °F"),
            ("pH", "6.5–7.5"),
            ("Ammonia", "0 ppm"),
            ("Nitrite", "0 ppm"),
            ("Nitrate", "Under 20 ppm"),
        ],
        "kit": [("hygrometer", "Not for humidity here — the same digital unit's temperature probe is the cheapest way to watch a tank climb past 20 °C.", "temperature")],
        "tags": ["axolotl", "Ambystoma mexicanum", "nitrogen cycle", "water quality"],
    },
    {
        "slug": "leachianus-gecko-enclosure-size",
        "title": "Leachianus Gecko Enclosure Size: Why the Minimum Is Bigger Than You Think",
        "dek": "The largest gecko in the world does not fit in the smallest vivarium on the shelf. Here is the floor space it actually uses.",
        "target_keyword": "leachianus gecko enclosure size minimum",
        "topic": "Rhacodactylus leachianus housing",
        "category": "Habitat Setup",
        "group": "Reptiles",
        "species": "Leachianus Gecko",
        "sci": "Rhacodactylus leachianus",
        "author": "nell",
        "image": "leachianus-gecko.jpg",
        "alt": "Leachianus gecko (Rhacodactylus leachianus) on a cork branch, olive-brown loose skin folded at the neck and a pale gold eye ringed with dark pigment.",
        "caption": "Rhacodactylus leachianus, the largest gecko alive. Loose skin and a short tail are the build of a species that lives on vertical bark.",
        "facts": [
            ("Species", "Rhacodactylus leachianus"),
            ("Adult size", "30–40 cm total"),
            ("Minimum enclosure", "90 × 45 × 90 cm"),
            ("Temperature", "22–26 °C / 72–79 °F"),
            ("Humidity", "60–80 %"),
        ],
        "kit": [("coco-fibre", "Deep substrate holds the humidity this species needs without daily misting.", "substrate")],
        "tags": ["leachianus gecko", "Rhacodactylus leachianus", "enclosure", "housing"],
    },
    {
        "slug": "chinchilla-dust-bath-humidity",
        "title": "Chinchilla Dust Baths: Frequency, Humidity and the Skin Problems Overbathing Causes",
        "dek": "Dust baths are coat care until the room passes 60 % humidity, at which point they start feeding a fungal problem instead of solving one.",
        "target_keyword": "chinchilla dust bath how often humidity",
        "topic": "Chinchilla coat care and ambient humidity",
        "category": "Habitat Setup",
        "group": "Exotic Mammals",
        "species": "Chinchilla",
        "sci": "Chinchilla lanigera",
        "author": "idris",
        "image": "chinchilla.jpg",
        "alt": "Chinchilla (Chinchilla lanigera) sitting upright on a textured surface, dense blue-grey fur standing in soft tufts and large round ears held erect.",
        "caption": "Chinchilla lanigera. Up to eighty hairs grow from a single follicle, which is why a damp coat cannot dry and why dust — not water — is the cleaning method.",
        "facts": [
            ("Species", "Chinchilla lanigera"),
            ("Ambient humidity", "40–60 %"),
            ("Dust bath frequency", "2–3 times weekly, 10–15 min"),
            ("Temperature", "18–22 °C / 64–72 °F"),
            ("Coat density", "Up to 80 hairs per follicle"),
        ],
        "kit": [("hygrometer", "Ambient humidity above 60 % is what turns a dust bath from coat care into a fungal risk.", "humidity")],
        "tags": ["chinchilla", "Chinchilla lanigera", "dust bath", "humidity"],
    },
    {
        "slug": "mexican-redknee-tarantula-molt",
        "title": "Mexican Redknee Tarantula: Reading Pre-Moult Before She Seals Herself In",
        "dek": "A tarantula that stops eating for six weeks is not starving. She is rebuilding an exoskeleton, and the humidity in those weeks decides whether she comes out of it intact.",
        "target_keyword": "mexican red knee tarantula premolt not eating",
        "topic": "Brachypelma hamorii pre-moult and ecdysis",
        "category": "Troubleshooting",
        "group": "Invertebrates",
        "species": "Mexican Redknee Tarantula",
        "sci": "Brachypelma hamorii",
        "author": "mara",
        "image": "mexican-redknee-tarantula.jpg",
        "alt": "Mexican redknee tarantula (Brachypelma hamorii) on pale sand, its black legs banded with bright orange-red patches at the joints and a tan carapace edged in black.",
        "caption": "Brachypelma hamorii. The orange knee bands give the species its name, but the abdomen is what tells you a moult is coming.",
        "facts": [
            ("Species", "Brachypelma hamorii"),
            ("Adult leg span", "14–16 cm"),
            ("Temperature", "24–28 °C / 75–82 °F"),
            ("Humidity", "60–70 %"),
            ("Pre-moult fast", "2–6 weeks"),
            ("Post-moult hardening", "7–10 days"),
        ],
        "kit": [
            ("coco-fibre", "Deep, slightly damp fibre holds 60–70 % through a moult; bone-dry substrate is the usual cause of a stuck leg.", "humidity"),
            ("hygrometer", "A tarantula moults inside a chamber you cannot see into. The hygrometer is your only reading.", "measure"),
            ("snug-hides", "A dark, closed retreat is where ecdysis happens. Without one she moults in the open and aborts.", "hide"),
        ],
        "tags": ["tarantula", "Brachypelma hamorii", "moult", "ecdysis", "invertebrate"],
    },
    {
        "slug": "giant-african-millipede-substrate",
        "title": "Giant African Millipede Substrate: Depth, Calcium and the Chamber They Moult In",
        "dek": "A millipede burrows, eats the soil and hardens its shell with calcium from it. A shallow, calcium-poor substrate is a slow starvation of the exoskeleton.",
        "target_keyword": "giant african millipede substrate depth calcium",
        "topic": "Archispirostreptus gigas substrate and moulting",
        "category": "Habitat Setup",
        "group": "Invertebrates",
        "species": "Giant African Millipede",
        "sci": "Archispirostreptus gigas",
        "author": "mara",
        "image": "giant-african-millipede.jpg",
        "alt": "Giant African millipede (Archispirostreptus gigas) on sand, its glossy black cylindrical body made of many ringed segments with reddish-brown edges and pale legs beneath.",
        "caption": "Archispirostreptus gigas. Every segment carries two pairs of legs, and every moult needs calcium the animal cannot get from fruit.",
        "facts": [
            ("Species", "Archispirostreptus gigas"),
            ("Adult length", "15–30 cm"),
            ("Temperature", "24–28 °C / 75–82 °F"),
            ("Humidity", "70–80 %"),
            ("Substrate depth", "10–15 cm"),
            ("Lifespan", "5–7 years"),
        ],
        "kit": [
            ("coco-fibre", "The base of the substrate: 10–15 cm of it, damp enough to hold a burrow without collapsing.", "substrate"),
            ("hygrometer", "Below 70 % the moulting chamber dries and the new cuticle hardens before the animal is out of the old one.", "humidity"),
            ("snug-hides", "Cork bark on the surface gives a humid retreat above ground while the deep layer does the rest.", "hide"),
        ],
        "tags": ["millipede", "Archispirostreptus gigas", "substrate", "calcium", "invertebrate"],
    },
    {
        "slug": "sugar-glider-diet-ca-p",
        "title": "Sugar Glider Diet: The Calcium-to-Phosphorus Ratio Behind Hind-Limb Paralysis",
        "dek": "Hind-limb paralysis in sugar gliders is usually nutritional, not neurological. The number that predicts it is a calcium-to-phosphorus ratio, and fruit does not supply it.",
        "target_keyword": "sugar glider diet calcium phosphorus HLP",
        "topic": "Petaurus breviceps nutrition and hind-limb paralysis",
        "category": "Feeding Guide",
        "group": "Exotic Mammals",
        "species": "Sugar Glider",
        "sci": "Petaurus breviceps",
        "author": "idris",
        "image": "sugar-glider.jpg",
        "alt": "A sugar glider gripping a cork bark ledge, holding a piece of food in both forepaws",
        "caption": "Petaurus breviceps. A captive diet that reads as generous — fruit, honey, a little minced meat — can still be calcium-negative, which is how hind-limb paralysis starts in an animal that looks well fed.",
        "facts": [
            ("Species", "Petaurus breviceps"),
            ("Adult weight", "90–160 g"),
            ("Dietary protein", "25–30 %"),
            ("Ca:P target", "1.5–2 : 1"),
            ("Temperature", "24–27 °C / 75–81 °F"),
            ("Enclosure height", "At least 1.8 m"),
        ],
        "kit": [
            ("kitchen-scale", "A 90 g animal needs a scale that reads to 1 g to track a diet change.", "weight"),
            ("calcium-d3", "The supplement that corrects a fruit-heavy diet — dusted by weight, never by eye.", "calcium"),
        ],
        "tags": ["sugar glider", "Petaurus breviceps", "HLP", "calcium phosphorus"],
    },
    {
        "slug": "bearded-dragon-brumation",
        "title": "Bearded Dragon Brumation: How to Tell a Normal Slowdown From a Sick Lizard",
        "dek": "A bearded dragon that sleeps for ten weeks is following the season. One that sleeps at the wrong temperature is dying slowly, and from outside the glass the two look identical.",
        "target_keyword": "bearded dragon brumation or sick",
        "topic": "Pogona vitticeps brumation and its look-alikes",
        "category": "Troubleshooting",
        "group": "Reptiles",
        "species": "Bearded Dragon",
        "sci": "Pogona vitticeps",
        "author": "nell",
        "image": "bearded-dragon.jpg",
        "alt": "A bearded dragon flattened on red sand, dorsal spines and full tail in frame",
        "caption": "Pogona vitticeps. A dragon that stops eating and settles into a cool corner in October is brumating; the same behaviour at 32 °C in July is not brumation and needs a vet.",
        "facts": [
            ("Species", "Pogona vitticeps"),
            ("Adult length", "45–60 cm"),
            ("Basking spot", "38–42 °C / 100–108 °F"),
            ("Cool end", "24–26 °C / 75–79 °F"),
            ("Brumation", "10–16 weeks at 18–22 °C"),
            ("UVB", "10–12 % tube, 30–40 cm"),
        ],
        "kit": [
            ("uvb-fixture", "A brumating dragon still needs its UVB reviewed; a tube past its service life is a common winter mistake.", "uvb"),
            ("ir-thermometer", "Basking spot measured on the surface the lizard actually uses, not the air above it.", "measure"),
        ],
        "tags": ["bearded dragon", "Pogona vitticeps", "brumation", "reptile"],
    },

    # ------------------------------------------------------------------ #
    # 13. Birds — the class the site was missing
    # ------------------------------------------------------------------ #
    {
        "slug": "budgerigar-goitre-iodine",
        "title": "Budgerigar Goitre: Why a Seed-Only Diet Swells the Throat",
        "dek": "A budgie that squeaks instead of chirps and puffs at the throat is not fat and is not egg-bound. Its thyroid is enlarging against a trachea the width of a pencil lead.",
        "target_keyword": "budgerigar goitre iodine deficiency",
        "topic": "Melopsittacus undulatus thyroid enlargement and dietary iodine",
        "category": "Troubleshooting",
        "group": "Birds",
        "species": "Budgerigar",
        "sci": "Melopsittacus undulatus",
        "author": "nell",
        "image": "budgerigar.jpg",
        "alt": "Two budgerigars perched close together against a dark background, yellow faces and black-barred green wings in sharp detail.",
        "caption": "Melopsittacus undulatus. A diet of nothing but millet and canary seed supplies almost no iodine, and the thyroid enlarges into a space that has no room for it.",
        "facts": [
            ("Species", "Melopsittacus undulatus"),
            ("Adult weight", "30–40 g"),
            ("Dietary iodine", "0.1–0.2 mg/kg"),
            ("Trachea diameter", "2–3 mm"),
            ("Body temperature", "40–41 °C / 104–106 °F"),
            ("Life span", "7–10 years"),
        ],
        "kit": [
            ("kitchen-scale", "A 35 g bird needs 1 g resolution — the weight loss that precedes a goitre is a few grams, not a few tens.", "weight"),
            ("critical-care", "A budgie that can no longer swallow seed needs support feeding the same day, not a wait-and-see.", "feeding"),
        ],
        "tags": ["budgerigar", "Melopsittacus undulatus", "goitre", "iodine", "bird"],
    },
    {
        "slug": "african-grey-hypocalcaemia",
        "title": "African Grey Parrot Hypocalcaemia: The Seizure That Starts in the Seed Bowl",
        "dek": "The first sign is usually a bird that falls off its perch. By then the ionised calcium has been sliding for months, and the seed mix is the reason.",
        "target_keyword": "african grey parrot hypocalcaemia seizures",
        "topic": "Psittacus erithacus calcium metabolism and seed-only diets",
        "category": "Feeding Guide",
        "group": "Birds",
        "species": "African Grey Parrot",
        "sci": "Psittacus erithacus",
        "author": "idris",
        "image": "african-grey-parrot.jpg",
        "alt": "Head and shoulders of an African grey parrot, pale grey feathers, black beak and a yellow eye ring, against a soft green background.",
        "caption": "Psittacus erithacus. Seed mixes run near 0.1 % calcium against a phosphorus load several times higher, which is the wrong direction for a bird that lives fifty years.",
        "facts": [
            ("Species", "Psittacus erithacus"),
            ("Adult weight", "400–550 g"),
            ("Calcium in seed mix", "about 0.1 %"),
            ("Target Ca:P", "1.5–2 : 1"),
            ("Ionised Ca, normal", "1.0–1.3 mmol/L"),
            ("Life span", "50–60 years"),
        ],
        "kit": [
            ("calcium-d3", "The correction itself — dosed by weight into a food the bird actually eats, not sprinkled on seed it discards.", "calcium"),
            ("uvb-fixture", "A parrot indoors gets no cutaneous vitamin D3; a tube over the cage is what lets absorbed calcium be used.", "uvb"),
        ],
        "tags": ["african grey", "Psittacus erithacus", "hypocalcaemia", "calcium", "bird"],
    },

    # ------------------------------------------------------------------ #
    # 14. Reptiles — the species that punishes a misting schedule
    # ------------------------------------------------------------------ #
    {
        "slug": "panther-chameleon-hydration",
        "title": "Panther Chameleon Hydration: Why Misting Twice a Day Still Leaves Them Dry",
        "dek": "Chameleons do not drink standing water and they do not drink on demand. Hydration is a function of when the fog runs, not how wet the cage gets.",
        "target_keyword": "panther chameleon dehydration misting schedule",
        "topic": "Furcifer pardalis hydration, fogging and nighttime humidity",
        "category": "Habitat Setup",
        "group": "Reptiles",
        "species": "Panther Chameleon",
        "sci": "Furcifer pardalis",
        "author": "mara",
        "image": "panther-chameleon.jpg",
        "alt": "A male panther chameleon in profile on a bare branch, turquoise-green flanks barred in black with a red-orange eye turret.",
        "caption": "Furcifer pardalis. The animal drinks the droplets it can reach, which is why a fogger running before dawn matters more than a midday spray.",
        "facts": [
            ("Species", "Furcifer pardalis"),
            ("Basking spot", "28–32 °C / 82–90 °F"),
            ("Ambient", "22–26 °C / 72–79 °F"),
            ("Night drop", "16–18 °C / 61–64 °F"),
            ("Humidity, day", "50–70 %"),
            ("Humidity, night", "80–100 %"),
        ],
        "kit": [
            ("hygrometer", "Two of them — a single probe at the top of the cage reads the hot dry layer and tells you nothing about the plant canopy.", "measure"),
            ("leca-drainage", "A drainage layer under the substrate, so the fog that keeps humidity up does not become the standing water that grows bacteria.", "substrate"),
        ],
        "tags": ["panther chameleon", "Furcifer pardalis", "hydration", "humidity", "reptile"],
    },

    # ------------------------------------------------------------------ #
    # 15. Amphibians — the swelling that is not "just a fat frog"
    # ------------------------------------------------------------------ #
    {
        "slug": "whites-tree-frog-oedema",
        "title": "White's Tree Frog Oedema: Reading Fluid Retention Before the Lymph Hearts Fail",
        "dek": "A frog that looks pleasingly plump is often a frog that is not moving fluid. The difference between a good body condition score and oedema is where the swelling sits.",
        "target_keyword": "whites tree frog oedema bloating",
        "topic": "Ranoidea caerulea lymph hearts, oedema and water quality",
        "category": "Troubleshooting",
        "group": "Amphibians",
        "species": "White's Tree Frog",
        "sci": "Ranoidea caerulea",
        "author": "idris",
        "image": "whites-tree-frog.jpg",
        "alt": "A White's tree frog resting on a weathered branch, glossy green skin with scattered white spots and a heavy fold above the eye.",
        "caption": "Ranoidea caerulea. Amphibian skin absorbs water directly, so a chlorinated bowl bypasses the gut entirely and reaches the lymph system first.",
        "facts": [
            ("Species", "Ranoidea caerulea"),
            ("Adult length", "7–10 cm"),
            ("Adult weight", "40–80 g"),
            ("Humidity", "50–60 %"),
            ("Temperature", "24–28 °C / 75–82 °F"),
            ("Water", "dechlorinated, never straight tap"),
        ],
        "kit": [
            ("hygrometer", "Oedema and desiccation look identical from outside the glass; the humidity reading is what separates them.", "measure"),
            ("leca-drainage", "Drainage under a damp substrate keeps the frog out of the saturated layer where bacteria bloom.", "substrate"),
        ],
        "tags": ["whites tree frog", "Ranoidea caerulea", "oedema", "amphibian", "water quality"],
    },

    # ------------------------------------------------------------------ #
    # 16. Invertebrates — a shell is a mineral record
    # ------------------------------------------------------------------ #
    {
        "slug": "giant-african-land-snail-shell",
        "title": "Giant African Land Snail Shell Growth: Calcium, pH and the Rings That Record Both",
        "dek": "A snail cannot repair a thin shell, only add to it. Every ridge on the whorl is a fortnight of whatever calcium the keeper happened to supply.",
        "target_keyword": "giant african land snail shell calcium",
        "topic": "Lissachatina fulica shell growth, calcium availability and substrate pH",
        "category": "Feeding Guide",
        "group": "Invertebrates",
        "species": "Giant African Land Snail",
        "sci": "Lissachatina fulica",
        "author": "mara",
        "image": "giant-african-land-snail.jpg",
        "alt": "A giant African land snail in profile, brown-and-cream banded shell with the soft body extended and tentacles visible.",
        "caption": "Lissachatina fulica. Shell is deposited at the aperture only, so the growth rings near the lip are a record of the last few weeks of husbandry.",
        "facts": [
            ("Species", "Lissachatina fulica"),
            ("Shell length", "15–20 cm"),
            ("Substrate pH", "6.5–7.5"),
            ("Temperature", "22–26 °C / 72–79 °F"),
            ("Humidity", "70–90 %"),
            ("Calcium", "available continuously, not weekly"),
        ],
        "kit": [
            ("coco-fibre", "Depth matters more than material — a snail that cannot bury to its shell lip will not lay, and will not retreat from dry air.", "substrate"),
            ("hygrometer", "Below about 70 % the mantle stops depositing and the new lip goes thin and translucent.", "measure"),
        ],
        "tags": ["giant african land snail", "Lissachatina fulica", "shell", "calcium", "invertebrate"],
    },

    # ------------------------------------------------------------------ #
    # 17. Exotic Mammals — a species that cannot process sugar at all
    # ------------------------------------------------------------------ #
    {
        "slug": "degu-sugar-sensitivity",
        "title": "Degu Sugar Sensitivity: Why One Raisin Is a Different Risk Than One for a Rat",
        "dek": "Degus are the only common pet rodent that cannot handle dietary sugar at all. The mechanism is a missing gene, and it makes fruit a species-inappropriate food rather than a treat.",
        "target_keyword": "degu sugar diabetes diet",
        "topic": "Octodon degus insulin response, dietary fibre and diabetes",
        "category": "Feeding Guide",
        "group": "Exotic Mammals",
        "species": "Degu",
        "sci": "Octodon degus",
        "author": "nell",
        "image": "degu.jpg",
        "alt": "A degu standing on a flat surface holding a piece of food in both forepaws, brown agouti fur and a thin tufted tail behind.",
        "caption": "Octodon degus. Unlike rats and mice, degus lack the enzyme to clear a sugar load quickly, so a fruit-based treat is a metabolic event rather than a snack.",
        "facts": [
            ("Species", "Octodon degus"),
            ("Adult weight", "170–300 g"),
            ("Dietary fibre", "15–20 % crude fibre"),
            ("Fruit", "none — not as a treat either"),
            ("Body temperature", "37–38 °C / 99–100 °F"),
            ("Life span", "6–8 years"),
        ],
        "kit": [
            ("kitchen-scale", "A 200 g degu that gains 15 g in a fortnight on a new pellet is the earliest sign the fibre fraction dropped.", "weight"),
            ("critical-care", "Support feeding for a degu that has stopped eating — they decompensate faster than a rat of the same size.", "feeding"),
        ],
        "tags": ["degu", "Octodon degus", "diabetes", "fibre", "exotic mammal"],
    },
]
