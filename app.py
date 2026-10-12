import math

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Analitik Inventory: EOQ vs EPQ", layout="wide")

# ---------------------------------------------------------------- Sidebar
st.sidebar.header("Parameter Biaya & Persediaan")
unit_cost = st.sidebar.number_input("Harga Beli / Biaya Produksi per Unit ($)", 0.0, value=50.0, step=1.0)
order_cost = st.sidebar.number_input("Biaya Pemesanan / Order ($)", 0.0, value=100.0, step=10.0)
setup_cost = st.sidebar.number_input("Biaya Setup Produksi / Run ($)", 0.0, value=200.0, step=10.0)
holding_cost = st.sidebar.number_input("Holding Cost / Unit / Tahun ($)", 0.01, value=10.0, step=1.0)

st.sidebar.header("Parameter Operasional")
prod_rate = st.sidebar.number_input("Laju Produksi (unit/hari)", 1.0, value=100.0, step=5.0)
lead_time = st.sidebar.number_input("Lead Time (hari)", 0.0, value=5.0, step=1.0)
safety_stock = st.sidebar.number_input("Safety Stock (unit)", 0.0, value=50.0, step=10.0)

st.sidebar.header("Kebijakan Saat Ini")
q_current = st.sidebar.number_input("Ukuran Pesanan Saat Ini (unit)", 1.0, value=1000.0, step=50.0)

# ---------------------------------------------------------------- Input data
st.title("Aplikasi Analitik Manajemen Persediaan")
st.caption("Simulasi kebijakan EOQ, EPQ, dan kebijakan saat ini (Operations Management, Chapter 13)")

st.subheader("Data Permintaan & Hari Kerja Bulanan")
default_df = pd.DataFrame({
    "Bulan": ["Januari", "Februari", "Maret", "April", "Mei", "Juni",
              "Juli", "Agustus", "September", "Oktober", "November", "Desember"],
    "Demand": [1000, 950, 1000, 1050, 1100, 1050, 1000, 950, 1000, 1050, 1000, 850],
    "Hari_Kerja": [22, 20, 22, 21, 22, 21, 22, 22, 21, 22, 21, 20],
})
df = st.data_editor(default_df, num_rows="fixed", width='stretch', hide_index=True)

D = float(df["Demand"].sum())
days = float(df["Hari_Kerja"].sum())
if D <= 0 or days <= 0:
    st.error("Total demand dan hari kerja harus lebih dari 0.")
    st.stop()
d = D / days  # permintaan harian

c1, c2, c3 = st.columns(3)
c1.metric("Demand Tahunan (D)", f"{D:,.0f} unit")
c2.metric("Hari Kerja / Tahun", f"{days:,.0f} hari")
c3.metric("Demand Harian (d)", f"{d:,.1f} unit")

# ---------------------------------------------------------------- Perhitungan
def relevant_cost(q, s, imax_factor=1.0):
    """Biaya relevan tahunan = pemesanan/setup + holding."""
    ordering = D / q * s
    holding = (q * imax_factor / 2) * holding_cost
    return ordering, holding


eoq = math.sqrt(2 * D * order_cost / holding_cost)

if prod_rate <= d:
    st.error("Laju produksi harus lebih besar dari demand harian agar EPQ dapat dihitung.")
    st.stop()
factor = 1 - d / prod_rate
epq = math.sqrt(2 * D * setup_cost / (holding_cost * factor))

rop = d * lead_time + safety_stock

rows = []
for name, q, s, f in [
    ("Kebijakan Saat Ini", q_current, order_cost, 1.0),
    ("EOQ (Beli)", eoq, order_cost, 1.0),
    ("EPQ (Produksi Sendiri)", epq, setup_cost, factor),
]:
    o, h = relevant_cost(q, s, f)
    imax = q * f
    sstock_cost = safety_stock * holding_cost
    rows.append({
        "Kebijakan": name,
        "Q (unit)": round(q, 1),
        "Jumlah Order/Run": round(D / q, 2),
        "Siklus (hari)": round(q / d, 1),
        "Inventori Maks (unit)": round(imax + safety_stock, 1),
        "Biaya Order/Setup ($)": round(o, 2),
        "Biaya Holding ($)": round(h + sstock_cost, 2),
        "Biaya Material ($)": round(D * unit_cost, 2),
    })
res = pd.DataFrame(rows)
res["Biaya Relevan ($)"] = res["Biaya Order/Setup ($)"] + res["Biaya Holding ($)"]
res["Total Biaya ($)"] = res["Biaya Relevan ($)"] + res["Biaya Material ($)"]

# ---------------------------------------------------------------- Ringkasan
st.subheader("Ringkasan Hasil Perbandingan Biaya")
st.dataframe(
    res[["Kebijakan", "Q (unit)", "Biaya Order/Setup ($)", "Biaya Holding ($)",
         "Biaya Relevan ($)", "Biaya Material ($)", "Total Biaya ($)"]],
    width='stretch', hide_index=True,
)

left, right = st.columns([3, 2])
with left:
    fig = px.bar(res, x="Kebijakan", y="Biaya Relevan ($)", color="Kebijakan",
                 title="Perbandingan Biaya Relevan Tahunan (Order/Setup + Holding)",
                 text_auto=",.0f")
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, width='stretch')

best = res.loc[res["Biaya Relevan ($)"].idxmin()]
with right:
    st.success(
        f"**Rekomendasi Kebijakan Optimal:** {best['Kebijakan']} memiliki biaya relevan "
        f"terendah, yaitu ${best['Biaya Relevan ($)']:,.2f} per tahun."
    )
    st.info(
        f"**Reorder Point (ROP)** = d × L + Safety Stock = "
        f"{d:,.1f} × {lead_time:g} + {safety_stock:g} = **{rop:,.1f} unit**"
    )
    st.caption("Catatan: EOQ vs EPQ mewakili dua sumber pasokan berbeda (beli vs produksi sendiri), "
               "sehingga perbandingannya bergantung pada biaya order dan setup masing-masing.")

# ---------------------------------------------------------------- Kurva biaya
st.subheader("Kurva Biaya Total terhadap Ukuran Lot (Q)")
q_range = np.linspace(max(10, eoq * 0.2), max(epq, q_current, eoq) * 1.5, 200)
curve = pd.DataFrame({
    "Q": q_range,
    "Biaya Order": D / q_range * order_cost,
    "Biaya Holding": q_range / 2 * holding_cost,
})
curve["Biaya Total"] = curve["Biaya Order"] + curve["Biaya Holding"]
fig2 = go.Figure()
for col in ["Biaya Order", "Biaya Holding", "Biaya Total"]:
    fig2.add_trace(go.Scatter(x=curve["Q"], y=curve[col], name=col, mode="lines"))
tc_eoq = D / eoq * order_cost + eoq / 2 * holding_cost
fig2.add_trace(go.Scatter(x=[eoq], y=[tc_eoq], mode="markers+text", name="EOQ",
                          text=[f"EOQ = {eoq:,.0f}"], textposition="top center",
                          marker=dict(size=12, color="red")))
fig2.update_layout(xaxis_title="Ukuran Pesanan Q (unit)", yaxis_title="Biaya Tahunan ($)")
st.plotly_chart(fig2, width='stretch')

# ---------------------------------------------------------------- Rincian
st.subheader("Rincian Perhitungan")
with st.expander("Rincian Kebijakan Saat Ini"):
    st.write(f"- Jumlah order/tahun = D / Q = {D:,.0f} / {q_current:,.0f} = {D / q_current:,.2f}")
    st.write(f"- Biaya order = {D / q_current:,.2f} × ${order_cost:,.0f} = ${D / q_current * order_cost:,.2f}")
    st.write(f"- Biaya holding = (Q/2) × H = {q_current / 2:,.1f} × ${holding_cost:,.0f} = ${q_current / 2 * holding_cost:,.2f}")
with st.expander("Rincian EOQ"):
    st.latex(r"EOQ = \sqrt{\frac{2DS}{H}}")
    st.write(f"EOQ = √(2 × {D:,.0f} × {order_cost:,.0f} / {holding_cost:,.0f}) = **{eoq:,.2f} unit**")
    st.write(f"Jumlah order/tahun = {D / eoq:,.2f}; siklus = {eoq / d:,.1f} hari")
    st.write(f"Biaya order = ${D / eoq * order_cost:,.2f}; biaya holding = ${eoq / 2 * holding_cost:,.2f}")
with st.expander("Rincian EPQ"):
    st.latex(r"EPQ = \sqrt{\frac{2DS}{H\,(1 - d/p)}}")
    st.write(f"d/p = {d:,.2f} / {prod_rate:,.0f} = {d / prod_rate:.4f}")
    st.write(f"EPQ = √(2 × {D:,.0f} × {setup_cost:,.0f} / ({holding_cost:,.0f} × {factor:.4f})) = **{epq:,.2f} unit**")
    st.write(f"Inventori maksimum = Q × (1 − d/p) = {epq * factor:,.2f} unit")
    st.write(f"Waktu produksi per run = Q / p = {epq / prod_rate:,.1f} hari")
