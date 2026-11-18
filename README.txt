THE DEAD STOCK COUNTER — free giveaway from "Build It With AI" (Episode 33)

Some of the cash in your business is on your shelves, dressed as inventory that stopped
moving. This tool reads your inventory and sales exports and counts it: what's dead, what's
slow, what carrying it costs you each month, and what a markdown would bring back.

WHAT'S IN THIS FOLDER
- Dead_Stock_Counter.html .. the tool. One file. Open it in any browser. No internet, no
                             account, nothing you paste leaves your machine.
- sample/inventory.csv ..... the episode's sample shop (Foxglove Home & Garden — fictional)
- sample/sales.csv ......... twelve months of the sample shop's sales
- PROMPTS.txt .............. the exact three prompts from the episode, word for word
- checker.py ............... the independent second implementation (Python) used to verify
                             the tool — run: python3 checker.py inventory.csv sales.csv
- engine_v1.js ............. the first build, kept verbatim, bugs and all (retail-priced
                             "cash", invisible never-sold stock, lifetime averages)
- engine_v2.js ............. the second build, kept verbatim (returns refresh recency,
                             returns never subtract, vanishing unknown-SKU rows)

HOW TO USE IT ON YOUR OWN SHOP
1. Open Dead_Stock_Counter.html. Click "Load the sample shop" to see it work.
2. Export your inventory as a CSV with columns: SKU, Item, Category, On Hand, Unit Cost,
   Unit Price.
3. Export your sales as a CSV with columns: Date, SKU, Qty. A negative Qty is a return.
   Most POS systems can produce both in a couple of clicks.
4. Paste both, set the four judgments (quiet days that count as dead, months of cover that
   count as slow, your carrying rate, your markdown), and walk the shop with the list.

If your export names its columns differently, hand your file and PROMPTS.txt's first prompt
to an AI assistant and tell it what your software calls things.

HONEST LIMITS
- It counts; it does not forecast. Seasonal stock you are deliberately holding for December
  will show as slow in June — the verdicts are arithmetic, the judgment stays yours.
- It reads sell-through, not shrinkage: stock that vanished without a sales row is a
  different problem (and a different episode).
- The carrying cost is an estimate from the rate YOU set, not a measurement.
- The sample shop is fictional. Any resemblance is coincidence.

Found a bug? Ask the AI to fix it — and make it show you the fix the way the episode does:
prove it on the numbers, not with reassurance.
