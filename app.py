import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import re

st.set_page_config(page_title="🌍 Global Layoff Trend Dashboard", layout="wide")

# Load data
try:
    df = pd.read_csv("reports/cleaned_layoffs.csv")
    summary = pd.read_csv("reports/summary_insights.csv")
except FileNotFoundError:
    st.error("⚠️ Required files not found! Please run the analysis notebooks first.")
    st.stop()

df['country'] = df['country'].astype(str).fillna("Unknown")
df['industry'] = df['industry'].astype(str).fillna("Unknown")
df['location'] = df['location'].astype(str).fillna("Unknown")
df['year'] = pd.to_numeric(df['year'], errors='coerce').fillna(0).astype(int)
month_map = dict(zip(
    ['January','February','March','April','May','June','July','August','September','October','November','December'],
    range(1,13)))
df['month'] = df['month'].astype(str).map(month_map).fillna(0).astype(int)
df['total_laid_off'] = pd.to_numeric(df['total_laid_off'], errors='coerce').fillna(0)
def clean_funds(value):
    if isinstance(value, str):
        value = value.replace(',', '').replace('$', '').strip()
        match = re.match(r"([\d\.]+)\s*([KMB]?)", value, re.IGNORECASE)
        if match:
            num, suffix = match.groups()
            num = float(num)
            if suffix.upper() == 'K': num *= 1e3
            elif suffix.upper() == 'M': num *= 1e6
            elif suffix.upper() == 'B': num *= 1e9
            return num
        else:
            return np.nan
    elif isinstance(value, (int, float)):
        return value
    else:
        return np.nan
df['funds_raised_clean'] = df['funds_raised'].apply(clean_funds)

# Sidebar Filters (From Year - To Year)
st.sidebar.header("🔎 Filter Data")
years_sorted = sorted(df['year'].unique())
from_year = st.sidebar.selectbox("From Year", years_sorted, index=0)
to_year = st.sidebar.selectbox("To Year", years_sorted, index=len(years_sorted)-1)
industry = st.sidebar.selectbox("Select Industry", ["All"] + sorted(df['industry'].unique().tolist()))
country = st.sidebar.selectbox("Select Country", ["All"] + sorted(df['country'].unique().tolist()))

filtered = df[df['year'].between(from_year, to_year)]
if industry != "All":
    filtered = filtered[filtered['industry'] == industry]
if country != "All":
    filtered = filtered[filtered['country'] == country]

# Dynamic Summary Calculation (for Key Metrics and Insights)
if not filtered.empty:
    yearly_totals = filtered.groupby('year')['total_laid_off'].sum().sort_index()
    yoy_changes = yearly_totals.pct_change().dropna() * 100
    avg_yoy_change = yoy_changes.mean() if not yoy_changes.empty else 0
    peak_year = yearly_totals.idxmax() if not yearly_totals.empty else "N/A"
    top_industry = filtered.groupby('industry')['total_laid_off'].sum().idxmax() if not filtered.empty else "N/A"
    top_country = filtered.groupby('country')['total_laid_off'].sum().idxmax() if not filtered.empty else "N/A"
    year_min = filtered['year'].min()
    year_max = filtered['year'].max()
else:
    avg_yoy_change = 0
    peak_year = "N/A"
    top_industry = "N/A"
    top_country = "N/A"
    year_min = ""
    year_max = ""

st.markdown("<h1 style='text-align:center;'>📊 Global Layoff Trend Analysis (2020–2025)</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center; color:gray;'>Interactive Insights • Animated Visuals • Real Data</h4>", unsafe_allow_html=True)
st.write("---")

st.subheader("📈 Key Metrics Overview")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Layoffs", f"{int(filtered['total_laid_off'].sum()):,}")
col2.metric("Peak Year", peak_year)
col3.metric("Top Industry", top_industry)
col4.metric("Top Country", top_country)
st.write("---")

st.subheader("🎬  Industry-wise Layoff Trends (2020–2025)")
animated_data = filtered.groupby(['year','industry'], as_index=False)['total_laid_off'].sum()
fig_anim = px.bar(
    animated_data,
    x='industry', y='total_laid_off',
    color='industry',
    animation_frame='year',
    title="Layoffs by Industry",
    template='plotly_dark',
    hover_data=['industry', 'total_laid_off']
)
fig_anim = go.Figure(fig_anim)
try:
    fig_anim.layout.updatemenus[0].buttons[0].args[1]['frame']['duration'] = 5000
except Exception:
    pass
fig_anim.update_layout(xaxis={'categoryorder': 'total descending'}, height=420)
st.plotly_chart(fig_anim, use_container_width=True)

st.subheader("📅 Total Layoffs per Year")
yearly = filtered.groupby('year')['total_laid_off'].sum().reset_index()
fig2 = px.line(
    yearly, x='year', y='total_laid_off',
    markers=True, text='total_laid_off',
    template='plotly_dark',
    title="Yearly Layoff Trend",
    height=340
)
fig2.update_traces(textposition="top center")
st.plotly_chart(fig2, use_container_width=True)

col1, col2 = st.columns(2)
with col1:
    top_ind = filtered.groupby('industry')['total_laid_off'].sum().sort_values(ascending=False).head(10).reset_index()
    fig3 = px.bar(
        top_ind,
        x='total_laid_off', y='industry',
        orientation='h',
        color='total_laid_off',
        color_continuous_scale='bluered',
        title="🏭 Top 10 Industries by Layoffs",
        template='plotly_dark',
        height=340
    )
    st.plotly_chart(fig3, use_container_width=True)
with col2:
    top_cty = filtered.groupby('country')['total_laid_off'].sum().sort_values(ascending=False).head(10).reset_index()
    fig4 = px.bar(
        top_cty,
        x='total_laid_off', y='country',
        orientation='h',
        color='total_laid_off',
        color_continuous_scale='tealrose',
        title="🌎 Top 10 Countries by Layoffs",
        template='plotly_dark',
        height=340
    )
    st.plotly_chart(fig4, use_container_width=True)

st.subheader("🔥 Monthly Layoff Distribution Heatmap")
if not filtered.empty:
    heatmap = filtered.groupby(['year','month'])['total_laid_off'].sum().unstack().fillna(0)
    st.dataframe(heatmap.style.background_gradient(cmap='Reds', axis=None))

st.subheader("💸 Relationship Between Funding and Layoffs")
valid = filtered[filtered['funds_raised_clean'].notnull() & (filtered['funds_raised_clean'] > 0)]
if valid.shape[0] == 0:
    st.warning("No funding data available for visualization.")
else:
    fig = px.scatter(
        valid,
        x='funds_raised_clean',
        y='total_laid_off',
        color='industry',
        animation_frame='year' if 'year' in valid.columns else None,
        size='total_laid_off',
        hover_name='company' if 'company' in valid.columns else None,
        log_x=True,
        title="💸 Relationship Between Funds Raised and Total Layoffs (Animated)",
        width=820,
        height=420
    )
    fig = go.Figure(fig)
    try:
        if fig.layout.updatemenus:
            fig.layout.updatemenus[0].buttons[0].args[1]['frame']['duration'] = 5000
    except Exception:
        pass
    fig.update_layout(margin=dict(l=20, r=20, t=60, b=30))
    st.plotly_chart(fig, use_container_width=False)

    corr = valid[['funds_raised_clean', 'total_laid_off']].corr().iloc[0, 1]
    if pd.isna(corr):
        corr_text = "Insufficient numeric data to calculate correlation."
    else:
        strength = ("Weak" if abs(corr)<0.3 else "Moderate" if abs(corr)<0.6 else "Strong")
        corr_text = f"**📊 Correlation:** {corr:.3f} — {strength} relationship."
    st.markdown(corr_text)

    if corr > 0:
        relation = "Companies with higher funding tend to have higher layoffs, possibly due to large-scale restructuring."
    elif corr < 0:
        relation = "Companies with higher funding generally avoided massive layoffs, showing better financial stability."
    else:
        relation = "No clear relationship between funding and layoffs was found."
    st.markdown(f"💡 **Insight:** {relation}")

st.subheader("🧠 Auto Insights & Observations")
fund_corr = float(summary['Funding_Correlation'][0])
if np.isnan(fund_corr):
    fund_rel = "Insufficient data to measure correlation between funding and layoffs."
elif fund_corr > 0:
    fund_rel = f"Positive correlation ({fund_corr:.3f}): Higher-funded companies tended to record larger layoffs, likely due to restructuring."
elif fund_corr < 0:
    fund_rel = f"Negative correlation ({fund_corr:.3f}): Companies with strong funding generally experienced fewer layoffs."
else:
    fund_rel = "No clear pattern detected between funding and layoffs."

st.markdown(f"""
**🗓️ Years Analyzed:** {year_min}–{year_max}  
**📊 Average YoY Change:** {avg_yoy_change:.2f}%  
**🏆 Peak Year:** {peak_year}  
**🏭 Top Industry:** {top_industry}  
**🌍 Most Affected Country:** {top_country}  

💡 **Funding–Layoff Relationship:**  
{fund_rel}  

Overall, layoffs peaked during the post-pandemic recovery period (around {peak_year}),  
with early months (Jan–Mar) showing consistent spikes across years.  
This analysis highlights structural corrections across industries after the 2020–2022 growth surge.
""")

st.caption("Developed by Sai Bhavana Turai • Powered by Streamlit + Plotly • © 2025")
