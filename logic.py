"""SaaS/API spend analysis — pure Python, no data is stored.

parse_costs(): accepts the CSV shapes people actually have (English or Turkish headers, comma / semicolon /
tab delimiters, "$1,250.00", "1.250,50", "(12.00)" style amounts, most common date formats).
analyze(): turns rows into findings that come from the data itself — month-over-month growth, spikes,
possible double charges, fixed subscriptions and unit-price increases. No invented numbers: savings are only
quoted where they are exact (duplicate charges).
"""
from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import median

MAX_ROWS = 20000
CURRENCIES = {"USD": "$", "EUR": "€", "GBP": "£", "TRY": "₺"}

_TR = str.maketrans("ıİşŞğĞüÜöÖçÇ", "iIsSgGuUoOcC")
ALIASES = {
    "service": ["service", "servicename", "vendor", "vendorname", "product", "productname", "tool", "app",
                "application", "provider", "merchant", "payee", "description", "lineitem", "item", "name",
                "servis", "hizmet", "saglayici", "tedarikci", "urun", "aciklama"],
    "date": ["date", "day", "billingdate", "invoicedate", "chargedate", "transactiondate", "usagedate", "period",
             "billingperiod", "month", "startdate", "created", "createdat", "tarih", "ay", "donem"],
    "cost": ["cost", "amount", "total", "totalcost", "price", "charge", "spend", "unblendedcost", "blendedcost",
             "amountusd", "costusd", "net", "maliyet", "tutar", "ucret", "fiyat", "toplam", "harcama"],
    "usage": ["usage", "usagequantity", "quantity", "qty", "units", "requests", "calls", "tokens", "seats",
              "kullanim", "miktar", "adet"],
}
DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y",
                "%Y-%m", "%Y/%m", "%m/%Y", "%b %Y", "%B %Y", "%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y"]


class ParseError(ValueError):
    pass


def _norm(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", header.translate(_TR).lower())


def _map_columns(headers: list[str]) -> dict[str, int]:
    normed = [_norm(h) for h in headers]
    found: dict[str, int] = {}
    for field, names in ALIASES.items():
        for i, h in enumerate(normed):  # exact match first
            if h in names and i not in found.values():
                found[field] = i
                break
        else:
            for i, h in enumerate(normed):  # then "cost (usd)", "service_name_x" …
                if i not in found.values() and h and any(h.startswith(n) or h.endswith(n) for n in names if len(n) > 3):
                    found[field] = i
                    break
    return found


def _sniff(text: str) -> str:
    head = "\n".join(text.splitlines()[:10])
    try:
        return csv.Sniffer().sniff(head, delimiters=",;\t|").delimiter
    except csv.Error:
        counts = {d: head.count(d) for d in (",", ";", "\t", "|")}
        return max(counts, key=counts.get)


def parse_amount(raw: str, european: bool) -> float | None:
    s = (raw or "").strip()
    if not s:
        return None
    negative = s.startswith("(") and s.endswith(")") or s.startswith("-")
    s = re.sub(r"[^\d.,]", "", s)
    if not s or not re.search(r"\d", s):
        return None
    if "," in s and "." in s:
        decimal = "," if s.rfind(",") > s.rfind(".") else "."
    elif "," in s:
        decimal = "" if re.fullmatch(r"\d{1,3}(,\d{3})+", s) and not european else ","
    elif "." in s:
        decimal = "" if re.fullmatch(r"\d{1,3}(\.\d{3})+", s) and european else "."
    else:
        decimal = "."
    thousands = {",": ".", ".": ",", "": ",."}[decimal]
    for ch in thousands:
        s = s.replace(ch, "")
    if decimal == ",":
        s = s.replace(",", ".")
    try:
        value = float(s)
    except ValueError:
        return None
    return -value if negative else value


def _pick_date_format(values: list[str]) -> str | None:
    clean = [v.strip().split("T")[0].split(" ")[0] if re.match(r"\d{4}-\d{2}-\d{2}[T ]", v.strip()) else v.strip()
             for v in values if v and v.strip()]
    if not clean:
        return None
    for fmt in DATE_FORMATS:
        try:
            for v in clean:
                datetime.strptime(v, fmt)
            return fmt
        except ValueError:
            continue
    return None


def _parse_date(raw: str, fmt: str) -> date | None:
    v = (raw or "").strip()
    if re.match(r"\d{4}-\d{2}-\d{2}[T ]", v):
        v = v.split("T")[0].split(" ")[0]
    try:
        return datetime.strptime(v, fmt).date()
    except ValueError:
        return None


def _looks_binary(text: str) -> bool:
    """Resim, zip, PDF gibi metin olmayan dosyalar: NUL ya da çok sayıda kontrol karakteri içerir."""
    sample = text[:20000]
    if "\x00" in sample:
        return True
    ctrl = sum(1 for ch in sample if ord(ch) < 32 and ch not in "\r\n\t")
    return bool(sample) and ctrl / len(sample) > 0.02


def _read_table(text: str, delim: str) -> list[list[str]]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")  # eski Mac satır sonları
    try:
        return [r for r in csv.reader(io.StringIO(text), delimiter=delim) if any(c.strip() for c in r)]
    except csv.Error as e:
        raise ParseError(f"This file couldn't be read as a CSV ({e}). Please export it again as CSV.") from e


def parse_costs(text: str) -> tuple[list[dict], list[str]]:
    """Returns (rows, warnings). Raises ParseError with a message the user can act on."""
    text = (text or "").lstrip("﻿").strip()
    if not text:
        raise ParseError("No data received. Paste a CSV or upload a file.")
    if _looks_binary(text):
        raise ParseError("This doesn't look like a CSV or text file (it may be an image, PDF or spreadsheet). "
                         "Please export your costs as CSV and upload that.")
    delim = _sniff(text)
    table = _read_table(text, delim)
    if len(table) < 2:
        raise ParseError("The data needs a header row and at least one line of costs.")
    headers, body = table[0], table[1:MAX_ROWS + 1]
    cols = _map_columns(headers)
    missing = [f for f in ("service", "cost") if f not in cols]
    if missing:
        raise ParseError(
            f"Couldn't find a {' or '.join(missing)} column. Columns found: {', '.join(h.strip() for h in headers)}. "
            "Name them e.g. Service / Vendor and Cost / Amount (Date and Usage are optional).")
    european = delim == ";"
    date_fmt = _pick_date_format([r[cols["date"]] for r in body if len(r) > cols["date"]]) if "date" in cols else None
    rows, skipped = [], []
    for n, r in enumerate(body, start=2):
        get = lambda f: r[cols[f]] if f in cols and cols[f] < len(r) else ""
        service = get("service").strip()
        cost = parse_amount(get("cost"), european)
        if not service or cost is None:
            skipped.append(n)
            continue
        rows.append({"service": service[:80], "cost": cost,
                     "usage": parse_amount(get("usage"), european) if "usage" in cols else None,
                     "date": _parse_date(get("date"), date_fmt) if date_fmt else None})
    if not rows:
        raise ParseError("No line had both a service name and a readable amount.")
    warnings = []
    if skipped:
        shown = ", ".join(map(str, skipped[:8])) + (" …" if len(skipped) > 8 else "")
        warnings.append(f"{len(skipped)} {'line' if len(skipped) == 1 else 'lines'} skipped because the service or "
                        f"amount was empty/unreadable ({'line' if len(skipped) == 1 else 'lines'} {shown}).")
    if "date" in cols and not date_fmt:
        warnings.append("The date column couldn't be read in a single format, so month-over-month trends are off.")
    elif "date" not in cols:
        warnings.append("No date column found, so month-over-month trends are off.")
    if len(table) - 1 > MAX_ROWS:
        warnings.append(f"Only the first {MAX_ROWS:,} lines were analyzed.")
    return rows, warnings


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #
def _month(d: date) -> str:
    return d.strftime("%Y-%m")


def analyze(rows: list[dict]) -> dict:
    total = sum(r["cost"] for r in rows)
    by_service: dict[str, float] = defaultdict(float)
    for r in rows:
        by_service[r["service"]] += r["cost"]
    services = sorted(by_service.items(), key=lambda kv: kv[1], reverse=True)
    top = max((v for _, v in services), default=0) or 1
    service_table = [{"service": s, "cost": c, "share": (c / total * 100) if total else 0, "bar": max(c, 0) / top * 100}
                     for s, c in services]

    dated = [r for r in rows if r["date"]]
    months = sorted({_month(r["date"]) for r in dated})
    monthly: dict[str, float] = defaultdict(float)
    svc_month: dict[tuple[str, str], float] = defaultdict(float)
    for r in dated:
        monthly[_month(r["date"])] += r["cost"]
        svc_month[(r["service"], _month(r["date"]))] += r["cost"]
    mtop = max(monthly.values(), default=0) or 1
    month_table = [{"month": m, "cost": monthly[m], "bar": max(monthly[m], 0) / mtop * 100} for m in months]

    findings: list[dict] = []

    # 1) Possible double charges: same service, same day, same amount, more than once
    dup = defaultdict(list)
    for r in dated:
        dup[(r["service"], r["date"], round(r["cost"], 2))].append(r)
    for (svc, d, amount), group in dup.items():
        if len(group) > 1 and amount > 0:
            extra = amount * (len(group) - 1)
            findings.append({"level": "high", "title": f"Possible double charge: {svc}", "service": svc,
                             "detail": f"{len(group)} identical charges of {{cur}}{amount:,.2f} on {d.isoformat()}.",
                             "action": "Check the invoice; if it's a duplicate, ask the vendor for a refund.",
                             "saving": extra})

    # 3) Spikes: a single charge far above that service's usual charge
    per_service = defaultdict(list)
    for r in rows:
        per_service[r["service"]].append(r)
    for svc, items in per_service.items():
        costs = [i["cost"] for i in items if i["cost"] > 0]
        if len(costs) < 4:
            continue
        med = median(costs)
        for i in items:
            if med > 0 and i["cost"] > 2.5 * med and i["cost"] - med >= max(0.005 * total, 1):
                when = f" on {i['date'].isoformat()}" if i["date"] else ""
                findings.append({"level": "medium", "title": f"Spike in {svc}", "service": svc,
                                 "detail": f"{{cur}}{i['cost']:,.2f}{when}, about {i['cost'] / med:.1f}× its usual "
                                           f"{{cur}}{med:,.2f}.",
                                 "action": "Look at usage logs for that day; add rate limits or caching if it was unintended.",
                                 "saving": None})

    # 2) Month-over-month growth per service (last two months)
    explained = {f["service"] for f in findings if f.get("service")}
    if len(months) >= 2:
        prev_m, last_m = months[-2], months[-1]
        for svc, _ in services:
            prev, last = svc_month.get((svc, prev_m), 0), svc_month.get((svc, last_m), 0)
            if svc in explained:  # artışı zaten çift ödeme ya da tek bir sıçrama açıklıyor
                continue
            if prev > 0 and last > prev * 1.25 and (last - prev) >= max(0.01 * total, 1):
                findings.append({"level": "medium", "title": f"{svc} is growing fast",
                                 "detail": f"{{cur}}{prev:,.2f} in {prev_m} → {{cur}}{last:,.2f} in {last_m} "
                                           f"(+{(last / prev - 1) * 100:.0f}%).",
                                 "action": "Find what changed (new feature, traffic, a retry loop) and set a budget alert.",
                                 "saving": None})

    # 4) Unit price increases (needs usage)
    if len(months) >= 2:
        for svc, items in per_service.items():
            by_m = defaultdict(lambda: [0.0, 0.0])
            for i in items:
                if i["date"] and i["usage"] and i["usage"] > 0:
                    by_m[_month(i["date"])][0] += i["cost"]
                    by_m[_month(i["date"])][1] += i["usage"]
            ms = sorted(by_m)
            if len(ms) >= 2:
                first, last = by_m[ms[0]][0] / by_m[ms[0]][1], by_m[ms[-1]][0] / by_m[ms[-1]][1]
                if first > 0 and last > first * 1.15:
                    scale, per = next(((k, lbl) for k, lbl in ((1, "unit"), (1_000, "1K units"), (1_000_000, "1M units"))
                                       if first * k >= 1), (1_000_000, "1M units"))
                    findings.append({"level": "medium", "title": f"{svc} costs more per unit",
                                     "detail": f"Cost per {per} went from {{cur}}{first * scale:,.2f} ({ms[0]}) to "
                                               f"{{cur}}{last * scale:,.2f} ({ms[-1]}), +{(last / first - 1) * 100:.0f}%.",
                                     "action": "Check for a plan or pricing-tier change, or a switch to a more expensive model/SKU.",
                                     "saving": None})

    # 5) Fixed subscriptions: same amount every month
    subs = []
    for svc, items in per_service.items():
        by_m = defaultdict(float)
        for i in items:
            if i["date"]:
                by_m[_month(i["date"])] += i["cost"]
        vals = list(by_m.values())
        if len(vals) >= 2 and min(vals) > 0 and max(vals) - min(vals) <= 0.01 * max(vals):
            subs.append((svc, vals[-1]))
    if subs:
        monthly_fixed = sum(v for _, v in subs)
        findings.append({"level": "low", "title": f"{len(subs)} fixed subscription{'' if len(subs) == 1 else 's'}: {{cur}}{monthly_fixed:,.2f}/month",
                         "detail": ", ".join(f"{s} ({{cur}}{v:,.2f})" for s, v in sorted(subs, key=lambda x: -x[1])) + ".",
                         "action": f"Review seat counts and unused tools — these add up to {{cur}}{monthly_fixed * 12:,.2f} a year.",
                         "saving": None})

    # 6) Concentration
    if services and total > 0 and services[0][1] / total >= 0.4 and len(services) > 1:
        svc, c = services[0]
        findings.append({"level": "low", "title": f"{svc} is {c / total * 100:.0f}% of your spend",
                         "detail": "A single vendor dominates the bill, so small changes there matter most.",
                         "action": "Ask about committed-use or annual discounts, and set a spend alert on this vendor.",
                         "saving": None})

    order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: order[f["level"]])
    run_rate = monthly[months[-1]] if months else None
    return {"total": total, "services": service_table, "months": month_table, "findings": findings,
            "run_rate": run_rate, "annualized": run_rate * 12 if run_rate is not None else None,
            "last_month": months[-1] if months else None, "rows": len(rows),
            "exact_savings": sum(f["saving"] for f in findings if f["saving"])}


def sample_csv(today: date | None = None) -> str:
    """Three recent months of realistic spend, including a spike, a duplicate charge and a price change."""
    today = today or date.today()
    prev = lambda d: (d.replace(day=1) - timedelta(days=1)).replace(day=1)
    m3_ = prev(today)          # last full month
    m2 = prev(m3_)
    m1 = prev(m2)
    lines = ["Service,Date,Usage,Cost"]
    for mon, openai_usage, openai_cost, aws, twilio in ((m1, 41_000_000, 410.00, 612.40, 88.10),
                                                         (m2, 52_000_000, 520.00, 640.95, 91.30),
                                                         (m3_, 61_000_000, 915.00, 655.20, 86.75)):
        d = lambda day: mon.replace(day=day).isoformat()
        lines += [f"OpenAI,{d(28)},{openai_usage},{openai_cost:.2f}", f"AWS,{d(28)},,{aws:.2f}",
                  f"Slack,{d(3)},24,{24 * 8.75:.2f}", f"Notion,{d(5)},24,{24 * 10:.2f}", f"Figma,{d(12)},6,{6 * 15:.2f}",
                  f"Vercel,{d(15)},,{20.00:.2f}"]
        for day in (7, 14, 21):
            lines.append(f"Twilio,{d(day)},{4000 + day * 10},{twilio / 3:.2f}")
    d3 = lambda day: m3_.replace(day=day).isoformat()
    lines.append(f"Twilio,{d3(24)},38000,{(91.30 / 3) * 9:.2f}")      # spike
    lines.append(f"Figma,{d3(12)},6,{6 * 15:.2f}")                      # duplicate charge
    return "\n".join(lines) + "\n"
