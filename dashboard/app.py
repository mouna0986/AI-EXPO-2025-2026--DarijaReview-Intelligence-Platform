import http

import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import plotly.io as pio
import requests
import urllib.parse

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
API_BASE = "http://127.0.0.1:8000/api"

# ── RAMY PALETTE (exact from Edition Limitée photo) ──
C_RED    = "#C8102E"   # Ramy logo red
C_RED2   = "#E63946"   # brighter red
C_GREEN  = "#1A6B2F"   # Algerian flag green
C_GOLD   = "#C8960A"   # zellige gold ground
C_GOLD2  = "#D4AF37"   # accent gold
C_PEACH  = "#F4A03A"   # orange-peach fruit
C_WHITE  = "#FFFDF5"   # warm white

# Dashboard colors
COLOR_BG       = "#FFF8E8"          # warm parchment — the "light" base
COLOR_SURFACE  = "rgba(255,253,245,0.78)"
COLOR_GLASS    = "rgba(255,253,240,0.65)"
COLOR_BORDER   = "rgba(200,150,10,0.35)"
COLOR_BORDER_H = "rgba(200,150,10,0.7)"
COLOR_TEXT     = "#1C0800"
COLOR_MUTED    = "#7A5520"
COLOR_POSITIVE = "#1A6B2F"
COLOR_NEGATIVE = C_RED
COLOR_NEUTRAL  = "#B87816"


# ─────────────────────────────────────────────
# ZELLIGE SVG TILE — matching the Ramy photo
# Red 12-pt stars + green octagons + gold ground
# Bright & vibrant, 240×240 repeat tile
# ─────────────────────────────────────────────
_ZELLIGE_RAW = """<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240' viewBox='0 0 240 240'>
<rect width='240' height='240' fill='%23C8960A'/>
<polygon points='120,6 132,38 164,22 156,56 190,48 178,80 212,82 194,110 214,136 188,136 198,170 164,158 158,192 132,172 120,204 108,172 82,192 76,158 42,170 52,136 26,136 46,110 28,82 62,80 50,48 84,56 76,22 108,38' fill='%23C8102E' stroke='%23FFF8E8' stroke-width='1.5'/>
<polygon points='120,44 140,60 152,82 152,118 140,140 120,156 100,140 88,118 88,82 100,60' fill='%231A6B2F' stroke='%23D4AF37' stroke-width='1.8'/>
<polygon points='120,72 136,96 120,120 104,96' fill='%23D4AF37' stroke='%23FFF8E8' stroke-width='1.2'/>
<polygon points='0,0 18,24 44,10 36,40 64,38 52,66 78,72 58,94 76,116 50,114 60,142 34,130 28,158 8,142 0,170' fill='%23C8102E' stroke='%23FFF8E8' stroke-width='1.2' opacity='0.9'/>
<polygon points='0,0 10,42 44,34 38,66 0,62' fill='%231A6B2F' stroke='%23D4AF37' stroke-width='1.5' opacity='0.9'/>
<polygon points='240,0 222,24 196,10 204,40 176,38 188,66 162,72 182,94 164,116 190,114 180,142 206,130 212,158 232,142 240,170' fill='%23C8102E' stroke='%23FFF8E8' stroke-width='1.2' opacity='0.9'/>
<polygon points='240,0 230,42 196,34 202,66 240,62' fill='%231A6B2F' stroke='%23D4AF37' stroke-width='1.5' opacity='0.9'/>
<polygon points='0,240 18,216 44,230 36,200 64,202 52,174 78,168 58,146 76,124 50,126 60,98 34,110 28,82 8,98 0,70' fill='%23C8102E' stroke='%23FFF8E8' stroke-width='1.2' opacity='0.9'/>
<polygon points='0,240 10,198 44,206 38,174 0,178' fill='%231A6B2F' stroke='%23D4AF37' stroke-width='1.5' opacity='0.9'/>
<polygon points='240,240 222,216 196,230 204,200 176,202 188,174 162,168 182,146 164,124 190,126 180,98 206,110 212,82 232,98 240,70' fill='%23C8102E' stroke='%23FFF8E8' stroke-width='1.2' opacity='0.9'/>
<polygon points='240,240 230,198 196,206 202,174 240,178' fill='%231A6B2F' stroke='%23D4AF37' stroke-width='1.5' opacity='0.9'/>
<polygon points='120,6 126,20 138,12 134,26 148,22 142,36 156,38 146,50 154,62 140,60 142,74 128,68 126,82 118,72 120,86 112,72 114,82 100,68 98,74 84,60 92,62 82,50 96,38 90,36 84,22 98,26 94,12 106,20' fill='%23D4AF37' stroke='%23FFF8E8' stroke-width='0.8' opacity='0.75'/>
<line x1='120' y1='0' x2='120' y2='240' stroke='%23D4AF37' stroke-width='0.6' opacity='0.35'/>
<line x1='0' y1='120' x2='240' y2='120' stroke='%23D4AF37' stroke-width='0.6' opacity='0.35'/>
<line x1='0' y1='0' x2='240' y2='240' stroke='%23FFF8E8' stroke-width='0.4' opacity='0.15'/>
<line x1='240' y1='0' x2='0' y2='240' stroke='%23FFF8E8' stroke-width='0.4' opacity='0.15'/>
</svg>"""

ZELLIGE_URL = "data:image/svg+xml," + urllib.parse.quote(_ZELLIGE_RAW.replace("\n", "").replace("  ", " "))


# ─────────────────────────────────────────────
# STAT CARD IMAGE SLOTS
# Replace these with your real image URLs!
# Each key maps to: (emoji_fallback, label)
# ─────────────────────────────────────────────
CARD_IMAGES = {
    "total":    {"url": None,  "emoji": "📋", "fruit": "🍹"},
    "positive": {"url": None,  "emoji": "😊", "fruit": "🍑"},   # → swap url with peach/can PNG
    "negative": {"url": None,  "emoji": "😞", "fruit": "🍊"},   # → swap url with orange/can PNG
    "neutral":  {"url": None,  "emoji": "😐", "fruit": "🫐"},   # → swap url with blueberry/can PNG
}
# Example: "url": "https://your-cdn.com/ramy-can-peach.png"


# ─────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────
GLOBAL_CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,700;0,9..144,900;1,9..144,800&family=DM+Sans:wght@300;400;500;600&display=swap');

*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ font-family: 'DM Sans', sans-serif; color-scheme: light; }}

/* ═══════════════════════════════════════════
   BODY: bright zellige matching the Ramy photo
   Warm golden light overlay so it's vibrant
   but cards remain readable
   ═══════════════════════════════════════════ */
body {{
    background-color: {COLOR_BG};
    background-image:
        linear-gradient(160deg,
            rgba(255,220,120,0.38) 0%,
            rgba(255,253,240,0.22) 35%,
            rgba(255,200,80,0.18) 70%,
            rgba(240,160,60,0.25) 100%
        ),
        url("{ZELLIGE_URL}");
    background-size: cover, 240px 240px;
    background-attachment: fixed, fixed;
    background-repeat: no-repeat, repeat;
    min-height: 100vh;
}}

/* ═══════════════════════════════════════════
   GLASS CARDS — warm frosted glass
   Semi-transparent over the zellige
   ═══════════════════════════════════════════ */
.glass {{
    background: {COLOR_GLASS};
    border: 1.5px solid {COLOR_BORDER};
    border-radius: 22px;
    backdrop-filter: blur(18px) saturate(160%) brightness(1.08);
    -webkit-backdrop-filter: blur(18px) saturate(160%) brightness(1.08);
    box-shadow:
        0 2px 0 rgba(255,255,220,0.9) inset,
        0 -1px 0 rgba(180,130,0,0.15) inset,
        0 8px 32px rgba(180,110,0,0.14),
        0 2px 8px rgba(0,0,0,0.06);
    position: relative;
    overflow: hidden;
    transition: all 0.38s cubic-bezier(0.34,1.56,0.64,1);
}}
.glass::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1.5px;
    background: linear-gradient(90deg, transparent, rgba(255,240,160,0.95) 40%, rgba(212,175,55,0.85) 60%, transparent);
    pointer-events: none;
}}
.glass:hover {{
    transform: translateY(-5px);
    border-color: {COLOR_BORDER_H};
    box-shadow:
        0 2px 0 rgba(255,255,220,0.95) inset,
        0 -1px 0 rgba(180,130,0,0.2) inset,
        0 20px 50px rgba(180,110,0,0.22),
        0 4px 12px rgba(0,0,0,0.1);
}}

/* ═══════════════════════════════════════════
   STAT CARDS — image ghost + emoji watermark
   ═══════════════════════════════════════════ */
.stat-card {{ padding: 26px 22px 20px; flex: 1; min-width: 175px; cursor: default; }}

/* Ghost fruit image — swap with real PNG URLs via inline style */
.card-img-ghost {{
    position: absolute;
    right: -14px;
    bottom: -18px;
    width: 110px;
    height: 110px;
    object-fit: contain;
    opacity: 0.13;
    filter: saturate(1.3) blur(0.3px);
    transform: rotate(-8deg);
    pointer-events: none;
    user-select: none;
    transition: opacity 0.35s, transform 0.35s;
}}
.glass:hover .card-img-ghost {{
    opacity: 0.25;
    transform: rotate(-3deg) scale(1.08) translateY(-4px);
}}

/* Emoji fallback (when no image URL provided) */
.card-emoji-ghost {{
    position: absolute;
    right: -8px;
    bottom: -12px;
    font-size: 80px;
    line-height: 1;
    opacity: 0.13;
    transform: rotate(-8deg);
    pointer-events: none;
    user-select: none;
    filter: blur(0.5px) saturate(1.2);
    transition: opacity 0.35s, transform 0.35s;
}}
.glass:hover .card-emoji-ghost {{
    opacity: 0.26;
    transform: rotate(-3deg) scale(1.1);
}}

/* Water splash / fruit scatter decoration strip at top of each card */
.card-fruit-strip {{
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 5px;
    border-radius: 22px 22px 0 0;
}}

/* ═══════════════════════════════════════════
   REVIEW BUBBLES
   ═══════════════════════════════════════════ */
.r-bubble {{
    background: rgba(255,253,240,0.6);
    border: 1.5px solid rgba(200,150,10,0.28);
    border-left: 4px solid {C_RED};
    border-radius: 16px;
    padding: 14px 18px;
    margin-bottom: 10px;
    cursor: default;
    transition: all 0.3s ease;
}}
.r-bubble.pos {{ border-left-color: {C_GREEN}; }}
.r-bubble:hover {{
    transform: translateX(5px);
    background: rgba(255,253,240,0.88);
    border-color: rgba(200,150,10,0.6);
    box-shadow: 0 4px 18px rgba(180,110,0,0.16);
}}

/* ═══════════════════════════════════════════
   PRICE TABLE
   ═══════════════════════════════════════════ */
.p-row {{ transition: background 0.2s ease; cursor: default; }}
.p-row:hover td {{ background: rgba(212,175,55,0.12) !important; }}

/* ═══════════════════════════════════════════
   ANALYZE BUTTON
   ═══════════════════════════════════════════ */
.analyze-btn {{ transition: all 0.3s cubic-bezier(0.34,1.56,0.64,1); }}
.analyze-btn:hover {{
    transform: translateY(-4px) scale(1.04) !important;
    box-shadow: 0 14px 36px rgba(200,16,46,0.48) !important;
}}
.analyze-btn:active {{ transform: scale(0.97) !important; }}

.review-ta {{ transition: border-color 0.25s, box-shadow 0.25s; }}
.review-ta:focus {{
    border-color: {C_GOLD2} !important;
    box-shadow: 0 0 0 3px rgba(212,175,55,0.22) !important;
    outline: none;
}}

/* ═══════════════════════════════════════════
   SENTIMENT EMOJI BADGES
   ═══════════════════════════════════════════ */
.sentiment-emoji {{
    display: inline-flex; align-items: center; justify-content: center;
    width: 36px; height: 36px; border-radius: 50%;
    font-size: 20px; flex-shrink: 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.12);
}}
.emoji-pos {{ background: rgba(26,107,47,0.14); border: 2px solid rgba(26,107,47,0.38); }}
.emoji-neg {{ background: rgba(200,16,46,0.12); border: 2px solid rgba(200,16,46,0.35); }}

/* ═══════════════════════════════════════════
   ANIMATIONS
   ═══════════════════════════════════════════ */
@keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0.2}} }}
.live-dot {{ animation: blink 1.6s ease-in-out infinite; }}

@keyframes fadeUp {{ from{{opacity:0;transform:translateY(22px)}} to{{opacity:1;transform:translateY(0)}} }}
.f1{{animation:fadeUp 0.55s 0.00s ease both}}
.f2{{animation:fadeUp 0.55s 0.10s ease both}}
.f3{{animation:fadeUp 0.55s 0.20s ease both}}
.f4{{animation:fadeUp 0.55s 0.30s ease both}}

@keyframes shimmer {{
    0%   {{ background-position: -300% center; }}
    100% {{ background-position: 300% center; }}
}}
.shimmer-text {{
    background: linear-gradient(90deg, {C_RED} 0%, {C_GOLD2} 35%, {C_RED} 55%, {C_GREEN} 80%, {C_GOLD2} 100%);
    background-size: 300% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: shimmer 4s linear infinite;
}}

/* Decorative gold divider */
.gold-bar {{
    height: 1.5px;
    background: linear-gradient(90deg, transparent, {C_GOLD2} 20%, {C_RED} 50%, {C_GREEN} 80%, transparent);
    border-radius: 2px;
    opacity: 0.55;
    margin-bottom: 18px;
}}

/* Section heading */
.sec-title {{
    font-family: 'Fraunces', serif;
    font-size: 17px; font-weight: 800;
    color: {COLOR_TEXT};
    margin-bottom: 14px;
}}

/* Scrollbar */
::-webkit-scrollbar {{ width: 5px; }}
::-webkit-scrollbar-track {{ background: rgba(200,150,10,0.08); }}
::-webkit-scrollbar-thumb {{ background: rgba(200,150,10,0.35); border-radius: 3px; }}
"""


# ─────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────
app = dash.Dash(__name__, title="DarijaReview Intelligence — Ramy 🧃",
                suppress_callback_exceptions=True)

pio.templates.default = "plotly_white"
pio.templates["plotly_white"].layout.paper_bgcolor = "rgba(0,0,0,0)"
pio.templates["plotly_white"].layout.plot_bgcolor  = "rgba(0,0,0,0)"

app.index_string = f"""<!DOCTYPE html>
<html>
<head>
    {{%metas%}}
    <title>{{%title%}}</title>
    {{%favicon%}}
    {{%css%}}
    <style>{GLOBAL_CSS}</style>
</head>
<body>
    {{%app_entry%}}
    <footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer>
</body>
</html>"""


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def fetch(endpoint):
    try:
        r = requests.get(f"{API_BASE}/{endpoint}", timeout=5)
        return r.json()
    except Exception as e:
        print(f"API error on {endpoint}: {e}")
        return None


def card_ghost(key):
    """
    Returns either an <img> ghost (if URL provided) or an emoji ghost.
    To use real images: set CARD_IMAGES[key]["url"] = "https://..."
    """
    cfg = CARD_IMAGES.get(key, {})
    url = cfg.get("url")
    if url:
        return html.Img(
            src=url,
            className="card-img-ghost",
            # Override position/sizing here if needed per card
        )
    else:
        # Emoji fallback until you link real images
        return html.Div(
            cfg.get("fruit", "🍊"),
            className="card-emoji-ghost"
        )


def stat_card(key, title, value, value_color, subtitle, stripe_color, anim="f1"):
    """
    Glassmorphism stat card.
    Ghost image slot ready — just update CARD_IMAGES[key]["url"].
    """
    return html.Div([
        # Colored top stripe
        html.Div(className="card-fruit-strip", style={
            "background": f"linear-gradient(90deg, {stripe_color}, {C_GOLD2}, {stripe_color})"
        }),
        # Ghost image / emoji watermark
        card_ghost(key),
        # Label
        html.P(title, style={
            "fontSize": "10px", "fontWeight": "600", "color": COLOR_MUTED,
            "textTransform": "uppercase", "letterSpacing": "2.5px",
            "marginBottom": "12px", "position": "relative", "zIndex": "1"
        }),
        # Big metric value
        html.H2(value, style={
            "fontSize": "50px", "fontWeight": "900",
            "color": value_color, "fontFamily": "'Fraunces', serif",
            "lineHeight": "1", "marginBottom": "6px",
            "textShadow": "0 1px 10px rgba(0,0,0,0.08)",
            "position": "relative", "zIndex": "1",
        }),
        # Subtitle
        html.P(subtitle, style={
            "fontSize": "11px", "color": COLOR_MUTED, "fontWeight": "300",
            "position": "relative", "zIndex": "1",
        }),
    ], className=f"glass stat-card {anim}")


def section_title(text):
    return html.P(text, className="sec-title")


def gold_divider():
    return html.Div(className="gold-bar")


def glass_card(children, extra=None, anim=""):
    style = {"padding": "26px"}
    if extra:
        style.update(extra)
    return html.Div(children, className=f"glass {anim}", style=style)


# ─────────────────────────────────────────────
# LAYOUT
# ─────────────────────────────────────────────
app.layout = html.Div([

    # ══ HEADER ══════════════════════════════════════════════════════
    html.Div([
        html.Div([

            # Left — logo + wordmark
            html.Div([
                html.Span("🧃", style={
                    "fontSize": "36px",
                    "filter": "drop-shadow(0 2px 6px rgba(200,16,46,0.35))"
                }),
                html.Div([
                    html.P("RAMY · الجزائر", style={
                        "margin": "0", "fontSize": "9px", "fontWeight": "700",
                        "color": C_GOLD, "letterSpacing": "5px"
                    }),
                    html.H1([
                        html.Span("Darija", style={"color": C_RED}),
                        html.Span("Review", style={"color": COLOR_TEXT}),
                        html.Span(" Intelligence", className="shimmer-text"),
                    ], style={
                        "margin": "0", "fontSize": "22px", "fontWeight": "900",
                        "fontFamily": "'Fraunces', serif", "lineHeight": "1.15",
                    }),
                    html.P("الذكاء الاصطناعي · Edition Limitée · AI EXPO 2026", style={
                        "margin": "0", "fontSize": "9px", "color": COLOR_MUTED,
                        "fontWeight": "300", "letterSpacing": "1.5px"
                    }),
                ]),
            ], style={"display": "flex", "alignItems": "center", "gap": "14px"}),

            # Right — live badge
            html.Div([
                html.Div([
                    html.Div(className="live-dot", style={
                        "width": "8px", "height": "8px", "borderRadius": "50%",
                        "backgroundColor": C_GREEN,
                        "boxShadow": f"0 0 8px {C_GREEN}"
                    }),
                    html.Span("LIVE", style={
                        "color": C_GREEN, "fontWeight": "700",
                        "fontSize": "11px", "letterSpacing": "2px"
                    })
                ], style={
                    "display": "flex", "alignItems": "center", "gap": "8px",
                    "background": "rgba(26,107,47,0.1)",
                    "border": f"1.5px solid rgba(26,107,47,0.4)",
                    "borderRadius": "100px", "padding": "7px 16px",
                    "backdropFilter": "blur(8px)"
                })
            ], style={"display": "flex", "alignItems": "center"}),

        ], style={
            "display": "flex", "justifyContent": "space-between",
            "alignItems": "center", "maxWidth": "1400px", "margin": "0 auto"
        })
    ], style={
        "background": "rgba(255,253,240,0.82)",
        "backdropFilter": "blur(22px) saturate(150%)",
        "borderBottom": f"1.5px solid {COLOR_BORDER}",
        "borderBottomColor": C_GOLD2,
        "padding": "15px 36px",
        "position": "sticky", "top": "0", "zIndex": "100",
        "boxShadow": f"0 2px 24px rgba(180,110,0,0.18), 0 1px 0 rgba(212,175,55,0.4)"
    }),

    # ══ MAIN ════════════════════════════════════════════════════════
    html.Div([

        # ── STAT CARDS ROW ──────────────────────────────────────────
        # Each card has a ghost slot. Update CARD_IMAGES dict with real URLs.
        html.Div(id="stat-cards", style={
            "display": "flex", "gap": "14px",
            "marginBottom": "18px", "flexWrap": "wrap"
        }),

        # ── PIE + RADAR ─────────────────────────────────────────────
        html.Div([
            glass_card([
                section_title("Sentiment Overview"),
                gold_divider(),
                dcc.Graph(id="sentiment-pie", config={"displayModeBar": False})
            ], {"flex": "1", "minWidth": "300px"}, "f2"),

            glass_card([
                section_title("What Customers Talk About"),
                gold_divider(),
                dcc.Graph(id="aspect-radar", config={"displayModeBar": False})
            ], {"flex": "1", "minWidth": "300px"}, "f2"),
        ], style={"display": "flex", "gap": "14px", "marginBottom": "18px", "flexWrap": "wrap"}),

        # ── REVIEWS + PRICES ────────────────────────────────────────
        html.Div([
            glass_card([
                section_title("📣 What Customers Are Saying"),
                gold_divider(),
                html.Div(id="top-reviews")
            ], {"flex": "1.3", "minWidth": "300px"}, "f3"),

            glass_card([
                section_title("💰 Competitor Prices"),
                gold_divider(),
                html.Div(id="price-table")
            ], {"flex": "1", "minWidth": "270px"}, "f3"),
        ], style={"display": "flex", "gap": "14px", "marginBottom": "18px", "flexWrap": "wrap"}),

        # ── LIVE ANALYZER ───────────────────────────────────────────
        glass_card([
            section_title("⚡ Live Review Analyzer"),
            gold_divider(),
            html.P(
                "Type any review in Darija, Arabic, French, or Arabizi — classified instantly.",
                style={"color": COLOR_MUTED, "fontSize": "13px",
                       "marginBottom": "16px", "fontWeight": "300"}
            ),
            dcc.Textarea(
                id="review-input",
                placeholder="...مثال: الطعم زين ولكن الثمن غالي شوية",
                className="review-ta",
                style={
                    "width": "100%", "height": "88px",
                    "backgroundColor": "rgba(255,245,210,0.55)",
                    "color": COLOR_TEXT,
                    "border": f"1.5px solid {COLOR_BORDER}",
                    "borderRadius": "14px",
                    "padding": "13px 16px",
                    "fontSize": "15px", "resize": "none",
                    "fontFamily": "'DM Sans', sans-serif",
                    "outline": "none", "display": "block",
                }
            ),
            html.Button("Analyze →", id="classify-btn", className="analyze-btn", style={
                "marginTop": "13px",
                "background": f"linear-gradient(135deg, {C_RED} 0%, {C_RED2} 60%, #900020 100%)",
                "color": "#FFFFFF", "border": "none", "borderRadius": "14px",
                "padding": "13px 40px", "fontSize": "15px", "fontWeight": "600",
                "fontFamily": "'DM Sans', sans-serif", "cursor": "pointer",
                "boxShadow": f"0 6px 26px rgba(200,16,46,0.42), 0 1px 0 rgba(255,255,255,0.2) inset",
                "display": "block", "letterSpacing": "0.4px",
            }),
            html.Div(id="classify-output", style={"marginTop": "18px"})
        ], {"marginBottom": "36px"}, "f4"),

    ], style={
        "padding": "26px 36px", "maxWidth": "1400px",
        "margin": "0 auto", "position": "relative", "zIndex": "1"
    }),

    dcc.Interval(id="interval", interval=30000, n_intervals=0)

], style={"fontFamily": "'DM Sans', sans-serif", "minHeight": "100vh"})


# ─────────────────────────────────────────────
# CALLBACKS
# ─────────────────────────────────────────────

@app.callback(Output("stat-cards", "children"), Input("interval", "n_intervals"))
def update_stat_cards(n):
    data = fetch("summary")
    if not data:
        return html.P("Could not load data", style={"color": COLOR_NEGATIVE})
    total    = data.get("total", 0)
    positive = data.get("positive", 0)
    negative = data.get("negative", 0)
    neutral  = data.get("neutral", 0)
    pos_pct  = f"{round(positive / total * 100)}%" if total > 0 else "—"
    neg_pct  = f"{round(negative / total * 100)}%" if total > 0 else "—"
    return [
        stat_card("total",    "Total Reviews", str(total),   COLOR_TEXT,     "across all platforms", C_GOLD2,   "f1"),
        stat_card("positive", "Positive",      pos_pct,      COLOR_POSITIVE, f"{positive} reviews",  C_GREEN,   "f1"),
        stat_card("negative", "Negative",      neg_pct,      COLOR_NEGATIVE, f"{negative} reviews",  C_RED,     "f1"),
        stat_card("neutral",  "Neutral",       str(neutral), COLOR_NEUTRAL,  "mixed opinions",       C_PEACH,   "f1"),
    ]


@app.callback(Output("sentiment-pie", "figure"), Input("interval", "n_intervals"))
def update_pie(n):
    data = fetch("summary")
    if not data:
        return {}
    labels = ["Positive", "Negative", "Neutral"]
    values = [data.get("positive", 0), data.get("negative", 0), data.get("neutral", 0)]
    colors = [COLOR_POSITIVE, C_RED, COLOR_NEUTRAL]
    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values, hole=0.58,
        marker=dict(colors=colors, line=dict(color="rgba(255,253,240,0.9)", width=3)),
        textfont=dict(color="white", size=12, family="DM Sans"),
        hovertemplate="<b>%{label}</b><br>%{value} reviews · %{percent}<extra></extra>",
        pull=[0.04, 0.04, 0.04]
    )])
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLOR_TEXT, family="DM Sans"),
        legend=dict(font=dict(color=COLOR_TEXT, size=12), bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=10, b=10, l=10, r=10), height=280
    )
    return fig


@app.callback(Output("aspect-radar", "figure"), Input("interval", "n_intervals"))
def update_radar(n):
    data = fetch("aspects")
    if not data:
        return {}
    aspects  = list(data.keys())
    pos_vals = [data[a].get("positive", 0) for a in aspects]
    neg_vals = [data[a].get("negative", 0) for a in aspects]
    a_cl = aspects + [aspects[0]]
    p_cl = pos_vals + [pos_vals[0]]
    n_cl = neg_vals + [neg_vals[0]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=p_cl, theta=a_cl, fill="toself", name="Positive",
        line=dict(color=COLOR_POSITIVE, width=2.5),
        fillcolor="rgba(26,107,47,0.2)"
    ))
    fig.add_trace(go.Scatterpolar(
        r=n_cl, theta=a_cl, fill="toself", name="Negative",
        line=dict(color=C_RED, width=2.5),
        fillcolor="rgba(200,16,46,0.14)"
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, color=C_GOLD2,
                            gridcolor="rgba(212,175,55,0.28)",
                            tickfont=dict(color=COLOR_MUTED, size=10)),
            angularaxis=dict(color=COLOR_TEXT,
                             tickfont=dict(color=COLOR_MUTED, size=11))
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLOR_TEXT, family="DM Sans"),
        legend=dict(font=dict(color=COLOR_TEXT, size=12), bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=20, b=20, l=40, r=40), height=280
    )
    return fig


@app.callback(Output("top-reviews", "children"), Input("interval", "n_intervals"))
def update_top_reviews(n):
    positive = fetch("top-reviews?sentiment=positive&limit=2")
    negative = fetch("top-reviews?sentiment=negative&limit=2")
    if not positive and not negative:
        return html.P("No reviews found", style={"color": COLOR_MUTED})

    platform_colors = {
        "facebook": "#1877f2", "tiktok": "#ff0050",
        "youtube":  "#ff0000", "jumia":  "#f68b1e"
    }

    def bubble(review, sentiment):
        is_pos   = sentiment == "positive"
        emoji    = "👍" if is_pos else "👎"
        ecls     = "emoji-pos" if is_pos else "emoji-neg"
        bcls     = "r-bubble pos" if is_pos else "r-bubble"
        platform = review.get("platform", "unknown")
        p_color  = platform_colors.get(platform, COLOR_MUTED)
        return html.Div([
            html.Div([
                html.Span(emoji, className=f"sentiment-emoji {ecls}"),
                html.Span(review.get("text", ""), style={
                    "color": COLOR_TEXT, "fontSize": "14px",
                    "direction": "rtl", "unicodeBidi": "plaintext",
                    "lineHeight": "1.6", "fontWeight": "400", "flex": "1",
                })
            ], style={"display": "flex", "alignItems": "flex-start", "gap": "12px"}),
            html.Div([
                html.Span(platform.upper(), style={
                    "display": "inline-block", "fontSize": "9px", "fontWeight": "700",
                    "letterSpacing": "1px", "padding": "3px 10px",
                    "borderRadius": "6px", "color": "white",
                    "marginRight": "8px", "backgroundColor": p_color
                }),
                html.Span(f"❤️ {review.get('engagement_score', 0)} engagements",
                          style={"color": COLOR_MUTED, "fontSize": "11px"})
            ], style={"marginTop": "10px", "marginLeft": "48px",
                      "display": "flex", "alignItems": "center"})
        ], className=bcls)

    items = []
    if positive:
        items.append(html.P("Most Loved 🍑", style={
            "color": C_GREEN, "fontSize": "10px", "fontWeight": "700",
            "margin": "0 0 10px 0", "letterSpacing": "2px", "textTransform": "uppercase"
        }))
        items += [bubble(r, "positive") for r in positive]
    if negative:
        items.append(html.P("Most Criticized 🍅", style={
            "color": C_RED, "fontSize": "10px", "fontWeight": "700",
            "margin": "16px 0 10px 0", "letterSpacing": "2px", "textTransform": "uppercase"
        }))
        items += [bubble(r, "negative") for r in negative]
    return items


@app.callback(Output("price-table", "children"), Input("interval", "n_intervals"))
def update_price_table(n):
    data = fetch("prices")
    if not data:
        return html.P("No price data", style={"color": COLOR_MUTED})

    def th(label, align="left"):
        return html.Th(label, style={
            "color": COLOR_MUTED, "fontWeight": "600",
            "padding": "8px 12px", "textAlign": align,
            "fontSize": "9px", "letterSpacing": "2px",
            "textTransform": "uppercase",
            "borderBottom": f"1px solid {COLOR_BORDER}"
        })

    rows = [html.Tr([th("Brand"), th("Product"), th("Price (DZD)", "right")])]
    for item in data:
        is_ramy = item["brand"] == "Ramy"
        bg = "rgba(212,175,55,0.10)" if is_ramy else "transparent"
        rows.append(html.Tr([
            html.Td(item["brand"], style={
                "padding": "11px 12px", "fontSize": "13px",
                "color": C_RED if is_ramy else COLOR_TEXT,
                "fontWeight": "700" if is_ramy else "400",
                "background": bg,
            }),
            html.Td(item["product"], style={
                "padding": "11px 12px", "fontSize": "13px",
                "color": COLOR_TEXT if is_ramy else COLOR_MUTED,
                "background": bg,
            }),
            html.Td(f"{item['price_dzd']} DZD", style={
                "padding": "11px 12px", "textAlign": "right",
                "fontWeight": "700", "fontSize": "13px",
                "color": C_GREEN if is_ramy else COLOR_MUTED,
                "background": bg,
            }),
        ], className="p-row",
           style={"borderBottom": "1px solid rgba(200,150,10,0.15)"}))
    return html.Table(rows, style={"width": "100%", "borderCollapse": "collapse"})


@app.callback(
    Output("classify-output", "children"),
    Input("classify-btn", "n_clicks"),
    State("review-input", "value"),
    prevent_initial_call=True
)
def classify_review(n_clicks, text):
    if not text or text.strip() == "":
        return html.P("Please enter a review first.",
                      style={"color": COLOR_NEUTRAL, "fontSize": "13px"})
    sentiment, confidence = rule_based_classify(text)
    color = {"positive": C_GREEN, "negative": C_RED, "neutral": COLOR_NEUTRAL}[sentiment]
    emoji = {"positive": "✅", "negative": "❌", "neutral": "⚠️"}[sentiment]
    bg    = {
        "positive": "rgba(26,107,47,0.10)",
        "negative": "rgba(200,16,46,0.08)",
        "neutral":  "rgba(184,120,22,0.09)"
    }[sentiment]
    # Convert hex color to rgb for border
    h = color.lstrip('#')
    r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    return html.Div([
        html.Div([
            html.Span(emoji + " ", style={"fontSize": "24px"}),
            html.Span(sentiment.upper(), style={
                "fontSize": "26px", "fontWeight": "900",
                "color": color, "fontFamily": "'Fraunces', serif"
            }),
            html.Span(f"  {confidence}% confidence", style={
                "fontSize": "12px", "color": COLOR_MUTED,
                "marginLeft": "12px", "fontWeight": "300"
            })
        ], style={"display": "flex", "alignItems": "center"}),
        html.P(get_insight(sentiment, text), style={
            "color": COLOR_MUTED, "fontSize": "13px",
            "marginTop": "10px", "fontStyle": "italic", "fontWeight": "300"
        })
    ], style={
        "background": bg, "borderRadius": "14px",
        "padding": "16px 20px",
        "border": f"1.5px solid rgba({r},{g},{b},0.35)",
        "borderLeft": f"4px solid {color}",
    })


# ─────────────────────────────────────────────
# CLASSIFIER
# ─────────────────────────────────────────────
POSITIVE_KEYWORDS = [
    "زين", "مليح", "ممتاز", "نعجبني", "3jebni",
    "bon ", "bien ", "super ", "top ",
    "بهية", "تستاهل", "يستاهل", "recommande ",
    "واو", "رائع", "نحب", "زينة", "waw ", "mzian"
]
NEGATIVE_KEYWORDS = [
    "خايب", "jbni3ma ", "غالي", "mauvais ", "nul ",
    "ما عجبنيش", "cher ", "déçu ",
    "خسارة", "ما نشريش", "واش", "بطل",
    "ما لقيتش", "خايبة", "مش مليح"
]

def rule_based_classify(text: str):
    t = text.lower()
    p = sum(1 for kw in POSITIVE_KEYWORDS if kw in t)
    q = sum(1 for kw in NEGATIVE_KEYWORDS if kw in t)
    if p > q: return "positive", min(70 + p * 5, 94)
    if q > p: return "negative", min(70 + q * 5, 94)
    return "neutral", 65

def get_insight(sentiment, text):
    if sentiment == "positive":
        return "💡 Customers responding positively — this review signals brand satisfaction."
    elif sentiment == "negative":
        return "💡 Negative signal detected — consider checking price or availability mentions."
    return "💡 Mixed signals — customer has both praise and criticism."


if __name__ == "__main__":
    app.run(debug=True, port=8050)