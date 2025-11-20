import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import re

st.set_page_config(page_title="🌍 Global Layoff Trend Dashboard", layout="wide")

# -------------------------
# Helper utilities
# -------------------------
def clean_funds(value):
    """Normalize funds strings like '12.3M', '$1,200', '5K' into numeric."""
    if isinstance(value, str):
        value = value.replace(',', '').replace('$', '').strip()
        match = re.match(r"([\d\.]+)\s*([KMB]?)", value, re.IGNORECASE)
        if match:
            num, suffix = match.groups()
            num = float(num)
            if suffix.upper() == 'K':
                num *= 1e3
            elif suffix.upper() == 'M':
                num *= 1e6
            elif suffix.upper() == 'B':
                num *= 1e9
            return num
        else:
            return np.nan
    elif isinstance(value, (int, float)):
        return value
    else:
        return np.nan

def dynamic_title(base, industry, country, fy, ty):
    """Create a compact dynamic title string based on filters."""
    parts = [f"{fy}–{ty}"]
    if industry != "All":
        parts.insert(0, industry)  # put industry before years
    if country != "All":
        parts.append(country)     # put country after years (so order: industry • years • country)
    extra = " • ".join(parts)
    return f"{base} ({extra})" if extra else base

def safe_groupby_sum(df, cols, value_col):
    """Groupby guard - return empty df with expected columns if original is empty."""
    if df.empty:
        return pd.DataFrame(columns=cols + [value_col])
    return df.groupby(cols, as_index=False)[value_col].sum()

# -------------------------
# Load data
# -------------------------
try:
    df = pd.read_csv("reports/cleaned_layoffs.csv")
    summary = pd.read_csv("reports/summary_insights.csv")
except FileNotFoundError:
    st.error("⚠️ Required files not found! Please run the analysis notebooks first.")
    st.stop()

# -------------------------
# Clean & normalize dataset
# -------------------------
# Strip strings, handle missing
for col in ['country', 'industry', 'location', 'company']:
    if col in df.columns:
        df[col] = df[col].fillna("Unknown").astype(str).str.strip()
    else:
        # ensure column exists to avoid KeyErrors later
        df[col] = "Unknown"

# Year handling: drop invalid years instead of converting to 0
df['year'] = pd.to_numeric(df['year'], errors='coerce')
df = df[df['year'].notna()]
df['year'] = df['year'].astype(int)

# Month mapping (safe)
month_map = dict(zip(
    ['January','February','March','April','May','June','July','August','September','October','November','December'],
    range(1,13)))
# If month numeric already, keep that; else map names; invalid -> 0
def normalize_month(m):
    if pd.isna(m):
        return 0
    if isinstance(m, (int, float)):
        try:
            return int(m)
        except Exception:
            return 0
    m = str(m).strip()
    if m.isdigit():
        return int(m)
    return month_map.get(m, 0)

df['month'] = df['month'].apply(normalize_month).astype(int)

# numeric conversions
df['total_laid_off'] = pd.to_numeric(df.get('total_laid_off', 0), errors='coerce').fillna(0).astype(int)
df['funds_raised_clean'] = df.get('funds_raised', np.nan).apply(clean_funds)

# -------------------------
# Sidebar Filters
# -------------------------
st.sidebar.header("🔎 Filter Data")

years_sorted = sorted(df['year'].unique())
if not years_sorted:
    st.sidebar.error("No valid years present in dataset.")
    st.stop()

# default indexes
from_year = st.sidebar.selectbox("From Year", years_sorted, index=0)
to_year = st.sidebar.selectbox("To Year", years_sorted, index=len(years_sorted)-1)

# industry & country lists
industries = ["All"] + sorted(df['industry'].dropna().unique().tolist())
countries = ["All"] + sorted(df['country'].dropna().unique().tolist())

industry = st.sidebar.selectbox("Select Industry", industries)
country = st.sidebar.selectbox("Select Country", countries)

# Show selected filters compactly
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Selected:** {industry} • {country} • {from_year}–{to_year}")

# -------------------------
# Apply Filters
# -------------------------
# Ensure from_year <= to_year by swapping if user picks in reverse
if from_year > to_year:
    from_year, to_year = to_year, from_year

filtered = df[df['year'].between(from_year, to_year)]
if industry != "All":
    filtered = filtered[filtered['industry'] == industry]
if country != "All":
    filtered = filtered[filtered['country'] == country]

# -------------------------
# Dynamic Headings
# -------------------------
main_title = dynamic_title("Global Layoff Trend Analysis", industry if industry!="All" else "All industries", country if country!="All" else "All countries", from_year, to_year)
# Make the displayed string a bit cleaner when "All industries" or "All countries" appear:
if "All industries" in main_title:
    main_title = main_title.replace("All industries • ", "")
if " • All countries" in main_title:
    main_title = main_title.replace(" • All countries", "")

st.markdown(f"<h1 style='text-align:center;'>📊 {main_title}</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center; color:gray;'>Interactive Insights • Animated Visuals • Real Data</h4>", unsafe_allow_html=True)
st.write("---")

# -------------------------
# Summary calculations (guarded)
# -------------------------
if not filtered.empty:
    yearly_totals = filtered.groupby('year')['total_laid_off'].sum().sort_index()
    yoy_changes = yearly_totals.pct_change().dropna() * 100
    avg_yoy_change = float(yoy_changes.mean()) if not yoy_changes.empty else 0.0
    peak_year = int(yearly_totals.idxmax()) if not yearly_totals.empty else "N/A"
    # top industry/country within the filtered subset
    try:
        top_industry = filtered.groupby('industry')['total_laid_off'].sum().idxmax()
    except Exception:
        top_industry = "N/A"
    try:
        top_country = filtered.groupby('country')['total_laid_off'].sum().idxmax()
    except Exception:
        top_country = "N/A"
    year_min = int(filtered['year'].min())
    year_max = int(filtered['year'].max())
else:
    avg_yoy_change = 0.0
    peak_year = "N/A"
    top_industry = "N/A"
    top_country = "N/A"
    year_min = from_year
    year_max = to_year

# -------------------------
# Key Metrics (dynamic heading)
# -------------------------
st.subheader(dynamic_title("📈 Key Metrics Overview", industry, country, from_year, to_year))
col1, col2, col3, col4 = st.columns(4)

total_layoffs_val = int(filtered['total_laid_off'].sum()) if not filtered.empty else 0
col1.metric("Total Layoffs", f"{total_layoffs_val:,}")
col2.metric("Peak Year", peak_year)
col3.metric("Top Industry", top_industry)
col4.metric("Top Country", top_country)
st.write("---")

# -------------------------
# Industry-wise Trends (dynamic)
# -------------------------
st.subheader(dynamic_title("🎬 Industry-wise Layoff Trends", industry, country, from_year, to_year))
animated_data = safe_groupby_sum(filtered, ['year', 'industry'], 'total_laid_off')

if animated_data.empty:
    st.info("No data available for the selected filters.")
else:
    fig_anim = px.bar(
        animated_data,
        x='industry', y='total_laid_off',
        color='industry',
        animation_frame='year',
        title="Layoffs by Industry",
        template='plotly_dark',
        hover_data=['industry', 'total_laid_off']
    )
    # convert to go.Figure so we can tweak layout safely
    fig_anim = go.Figure(fig_anim)
    try:
        if fig_anim.layout.updatemenus:
            fig_anim.layout.updatemenus[0].buttons[0].args[1]['frame']['duration'] = 1200
    except Exception:
        pass
    fig_anim.update_layout(xaxis={'categoryorder': 'total descending'}, height=420, margin=dict(t=60))
    st.plotly_chart(fig_anim, use_container_width=True)

# -------------------------
# Yearly Layoff Trend
# -------------------------
st.subheader(dynamic_title("📅 Total Layoffs per Year", industry, country, from_year, to_year))
yearly = filtered.groupby('year')['total_laid_off'].sum().reset_index()

if yearly.empty:
    st.info("No yearly data to show for selected filters.")
else:
    fig2 = px.line(
        yearly, x='year', y='total_laid_off',
        markers=True, text='total_laid_off',
        template='plotly_dark',
        title="Yearly Layoff Trend",
        height=340
    )
    fig2.update_traces(textposition="top center")
    st.plotly_chart(fig2, use_container_width=True)

# -------------------------
# Top Industries & Countries
# -------------------------
col1, col2 = st.columns(2)
with col1:
    st.subheader(dynamic_title("🏭 Top Industries by Layoffs", industry, country, from_year, to_year))
    if filtered.empty:
        st.info("No data to display.")
    else:
        top_ind = filtered.groupby('industry')['total_laid_off'].sum().sort_values(ascending=False).head(10).reset_index()
        if top_ind.empty:
            st.info("No industries to display.")
        else:
            fig3 = px.bar(
                top_ind,
                x='total_laid_off', y='industry',
                orientation='h',
                color='total_laid_off',
                color_continuous_scale='bluered',
                title="Top Industries",
                template='plotly_dark',
                height=340
            )
            st.plotly_chart(fig3, use_container_width=True)
with col2:
    st.subheader(dynamic_title("🌎 Top Countries by Layoffs", industry, country, from_year, to_year))
    if filtered.empty:
        st.info("No data to display.")
    else:
        top_cty = filtered.groupby('country')['total_laid_off'].sum().sort_values(ascending=False).head(10).reset_index()
        if top_cty.empty:
            st.info("No countries to display.")
        else:
            fig4 = px.bar(
                top_cty,
                x='total_laid_off', y='country',
                orientation='h',
                color='total_laid_off',
                color_continuous_scale='tealrose',
                title="Top Countries",
                template='plotly_dark',
                height=340
            )
            st.plotly_chart(fig4, use_container_width=True)

# -------------------------
# Monthly Heatmap
# -------------------------
st.subheader(dynamic_title("🔥 Monthly Layoff Distribution Heatmap", industry, country, from_year, to_year))
if not filtered.empty:
    heatmap = filtered.groupby(['year','month'])['total_laid_off'].sum().unstack().fillna(0)
    st.dataframe(heatmap.style.background_gradient(cmap='Reds', axis=None))
else:
    st.info("No monthly distribution to show for selected filters.")

# -------------------------
# Funding vs Layoffs
# -------------------------
st.subheader(dynamic_title("💸 Relationship Between Funding and Layoffs", industry, country, from_year, to_year))
valid = filtered[filtered['funds_raised_clean'].notnull() & (filtered['funds_raised_clean'] > 0)]
if valid.shape[0] == 0:
    st.warning("No funding data available for visualization for the current filters.")
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
        title="Relationship Between Funds Raised and Total Layoffs (Animated)",
        width=820,
        height=420,
        template='plotly_dark'
    )
    fig = go.Figure(fig)
    try:
        if fig.layout.updatemenus:
            fig.layout.updatemenus[0].buttons[0].args[1]['frame']['duration'] = 1200
    except Exception:
        pass
    fig.update_layout(margin=dict(l=20, r=20, t=60, b=30))
    st.plotly_chart(fig, use_container_width=False)

    corr = valid[['funds_raised_clean', 'total_laid_off']].corr().iloc[0, 1]
    if pd.isna(corr):
        corr_text = "Insufficient numeric data to calculate correlation."
    else:
        strength = ("Weak" if abs(corr) < 0.3 else "Moderate" if abs(corr) < 0.6 else "Strong")
        corr_text = f"**📊 Correlation:** {corr:.3f} — {strength} relationship."
    st.markdown(corr_text)

    if corr > 0:
        relation = "Companies with higher funding tend to have higher layoffs, possibly due to large-scale restructuring."
    elif corr < 0:
        relation = "Companies with higher funding generally avoided massive layoffs, showing better financial stability."
    else:
        relation = "No clear relationship between funding and layoffs was found."
    st.markdown(f"💡 **Insight:** {relation}")

# -------------------------
# Auto Insights & Observations (from summary file)
# -------------------------
st.subheader(dynamic_title("🧠 Auto Insights & Observations", industry, country, from_year, to_year))
fund_corr = None
try:
    fund_corr = float(summary['Funding_Correlation'].iloc[0])
except Exception:
    fund_corr = np.nan

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
