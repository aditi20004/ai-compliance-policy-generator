import sys
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from components.sidebar import render_sidebar

from app.compliance_checker import calculate_compliance_score
from app.database import SessionLocal, init_db
from app.models import Organisation, PolicyDocument, org_to_dict

render_sidebar()
init_db()

st.title("Compare Organisations")

db = SessionLocal()
try:
    orgs = db.query(Organisation).order_by(Organisation.created_at.desc()).all()

    if len(orgs) < 2:
        st.info("You need at least 2 organisations to compare. Complete the questionnaire for another organisation.")
        st.stop()

    # --- Org selection ---
    org_options = {org.id: org.business_name for org in orgs}
    selected_ids = st.multiselect(
        "Select organisations to compare:",
        options=list(org_options.keys()),
        default=list(org_options.keys())[: min(4, len(org_options))],
        format_func=lambda x: org_options[x],
        max_selections=6,
    )

    if len(selected_ids) < 2:
        st.warning("Select at least 2 organisations to compare.")
        st.stop()

    # --- Calculate compliance for each ---
    org_results = []
    for oid in selected_ids:
        org = db.query(Organisation).filter(Organisation.id == oid).first()
        if not org:
            continue
        policies = db.query(PolicyDocument).filter(PolicyDocument.org_id == oid).all()
        policy_types = {p.template_type for p in policies}

        org_data = org_to_dict(org)
        result = calculate_compliance_score(org_data, policy_types)
        org_results.append(
            {
                "id": oid,
                "name": org.business_name,
                "industry": org.industry.replace("_", " ").title(),
                "employees": org.employee_count,
                "score": result["score_percentage"],
                "risk": result["risk_rating"],
                "passed": result["passed"],
                "total": result["total"],
                "penalty": result["penalty_exposure"]["total_maximum_exposure"],
                "critical_gaps": len(result["critical_gaps"]),
                "high_gaps": len(result["high_gaps"]),
                "policies": len(policies),
                "result": result,
            }
        )

    # --- Summary Table ---
    st.subheader("Comparison Summary")

    cols = st.columns(len(org_results))
    for i, r in enumerate(org_results):
        with cols[i]:
            risk_colors = {"LOW": "#16a34a", "MEDIUM": "#ea580c", "HIGH": "#dc2626", "CRITICAL": "#dc2626"}
            rc = risk_colors.get(r["risk"], "#64748b")
            st.markdown(
                f"""
            <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:16px; text-align:center;">
                <div style="font-weight:700; color:#1a3c6e; font-size:1rem; margin-bottom:8px;">{escape(str(r["name"]))}</div>
                <div style="font-size:0.75rem; color:#64748b; margin-bottom:12px;">{escape(str(r["industry"]))} | {r["employees"]} staff</div>
                <div style="font-size:2.2rem; font-weight:800; color:#1a3c6e;">{r["score"]}%</div>
                <div style="font-size:0.8rem; color:#64748b;">Compliance Score</div>
                <div style="margin-top:8px;">
                    <span style="background:{rc}15; color:{rc}; padding:3px 12px; border-radius:20px; font-size:0.75rem; font-weight:600; border:1px solid {rc}30;">{r["risk"]}</span>
                </div>
                <div style="margin-top:12px; font-size:0.8rem; color:#334155;">
                    <div>{r["passed"]}/{r["total"]} items passed</div>
                    <div>{r["policies"]} policies generated</div>
                    <div style="color:#dc2626; font-weight:600;">${r["penalty"]:,.0f} exposure</div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    # --- Score Comparison Bar Chart ---
    st.divider()
    st.subheader("Compliance Score Comparison")

    names = [r["name"] for r in org_results]
    scores = [r["score"] for r in org_results]

    bar_colors = []
    for s in scores:
        if s >= 75:
            bar_colors.append("#16a34a")
        elif s >= 50:
            bar_colors.append("#2563eb")
        elif s >= 25:
            bar_colors.append("#ea580c")
        else:
            bar_colors.append("#dc2626")

    fig_bar = go.Figure(
        data=[
            go.Bar(
                x=names,
                y=scores,
                marker_color=bar_colors,
                text=[f"{s}%" for s in scores],
                textposition="outside",
                textfont=dict(size=14, color="#1a3c6e"),
            )
        ]
    )
    fig_bar.update_layout(
        yaxis=dict(title="Compliance Score (%)", range=[0, max(scores) + 15]),
        xaxis=dict(title=""),
        height=350,
        margin=dict(l=40, r=20, t=20, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # --- Radar Overlay ---
    st.divider()
    st.subheader("AI6 Practice Radar — Overlay")

    radar_colors = ["#1a3c6e", "#dc2626", "#16a34a", "#ea580c", "#7c3aed", "#0891b2"]

    fig_radar = go.Figure()
    for i, r in enumerate(org_results):
        practice_names = []
        practice_scores = []
        for pname, pdata in r["result"]["by_practice"].items():
            short = pname.split(". ", 1)[1] if ". " in pname else pname
            practice_names.append(short)
            pct = round((pdata["passed"] / pdata["total"]) * 100) if pdata["total"] > 0 else 0
            practice_scores.append(pct)

        # Close polygon
        rn = practice_names + [practice_names[0]]
        rs = practice_scores + [practice_scores[0]]

        color = radar_colors[i % len(radar_colors)]
        fig_radar.add_trace(
            go.Scatterpolar(
                r=rs,
                theta=rn,
                fill="toself",
                fillcolor=f"rgba({int(color[1:3], 16)},{int(color[3:5], 16)},{int(color[5:7], 16)},0.08)",
                line=dict(color=color, width=2),
                marker=dict(size=5, color=color),
                name=r["name"],
            )
        )

    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=10), gridcolor="#e2e8f0"),
            angularaxis=dict(tickfont=dict(size=11, color="#1a3c6e")),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        height=450,
        margin=dict(l=60, r=60, t=30, b=60),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    # --- Penalty Exposure Comparison ---
    st.divider()
    st.subheader("Penalty Exposure Comparison")

    penalties = [r["penalty"] for r in org_results]
    fig_penalty = go.Figure(
        data=[
            go.Bar(
                x=names,
                y=penalties,
                marker_color=["#dc2626" if p > 0 else "#16a34a" for p in penalties],
                text=[f"${p:,.0f}" for p in penalties],
                textposition="outside",
                textfont=dict(size=12, color="#1a3c6e"),
            )
        ]
    )
    fig_penalty.update_layout(
        yaxis=dict(title="Maximum Exposure (AUD)"),
        xaxis=dict(title=""),
        height=300,
        margin=dict(l=40, r=20, t=20, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_penalty, use_container_width=True)

    # --- Gap Summary Table ---
    st.divider()
    st.subheader("Gap Analysis Summary")

    gap_data = []
    for r in org_results:
        gap_data.append(
            {
                "Organisation": r["name"],
                "Industry": r["industry"],
                "Score": f"{r['score']}%",
                "Risk": r["risk"],
                "Critical Gaps": r["critical_gaps"],
                "High Gaps": r["high_gaps"],
                "Policies": r["policies"],
                "Penalty Exposure": f"${r['penalty']:,.0f}",
            }
        )

    st.dataframe(pd.DataFrame(gap_data), use_container_width=True, hide_index=True)

finally:
    db.close()
