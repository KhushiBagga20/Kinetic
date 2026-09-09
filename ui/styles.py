"""
Kinetic Design System & Custom CSS — Institutional Financial Intelligence Terminal.

Aesthetic: Bloomberg Terminal × Linear × Modern Fintech × Refined Glassmorphism.
Color Palette:
    - Primary Accent: #CDFF9A (Lime — active, positive, focus, metrics)
    - Deep Structural: #203D43 (Deep Slate/Teal — panels, navigation, backgrounds)
    - Neutral Dark: #2A2A2A (Charcoal — secondary surfaces, cards, containers)
    - Alert Accent: #DF4100 (Safety Orange — danger, high risk, negative indicators)
"""


def get_custom_css() -> str:
    """Return the complete institutional terminal CSS for the Streamlit app."""
    return """
    <style>
    /* ─── Typography: IBM Plex Sans & IBM Plex Mono ─────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap');

    /* ─── CSS Variables / Design Tokens ────────────────────────────── */
    :root {
        --k-lime: #CDFF9A;
        --k-lime-dim: rgba(205, 255, 154, 0.12);
        --k-lime-glow: rgba(205, 255, 154, 0.25);
        --k-lime-border: rgba(205, 255, 154, 0.22);
        
        --k-teal: #203D43;
        --k-teal-dark: #13262A;
        --k-teal-canvas: #0E1C1F;
        --k-teal-surface: rgba(32, 61, 67, 0.45);
        --k-teal-border: rgba(32, 61, 67, 0.7);

        --k-charcoal: #2A2A2A;
        --k-charcoal-card: rgba(42, 42, 42, 0.6);
        --k-charcoal-surface: rgba(28, 30, 31, 0.75);

        --k-orange: #DF4100;
        --k-orange-dim: rgba(223, 65, 0, 0.15);
        --k-orange-glow: rgba(223, 65, 0, 0.3);
        --k-orange-border: rgba(223, 65, 0, 0.4);

        --k-text-primary: #F0F6F5;
        --k-text-secondary: #9EB5B7;
        --k-text-muted: #627C80;
        --k-text-dim: #3E5457;

        --k-font-sans: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        --k-font-mono: 'IBM Plex Mono', 'SF Mono', Menlo, Monaco, Consolas, monospace;
    }

    /* ─── App Canvas & Global Reset ────────────────────────────────── */
    .stApp {
        font-family: var(--k-font-sans);
        background-color: var(--k-teal-canvas);
        background-image: 
            radial-gradient(ellipse 80% 50% at 50% -20%, rgba(32, 61, 67, 0.5), transparent 70%),
            radial-gradient(ellipse 60% 40% at 100% 100%, rgba(20, 38, 42, 0.6), transparent),
            linear-gradient(180deg, #0E1C1F 0%, #132427 100%);
        background-attachment: fixed;
        color: var(--k-text-primary);
        letter-spacing: -0.01em;
    }

    /* Subtle technical grid overlay */
    .stApp::before {
        content: "";
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        background-image: 
            linear-gradient(to right, rgba(205, 255, 154, 0.015) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(205, 255, 154, 0.015) 1px, transparent 1px);
        background-size: 48px 48px;
        pointer-events: none;
        z-index: 0;
    }

    /* Target main block wrapper */
    .main .block-container {
        max-width: 1380px;
        padding-top: 2rem;
        padding-bottom: 5rem;
        position: relative;
        z-index: 1;
    }

    /* ─── Sidebar: Institutional Control Panel ─────────────────────── */
    section[data-testid="stSidebar"] {
        background-color: #122225 !important;
        background-image: linear-gradient(180deg, #132427 0%, #0D191B 100%) !important;
        border-right: 1px solid rgba(205, 255, 154, 0.12) !important;
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.35);
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    /* Sidebar headers */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        font-family: var(--k-font-sans);
        color: var(--k-text-primary);
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        font-size: 0.78rem !important;
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
        padding-bottom: 4px;
        border-bottom: 1px solid rgba(205, 255, 154, 0.08);
    }

    /* ─── Top Institutional Navigation Bar ─────────────────────────── */
    .top-navbar-container {
        background: linear-gradient(135deg, rgba(32, 61, 67, 0.75) 0%, rgba(20, 38, 42, 0.9) 100%);
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        border: 1px solid rgba(205, 255, 154, 0.18);
        border-radius: 12px;
        padding: 10px 22px;
        margin-bottom: 22px;
        position: relative;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }

    .top-navbar-container::after {
        content: "";
        position: absolute;
        bottom: 0; left: 0; right: 0; height: 1px;
        background: linear-gradient(90deg, transparent, rgba(205, 255, 154, 0.4), transparent);
    }

    /* Target horizontal radio in main area (Top Navbar) */
    .main div[data-testid="stRadio"] > label {
        display: none !important;
    }

    .main div[data-testid="stRadio"] div[role="radiogroup"] {
        display: flex !important;
        flex-direction: row !important;
        justify-content: center !important;
        align-items: center !important;
        background: rgba(14, 28, 31, 0.85) !important;
        border: 1px solid rgba(205, 255, 154, 0.16) !important;
        border-radius: 8px !important;
        padding: 3px !important;
        gap: 4px !important;
        box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.4) !important;
    }

    .main div[data-testid="stRadio"] label[data-baseweb="radio"] {
        background: transparent !important;
        border: 1px solid transparent !important;
        border-radius: 6px !important;
        padding: 7px 18px !important;
        margin: 0 !important;
        cursor: pointer !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }

    /* Hide the radio circle button */
    .main div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {
        display: none !important;
    }

    /* Nav label text */
    .main div[data-testid="stRadio"] label[data-baseweb="radio"] p {
        font-family: var(--k-font-sans) !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        color: var(--k-text-secondary) !important;
        letter-spacing: 0.02em !important;
        margin: 0 !important;
        white-space: nowrap !important;
    }

    /* Hover */
    .main div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {
        background: rgba(32, 61, 67, 0.5) !important;
    }

    .main div[data-testid="stRadio"] label[data-baseweb="radio"]:hover p {
        color: #FFFFFF !important;
    }

    /* Active selected nav item */
    .main div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
        background: linear-gradient(135deg, rgba(32, 61, 67, 0.95) 0%, rgba(20, 38, 42, 0.95) 100%) !important;
        border: 1px solid var(--k-lime-border) !important;
        box-shadow: 0 0 14px rgba(205, 255, 154, 0.16) !important;
    }

    .main div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p {
        color: var(--k-lime) !important;
        font-weight: 600 !important;
    }

    /* ─── Navigation Radio (Sidebar Fallback) ───────────────────────── */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > label {
        display: none;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] {
        gap: 6px;
        display: flex;
        flex-direction: column;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"] {
        background: rgba(32, 61, 67, 0.3);
        border: 1px solid rgba(205, 255, 154, 0.08);
        border-radius: 8px;
        padding: 10px 14px;
        margin: 0;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        cursor: pointer;
        width: 100%;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {
        background: rgba(32, 61, 67, 0.6);
        border-color: rgba(205, 255, 154, 0.3);
        transform: translateX(2px);
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
        background: rgba(32, 61, 67, 0.85);
        border-color: var(--k-lime);
        box-shadow: 0 0 12px rgba(205, 255, 154, 0.15), inset 0 0 0 1px rgba(205, 255, 154, 0.2);
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"] span {
        font-family: var(--k-font-sans);
        font-size: 0.88rem;
        font-weight: 500;
        color: var(--k-text-primary);
    }

    /* ─── Typography & Headings ────────────────────────────────────── */
    h1, h2, h3, h4, h5, h6 {
        font-family: var(--k-font-sans);
        color: var(--k-text-primary);
        font-weight: 600;
        letter-spacing: -0.02em;
    }

    p, span, div {
        color: var(--k-text-secondary);
    }

    code, pre {
        font-family: var(--k-font-mono) !important;
        font-size: 0.85rem;
    }

    hr {
        border-color: rgba(205, 255, 154, 0.08) !important;
        margin: 1.5rem 0 !important;
    }

    /* ─── Institutional Terminal Header ────────────────────────────── */
    .terminal-header {
        background: linear-gradient(135deg, rgba(32, 61, 67, 0.7) 0%, rgba(20, 38, 42, 0.85) 100%);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(205, 255, 154, 0.18);
        border-radius: 12px;
        padding: 20px 26px;
        margin-bottom: 24px;
        position: relative;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
    }

    .terminal-header::after {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0; height: 1px;
        background: linear-gradient(90deg, transparent, var(--k-lime), transparent);
        opacity: 0.6;
    }

    .terminal-title-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 12px;
    }

    .terminal-title {
        display: flex;
        align-items: center;
        gap: 12px;
        font-family: var(--k-font-sans);
        font-size: 1.6rem;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -0.03em;
        margin: 0;
    }

    .terminal-badge {
        font-family: var(--k-font-mono);
        font-size: 0.68rem;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 4px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        background: var(--k-lime-dim);
        color: var(--k-lime);
        border: 1px solid var(--k-lime-border);
    }

    .terminal-status-strip {
        display: flex;
        align-items: center;
        gap: 18px;
        font-family: var(--k-font-mono);
        font-size: 0.75rem;
        color: var(--k-text-muted);
    }

    .terminal-status-item {
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .pulse-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: var(--k-lime);
        box-shadow: 0 0 8px var(--k-lime);
        animation: terminal-pulse 2s infinite ease-in-out;
    }

    @keyframes terminal-pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(0.85); }
    }

    .terminal-subtext {
        font-family: var(--k-font-mono);
        font-size: 0.78rem;
        color: var(--k-text-secondary);
        margin: 6px 0 0 0;
        letter-spacing: 0.02em;
    }

    /* ─── Glassmorphism Panels & Cards ─────────────────────────────── */
    .glass-card, .terminal-panel {
        background: linear-gradient(135deg, rgba(42, 42, 42, 0.4) 0%, rgba(32, 61, 67, 0.25) 100%);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(205, 255, 154, 0.1);
        border-radius: 12px;
        padding: 22px;
        margin: 14px 0;
        position: relative;
        transition: border-color 0.25s ease, box-shadow 0.25s ease, transform 0.25s ease;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }

    .glass-card:hover, .terminal-panel:hover {
        border-color: rgba(205, 255, 154, 0.24);
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35), 0 0 16px rgba(205, 255, 154, 0.06);
    }

    .terminal-panel-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 16px;
        padding-bottom: 10px;
        border-bottom: 1px solid rgba(205, 255, 154, 0.08);
    }

    .terminal-panel-title {
        font-family: var(--k-font-sans);
        font-size: 0.92rem;
        font-weight: 600;
        color: var(--k-text-primary);
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .terminal-panel-meta {
        font-family: var(--k-font-mono);
        font-size: 0.72rem;
        color: var(--k-text-muted);
    }

    /* ─── Financial Stock / Metric Cards ───────────────────────────── */
    .metric-card, .stock-tile {
        background: linear-gradient(145deg, rgba(32, 61, 67, 0.5) 0%, rgba(42, 42, 42, 0.5) 100%);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1px solid rgba(205, 255, 154, 0.12);
        border-radius: 10px;
        padding: 16px 18px;
        transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
        position: relative;
        overflow: hidden;
        margin-bottom: 10px;
    }

    .metric-card:hover, .stock-tile:hover {
        border-color: rgba(205, 255, 154, 0.35);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3), 0 0 12px rgba(205, 255, 154, 0.08);
    }

    .stock-tile-top {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        margin-bottom: 8px;
    }

    .stock-symbol {
        font-family: var(--k-font-mono);
        font-size: 1.05rem;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: 0.02em;
    }

    .stock-company {
        font-family: var(--k-font-sans);
        font-size: 0.74rem;
        color: var(--k-text-muted);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 140px;
        margin-top: 1px;
    }

    .stock-price {
        font-family: var(--k-font-mono);
        font-size: 1.55rem;
        font-weight: 700;
        color: var(--k-text-primary);
        letter-spacing: -0.02em;
        margin: 6px 0;
    }

    .stock-delta-pill {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-family: var(--k-font-mono);
        font-size: 0.78rem;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 4px;
    }

    .delta-positive {
        background: var(--k-lime-dim);
        color: var(--k-lime);
        border: 1px solid var(--k-lime-border);
    }

    .delta-negative {
        background: var(--k-orange-dim);
        color: var(--k-orange);
        border: 1px solid var(--k-orange-border);
    }

    .metric-label {
        font-family: var(--k-font-sans);
        font-size: 0.72rem;
        color: var(--k-text-muted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600;
        margin-bottom: 4px;
    }

    .metric-value {
        font-family: var(--k-font-mono);
        font-size: 1.7rem;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -0.02em;
    }

    .metric-change-positive {
        font-family: var(--k-font-mono);
        color: var(--k-lime);
        font-weight: 600;
        font-size: 0.82rem;
    }

    .metric-change-negative {
        font-family: var(--k-font-mono);
        color: var(--k-orange);
        font-weight: 600;
        font-size: 0.82rem;
    }

    /* ─── Signal Badges (Institutional Style) ───────────────────────── */
    .signal-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 16px;
        border-radius: 6px;
        font-family: var(--k-font-mono);
        font-size: 0.88rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }

    .signal-bullish {
        background: rgba(205, 255, 154, 0.15);
        border: 1px solid var(--k-lime);
        color: var(--k-lime);
        box-shadow: 0 0 14px rgba(205, 255, 154, 0.25);
    }

    .signal-bearish {
        background: rgba(223, 65, 0, 0.15);
        border: 1px solid var(--k-orange);
        color: var(--k-orange);
        box-shadow: 0 0 14px rgba(223, 65, 0, 0.25);
    }

    .signal-neutral {
        background: rgba(158, 181, 183, 0.12);
        border: 1px solid rgba(158, 181, 183, 0.35);
        color: var(--k-text-secondary);
    }

    /* ─── News Intel Feed ──────────────────────────────────────────── */
    .news-card, .intel-feed-item {
        background: rgba(42, 42, 42, 0.35);
        border: 1px solid rgba(205, 255, 154, 0.08);
        border-left: 3px solid var(--k-lime);
        padding: 14px 18px;
        margin: 10px 0;
        border-radius: 0 8px 8px 0;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .news-card:hover, .intel-feed-item:hover {
        background: rgba(32, 61, 67, 0.4);
        border-color: rgba(205, 255, 154, 0.25);
        border-left-color: var(--k-lime);
        transform: translateX(3px);
    }

    .news-title {
        color: var(--k-text-primary);
        font-family: var(--k-font-sans);
        font-weight: 500;
        font-size: 0.93rem;
        line-height: 1.45;
        margin-bottom: 6px;
    }

    .news-meta {
        font-family: var(--k-font-mono);
        color: var(--k-text-muted);
        font-size: 0.74rem;
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .news-meta a {
        color: var(--k-lime) !important;
        text-decoration: none;
        font-weight: 600;
        transition: color 0.2s ease;
    }

    .news-meta a:hover {
        color: #FFFFFF !important;
        text-decoration: underline;
    }

    /* ─── Institutional Analyst Workstation (Chat) ─────────────────── */
    .chat-user {
        background: linear-gradient(135deg, rgba(32, 61, 67, 0.75) 0%, rgba(20, 38, 42, 0.9) 100%);
        border: 1px solid rgba(205, 255, 154, 0.2);
        color: #FFFFFF;
        padding: 14px 18px;
        border-radius: 10px 10px 2px 10px;
        margin: 12px 0 12px auto;
        max-width: 82%;
        font-family: var(--k-font-sans);
        font-size: 0.92rem;
        line-height: 1.5;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
        position: relative;
    }

    .chat-user::before {
        content: "// USER QUERY";
        display: block;
        font-family: var(--k-font-mono);
        font-size: 0.65rem;
        color: var(--k-lime);
        letter-spacing: 0.1em;
        margin-bottom: 4px;
        font-weight: 600;
    }

    .chat-assistant {
        background: linear-gradient(135deg, rgba(42, 42, 42, 0.7) 0%, rgba(28, 42, 45, 0.6) 100%);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(205, 255, 154, 0.12);
        border-left: 3px solid var(--k-lime);
        color: var(--k-text-primary);
        padding: 16px 20px;
        border-radius: 2px 10px 10px 10px;
        margin: 12px auto 12px 0;
        max-width: 90%;
        font-family: var(--k-font-sans);
        font-size: 0.92rem;
        line-height: 1.6;
        box-shadow: 0 6px 24px rgba(0, 0, 0, 0.35);
    }

    .chat-assistant::before {
        content: "// KINETIC RESEARCH AGENT // SYNTHESIS";
        display: block;
        font-family: var(--k-font-mono);
        font-size: 0.65rem;
        color: var(--k-lime);
        letter-spacing: 0.1em;
        margin-bottom: 8px;
        font-weight: 600;
    }

    /* ─── Quick Ask Action Buttons ─────────────────────────────────── */
    .quick-ask-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 12px;
        margin: 16px 0;
    }

    /* ─── Streamlit Tabs Overrides ─────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background: rgba(14, 28, 31, 0.6);
        border: 1px solid rgba(205, 255, 154, 0.1);
        border-radius: 8px;
        padding: 4px;
        margin-bottom: 18px;
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border: 1px solid transparent;
        border-radius: 6px;
        color: var(--k-text-secondary);
        padding: 8px 18px;
        font-family: var(--k-font-sans);
        font-size: 0.85rem;
        font-weight: 500;
        letter-spacing: 0.02em;
        transition: all 0.2s ease;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(32, 61, 67, 0.5);
        color: var(--k-lime);
    }

    .stTabs [aria-selected="true"] {
        background: var(--k-teal) !important;
        border: 1px solid var(--k-lime-border) !important;
        color: var(--k-lime) !important;
        font-weight: 600 !important;
        box-shadow: 0 0 10px rgba(205, 255, 154, 0.12) !important;
    }

    /* ─── Streamlit Button Overrides ───────────────────────────────── */
    .stButton > button {
        background: linear-gradient(135deg, #203D43 0%, #172D32 100%) !important;
        color: var(--k-lime) !important;
        border: 1px solid var(--k-lime-border) !important;
        border-radius: 8px !important;
        padding: 8px 20px !important;
        font-family: var(--k-font-mono) !important;
        font-size: 0.84rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.04em !important;
        transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #2A5159 0%, #203D43 100%) !important;
        border-color: var(--k-lime) !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 18px rgba(205, 255, 154, 0.2) !important;
        transform: translateY(-1px);
    }

    .stButton > button:active {
        transform: translateY(1px);
    }

    /* Primary execute button variant */
    div[data-testid="stForm"] .stButton > button,
    button[kind="primary"] {
        background: var(--k-lime) !important;
        color: #0E1C1F !important;
        border: 1px solid var(--k-lime) !important;
        font-weight: 700 !important;
    }

    div[data-testid="stForm"] .stButton > button:hover,
    button[kind="primary"]:hover {
        background: #DCFFB5 !important;
        box-shadow: 0 4px 20px rgba(205, 255, 154, 0.4) !important;
    }

    /* ─── Input & Select Overrides ─────────────────────────────────── */
    .stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] {
        background-color: rgba(19, 36, 39, 0.8) !important;
        border: 1px solid rgba(205, 255, 154, 0.15) !important;
        border-radius: 8px !important;
        color: #FFFFFF !important;
        font-family: var(--k-font-mono) !important;
        font-size: 0.88rem !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }

    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: var(--k-lime) !important;
        box-shadow: 0 0 0 2px rgba(205, 255, 154, 0.2) !important;
    }

    .stSelectbox [data-baseweb="select"] > div {
        background-color: transparent !important;
        border: none !important;
        color: #FFFFFF !important;
        font-family: var(--k-font-mono) !important;
    }

    /* Slider styling */
    .stSlider [data-baseweb="slider"] {
        margin: 10px 0;
    }

    /* ─── Chat Input Override ──────────────────────────────────────── */
    .stChatInput {
        background-color: transparent !important;
    }

    .stChatInput > div {
        background-color: rgba(19, 36, 39, 0.9) !important;
        border: 1px solid rgba(205, 255, 154, 0.25) !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4) !important;
    }

    .stChatInput textarea {
        font-family: var(--k-font-sans) !important;
        color: #FFFFFF !important;
    }

    .stChatInput textarea:focus {
        border-color: var(--k-lime) !important;
    }

    /* ─── Disclaimer Banner ────────────────────────────────────────── */
    .disclaimer-banner {
        background: linear-gradient(135deg, rgba(223, 65, 0, 0.08) 0%, rgba(42, 42, 42, 0.4) 100%);
        border: 1px solid var(--k-orange-border);
        border-left: 4px solid var(--k-orange);
        border-radius: 8px;
        padding: 12px 18px;
        margin: 16px 0;
        color: #FFA585;
        font-family: var(--k-font-mono);
        font-size: 0.76rem;
        line-height: 1.5;
        display: flex;
        align-items: flex-start;
        gap: 12px;
    }

    .disclaimer-banner strong {
        color: var(--k-orange);
    }

    /* ─── Metric Widget Overrides ──────────────────────────────────── */
    div[data-testid="stMetric"] {
        background: rgba(32, 61, 67, 0.45);
        border: 1px solid rgba(205, 255, 154, 0.12);
        border-radius: 8px;
        padding: 12px 16px;
    }

    div[data-testid="stMetricLabel"] {
        font-family: var(--k-font-sans);
        font-size: 0.74rem !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--k-text-muted) !important;
    }

    div[data-testid="stMetricValue"] {
        font-family: var(--k-font-mono);
        color: #FFFFFF !important;
        font-size: 1.4rem !important;
    }

    /* ─── Expander Overrides ────────────────────────────────────────── */
    div[data-testid="stExpander"] {
        background: rgba(42, 42, 42, 0.4);
        border: 1px solid rgba(205, 255, 154, 0.1);
        border-radius: 8px;
        overflow: hidden;
    }

    div[data-testid="stExpander"] summary {
        font-family: var(--k-font-mono);
        font-size: 0.82rem;
        color: var(--k-text-secondary);
    }

    div[data-testid="stExpander"] summary:hover {
        color: var(--k-lime);
    }

    /* ─── Code Block Overrides ─────────────────────────────────────── */
    .stCodeBlock, pre {
        background-color: #0B1618 !important;
        border: 1px solid rgba(205, 255, 154, 0.1) !important;
        border-radius: 8px !important;
    }

    /* ─── Scrollbar Customization ──────────────────────────────────── */
    ::-webkit-scrollbar {
        width: 5px;
        height: 5px;
    }

    ::-webkit-scrollbar-track {
        background: rgba(14, 28, 31, 0.8);
    }

    ::-webkit-scrollbar-thumb {
        background: rgba(205, 255, 154, 0.2);
        border-radius: 3px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--k-lime);
    }

    /* ─── Fixed Institutional Footer ───────────────────────────────── */
    .footer-disclaimer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: rgba(14, 28, 31, 0.94);
        border-top: 1px solid rgba(205, 255, 154, 0.12);
        padding: 7px 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        color: var(--k-text-muted);
        font-family: var(--k-font-mono);
        font-size: 0.70rem;
        letter-spacing: 0.02em;
        z-index: 999;
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
    }

    .footer-tag {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        color: var(--k-lime);
        font-weight: 600;
    }

    /* ─── Terminal Data Table ──────────────────────────────────────── */
    .terminal-table {
        width: 100%;
        border-collapse: collapse;
        font-family: var(--k-font-mono);
        font-size: 0.82rem;
        margin: 12px 0;
    }

    .terminal-table th {
        text-align: left;
        padding: 8px 12px;
        color: var(--k-text-muted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.70rem;
        border-bottom: 1px solid rgba(205, 255, 154, 0.15);
    }

    .terminal-table td {
        padding: 10px 12px;
        border-bottom: 1px solid rgba(205, 255, 154, 0.05);
        color: var(--k-text-primary);
    }

    .terminal-table tr:hover td {
        background: rgba(205, 255, 154, 0.03);
    }
    </style>
    """
