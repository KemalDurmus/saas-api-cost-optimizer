import pandas as pd
import io
import base64
import matplotlib.pyplot as plt
import seaborn as sns

def parse_cost_data(csv_string):
    """
    CSV string'i ayrıştırır ve bir pandas DataFrame'e dönüştürür.
    Beklenen format: Servis,Tarih,Kullanım,Maliyet
    """
    if not csv_string.strip():
        raise ValueError("Maliyet verisi boş olamaz.")
    try:
        df = pd.read_csv(io.StringIO(csv_string))
        if not all(col in df.columns for col in ['Servis', 'Tarih', 'Kullanım', 'Maliyet']):
            raise ValueError("CSV verisi 'Servis', 'Tarih', 'Kullanım', 'Maliyet' sütunlarını içermelidir.")
        
        df['Tarih'] = pd.to_datetime(df['Tarih'])
        df['Maliyet'] = pd.to_numeric(df['Maliyet'])
        df['Kullanım'] = pd.to_numeric(df['Kullanım'])
        return df
    except Exception as e:
        raise ValueError(f"Veri ayrıştırma hatası: {e}. Lütfen formatı kontrol edin.")

def analyze_costs(df):
    """
    Maliyet verilerini analiz eder ve özet istatistikler, anormallikler ve öneriler döndürür.
    """
    total_cost = df['Maliyet'].sum()
    
    cost_by_service = df.groupby('Servis')['Maliyet'].sum().sort_values(ascending=False).reset_index()
    cost_by_service.columns = ['Servis', 'Toplam Maliyet']

    # Anormallik tespiti (basit bir örnek: ortalamanın çok üzerindeki maliyetler)
    anomalies = []
    if not df.empty and df['Maliyet'].sum() > 0:
        avg_cost_per_entry = df['Maliyet'].mean()
        # Ortalama maliyetin 3 katından fazla olan ve en az 100 TL olan girişleri anormallik olarak işaretle
        high_cost_threshold = avg_cost_per_entry * 3 

        for index, row in df.iterrows():
            if row['Maliyet'] > high_cost_threshold and row['Maliyet'] > 100: 
                anomalies.append(f"{row['Servis']} hizmetinde {row['Tarih'].strftime('%Y-%m-%d')} tarihinde anormal yüksek maliyet ({row['Maliyet']:.2f} TL) tespit edildi. Kullanım: {row['Kullanım']}")
        
        if not anomalies:
            anomalies.append("Belirgin bir anormallik tespit edilmedi, ancak maliyetleri düzenli olarak gözden geçirin.")
    else:
        anomalies.append("Analiz edilecek maliyet verisi bulunamadı veya toplam maliyet sıfır.")

    # Optimizasyon önerileri
    suggestions = [
        "En yüksek maliyetli hizmetleri (yukarıdaki tabloya bakın) gözden geçirin ve kullanımını optimize etme yollarını arayın.",
        "Kullanılmayan veya az kullanılan SaaS aboneliklerini iptal etmeyi düşünün.",
        "API çağrılarınızı önbelleğe alarak veya toplu işlemler yaparak kullanım maliyetlerini azaltın.",
        "Webhook tetikleyicilerini ve otomasyon akışlarını gereksiz çalıştırmaları önlemek için optimize edin.",
        "Kullanım limitlerini ve fiyatlandırma katmanlarını düzenli olarak kontrol edin."
    ]
    
    if not cost_by_service.empty:
        top_service = cost_by_service.iloc[0]['Servis']
        suggestions.insert(0, f"'{top_service}' hizmetinin kullanımını ve maliyetini detaylı inceleyin. Bu, en yüksek maliyetli hizmetinizdir.")

    return {
        'total_cost': total_cost,
        'cost_by_service': cost_by_service.to_dict('records'),
        'anomalies': anomalies,
        'suggestions': suggestions
    }

def generate_cost_plot(df):
    """
    Maliyet dağılımını gösteren bir grafik oluşturur ve base64 kodlu PNG olarak döndürür.
    """
    if df.empty or df['Maliyet'].sum() == 0:
        return None

    cost_by_service = df.groupby('Servis')['Maliyet'].sum().sort_values(ascending=False)

    sns.set_theme(style="whitegrid") # Modern ve temiz bir stil
    plt.figure(figsize=(10, 6))
    sns.barplot(x=cost_by_service.index, y=cost_by_service.values, palette="viridis")
    plt.title('Servislere Göre Toplam Maliyet Dağılımı', fontsize=16)
    plt.xlabel('Servis', fontsize=12)
    plt.ylabel('Toplam Maliyet (TL)', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png')
    img_buffer.seek(0)
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
    plt.close() # Grafiği kapatarak bellek sızıntısını önle
    return img_base64

def get_sample_data():
    """
    Örnek maliyet verisi döndürür.
    """
    return """Servis,Tarih,Kullanım,Maliyet
OpenAI,2023-10-01,150000,350.75
Zapier,2023-10-05,5000,49.99
Clerk,2023-10-10,1200,75.00
Stripe,2023-10-12,10000,120.50
CRM_X,2023-10-15,500,99.00
OpenAI,2023-10-20,200000,480.20
Zapier,2023-10-22,6000,49.99
AWS_Lambda,2023-10-25,1000000,250.00
CRM_X,2023-10-28,550,99.00
Google_Maps_API,2023-11-01,50000,80.00
OpenAI,2023-11-05,300000,720.50
Zapier,2023-11-08,7000,49.99
Clerk,2023-11-10,1300,75.00
Stripe,2023-11-12,11000,130.25
CRM_X,2023-11-15,600,99.00
AWS_Lambda,2023-11-18,1200000,300.00
OpenAI,2023-11-20,400000,980.00
Google_Maps_API,2023-11-25,60000,95.00
"""