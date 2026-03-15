from html import escape

import streamlit as st


def apply_theme():
    """Apply custom CSS theming across the app."""
    st.markdown(
        """
    <style>
    /* --- Header bar --- */
    header[data-testid="stHeader"] {
        background: linear-gradient(90deg, #1a3c6e 0%, #2d5fa1 100%);
    }

    /* --- Sidebar branding --- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f2744 0%, #1a3c6e 100%);
    }
    section[data-testid="stSidebar"] * {
        color: #e0e7ef !important;
    }
    section[data-testid="stSidebar"] .stMarkdown a {
        color: #6db3f2 !important;
    }

    /* --- Metric cards --- */
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #1a3c6e;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        transition: box-shadow 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    div[data-testid="stMetric"] label {
        color: #64748b !important;
        font-size: 0.85rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #1a3c6e !important;
        font-weight: 700 !important;
    }

    /* --- Buttons --- */
    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #1a3c6e, #2d5fa1);
        border: none;
        border-radius: 8px;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(90deg, #15325c, #245089);
    }
    .stButton > button[kind="secondary"] {
        border: 1.5px solid #1a3c6e;
        color: #1a3c6e;
        border-radius: 8px;
        font-weight: 600;
    }

    /* --- Expanders --- */
    details[data-testid="stExpander"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        margin-bottom: 8px;
    }

    /* --- Dividers --- */
    hr {
        border-color: #e2e8f0 !important;
    }

    /* --- Download buttons --- */
    .stDownloadButton > button {
        background: #f0f7ff;
        border: 1.5px solid #1a3c6e;
        color: #1a3c6e;
        border-radius: 8px;
        font-weight: 600;
    }

    /* --- Info/warning/error boxes --- */
    div[data-testid="stAlert"] {
        border-radius: 10px;
    }

    /* --- Tab styling --- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
        font-weight: 600;
    }

    /* --- Page title --- */
    h1 {
        color: #1a3c6e !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em;
    }
    h2, h3 {
        color: #1a3c6e !important;
    }

    /* --- Page subtitle --- */
    .page-subtitle {
        color: #64748b;
        font-size: 1.05rem;
        margin-top: -8px;
        margin-bottom: 20px;
    }

    /* --- Progress bar --- */
    .stProgress > div > div {
        background: linear-gradient(90deg, #1a3c6e, #2d5fa1) !important;
    }

    /* --- Section card --- */
    .section-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    .section-card-header {
        font-weight: 700;
        color: #1a3c6e;
        font-size: 1rem;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #e2e8f0;
    }

    /* --- Container(border=True) enhancement --- */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
        transition: box-shadow 0.2s ease;
    }
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }

    /* --- Table/dataframe styling --- */
    .stDataFrame thead tr th {
        background: #f0f4f8 !important;
        color: #1a3c6e !important;
        font-weight: 600 !important;
    }
    .stDataFrame tbody tr:nth-child(even) {
        background: #f8fafc;
    }

    /* --- Questionnaire section header --- */
    .q-section-header {
        background: linear-gradient(135deg, #1a3c6e 0%, #2d5fa1 100%);
        color: #ffffff;
        padding: 14px 20px;
        border-radius: 10px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .q-section-header .step-circle {
        background: rgba(255,255,255,0.2);
        border: 2px solid rgba(255,255,255,0.6);
        border-radius: 50%;
        width: 38px;
        height: 38px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 1.1rem;
        flex-shrink: 0;
    }
    .q-section-header .step-info {
        display: flex;
        flex-direction: column;
    }
    .q-section-header .step-title {
        font-weight: 700;
        font-size: 1.05rem;
    }
    .q-section-header .step-questions {
        font-size: 0.8rem;
        opacity: 0.8;
    }

    /* --- Quick action cards --- */
    .quick-action-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        transition: all 0.2s ease;
        cursor: pointer;
        text-decoration: none !important;
        display: block;
    }
    .quick-action-card:hover {
        box-shadow: 0 4px 16px rgba(26,60,110,0.12);
        border-color: #1a3c6e;
        transform: translateY(-1px);
    }
    .quick-action-card .qa-icon {
        font-size: 1.8rem;
        margin-bottom: 8px;
    }
    .quick-action-card .qa-label {
        font-weight: 700;
        color: #1a3c6e;
        font-size: 0.95rem;
        margin-bottom: 4px;
    }
    .quick-action-card .qa-desc {
        color: #64748b;
        font-size: 0.8rem;
    }

    /* --- Severity border colors --- */
    .severity-critical { border-left: 4px solid #dc2626 !important; }
    .severity-high { border-left: 4px solid #ea580c !important; }
    .severity-medium { border-left: 4px solid #2563eb !important; }
    .severity-low { border-left: 4px solid #64748b !important; }

    /* --- Audit log entry --- */
    .audit-entry {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 4px 0;
    }
    .audit-entry .audit-org {
        background: #f0f4f8;
        color: #1a3c6e;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    /* --- Policy card --- */
    .policy-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 12px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
        transition: box-shadow 0.2s ease;
    }
    .policy-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    .policy-card .policy-title {
        font-weight: 700;
        color: #1a3c6e;
        font-size: 1rem;
    }
    .policy-card .policy-meta {
        color: #64748b;
        font-size: 0.8rem;
        margin-top: 4px;
    }
    .policy-card .policy-hash {
        font-family: 'SF Mono', 'Fira Code', monospace;
        font-size: 0.75rem;
        color: #94a3b8;
        background: #f8fafc;
        padding: 2px 8px;
        border-radius: 4px;
    }
    .policy-card .version-badge {
        background: #eff6ff;
        color: #2563eb;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        border: 1px solid #2563eb20;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


def section_header(step: int, title: str, questions: str = "") -> None:
    """Render a styled questionnaire section header."""
    q_text = f'<span class="step-questions">{escape(questions)}</span>' if questions else ""
    st.markdown(
        f"""
    <div class="q-section-header">
        <div class="step-circle">{step}</div>
        <div class="step-info">
            <span class="step-title">{escape(title)}</span>
            {q_text}
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def status_badge(label: str, color: str = "blue") -> str:
    """Return HTML for a colored status badge."""
    colors = {
        "red": ("#dc2626", "#fef2f2"),
        "orange": ("#ea580c", "#fff7ed"),
        "green": ("#16a34a", "#f0fdf4"),
        "blue": ("#2563eb", "#eff6ff"),
        "gray": ("#64748b", "#f8fafc"),
    }
    fg, bg = colors.get(color, colors["blue"])
    return f'<span style="background:{bg};color:{fg};padding:3px 10px;border-radius:20px;font-size:0.8rem;font-weight:600;border:1px solid {fg}20">{escape(label)}</span>'
