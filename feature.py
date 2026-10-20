from flask import Blueprint, render_template, request, flash, redirect, url_for
import logic

bp = Blueprint("feature", __name__)

@bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@bp.route("/analyze", methods=["POST"])
def analyze():
    cost_data_input = request.form.get("cost_data", "").strip()
    
    if request.form.get("sample_data"):
        cost_data_input = logic.get_sample_data()

    if not cost_data_input:
        flash("Lütfen analiz etmek için maliyet verisi girin veya örnek veriyle deneyin.", "error")
        return redirect(url_for("feature.index"))

    try:
        df = logic.parse_cost_data(cost_data_input)
        analysis_results = logic.analyze_costs(df)
        plot_url = logic.generate_cost_plot(df)
        
        return render_template("results.html", 
                               total_cost=f"{analysis_results['total_cost']:.2f}",
                               cost_by_service=analysis_results['cost_by_service'],
                               anomalies=analysis_results['anomalies'],
                               suggestions=analysis_results['suggestions'],
                               plot_url=plot_url)
    except ValueError as e:
        flash(f"Veri işleme hatası: {e}", "error")
        return redirect(url_for("feature.index"))
    except Exception as e:
        flash(f"Beklenmeyen bir hata oluştu: {e}", "error")
        return redirect(url_for("feature.index"))
