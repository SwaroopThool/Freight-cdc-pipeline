"""
Real-time Freight Tracking Dashboard
Tabs: Live Map | Shipments | Revenue | Jobs | Invoices
Refreshes every 3 seconds via st.rerun().
"""

import os, time
import pandas as pd
import psycopg2, psycopg2.extras
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

MZ_DSN = os.environ.get("MATERIALIZE_DSN", "postgresql://materialize@materialized:6875/materialize")
PG_DSN = os.environ.get("POSTGRES_DSN",    "postgresql://freight_user:freight_pass@postgres:5432/freight_db")
REFRESH = 3

st.set_page_config(page_title="Freight CDC", page_icon="🚚", layout="wide")


def query(dsn: str, sql: str, params=None) -> pd.DataFrame:
    try:
        with psycopg2.connect(dsn, cursor_factory=psycopg2.extras.RealDictCursor) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return pd.DataFrame(cur.fetchall())
    except Exception as e:
        st.warning(f"Query error: {e}")
        return pd.DataFrame()


st.title("🚚 Freight CDC — Live Dashboard")

tab_map, tab_ship, tab_rev, tab_jobs, tab_inv = st.tabs(
    ["🗺 Live Map", "📦 Shipments", "💰 Revenue", "🔧 Jobs", "📄 Invoices"]
)

# ── Live Map ─────────────────────────────────────────────────
with tab_map:
    st.subheader("Vehicle Positions")
    df = query(PG_DSN, """
        SELECT DISTINCT ON (t.vehicle_id)
            t.vehicle_id, v.name, v.type, t.lat::float, t.lon::float, t.speed_kmh::float, t.hop_number
        FROM tracking_event t
        JOIN vehicle v ON v.id = t.vehicle_id
        ORDER BY t.vehicle_id, t.timestamp DESC
    """)
    if df.empty:
        st.info("No tracking data yet — generator is warming up.")
    else:
        st.map(df.rename(columns={"lat": "latitude", "lon": "longitude"}), zoom=1)
        c1, c2, c3 = st.columns(3)
        c1.metric("Trucks",  int((df["type"] == "truck").sum()))
        c2.metric("Ships",   int((df["type"] == "ship").sum()))
        c3.metric("Planes",  int((df["type"] == "plane").sum()))

    st.markdown("---")
    st.subheader("Hop Trail — select a vehicle")
    vehicles = query(PG_DSN, "SELECT id, name, type FROM vehicle ORDER BY name")
    if not vehicles.empty:
        sel = st.selectbox(
            "Vehicle",
            vehicles["id"].tolist(),
            format_func=lambda i: vehicles.loc[vehicles["id"] == i, "name"].values[0],
        )
        vrow = vehicles.loc[vehicles["id"] == sel].iloc[0]

        trail = query(PG_DSN, """
            SELECT hop_number,
                   lat::float      AS latitude,
                   lon::float      AS longitude,
                   speed_kmh::float AS speed_kmh,
                   timestamp
            FROM tracking_event
            WHERE vehicle_id = %s
            ORDER BY hop_number ASC
        """, (sel,))

        if trail.empty:
            st.info("No hops recorded yet for this vehicle.")
        else:
            # ── Summary stats ─────────────────────────────────
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Vehicle",    vrow["name"])
            c2.metric("Type",       vrow["type"].capitalize())
            c3.metric("Total Hops", len(trail))
            c4.metric("Max Speed",  f"{trail['speed_kmh'].max():.0f} km/h")

            # ── Route map with connected path ──────────────────
            fig = go.Figure()

            # Path line
            fig.add_trace(go.Scattermapbox(
                lat=trail["latitude"],
                lon=trail["longitude"],
                mode="lines",
                line=dict(width=2, color="rgba(255,165,0,0.6)"),
                name="Route",
                hoverinfo="skip",
            ))

            # Hop dots coloured by speed
            fig.add_trace(go.Scattermapbox(
                lat=trail["latitude"],
                lon=trail["longitude"],
                mode="markers",
                marker=dict(
                    size=8,
                    color=trail["speed_kmh"],
                    colorscale="RdYlGn",
                    cmin=0,
                    cmax=trail["speed_kmh"].max() or 1,
                    showscale=True,
                    colorbar=dict(title="km/h", thickness=12),
                ),
                text=trail["hop_number"].apply(lambda h: f"Hop {h}"),
                customdata=trail["speed_kmh"],
                hovertemplate="<b>%{text}</b><br>Speed: %{customdata:.0f} km/h<extra></extra>",
                name="Hops",
            ))

            # Start (green) and end (red) markers
            for i, color, label in [(0, "green", "Start"), (-1, "red", "End")]:
                fig.add_trace(go.Scattermapbox(
                    lat=[trail.iloc[i]["latitude"]],
                    lon=[trail.iloc[i]["longitude"]],
                    mode="markers+text",
                    marker=dict(size=14, color=color),
                    text=[label],
                    textposition="top right",
                    hoverinfo="skip",
                    name=label,
                    showlegend=False,
                ))

            fig.update_layout(
                mapbox_style="open-street-map",
                mapbox=dict(
                    center=dict(
                        lat=trail["latitude"].mean(),
                        lon=trail["longitude"].mean(),
                    ),
                    zoom=2,
                ),
                margin=dict(l=0, r=0, t=0, b=0),
                height=420,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig, use_container_width=True)

            # ── Hop detail table ───────────────────────────────
            with st.expander("Hop details"):
                st.dataframe(
                    trail[["hop_number", "latitude", "longitude", "speed_kmh", "timestamp"]]
                    .rename(columns={"hop_number": "Hop", "latitude": "Latitude",
                                     "longitude": "Longitude", "speed_kmh": "Speed (km/h)",
                                     "timestamp": "Time"}),
                    use_container_width=True,
                    hide_index=True,
                )

# ── Shipments ────────────────────────────────────────────────
with tab_ship:
    st.subheader("Shipments by Mode & Status")
    df = query(MZ_DSN, "SELECT mode, status, shipment_count::int FROM v_active_shipments")
    if df.empty:
        st.info("Waiting for Materialize…")
    else:
        fig = px.bar(df, x="mode", y="shipment_count", color="status", barmode="group",
                     labels={"mode": "Mode", "shipment_count": "Count"})
        st.plotly_chart(fig, use_container_width=True)
        for mode, cnt in df.groupby("mode")["shipment_count"].sum().items():
            st.metric(mode.capitalize(), int(cnt))

# ── Revenue ──────────────────────────────────────────────────
with tab_rev:
    st.subheader("Revenue by Route")
    # Read raw revenue from Materialize, then join location names from Postgres
    rev = query(MZ_DSN, """
        SELECT origin_id, destination_id, order_count::int, total_revenue_usd::float
        FROM v_revenue_by_route
        ORDER BY total_revenue_usd DESC LIMIT 20
    """)
    if rev.empty:
        st.info("Waiting for data…")
    else:
        locs = query(PG_DSN, "SELECT id, name, city FROM location")
        loc_map = {int(r["id"]): f"{r['name']} ({r['city']})" for _, r in locs.iterrows()}
        rev["route"] = (
            rev["origin_id"].map(loc_map).fillna(rev["origin_id"].astype(str))
            + " → "
            + rev["destination_id"].map(loc_map).fillna(rev["destination_id"].astype(str))
        )
        fig = px.bar(rev, x="total_revenue_usd", y="route", orientation="h",
                     color="total_revenue_usd", color_continuous_scale="Teal",
                     labels={"total_revenue_usd": "Revenue (USD)", "route": "Route"},
                     hover_data={"order_count": True})
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
        c1, c2 = st.columns(2)
        c1.metric("Total Revenue",  f"${rev['total_revenue_usd'].sum():,.0f}")
        c2.metric("Total Orders",   int(rev["order_count"].sum()))

# ── Jobs ─────────────────────────────────────────────────────
with tab_jobs:
    st.subheader("Job Status")
    df = query(MZ_DSN, "SELECT status, job_count::int FROM v_job_summary")
    if df.empty:
        st.info("Waiting for data…")
    else:
        fig = px.pie(df, names="status", values="job_count",
                     color="status",
                     color_discrete_map={"pending": "#f39c12", "in_progress": "#3498db",
                                         "completed": "#2ecc71", "failed": "#e74c3c"})
        st.plotly_chart(fig, use_container_width=True)

# ── Invoices ─────────────────────────────────────────────────
with tab_inv:
    st.subheader("Invoice Aging")
    df = query(MZ_DSN, "SELECT status, invoice_count::int, total_amount_usd::float FROM v_invoice_aging")
    if df.empty:
        st.info("Waiting for data…")
    else:
        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(df, x="status", y="invoice_count", color="status",
                         color_discrete_map={"draft": "#95a5a6", "sent": "#3498db", "paid": "#2ecc71"})
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = px.pie(df, names="status", values="total_amount_usd",
                         color="status",
                         color_discrete_map={"draft": "#95a5a6", "sent": "#3498db", "paid": "#2ecc71"})
            st.plotly_chart(fig, use_container_width=True)

st.caption(f"Refreshes every {REFRESH}s · Materialize port 6875")
time.sleep(REFRESH)
st.rerun()
