/**
 * Sample zine content for the web editor.
 * Each sample has a name, markdown content, and optional TOML config.
 */

export const samples = [
  {
    name: "Starter Zine",
    description: "A simple intro to zinewire directives",
    config: `[zine]
page-size = "a4"
`,
    markdown: `/title My Zine

# My Zine

## A zinewire project

/page
/two-columns

## Getting Started

Write your content in **markdown**. Use zinewire directives to control layout:

- \`/page\` --- start a new page
- \`/two-columns\` --- switch to two-column layout
- \`/column\` --- move to the next column
- \`/cover\` --- add a cover page

/column

## Why Zines?

- **No gatekeepers** --- publish what you want
- **Cheap** --- a photocopier and stapler is all you need
- **Personal** --- your voice, your rules
- **Tangible** --- a real thing in a digital world

> *"The best zine is the one that exists."*

/page
/one-column

That's it. Edit the markdown on the left and see your zine on the right.

*Made with zinewire.*
`,
  },
  {
    name: "Booklet: How to Make a Zine",
    description: "Saddle-stitch booklet (A5 reading pages on A4 sheets)",
    config: `[zine]
page-size = "a4-landscape"
booklet = true
`,
    markdown: `/title How to Make a Zine
/cover

# How to Make a Zine

## A pocket guide to self-publishing

/page
/two-columns

## What Is a Zine?

A **zine** (short for magazine or fanzine) is a small, self-published work of writing, art, or a mix of both. Zines are typically photocopied and distributed by hand or by mail.

Unlike blogs or social media posts, zines are *physical objects*. You can hold them, fold them, pass them to a friend. That tactility is the whole point.

/column

## Why Make One?

- **No gatekeepers** --- you publish what you want
- **Cheap** --- a photocopier and a stapler is all you need
- **Personal** --- your voice, your layout, your rules
- **Tangible** --- a real thing in a digital world

> "A zine is a small circulation publication of original or appropriated texts and images, usually reproduced via photocopier."
> **--- Stephen Duncombe**

/page
/two-columns

## The Process

### 1. Pick a topic

Anything you care about. Recipes, poetry, local history, a rant about fonts, a guide to your neighbourhood's best trees.

### 2. Write and layout

Write your content in markdown. Use zinewire to handle columns, pages, and print layout. Focus on content; the tool handles pagination.

/column

### 3. Print

Open the HTML in a browser and print. The booklet imposition gives you imposed A4 sheets --- fold and staple for an A5 booklet.

### 4. Distribute

Leave copies at coffee shops, bookstores, libraries. Trade with other zine-makers. Mail them to friends.

/page
/one-column

/large

| Step | Tool | Time |
|------|------|------|
| Write | Any text editor | 1--2 hours |
| Build | \`zinewire build\` | Seconds |
| Print | Any printer | 5 minutes |
| Staple | Long-reach stapler | 2 minutes |

/normal

/space

*That's it. Four steps from idea to finished zine. No publisher, no approval process, no algorithm. Just you and a stapler.*
`,
  },
  {
    name: "Mini Zine: 8 Things",
    description: "One-sheet fold-and-cut mini zine (8 pages on 1 sheet)",
    config: `[zine]
page-size = "a4-landscape"
mini-zine = true
`,
    markdown: `/title 8 Things I Learned This Week

# 8 Things I Learned This Week

/page

## 1. Crows remember faces

They hold grudges for years. Be nice to crows.

/page

## 2. The Oxford comma saves lives

"I love my parents, Batman and Wonder Woman" vs "I love my parents, Batman, and Wonder Woman."

/page

## 3. Honey never spoils

Archaeologists found 3,000-year-old honey in Egyptian tombs. Still edible.

/page

## 4. Octopuses have three hearts

Two pump blood to the gills. One pumps it to the body. When they swim, the body heart stops --- which is why they prefer crawling.

/page

## 5. The speed of dark

Dark technically "moves" faster than light. When you swing a laser pointer across the moon's surface, the dot can travel faster than *c*.

/page

## 6. A jiffy is real

In physics, a jiffy is the time it takes light to travel one centimetre: about 33.3 picoseconds.

/page

## 7. Bananas are berries

Strawberries aren't. Taxonomy is unhinged.

*Cut along the centre, fold, and you have a tiny zine.*
`,
  },
  {
    name: "Trifold: Event Guide",
    description: "Tri-fold pamphlet (6 panels on 1 sheet)",
    config: `[zine]
page-size = "a4-landscape"
trifold = true

[theme]
color-accent = "#1a7a4c"
`,
    markdown: `/title Zine Fest 2026

# Zine Fest 2026

## March 15 --- Town Hall

*Free entry. Bring zines to trade.*

/page

## Schedule

**11:00** Doors open

**11:30** Welcome & intro

**12:00** Workshop: Risograph printing

**13:00** Lunch break (food trucks outside)

**14:00** Panel: Why print still matters

**15:00** Distro fair opens

**17:00** Closing & zine swap

/page

## Workshops

### Risograph 101

Learn the basics of riso printing. Bring a design on USB or make one on the spot.

*Room B, 12:00--13:00*

### Bookbinding

Hand-stitch your own chapbook. Materials provided.

*Room C, 14:00--15:00*

/page

## Map & Venue

**Town Hall**, 42 High Street

- **Main Hall** --- Distro tables & panels
- **Room B** --- Risograph workshop
- **Room C** --- Bookbinding workshop
- **Courtyard** --- Food trucks & seating

*Wheelchair accessible. Gender-neutral toilets on ground floor.*

/page

## Exhibitors

- Rough Trade Zines
- Ink & Staple Collective
- Night Bus Press
- The Pamphlet Society
- Dead Typewriter Distro
- Foxglove Print Co.
- Stencil Liberation Front

*Table applications closed. Waiting list: zinefest@example.com*

/page

## About

Zine Fest is a volunteer-run, non-profit event celebrating self-publishing, small press, and DIY print culture.

**Contact:** zinefest@example.com

**Social:** @zinefest2026

*This pamphlet was made with zinewire. Fold into thirds for a pocket guide.*
`,
  },
  {
    name: "French Fold: Album Art",
    description: "French fold (4 panels, fold twice)",
    config: `[zine]
page-size = "a4"
french-fold = true

[theme]
font-heading = "Cormorant Garamond"
font-body = "Cormorant Garamond"
color-text = "#1a1a1a"
color-accent = "#8B4513"
`,
    markdown: `/title Postcards from Nowhere

# Postcards from Nowhere

## an album by The Distances

*2026 --- All tracks written and recorded in a shed in Margate.*

/page

## Side A

1. **The Long Way Home** --- 4:12
2. **Salt Air** --- 3:47
3. **Postcards from Nowhere** --- 5:01
4. **The Fog Comes In** --- 3:33
5. **Harbour Light** --- 4:28

## Side B

6. **Low Tide** --- 3:55
7. **Letters I Never Sent** --- 4:44
8. **The Distance Between** --- 6:02
9. **Margate in Winter** --- 3:19
10. **Goodnight, Somewhere** --- 5:17

/page

## Liner Notes

Recorded at Shed Studios, Margate, January--March 2026.

Produced by **Ali Kemp**. Mixed by **Sam Voss** at Electric Garden.

*Thanks to everyone who let us make noise at unreasonable hours. Thanks to the sea for being there.*

**The Distances are:**
Jo Blackwell (vocals, guitar),
Ali Kemp (keys, production),
Dev Osei (bass),
Erin Chow (drums)

/page

## Credits

Cover photograph by **Erin Chow**.

Design and layout by **Jo Blackwell**.

This is a limited edition of 200 copies. If you're reading this, you're one of them.

*thebandthedistances.co.uk*

*Fold along the centre lines. The music is better on vinyl but this insert is better on paper.*
`,
  },
  {
    name: "Micro Mini: Field Notes",
    description: "Micro-mini zine (16 tiny pages on 1 sheet)",
    config: `[zine]
page-size = "a4-landscape"
micro-mini = true

[theme]
font-heading = "Space Mono"
font-body = "Space Mono"
color-accent = "#e06c75"
`,
    markdown: `/title Bug Field Guide

# Bug Field Guide

## Pocket edition

/page

## Ladybird

Spots ≠ age. That's a myth. Spots indicate species.

/page

## Woodlouse

Not an insect. A crustacean. Related to lobsters. Think about that.

/page

## Garden Spider

Eats its web every night and spins a new one. Every. Night.

/page

## Earwig

Those pincers? Mostly for folding wings. They're not interested in your ears.

/page

## Centipede

Never has exactly 100 legs. Always an odd number of pairs. Nature's off-by-one error.

/page

## Slug

Has four noses. Well, tentacles. Two for seeing, two for smelling.

/page

## Ant

Can carry 50× its body weight. You can carry a backpack and complain about it.

/page

## Bee

Dies after stinging you. Thinks about this and stings you anyway. Respect.

/page

## Moth

Navigates by the moon. Streetlights are a catastrophic UI failure.

/page

## Dragonfly

360° vision. Can fly backwards. Existed before dinosaurs. Still unbothered.

/page

## Beetle

One in four animal species on Earth is a beetle. They won evolution.

/page

## Worm

Has five hearts. Cut in half? Only the head end survives. The other half is just wishful thinking.

/page

## Grasshopper

Ears are on its knees. Hears with its legs. Plays music with them too.

/page

## Snail

Has 14,000 teeth. All on its tongue. Imagine flossing.

/page

*Fold, cut, fold again. Now you have a tiny field guide that fits in your pocket.*
`,
  },
  {
    name: "Poetry Chapbook",
    description: "Minimal single-column poems (no imposition)",
    config: `[zine]
page-size = "a4"

[theme]
font-heading = "Cormorant Garamond"
font-body = "Cormorant Garamond"
color-accent = "#8B4513"
`,
    markdown: `/title Small Hours
/cover

# Small Hours

## Poems for the sleepless

/page

## Inventory

The fridge hums its one note.
A tap drips in the dark.
The radiator clicks
like someone counting.

I own: two mugs, one chipped.
A stack of books I'll finish
when I finish being tired.
A coat that smells of rain.

The hours between three and five
belong to no one.
I borrow them
and give them back unmarked.

/page

## Letter to a Stranger on the Night Bus

You fell asleep on the 73
somewhere past Stoke Newington.
Your head against the glass,
your breath a small cloud.

I wanted to tell you:
the stop you want is next.
But you looked so peaceful
I let you ride.

I hope you woke up somewhere good ---
or at least somewhere warm ---
and that the extra distance
felt like a gift, not a mistake.

/page

## Recipe for Insomnia

Take one thought.
Hold it up to the light.
Turn it over. Find the flaw.
Repeat.

Add: a worry you forgot to worry about at noon.
A thing you said in 2014.
The sound your knee makes now.

Fold in darkness.
Let it rise.

Serves one, indefinitely.

/page

## Things I Know at 4am

That the fox in the garden
has a route.

That the streetlight
has a frequency.

That the gap between
one car passing
and the next
is a kind of silence
you can't find in daytime.

That sleep is not the opposite
of waking
but a country with a border
I keep arriving at
without my papers.
`,
  },
  {
    name: "Recipe Zine",
    description: "Two-column recipes with tables (no imposition)",
    config: `[zine]
page-size = "a4"

[theme]
font-heading = "Bitter"
color-accent = "#c0392b"
`,
    markdown: `/title Broke but Hungry
/cover

# Broke but Hungry

## Real food for empty wallets

/page
/two-columns

## The Rules

1. **Nothing over £2 per serving.** If a recipe costs more, it's not in this zine.
2. **No weird ingredients.** If you can't find it at a corner shop, forget it.
3. **Minimal equipment.** One pot, one pan, one knife. Maybe a baking tray.
4. **Feeds at least two.** Cooking for one is inefficient and sad.

/column

## Pantry Staples

Keep these stocked and you can always eat:

- Rice (the big bag, always)
- Pasta (whatever's cheapest)
- Tinned tomatoes
- Onions
- Garlic
- Eggs
- Soy sauce
- Vegetable oil
- Salt, pepper, chilli flakes

> If you have rice and an egg, you have dinner. Everything else is a bonus.

/page
/two-columns

## Egg Fried Rice

The ultimate broke meal. Ten minutes, one pan, infinite variations.

**You need:**

- 2 cups leftover rice (cold, ideally day-old)
- 2 eggs
- 2 tbsp soy sauce
- 1 tbsp oil
- Whatever veg you have (frozen peas, spring onion, carrot)

**Do this:**

1. Heat oil in a large pan, screaming hot
2. Add veg, stir-fry 2 minutes
3. Push veg to the side, crack in eggs
4. Scramble the eggs, then mix with veg
5. Add rice, break up any clumps
6. Pour soy sauce around the edge of the pan (not on the rice)
7. Toss everything together for 2 minutes

/column

**Tips:**

- Cold rice is essential. Hot rice goes mushy.
- The soy sauce hitting the hot pan is where the flavour comes from.
- Add a splash of sesame oil at the end if you're feeling fancy.
- Leftover chicken, ham, or prawns all work.

**Cost:** About 60p per serving.

---

## Garlic Pasta

When you literally have nothing else.

**You need:**

- 200g spaghetti
- 4 cloves garlic, sliced thin
- 3 tbsp olive oil
- Chilli flakes
- Salt

**Do this:**

1. Cook pasta in salted water
2. Meanwhile, gently fry garlic in oil until golden (not brown!)
3. Add chilli flakes, cook 30 seconds
4. Drain pasta, save a cup of water
5. Toss pasta in the garlic oil with a splash of pasta water

**Cost:** About 30p per serving.

/page
/one-column

## Meal Plan (One Week, Two People)

/large

| Day | Meal | Cost |
|-----|------|------|
| Mon | Egg fried rice | £1.20 |
| Tue | One-pot dal + rice | £1.40 |
| Wed | Garlic pasta | £0.60 |
| Thu | Bean chilli + rice | £1.50 |
| Fri | Quesadillas | £1.00 |
| Sat | Potato soup + bread | £1.00 |
| Sun | Dal leftovers + rice | £0.00 |

/normal

/space

**Weekly total: £6.70 for two people.** That's £3.35 each. For a week of actual food.

/space

*The secret to eating well on nothing isn't recipes --- it's planning. Cook once, eat twice. Buy in bulk. Freeze everything. And never, ever shop hungry.*
`,
  },
];
