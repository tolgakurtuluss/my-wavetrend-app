import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
from io import StringIO

# ==============================
#   BIST 100 + ŞİRKET ADLARI ÇEK
# ==============================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_bist100_with_names():
    try:
        url = "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/Temel-Degerler-Ve-Oranlar.aspx?endeks=09#page-1"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        html_io = StringIO(response.text)
        df = pd.read_html(html_io, flavor='bs4')[2]
        df = df[['Kod', 'Ad']]  # Sadece Kod ve Ad
        df['Kod'] = df['Kod'] + ".IS"
        df['Label'] = df.apply(lambda row: f"{row['Kod']} - {row['Ad']}", axis=1)
        return dict(zip(df['Kod'], df['Label']))
    except Exception as e:
        return None

def clear_bist_cache():
    fetch_bist100_with_names.clear()

# ==============================
#   YARDIMCI FONKSİYONLAR
# ==============================
def ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def sma(series, span):
    return series.rolling(window=span).mean()

# ==============================
#   WAVETREND GÖSTERGESİ
# ==============================
@st.cache_data(show_spinner=False)
def get_wt_data(ticker, period):
    data = yf.download(ticker, period=period, progress=False, auto_adjust=True)
    if data.empty:
        return None, None, None

    n1, n2 = 10, 21
    data['hlc3'] = (data['High'] + data['Low'] + data['Close']) / 3
    data['esa']  = ema(data['hlc3'], n1)
    data['d']    = ema((data['hlc3'] - data['esa']).abs(), n1)
    data['ci']   = (data['hlc3'] - data['esa']) / (0.015 * data['d'])
    data['wt1']  = ema(data['ci'], n2)
    data['wt2']  = sma(data['wt1'], 4)
    hl2 = (data['High'] + data['Low']) / 2
    data['ao'] = ema(hl2, 5) - ema(hl2, 34)

    buy  = (data['wt1'].shift(1) < data['wt2'].shift(1)) & (data['wt1'] > data['wt2'])
    sell = (data['wt1'].shift(1) > data['wt2'].shift(1)) & (data['wt1'] < data['wt2'])

    return data, buy, sell

# ==============================
#   BACKTEST
# ==============================
@st.cache_data(show_spinner=False)
def backtest_strategy(data, buy_signals, sell_signals, initial_capital):
    if data is None:
        return pd.DataFrame(), initial_capital, pd.DataFrame()

    capital = float(initial_capital)
    position_price = None
    shares = 0.0
    trades = []
    portfolio = []

    for i in range(len(data)):
        date = data.index[i]
        price = float(data['Close'].iloc[i])

        if buy_signals.iloc[i] and position_price is None:
            position_price = price
            shares = capital / price
            trades.append({
                'Tarih': date.strftime('%Y-%m-%d'),
                'İşlem': 'AL',
                'Fiyat': round(price, 4),
                'Yatırım': round(capital, 2)
            })

        elif sell_signals.iloc[i] and position_price is not None:
            proceeds = shares * price
            capital = proceeds
            trades.append({
                'Tarih': date.strftime('%Y-%m-%d'),
                'İşlem': 'SAT',
                'Fiyat': round(price, 4),
                'Yatırım': round(capital, 2)
            })
            position_price = None
            shares = 0.0

        current_value = capital if position_price is None else shares * price
        portfolio.append({
            'Tarih': date.strftime('%Y-%m-%d'),
            'Değer': round(current_value, 2)
        })

    trades_df = pd.DataFrame(trades)
    portfolio_df = pd.DataFrame(portfolio)
    final_value = float(portfolio_df['Değer'].iloc[-1]) if not portfolio_df.empty else float(initial_capital)

    return trades_df, final_value, portfolio_df

# ==============================
#   STREAMLIT UI
# ==============================
st.set_page_config(page_title="WaveTrend Pro", layout="wide", initial_sidebar_state="expanded")
st.markdown("<h1 style='text-align: center;'>WaveTrend Pro</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666;'>BIST 100 & Global Hisse Analizi</p>", unsafe_allow_html=True)

# ------------------- SİDEBAR -------------------
with st.sidebar:
    st.header("Analiz Ayarları")

    col_btn1, col_btn2 = st.columns([3, 1])
    with col_btn1:
        refresh_bist = st.button("BIST 100 Yenile", type="secondary", use_container_width=True)
    with col_btn2:
        if st.button("Temizle", key="clear_cache"):
            clear_bist_cache()
            st.success("Cache temizlendi!")

    # Şirket adları
    stock_names = None
    if 'bist_names' not in st.session_state:
        st.session_state.bist_names = None

    if refresh_bist:
        with st.spinner("BIST 100 + Şirket Adları yükleniyor..."):
            stock_names = fetch_bist100_with_names()
            if stock_names:
                st.session_state.bist_names = stock_names
                st.success(f"{len(stock_names)} hisse (adlarıyla) yüklendi!")
            else:
                st.session_state.bist_names = None
                st.error("Yükleme başarısız. Manuel giriş kullanın.")

    elif st.session_state.bist_names is not None:
        stock_names = st.session_state.bist_names
        st.info(f"Kullanımda: {len(stock_names)} hisse")

    # Hisse Seçimi
    ticker_input = st.text_input("Hisse Kodu (Manuel)", value="THYAO.IS", help="Örn: AAPL, BTC-USD")

    if stock_names:
        selected_label = st.selectbox(
            "veya BIST 100'den seç",
            options=[""] + list(stock_names.values()),
            format_func=lambda x: x if x else "— Seçiniz —"
        )
        ticker = next((k for k, v in stock_names.items() if v == selected_label), None) if selected_label else ticker_input.upper()
    else:
        st.info("BIST 100 listesi yok. Sadece manuel giriş aktif.")
        ticker = ticker_input.upper()

    period = st.selectbox("Zaman Aralığı", 
                          ["5d","1mo","3mo","6mo","1y","2y","3y","5y","max"], 
                          index=6)

    initial_capital = st.number_input("Başlangıç Sermayesi", min_value=1000, value=10000, step=1000, format="%d")
    initial_capital = float(initial_capital)

    st.markdown("---")
    st.caption("WaveTrend (n1=10, n2=21) | Veri: Yahoo Finance")

# ------------------- ANA İÇERİK -------------------
if st.button("Analizi Başlat", type="primary", use_container_width=True):
    with st.spinner("Veriler analiz ediliyor..."):
        data, buy_sig, sell_sig = get_wt_data(ticker, period)
        
        if data is None:
            st.error(f"`{ticker}` için veri alınamadı. Kodu kontrol edin.")
        else:
            trades_df, final_value, portfolio_df = backtest_strategy(data, buy_sig, sell_sig, initial_capital)
            total_return = ((final_value - initial_capital) / initial_capital) * 100

            tab1, tab2 = st.tabs(["Gösterge & Sinyaller", "Performans & Portföy"])

            # --- TAB 1 ---
            with tab1:
                col1, col2 = st.columns([3, 1])
                with col1:
                    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9))

                    ax1.plot(data.index, data['wt1'], label='WT1', color='#00ff88', linewidth=1.8)
                    ax1.plot(data.index, data['wt2'], label='WT2', color='#ff4444', linewidth=1.8)
                    ax1.axhline(45, color='red', linestyle='--', alpha=0.6)
                    ax1.axhline(-45, color='green', linestyle='--', alpha=0.6)
                    ax1.axhline(53, color='red', linestyle=':', alpha=0.6)
                    ax1.axhline(-53, color='green', linestyle=':', alpha=0.6)

                    ax1.scatter(data.index[buy_sig], data['wt1'][buy_sig], 
                               color='lime', s=100, marker='^', label='AL', zorder=5, edgecolors='black', linewidth=0.5)
                    ax1.scatter(data.index[sell_sig], data['wt1'][sell_sig], 
                               color='red', s=100, marker='v', label='SAT', zorder=5, edgecolors='black', linewidth=0.5)

                    # Şirket adını başlıkta göster
                    company_name = stock_names.get(ticker, ticker) if stock_names else ticker
                    ax1.set_title(f"WaveTrend – {company_name}", fontsize=14, pad=15)
                    ax1.set_ylabel("WT")
                    ax1.legend(frameon=True, fancybox=True, shadow=True)
                    ax1.grid(True, alpha=0.3)

                    colors = np.where(data['ao'] > 0, '#00c853', '#d50000')
                    ax2.bar(data.index, data['ao'], color=colors, alpha=0.7, width=0.8)
                    ax2.axhline(0, color='white', linewidth=1)
                    ax2.set_title("Awesome Oscillator", fontsize=12)
                    ax2.set_ylabel("AO")
                    ax2.grid(True, alpha=0.3)

                    plt.tight_layout()
                    st.pyplot(fig)

                with col2:
                    st.markdown("### Sinyal Özeti")
                    st.metric("AL", int(buy_sig.sum()))
                    st.metric("SAT", int(sell_sig.sum()))
                    st.metric("Toplam", int(buy_sig.sum() + sell_sig.sum()))

            # --- TAB 2 ---
            with tab2:
                col1, col2 = st.columns([1, 2])

                with col1:
                    st.markdown("### Strateji Sonucu")
                    c1, c2 = st.columns(2)
                    c1.metric("Başlangıç", f"{initial_capital:,.0f} TL")
                    c2.metric("Son Değer", f"{final_value:,.2f} TL")

                    kar_zarar = final_value - initial_capital
                    st.metric("Kar/Zarar", f"{kar_zarar:,.2f} TL", f"%{total_return:+.2f}")

                    if not trades_df.empty:
                        st.markdown("### İşlemler")
                        display_df = trades_df.copy()
                        display_df['Fiyat'] = display_df['Fiyat'].map("{:.4f}".format)
                        display_df['Yatırım'] = display_df['Yatırım'].map("{:,.2f}".format)
                        st.dataframe(display_df, use_container_width=True)

                        csv = display_df.to_csv(index=False).encode('utf-8')
                        st.download_button("CSV İndir", csv, f"{ticker}_{period}.csv", "text/csv")
                    else:
                        st.info("Sinyal yok.")

                with col2:
                    st.markdown("### Portföy Büyümesi")
                    if not portfolio_df.empty:
                        fig2, ax = plt.subplots(figsize=(12, 6))
                        ax.fill_between(portfolio_df['Tarih'], portfolio_df['Değer'], initial_capital,
                                        where=portfolio_df['Değer'] >= initial_capital,
                                        color='#00ff88', alpha=0.3, interpolate=True)
                        ax.fill_between(portfolio_df['Tarih'], portfolio_df['Değer'], initial_capital,
                                        where=portfolio_df['Değer'] < initial_capital,
                                        color='#ff4444', alpha=0.3, interpolate=True)
                        ax.plot(portfolio_df['Tarih'], portfolio_df['Değer'], color='#0066ff', linewidth=2.5)
                        ax.axhline(initial_capital, color='gray', linestyle='--', linewidth=1.5)

                        ax.set_title(f"Portföy – {company_name}")
                        ax.set_ylabel("Değer (TL)")
                        ax.grid(True, alpha=0.3)
                        plt.xticks(rotation=45)
                        plt.tight_layout()
                        st.pyplot(fig2)
                    else:
                        st.info("Veri yok.")

else:
    st.info("Lütfen hisse seçip **'Analizi Başlat'** butonuna basın.")
    st.markdown("### Kullanım")
    st.markdown("""
    - **BIST 100 Yenile** → Şirket adlarıyla birlikte yükler  
    - Çalışmazsa **manuel giriş** kullanın  
    - Zaman aralığı ve sermaye seçin  
    - **Analizi Başlat**  
    """)
