import dataclasses
import re

import dash
from dash import html, dcc, Input, Output, State, callback, no_update, ALL, ctx

from src.scraper.runner import run_test_with_rules, TestRun, ExtractionStatus
from src.validator import (
    FieldValidation,
    VALIDATED_FIELDS,
    compute_score,
    build_validation_result,
    save_validation,
)
import dataclasses as _dc

from src.rules import (
    RuleScope,
    RuleAction,
    make_rule,
    save_rule,
    load_rule,
    list_rules,
    RULES_DIR,
    analyze_validations,
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
    RULES_CARD_STYLE,
    RULE_ROW_STYLE,
    VAL_INPUT_STYLE,
)
from src.ui.helper_functions import (
    dot,
    field_row,
    score_badge,
    status_badge,
    val_field_row,
)

app = dash.Dash(__name__, title="HU News Scraper Validator", suppress_callback_exceptions=True)
server = app.server

_SCOPE_OPTIONS = [{"label": s.value.capitalize(), "value": s.value} for s in RuleScope]
_ACTION_OPTIONS = [
    {"label": "Regex csere (REGEX_REPLACE)",           "value": "REGEX_REPLACE"},
    {"label": "Előtag törlés (STRIP_PREFIX)",           "value": "STRIP_PREFIX"},
    {"label": "Utótag törlés (STRIP_SUFFIX)",           "value": "STRIP_SUFFIX"},
    {"label": "Nullázás ha illeszkedik (SET_NULL_IF)",  "value": "SET_NULL_IF"},
    {"label": "Szóköz normalizálás (NORMALIZE_WS)",     "value": "NORMALIZE_WS"},
    {"label": "Lista elem törlés (LIST_REMOVE)",        "value": "LIST_REMOVE"},
    {"label": "CSS selector override (CSS_SELECTOR_OVERRIDE)", "value": "CSS_SELECTOR_OVERRIDE"},
]
_ACTION_HINTS = {
    "REGEX_REPLACE":         "Szükséges: Minta (regex) + Helyettesítés. A mező értékén re.sub(minta, helyettesítés) fut.",
    "STRIP_PREFIX":          "Szükséges: Érték — az eltávolítandó rögzített előtag szöveg.",
    "STRIP_SUFFIX":          "Szükséges: Érték — az eltávolítandó rögzített utótag szöveg.",
    "SET_NULL_IF":           "Szükséges: Minta (regex). Ha illeszkedik, a mező None lesz.",
    "NORMALIZE_WS":          "Nincs extra mező. Többszörös szóközöket egyre csökkenti, majd trimmel.",
    "LIST_REMOVE":           "Szükséges: Minta (regex). Listamezőből eltávolítja az illeszkedő elemeket.",
    "CSS_SELECTOR_OVERRIDE": "Szükséges: Minta (CSS selector) + Domain. Kinyeréskor ez az elem szövegét veszi a mező értékeként — nem post-processing!",
}
_SCOPE_COLORS = {
    "title":    COLORS["primary"],
    "text":     COLORS["success"],
    "author":   COLORS["partial"],
    "date":     "#6f42c1",
    "keywords": "#20c997",
}
_SCOPE_LABELS = {
    "title": "Cím", "text": "Szöveg", "author": "Szerző",
    "date": "Dátum", "keywords": "Kulcsszavak",
}

_INPUT_STYLE = {**VAL_INPUT_STYLE, "width": "100%", "boxSizing": "border-box"}
_FORM_GRID = {
    "display": "grid",
    "gridTemplateColumns": "repeat(auto-fill, minmax(200px, 1fr))",
    "gap": "12px",
    "marginBottom": "12px",
}
_BTN_SMALL = {
    "padding": "4px 12px", "borderRadius": "5px", "border": "none",
    "cursor": "pointer", "fontSize": "12px", "fontWeight": "600",
}

def _badge(text: str, color: str) -> html.Span:
    return html.Span(text, style={
        "background": color, "color": "#fff", "borderRadius": "4px",
        "padding": "2px 8px", "fontSize": "11px", "fontWeight": "600",
        "marginRight": "4px", "whiteSpace": "nowrap",
    })


def _build_rules_table() -> list:
    paths = list_rules()
    if not paths:
        return [html.P(
            "Nincsenek mentett szabályok.",
            style={"color": COLORS["muted"], "fontSize": "14px", "margin": "0"},
        )]

    rows = []
    for path in paths:
        try:
            rule = load_rule(path)
        except Exception:
            continue

        scope_color = _SCOPE_COLORS.get(rule.scope, COLORS["muted"])
        scope_label = _SCOPE_LABELS.get(rule.scope, rule.scope)
        enabled = rule.enabled
        toggle_label = "✓ Aktív" if enabled else "✗ Letiltva"
        toggle_color = COLORS["success"] if enabled else COLORS["muted"]

        detail_parts = []
        if rule.pattern:
            detail_parts.append(f"minta: {rule.pattern}")
        if rule.replacement is not None:
            detail_parts.append(f"csere: \"{rule.replacement}\"")
        if rule.value:
            detail_parts.append(f"érték: \"{rule.value}\"")
        if rule.domain:
            detail_parts.append(f"domain: {rule.domain}")
        detail_str = " · ".join(detail_parts)

        rows.append(html.Div(
            style={
                **CARD_STYLE,
                "marginBottom": "8px",
                "display": "flex",
                "alignItems": "flex-start",
                "gap": "12px",
                "flexWrap": "wrap",
            },
            children=[
                # Info blokk
                html.Div(style={"flex": "1", "minWidth": "200px"}, children=[
                    html.Div(style={"display": "flex", "alignItems": "center", "gap": "8px", "marginBottom": "4px"}, children=[
                        html.Strong(rule.name, style={"fontSize": "14px", "color": COLORS["text"]}),
                        _badge(scope_label, scope_color),
                        _badge(rule.action, COLORS["muted"]),
                        html.Span(f"P:{rule.priority}", style={"fontSize": "11px", "color": COLORS["muted"]}),
                    ]),
                    html.Div(detail_str, style={"fontSize": "12px", "color": COLORS["muted"], "fontFamily": "monospace"}) if detail_str else None,
                    html.Div(rule.description, style={"fontSize": "12px", "color": COLORS["muted"], "marginTop": "2px"}) if rule.description else None,
                ]),
                # Gombok
                html.Div(style={"display": "flex", "gap": "6px", "alignItems": "center", "flexShrink": "0"}, children=[
                    html.Button(
                        toggle_label,
                        id={"type": "rule-toggle-btn", "index": rule.id},
                        n_clicks=0,
                        style={**_BTN_SMALL, "background": toggle_color, "color": "#fff"},
                    ),
                    html.Button(
                        "Törlés",
                        id={"type": "rule-delete-btn", "index": rule.id},
                        n_clicks=0,
                        style={**_BTN_SMALL, "background": COLORS["failed"], "color": "#fff"},
                    ),
                ]),
            ],
        ))
    return rows


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

_TAB_STYLE = {"padding": "8px 16px", "fontWeight": "600"}
_TAB_SELECTED = {**_TAB_STYLE, "borderTop": f"3px solid {COLORS['primary']}", "color": COLORS["primary"]}

app.layout = html.Div(
    style={
        "background": COLORS["bg"],
        "minHeight": "100vh",
        "padding": "32px 16px",
        "fontFamily": "system-ui, sans-serif",
        "maxWidth": "900px",
        "margin": "0 auto",
    },
    children=[
        html.H1(
            "HU News Scraper Validator",
            style={"color": COLORS["text"], "marginBottom": "4px", "fontSize": "24px"},
        ),
        html.P(
            "Magyar hírportál cikkek kinyerésének tesztelése és szabályalapú javítása.",
            style={"color": COLORS["muted"], "marginBottom": "20px"},
        ),

        dcc.Tabs(
            id="main-tabs",
            value="tab-extract",
            children=[
                dcc.Tab(
                    label="Kinyerés",
                    value="tab-extract",
                    style=_TAB_STYLE,
                    selected_style=_TAB_SELECTED,
                    children=[html.Div(style={"paddingTop": "16px"}, children=[
                        # Input kártya
                        html.Div(style=CARD_STYLE, children=[
                            html.Div(
                                style={"display": "flex", "gap": "10px", "alignItems": "center"},
                                children=[
                                    dcc.Input(
                                        id="url-input", type="url",
                                        placeholder="https://hirportal.hu/...",
                                        debounce=False,
                                        style={
                                            "flex": "1", "padding": "10px 14px",
                                            "fontSize": "14px",
                                            "border": f"1px solid {COLORS['border']}",
                                            "borderRadius": "6px", "outline": "none",
                                        },
                                    ),
                                    html.Button(
                                        "Kinyerés", id="extract-btn", n_clicks=0,
                                        style={
                                            "padding": "10px 22px",
                                            "background": COLORS["primary"], "color": "#fff",
                                            "border": "none", "borderRadius": "6px",
                                            "cursor": "pointer", "fontWeight": "600",
                                            "fontSize": "14px", "whiteSpace": "nowrap",
                                        },
                                    ),
                                ],
                            ),
                            dcc.Loading(
                                id="loading", type="circle", color=COLORS["primary"],
                                children=html.Div(id="loading-anchor", style={"height": "4px"}),
                            ),
                        ]),

                        html.Div(id="results-section"),
                        html.Div(id="rules-applied-section"),

                        html.Div(id="validation-section", style={"display": "none"}, children=[
                            html.Div(style=VAL_SECTION_STYLE, children=[
                                html.Div(
                                    style={"display": "flex", "alignItems": "center", "gap": "16px", "marginBottom": "16px"},
                                    children=[
                                        html.H2("Validáció", style={"margin": "0", "fontSize": "18px", "color": COLORS["text"]}),
                                        html.Div(id="val-score-display", children=score_badge(None)),
                                    ],
                                ),
                                *[val_field_row(f) for f in VALIDATED_FIELDS],
                                html.Div(style={"marginTop": "16px"}, children=[
                                    html.Label("Összesített megjegyzés", style={**LABEL_STYLE, "display": "block", "marginBottom": "6px"}),
                                    dcc.Textarea(
                                        id="val-overall-comment",
                                        placeholder="Általános észrevételek...",
                                        style={**VAL_TEXTAREA_STYLE, "width": "100%", "minHeight": "80px", "boxSizing": "border-box"},
                                    ),
                                ]),
                                html.Div(
                                    style={"marginTop": "16px", "display": "flex", "alignItems": "center", "gap": "16px"},
                                    children=[
                                        html.Button("Mentés", id="val-save-btn", n_clicks=0, style=VAL_SAVE_BTN_STYLE),
                                        html.Div(id="val-save-status"),
                                    ],
                                ),
                            ]),
                        ]),
                    ])],
                ),

                dcc.Tab(
                    label="Szabályok",
                    value="tab-rules",
                    style=_TAB_STYLE,
                    selected_style=_TAB_SELECTED,
                    children=[html.Div(style={"paddingTop": "16px"}, children=[

                        # ── Automatikus javaslatok ──
                        html.Div(style={**CARD_STYLE, "borderLeft": f"4px solid {COLORS['success']}"}, children=[
                            html.Div(
                                style={"display": "flex", "alignItems": "center", "gap": "16px", "marginBottom": "12px"},
                                children=[
                                    html.H3("Automatikus javaslatok", style={"margin": "0", "fontSize": "16px", "color": COLORS["text"]}),
                                    html.Button(
                                        "Generálás validációkból",
                                        id="suggestions-gen-btn", n_clicks=0,
                                        style={**_BTN_SMALL, "background": COLORS["success"], "color": "#fff", "fontSize": "13px", "padding": "6px 14px"},
                                    ),
                                    html.Span(id="suggestions-gen-status", style={"fontSize": "13px", "color": COLORS["muted"]}),
                                ],
                            ),
                            html.P(
                                "Elemzi a mentett validációkat és automatikusan javasol javítási szabályokat. "
                                "Minden javaslatot átnézhetsz elfogadás előtt.",
                                style={"color": COLORS["muted"], "fontSize": "13px", "margin": "0 0 12px"},
                            ),
                            html.Div(id="suggestions-section"),
                        ]),

                        html.Div(style={**CARD_STYLE, "borderLeft": f"4px solid {COLORS['primary']}"}, children=[
                            html.H3("Új szabály", style={"margin": "0 0 16px", "fontSize": "16px", "color": COLORS["text"]}),

                            html.Div(style=_FORM_GRID, children=[
                                html.Div([
                                    html.Label("Név *", style=LABEL_STYLE),
                                    dcc.Input(id="rule-form-name", type="text", placeholder="pl. Strip Telex suffix", style=_INPUT_STYLE),
                                ]),
                                html.Div([
                                    html.Label("Mező (scope) *", style=LABEL_STYLE),
                                    dcc.Dropdown(id="rule-form-scope", options=_SCOPE_OPTIONS, placeholder="Válassz...", style={"fontSize": "13px"}),
                                ]),
                                html.Div([
                                    html.Label("Akció *", style=LABEL_STYLE),
                                    dcc.Dropdown(id="rule-form-action", options=_ACTION_OPTIONS, placeholder="Válassz...", style={"fontSize": "13px"}),
                                ]),
                                html.Div([
                                    html.Label("Prioritás", style=LABEL_STYLE),
                                    dcc.Input(id="rule-form-priority", type="number", value=50, min=1, max=999, style=_INPUT_STYLE),
                                ]),
                            ]),

                            html.Div(id="rule-form-hint", style={
                                "fontSize": "12px", "color": COLORS["primary"],
                                "background": "#e8f0fe", "borderRadius": "5px",
                                "padding": "6px 10px", "marginBottom": "12px",
                                "display": "none",
                            }),

                            html.Div(style=_FORM_GRID, children=[
                                html.Div([
                                    html.Label("Minta (regex)", style=LABEL_STYLE),
                                    dcc.Input(id="rule-form-pattern", type="text", placeholder=r"pl. \s+$", style=_INPUT_STYLE),
                                ]),
                                html.Div([
                                    html.Label("Helyettesítés", style=LABEL_STYLE),
                                    dcc.Input(id="rule-form-replacement", type="text", placeholder='pl. ""', style=_INPUT_STYLE),
                                ]),
                                html.Div([
                                    html.Label("Érték (prefix/suffix)", style=LABEL_STYLE),
                                    dcc.Input(id="rule-form-value", type="text", placeholder='pl. " | Telex"', style=_INPUT_STYLE),
                                ]),
                                html.Div([
                                    html.Label("Domain (opcionális)", style=LABEL_STYLE),
                                    dcc.Input(id="rule-form-domain", type="text", placeholder="pl. telex.hu", style=_INPUT_STYLE),
                                ]),
                            ]),

                            html.Div(style={"marginBottom": "12px"}, children=[
                                html.Label("Leírás (opcionális)", style=LABEL_STYLE),
                                dcc.Textarea(
                                    id="rule-form-description",
                                    placeholder="Mire való ez a szabály?",
                                    style={**VAL_TEXTAREA_STYLE, "width": "100%", "minHeight": "60px", "boxSizing": "border-box"},
                                ),
                            ]),

                            html.Div(style={"display": "flex", "alignItems": "center", "gap": "16px"}, children=[
                                html.Button(
                                    "Hozzáadás", id="rule-form-btn", n_clicks=0,
                                    style={**VAL_SAVE_BTN_STYLE},
                                ),
                                html.Div(id="rule-form-status"),
                            ]),
                        ]),

                        html.Div(style={**CARD_STYLE, "marginTop": "0"}, children=[
                            html.Div(
                                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "12px"},
                                children=[
                                    html.H3("Mentett szabályok", style={"margin": "0", "fontSize": "16px", "color": COLORS["text"]}),
                                    html.Button(
                                        "Frissítés", id="rules-refresh-btn", n_clicks=0,
                                        style={**_BTN_SMALL, "background": COLORS["primary"], "color": "#fff"},
                                    ),
                                ],
                            ),
                            html.Div(id="rules-table", children=_build_rules_table()),
                        ]),
                    ])],
                ),
            ],
        ),

        dcc.Store(id="run-result-store",      storage_type="memory"),
        dcc.Store(id="pipeline-result-store", storage_type="memory"),
        dcc.Store(id="suggestions-store",     storage_type="memory", data=[]),
    ],
)


@callback(
    Output("run-result-store", "data"),
    Output("pipeline-result-store", "data"),
    Output("loading-anchor", "children"),
    Input("extract-btn", "n_clicks"),
    State("url-input", "value"),
    prevent_initial_call=True,
)
def trigger_extraction(n_clicks, url):
    if not n_clicks:
        return no_update, no_update, no_update
    pr = run_test_with_rules((url or "").strip())
    return pr.modified_run, dataclasses.asdict(pr), ""


@callback(
    Output("results-section", "children"),
    Input("run-result-store", "data"),
    prevent_initial_call=True,
)
def render_results(data):
    if not data:
        return []
    run = TestRun(**data)
    duration_str = f"{run.duration_ms:,.0f} ms" if run.duration_ms is not None else "—"
    ran_at_str   = run.ran_at[:19].replace("T", " ") + " UTC" if run.ran_at else "—"

    status_bar = html.Div(
        style={**CARD_STYLE, "display": "flex", "alignItems": "center", "flexWrap": "wrap", "gap": "8px"},
        children=[
            status_badge(run.status),
            html.Span(f"Futás: {duration_str}", style={"color": COLORS["muted"], "fontSize": "13px"}),
            html.Span("·", style={"color": COLORS["border"]}),
            html.Span(ran_at_str, style={"color": COLORS["muted"], "fontSize": "13px"}),
        ],
    )

    if run.status == ExtractionStatus.FAILED and run.error_detail:
        return [status_bar, html.Div(
            style={**CARD_STYLE, "borderLeft": f"4px solid {COLORS['failed']}"},
            children=[
                html.Strong(run.error_category or "Hiba", style={"color": COLORS["failed"]}),
                html.P(run.error_detail, style={"margin": "6px 0 0", "color": COLORS["text"], "fontSize": "14px"}),
            ],
        )]

    keywords_str = ", ".join(run.keywords) if run.keywords else None
    results_card = html.Div(style=CARD_STYLE, children=[
        field_row("URL",        run.url),
        field_row("Oldal",      run.page),
        field_row("Cím",        run.title),
        field_row("Szerző",     run.author),
        field_row("Dátum",      run.date),
        field_row("Szöveg",     run.text, scrollable=True),
        html.Div(
            style={**FIELD_ROW_STYLE, "borderBottom": "none"},
            children=[
                html.Span("Kulcsszavak", style=LABEL_STYLE),
                html.Span(keywords_str or "—", style={**VALUE_STYLE, "fontStyle": "italic" if not keywords_str else "normal"}),
                dot(bool(keywords_str)),
            ],
        ),
    ])
    return [status_bar, results_card]


@callback(
    Output("rules-applied-section", "children"),
    Input("pipeline-result-store", "data"),
    prevent_initial_call=True,
)
def render_rules_applied_card(data):
    if not data:
        return []
    rules_ran     = data.get("rules_ran", 0)
    rules_changed = data.get("rules_changed", 0)
    applied       = data.get("applied", [])

    if rules_ran == 0:
        return [html.Div(
            style={**CARD_STYLE, "color": COLORS["muted"], "fontSize": "13px"},
            children="Szabálymotor: nincsenek betöltött szabályok.",
        )]

    changed_rows = [a for a in applied if a.get("changed")]
    header = f"Szabálymotor — {rules_ran} szabály, {rules_changed} módosítást végzett"

    if not changed_rows:
        rows = []

    rows = []
    for entry in changed_rows:
        scope    = entry.get("scope", "")
        label    = _SCOPE_LABELS.get(scope, scope.capitalize())
        orig_str = str(entry.get("original_value") or "—")
        new_str  = str(entry.get("new_value")      or "—")
        rows.append(html.Div(style=RULE_ROW_STYLE, children=[
            html.Span(label,      style={"fontWeight": "600", "width": "80px",  "flexShrink": "0"}),
            html.Span(entry.get("rule_name", ""), style={"color": COLORS["primary"], "width": "160px", "flexShrink": "0"}),
            html.Span(orig_str[:100], style={"color": COLORS["failed"],  "flex": "1", "wordBreak": "break-all"}),
            html.Span("→",        style={"color": COLORS["muted"]}),
            html.Span(new_str[:100],  style={"color": COLORS["success"], "flex": "1", "wordBreak": "break-all"}),
        ]))

    # Extraction trace
    trace = data.get("extraction_trace") or {}
    trace_rows = []
    for field, info in trace.items():
        source = info.get("source", "?")
        selector = info.get("selector") or ""
        label = _SCOPE_LABELS.get(field, field.capitalize())
        trace_rows.append(html.Div(style={**RULE_ROW_STYLE, "fontSize": "12px", "color": COLORS["muted"]}, children=[
            html.Span(label,    style={"width": "80px", "flexShrink": "0", "fontWeight": "600"}),
            html.Span(source,   style={"color": COLORS["primary"], "width": "140px", "flexShrink": "0"}),
            html.Span(selector, style={"fontFamily": "monospace", "wordBreak": "break-all"}),
        ]))

    html_key = data.get("html_cache_key")
    cache_note = html.Div(
        f"HTML mentve: {html_key[:8]}…" if html_key else "HTML nem mentve",
        style={"fontSize": "11px", "color": COLORS["muted"], "marginTop": "8px"},
    )

    return [html.Div(style=RULES_CARD_STYLE, children=[
        html.Div(header, style={"fontWeight": "600", "marginBottom": "12px", "fontSize": "14px", "color": COLORS["text"]}),
        *rows,
        html.Hr(style={"margin": "12px 0", "borderColor": COLORS["border"]}) if trace_rows else None,
        html.Div("Kinyerési nyomkövetés:", style={"fontSize": "12px", "fontWeight": "600", "marginBottom": "6px", "color": COLORS["muted"]}) if trace_rows else None,
        *trace_rows,
        cache_note,
    ])]


@callback(
    Output("validation-section", "style"),
    Output("val-radio-title",    "value"), Output("val-radio-text",     "value"),
    Output("val-radio-author",   "value"), Output("val-radio-date",     "value"),
    Output("val-radio-keywords", "value"),
    Output("val-error-title",    "value"), Output("val-error-text",     "value"),
    Output("val-error-author",   "value"), Output("val-error-date",     "value"),
    Output("val-error-keywords", "value"),
    Output("val-corrected-title",    "value"), Output("val-corrected-text",     "value"),
    Output("val-corrected-author",   "value"), Output("val-corrected-date",     "value"),
    Output("val-corrected-keywords", "value"),
    Output("val-comment-title",    "value"), Output("val-comment-text",     "value"),
    Output("val-comment-author",   "value"), Output("val-comment-date",     "value"),
    Output("val-comment-keywords", "value"),
    Output("val-overall-comment", "value"),
    Output("val-score-display",   "children"),
    Output("val-save-status",     "children"),
    Input("run-result-store", "data"),
    prevent_initial_call=True,
)
def show_and_reset_validation(data):
    hidden = {"display": "none"}
    reset = (hidden, "none","none","none","none","none", None,None,None,None,None,
             "","","","","", "","","","","", "", score_badge(None), "")
    if not data:
        return reset
    run = TestRun(**data)
    show = run.status in (ExtractionStatus.SUCCESS, ExtractionStatus.PARTIAL)
    return (
        {} if show else hidden,
        "none","none","none","none","none",
        None,None,None,None,None,
        "","","","","",
        "","","","","",
        "", score_badge(None), "",
    )


@callback(
    Output("val-score-display", "children", allow_duplicate=True),
    Input("val-radio-title",    "value"), Input("val-radio-text",     "value"),
    Input("val-radio-author",   "value"), Input("val-radio-date",     "value"),
    Input("val-radio-keywords", "value"),
    prevent_initial_call=True,
)
def update_score(r_title, r_text, r_author, r_date, r_keywords):
    def ic(v): return True if v == "correct" else (False if v == "incorrect" else None)
    fvs = {f: FieldValidation(field_name=f, is_correct=ic(v))
           for f, v in zip(VALIDATED_FIELDS, [r_title, r_text, r_author, r_date, r_keywords])}
    return score_badge(compute_score(fvs))


@callback(
    Output("val-save-status", "children", allow_duplicate=True),
    Input("val-save-btn", "n_clicks"),
    State("run-result-store", "data"),
    State("pipeline-result-store", "data"),
    State("val-radio-title",    "value"), State("val-radio-text",     "value"),
    State("val-radio-author",   "value"), State("val-radio-date",     "value"),
    State("val-radio-keywords", "value"),
    State("val-error-title",    "value"), State("val-error-text",     "value"),
    State("val-error-author",   "value"), State("val-error-date",     "value"),
    State("val-error-keywords", "value"),
    State("val-corrected-title",    "value"), State("val-corrected-text",     "value"),
    State("val-corrected-author",   "value"), State("val-corrected-date",     "value"),
    State("val-corrected-keywords", "value"),
    State("val-comment-title",    "value"), State("val-comment-text",     "value"),
    State("val-comment-author",   "value"), State("val-comment-date",     "value"),
    State("val-comment-keywords", "value"),
    State("val-overall-comment", "value"),
    prevent_initial_call=True,
)
def save_validation_callback(n_clicks, run_data, pipeline_data,
    r_title, r_text, r_author, r_date, r_keywords,
    e_title, e_text, e_author, e_date, e_keywords,
    c_title, c_text, c_author, c_date, c_keywords,
    cm_title, cm_text, cm_author, cm_date, cm_keywords,
    overall_comment):
    if not n_clicks or run_data is None:
        return no_update
    def ic(v): return True if v == "correct" else (False if v == "incorrect" else None)
    radio_map    = dict(zip(VALIDATED_FIELDS, [r_title, r_text, r_author, r_date, r_keywords]))
    error_map    = dict(zip(VALIDATED_FIELDS, [e_title, e_text, e_author, e_date, e_keywords]))
    corrected_map= dict(zip(VALIDATED_FIELDS, [c_title, c_text, c_author, c_date, c_keywords]))
    comment_map  = dict(zip(VALIDATED_FIELDS, [cm_title, cm_text, cm_author, cm_date, cm_keywords]))
    fvs, field_data = {}, {}
    for f in VALIDATED_FIELDS:
        is_c = ic(radio_map[f])
        fv = FieldValidation(f, is_correct=is_c, error_category=error_map[f] if is_c is False else None,
                             corrected_value=corrected_map[f] or None, comment=comment_map[f] or None)
        fvs[f] = fv
        field_data[f] = dataclasses.asdict(fv)
    html_cache_key = (pipeline_data or {}).get("html_cache_key")
    extraction_trace = (pipeline_data or {}).get("extraction_trace")
    try:
        result = build_validation_result(
            run_dict=run_data, field_data=field_data,
            global_score=compute_score(fvs), overall_comment=overall_comment,
            html_cache_key=html_cache_key, extraction_trace=extraction_trace,
        )
        path = save_validation(result)
        return html.Span(f"Mentve: {path.name}", style={"color": COLORS["success"], "fontSize": "13px", "fontWeight": "600"})
    except Exception as exc:
        return html.Span(f"Hiba: {exc}", style={"color": COLORS["failed"], "fontSize": "13px"})


@callback(
    Output("rule-form-hint", "children"),
    Output("rule-form-hint", "style"),
    Input("rule-form-action", "value"),
    prevent_initial_call=True,
)
def show_action_hint(action):
    base_style = {
        "fontSize": "12px", "color": COLORS["primary"],
        "background": "#e8f0fe", "borderRadius": "5px",
        "padding": "6px 10px", "marginBottom": "12px",
    }
    if not action:
        return "", {**base_style, "display": "none"}
    return _ACTION_HINTS.get(action, ""), base_style


@callback(
    Output("rules-table", "children"),
    Output("rule-form-status", "children"),
    Output("rule-form-name", "value"),
    Output("rule-form-scope", "value"),
    Output("rule-form-action", "value"),
    Output("rule-form-pattern", "value"),
    Output("rule-form-replacement", "value"),
    Output("rule-form-value", "value"),
    Output("rule-form-domain", "value"),
    Output("rule-form-priority", "value"),
    Output("rule-form-description", "value"),
    Input("rule-form-btn", "n_clicks"),
    State("rule-form-name",        "value"),
    State("rule-form-scope",       "value"),
    State("rule-form-action",      "value"),
    State("rule-form-pattern",     "value"),
    State("rule-form-replacement", "value"),
    State("rule-form-value",       "value"),
    State("rule-form-domain",      "value"),
    State("rule-form-priority",    "value"),
    State("rule-form-description", "value"),
    prevent_initial_call=True,
)
def create_rule_callback(n_clicks, name, scope, action, pattern, replacement,
                         value, domain, priority, description):
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

    # Validáció
    if not name or not name.strip():
        return no_update, _err("A Név mező kötelező."), no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
    if not scope:
        return no_update, _err("A Mező (scope) kötelező."), no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
    if not action:
        return no_update, _err("Az Akció kötelező."), no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
    if pattern:
        try:
            re.compile(pattern)
        except re.error as e:
            return no_update, _err(f"Érvénytelen regex minta: {e}"), no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

    try:
        rule = make_rule(
            name=name.strip(),
            scope=scope,
            action=action,
            description=(description or "").strip() or None,
            pattern=pattern or None,
            replacement=replacement if replacement is not None else None,
            value=value or None,
            domain=(domain or "").strip() or None,
            priority=int(priority) if priority else 50,
        )
        save_rule(rule)
    except Exception as exc:
        return no_update, _err(f"Mentési hiba: {exc}"), no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

    status = html.Span(f"✓ Szabály létrehozva: {rule.name}", style={"color": COLORS["success"], "fontSize": "13px", "fontWeight": "600"})
    # Reset form, refresh table
    return _build_rules_table(), status, "", None, None, "", "", "", "", 50, ""


@callback(
    Output("rules-table", "children", allow_duplicate=True),
    Input("rules-refresh-btn", "n_clicks"),
    prevent_initial_call=True,
)
def refresh_rules_table(n_clicks):
    return _build_rules_table()


@callback(
    Output("rules-table", "children", allow_duplicate=True),
    Input({"type": "rule-delete-btn", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def delete_rule_callback(n_clicks_list):
    triggered = ctx.triggered_id
    if not triggered or not any(n_clicks_list):
        return no_update
    rule_id = triggered["index"]
    path = RULES_DIR / f"{rule_id}.json"
    if path.exists():
        path.unlink()
    return _build_rules_table()


@callback(
    Output("rules-table", "children", allow_duplicate=True),
    Input({"type": "rule-toggle-btn", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def toggle_rule_callback(n_clicks_list):
    triggered = ctx.triggered_id
    if not triggered or not any(n_clicks_list):
        return no_update
    rule_id = triggered["index"]
    path = RULES_DIR / f"{rule_id}.json"
    if path.exists():
        rule = load_rule(path)
        rule.enabled = not rule.enabled
        save_rule(rule)
    return _build_rules_table()


@callback(
    Output("suggestions-store", "data"),
    Output("suggestions-gen-status", "children"),
    Input("suggestions-gen-btn", "n_clicks"),
    prevent_initial_call=True,
)
def generate_suggestions(n_clicks):
    """Elemzi a validációs JSON-okat és feltölti a javaslatokat a store-ba."""
    suggestions = analyze_validations()
    serialized = [_dc.asdict(s) for s in suggestions]
    if not suggestions:
        return serialized, "Nem találtam generálható javaslatot a meglévő validációkból."
    return serialized, f"{len(suggestions)} javaslat generálva."


@callback(
    Output("suggestions-section", "children"),
    Input("suggestions-store", "data"),
)
def render_suggestions(suggestions):
    """Kirajzolja a javaslatkártyákat a store tartalma alapján."""
    if not suggestions:
        return html.P(
            "Kattints a \"Generálás validációkból\" gombra a javaslatok megtekintéséhez.",
            style={"color": COLORS["muted"], "fontSize": "13px", "margin": "0"},
        )
    return [_suggestion_card(s) for s in suggestions]


@callback(
    Output("suggestions-store", "data", allow_duplicate=True),
    Output("rules-table", "children", allow_duplicate=True),
    Input({"type": "suggestion-accept-btn", "index": ALL}, "n_clicks"),
    State("suggestions-store", "data"),
    prevent_initial_call=True,
)
def accept_suggestion(n_clicks_list, suggestions):
    """Elfogadja a javaslatot: létrehozza a szabályt, eltávolítja a listából."""
    if not any(n_clicks_list) or not ctx.triggered_id or not suggestions:
        return no_update, no_update
    sid = ctx.triggered_id["index"]
    target = next((s for s in suggestions if s["id"] == sid), None)
    if target is None:
        return no_update, no_update
    try:
        rule = make_rule(
            name=target["name"],
            scope=target["scope"],
            action=target["action"],
            description=target["description"],
            pattern=target.get("pattern"),
            replacement=target.get("replacement"),
            value=target.get("value"),
            domain=target.get("domain"),
            priority=50,
        )
        save_rule(rule)
    except Exception:
        return no_update, no_update
    updated = [s for s in suggestions if s["id"] != sid]
    return updated, _build_rules_table()


@callback(
    Output("suggestions-store", "data", allow_duplicate=True),
    Input({"type": "suggestion-dismiss-btn", "index": ALL}, "n_clicks"),
    State("suggestions-store", "data"),
    prevent_initial_call=True,
)
def dismiss_suggestion(n_clicks_list, suggestions):
    """Elveti a javaslatot (csak a listából törli, szabályt nem hoz létre)."""
    if not any(n_clicks_list) or not ctx.triggered_id or not suggestions:
        return no_update
    sid = ctx.triggered_id["index"]
    return [s for s in suggestions if s["id"] != sid]


def _err(msg: str) -> html.Span:
    return html.Span(msg, style={"color": COLORS["failed"], "fontSize": "13px"})


def _suggestion_card(s: dict) -> html.Div:
    """Egy javaslatkártyát épít fel elfogadás / elvetés gombokkal."""
    scope_color = _SCOPE_COLORS.get(s["scope"], COLORS["muted"])
    scope_label = _SCOPE_LABELS.get(s["scope"], s["scope"])
    conf = s.get("confidence", 1)
    conf_color = COLORS["success"] if conf >= 3 else (COLORS["partial"] if conf >= 2 else COLORS["muted"])

    summary_parts = []
    if s.get("value"):
        summary_parts.append(html.Span(["Érték: ", html.Code(s["value"], style={"background": "#f0f0f0", "padding": "1px 4px", "borderRadius": "3px"})]))
    if s.get("pattern"):
        summary_parts.append(html.Span(["Minta: ", html.Code(s["pattern"], style={"background": "#f0f0f0", "padding": "1px 4px", "borderRadius": "3px", "wordBreak": "break-all"})]))
    if s.get("replacement") is not None:
        r_display = f'"{s["replacement"]}"' if s["replacement"] else '""'
        summary_parts.append(html.Span(f"→ {r_display}"))
    if s.get("domain"):
        summary_parts.append(html.Span(s["domain"], style={"color": COLORS["muted"]}))

    example_rows = []
    for ex in s.get("examples", [])[:2]:
        orig = str(ex.get("original", ""))[:80]
        corr = str(ex.get("corrected", ""))[:80]
        example_rows.append(html.Div(
            style={"fontSize": "12px", "color": COLORS["muted"], "fontFamily": "monospace", "marginTop": "4px"},
            children=[
                html.Span(orig, style={"color": COLORS["failed"]}),
                html.Span(" → ", style={"color": COLORS["muted"]}),
                html.Span(corr, style={"color": COLORS["success"]}),
            ],
        ))

    return html.Div(
        style={
            **CARD_STYLE,
            "marginBottom": "8px",
            "borderLeft": f"4px solid {scope_color}",
            "display": "flex",
            "gap": "16px",
            "flexWrap": "wrap",
        },
        children=[
            html.Div(style={"flex": "1", "minWidth": "200px"}, children=[
                html.Div(
                    style={"display": "flex", "alignItems": "center", "gap": "6px", "marginBottom": "4px", "flexWrap": "wrap"},
                    children=[
                        _badge(scope_label, scope_color),
                        _badge(s["action"], COLORS["muted"]),
                        html.Span(
                            f"{conf}× megerősítve",
                            style={"fontSize": "11px", "color": conf_color, "fontWeight": "600"},
                        ),
                    ],
                ),
                html.Div(
                    style={"display": "flex", "gap": "12px", "flexWrap": "wrap", "fontSize": "13px", "marginBottom": "4px"},
                    children=[html.Span(part) for part in summary_parts],
                ),
                *example_rows,
            ]),
            html.Div(
                style={"display": "flex", "flexDirection": "column", "gap": "6px", "flexShrink": "0", "justifyContent": "center"},
                children=[
                    html.Button(
                        "✓ Elfogadás",
                        id={"type": "suggestion-accept-btn", "index": s["id"]},
                        n_clicks=0,
                        style={**_BTN_SMALL, "background": COLORS["success"], "color": "#fff"},
                    ),
                    html.Button(
                        "✗ Elvetés",
                        id={"type": "suggestion-dismiss-btn", "index": s["id"]},
                        n_clicks=0,
                        style={**_BTN_SMALL, "background": COLORS["muted"], "color": "#fff"},
                    ),
                ],
            ),
        ],
    )
