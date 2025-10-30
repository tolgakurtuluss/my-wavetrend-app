# WaveTrend Pro

**BIST 100 & Global Hisse Analizi için WaveTrend Strateji Aracı**

![WaveTrend Pro](https://via.placeholder.com/800x400.png?text=WaveTrend+Pro)  
*WaveTrend göstergesi ile AL/SAT sinyalleri ve portföy performansı analizi*

---

## Özellikler

- **BIST 100 / Amerika hisseleri + şirket adları** (AAPL, BTC-USD, THYAO.IS vb.)
- **WaveTrend + Awesome Oscillator** görselleştirme
- **Backtest & Portföy Büyümesi** grafiği
- **İşlem geçmişi & CSV indirme**
- **Tamamen ücretsiz & açık kaynak**

---

## Canlı Demo

[WaveTrend Pro'yu Deneyin](https://my-wavetrend-app.streamlit.app/)

---

## Kurulum (Yerel)

```bash
# 1. Repoyu klonla
git clone https://github.com/kullanici/wavetrend-pro.git
cd wavetrend-pro

# 2. Sanal ortam oluştur
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Gerekli paketleri kur
pip install -r requirements.txt

# 4. Uygulamayı başlat
streamlit run streamlit_app.py
