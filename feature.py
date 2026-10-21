from flask import Blueprint, flash, redirect, render_template, request, url_for

import logic

bp = Blueprint("feature", __name__)


def _read_upload() -> str:
    f = request.files.get("file")
    if not f or not f.filename:
        return ""
    raw = f.read()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return ""


@bp.route("/", methods=["GET"])
def index():
    return render_template("index.html", currencies=logic.CURRENCIES)


@bp.route("/analyze", methods=["POST"])
def analyze():
    currency = request.form.get("currency", "USD")
    if currency not in logic.CURRENCIES:
        currency = "USD"
    if request.form.get("sample_data"):
        text = logic.sample_csv()
    else:
        text = _read_upload() or request.form.get("cost_data", "")
    try:
        rows, warnings = logic.parse_costs(text)
    except logic.ParseError as e:
        flash(str(e), "error")
        return redirect(url_for("feature.index"))
    result = logic.analyze(rows)
    return render_template("results.html", r=result, warnings=warnings, cur=logic.CURRENCIES[currency],
                           sample=bool(request.form.get("sample_data")))
