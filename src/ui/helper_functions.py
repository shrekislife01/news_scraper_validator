from dash import html, dcc, Input, Output, State, callback

from src.scraper.runner import run_test, TestRun, ExtractionStatus

from src.ui.styling import (
    COLORS,
    CARD_STYLE,
    STATUS_BADGE_BASE,
    FIELD_ROW_STYLE,
    LABEL_STYLE,
    VALUE_STYLE,
    DOT_STYLE_BASE,
    VAL_SECTION_STYLE,
    VAL_FIELD_ROW_STYLE,
    VAL_CONTROLS_ROW_STYLE,
    VAL_INPUT_STYLE,
    VAL_TEXTAREA_STYLE,
    VAL_SAVE_BTN_STYLE,
)
from src.ui.helper_constants import (
    ERROR_OPTIONS,
    FIELD_LABELS,
    RADIO_OPTIONS
)

# ---------------------------------------------------------------------------
# Layout segédfüggvények
# ---------------------------------------------------------------------------

def dot(filled: bool) -> html.Span:
    color = COLORS["success"] if filled else COLORS["failed"]
    return html.Span(style={**DOT_STYLE_BASE, "background": color})


def field_row(label: str, value, scrollable: bool = False) -> html.Div:
    is_present = bool(value)
    display = value if value else "—"

    if scrollable and value:
        value_element = html.Div(
            display,
            style={
                **VALUE_STYLE,
                "maxHeight": "260px",
                "overflowY": "auto",
                "whiteSpace": "pre-wrap",
                "background": COLORS["bg"],
                "padding": "8px",
                "borderRadius": "4px",
                "border": f"1px solid {COLORS['border']}",
            },
        )
    else:
        value_element = html.Span(str(display), style=VALUE_STYLE)

    return html.Div(
        style=FIELD_ROW_STYLE,
        children=[
            html.Span(label, style=LABEL_STYLE),
            value_element,
            dot(is_present),
        ],
    )


def status_badge(status: str) -> html.Span:
    color_map = {
        ExtractionStatus.SUCCESS: COLORS["success"],
        ExtractionStatus.PARTIAL: COLORS["partial"],
        ExtractionStatus.FAILED:  COLORS["failed"],
    }
    label_map = {
        ExtractionStatus.SUCCESS: "SUCCESS",
        ExtractionStatus.PARTIAL: "PARTIAL",
        ExtractionStatus.FAILED:  "FAILED",
    }
    color = color_map.get(status, COLORS["failed"])
    label = label_map.get(status, status.upper())
    return html.Span(label, style={**STATUS_BADGE_BASE, "background": color})


def score_badge(score: float | None) -> html.Span:
    if score is None:
        return html.Span("—", style={"color": COLORS["muted"], "fontSize": "20px", "fontWeight": "700"})
    if score >= 80:
        color = COLORS["success"]
    elif score >= 50:
        color = COLORS["partial"]
    else:
        color = COLORS["failed"]
    return html.Span(
        f"{score:.1f}%",
        style={**STATUS_BADGE_BASE, "background": color, "fontSize": "16px"},
    )


def val_field_row(field: str) -> html.Div:
    """Egy mező validációs sorát építi fel (radio + dropdown + javított érték + megjegyzés)."""
    label = FIELD_LABELS.get(field, field.capitalize())
    return html.Div(
        style=VAL_FIELD_ROW_STYLE,
        children=[
            html.Span(label, style={**LABEL_STYLE, "display": "block", "marginBottom": "4px"}),
            html.Div(
                style=VAL_CONTROLS_ROW_STYLE,
                children=[
                    dcc.RadioItems(
                        id=f"val-radio-{field}",
                        options=RADIO_OPTIONS,
                        value="none",
                        inline=True,
                        inputStyle={"marginRight": "4px"},
                        labelStyle={"marginRight": "16px", "fontSize": "13px", "cursor": "pointer"},
                    ),
                    dcc.Dropdown(
                        id=f"val-error-{field}",
                        options=ERROR_OPTIONS,
                        placeholder="Hibakategória...",
                        clearable=True,
                        style={**VAL_INPUT_STYLE, "minWidth": "200px", "padding": "0"},
                    ),
                    dcc.Input(
                        id=f"val-corrected-{field}",
                        type="text",
                        placeholder="Helyes érték...",
                        debounce=False,
                        style={**VAL_INPUT_STYLE, "flex": "1", "minWidth": "180px"},
                    ),
                    dcc.Textarea(
                        id=f"val-comment-{field}",
                        placeholder="Megjegyzés...",
                        style={**VAL_TEXTAREA_STYLE, "flex": "1", "minWidth": "180px"},
                    ),
                ],
            ),
        ],
    )