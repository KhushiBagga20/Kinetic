"""
Custom CSS Styles — premium dark-theme financial dashboard aesthetics.

Applied via st.markdown() in the main app.
Features: glassmorphism cards, gradient accents, professional typography,
micro-animations, and responsive layouts.
"""


def get_custom_css() -> str:
    """Return the full custom CSS for the Streamlit app."""
    return """
    <style>
    /* ─── Import Professional Font ─────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ─── Global Styles ────────────────────────────────────────────── */
    .stApp {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, #0a0e17 0%, #121a2e 50%, #0d1520 100%);
    }

    /* ─── Sidebar ──────────────────────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1520 0%, #131b2e 100%);
        border-right: 1px solid rgba(99, 179, 237, 0.1);
    }

    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #63b3ed;
    }

    /* ─── Glassmorphism Cards ──────────────────────────────────────── */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        margin: 12px 0;
        transition: all 0.3s ease;
    }

    .glass-card:hover {
        border-color: rgba(99, 179, 237, 0.3);
        box-shadow: 0 8px 32px rgba(99, 179, 237, 0.1);
        transform: translateY(-2px);
    }

    /* ─── Metric Cards ─────────────────────────────────────────────── */
    .metric-card {
        background: linear-gradient(135deg, rgba(26, 32, 53, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(99, 179, 237, 0.15);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        transition: all 0.3s ease;
    }

    .metric-card:hover {
        border-color: rgba(99, 179, 237, 0.4);
        box-shadow: 0 4px 20px rgba(99, 179, 237, 0.15);
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #e2e8f0;
        margin: 8px 0;
    }

    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .metric-change-positive {
        color: #48bb78;
        font-weight: 600;
    }

    .metric-change-negative {
        color: #fc8181;
        font-weight: 600;
    }

    /* ─── Signal Badge ─────────────────────────────────────────────── */
    .signal-bullish {
        background: linear-gradient(135deg, rgba(72, 187, 120, 0.2), rgba(72, 187, 120, 0.05));
        border: 1px solid rgba(72, 187, 120, 0.4);
        color: #48bb78;
        padding: 8px 20px;
        border-radius: 30px;
        font-weight: 600;
        display: inline-block;
        animation: pulse-green 2s infinite;
    }

    .signal-bearish {
        background: linear-gradient(135deg, rgba(252, 129, 129, 0.2), rgba(252, 129, 129, 0.05));
        border: 1px solid rgba(252, 129, 129, 0.4);
        color: #fc8181;
        padding: 8px 20px;
        border-radius: 30px;
        font-weight: 600;
        display: inline-block;
        animation: pulse-red 2s infinite;
    }

    .signal-neutral {
        background: linear-gradient(135deg, rgba(160, 174, 192, 0.2), rgba(160, 174, 192, 0.05));
        border: 1px solid rgba(160, 174, 192, 0.4);
        color: #a0aec0;
        padding: 8px 20px;
        border-radius: 30px;
        font-weight: 600;
        display: inline-block;
    }

    /* ─── Pulse Animations ─────────────────────────────────────────── */
    @keyframes pulse-green {
        0%, 100% { box-shadow: 0 0 0 0 rgba(72, 187, 120, 0.3); }
        50% { box-shadow: 0 0 0 8px rgba(72, 187, 120, 0); }
    }

    @keyframes pulse-red {
        0%, 100% { box-shadow: 0 0 0 0 rgba(252, 129, 129, 0.3); }
        50% { box-shadow: 0 0 0 8px rgba(252, 129, 129, 0); }
    }

    /* ─── Chat Bubbles ─────────────────────────────────────────────── */
    .chat-user {
        background: linear-gradient(135deg, #2b5797, #1e3a5f);
        color: #e2e8f0;
        padding: 14px 20px;
        border-radius: 18px 18px 4px 18px;
        margin: 8px 0;
        max-width: 80%;
        margin-left: auto;
        font-size: 0.95rem;
    }

    .chat-assistant {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.08);
        color: #e2e8f0;
        padding: 14px 20px;
        border-radius: 18px 18px 18px 4px;
        margin: 8px 0;
        max-width: 80%;
        font-size: 0.95rem;
    }

    /* ─── News Card ────────────────────────────────────────────────── */
    .news-card {
        background: rgba(255, 255, 255, 0.02);
        border-left: 3px solid #63b3ed;
        padding: 12px 16px;
        margin: 8px 0;
        border-radius: 0 8px 8px 0;
        transition: all 0.2s ease;
    }

    .news-card:hover {
        background: rgba(99, 179, 237, 0.05);
        border-left-color: #90cdf4;
    }

    .news-title {
        color: #e2e8f0;
        font-weight: 500;
        font-size: 0.95rem;
        margin-bottom: 4px;
    }

    .news-meta {
        color: #718096;
        font-size: 0.8rem;
    }

    /* ─── Disclaimer Banner ────────────────────────────────────────── */
    .disclaimer-banner {
        background: linear-gradient(135deg, rgba(236, 201, 75, 0.1), rgba(236, 201, 75, 0.02));
        border: 1px solid rgba(236, 201, 75, 0.3);
        border-radius: 12px;
        padding: 16px 20px;
        margin: 16px 0;
        color: #ecc94b;
        font-size: 0.85rem;
        line-height: 1.5;
    }

    /* ─── Streamlit Element Overrides ──────────────────────────────── */
    .stMetric {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 16px;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 10px;
        color: #94a3b8;
        padding: 10px 24px;
        font-weight: 500;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(99, 179, 237, 0.1);
        color: #63b3ed;
    }

    .stTabs [aria-selected="true"] {
        background: rgba(99, 179, 237, 0.15) !important;
        border-color: rgba(99, 179, 237, 0.4) !important;
        color: #63b3ed !important;
    }

    /* ─── Buttons ──────────────────────────────────────────────────── */
    .stButton > button {
        background: linear-gradient(135deg, #2b5797, #1e3a5f);
        color: #e2e8f0;
        border: 1px solid rgba(99, 179, 237, 0.3);
        border-radius: 10px;
        padding: 10px 24px;
        font-weight: 500;
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #3568a8, #2b5797);
        border-color: rgba(99, 179, 237, 0.6);
        box-shadow: 0 4px 16px rgba(99, 179, 237, 0.2);
        transform: translateY(-1px);
    }

    /* ─── Text Inputs ──────────────────────────────────────────────── */
    .stTextInput input, .stTextArea textarea {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        color: #e2e8f0;
    }

    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: rgba(99, 179, 237, 0.5);
        box-shadow: 0 0 0 2px rgba(99, 179, 237, 0.1);
    }

    /* ─── Header Gradient ──────────────────────────────────────────── */
    .main-header {
        background: linear-gradient(135deg, rgba(43, 87, 151, 0.3) 0%, rgba(99, 179, 237, 0.1) 100%);
        border: 1px solid rgba(99, 179, 237, 0.2);
        border-radius: 16px;
        padding: 24px 32px;
        margin-bottom: 24px;
    }

    .main-header h1 {
        background: linear-gradient(135deg, #63b3ed, #90cdf4, #bee3f8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
    }

    .main-header p {
        color: #94a3b8;
        margin: 4px 0 0 0;
    }

    /* ─── Scrollbar ────────────────────────────────────────────────── */
    ::-webkit-scrollbar {
        width: 6px;
    }

    ::-webkit-scrollbar-track {
        background: transparent;
    }

    ::-webkit-scrollbar-thumb {
        background: rgba(99, 179, 237, 0.3);
        border-radius: 3px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: rgba(99, 179, 237, 0.5);
    }

    /* ─── Footer ───────────────────────────────────────────────────── */
    .footer-disclaimer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: rgba(10, 14, 23, 0.95);
        border-top: 1px solid rgba(236, 201, 75, 0.2);
        padding: 8px 16px;
        text-align: center;
        color: #a0aec0;
        font-size: 0.75rem;
        z-index: 999;
        backdrop-filter: blur(10px);
    }
    </style>
    """
