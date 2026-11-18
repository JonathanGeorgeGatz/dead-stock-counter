#!/usr/bin/env python3
"""Independent second implementation of the Dead Stock Counter's rules (shares no code with the
tool). Reads inventory.csv + sales.csv, prints a JSON report in the same shape as engine.js's
count(). All money in integer cents; dates as integer serial days (civil-from-days); divisions
via half-up integer arithmetic."""
import csv, io, json, re, sys

DEF = {"dead_days": 90, "slow_months": 6, "carry_tenths": 250, "md_tenths": 300}
MONEY = re.compile(r"^\s*\$?\s*([0-9][0-9,]*)(?:\.([0-9]{1,2}))?\s*$")
INT = re.compile(r"^\s*(-?)([0-9][0-9,]*)\s*$")
ISO = re.compile(r"^\s*(\d{4})-(\d{2})-(\d{2})\s*$")
SLASH = re.compile(r"^\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*$")


def half_up_div(a, b):
    return (2 * a + b) // (2 * b)


def pct_tenths(part, whole):
    return half_up_div(part * 1000, whole) if whole else 0


def cents(s):
    m = MONEY.match(s or "")
    if not m:
        return None
    frac = m.group(2) or ""
    f = int(frac) * 10 if len(frac) == 1 else (int(frac) if frac else 0)
    return int(m.group(1).replace(",", "")) * 100 + f


def whole_units(s):
    m = INT.match(s or "")
    if not m:
        return None
    v = int(m.group(2).replace(",", ""))
    return -v if m.group(1) == "-" else v


def leap(y):
    return (y % 4 == 0 and y % 100 != 0) or y % 400 == 0


MLEN = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def days_from_civil(y, m, d):
    y -= m <= 2
    era = (y if y >= 0 else y - 399) // 400
    yoe = y - era * 400
    doy = (153 * (m + (-3 if m > 2 else 9)) + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


def civil_from_days(z):
    z += 719468
    era = (z if z >= 0 else z - 146096) // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    y = yoe + era * 400
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + (3 if mp < 10 else -9)
    return y + (m <= 2), m, d


def parse_day(s):
    m = ISO.match(s or "")
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m2 = SLASH.match(s or "")
        if not m2:
            return None
        mo, d, y = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
    if mo < 1 or mo > 12:
        return None
    lim = 29 if (mo == 2 and leap(y)) else MLEN[mo - 1]
    if d < 1 or d > lim:
        return None
    return days_from_civil(y, mo, d)


def day_text(z):
    y, m, d = civil_from_days(z)
    return "%04d-%02d-%02d" % (y, m, d)


def rows_of(text):
    return [r for r in csv.reader(io.StringIO(text)) if len(r) > 1 or (r and r[0].strip())]


def count(inv_csv, sales_csv, settings=None):
    S = dict(DEF)
    S.update(settings or {})
    ir = rows_of(inv_csv)
    sr = rows_of(sales_csv)
    if not ir or not sr:
        raise ValueError("Paste both files (or load the sample shop).")
    ih = [c.strip().lower() for c in ir[0]]
    sh = [c.strip().lower() for c in sr[0]]
    for n in ("sku", "item", "category", "on hand", "unit cost", "unit price"):
        if n not in ih:
            raise ValueError("The inventory file is missing a “" + n + "” column.")
    for n in ("date", "sku", "qty"):
        if n not in sh:
            raise ValueError("The sales file is missing a “" + n + "” column.")
    ii = {n: ih.index(n) for n in ih}
    si = {n: sh.index(n) for n in sh}

    refused_inv, refused_sales = [], []
    kept = {}
    kept_order = []
    inv_rows = 0
    for ln, row in enumerate(ir[1:], start=2):
        inv_rows += 1
        g = lambda n: (row[ii[n]] if ii[n] < len(row) else "").strip()
        sku = g("sku")
        if not sku:
            refused_inv.append({"line": ln, "sku": "(blank)", "reason": "no SKU"}); continue
        if sku in kept:
            refused_inv.append({"line": ln, "sku": sku, "reason": "duplicate SKU — the first row was kept"}); continue
        oh = whole_units(g("on hand"))
        uc = cents(g("unit cost"))
        up = cents(g("unit price"))
        if oh is None or oh < 0:
            refused_inv.append({"line": ln, "sku": sku, "reason": "on-hand unreadable: “" + g("on hand") + "”"}); continue
        if uc is None or uc < 1:
            refused_inv.append({"line": ln, "sku": sku, "reason": "no usable unit cost: “" + g("unit cost") + "”"}); continue
        if up is None or up < 1:
            refused_inv.append({"line": ln, "sku": sku, "reason": "unit price unreadable: “" + g("unit price") + "”"}); continue
        kept[sku] = {"sku": sku, "item": g("item"), "category": g("category"),
                     "onHand": oh, "unitCost": uc, "unitPrice": up}
        kept_order.append(sku)

    used = []     # (day, sku, qty) in file order
    sales_rows = 0
    for ln, row in enumerate(sr[1:], start=2):
        sales_rows += 1
        g = lambda n: (row[si[n]] if si[n] < len(row) else "").strip()
        day = parse_day(g("date"))
        sku = g("sku")
        qty = whole_units(g("qty"))
        if day is None:
            refused_sales.append({"line": ln, "sku": sku or "(blank)", "reason": "unreadable date: “" + g("date") + "”"}); continue
        if sku not in kept:
            refused_sales.append({"line": ln, "sku": sku or "(blank)", "reason": "SKU not in the inventory file"}); continue
        if qty is None or qty == 0:
            refused_sales.append({"line": ln, "sku": sku, "reason": "quantity unreadable or zero: “" + g("qty") + "”"}); continue
        used.append((day, sku, qty))

    if not used:
        raise ValueError("No readable sales rows.")
    as_of = max(u[0] for u in used)

    last_sale = {}
    win = {}
    for day, sku, qty in used:
        if qty > 0 and (sku not in last_sale or day > last_sale[sku]):
            last_sale[sku] = day
        if as_of - 90 < day <= as_of:
            win[sku] = win.get(sku, 0) + qty
    # shadow route: reverse order
    win2 = {}
    for day, sku, qty in reversed(used):
        if as_of - 90 < day <= as_of:
            win2[sku] = win2.get(sku, 0) + qty
    shadow_ok = all(win.get(k, 0) == win2.get(k, 0) for k in set(win) | set(win2))

    limit = S["slow_months"] * 30
    skus = []
    for sku in kept_order:
        L = kept[sku]
        u90 = max(0, win.get(sku, 0))
        ls = last_sale.get(sku)
        days_since = None if ls is None else as_of - ls
        cover = half_up_div(L["onHand"] * 90, u90) if u90 > 0 else None
        cash = L["onHand"] * L["unitCost"]
        retail = L["onHand"] * L["unitPrice"]
        if L["onHand"] == 0:
            cls = "OUT"
        elif ls is None or days_since >= S["dead_days"]:
            cls = "DEAD"
        elif cover is None or cover >= limit:
            cls = "SLOW"
        else:
            cls = "HEALTHY"
        skus.append({"sku": sku, "item": L["item"], "category": L["category"],
                     "onHand": L["onHand"], "unitCost": L["unitCost"], "unitPrice": L["unitPrice"],
                     "cash": cash, "retail": retail,
                     "lastSaleText": None if ls is None else day_text(ls),
                     "daysSince": days_since, "units90": u90, "coverDays": cover, "class": cls})

    korder = {"DEAD": 0, "SLOW": 1, "HEALTHY": 2, "OUT": 3}

    def key(l):
        if l["class"] == "DEAD":
            return (0, -l["cash"], l["sku"])
        if l["class"] == "SLOW":
            inf = l["coverDays"] is None
            return (1, 0 if inf else 1, 0 if inf else -l["coverDays"], l["sku"])
        return (korder[l["class"]], l["sku"])

    skus.sort(key=key)
    by = lambda c: [l for l in skus if l["class"] == c]
    dead, slow, healthy, out = by("DEAD"), by("SLOW"), by("HEALTHY"), by("OUT")
    total_cash = sum(kept[s]["onHand"] * kept[s]["unitCost"] for s in kept_order)
    dead_cash = sum(l["cash"] for l in dead)
    slow_cash = sum(l["cash"] for l in slow)
    healthy_cash = sum(l["cash"] for l in healthy)
    out_cash = sum(l["cash"] for l in out)
    dead_retail = sum(l["retail"] for l in dead)
    recover_now = sum(half_up_div(l["retail"] * (1000 - S["md_tenths"]), 1000) for l in dead)
    carry_monthly = half_up_div((dead_cash + slow_cash) * S["carry_tenths"], 12000)
    carry_dead = half_up_div(dead_cash * S["carry_tenths"], 12000)

    counts = {"invRows": inv_rows, "salesRows": sales_rows, "kept": len(kept_order),
              "used": len(used), "dead": len(dead), "slow": len(slow), "healthy": len(healthy),
              "out": len(out), "neverSold": sum(1 for l in dead if l["lastSaleText"] is None),
              "refusedInv": len(refused_inv), "refusedSales": len(refused_sales),
              "returns": sum(1 for u in used if u[2] < 0)}
    rows_tie = (counts["kept"] + counts["refusedInv"] == inv_rows
                and counts["dead"] + counts["slow"] + counts["healthy"] + counts["out"] == counts["kept"])
    cash_tie = total_cash == dead_cash + slow_cash + healthy_cash + out_cash
    sales_tie = counts["used"] + counts["refusedSales"] == sales_rows
    sh_inv = pct_tenths(counts["refusedInv"], inv_rows)
    sh_sales = pct_tenths(counts["refusedSales"], sales_rows)
    share_ok = sh_inv <= 100 and sh_sales <= 100
    trusted = rows_tie and cash_tie and sales_tie and shadow_ok and share_ok
    banner = ""
    if not trusted:
        banner = "DO NOT TRUST THIS COUNT — " + (
            "the row buckets do not tie." if not rows_tie
            else "the cash self-audit does not tie." if not cash_tie
            else "the sales rows do not tie." if not sales_tie
            else "the velocity shadow pass disagrees." if not shadow_ok
            else "too many rows refused (inventory %s%%, sales %s%%). Fix the exports and run it again."
                 % (fmt_t(sh_inv), fmt_t(sh_sales)))

    cats = {}
    cat_order = []
    for sku in kept_order:
        key_c = kept[sku]["category"].lower()
        if key_c not in cats:
            cats[key_c] = {"category": kept[sku]["category"], "tiedCash": 0, "catCash": 0, "skuCount": 0}
            cat_order.append(key_c)
        cats[key_c]["catCash"] += kept[sku]["onHand"] * kept[sku]["unitCost"]
        cats[key_c]["skuCount"] += 1
    for l in dead + slow:
        cats[l["category"].lower()]["tiedCash"] += l["cash"]
    categories = sorted(cats.values(), key=lambda c: (-c["tiedCash"], c["category"].lower()))

    money = {"totalCash": total_cash, "deadCash": dead_cash, "slowCash": slow_cash,
             "healthyCash": healthy_cash, "outCash": out_cash, "deadRetail": dead_retail,
             "recoverNow": recover_now, "carryMonthly": carry_monthly,
             "carryMonthlyDead": carry_dead, "carrySix": 6 * carry_dead}
    return {
        "settings": S, "asOfDay": as_of, "asOfText": day_text(as_of),
        "counts": counts, "money": money,
        "deadCashPct_tenths": pct_tenths(dead_cash, total_cash),
        "slowCashPct_tenths": pct_tenths(slow_cash, total_cash),
        "tiedPct_tenths": pct_tenths(dead_cash + slow_cash, total_cash),
        "skus": [{k: l[k] for k in ("sku", "item", "category", "onHand", "unitCost", "unitPrice",
                                    "cash", "lastSaleText", "daysSince", "units90", "coverDays", "class")}
                 for l in skus],
        "categories": categories,
        "refusedInv": refused_inv, "refusedSales": refused_sales,
        "recon": {"rowsTie": rows_tie, "cashTie": cash_tie, "salesTie": sales_tie,
                  "shadowOk": shadow_ok, "refusedShareInv_tenths": sh_inv,
                  "refusedShareSales_tenths": sh_sales, "trusted": trusted, "banner": banner},
    }


def fmt_t(t):
    return "%d.%d" % (t // 10, t % 10)


if __name__ == "__main__":
    inv = open(sys.argv[1]).read()
    sal = open(sys.argv[2]).read()
    st = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
    print(json.dumps(count(inv, sal, st), indent=1))
