"""Azərbaycanda elektronika satışı üçün sintetik əməliyyat məlumatları yaradır."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
TRANSACTION_COUNT = 5_000
RANDOM_SEED = 2026

FILIAL_LAR = [
    "Bakı - 28 May",
    "Bakı - Əcəmi",
    "Bakı - Gənclik Mall",
    "Sumqayıt",
    "Gəncə",
    "Lənkəran",
]

MEHSULLAR = {
    "Smartfonlar": {
        "iPhone 15": (2_250.00, 0.79),
        "Samsung S24": (1_950.00, 0.77),
        "Redmi Note 13": (520.00, 0.81),
    },
    "Noutbuklar": {
        "Lenovo Yoga": (2_450.00, 0.78),
        "Asus TUF": (2_800.00, 0.80),
        "MacBook Air": (3_600.00, 0.82),
    },
    "Məişət Texnikası": {
        "Paltaryuyan": (1_150.00, 0.76),
        "Soyuducu": (1_650.00, 0.78),
        "Kondisioner": (1_300.00, 0.75),
    },
    "Aksesuarlar": {
        "Qulaqlıq": (85.00, 0.55),
        "Adapter": (25.00, 0.42),
        "Powerbank": (65.00, 0.58),
    },
}

ADLAR = [
    "Aysel", "Nigar", "Leyla", "Günel", "Sevinc", "Fərid", "Elvin",
    "Orxan", "Rəşad", "Tural", "Murad", "Kənan", "Zəhra", "Aylin",
    "Kamran", "Nərmin", "Samir", "Lalə", "Ramin", "Ülviyyə",
]

SOYADLAR = [
    "Məmmədov", "Əliyev", "Hüseynov", "Quliyev", "Rzayev",
    "Həsənov", "İbrahimov", "Əhmədov", "Cəfərov", "Vəliyev",
    "Məmmədova", "Əliyeva", "Hüseynova", "Quliyeva", "Rzayeva",
    "Həsənova", "İbrahimova", "Əhmədova", "Cəfərova", "Vəliyeva",
]

ODENIS_NOVLERI = ["Nağd", "Kredit (Daxili)", "Taksit Kartı"]
ODENIS_EHTIMALLARI = [0.35, 0.35, 0.30]
IADE_SEBEBLERI = [
    "Zavod qüsuru",
    "Müştəri fikrini dəyişdi",
    "Kredit təsdiqlənmədi",
    "Çatdırılma zamanı zədə",
    "Texniki uyğunsuzluq",
]


def _mehsul_sec(rng: np.random.Generator) -> tuple[str, str, float, float]:
    """Kateqoriya və həmin kateqoriyaya uyğun məhsul seçir."""
    kateqoriyalar = list(MEHSULLAR)
    kateqoriya = str(rng.choice(kateqoriyalar, p=[0.34, 0.20, 0.24, 0.22]))
    mehsul_adi = str(rng.choice(list(MEHSULLAR[kateqoriya])))
    vahid_qiymet, maya_faizi = MEHSULLAR[kateqoriya][mehsul_adi]

    qiymet_varyasiyasi = float(rng.normal(1.0, 0.035))
    vahid_qiymet = round(vahid_qiymet * qiymet_varyasiyasi, 2)
    vahid_maya = round(vahid_qiymet * maya_faizi, 2)
    return kateqoriya, mehsul_adi, vahid_qiymet, vahid_maya


def _iade_ehtimali(odenis_novu: str, mehsul_adi: str) -> float:
    """Ödəniş və məhsul xüsusiyyətlərinə görə əməliyyatın iade ehtimalını verir."""
    ehtimal = {
        "Nağd": 0.095,
        "Kredit (Daxili)": 0.230,
        "Taksit Kartı": 0.135,
    }[odenis_novu]

    if mehsul_adi == "Adapter":
        ehtimal += 0.10
    elif mehsul_adi == "Qulaqlıq":
        ehtimal += 0.045
    elif mehsul_adi in {"Paltaryuyan", "Soyuducu", "Kondisioner"}:
        ehtimal += 0.015

    return min(ehtimal, 0.60)


def _iade_sebebi_sec(
    rng: np.random.Generator,
    odenis_novu: str,
    mehsul_adi: str,
) -> str:
    """İadənin səbəbini ödəniş və məhsul risklərinə uyğun seçir."""
    if odenis_novu == "Kredit (Daxili)":
        ehtimallar = [0.28, 0.15, 0.38, 0.07, 0.12]
    else:
        ehtimallar = [0.32, 0.23, 0.02, 0.16, 0.27]

    if mehsul_adi == "Adapter":
        ehtimallar = [0.58, 0.12, ehtimallar[2], 0.10, 0.10]
    elif mehsul_adi in {"Qulaqlıq", "Powerbank"}:
        ehtimallar = [0.43, 0.18, ehtimallar[2], 0.12, 0.17]

    # Kredit təsdiqlənməməsi yalnız daxili kredit əməliyyatlarına aiddir.
    if odenis_novu != "Kredit (Daxili)":
        ehtimallar[2] = 0.0
    cem = sum(ehtimallar)
    ehtimallar = [ehtimal / cem for ehtimal in ehtimallar]

    return str(rng.choice(IADE_SEBEBLERI, p=ehtimallar))


def generate_dataset() -> pd.DataFrame:
    """Sabit toxumla 5 000 sintetik pərakəndə əməliyyat yaradır."""
    rng = np.random.default_rng(RANDOM_SEED)

    musteri_saylari = 1_800
    musteri_idler = np.arange(10_001, 10_001 + musteri_saylari)
    musteri_ehtimallari = 1 / np.arange(1, musteri_saylari + 1, dtype=float) ** 1.08
    musteri_ehtimallari /= musteri_ehtimallari.sum()
    secilmis_musteriler = rng.choice(
        musteri_idler,
        size=TRANSACTION_COUNT,
        p=musteri_ehtimallari,
    )

    musteri_adlari = {
        musteri_id: (
            f"{rng.choice(ADLAR)} "
            f"{rng.choice(SOYADLAR)}"
        )
        for musteri_id in musteri_idler
    }

    tarix_baslangici = np.datetime64("2025-01-01")
    tarix_sayi = 365 + 365
    tarixler = tarix_baslangici + rng.integers(
        0,
        tarix_sayi,
        size=TRANSACTION_COUNT,
    ).astype("timedelta64[D]")

    qeydlər: list[dict[str, object]] = []
    for indeks in range(TRANSACTION_COUNT):
        kateqoriya, mehsul_adi, vahid_qiymet, vahid_maya = _mehsul_sec(rng)
        odenis_novu = str(rng.choice(ODENIS_NOVLERI, p=ODENIS_EHTIMALLARI))

        say_ehtimallari = [0.84, 0.13, 0.03] if kateqoriya == "Aksesuarlar" else [0.95, 0.045, 0.005]
        say = int(rng.choice([1, 2, 3], p=say_ehtimallari))
        umumi_mebleg = round(vahid_qiymet * say, 2)
        maya_deyeri = round(vahid_maya * say, 2)

        qaytarilib = rng.random() < _iade_ehtimali(odenis_novu, mehsul_adi)
        status = "Geri Qaytarılıb" if qaytarilib else "Satılıb"
        iade_sebebi = (
            _iade_sebebi_sec(rng, odenis_novu, mehsul_adi)
            if qaytarilib
            else None
        )

        qeydlər.append(
            {
                "Emeliyyat_ID": f"EM{indeks + 1:06d}",
                "Tarix": pd.Timestamp(tarixler[indeks]),
                "Musteri_ID": f"MS{int(secilmis_musteriler[indeks])}",
                "Musteri_Ad_Soyad": musteri_adlari[int(secilmis_musteriler[indeks])],
                "Filial": str(rng.choice(FILIAL_LAR, p=[0.28, 0.15, 0.18, 0.14, 0.15, 0.10])),
                "Kateqoriya": kateqoriya,
                "Mehsul_Adi": mehsul_adi,
                "Say": say,
                "Vahid_Qiymet_AZN": vahid_qiymet,
                "Umumi_Mebleg_AZN": umumi_mebleg,
                "Maya_Deyeri_AZN": maya_deyeri,
                "Odenis_Novu": odenis_novu,
                "Status": status,
                "Iade_Sebebi": iade_sebebi,
            }
        )

    return pd.DataFrame(qeydlər)


def save_excel(data: pd.DataFrame, output_path: Path) -> None:
    """Məlumatları oxunaqlı başlıq və formatlarla Excel faylına yazır."""
    with pd.ExcelWriter(output_path, engine="openpyxl", date_format="DD.MM.YYYY") as writer:
        data.to_excel(writer, index=False, sheet_name="Əməliyyatlar")
        worksheet = writer.sheets["Əməliyyatlar"]
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions

        header_fill = PatternFill(fill_type="solid", fgColor="1B365D")
        header_font = Font(color="FFFFFF", bold=True)
        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for column_index, column_name in enumerate(data.columns, start=1):
            values = [str(column_name)] + [
                "" if pd.isna(value) else str(value)
                for value in data[column_name].head(250)
            ]
            width = min(max(max(map(len, values)) + 2, 12), 34)
            worksheet.column_dimensions[get_column_letter(column_index)].width = width

            if column_name == "Tarix":
                for cell in worksheet.iter_cols(
                    min_col=column_index,
                    max_col=column_index,
                    min_row=2,
                    max_row=worksheet.max_row,
                ):
                    for date_cell in cell:
                        date_cell.number_format = "DD.MM.YYYY"
            elif column_name.endswith("_AZN"):
                for cell in worksheet.iter_cols(
                    min_col=column_index,
                    max_col=column_index,
                    min_row=2,
                    max_row=worksheet.max_row,
                ):
                    for amount_cell in cell:
                        amount_cell.number_format = '#,##0.00 "₼"'

        worksheet.row_dimensions[1].height = 28


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = generate_dataset()

    csv_path = DATA_DIR / "elektronika_satis_data.csv"
    excel_path = DATA_DIR / "elektronika_satis_data.xlsx"
    data.to_csv(csv_path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    save_excel(data, excel_path)

    print(f"Yaradıldı: {csv_path} ({len(data):,} sətir)")
    print(f"Yaradıldı: {excel_path} ({len(data):,} sətir)")
    print(f"İadə payı: {(data['Status'] == 'Geri Qaytarılıb').mean():.1%}")


if __name__ == "__main__":
    main()
