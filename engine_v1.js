// The Dead Stock Counter — FIRST BUILD (prompt 1), kept verbatim for the episode.
// Its sins, exactly as the naive build made them:
//   * it is keyed off the SALES file — a SKU that never sold NEVER APPEARS anywhere
//     (the deadest stock on the shelf is invisible to a dead-stock report);
//   * "dead" is hard-coded at 30 days of quiet;
//   * "cash tied up" is counted at RETAIL price, not cost — the scary number is inflated;
//   * velocity is a lifetime average over the whole file's date span, so a SKU that sold
//     hard in spring still looks alive in November;
//   * a return is just a sale with Math.abs() around it — returns INCREASE "demand";
//   * sales rows whose SKU is missing from the inventory file are silently skipped;
//   * floats and toFixed everywhere.
(function (root) {
  "use strict";
  function rows(text) { return text.split(/\r?\n/).filter(l => l.trim()).map(l => l.split(",")); }
  function num(s) { const v = parseFloat(String(s || "").replace(/[$,]/g, "")); return isNaN(v) ? null : v; }

  function count(invCsv, salesCsv) {
    const inv = rows(invCsv), sal = rows(salesCsv);
    const ih = inv[0].map(s => s.trim().toLowerCase());
    const sh = sal[0].map(s => s.trim().toLowerCase());
    const ii = n => ih.indexOf(n), si = n => sh.indexOf(n);
    const stock = {};
    for (let r = 1; r < inv.length; r++) {
      const row = inv[r];
      const sku = (row[ii("sku")] || "").trim();
      const oh = num(row[ii("on hand")]), price = num(row[ii("unit price")]);
      if (!sku || oh === null || price === null) continue;       // silently skipped
      stock[sku] = { item: (row[ii("item")] || "").trim(), onHand: oh, price };
    }
    const seen = {};
    let minT = null, maxT = null;
    for (let r = 1; r < sal.length; r++) {
      const row = sal[r];
      const t = Date.parse(row[si("date")]);
      const sku = (row[si("sku")] || "").trim();
      const qty = num(row[si("qty")]);
      if (isNaN(t) || qty === null) continue;                    // silently skipped
      if (!stock[sku]) continue;                                 // unknown SKU: silently skipped
      if (minT === null || t < minT) minT = t;
      if (maxT === null || t > maxT) maxT = t;
      const s = seen[sku] || (seen[sku] = { units: 0, last: 0 });
      s.units += Math.abs(qty);                                  // a return counts as demand
      if (t > s.last) s.last = t;
    }
    const spanDays = (maxT - minT) / 86400000 || 1;
    const DAY = 86400000;
    const report = { dead: [], fine: [], deadValue: 0, totalValue: 0 };
    for (const sku in seen) {
      const st = stock[sku];
      const daysSince = Math.round((maxT - seen[sku].last) / DAY);
      const perDay = seen[sku].units / spanDays;
      const value = +(st.onHand * st.price).toFixed(2);          // "cash" at retail
      report.totalValue = +(report.totalValue + value).toFixed(2);
      const rec = { sku, item: st.item, onHand: st.onHand, daysSince,
        perDay: +perDay.toFixed(3), value };
      if (daysSince > 30) { report.dead.push(rec); report.deadValue = +(report.deadValue + value).toFixed(2); }
      else report.fine.push(rec);
    }
    report.dead.sort((a, b) => b.value - a.value);
    report.deadPct = +(report.deadValue / report.totalValue * 100).toFixed(1);
    return report;
  }
  root.DS_V1 = { count };
})(typeof window !== "undefined" ? window : (typeof module !== "undefined" ? module.exports : this));
