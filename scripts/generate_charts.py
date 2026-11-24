"""Satış və iadə məlumatlarından Azərbaycan dilində analitik qrafiklər yaradır."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.ticker import FuncFormatter, MaxNLocator


ROOT_DIR = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT_DIR / "data" / "elektronika_satis_data.csv"
IMAGE_DIR = ROOT_DIR / "images"

NAVY = "#1B365D"
TEAL = "#008080"
CORAL = "#D9534F"
TEXT = "#243447"
MUTED = "#667085"
GRID = "#E6EBF1"

REQUIRED_COLUMNS = {
    "Tarix",
    "Filial",
    "Kateqoriya",
    "Umumi_Mebleg_AZN",
    "Status",
    "Iade_Sebebi",
}

AY_ADLARI = {
    1: "Yan",
    2: "Fev",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "İyn",
    7: "İyl",
    8: "Avq",
    9: "Sen",
    10: "Okt",
    11: "Noy",
    12: "Dek",
}


def load_data() -> pd.DataFrame:
    """CSV məlumatlarını oxuyur və tələb olunan sütunları yoxlayır."""
    data = pd.read_csv(CSV_PATH, encoding="utf-8-sig", parse_dates=["Tarix"])
    missing_columns = sorted(REQUIRED_COLUMNS - set(data.columns))
    if missing_columns:
        raise ValueError(f"CSV faylında tələb olunan sütunlar yoxdur: {missing_columns}")
    if data.empty:
        raise ValueError("CSV faylı boşdur; qrafik yaratmaq mümkün deyil.")

    data["Umumi_Mebleg_AZN"] = pd.to_numeric(data["Umumi_Mebleg_AZN"], errors="raise")
    expected_statuses = {"Satılıb", "Geri Qaytarılıb"}
    unexpected_statuses = set(data["Status"].dropna().unique()) - expected_statuses
    if unexpected_statuses:
        raise ValueError(f"Gözlənilməyən əməliyyat statusları: {unexpected_statuses}")
    return data


def prepare_chart_style() -> None:
    """Bütün qrafiklər üçün vahid korporativ görünüş tətbiq edir."""
    sns.set_theme(style="whitegrid", context="notebook", font="DejaVu Sans")
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": GRID,
            "axes.labelcolor": TEXT,
            "axes.titlecolor": NAVY,
            "axes.titleweight": "bold",
            "axes.titlesize": 15,
            "axes.labelsize": 10,
            "xtick.color": MUTED,
            "ytick.color": TEXT,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "font.family": "DejaVu Sans",
            "savefig.facecolor": "white",
        }
    )


def format_azn(value: float) -> str:
    """Məbləği minlik ayırıcı və AZN valyuta kodu ilə göstərir."""
    return f"{value:,.0f} AZN"


def style_axis(axis: plt.Axes, *, x_grid: bool = True, y_grid: bool = False) -> None:
    """Oxların çərçivə və tor görünüşünü sadələşdirir."""
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.spines["left"].set_color(GRID)
    axis.spines["bottom"].set_color(GRID)
    axis.grid(axis="x" if x_grid else "y", visible=True, color=GRID)
    if x_grid and not y_grid:
        axis.grid(axis="y", visible=False)


def create_branch_return_chart(data: pd.DataFrame) -> Path:
    """Filiallar üzrə iadə faizini və maliyyə zərərini yanaşı göstərir."""
    grouped = (
        data.assign(
            Iade_Gostericisi=data["Status"].eq("Geri Qaytarılıb"),
            Iade_Meblegi=data["Umumi_Mebleg_AZN"].where(
                data["Status"].eq("Geri Qaytarılıb"), 0
            ),
        )
        .groupby("Filial", as_index=False)
        .agg(
            Emeliyyat_Sayi=("Status", "size"),
            Iade_Sayi=("Iade_Gostericisi", "sum"),
            Iade_Zereri=("Iade_Meblegi", "sum"),
        )
    )
    grouped["Iade_Faizi"] = 100 * grouped["Iade_Sayi"] / grouped["Emeliyyat_Sayi"]
    grouped = grouped.sort_values("Iade_Faizi", ascending=True)

    figure, (rate_axis, loss_axis) = plt.subplots(
        1,
        2,
        figsize=(13.5, 6.4),
        sharey=True,
        gridspec_kw={"width_ratios": [1, 1.25]},
    )
    figure.suptitle("Filiallar üzrə geri qaytarılma təhlili", x=0.08, ha="left", y=0.98, fontsize=18)
    figure.text(
        0.08,
        0.925,
        "İadə tezliyi və qaytarılmış əməliyyatların maliyyə zərəri",
        color=MUTED,
        fontsize=10,
    )

    sns.barplot(
        data=grouped,
        x="Iade_Faizi",
        y="Filial",
        color=NAVY,
        ax=rate_axis,
        orient="h",
    )
    sns.barplot(
        data=grouped,
        x="Iade_Zereri",
        y="Filial",
        color=CORAL,
        ax=loss_axis,
        orient="h",
    )
    rate_axis.set_title("İadə faizi", loc="left", pad=12)
    rate_axis.set_xlabel("Bütün əməliyyatlarda iadələrin payı (%)")
    rate_axis.set_ylabel("")
    rate_axis.set_xlim(0, grouped["Iade_Faizi"].max() * 1.25)
    for bar, value in zip(rate_axis.patches, grouped["Iade_Faizi"]):
        rate_axis.text(
            value + grouped["Iade_Faizi"].max() * 0.025,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.1f}%",
            va="center",
            ha="left",
            color=NAVY,
            fontsize=9,
            fontweight="bold",
        )

    loss_axis.set_title("İadə zərəri", loc="left", pad=12)
    loss_axis.set_xlabel("Məbləğ (AZN)")
    loss_axis.set_ylabel("")
    loss_axis.set_xlim(0, grouped["Iade_Zereri"].max() * 1.32)
    loss_axis.xaxis.set_major_locator(MaxNLocator(nbins=5))
    loss_axis.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:,.0f}"))
    for bar, value in zip(loss_axis.patches, grouped["Iade_Zereri"]):
        loss_axis.text(
            value + grouped["Iade_Zereri"].max() * 0.025,
            bar.get_y() + bar.get_height() / 2,
            format_azn(value),
            va="center",
            ha="left",
            color=CORAL,
            fontsize=9,
            fontweight="bold",
        )
    style_axis(rate_axis)
    style_axis(loss_axis)
    rate_axis.grid(axis="y", visible=False)
    loss_axis.grid(axis="y", visible=False)
    figure.subplots_adjust(left=0.22, right=0.96, top=0.84, bottom=0.13, wspace=0.12)

    output_path = IMAGE_DIR / "1_filial_iade_faizi.png"
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return output_path


def create_return_reason_pareto_chart(data: pd.DataFrame) -> Path:
    """İadə səbəblərinin zərər məbləğini və kumulyativ payını Pareto üsulu ilə göstərir."""
    returned = data.loc[
        data["Status"].eq("Geri Qaytarılıb") & data["Iade_Sebebi"].notna()
    ]
    grouped = (
        returned.groupby("Iade_Sebebi", as_index=False)
        .agg(Iade_Zereri=("Umumi_Mebleg_AZN", "sum"))
        .sort_values("Iade_Zereri", ascending=False)
    )
    if grouped.empty:
        raise ValueError("Pareto qrafiki üçün iadə səbəbləri üzrə məlumat yoxdur.")
    grouped["Kumulyativ_Pay"] = grouped["Iade_Zereri"].cumsum() / grouped["Iade_Zereri"].sum() * 100

    figure, axis = plt.subplots(figsize=(11.5, 6.4))
    figure.suptitle("İadə səbəblərinin Pareto təhlili", x=0.09, ha="left", y=0.98, fontsize=18)
    figure.text(
        0.09,
        0.925,
        "Maliyyə zərəri səbəblər üzrə sıralanıb; xətt kumulyativ payı göstərir",
        color=MUTED,
        fontsize=10,
    )
    bars = sns.barplot(
        data=grouped,
        x="Iade_Sebebi",
        y="Iade_Zereri",
        color=CORAL,
        ax=axis,
    )
    axis.set_xlabel("İadə səbəbi")
    axis.set_ylabel("Maliyyə zərəri (AZN)")
    axis.tick_params(axis="x", labelrotation=15)
    axis.set_ylim(0, grouped["Iade_Zereri"].max() * 1.2)
    axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:,.0f}"))
    for patch, value in zip(bars.patches, grouped["Iade_Zereri"]):
        axis.annotate(
            format_azn(value),
            (patch.get_x() + patch.get_width() / 2, patch.get_height()),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
            va="bottom",
            color=CORAL,
            fontsize=9,
            fontweight="bold",
        )

    cumulative_axis = axis.twinx()
    cumulative_axis.plot(
        range(len(grouped)),
        grouped["Kumulyativ_Pay"],
        color=TEAL,
        marker="o",
        markersize=7,
        linewidth=2.5,
        label="Kumulyativ pay",
        zorder=5,
    )
    cumulative_axis.set_ylabel("Kumulyativ pay (%)", color=TEAL)
    cumulative_axis.set_ylim(0, 115)
    cumulative_axis.tick_params(axis="y", colors=TEAL)
    cumulative_axis.spines["top"].set_visible(False)
    cumulative_axis.spines["right"].set_color(GRID)
    for index, value in enumerate(grouped["Kumulyativ_Pay"]):
        cumulative_axis.annotate(
            f"{value:.0f}%",
            (index, value),
            xytext=(0, 9),
            textcoords="offset points",
            ha="center",
            color=TEAL,
            fontsize=9,
            fontweight="bold",
        )
    style_axis(axis)
    axis.grid(axis="x", visible=False)
    figure.subplots_adjust(left=0.11, right=0.89, top=0.83, bottom=0.22)

    output_path = IMAGE_DIR / "2_iade_sebebleri.png"
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return output_path


def create_category_comparison_chart(data: pd.DataFrame) -> Path:
    """Məhsul kateqoriyaları üzrə satış gəlirini və iadə məbləğini müqayisə edir."""
    grouped = (
        data.assign(
            Satish_Meblegi=data["Umumi_Mebleg_AZN"].where(data["Status"].eq("Satılıb"), 0),
            Iade_Meblegi=data["Umumi_Mebleg_AZN"].where(
                data["Status"].eq("Geri Qaytarılıb"), 0
            ),
        )
        .groupby("Kateqoriya", as_index=False)
        .agg(
            Satish_Meblegi=("Satish_Meblegi", "sum"),
            Iade_Meblegi=("Iade_Meblegi", "sum"),
        )
    )
    long_data = grouped.melt(
        id_vars="Kateqoriya",
        value_vars=["Satish_Meblegi", "Iade_Meblegi"],
        var_name="Gosterici",
        value_name="Mebleg",
    )
    long_data["Gosterici"] = long_data["Gosterici"].map(
        {
            "Satish_Meblegi": "Satış gəliri",
            "Iade_Meblegi": "İadə məbləği",
        }
    )

    figure, axis = plt.subplots(figsize=(11.5, 6.4))
    figure.suptitle("Kateqoriyalar üzrə satış və iadə müqayisəsi", x=0.09, ha="left", y=0.98, fontsize=18)
    figure.text(
        0.09,
        0.925,
        "Satılmış əməliyyatların gəliri qaytarılmış əməliyyatların məbləği ilə müqayisədə",
        color=MUTED,
        fontsize=10,
    )
    sns.barplot(
        data=long_data,
        x="Kateqoriya",
        y="Mebleg",
        hue="Gosterici",
        hue_order=["Satış gəliri", "İadə məbləği"],
        palette={"Satış gəliri": NAVY, "İadə məbləği": CORAL},
        ax=axis,
    )
    axis.set_xlabel("Məhsul kateqoriyası")
    axis.set_ylabel("Məbləğ (AZN)")
    axis.tick_params(axis="x", labelrotation=8)
    axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:,.0f}"))
    axis.set_ylim(0, long_data["Mebleg"].max() * 1.18)
    axis.legend(title="", frameon=False, loc="upper right")
    for patch in axis.patches:
        value = patch.get_height()
        if value > 0:
            axis.annotate(
                format_azn(value),
                (patch.get_x() + patch.get_width() / 2, value),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
                color=TEXT,
                rotation=0,
            )
    style_axis(axis)
    axis.grid(axis="x", visible=False)
    figure.subplots_adjust(left=0.11, right=0.96, top=0.83, bottom=0.2)

    output_path = IMAGE_DIR / "3_kateqoriya_muqayisesi.png"
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return output_path


def create_monthly_dynamics_chart(data: pd.DataFrame) -> Path:
    """Son 12 təqvim ayının xalis satış və iadə zərəri dinamikasını göstərir."""
    latest_month = data["Tarix"].max().to_period("M")
    first_month = latest_month - 11
    months = pd.period_range(first_month, latest_month, freq="M")

    monthly_data = data.copy()
    monthly_data["Ay"] = monthly_data["Tarix"].dt.to_period("M")
    monthly_data["Satis_Meblegi"] = monthly_data["Umumi_Mebleg_AZN"].where(
        monthly_data["Status"].eq("Satılıb"), 0
    )
    monthly_data["Iade_Meblegi"] = monthly_data["Umumi_Mebleg_AZN"].where(
        monthly_data["Status"].eq("Geri Qaytarılıb"), 0
    )
    monthly = (
        monthly_data.groupby("Ay")
        .agg(
            Satis_Meblegi=("Satis_Meblegi", "sum"),
            Iade_Zereri=("Iade_Meblegi", "sum"),
        )
        .reindex(months, fill_value=0)
        .rename_axis("Ay")
        .reset_index()
    )
    monthly["Xalis_Satis"] = monthly["Satis_Meblegi"] - monthly["Iade_Zereri"]
    monthly["Ay_Etiket"] = monthly["Ay"].map(lambda period: AY_ADLARI[period.month])

    long_data = monthly.melt(
        id_vars=["Ay", "Ay_Etiket"],
        value_vars=["Xalis_Satis", "Iade_Zereri"],
        var_name="Gosterici",
        value_name="Mebleg",
    )
    long_data["Gosterici"] = long_data["Gosterici"].map(
        {
            "Xalis_Satis": "Xalis satış",
            "Iade_Zereri": "İadə zərəri",
        }
    )
    long_data["Ay_Sira"] = long_data["Ay"].map(lambda period: period.month)

    figure, axis = plt.subplots(figsize=(12.5, 6.4))
    period_label = f"{AY_ADLARI[first_month.month]} {first_month.year} — {AY_ADLARI[latest_month.month]} {latest_month.year}"
    figure.suptitle("Aylıq xalis satış və iadə dinamikası", x=0.09, ha="left", y=0.98, fontsize=18)
    figure.text(
        0.09,
        0.925,
        f"Son 12 təqvim ayı: {period_label}",
        color=MUTED,
        fontsize=10,
    )
    sns.lineplot(
        data=long_data,
        x="Ay_Sira",
        y="Mebleg",
        hue="Gosterici",
        hue_order=["Xalis satış", "İadə zərəri"],
        palette={"Xalis satış": NAVY, "İadə zərəri": CORAL},
        style="Gosterici",
        markers=True,
        dashes=False,
        linewidth=2.8,
        markersize=7,
        ax=axis,
    )
    axis.set_xlabel("Ay")
    axis.set_ylabel("Məbləğ (AZN)")
    axis.set_xticks(range(1, 13))
    axis.set_xticklabels([AY_ADLARI[month] for month in range(1, 13)])
    axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:,.0f}"))
    axis.legend(title="", frameon=False, loc="upper left")
    style_axis(axis)
    axis.grid(axis="x", visible=False)
    figure.subplots_adjust(left=0.11, right=0.96, top=0.83, bottom=0.14)

    output_path = IMAGE_DIR / "4_ayliq_dinamika.png"
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return output_path


def main() -> None:
    """Yükləyir, dörd qrafiki yaradır və nəticələri qeyd edir."""
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    data = load_data()
    prepare_chart_style()

    chart_paths = [
        create_branch_return_chart(data),
        create_return_reason_pareto_chart(data),
        create_category_comparison_chart(data),
        create_monthly_dynamics_chart(data),
    ]
    for chart_path in chart_paths:
        print(f"Yaradıldı: {chart_path} ({chart_path.stat().st_size:,} bayt)")


if __name__ == "__main__":
    main()
