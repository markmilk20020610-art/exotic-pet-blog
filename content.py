# -*- coding: utf-8 -*-
"""
content.py — editorial layer for Exotic Pet Care Hub.

Each entry is keyed by the `id` in keywords.json and supplies:
  * the magazine metadata (title, dek, species, facts, kit list)
  * a hand-written HTML body used as the offline / fallback corpus

generate.py prefers, in order:
  1. cache/<id>.html        (previously generated, committed to the repo)
  2. DeepSeek API           (when DEEPSEEK_API_KEY is set and --refresh is passed)
  3. body_html below        (deterministic, always available)

Images are never looked up by category. Each post declares an exact species
image from static/images/, so a jumping-spider guide can never show a dog.
"""

POSTS = {
    "pet-001": {
        "title": "How Often Should You Feed an Adult Jumping Spider?",
        "dek": "A plump abdomen is a better calendar than any schedule. Here is what adult jumping spiders actually eat, how often, and the two feeding mistakes that shorten their lives.",
        "category": "Feeding Guide",
        "group": "Invertebrates",
        "is_pinned": True,
        "species": "Regal Jumping Spider",
        "sci": "Phidippus regius",
        "author": "mara",
        "date": "2026-10-26",
        "image": "jumping-spider.jpg",
        "alt": "Male regal jumping spider (Phidippus regius) with banded black-and-white legs and iridescent green chelicerae, perched on the edge of a pale leaf.",
        "caption": "Male Phidippus regius. Males are smaller and shorter-lived than females, but the feeding rhythm is the same — one prey item every two to four days.",
        "facts": [
            ("Species", "Phidippus regius"),
            ("Adult size", "12–18 mm"),
            ("Feeding rhythm", "Every 2–4 days"),
            ("Prey size", "≤ body length"),
            ("Temperature", "24–28 °C / 75–82 °F"),
            ("Humidity", "60–70%"),
        ],
        "kit": [
            ("spider-enclosure", "Ventilated arboreal cube with cork bark and a feeding ledge — the whole starting point in one box.", "two mistakes"),
            ("hydei-culture", "The correct staple size for adults and juveniles alike, and it keeps producing for weeks.", "actually eat"),
            ("feeding-tongs", "Hand-feeding is the best part of keeping a regal. Tongs keep your fingers out of the strike zone."),
        ],
        "tags": ["jumping spider", "feeding", "Phidippus regius", "invertebrate"],
        "body_html": """
<p>You brought home a spider the size of a fingernail, and it has been watching you ever since. Now the question that every new keeper asks: <em>is it hungry?</em> The answer matters more than most care sheets admit, because adult jumping spiders are far more likely to be overfed than underfed — and overfeeding is the quieter, slower problem.</p>

<h2>What adult jumping spiders actually eat</h2>

<p>Jumping spiders are visual hunters. They do not build webs to catch dinner; they stalk, triangulate, and pounce. That means prey has to <strong>move</strong>. A dead insect will be ignored, then mould.</p>

<p>The workable menu for an adult <em>Phidippus regius</em>:</p>

<ul>
  <li><strong>Blue bottle or house flies</strong> — the best enrichment food. Fast, and they trigger a full hunting sequence.</li>
  <li><strong>Small crickets</strong> (4–6 mm) — a reliable staple, ideally gut-loaded for 24 hours first.</li>
  <li><strong>Hydei fruit flies</strong> — small, but useful for variety and for adults that are slowing down.</li>
  <li><strong>Mealworms</strong> — occasional only. High in fat, and they burrow if uneaten.</li>
  <li><strong>Waxworms</strong> — a treat. Think of them as the spider equivalent of cake.</li>
</ul>

<p>Size is the rule that matters most: prey should be <strong>no longer than the spider's body</strong>, legs excluded. Oversized crickets are not a challenge, they are an injury risk.</p>

<h2>How often to feed an adult</h2>

<p>Every two to four days, one or two appropriately sized prey items. That is the whole schedule. Adults have a far slower metabolism than spiderlings, and a spider that eats daily will become obese within a couple of months.</p>

<p>Three things move you within that range:</p>

<ul>
  <li><strong>Abdomen shape.</strong> Plump and oval is correct. Flat and pinched means feed now. Stretched and balloon-like means skip several days.</li>
  <li><strong>Sex.</strong> Gravid females eat more often and should not be rationed.</li>
  <li><strong>Season.</strong> Activity and appetite drop in cooler months, even indoors.</li>
</ul>

<blockquote>Feed the abdomen, not the calendar. A jumping spider's body condition is visible from across the room — use it.</blockquote>

<h2>The two mistakes that actually cause harm</h2>

<p><strong>1. Leaving live prey in the enclosure.</strong> A cricket left overnight will chew on a resting or moulting spider. Remove anything uneaten within 24 hours. This single habit prevents most captive injuries.</p>

<p><strong>2. Feeding straight through a moult.</strong> When a spider stops eating and seals itself into a silk hammock, it is in premoult. Do not feed, do not open the enclosure more than necessary. Wait until it is actively hunting again — usually five to ten days after the moult — before offering prey.</p>

<h2>Quick reference</h2>

<table>
  <tr><th>Factor</th><th>Adult jumping spider</th><th>Notes</th></tr>
  <tr><td>Frequency</td><td>Every 2–4 days</td><td>Judge by abdomen, not by habit</td></tr>
  <tr><td>Prey size</td><td>≤ body length</td><td>Legs excluded</td></tr>
  <tr><td>Prey count</td><td>1–2 per feed</td><td>Never a handful "for later"</td></tr>
  <tr><td>Water</td><td>Bottle-cap dish</td><td>Refresh every second day</td></tr>
  <tr><td>During moult</td><td>No food</td><td>Resume 5–10 days after</td></tr>
  <tr><td>Uneaten prey</td><td>Remove within 24 h</td><td>Non-negotiable</td></tr>
</table>

<h2>Frequently asked questions</h2>

<h3>Can I feed my jumping spider dead insects?</h3>
<p>No. Jumping spiders hunt by sight and movement. Dead prey is ignored, then spoils. The exception is pre-killed prey offered on tongs with a slight wiggle, which some captives will take — but live food is the default.</p>

<h3>My spider stopped eating. Is it dying?</h3>
<p>Usually not. Refusing food for a week or two is normal before a moult, and adult females also fast around egg-laying. Check the abdomen first; if it is still plump and the spider is alert, wait.</p>

<h3>How much water does it need?</h3>
<p>Very little. A shallow cap of water plus a light mist on one side of the enclosure every second or third day is enough. Never mist the spider directly.</p>
""",
    },

    "pet-002": {
        "title": "The Best Bioactive Substrate Mix for a Crested Gecko Tank",
        "dek": "Coir alone is not bioactive — it is a wet sponge. The mix that actually supports plants, springtails and a gecko that sheds cleanly, plus the drainage layer everyone skips.",
        "category": "Habitat Setup",
        "group": "Reptiles",
        "is_pinned": True,
        "species": "Crested Gecko",
        "sci": "Correlophus ciliatus",
        "author": "nell",
        "date": "2026-10-19",
        "image": "crested-gecko.jpg",
        "alt": "Crested gecko (Correlophus ciliatus) with rufous-brown skin and the raised crest scales above each eye, gripping a broad green leaf.",
        "caption": "Correlophus ciliatus. This species lives in the top two-thirds of the enclosure — the floor build matters far less than the climb.",
        "facts": [
            ("Species", "Correlophus ciliatus"),
            ("Mix ratio", "60% topsoil · 30% coir · 10% sand"),
            ("Depth", "7–10 cm over drainage"),
            ("Drainage layer", "4–5 cm LECA"),
            ("Crew", "Springtails + dwarf isopods"),
            ("Humidity", "60–80%, cycling"),
        ],
        "kit": [
            ("bioactive-substrate", "Pre-mixed, composted and ready to use. Saves you sourcing topsoil you can actually trust.", "The mix, by volume"),
            ("leca-drainage", "The layer that stops a bioactive floor turning into a swamp.", "drainage layer"),
            ("springtail-culture", "Mould control you cannot see working until it stops."),
        ],
        "tags": ["crested gecko", "bioactive", "substrate", "Correlophus ciliatus"],
        "body_html": """
<p>Almost every "bioactive" crested gecko setup online is a layer of coco coir with a fake plant pushed into it. It looks the part, it holds water, and it is not bioactive in any meaningful sense — there is nothing living in it to process waste, and no drainage to stop it going anaerobic.</p>

<p>A working substrate does three jobs at once: it drains, it hosts a cleanup crew, and it grows roots. That requires a layered mix, not a single bag of fibre.</p>

<h2>The mix, by volume</h2>

<p>This ratio works for crested geckos because it holds shape for burrowing crew members without compacting into an airless brick:</p>

<ul>
  <li><strong>60% organic topsoil</strong> — the structural base. Must be free of fertiliser, perlite and wetting agents.</li>
  <li><strong>30% coco coir</strong> — moisture retention. Coir alone is too dense; as a third of the mix it is ideal.</li>
  <li><strong>10% coarse sand or fine orchid bark</strong> — drainage and particle size variety, which is what stops the mix turning to mud.</li>
  <li><strong>A handful of leaf litter</strong> on the surface — food and cover for the crew, and it slows evaporation.</li>
  <li><strong>Crushed cuttlebone</strong> — calcium for isopod moults. Without it, a colony quietly fails.</li>
</ul>

<h2>The drainage layer nobody builds</h2>

<p>Under the substrate, 4–5 cm of LECA clay pebbles, separated by a fine mesh or weed fabric. Crested gecko enclosures are misted twice a day; without drainage, the bottom two centimetres of substrate become anaerobic within weeks and smell of sulphur when disturbed.</p>

<p>The drainage layer is also where your water reserve lives. You should be able to see the water level through the glass and keep it below the mesh — never touching the soil.</p>

<blockquote>A bioactive floor without drainage is not a ecosystem. It is a terrarium-shaped bog.</blockquote>

<h2>Depth, and why 7–10 cm is the number</h2>

<p>Shallow substrate cannot buffer moisture or support plant roots. Deep substrate without drainage drowns. Seven to ten centimetres over a drainage layer is the range that gives springtails somewhere to retreat when the surface dries, and gives plants enough root volume to establish.</p>

<p>If your enclosure is front-opening with a bottom vent, keep the substrate line below the vent. A blocked vent turns a well-designed enclosure into a stagnant box.</p>

<h2>Seeding the crew — and the order matters</h2>

<p>Add springtails first, generously, and give them two weeks before the gecko goes in. They colonise the mould before it becomes visible. Then add dwarf isopods — <em>Trichorhina tomentosa</em> is the safe choice for a humid, planted enclosure because it does not burrow deeply or chew live plants.</p>

<p>Do not add large <em>Porcellio</em> species to a crested gecko tank. They are protein-driven, and a sleeping gecko on the floor is, to them, a very large piece of scenery worth investigating.</p>

<h2>What "cycled" actually looks like</h2>

<p>A cycled substrate is dark, smells of forest floor, holds a burrow when you press it, and has visible springtails when you lift the leaf litter. It does not smell sour, it does not grow white fuzz across the surface, and it does not stay wet for a week.</p>

<p>Expect two to four weeks. Feed the crew a vegetable scrap once a week during that period, then stop — the gecko's waste takes over.</p>

<h2>Frequently asked questions</h2>

<h3>Can I use garden soil from outside?</h3>
<p>Only from ground you know is unsprayed, and only after baking or freezing it. The risk is not dirt — it is pesticides, which will kill your cleanup crew and can harm the gecko.</p>

<h3>Do I ever have to replace the substrate?</h3>
<p>Not on a schedule. Spot-clean visible waste, keep the crew alive, and top up leaf litter. Replace it if it turns anaerobic or the crew crashes — both are symptoms of a design problem, not a maintenance interval.</p>

<h3>Will the gecko eat the isopods?</h3>
<p>Occasionally, and it does no harm. A healthy crew out-breeds casual predation.</p>
""",
    },

    "pet-003": {
        "title": "How to Fix High Humidity and Mould in Isopod Cultures",
        "dek": "Mould in an isopod tub is almost never a humidity problem. It is an airflow problem, and the fix takes five minutes and a drill.",
        "category": "Troubleshooting",
        "group": "Invertebrates",
        "is_pinned": False,
        "species": "Isopod Culture",
        "sci": "Porcellio scaber",
        "author": "mara",
        "date": "2026-10-12",
        "image": "isopods.jpg",
        "alt": "Macro photograph of a single Porcellio scaber isopod, a slate-purple segmented woodlouse, on weathered bark.",
        "caption": "Porcellio scaber on weathered wood. A healthy culture shows animals at every life stage — one large adult is not a colony.",
        "facts": [
            ("Species", "Porcellio scaber"),
            ("Target humidity", "70–90%, graded"),
            ("Ventilation", "2–4 mesh vents, 25 mm"),
            ("Temperature", "20–24 °C / 68–75 °F"),
            ("Substrate", "5–7 cm coir + leaf litter"),
            ("Crew partner", "Springtails"),
        ],
        "kit": [
            ("hygrometer", "Two probes, min/max memory. Guessing humidity is how cultures crash.", "moisture gradient"),
            ("mesh-vents", "The actual fix for a mouldy tub. Drill, glue, done.", "five-minute fix"),
            ("springtail-culture", "Springtails eat mould before you can see it. Isopods eat the mould the springtails leave."),
        ],
        "tags": ["isopods", "mould", "humidity", "culture"],
        "body_html": """
<p>You open the tub and there it is: a white fur of mould spreading across the leaf litter, a sour smell, and isopods clustered on the walls trying to get away from the substrate. The instinct is to dry everything out. That instinct is wrong, and it usually kills the colony faster than the mould would have.</p>

<p>Mould is a symptom of still, saturated air. Isopods need high humidity <em>and</em> airflow, and almost every failing culture has one without the other.</p>

<h2>Why drying it out backfires</h2>

<p>Isopods breathe through pleopods that must stay moist. Drop the humidity sharply and you get a wave of deaths, failed moults, and a colony that never recovers its numbers. The mould goes away; so does everything else.</p>

<p>The correct move is to keep the moisture and <strong>move the air</strong>.</p>

<h2>The five-minute fix: ventilation</h2>

<p>Most cultures are kept in sealed food containers with a few pinpricks in the lid. That is not ventilation, it is a humidity trap. What works:</p>

<ul>
  <li><strong>Two to four vents</strong> of 25 mm, on opposing sides — not all in the lid.</li>
  <li><strong>Fine mesh</strong> (0.5 mm or smaller) glued over each, so springtails and hatchlings stay in.</li>
  <li><strong>One vent low, one high</strong> if you can manage it. That creates a convection loop instead of a dead zone.</li>
</ul>

<p>After drilling, expect the surface to dry within a day. That is the point — the substrate below stays damp, and the isopods move down.</p>

<blockquote>Humidity without airflow is a swamp. Airflow without humidity is a desert. A culture needs both, in the same box.</blockquote>

<h2>The moisture gradient, not a moisture number</h2>

<p>Stop trying to hit one humidity figure. Soak one end of the substrate and leave the other end dry, then let the animals choose. This gives you three things at once: a hydration zone, a dry refuge, and a visible indicator — isopods clustered in the middle mean the gradient is working.</p>

<p>Re-wet the damp end when it starts to feel dry to the touch, roughly every five to seven days. Never flood it. Standing water in the bottom of a tub is how you grow anaerobic bacteria and fungus gnats.</p>

<h2>Fix the food, not just the air</h2>

<p>Mould needs fuel. The usual culprits:</p>

<ul>
  <li><strong>Fresh vegetables left in too long.</strong> Remove after 48 hours, without exception.</li>
  <li><strong>Too much protein.</strong> Fish flake and dried shrimp are excellent — in pinches, weekly. A spoonful will mould and then crash the population.</li>
  <li><strong>Wet leaf litter.</strong> Leaves should be damp, not sodden. Bake or freeze collected leaves before use.</li>
  <li><strong>No springtails.</strong> Isopods are grazers, not mould specialists. Springtails are the mould specialists.</li>
</ul>

<h2>If the culture has already crashed</h2>

<p>Salvage what you can: move surviving adults to a fresh tub with new substrate and a properly vented lid. Do not reuse the mouldy substrate, and do not try to "rescue" it by drying — the spore load is already high.</p>

<p>Then diagnose before you restock. Nine times out of ten it was ventilation, and the same tub will fail again.</p>

<h2>Frequently asked questions</h2>

<h3>Is surface mould always a problem?</h3>
<p>Not always. A little white mycelium on a dead leaf is normal decomposition and the crew will eat it. Mould that spreads across the substrate, smells sour, or makes the isopods climb the walls is a problem.</p>

<h3>Do springtails really stop mould?</h3>
<p>They suppress it by grazing on hyphae and bacterial films before it becomes visible. They are not a steriliser — they work alongside ventilation, not instead of it.</p>

<h3>Should I use a lid at all?</h3>
<p>Yes, but a vented one. Fully open tubs dry out in hours and let in fungus gnats, which are far more annoying than the mould you were trying to fix.</p>
""",
    },

    "pet-004": {
        "title": "Why Your Ball Python Is Refusing Frozen-Thawed Rats",
        "dek": "Before you change the feeding schedule, change the thermometer. Nine out of ten feeding strikes are a temperature, security or presentation problem — in that order.",
        "category": "Feeding Guide",
        "group": "Reptiles",
        "is_pinned": False,
        "species": "Ball Python",
        "sci": "Python regius",
        "author": "nell",
        "date": "2026-10-05",
        "image": "ball-python.jpg",
        "alt": "Head portrait of a wild-type ball python (Python regius) with pale tan scales and dark brown blotching.",
        "caption": "Wild-type Python regius. A balled-up posture at feeding time is a security signal, not a hunger strike.",
        "facts": [
            ("Species", "Python regius"),
            ("Hot spot", "31–32 °C / 88–90 °F"),
            ("Cool end", "24–26 °C / 75–79 °F"),
            ("Humidity", "60–70%, 75%+ in shed"),
            ("Feed interval", "7–14 days, adult"),
            ("Prey", "Frozen-thawed, warmed to 37 °C"),
        ],
        "kit": [
            ("kitchen-scale", "Weigh the snake, weigh the prey. The only objective way to know if a strike is a problem.", "Overfeeding"),
            ("ir-thermometer", "Surface temperature at the hot spot, measured instead of assumed.", "Temperature, measured"),
            ("snug-hides", "Security is the most under-rated feeding trigger in the species.", "Security"),
            ("critical-care", "If the strike passes eight weeks, this is what buys you time to find a vet.", "The fast that is not"),
        ],
        "tags": ["ball python", "feeding strike", "frozen thawed", "Python regius"],
        "body_html": """
<p>Your ball python has eaten frozen-thawed reliably for eight months. Then it stops. It ignores the rat, balls up, and looks at you with the flat indifference that only a <em>Python regius</em> can manage. Two weeks pass. Three.</p>

<p>This is the most common question in the species, and the honest answer is that a feeding strike is usually not about food at all. Work through these in order, and do not skip ahead.</p>

<h2>1. Temperature, measured not guessed</h2>

<p>A ball python digests by choice. If the hot spot is 27 °C instead of 31 °C, digestion slows, the animal feels wrong, and it stops eating. This is the single most common cause, and the most commonly missed, because keepers trust the thermostat dial instead of a reading.</p>

<p>Measure the surface under the hot hide with an infrared gun. You want 31–32 °C. Cool end 24–26 °C. If the numbers are off, fix them and wait two weeks before drawing any conclusion.</p>

<h2>2. Security — the hide test</h2>

<p>A ball python that does not feel hidden will not eat. It is that simple, and it is why so many glass tanks with one oversized hide produce chronic problem feeders.</p>

<ul>
  <li>Two hides, identical, one warm one cool.</li>
  <li>Snug: the snake should touch the walls when coiled.</li>
  <li>Opaque back and sides on the enclosure — cover the glass if you must.</li>
  <li>Clutter. Empty floor space reads as exposure.</li>
</ul>

<p>If your snake spends all day in the cool hide and never uses the warm one, the warm hide is probably too big or too hot.</p>

<blockquote>A ball python that is not eating is usually a ball python that does not feel safe. Fix the room before you fix the rat.</blockquote>

<h2>3. Presentation: the rat is probably too cold</h2>

<p>Frozen-thawed prey must be thawed thoroughly and then <strong>warmed to roughly 37 °C</strong> at the head. A rat that is thawed but cool reads as carrion, and many ball pythons will refuse it indefinitely.</p>

<p>The reliable method: thaw in the fridge overnight, then place in a sealed bag in warm water for 10–15 minutes. Check the head with an infrared gun. Then offer with tongs, holding the rat at the level of the snake's head, with a small twitch — not a dance.</p>

<p>Do not refreeze. Do not microwave. Do not leave a refused rat in the enclosure overnight.</p>

<h2>4. Overfeeding, and the schedule nobody follows</h2>

<p>An adult ball python eats every 7–14 days, one prey item of roughly 10–15% of its body weight. Keepers who feed every five days "because it always takes it" end up with a fat snake that goes off food for months. If the spine is buried and the body is round in cross-section, the animal is overweight.</p>

<h2>5. The fast that is not a crisis</h2>

<p>Healthy adult ball pythons fast. Two to four months, typically over winter, is normal and requires no intervention if the animal is not losing weight quickly, is drinking, and is behaving normally.</p>

<p>What <em>is</em> a crisis: rapid weight loss, regurgitation, wheezing, mucus in the mouth, or a snake that is suddenly lethargic. Those are veterinary appointments, not husbandry puzzles.</p>

<h2>Quick diagnostic table</h2>

<table>
  <tr><th>What you see</th><th>Most likely cause</th><th>First action</th></tr>
  <tr><td>Refuses, stays in cool hide</td><td>Hot spot too cool or hide too large</td><td>Measure surfaces, resize hides</td></tr>
  <tr><td>Strikes then drops the rat</td><td>Prey too cold</td><td>Warm head to 37 °C</td></tr>
  <tr><td>Balls up, ignores entirely</td><td>Stress / no cover</td><td>Opaque sides, add clutter</td></tr>
  <tr><td>Refuses for months, weight stable</td><td>Normal seasonal fast</td><td>Monitor weight weekly</td></tr>
  <tr><td>Refuses, losing weight, lethargic</td><td>Illness or husbandry failure</td><td>Exotics vet</td></tr>
</table>

<h2>Frequently asked questions</h2>

<h3>How long can a ball python go without eating?</h3>
<p>A healthy adult can go several months. The number that matters is weight, not days. Weigh monthly; a loss of more than 10% of body weight is the point to involve a vet.</p>

<h3>Should I try live prey to break the strike?</h3>
<p>No. Live feeding is a welfare problem for the rodent and an injury risk for the snake, and it teaches a hunger strike to escalate. Fix temperature, security and prey temperature instead.</p>

<h3>Will handling make it worse?</h3>
<p>Yes, temporarily. Reduce handling to zero while you troubleshoot, and never handle in the 48 hours after a feed.</p>
""",
    },

    "pet-005": {
        "title": "Do Leopard Geckos Need UVB — or Just a Heat Mat?",
        "dek": "The honest answer is more interesting than either camp admits: leopard geckos are crepuscular, not nocturnal, and a low-level UVB zone changes how you supplement calcium.",
        "category": "Habitat Setup",
        "group": "Reptiles",
        "is_pinned": False,
        "species": "Leopard Gecko",
        "sci": "Eublepharis macularius",
        "author": "idris",
        "date": "2026-09-28",
        "image": "leopard-gecko.jpg",
        "alt": "Leopard gecko (Eublepharis macularius) in wild-type colouration — pale yellow with black spotting and a thick tail — photographed against a plain background.",
        "caption": "Wild-type Eublepharis macularius. A thick tail base is the most reliable body-condition signal in the species.",
        "facts": [
            ("Species", "Eublepharis macularius"),
            ("UVB", "Optional · 2–7% shadedweller"),
            ("Basking surface", "32 °C / 90 °F"),
            ("Cool end", "24 °C / 75 °F"),
            ("Photoperiod", "10–12 h, gentle"),
            ("Calcium", "Every feed, D3 1–2× weekly"),
        ],
        "kit": [
            ("uvb-fixture", "A low-output UVB tube plus fixture — the setup that makes supplementation simple rather than guesswork.", "What UVB actually does"),
            ("heat-mat", "Belly heat is still the primary requirement. The thermostat is what makes it safe.", "Belly heat"),
            ("ir-thermometer", "Surface temperature at the hot spot, measured rather than assumed."),
            ("calcium-d3", "UVB and dietary D3 are one decision. Get the lamp right, then dust accordingly.", "supplementation"),
        ],
        "tags": ["leopard gecko", "UVB", "lighting", "Eublepharis macularius"],
        "body_html": """
<p>Ask ten keepers whether leopard geckos need UVB and you will get two confident, opposite answers. Both camps are arguing from the same wrong premise: that this is a nocturnal animal living in total darkness.</p>

<p>Leopard geckos are <strong>crepuscular</strong>. They are active at dawn and dusk, they bask briefly at burrow mouths, and field data shows them exposed to low-level sunlight. That reframes the question: not "UVB or no UVB", but "how much, and what changes if I provide it".</p>

<h2>What UVB actually does for this species</h2>

<p>UVB drives endogenous vitamin D3 synthesis, which is what allows calcium to be absorbed. Without it, you must supply D3 in powder form — and that works, but it is a narrow window. Too little causes metabolic bone disease; too much is toxic to the kidneys.</p>

<p>Providing a low-level UVB zone gives the animal a choice, and lets you reduce dietary D3. That is the entire argument in favour, and it is a good one.</p>

<h2>The practical setup</h2>

<ul>
  <li><strong>Use a low-output tube</strong> — 2–7% UVB (a "shadedweller" type), not a desert-strength bulb. This is a crepuscular animal from scrubland, not a bearded dragon.</li>
  <li><strong>Mount it at one end</strong>, so the gecko can leave the UV zone entirely. Choice is the point.</li>
  <li><strong>Provide shade and cover</strong> — cork flats and a plant. An exposed UV zone is not used.</li>
  <li><strong>10–12 hour photoperiod</strong>, on a timer. No coloured night bulbs; they disturb the animal.</li>
  <li><strong>Replace the tube every 9–12 months</strong>, even if it still lights. UV output decays long before visible light does.</li>
</ul>

<blockquote>UVB is not a substitute for belly heat. A gecko with perfect lighting and a 27 °C floor will still stop digesting.</blockquote>

<h2>Belly heat is still the main event</h2>

<p>Leopard geckos absorb heat ventrally, from warm rock. A heat mat or deep heat projector under one third of the floor, on a dimming thermostat, giving a 32 °C surface and a 24 °C cool end, is the foundation. UVB sits on top of that, never instead of it.</p>

<p>Measure the surface with an infrared gun. Human hands read 32 °C as "pleasantly warm" and tell you nothing.</p>

<h2>How supplementation changes</h2>

<p><strong>With UVB:</strong> dust with plain calcium at every feed, and use a D3 supplement rarely — once or twice a month at most, or not at all depending on the bulb and the animal's exposure.</p>

<p><strong>Without UVB:</strong> calcium with D3 once or twice a week, plain calcium at every other feed. This is a well-established, safe protocol — it simply requires more discipline.</p>

<p>Never do both at full dose. Over-supplementation looks a lot like the MBD you were trying to prevent, and it is harder to diagnose.</p>

<h2>Signs something is wrong</h2>

<p>Rubbery jaw, difficulty lifting the body off the floor, tremors in the toes, a curved spine, or repeated shedding problems. Any of these means a vet visit with a blood panel — husbandry changes alone will not reverse advanced metabolic bone disease.</p>

<h2>Frequently asked questions</h2>

<h3>Can I use a UVB bulb instead of a heat mat?</h3>
<p>No. A bulb warms the air and the back, not the belly, and it dries the enclosure. Use both: heat for digestion, UVB for calcium metabolism.</p>

<h3>Is a coloured night bulb acceptable?</h3>
<p>No. Leopard geckos see colour and are active at dusk; red and blue bulbs disrupt their cycle. Use a ceramic heater or a heat mat if you need night warmth.</p>

<h3>My gecko never sits under the UVB. Is it wasted?</h3>
<p>It is still providing a gradient and a light cycle, and many geckos use it briefly at dawn. If the animal avoids the zone entirely, check the output — a bulb that is too strong will be avoided.</p>
""",
    },

    "pet-006": {
        "title": "Humidity and Salt Water Pools for Land Hermit Crabs",
        "dek": "Hermit crabs do not drown in water — they drown in air that is too dry. The two-pool system, the substrate depth, and the gauge that decides whether they survive a moult.",
        "category": "Troubleshooting",
        "group": "Crustaceans",
        "is_pinned": False,
        "species": "Land Hermit Crab",
        "sci": "Coenobita clypeatus",
        "author": "idris",
        "date": "2026-09-21",
        "image": "hermit-crab.jpg",
        "alt": "Land hermit crab (Coenobita clypeatus) with reddish-orange legs climbing weathered driftwood beside its spiral shell.",
        "caption": "Coenobita clypeatus. The shell is not decoration — it holds the water reserve the crab carries between pools.",
        "facts": [
            ("Species", "Coenobita clypeatus"),
            ("Humidity", "70–80% RH"),
            ("Temperature", "24–28 °C / 75–82 °F"),
            ("Substrate", "15 cm+, sand + coir, damp"),
            ("Water", "Two pools: fresh + salt 1.023 SG"),
            ("Pool depth", "Deep enough to submerge"),
        ],
        "kit": [
            ("salt-set", "Marine salt mix plus a hydrometer — the only way to know your salt pool is actually at 1.023 SG.", "Two pools"),
            ("hygrometer", "Humidity at substrate level and at the top of the tank are different numbers.", "Why humidity"),
            ("coco-fibre", "Mixes with sand to hold a moulting burrow without collapsing.", "Substrate: deep enough"),
        ],
        "tags": ["hermit crab", "humidity", "salt water", "Coenobita clypeatus"],
        "body_html": """
<p>Land hermit crabs are sold in wire cages with a sponge and a shallow dish, which is roughly like keeping a cat in a shoebox with a saucer of milk. They are not desert animals. They are tropical coastal animals that live in humid air, drink fresh water, and require marine water to regulate their salt balance.</p>

<p>Get the air and the water wrong and the animal does not die immediately. It slowly fails to moult, loses limbs, and dies weeks later in a way that looks like bad luck.</p>

<h2>Why humidity is the whole ballgame</h2>

<p>Hermit crabs breathe through modified gills that must stay moist. In air below roughly 70% relative humidity, those gills dry and the animal suffocates slowly. This is why "misting occasionally" is not a strategy — you need a sealed, humid microclimate that holds its number overnight.</p>

<p>Target 70–80% RH, measured at substrate level with a digital gauge, not a dial stuck to the glass. Cover most of the lid with glass or foil to hold humidity, and leave a gap for airflow. A tank that fogs completely and smells stagnant needs more ventilation, not less misting.</p>

<h2>Two pools, not one</h2>

<p>This is the part that gets skipped. Land hermit crabs need <strong>both</strong> fresh water and marine salt water, in separate pools deep enough to fully submerge the shell.</p>

<ul>
  <li><strong>Fresh pool:</strong> dechlorinated water. Tap water must be treated; chlorine and chloramine both harm them.</li>
  <li><strong>Salt pool:</strong> marine salt mixed to 1.023 specific gravity, measured with a hydrometer. Aquarium "tonic" salt is not the same thing and does not work.</li>
  <li><strong>Depth:</strong> deep enough that the crab can submerge completely, with an easy exit — a ramp of mesh, driftwood, or stacked stones.</li>
  <li><strong>Change:</strong> fresh daily, salt every two to three days.</li>
</ul>

<p>A crab that cannot submerge cannot replenish the water held in its shell, and a crab that cannot climb out will drown. Both are design failures, not accidents.</p>

<blockquote>A hermit crab carries its own water supply in its shell. Your job is to make sure it can refill it, in both salinities.</blockquote>

<h2>Substrate: deep enough to bury a crab</h2>

<p>Fifteen centimetres minimum, and more for large specimens. A 5:1 mix of play sand and coco fibre, damp enough to hold a tunnel when you push a finger into it — that is the consistency that lets a crab dig a moulting chamber that does not collapse.</p>

<p>Moulting is when crabs die in captivity. They bury for weeks, shed their exoskeleton, and harden. Disturbing them mid-moult, or keeping them in shallow dry substrate where they cannot bury at all, is the most common cause of "it just died for no reason".</p>

<h2>Temperature and the gradient</h2>

<p>24–28 °C, with a warm end and a cooler end. An under-tank heater on a thermostat at one end, never a heat lamp blasting the whole tank. Above 30 °C and below 22 °C both suppress activity and feeding.</p>

<h2>What good looks like</h2>

<table>
  <tr><th>Parameter</th><th>Target</th><th>How to measure</th></tr>
  <tr><td>Humidity</td><td>70–80% RH</td><td>Digital gauge at substrate level</td></tr>
  <tr><td>Temperature</td><td>24–28 °C</td><td>Thermometer at both ends</td></tr>
  <tr><td>Substrate</td><td>15 cm+, sand/coir</td><td>Holds a tunnel when pressed</td></tr>
  <tr><td>Fresh water</td><td>Dechlorinated</td><td>Changed daily</td></tr>
  <tr><td>Salt water</td><td>1.023 SG</td><td>Hydrometer, every mix</td></tr>
  <tr><td>Shells</td><td>3–5 spares per crab</td><td>Slightly larger than current</td></tr>
</table>

<h2>Frequently asked questions</h2>

<h3>Can I use table salt for the salt pool?</h3>
<p>No. Table salt is sodium chloride with anti-caking agents; marine salt contains the full mineral profile the crab needs. Use a proper marine mix and measure it with a hydrometer.</p>

<h3>My crab is buried and has not moved in two weeks. Is it dead?</h3>
<p>Probably moulting. Do not dig it up. Keep humidity stable, keep the water fresh, and wait. Disturbing a moulting crab can kill it.</p>

<h3>Do I need a lid?</h3>
<p>Yes, with partial coverage. An open tank cannot hold 70–80% humidity; a sealed one goes stagnant. Cover most of the top and leave a vent gap.</p>
""",
    },
}

AUTHORS = {
    "mara": {
        "name": "Mara Ellison",
        "role": "Editor · Invertebrates",
        "bio": "Keeps seventeen species of arachnid and has strong opinions about all of them.",
    },
    "idris": {
        "name": "Dr. Idris Kwan",
        "role": "Veterinary contributor",
        "bio": "Exotics-focused veterinarian writing on the husbandry failures that end up in the clinic.",
    },
    "nell": {
        "name": "Nell Farraday",
        "role": "Senior keeper · Reptiles",
        "bio": "Fifteen years of geckos, pythons, and one extremely stubborn rescue.",
    },
}
