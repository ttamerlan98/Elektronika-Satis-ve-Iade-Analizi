"""Satış məlumatlarından rəhbərlik üçün formatlanmış Excel hesabatı yaradır."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule, DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter


ROOT_DIR = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT_DIR / "data" / "elektronika_satis_data.csv"
REPORT_DIR = ROOT_DIR / "reports"
REPORT_PATH = REPORT_DIR / "Rehberlik_Uchun_Analitik_Hesabat.xlsx"

REQUIRED_COLUMNS = [
    "Emeliyyat_ID",
    "Tarix",
    "Musteri_ID",
    "Musteri_Ad_Soyad",
    "Filial",
    "Kateqoriya",
    "Mehsul_Adi",
    "Say",
    "Vahid_Qiymet_AZN",
    "Umumi_Mebleg_AZN",
    "Maya_Deyeri_AZN",
    "Odenis_Novu",
    "Status",
    "Iade_Sebebi",
]

NAVY = "1B365D"
TEAL = "008080"
CORAL = "D9534F"
SOFT_RED = "FCE4D6"
PALE_BLUE = "EAF0F7"
PALE_TEAL = "E5F2F1"
WHITE = "FFFFFF"
MID_GREY = "667085"
LIGHT_BORDER = "D6DEE8"
AZN_FORMAT = '#,##0.00 "₼"'
PERCENT_FORMAT = "0.0%"
DATE_FORMAT = "dd.mm.yyyy"


def load_data() -> pd.DataFrame:
    """CSV faylını oxuyur və hesabat üçün vacib ilkin yoxlamaları aparır."""
    data = pd.read_csv(CSV_PATH, encoding="utf-8-sig", parse_dates=["Tarix"])
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(data.columns))
    if missing_columns:
        raise ValueError(f"CSV faylında tələb olunan sütunlar yoxdur: {missing_columns}")
    if data.empty:
        raise ValueError("CSV faylı boşdur; hesabat yaratmaq mümkün deyil.")

    numeric_columns = [
        "Say",
        "Vahid_Qiymet_AZN",
        "Umumi_Mebleg_AZN",
        "Maya_Deyeri_AZN",
    ]
    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="raise")

    allowed_statuses = {"Satılıb", "Geri Qaytarılıb"}
    unexpected_statuses = set(data["Status"].dropna().unique()) - allowed_statuses
    if unexpected_statuses:
        raise ValueError(f"Gözlənilməyən əməliyyat statusları: {unexpected_statuses}")
    if data["Status"].isna().any():
        raise ValueError("Status sütununda boş dəyərlər var.")

    return data


def style_title(worksheet, title: str, subtitle: str, end_column: int) -> None:
    """Vərəq başlığını korporativ rənglər və birləşdirilmiş xanalarla formatlayır."""
    last_column = get_column_letter(end_column)
    worksheet.merge_cells(f"A1:{last_column}1")
    title_cell = worksheet["A1"]
    title_cell.value = title
    title_cell.fill = PatternFill("solid", fgColor=NAVY)
    title_cell.font = Font(name="Aptos Display", size=18, bold=True, color=WHITE)
    title_cell.alignment = Alignment(vertical="center")
    worksheet.row_dimensions[1].height = 36

    worksheet.merge_cells(f"A2:{last_column}2")
    subtitle_cell = worksheet["A2"]
    subtitle_cell.value = subtitle
    subtitle_cell.font = Font(name="Aptos", size=10, italic=True, color=MID_GREY)
    subtitle_cell.alignment = Alignment(vertical="center")
    worksheet.row_dimensions[2].height = 23


def style_table_header(worksheet, row: int, start_column: int, end_column: int) -> None:
    """Cədvəl başlıqlarını vahid tünd göy üslubda göstərir."""
    for cells in worksheet.iter_rows(
        min_row=row,
        max_row=row,
        min_col=start_column,
        max_col=end_column,
    ):
        for cell in cells:
            cell.fill = PatternFill("solid", fgColor=NAVY)
            cell.font = Font(name="Aptos", bold=True, color=WHITE)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = Border(bottom=Side(style="medium", color=TEAL))
    worksheet.row_dimensions[row].height = 32


def format_data_region(worksheet, start_row: int, end_row: int, end_column: int) -> None:
    """Hesabat cədvəllərində oxunaqlı sətir və sərhəd formatı tətbiq edir."""
    for row in worksheet.iter_rows(
        min_row=start_row,
        max_row=end_row,
        min_col=1,
        max_col=end_column,
    ):
        for cell in row:
            cell.font = Font(name="Aptos", size=10, color="243447")
            cell.alignment = Alignment(vertical="center")
            cell.border = Border(bottom=Side(style="hair", color=LIGHT_BORDER))
            if cell.row % 2 == 0:
                cell.fill = PatternFill("solid", fgColor="F7F9FC")


def set_column_widths(worksheet, minimum: int = 12, maximum: int = 34) -> None:
    """Vərəqdə məzmun uzunluğuna əsasən sütun enlərini tənzimləyir."""
    for column_cells in worksheet.columns:
        column_letter = get_column_letter(column_cells[0].column)
        width = max(
            (len(str(cell.value)) for cell in column_cells if cell.value is not None),
            default=minimum,
        )
        worksheet.column_dimensions[column_letter].width = min(
            max(width + 2, minimum),
            maximum,
        )


def add_excel_table(worksheet, name: str, reference: str) -> None:
    """Filtr və zolaqlı sətir üslubu olan Excel cədvəli əlavə edir."""
    table = Table(displayName=name, ref=reference)
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    worksheet.add_table(table)


def prepare_source_sheet(workbook: Workbook, data: pd.DataFrame):
    """Hesabat formullarının istinad etdiyi gizli əməliyyat vərəqini yaradır."""
    worksheet = workbook.create_sheet("Mənbə_Məlumat")
    source = data[REQUIRED_COLUMNS].copy()
    source["Iade_Gostericisi"] = source["Status"].eq("Geri Qaytarılıb").astype(int)
    worksheet.append(source.columns.tolist())

    for row in source.itertuples(index=False, name=None):
        worksheet.append(
            [
                value.to_pydatetime() if isinstance(value, pd.Timestamp) else (
                    None if pd.isna(value) else value
                )
                for value in row
            ]
        )

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions
    for cell in worksheet[1]:
        cell.fill = PatternFill("solid", fgColor=NAVY)
        cell.font = Font(bold=True, color=WHITE)
    for row in worksheet.iter_rows(min_row=2, min_col=2, max_col=2):
        row[0].number_format = DATE_FORMAT
    worksheet.sheet_state = "hidden"
    return worksheet


def create_kpi_sheet(workbook: Workbook, source_end_row: int) -> None:
    """KPI vərəqini, Excel daxilində yenidən hesablanan formulalarla qurur."""
    worksheet = workbook.create_sheet("Icmal_KPI", 0)
    style_title(
        worksheet,
        "ELEKTRONİKA SATIŞI VƏ İADƏLƏR — İCRAÇI İCMALI",
        "Əməliyyat məlumatları əsasında maliyyə və müştəri xidməti göstəriciləri",
        10,
    )

    statuses = f"'Mənbə_Məlumat'!$M$2:$M${source_end_row}"
    amounts = f"'Mənbə_Məlumat'!$J$2:$J${source_end_row}"
    costs = f"'Mənbə_Məlumat'!$K$2:$K${source_end_row}"
    gross_sales_formula = f'=SUMIFS({amounts},{statuses},"Satılıb")'
    returns_formula = f'=SUMIFS({amounts},{statuses},"Geri Qaytarılıb")'
    sold_cost_formula = f'=SUMIFS({costs},{statuses},"Satılıb")'
    returned_count_formula = f'=COUNTIF({statuses},"Geri Qaytarılıb")'
    transaction_count_formula = f"=COUNTA({statuses})"

    cards = [
        ("ÜMUMİ SATIŞ DÖVRİYYƏSİ", gross_sales_formula, AZN_FORMAT),
        ("İADƏLƏRİN MƏBLƏĞİ", returns_formula, AZN_FORMAT),
        ("XALİS GƏLİR", "=A5-C5", AZN_FORMAT),
        ("XALİS MƏNFƏƏT", "=E5-G8", AZN_FORMAT),
        ("ÜMUMİ İADƏ FAİZİ", "=B8/B9", PERCENT_FORMAT),
    ]
    card_pairs = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10)]
    for (label, formula, number_format), (start_column, end_column) in zip(cards, card_pairs):
        label_range = (
            f"{get_column_letter(start_column)}4:"
            f"{get_column_letter(end_column)}4"
        )
        value_range = (
            f"{get_column_letter(start_column)}5:"
            f"{get_column_letter(end_column)}6"
        )
        worksheet.merge_cells(label_range)
        worksheet.merge_cells(value_range)
        label_cell = worksheet.cell(row=4, column=start_column, value=label)
        label_cell.fill = PatternFill("solid", fgColor=NAVY)
        label_cell.font = Font(name="Aptos", size=9, bold=True, color=WHITE)
        label_cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        value_cell = worksheet.cell(row=5, column=start_column, value=formula)
        value_cell.number_format = number_format
        value_cell.fill = PatternFill("solid", fgColor=PALE_TEAL if start_column in (5, 7) else PALE_BLUE)
        value_cell.font = Font(name="Aptos Display", size=16, bold=True, color=NAVY)
        value_cell.alignment = Alignment(horizontal="center", vertical="center")

    worksheet.row_dimensions[4].height = 34
    worksheet.row_dimensions[5].height = 29
    worksheet.row_dimensions[6].height = 15
    worksheet.row_dimensions[8].hidden = True
    worksheet.row_dimensions[9].hidden = True
    worksheet["G8"] = sold_cost_formula
    worksheet["G9"] = transaction_count_formula
    worksheet["G8"].number_format = AZN_FORMAT
    worksheet["G9"] = transaction_count_formula
    worksheet["B8"] = returned_count_formula
    worksheet["B9"] = transaction_count_formula
    worksheet["B8"].number_format = "0"
    worksheet["B9"].number_format = "0"
    worksheet["A8"] = "Daxili hesablama: qaytarılmış əməliyyatların sayı"
    worksheet["A9"] = "Daxili hesablama: bütün əməliyyatların sayı"
    worksheet["G8"] = sold_cost_formula
    worksheet["F8"] = "Daxili hesablama: satılmış malların maya dəyəri"
    for coordinate in ("A8", "A9", "F8"):
        worksheet[coordinate].font = Font(color=MID_GREY, size=9)

    worksheet.merge_cells("A11:J11")
    worksheet["A11"] = (
        "Qeyd: Xalis mənfəət xalis gəlirdən satılmış malların maya dəyəri "
        "çıxılmaqla hesablanır. İadə olunan malın maya dəyəri bərpa oluna "
        "bilən ehtiyat kimi qəbul edilir; logistika və təmir xərcləri "
        "mənbə məlumatlarında yoxdur."
    )
    worksheet["A11"].alignment = Alignment(wrap_text=True, vertical="center")
    worksheet["A11"].font = Font(name="Aptos", size=9, italic=True, color=MID_GREY)
    worksheet.row_dimensions[11].height = 42
    worksheet.freeze_panes = "A4"
    worksheet.sheet_view.showGridLines = False

    for column in range(1, 11):
        worksheet.column_dimensions[get_column_letter(column)].width = 15


def create_branch_and_reason_sheet(workbook: Workbook, data: pd.DataFrame, source_end_row: int) -> None:
    """Filial və iadə səbəbləri üzrə maliyyə bölgülərini yaradır."""
    worksheet = workbook.create_sheet("Filial_ve_Sebebler")
    style_title(
        worksheet,
        "FİLİALLAR VƏ İADƏ SƏBƏBLƏRİ",
        "Satış dövriyyəsi, iadə zərəri və iadə riskinin müqayisəsi",
        10,
    )

    branch_headers = [
        "Filial",
        "Satış məbləği (AZN)",
        "Satış sayı",
        "İadə zərəri (AZN)",
        "İadə sayı",
        "İadə faizi",
    ]
    start_row = 4
    for column, header in enumerate(branch_headers, start=1):
        worksheet.cell(start_row, column, header)
    style_table_header(worksheet, start_row, 1, len(branch_headers))

    source_branch = f"'Mənbə_Məlumat'!$E$2:$E${source_end_row}"
    source_status = f"'Mənbə_Məlumat'!$M$2:$M${source_end_row}"
    source_amount = f"'Mənbə_Məlumat'!$J$2:$J${source_end_row}"
    branches = sorted(data["Filial"].dropna().unique())
    for row_number, branch in enumerate(branches, start=start_row + 1):
        worksheet.cell(row_number, 1, branch)
        worksheet.cell(
            row_number,
            2,
            f'=SUMIFS({source_amount},{source_branch},A{row_number},{source_status},"Satılıb")',
        )
        worksheet.cell(
            row_number,
            3,
            f'=COUNTIFS({source_branch},A{row_number},{source_status},"Satılıb")',
        )
        worksheet.cell(
            row_number,
            4,
            f'=SUMIFS({source_amount},{source_branch},A{row_number},{source_status},"Geri Qaytarılıb")',
        )
        worksheet.cell(
            row_number,
            5,
            f'=COUNTIFS({source_branch},A{row_number},{source_status},"Geri Qaytarılıb")',
        )
        worksheet.cell(row_number, 6, f"=E{row_number}/(C{row_number}+E{row_number})")
    branch_end_row = start_row + len(branches)
    format_data_region(worksheet, start_row + 1, branch_end_row, len(branch_headers))
    add_excel_table(
        worksheet,
        "FilialGostericileri",
        f"A{start_row}:F{branch_end_row}",
    )
    for row_number in range(start_row + 1, branch_end_row + 1):
        worksheet.cell(row_number, 2).number_format = AZN_FORMAT
        worksheet.cell(row_number, 4).number_format = AZN_FORMAT
        worksheet.cell(row_number, 6).number_format = PERCENT_FORMAT

    reason_start = branch_end_row + 4
    worksheet.merge_cells(start_row=reason_start, start_column=1, end_row=reason_start, end_column=4)
    worksheet.cell(reason_start, 1, "İADƏ SƏBƏBLƏRİ ÜZRƏ İTKİ")
    worksheet.cell(reason_start, 1).fill = PatternFill("solid", fgColor=TEAL)
    worksheet.cell(reason_start, 1).font = Font(bold=True, color=WHITE, size=11)
    worksheet.cell(reason_start, 1).alignment = Alignment(vertical="center")
    worksheet.row_dimensions[reason_start].height = 25

    reason_headers = ["İadə səbəbi", "İadə zərəri (AZN)", "İadə sayı", "Ümumi zərərdə pay"]
    reason_header_row = reason_start + 1
    for column, header in enumerate(reason_headers, start=1):
        worksheet.cell(reason_header_row, column, header)
    style_table_header(worksheet, reason_header_row, 1, len(reason_headers))

    source_reason = f"'Mənbə_Məlumat'!$N$2:$N${source_end_row}"
    reasons = sorted(data.loc[data["Status"].eq("Geri Qaytarılıb"), "Iade_Sebebi"].dropna().unique())
    reason_end_row = reason_header_row + len(reasons)
    for row_number, reason in enumerate(reasons, start=reason_header_row + 1):
        worksheet.cell(row_number, 1, reason)
        worksheet.cell(
            row_number,
            2,
            f'=SUMIFS({source_amount},{source_reason},A{row_number},{source_status},"Geri Qaytarılıb")',
        )
        worksheet.cell(
            row_number,
            3,
            f'=COUNTIFS({source_reason},A{row_number},{source_status},"Geri Qaytarılıb")',
        )
        worksheet.cell(row_number, 4, f"=B{row_number}/SUM(B{reason_header_row + 1}:B{reason_end_row})")
    format_data_region(worksheet, reason_header_row + 1, reason_end_row, len(reason_headers))
    add_excel_table(
        worksheet,
        "IadeSebebleri",
        f"A{reason_header_row}:D{reason_end_row}",
    )
    for row_number in range(reason_header_row + 1, reason_end_row + 1):
        worksheet.cell(row_number, 2).number_format = AZN_FORMAT
        worksheet.cell(row_number, 4).number_format = PERCENT_FORMAT

    worksheet.conditional_formatting.add(
        f"F{start_row + 1}:F{branch_end_row}",
        CellIsRule(
            operator="greaterThan",
            formula=["0.18"],
            fill=PatternFill("solid", fgColor=SOFT_RED),
            font=Font(color=CORAL, bold=True),
        ),
    )
    worksheet.freeze_panes = "A5"
    worksheet.sheet_view.showGridLines = False
    set_column_widths(worksheet)


def create_customer_sheet(workbook: Workbook, data: pd.DataFrame) -> None:
    """Ən yüksək iadə tezliyi və məbləği olan 20 müştərini sıralayır."""
    worksheet = workbook.create_sheet("Riskli_Musteriler")
    style_title(
        worksheet,
        "RİSKLİ MÜŞTƏRİLƏR — ƏN YÜKSƏK İADƏ GÖSTƏRİCİLƏRİ",
        "Sıralama əvvəlcə iadə tezliyinə, sonra iadə məbləğinə əsaslanır",
        7,
    )
    headers = [
        "Müştəri ID",
        "Müştərinin adı",
        "Əməliyyat sayı",
        "İadə sayı",
        "İadə məbləği (AZN)",
        "İadə faizi",
        "Son iadə tarixi",
    ]
    header_row = 4
    for column, header in enumerate(headers, start=1):
        worksheet.cell(header_row, column, header)
    style_table_header(worksheet, header_row, 1, len(headers))

    returned = data.loc[data["Status"].eq("Geri Qaytarılıb")].copy()
    customers = (
        data.groupby("Musteri_ID")
        .agg(
            Musteri_Ad_Soyad=("Musteri_Ad_Soyad", "first"),
            Emeliyyat_Sayi=("Emeliyyat_ID", "count"),
        )
        .join(
            returned.groupby("Musteri_ID").agg(
                Iade_Sayi=("Emeliyyat_ID", "count"),
                Iade_Meblegi=("Umumi_Mebleg_AZN", "sum"),
                Son_Iade_Tarixi=("Tarix", "max"),
            ),
            how="inner",
        )
        .reset_index()
    )
    customers["Iade_Faizi"] = customers["Iade_Sayi"] / customers["Emeliyyat_Sayi"]
    customers = customers.sort_values(
        ["Iade_Sayi", "Iade_Meblegi", "Iade_Faizi"],
        ascending=[False, False, False],
        kind="stable",
    ).head(20)

    for row_number, customer in enumerate(customers.itertuples(index=False), start=header_row + 1):
        values = [
            customer.Musteri_ID,
            customer.Musteri_Ad_Soyad,
            int(customer.Emeliyyat_Sayi),
            int(customer.Iade_Sayi),
            float(customer.Iade_Meblegi),
            float(customer.Iade_Faizi),
            customer.Son_Iade_Tarixi.to_pydatetime(),
        ]
        for column, value in enumerate(values, start=1):
            worksheet.cell(row_number, column, value)
        worksheet.cell(row_number, 5).number_format = AZN_FORMAT
        worksheet.cell(row_number, 6).number_format = PERCENT_FORMAT
        worksheet.cell(row_number, 7).number_format = DATE_FORMAT

    end_row = header_row + len(customers)
    format_data_region(worksheet, header_row + 1, end_row, len(headers))
    add_excel_table(worksheet, "RiskliMusteriler", f"A{header_row}:G{end_row}")
    worksheet.conditional_formatting.add(
        f"F{header_row + 1}:F{end_row}",
        CellIsRule(
            operator="greaterThan",
            formula=["0.18"],
            fill=PatternFill("solid", fgColor=SOFT_RED),
            font=Font(color=CORAL, bold=True),
        ),
    )
    worksheet.conditional_formatting.add(
        f"E{header_row + 1}:E{end_row}",
        DataBarRule(start_type="num", start_value=0, end_type="max", color=CORAL),
    )
    worksheet.freeze_panes = "A5"
    worksheet.sheet_view.showGridLines = False
    set_column_widths(worksheet)


def create_report() -> Path:
    """Məlumatları emal edir və idarəetmə hesabatını XLSX formatında saxlayır."""
    data = load_data()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    workbook.remove(workbook.active)
    source_end_row = len(data) + 1
    create_kpi_sheet(workbook, source_end_row)
    create_branch_and_reason_sheet(workbook, data, source_end_row)
    create_customer_sheet(workbook, data)
    prepare_source_sheet(workbook, data)

    workbook.calculation.fullCalcOnLoad = True
    workbook.calculation.forceFullCalc = True
    workbook.calculation.calcMode = "auto"
    workbook.properties.title = "Elektronika Satışı və İadələr üzrə Rəhbərlik Hesabatı"
    workbook.properties.subject = "Satış, gəlirlilik və iadə risklərinin təhlili"
    workbook.properties.creator = "Analitika komandası"
    workbook.active = 0
    workbook.save(REPORT_PATH)
    return REPORT_PATH


def main() -> None:
    report_path = create_report()
    print(f"Hesabat uğurla yaradıldı: {report_path}")
    print(f"Fayl ölçüsü: {report_path.stat().st_size:,} bayt")


if __name__ == "__main__":
    main()
