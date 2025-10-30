import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# ==============================
#   UYGULAMA AYARLARI
# ==============================
st.set_page_config(
    page_title="WaveTrend Pro",
    page_icon="chart_with_upwards_trend",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/tolgakurtuluss/my-wavetrend-app",
        "Report a bug": "https://github.com/tolgakurtuluss/my-wavetrend-app/issues",
        "About": "# WaveTrend Pro\nBIST 100 & Global Hisse Analizi",
    },
)

# ==============================
#   STİL & TEMA
# ==============================
st.markdown(
    """
<style>
    .main > div {padding-top: 2rem;}
    .stButton>button {width: 100%; height: 3rem; font-weight: bold;}
    .metric-card {background-color: #f8f9fa; padding: 1rem; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);}
    .stTabs [data-baseweb="tab-list"] {gap: 1rem;}
    .stTabs [data-baseweb="tab"] {height: 3rem; padding: 0 1.5rem; font-weight: 600;}
</style>
""",
    unsafe_allow_html=True,
)

# ==============================
#   BAŞLIK
# ==============================
col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    st.markdown(
        "<h1 style='text-align: center; color: #1E88E5;'>WaveTrend Pro</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; color: #666; font-size: 1.1rem;'>BIST 100 & Global Hisse Analizi</p>",
        unsafe_allow_html=True,
    )


# ==============================
#   BIST 100 LİSTESİ
# ==============================
@st.cache_data
def get_bist100_stocks():
    try:
        df = pd.read_json(
            "https://raw.githubusercontent.com/tolgakurtuluss/my-wavetrend-app/refs/heads/main/listofstocks.json"
        )
        stocks = df["stockname"].dropna().unique().tolist()
        return sorted(stocks)
    except Exception as e:
        st.error(f"JSON dosyası okunamadı: {e}")
        return ["THYAO.IS"]  # fallback


bist_stocks = get_bist100_stocks()


# ==============================
#   YARDIMCI FONKSİYONLAR
# ==============================
def ema(series, span):
    return series.ewm(span=span, adjust=False).mean()


def sma(series, span):
    return series.rolling(window=span).mean()


# ==============================
#   WAVETREND & AO
# ==============================
@st.cache_data(show_spinner=False)
def get_wt_data(ticker, period):
    data = yf.download(ticker, period=period, auto_adjust=False)
    if data.empty:
        return None, None, None

    n1, n2 = 10, 21
    data["hlc3"] = (data["High"] + data["Low"] + data["Close"]) / 3
    data["esa"] = ema(data["hlc3"], n1)
    data["d"] = ema(abs(data["hlc3"] - data["esa"]), n1)
    data["ci"] = (data["hlc3"] - data["esa"]) / (0.015 * data["d"])
    data["wt1"] = ema(data["ci"], n2)
    data["wt2"] = sma(data["wt1"], 4)
    data["ao"] = ema((data["High"] + data["Low"]) / 2, 5) - ema(
        (data["High"] + data["Low"]) / 2, 34
    )

    buy = (data["wt1"].shift(1) < data["wt2"].shift(1)) & (data["wt1"] > data["wt2"])
    sell = (data["wt1"].shift(1) > data["wt2"].shift(1)) & (data["wt1"] < data["wt2"])

    return data, buy, sell


# ==============================
#   BACKTEST
# ==============================
@st.cache_data(show_spinner=False)
def backtest_strategy(data, buy_signals, sell_signals, initial_capital):
    if data is None:
        return pd.DataFrame(), initial_capital, pd.DataFrame()

    capital = float(initial_capital)
    position_price = shares = 0.0
    trades = portfolio = []

    for i, (date, row) in enumerate(data.iterrows()):
        price = float(row["Close"].iloc[0])
        current_value = capital if shares == 0 else shares * price

        if buy_signals.iloc[i] and shares == 0:
            shares = capital / price
            capital = 0
            trades.append(
                {
                    "Tarih": date.strftime("%Y-%m-%d"),
                    "İşlem": "AL",
                    "Fiyat": round(price, 4),
                    "Yatırım": round(shares * price, 2),
                }
            )

        elif sell_signals.iloc[i] and shares > 0:
            capital = shares * price
            shares = 0
            trades.append(
                {
                    "Tarih": date.strftime("%Y-%m-%d"),
                    "İşlem": "SAT",
                    "Fiyat": round(price, 4),
                    "Yatırım": round(capital, 2),
                }
            )

        portfolio.append(
            {"Tarih": date.strftime("%Y-%m-%d"), "Değer": round(current_value, 2)}
        )

    trades_df = pd.DataFrame(trades)
    portfolio_df = pd.DataFrame(portfolio)
    final_value = (
        portfolio_df["Değer"].iloc[-1] if not portfolio_df.empty else initial_capital
    )

    return trades_df, final_value, portfolio_df


# ==============================
#   MEVCUT DURUM
# ==============================
@st.cache_data(show_spinner=False)
def get_current_info(ticker):
    try:
        info = yf.Ticker(ticker).info
        return {
            "Şirket": info.get("longName") or info.get("shortName") or ticker,
            "Fiyat": info.get("regularMarketPrice") or info.get("previousClose"),
            "Değişim (%)": info.get("regularMarketChangePercent"),
            "Hacim": info.get("regularMarketVolume"),
            "PiyConf": info.get("marketCap"),
            "52H Yüksek": info.get("fiftyTwoWeekHigh"),
            "52H Düşük": info.get("fiftyTwoWeekLow"),
        }
    except:
        return None


# ==============================
#   SİDEBAR
# ==============================
with st.sidebar:
    st.markdown("WaveTrend Pro")
    st.markdown("---")
    st.markdown("### Analiz Ayarları")

    ticker = st.selectbox(
        "Hisse Kodu",
        options=[""] + bist_stocks,
        format_func=lambda x: "— Seçiniz —" if not x else x,
        help="Hisse listesinden seçin",
    )
    if not ticker:
        ticker = "THYAO.IS"

    period = st.selectbox(
        "Zaman Aralığı",
        ["5d", "1mo", "3mo", "6mo", "1y", "2y", "3y", "5y", "max"],
        index=7,
    )
    initial_capital = st.number_input(
        "Başlangıç Sermayesi (₺)", 1000, 1_000_000, 10_000, 1000
    )

    st.markdown("---")
    st.caption("WaveTrend (n1=10, n2=21) • Veri: Yahoo Finance")

# ==============================
#   ANA İÇERİK
# ==============================
if st.button("Analizi Başlat", type="primary", width="stretch"):
    with st.spinner("Veriler çekiliyor ve analiz ediliyor..."):
        data, buy_sig, sell_sig = get_wt_data(ticker, period)
        current_info = get_current_info(ticker)

        if data is None or data.empty:
            st.error(f"`{ticker}` için veri alınamadı.")
        else:
            trades_df, final_value, portfolio_df = backtest_strategy(
                data, buy_sig, sell_sig, initial_capital
            )
            total_return = ((final_value - initial_capital) / initial_capital) * 100

            tab1, tab2, tab3 = st.tabs(["Mevcut Durum", "Performans", "WaveTrend"])

            # === TAB 1: MEVCUT DURUM ===
            with tab1:
                if current_info:
                    st.markdown(f"### {current_info['Şirket']}")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric(
                            "Fiyat",
                            (
                                f"{current_info['Fiyat']:,.2f} ₺"
                                if current_info["Fiyat"]
                                else "N/A"
                            ),
                            (
                                f"%{current_info['Değişim (%)']:+.2f}"
                                if current_info["Değişim (%)"]
                                else None
                            ),
                        )
                    with c2:
                        st.metric(
                            "Hacim",
                            (
                                f"{current_info['Hacim']:,.0f}"
                                if current_info["Hacim"]
                                else "N/A"
                            ),
                        )
                    with c3:
                        cap = current_info["PiyConf"]
                        if cap and cap > 1e12:
                            st.metric("Piyasa Değeri", f"{cap/1e12:.2f}T ₺")
                        elif cap and cap > 1e9:
                            st.metric("Piyasa Değeri", f"{cap/1e9:.2f}B ₺")
                        else:
                            st.metric("Piyasa Değeri", "N/A")

                    c4, c5 = st.columns(2)
                    with c4:
                        st.metric(
                            "52H En Yüksek",
                            (
                                f"{current_info['52H Yüksek']:,.2f} ₺"
                                if current_info["52H Yüksek"]
                                else "N/A"
                            ),
                        )
                    with c5:
                        st.metric(
                            "52H En Düşük",
                            (
                                f"{current_info['52H Düşük']:,.2f} ₺"
                                if current_info["52H Düşük"]
                                else "N/A"
                            ),
                        )

                    if len(data) > 0:
                        last = data.iloc[-1]
                        st.markdown("### Teknik Göstergeler")
                        cols = st.columns(3)
                        cols[0].metric("WT1", f"{float(last['wt1'].iloc[0]):.2f}")
                        cols[1].metric("WT2", f"{float(last['wt2'].iloc[0]):.2f}")
                        ao_val = float(last["ao"].iloc[0])
                        cols[2].metric(
                            "AO",
                            f"{ao_val:.2f}",
                            delta="Yukarı" if ao_val > 0 else "Aşağı",
                        )
                else:
                    st.warning("Mevcut durum bilgileri alınamadı.")

            # === TAB 2: PERFORMANS ===
            with tab2:
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown("### Strateji Sonucu")
                    st.metric("Başlangıç", f"{initial_capital:,.0f} ₺")
                    st.metric("Son Değer", f"{final_value:,.2f} ₺")
                    st.metric(
                        "Kar/Zarar",
                        f"{final_value - initial_capital:,.2f} ₺",
                        f"%{total_return:+.2f}",
                    )

                    if not trades_df.empty:
                        st.markdown("### İşlemler")
                        df_disp = trades_df.copy()
                        df_disp["Fiyat"] = df_disp["Fiyat"].map("{:.4f}".format)
                        df_disp["Yatırım"] = df_disp["Yatırım"].map("{:,.2f}".format)
                        st.dataframe(df_disp, width="stretch")
                        st.download_button(
                            "CSV İndir",
                            df_disp.to_csv(index=False).encode("utf-8"),
                            f"{ticker}.csv",
                            "text/csv",
                        )
                    else:
                        st.info("Sinyal üretilmedi.")

                with col2:
                    st.markdown("### Portföy Büyümesi")
                    if not portfolio_df.empty:
                        fig, ax = plt.subplots(figsize=(12, 6))
                        ax.fill_between(
                            portfolio_df["Tarih"],
                            portfolio_df["Değer"],
                            initial_capital,
                            where=portfolio_df["Değer"] >= initial_capital,
                            color="#00ff88",
                            alpha=0.3,
                        )
                        ax.fill_between(
                            portfolio_df["Tarih"],
                            portfolio_df["Değer"],
                            initial_capital,
                            where=portfolio_df["Değer"] < initial_capital,
                            color="#ff4444",
                            alpha=0.3,
                        )
                        ax.plot(
                            portfolio_df["Tarih"],
                            portfolio_df["Değer"],
                            color="#0066ff",
                            linewidth=2.5,
                        )
                        ax.axhline(initial_capital, color="gray", linestyle="--")
                        ax.set_title(f"Portföy Büyümesi – {ticker}")
                        ax.set_ylabel("Değer (₺)")
                        ax.grid(True, alpha=0.3)
                        plt.xticks(rotation=45)
                        plt.tight_layout()
                        st.pyplot(fig)

            # === TAB 3: WAVETREND ===
            with tab3:
                col1, col2 = st.columns([3, 1])
                with col1:
                    fig, (ax1, ax2) = plt.subplots(
                        2, 1, figsize=(14, 9), gridspec_kw={"height_ratios": [3, 1]}
                    )
                    ax1.plot(
                        data.index,
                        data["wt1"],
                        label="WT1",
                        color="#00ff88",
                        linewidth=2,
                    )
                    ax1.plot(
                        data.index,
                        data["wt2"],
                        label="WT2",
                        color="#ff4444",
                        linewidth=2,
                    )
                    ax1.axhline(
                        53, color="red", linestyle=":", alpha=0.7, linewidth=1.5
                    )
                    ax1.axhline(45, color="red", linestyle="--", alpha=0.7)
                    ax1.axhline(-45, color="green", linestyle="--", alpha=0.7)
                    ax1.axhline(-53, color="green", linestyle=":", alpha=0.7)

                    ax1.scatter(
                        data.index[buy_sig],
                        data["wt1"][buy_sig],
                        color="lime",
                        s=120,
                        marker="^",
                        label="AL",
                        zorder=5,
                        edgecolors="black",
                    )
                    ax1.scatter(
                        data.index[sell_sig],
                        data["wt1"][sell_sig],
                        color="red",
                        s=120,
                        marker="v",
                        label="SAT",
                        zorder=5,
                        edgecolors="black",
                    )

                    ax1.set_title(
                        f"WaveTrend – {ticker}", fontsize=16, pad=20, fontweight="bold"
                    )
                    ax1.set_ylabel("WT Değeri")
                    ax1.legend(
                        frameon=True, fancybox=True, shadow=True, loc="upper left"
                    )
                    ax1.grid(True, alpha=0.3)

                    colors = np.where(data["ao"] > 0, "#00c853", "#d50000")
                    ax2.bar(data.index, data["ao"], color=colors, alpha=0.7, width=0.8)
                    ax2.axhline(0, color="white", linewidth=1.5)
                    ax2.set_title("Awesome Oscillator", fontsize=13)
                    ax2.set_ylabel("AO")
                    ax2.grid(True, alpha=0.3)

                    plt.tight_layout()
                    st.pyplot(fig)

                with col2:
                    st.markdown("### Sinyal Özeti")
                    st.metric("AL Sinyali", int(buy_sig.sum()), delta=None)
                    st.metric("SAT Sinyali", int(sell_sig.sum()), delta=None)
                    st.metric("Toplam", int(buy_sig.sum() + sell_sig.sum()), delta=None)

else:
    st.info("Lütfen bir hisse seçip **'Analizi Başlat'** butonuna basın.")
    st.markdown(
        """
    ### Kullanım
    - BIST 100 listesinden hisse seçin  
    - Zaman aralığı ve sermaye belirleyin  
    - Analizi başlatın  
    """
    )

# ==============================
#   FOOTER
# ==============================
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #888; font-size: 0.9rem;'>"
    "© 2025 WaveTrend Pro • Veri: Yahoo Finance • <a href='https://github.com/tolgakurtuluss/my-wavetrend-app' target='_blank'>GitHub</a>"
    "</p>",
    unsafe_allow_html=True,
)
