import dataclasses

import dash
from dash import html, dcc, Input, Output, State, callback, no_update

from src.scraper.runner import run_test, TestRun, ExtractionStatus
from src.validator import (
    FieldValidation,
    VALIDATED_FIELDS,
    compute_score,
    build_validation_result,
    save_validation,
)

from src.ui.styling import (
    COLORS,
    CARD_STYLE,
    FIELD_ROW_STYLE,
    LABEL_STYLE,
    VALUE_STYLE,
    VAL_SECTION_STYLE,
    VAL_TEXTAREA_STYLE,
    VAL_SAVE_BTN_STYLE,
)

from src.ui.helper_functions import (
    dot,
    field_row,
    score_badge,
    status_badge,
    val_field_row,
)

app = dash.Dash(__name__, title="HU News Scraper Validator")
server = app.server  # WSGI-kompatibilis

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

app.layout = html.Div(
    style={
        "background": COLORS["bg"],
        "minHeight": "100vh",
        "padding": "32px 16px",
        "fontFamily": "system-ui, sans-serif",
    },
    children=[
        html.H1(
            "HU News Scraper Validator",
            style={"color": COLORS["text"], "marginBottom": "8px", "fontSize": "24px"},
        ),
        html.P(
            "Illeszd be egy magyar hírportál cikkének URL-jét, és kattints a Kinyerés gombra.",
            style={"color": COLORS["muted"], "marginBottom": "24px"},
        ),
        html.Div(
            style=CARD_STYLE,
            children=[
                html.Div(
                    style={"display": "flex", "gap": "10px", "alignItems": "center"},
                    children=[
                        dcc.Input(
                            id="url-input",
                            type="url",
                            placeholder="https://hirportal.hu/...",
                            debounce=False,
                            style={
                                "flex": "1",
                                "padding": "10px 14px",
                                "fontSize": "14px",
                                "border": f"1px solid {COLORS['border']}",
                                "borderRadius": "6px",
                                "outline": "none",
                            },
                        ),
                        html.Button(
                            "Kinyerés",
                            id="extract-btn",
                            n_clicks=0,
                            style={
                                "padding": "10px 22px",
                                "background": COLORS["primary"],
                                "color": "#fff",
                                "border": "none",
                                "borderRadius": "6px",
                                "cursor": "pointer",
                                "fontWeight": "600",
                                "fontSize": "14px",
                                "whiteSpace": "nowrap",
                            },
                        ),
                    ],
                ),
                dcc.Loading(
                    id="loading",
                    type="circle",
                    color=COLORS["primary"],
                    children=html.Div(id="loading-anchor", style={"height": "4px"}),
                ),
            ],
        ),
        html.Div(id="results-section"),
        html.Div(
            id="validation-section",
            style={"display": "none"},
            children=[
                html.Div(
                    style=VAL_SECTION_STYLE,
                    children=[
                        html.Div(
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "gap": "16px",
                                "marginBottom": "16px",
                            },
                            children=[
                                html.H2(
                                    "Validáció",
                                    style={
                                        "margin": "0",
                                        "fontSize": "18px",
                                        "color": COLORS["text"],
                                    },
                                ),
                                html.Div(id="val-score-display", children=score_badge(None)),
                            ],
                        ),
                        *[val_field_row(f) for f in VALIDATED_FIELDS],
                        html.Div(
                            style={"marginTop": "16px"},
                            children=[
                                html.Label(
                                    "Összesített megjegyzés",
                                    style={
                                        **LABEL_STYLE,
                                        "display": "block",
                                        "marginBottom": "6px",
                                    },
                                ),
                                dcc.Textarea(
                                    id="val-overall-comment",
                                    placeholder="Általános észrevételek a kinyerési eredményről...",
                                    style={
                                        **VAL_TEXTAREA_STYLE,
                                        "width": "100%",
                                        "minHeight": "80px",
                                        "boxSizing": "border-box",
                                    },
                                ),
                            ],
                        ),
                        html.Div(
                            style={
                                "marginTop": "16px",
                                "display": "flex",
                                "alignItems": "center",
                                "gap": "16px",
                            },
                            children=[
                                html.Button(
                                    "Mentés",
                                    id="val-save-btn",
                                    n_clicks=0,
                                    style=VAL_SAVE_BTN_STYLE,
                                ),
                                html.Div(id="val-save-status"),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        dcc.Store(id="run-result-store", storage_type="memory"),
    ],
)

# ---------------------------------------------------------------------------
# Callbacks – kinyerés
# ---------------------------------------------------------------------------


@callback(
    Output("run-result-store", "data"),
    Output("loading-anchor", "children"),
    Input("extract-btn", "n_clicks"),
    State("url-input", "value"),
    prevent_initial_call=True,
)
def trigger_extraction(n_clicks, url):
    """Lekéri az oldalt és futtatja a kinyerőt. Az eredményt dict-ként tárolja."""
    if not n_clicks:
        return no_update, no_update

    run = run_test((url or "").strip())
    return dataclasses.asdict(run), ""


@callback(
    Output("results-section", "children"),
    Input("run-result-store", "data"),
    prevent_initial_call=True,
)
def render_results(data):
    """A tárolt TestRun dict-ből felépíti az eredménynézetet."""
    if not data:
        return []

    run = TestRun(**data)

    duration_str = f"{run.duration_ms:,.0f} ms" if run.duration_ms is not None else "—"
    ran_at_str = run.ran_at[:19].replace("T", " ") + " UTC" if run.ran_at else "—"

    status_bar = html.Div(
        style={
            **CARD_STYLE,
            "display": "flex",
            "alignItems": "center",
            "flexWrap": "wrap",
            "gap": "8px",
        },
        children=[
            status_badge(run.status),
            html.Span(
                f"Futás: {duration_str}",
                style={"color": COLORS["muted"], "fontSize": "13px"},
            ),
            html.Span("·", style={"color": COLORS["border"]}),
            html.Span(ran_at_str, style={"color": COLORS["muted"], "fontSize": "13px"}),
        ],
    )

    if run.status == ExtractionStatus.FAILED and run.error_detail:
        error_card = html.Div(
            style={**CARD_STYLE, "borderLeft": f"4px solid {COLORS['failed']}"},
            children=[
                html.Strong(run.error_category or "Hiba", style={"color": COLORS["failed"]}),
                html.P(
                    run.error_detail,
                    style={"margin": "6px 0 0", "color": COLORS["text"], "fontSize": "14px"},
                ),
            ],
        )
        return [status_bar, error_card]

    keywords_str = ", ".join(run.keywords) if run.keywords else None

    results_card = html.Div(
        style=CARD_STYLE,
        children=[
            field_row("URL", run.url),
            field_row("Oldal", run.page),
            field_row("Cím", run.title),
            field_row("Szerző", run.author),
            field_row("Dátum", run.date),
            field_row("Szöveg", run.text, scrollable=True),
            html.Div(
                style={**FIELD_ROW_STYLE, "borderBottom": "none"},
                children=[
                    html.Span("Kulcsszavak", style=LABEL_STYLE),
                    html.Span(
                        keywords_str or "—",
                        style={
                            **VALUE_STYLE,
                            "fontStyle": "italic" if not keywords_str else "normal",
                        },
                    ),
                    dot(bool(keywords_str)),
                ],
            ),
        ],
    )

    return [status_bar, results_card]


# ---------------------------------------------------------------------------
# Callback – validáció megjelenítése és visszaállítása
# ---------------------------------------------------------------------------


@callback(
    Output("validation-section", "style"),
    Output("val-radio-title", "value"),
    Output("val-radio-text", "value"),
    Output("val-radio-author", "value"),
    Output("val-radio-date", "value"),
    Output("val-radio-keywords", "value"),
    Output("val-error-title", "value"),
    Output("val-error-text", "value"),
    Output("val-error-author", "value"),
    Output("val-error-date", "value"),
    Output("val-error-keywords", "value"),
    Output("val-corrected-title", "value"),
    Output("val-corrected-text", "value"),
    Output("val-corrected-author", "value"),
    Output("val-corrected-date", "value"),
    Output("val-corrected-keywords", "value"),
    Output("val-comment-title", "value"),
    Output("val-comment-text", "value"),
    Output("val-comment-author", "value"),
    Output("val-comment-date", "value"),
    Output("val-comment-keywords", "value"),
    Output("val-overall-comment", "value"),
    Output("val-score-display", "children"),
    Output("val-save-status", "children"),
    Input("run-result-store", "data"),
    prevent_initial_call=True,
)
def show_and_reset_validation(data):
    """Új kinyerés esetén megjeleníti a validációs panelt és visszaállítja az összes mezőt."""
    hidden = {"display": "none"}

    if not data:
        return (
            hidden,
            "none",
            "none",
            "none",
            "none",
            "none",
            None,
            None,
            None,
            None,
            None,
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            score_badge(None),
            "",
        )

    run = TestRun(**data)
    show = run.status in (ExtractionStatus.SUCCESS, ExtractionStatus.PARTIAL)
    section_style = {} if show else hidden

    return (
        section_style,
        "none",
        "none",
        "none",
        "none",
        "none",
        None,
        None,
        None,
        None,
        None,
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        score_badge(None),
        "",
    )


# ---------------------------------------------------------------------------
# Callback – pontszám élő frissítése
# ---------------------------------------------------------------------------


@callback(
    Output("val-score-display", "children", allow_duplicate=True),
    Input("val-radio-title", "value"),
    Input("val-radio-text", "value"),
    Input("val-radio-author", "value"),
    Input("val-radio-date", "value"),
    Input("val-radio-keywords", "value"),
    prevent_initial_call=True,
)
def update_score(r_title, r_text, r_author, r_date, r_keywords):
    """A radio gombok változásakor újraszámolja és megjeleníti a pontszámot."""
    radio_values = {
        "title": r_title,
        "text": r_text,
        "author": r_author,
        "date": r_date,
        "keywords": r_keywords,
    }

    def to_is_correct(v):
        if v == "correct":
            return True
        if v == "incorrect":
            return False
        return None

    field_validations = {
        f: FieldValidation(field_name=f, is_correct=to_is_correct(v))
        for f, v in radio_values.items()
    }

    score = compute_score(field_validations)
    return score_badge(score)


# ---------------------------------------------------------------------------
# Callback – validáció mentése
# ---------------------------------------------------------------------------


@callback(
    Output("val-save-status", "children", allow_duplicate=True),
    Input("val-save-btn", "n_clicks"),
    State("run-result-store", "data"),
    State("val-radio-title", "value"),
    State("val-radio-text", "value"),
    State("val-radio-author", "value"),
    State("val-radio-date", "value"),
    State("val-radio-keywords", "value"),
    State("val-error-title", "value"),
    State("val-error-text", "value"),
    State("val-error-author", "value"),
    State("val-error-date", "value"),
    State("val-error-keywords", "value"),
    State("val-corrected-title", "value"),
    State("val-corrected-text", "value"),
    State("val-corrected-author", "value"),
    State("val-corrected-date", "value"),
    State("val-corrected-keywords", "value"),
    State("val-comment-title", "value"),
    State("val-comment-text", "value"),
    State("val-comment-author", "value"),
    State("val-comment-date", "value"),
    State("val-comment-keywords", "value"),
    State("val-overall-comment", "value"),
    prevent_initial_call=True,
)
def save_validation_callback(
    n_clicks,
    run_data,
    r_title,
    r_text,
    r_author,
    r_date,
    r_keywords,
    e_title,
    e_text,
    e_author,
    e_date,
    e_keywords,
    c_title,
    c_text,
    c_author,
    c_date,
    c_keywords,
    cm_title,
    cm_text,
    cm_author,
    cm_date,
    cm_keywords,
    overall_comment,
):
    """Összegyűjti a validációs adatokat, kiszámolja a pontszámot, és JSON-ba menti."""
    if not n_clicks or run_data is None:
        return no_update

    radio_map = dict(zip(VALIDATED_FIELDS, [r_title, r_text, r_author, r_date, r_keywords]))
    error_map = dict(zip(VALIDATED_FIELDS, [e_title, e_text, e_author, e_date, e_keywords]))
    corrected_map = dict(
        zip(VALIDATED_FIELDS, [c_title, c_text, c_author, c_date, c_keywords])
    )
    comment_map = dict(
        zip(VALIDATED_FIELDS, [cm_title, cm_text, cm_author, cm_date, cm_keywords])
    )

    def to_is_correct(v):
        if v == "correct":
            return True
        if v == "incorrect":
            return False
        return None

    field_validations = {}
    field_data = {}

    for f in VALIDATED_FIELDS:
        is_correct = to_is_correct(radio_map[f])
        fv = FieldValidation(
            field_name=f,
            is_correct=is_correct,
            error_category=error_map[f] if is_correct is False else None,
            corrected_value=corrected_map[f] or None,
            comment=comment_map[f] or None,
        )
        field_validations[f] = fv
        field_data[f] = dataclasses.asdict(fv)

    score = compute_score(field_validations)

    try:
        result = build_validation_result(
            run_dict=run_data,
            field_data=field_data,
            global_score=score,
            overall_comment=overall_comment,
        )
        path = save_validation(result)
        return html.Span(
            f"Mentve: {path.name}",
            style={"color": COLORS["success"], "fontSize": "13px", "fontWeight": "600"},
        )
    except Exception as exc:
        return html.Span(
            f"Hiba a mentés során: {exc}",
            style={"color": COLORS["failed"], "fontSize": "13px"},
        )