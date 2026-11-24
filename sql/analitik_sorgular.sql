-- ELEKTRONİKA SATIŞI VƏ GERİ QAYTARILMA ÜZRƏ ANALİTİK SORĞULAR
--
-- Uyğun verilənlər bazaları: Oracle Database və PostgreSQL.
-- Mənbə cədvəli: elektronika_satis_data
-- Mənbə sütunları: Emeliyyat_ID, Tarix, Musteri_ID, Musteri_Ad_Soyad,
-- Filial, Kateqoriya, Mehsul_Adi, Say, Vahid_Qiymet_AZN,
-- Umumi_Mebleg_AZN, Maya_Deyeri_AZN, Odenis_Novu, Status, Iade_Sebebi.
--
-- Hesablama qaydaları:
-- 1. Satış dövriyyəsi yalnız "Satılıb" statuslu əməliyyatların məbləğidir.
-- 2. İadə zərəri "Geri Qaytarılıb" statuslu əməliyyatların məbləğidir.
-- 3. Xalis dövriyyə satış dövriyyəsindən iadə zərərinin çıxılması ilə tapılır.
-- 4. Xalis mənfəət hesabında iadə olunan malın ilkin maya dəyəri
--    anbara geri qaytarılmış və bərpa oluna bilən dəyər kimi qəbul edilir.
--    Daşınma, təmir və digər iadə xərcləri mənbə məlumatlarında yoxdur.
-- 5. Faiz göstəriciləri faiz vahidində qaytarılır; məsələn, 16.0 = 16 faiz.
--
-- Qeyd: Mənbə cədvəlini icra etməzdən əvvəl müvafiq verilənlər bazasına
-- yükləyin. Tarix sütunu DATE və ya TIMESTAMP tipində olmalıdır.


-- 1. Ümumi dövriyyə, xalis gəlir və iadə zərəri
-- CTE vasitəsilə satış və iadə məbləğləri, həmçinin xalis mənfəət hesablanır.

WITH maliyye_gostericileri AS (
    SELECT
        SUM(
            CASE
                WHEN Status = 'Satılıb' THEN Umumi_Mebleg_AZN
                ELSE 0
            END
        ) AS satis_dovriyyesi,
        SUM(
            CASE
                WHEN Status = 'Satılıb' THEN Maya_Deyeri_AZN
                ELSE 0
            END
        ) AS satilan_mallarin_maya_deyeri,
        SUM(
            CASE
                WHEN Status = 'Geri Qaytarılıb' THEN Umumi_Mebleg_AZN
                ELSE 0
            END
        ) AS iade_zereri,
        SUM(
            CASE
                WHEN Status = 'Geri Qaytarılıb' THEN Maya_Deyeri_AZN
                ELSE 0
            END
        ) AS qaytarilan_mallarin_maya_deyeri
    FROM elektronika_satis_data
)
SELECT
    satis_dovriyyesi AS "Ümumi satış dövriyyəsi (AZN)",
    iade_zereri AS "İadə zərəri (AZN)",
    satis_dovriyyesi - iade_zereri AS "Xalis gəlir (AZN)",
    (satis_dovriyyesi - iade_zereri)
        - (satilan_mallarin_maya_deyeri - qaytarilan_mallarin_maya_deyeri)
        AS "Xalis mənfəət (AZN)",
    100.0 * iade_zereri / NULLIF(satis_dovriyyesi, 0)
        AS "Dövriyyəyə nisbətən iadə faizi"
FROM maliyye_gostericileri;


-- 2. Filiallar üzrə satış və geri qaytarılma faizi
-- İadə faizi filialdakı bütün əməliyyatlar arasında iadələrin payıdır.
-- Filiallar satış dövriyyəsinə görə sıralanır; bərabər nəticələr eyni yer alır.

WITH filial_gostericileri AS (
    SELECT
        Filial,
        SUM(
            CASE
                WHEN Status = 'Satılıb' THEN Umumi_Mebleg_AZN
                ELSE 0
            END
        ) AS satis_meblegi,
        SUM(
            CASE
                WHEN Status = 'Geri Qaytarılıb' THEN Umumi_Mebleg_AZN
                ELSE 0
            END
        ) AS iade_zereri,
        SUM(CASE WHEN Status = 'Satılıb' THEN 1 ELSE 0 END) AS satis_sayi,
        SUM(CASE WHEN Status = 'Geri Qaytarılıb' THEN 1 ELSE 0 END) AS iade_sayi,
        COUNT(*) AS emeliyyat_sayi
    FROM elektronika_satis_data
    GROUP BY Filial
)
SELECT
    Filial AS "Filial",
    satis_meblegi AS "Satış məbləği (AZN)",
    satis_sayi AS "Satış sayı",
    iade_zereri AS "İadə zərəri (AZN)",
    iade_sayi AS "İadə sayı",
    100.0 * iade_sayi / NULLIF(emeliyyat_sayi, 0) AS "İadə faizi",
    DENSE_RANK() OVER (ORDER BY satis_meblegi DESC) AS "Satış üzrə reytinq"
FROM filial_gostericileri
ORDER BY satis_meblegi DESC, Filial;


-- 3. Geri qaytarılma səbəblərinin Pareto təhlili
-- İadə zərəri səbəblər üzrə cəmlənir, ümumi zərərdə payı və
-- azalan məbləğ sırası ilə kumulyativ payı hesablanır.

WITH sebeb_meblegleri AS (
    SELECT
        Iade_Sebebi,
        SUM(Umumi_Mebleg_AZN) AS iade_zereri
    FROM elektronika_satis_data
    WHERE Status = 'Geri Qaytarılıb'
      AND Iade_Sebebi IS NOT NULL
    GROUP BY Iade_Sebebi
),
sebeb_paylari AS (
    SELECT
        Iade_Sebebi,
        iade_zereri,
        100.0 * iade_zereri / NULLIF(SUM(iade_zereri) OVER (), 0)
            AS umumi_zererde_pay
    FROM sebeb_meblegleri
)
SELECT
    Iade_Sebebi AS "İadə səbəbi",
    iade_zereri AS "İadə zərəri (AZN)",
    umumi_zererde_pay AS "Ümumi zərərdə payı (%)",
    SUM(umumi_zererde_pay) OVER (
        ORDER BY iade_zereri DESC, Iade_Sebebi
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS "Kumulyativ pay (%)"
FROM sebeb_paylari
ORDER BY iade_zereri DESC, Iade_Sebebi;


-- 4. Nağd və kredit ödənişlərində iadə riskinin müqayisəsi
-- Daxili kredit və taksit kartı "Kredit və taksit" qrupunda birləşdirilir.
-- Şərti aqreqasiya ilə satış, iadə və kredit təsdiqlənməməsi göstəriciləri
-- eyni nəticə cədvəlində təqdim olunur.

WITH odenis_qruplari AS (
    SELECT
        CASE
            WHEN Odenis_Novu = 'Nağd' THEN 'Nağd'
            ELSE 'Kredit və taksit'
        END AS odenis_qrupu,
        Status,
        Iade_Sebebi,
        Umumi_Mebleg_AZN
    FROM elektronika_satis_data
)
SELECT
    odenis_qrupu AS "Ödəniş qrupu",
    COUNT(*) AS "Əməliyyat sayı",
    SUM(CASE WHEN Status = 'Satılıb' THEN 1 ELSE 0 END) AS "Satış sayı",
    SUM(CASE WHEN Status = 'Geri Qaytarılıb' THEN 1 ELSE 0 END) AS "İadə sayı",
    100.0 * SUM(CASE WHEN Status = 'Geri Qaytarılıb' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0) AS "İadə riski (%)",
    SUM(
        CASE
            WHEN Status = 'Satılıb' THEN Umumi_Mebleg_AZN
            ELSE 0
        END
    ) AS "Satış məbləği (AZN)",
    SUM(
        CASE
            WHEN Status = 'Geri Qaytarılıb' THEN Umumi_Mebleg_AZN
            ELSE 0
        END
    ) AS "İadə zərəri (AZN)",
    SUM(
        CASE
            WHEN Iade_Sebebi = 'Kredit təsdiqlənmədi' THEN 1
            ELSE 0
        END
    ) AS "Kredit təsdiqlənmədiyinə görə iadə sayı"
FROM odenis_qruplari
GROUP BY odenis_qrupu
ORDER BY odenis_qrupu;


-- 5. Müştərilərin RFM məntiqi ilə seqmentasiyası
-- Tezlik satış əməliyyatlarının sayı, məbləğ xalis müştəri gəliri,
-- sonluq isə hesabat tarixindən son satışadək keçən gün sayı ilə ölçülür.
-- Riskli müştərilər VIP və sadiq müştərilərdən əvvəl müəyyən edilir.

WITH hesabat_tarixi AS (
    SELECT MAX(Tarix) AS son_emeliyyat_tarixi
    FROM elektronika_satis_data
),
musteri_gostericileri AS (
    SELECT
        Musteri_ID,
        MAX(Musteri_Ad_Soyad) AS musteri_adi,
        SUM(CASE WHEN Status = 'Satılıb' THEN 1 ELSE 0 END) AS satis_sayi,
        SUM(
            CASE
                WHEN Status = 'Satılıb' THEN Umumi_Mebleg_AZN
                ELSE 0
            END
        ) AS satis_meblegi,
        SUM(
            CASE
                WHEN Status = 'Geri Qaytarılıb' THEN Umumi_Mebleg_AZN
                ELSE 0
            END
        ) AS iade_meblegi,
        SUM(CASE WHEN Status = 'Geri Qaytarılıb' THEN 1 ELSE 0 END) AS iade_sayi,
        COUNT(*) AS emeliyyat_sayi,
        MAX(CASE WHEN Status = 'Satılıb' THEN Tarix ELSE NULL END)
            AS son_satis_tarixi
    FROM elektronika_satis_data
    GROUP BY Musteri_ID
),
rfm_gostericileri AS (
    SELECT
        m.Musteri_ID,
        m.musteri_adi,
        m.satis_sayi,
        m.satis_meblegi,
        m.iade_meblegi,
        m.iade_sayi,
        m.emeliyyat_sayi,
        m.satis_meblegi - m.iade_meblegi AS xalis_musteri_meblegi,
        CASE
            WHEN m.son_satis_tarixi IS NOT NULL THEN
                CAST(h.son_emeliyyat_tarixi AS DATE)
                    - CAST(m.son_satis_tarixi AS DATE)
            ELSE NULL
        END AS son_satisdan_gun_sayi,
        100.0 * m.iade_sayi / NULLIF(m.emeliyyat_sayi, 0) AS iade_faizi
    FROM musteri_gostericileri m
    CROSS JOIN hesabat_tarixi h
)
SELECT
    Musteri_ID AS "Müştəri ID",
    musteri_adi AS "Müştəri adı",
    satis_sayi AS "Satış sayı",
    satis_meblegi AS "Satış məbləği (AZN)",
    iade_sayi AS "İadə sayı",
    iade_meblegi AS "İadə məbləği (AZN)",
    xalis_musteri_meblegi AS "Xalis müştəri məbləği (AZN)",
    son_satisdan_gun_sayi AS "Son satışdan keçən gün sayı",
    iade_faizi AS "İadə faizi",
    CASE
        WHEN iade_sayi >= 2
          OR (emeliyyat_sayi >= 3 AND iade_faizi >= 30)
            THEN 'Riskli / Tez-tez İadə Edən Müştəri'
        WHEN satis_sayi >= 5
          AND xalis_musteri_meblegi >= 5000
          AND son_satisdan_gun_sayi <= 90
            THEN 'VIP Müştəri'
        WHEN satis_sayi >= 3
          AND son_satisdan_gun_sayi <= 180
            THEN 'Sadiq Müştəri'
        ELSE 'Digər Müştəri'
    END AS "Müştəri seqmenti"
FROM rfm_gostericileri
ORDER BY iade_sayi DESC, iade_meblegi DESC, xalis_musteri_meblegi DESC;


-- 6. Aylıq satış və iadə dinamikası
-- Hər ay üçün satış və iadə məbləğləri hesablanır.
-- LAG əvvəlki mövcud ayın göstəricisini, dəyişiklik faizi isə
-- əvvəlki ayla müqayisədə artım və ya azalmanı göstərir.
-- Sıfır və ya olmayan əvvəlki göstəricidə faiz NULL qaytarılır.

WITH ayliq_gostericiler AS (
    SELECT
        EXTRACT(YEAR FROM Tarix) AS il,
        EXTRACT(MONTH FROM Tarix) AS ay,
        MIN(Tarix) AS ayin_tarixi,
        SUM(
            CASE
                WHEN Status = 'Satılıb' THEN Umumi_Mebleg_AZN
                ELSE 0
            END
        ) AS satis_meblegi,
        SUM(
            CASE
                WHEN Status = 'Geri Qaytarılıb' THEN Umumi_Mebleg_AZN
                ELSE 0
            END
        ) AS iade_zereri,
        SUM(CASE WHEN Status = 'Satılıb' THEN 1 ELSE 0 END) AS satis_sayi,
        SUM(CASE WHEN Status = 'Geri Qaytarılıb' THEN 1 ELSE 0 END) AS iade_sayi
    FROM elektronika_satis_data
    GROUP BY EXTRACT(YEAR FROM Tarix), EXTRACT(MONTH FROM Tarix)
),
evvelki_ay_gostericileri AS (
    SELECT
        il,
        ay,
        ayin_tarixi,
        satis_meblegi,
        iade_zereri,
        satis_sayi,
        iade_sayi,
        LAG(satis_meblegi) OVER (ORDER BY il, ay) AS evvelki_ay_satisi,
        LAG(iade_zereri) OVER (ORDER BY il, ay) AS evvelki_ay_iadesi
    FROM ayliq_gostericiler
)
SELECT
    TO_CHAR(ayin_tarixi, 'YYYY-MM') AS "Ay",
    satis_sayi AS "Satış sayı",
    satis_meblegi AS "Satış məbləği (AZN)",
    evvelki_ay_satisi AS "Əvvəlki ayın satış məbləği (AZN)",
    100.0 * (satis_meblegi - evvelki_ay_satisi)
        / NULLIF(evvelki_ay_satisi, 0) AS "Satış dəyişikliyi (%)",
    iade_sayi AS "İadə sayı",
    iade_zereri AS "İadə zərəri (AZN)",
    evvelki_ay_iadesi AS "Əvvəlki ayın iadə zərəri (AZN)",
    100.0 * (iade_zereri - evvelki_ay_iadesi)
        / NULLIF(evvelki_ay_iadesi, 0) AS "İadə dəyişikliyi (%)"
FROM evvelki_ay_gostericileri
ORDER BY il, ay;
