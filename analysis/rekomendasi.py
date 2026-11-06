import pandas as pd
from analysis.moving_average import calculate_moving_average
from analysis.apriori import perform_apriori

def get_restock_recommendations(df, window=12, min_support=0.005, min_confidence=0.5):
    """
    Integrasi Model Penelitian Skripsi:
    - Moving Average: Sebagai pemicu (trigger) evaluasi kebutuhan restok berdasarkan proyeksi permintaan minggu berikutnya.
    - Apriori: Menganalisis pola pembelian bersama untuk memberikan rekomendasi produk komplementer (mencegah cross-stockout).
    """
    if df.empty:
        return None

    # 1. Hitung Moving Average (Pemicu)
    ma_result = calculate_moving_average(df, window=window)
    if not ma_result:
        return None
        
    ma_items = ma_result['items']
    validation = ma_result['validation']

    # 2. Jalankan Apriori (Pola Asosiasi)
    frequent_itemsets, rules, apriori_stats = perform_apriori(
        df, min_support=min_support, min_threshold=min_confidence, return_stats=True
    )

    # Siapkan dictionary rules berdasarkan antecedent untuk pencarian cepat
    rules_map = {}
    rules_list = []
    if rules is not None and not rules.empty:
        for _, r in rules.iterrows():
            ant_items = list(r['antecedents'])
            con_items = list(r['consequents'])
            r_dict = {
                'antecedents': ', '.join(ant_items),
                'consequents': ', '.join(con_items),
                'support': round(float(r['support']), 4),
                'confidence': round(float(r['confidence']) * 100, 1),
                'lift': round(float(r['lift']), 3)
            }
            rules_list.append(r_dict)
            
            # Petakan setiap antecedent individual
            for ant in ant_items:
                if ant not in rules_map:
                    rules_map[ant] = []
                rules_map[ant].append(r_dict)

    # 3. Integrasi: Evaluasi Kebutuhan Restok per Produk
    recommendations = []
    total_memicu = 0
    total_dengan_pendamping = 0
    total_mandiri = 0
    total_tidak_memicu = 0

    for item in ma_items:
        prod_name = item['produk']
        pred_qty = item['prediction']
        ma_val = item['moving_avg']
        last_sales = item['last_week_sales']

        # Logika Pemicu (Trigger)
        if pred_qty > 0:
            is_triggered = True
            total_memicu += 1
            trigger_status = "Indikasi Restok"
            trigger_badge = "danger"
            trigger_reason = f"Terindikasi kebutuhan restok berdasarkan proyeksi permintaan {pred_qty} unit (Rata-rata {window} minggu: {ma_val} unit)."
        else:
            is_triggered = False
            total_tidak_memicu += 1
            trigger_status = "Belum Terindikasi"
            trigger_badge = "secondary"
            trigger_reason = "Belum terindikasi kebutuhan restok karena proyeksi permintaan bernilai 0 unit berdasarkan tren historis."

        # Evaluasi Keterkaitan Apriori
        associated_rules = rules_map.get(prod_name, [])

        if is_triggered:
            if associated_rules:
                total_dengan_pendamping += 1
                rec_type = "Restok + Pendamping"
                rec_badge = "primary"
                
                # Buat deskripsi produk komplementer
                pendamping_desc = []
                for ar in associated_rules:
                    pendamping_desc.append(
                        f"{ar['consequents']} (Confidence: {ar['confidence']}%, Lift: {ar['lift']})"
                    )
                action_text = (
                    f"Terindikasi kebutuhan restok utama berdasarkan proyeksi permintaan {pred_qty} unit. "
                    f"Pola asosiasi Apriori menunjukkan pembeli produk ini berpeluang membeli produk pendamping: "
                    f"{'; '.join(pendamping_desc)}. Disarankan menyinkronkan pengadaan produk pendamping untuk memitigasi cross-stockout "
                    f"(Catatan: konfirmasi volume pengadaan riil memerlukan verifikasi stok gudang aktual)."
                )
            else:
                total_mandiri += 1
                rec_type = "Restok Mandiri"
                rec_badge = "info"
                action_text = (
                    f"Terindikasi kebutuhan restok berdasarkan proyeksi permintaan {pred_qty} unit. "
                    f"Tidak terdeteksi produk pendamping yang memenuhi ambang batas asosiasi Apriori "
                    f"(Catatan: konfirmasi volume pengadaan riil memerlukan verifikasi stok gudang aktual)."
                )
        else:
            rec_type = "Tunda Pengadaan"
            rec_badge = "light"
            action_text = "Belum terindikasi kebutuhan pengadaan stok tambahan untuk minggu depan berdasarkan pola historis."

        recommendations.append({
            'produk': prod_name,
            'last_week_sales': last_sales,
            'moving_avg': ma_val,
            'prediction': pred_qty,
            'is_triggered': is_triggered,
            'trigger_status': trigger_status,
            'trigger_badge': trigger_badge,
            'trigger_reason': trigger_reason,
            'rec_type': rec_type,
            'rec_badge': rec_badge,
            'action_text': action_text,
            'associated_rules': associated_rules
        })

    # Urutkan: Produk yang memicu restok dan memiliki rekomendasi pendamping di atas, lalu yang restok mandiri
    recommendations.sort(key=lambda x: (not x['is_triggered'], len(x['associated_rules']) == 0, -x['prediction']))

    summary = {
        'total_products': len(ma_items),
        'total_memicu': total_memicu,
        'total_dengan_pendamping': total_dengan_pendamping,
        'total_mandiri': total_mandiri,
        'total_tidak_memicu': total_tidak_memicu
    }

    return {
        'recommendations': recommendations,
        'summary': summary,
        'validation': validation,
        'apriori_stats': apriori_stats,
        'rules': rules_list
    }
