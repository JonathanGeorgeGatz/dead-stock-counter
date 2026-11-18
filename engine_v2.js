// The Dead Stock Counter — SECOND BUILD (after prompt 2), kept verbatim for the episode.
// Prompt 2 fixed the frame: value stock at COST, include every inventory SKU (never-sold
// included), measure pace in a 90-day window, class DEAD / SLOW / HEALTHY. What the
// independent checker later caught, still in here exactly as built:
//   * recency is taken from ANY sales row — a RETURN refreshes a SKU's last-sale date, so
//     dead stock with one recent return reads alive;
//   * velocity counts only the positive rows — returns never subtract, so months of cover
//     comes out short and a slow mover can grade HEALTHY;
//   * sales rows whose SKU is not in the inventory file are still silently dropped — no
//     count anywhere admits they existed.
(function (root) {
  "use strict";
  function rows(text) { return text.split(/\r?\n/).filter(l => l.trim()).map(l => l.split(",")); }
  function num(s) { const v = parseFloat(String(s || "").replace(/[$,]/g, "")); return isNaN(v) ? null : v; }

  function count(invCsv, salesCsv, deadDays, slowMonths) {
    deadDays = deadDays || 90; slowMonths = slowMonths || 6;
    const inv = rows(invCsv), sal = rows(salesCsv);
    const ih = inv[0].map(s => s.trim().toLowerCase());
    const sh = sal[0].map(s => s.trim().toLowerCase());
    const ii = n => ih.indexOf(n), si = n => sh.indexOf(n);
    const stock = [];
    const bySku = {};
    for (let r = 1; r < inv.length; r++) {
      const row = inv[r];
      const sku = (row[ii("sku")] || "").trim();
      const oh = num(row[ii("on hand")]), cost = num(row[ii("unit cost")]);
      if (!sku || oh === null || cost === null) continue;
      if (bySku[sku]) continue;
      const rec = { sku, item: (row[ii("item")] || "").trim(), onHand: oh, cost,
        last: null, sold90: 0 };
      stock.push(rec); bySku[sku] = rec;
    }
    const DAY = 86400000;
    let maxT = null;
    const parsed = [];
    for (let r = 1; r < sal.length; r++) {
      const row = sal[r];
      const t = Date.parse(row[si("date")]);
      const sku = (row[si("sku")] || "").trim();
      const qty = num(row[si("qty")]);
      if (isNaN(t) || qty === null || !bySku[sku]) continue;     // unknowns still vanish
      parsed.push([t, sku, qty]);
      if (maxT === null || t > maxT) maxT = t;
    }
    for (const [t, sku, qty] of parsed) {
      const s = bySku[sku];
      if (s.last === null || t > s.last) s.last = t;             // a RETURN refreshes recency
      if (maxT - t < 90 * DAY && qty > 0) s.sold90 += qty;       // returns never subtract
    }
    const report = { dead: [], slow: [], healthy: [], out: [],
      deadCash: 0, slowCash: 0, totalCash: 0 };
    for (const s of stock) {
      const cash = +(s.onHand * s.cost).toFixed(2);
      report.totalCash = +(report.totalCash + cash).toFixed(2);
      const daysSince = s.last === null ? null : Math.round((maxT - s.last) / DAY);
      const cover = s.sold90 > 0 ? Math.round(s.onHand * 90 / s.sold90) : null;
      const rec = { sku: s.sku, item: s.item, onHand: s.onHand, cash, daysSince, cover };
      if (s.onHand === 0) report.out.push(rec);
      else if (daysSince === null || daysSince >= deadDays) {
        report.dead.push(rec); report.deadCash = +(report.deadCash + cash).toFixed(2);
      } else if (cover === null || cover >= slowMonths * 30) {
        report.slow.push(rec); report.slowCash = +(report.slowCash + cash).toFixed(2);
      } else report.healthy.push(rec);
    }
    report.dead.sort((a, b) => b.cash - a.cash);
    report.deadPct = +(report.deadCash / report.totalCash * 100).toFixed(1);
    return report;
  }
  root.DS_V2 = { count };
})(typeof window !== "undefined" ? window : (typeof module !== "undefined" ? module.exports : this));
