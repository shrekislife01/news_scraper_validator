# ---------------------------------------------------------------------------
# Stílusok
# ---------------------------------------------------------------------------

COLORS = {
    "bg": "#f8f9fa",
    "card": "#ffffff",
    "border": "#dee2e6",
    "primary": "#0d6efd",
    "success": "#198754",
    "partial": "#fd7e14",
    "failed": "#dc3545",
    "text": "#212529",
    "muted": "#6c757d",
}

CARD_STYLE = {
    "background": COLORS["card"],
    "border": f"1px solid {COLORS['border']}",
    "borderRadius": "8px",
    "padding": "20px",
    "marginBottom": "16px",
}

STATUS_BADGE_BASE = {
    "display": "inline-block",
    "padding": "4px 12px",
    "borderRadius": "20px",
    "fontWeight": "bold",
    "fontSize": "14px",
    "color": "#fff",
    "marginRight": "12px",
}

FIELD_ROW_STYLE = {
    "display": "flex",
    "alignItems": "flex-start",
    "padding": "10px 0",
    "borderBottom": f"1px solid {COLORS['border']}",
}

LABEL_STYLE = {
    "width": "100px",
    "flexShrink": "0",
    "fontWeight": "600",
    "color": COLORS["muted"],
    "fontSize": "13px",
    "paddingTop": "2px",
}

VALUE_STYLE = {
    "flex": "1",
    "color": COLORS["text"],
    "wordBreak": "break-word",
    "fontSize": "14px",
    "lineHeight": "1.6",
}

DOT_STYLE_BASE = {
    "width": "10px",
    "height": "10px",
    "borderRadius": "50%",
    "flexShrink": "0",
    "marginTop": "5px",
    "marginLeft": "12px",
}

# ---------------------------------------------------------------------------
# Validációs stílusok
# ---------------------------------------------------------------------------

VAL_SECTION_STYLE = {
    **CARD_STYLE,
    "borderLeft": f"4px solid {COLORS['primary']}",
}

VAL_FIELD_ROW_STYLE = {
    "padding": "12px 0",
    "borderBottom": f"1px solid {COLORS['border']}",
}

VAL_CONTROLS_ROW_STYLE = {
    "display": "flex",
    "flexWrap": "wrap",
    "gap": "8px",
    "marginTop": "6px",
    "alignItems": "flex-start",
}

VAL_INPUT_STYLE = {
    "padding": "6px 10px",
    "fontSize": "13px",
    "border": f"1px solid {COLORS['border']}",
    "borderRadius": "6px",
    "outline": "none",
    "background": "#fff",
    "color": COLORS["text"],
}

VAL_TEXTAREA_STYLE = {
    **VAL_INPUT_STYLE,
    "resize": "vertical",
    "minHeight": "56px",
    "lineHeight": "1.5",
}

VAL_SAVE_BTN_STYLE = {
    "padding": "10px 24px",
    "background": COLORS["primary"],
    "color": "#fff",
    "border": "none",
    "borderRadius": "6px",
    "cursor": "pointer",
    "fontWeight": "600",
    "fontSize": "14px",
}
