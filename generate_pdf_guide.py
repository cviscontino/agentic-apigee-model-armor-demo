"""
Generates a comprehensive 2-page PDF document containing:
1. Implementation Plan & Architecture Specification
2. Deployed Argolis Environment Details (`cvisco-agentic-demo`)
3. Step-by-Step CE Demo Script & Usage Instructions (Valid Calls, Model Armor Blocks, Stress Test, BigQuery Explorer)
4. Codebase Structure & CLI Reference
"""
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line


OUTPUT_PDF = Path(__file__).resolve().parent / "GCP_Agentic_Architecture_Demo_Guide.pdf"


def build_architecture_diagram() -> Drawing:
    """Draws a crisp vector architecture diagram of the 6-hop Agentic Pipeline."""
    d = Drawing(480, 96)

    nodes = [
        (0, 26, 68, 42, colors.HexColor("#eff6ff"), colors.HexColor("#2563eb"), "1. Client App", "React Console"),
        (82, 26, 72, 42, colors.HexColor("#fef3c7"), colors.HexColor("#d97706"), "2. Apigee X", "Quota / Cache"),
        (168, 26, 76, 42, colors.HexColor("#ffe4e6"), colors.HexColor("#e11d48"), "3. Model Armor", "PI / SDP / RAI"),
        (258, 26, 76, 42, colors.HexColor("#ecfdf5"), colors.HexColor("#059669"), "4. Gemini Ent.", "Root Multi-Agent"),
        (348, 52, 66, 34, colors.HexColor("#f3e8ff"), colors.HexColor("#7c3aed"), "5a. A2A #1", "Tx & Risk"),
        (348, 6, 66, 34, colors.HexColor("#f3e8ff"), colors.HexColor("#7c3aed"), "5b. A2A #2", "AML & KYC"),
        (426, 26, 54, 42, colors.HexColor("#e0f2fe"), colors.HexColor("#0284c7"), "6. BigQuery", "MCP Server"),
    ]

    for x, y, w, h, fill_c, stroke_c, title, subtitle in nodes:
        d.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=fill_c, strokeColor=stroke_c, strokeWidth=1.2))
        d.add(String(x + w / 2, y + h - 14, title, fontName="Helvetica-Bold", fontSize=7.5, fillColor=colors.HexColor("#09090b"), textAnchor="middle"))
        d.add(String(x + w / 2, y + 9, subtitle, fontName="Helvetica", fontSize=6.8, fillColor=colors.HexColor("#3f3f46"), textAnchor="middle"))

    arrows = [
        (68, 47, 82, 47),
        (154, 47, 168, 47),
        (244, 47, 258, 47),
        (334, 54, 348, 69),
        (334, 40, 348, 23),
        (414, 69, 426, 54),
        (414, 23, 426, 40),
    ]
    for x1, y1, x2, y2 in arrows:
        d.add(Line(x1, y1, x2, y2, strokeColor=colors.HexColor("#52525b"), strokeWidth=1.1))

    return d


def generate_pdf():
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="GCP Agentic Architecture Demo - Implementation Plan & Usage Guide",
        author="Google Cloud Customer Engineering",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=17.5,
        leading=21,
        textColor=colors.HexColor("#09090b"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#52525b"),
        spaceAfter=8,
    )
    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#1d4ed8"),
        spaceBefore=6,
        spaceAfter=3,
    )
    h2_style = ParagraphStyle(
        "SectionH2",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=9.8,
        leading=12.5,
        textColor=colors.HexColor("#09090b"),
        spaceBefore=5,
        spaceAfter=2,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.8,
        leading=11.8,
        textColor=colors.HexColor("#18181b"),
        spaceAfter=3,
    )
    bullet_style = ParagraphStyle(
        "BulletItem",
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-6,
        spaceAfter=2.5,
    )
    cell_header_style = ParagraphStyle(
        "CellHeader",
        parent=body_style,
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        spaceAfter=0,
    )
    cell_body_style = ParagraphStyle(
        "CellBody",
        parent=body_style,
        fontName="Helvetica",
        fontSize=7.8,
        leading=10.2,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=0,
    )
    cell_status_style = ParagraphStyle(
        "CellStatus",
        parent=body_style,
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#047857"),
        spaceAfter=0,
    )
    code_style = ParagraphStyle(
        "CodeBlock",
        fontName="Courier",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f4f4f5"),
        borderPadding=6,
        spaceBefore=4,
        spaceAfter=4,
    )

    story = []

    # HEADER
    story.append(Paragraph("GCP Enterprise Agentic Architecture Demo", title_style))
    story.append(
        Paragraph(
            "<b>Apigee X (AI Gateway) • Cloud Model Armor • Gemini Enterprise • Protocollo A2A • BigQuery MCP</b><br/>"
            "Piano di Implementazione, Risorse Deployate su Argolis (<b>cvisco-agentic-demo</b>) e Guida Operativa per la Demo CE",
            subtitle_style,
        )
    )

    # SECTION 1: IMPLEMENTATION PLAN & ARCHITECTURE
    story.append(Paragraph("1. Piano di Implementazione e Architettura End-to-End", h1_style))
    story.append(
        Paragraph(
            "La soluzione dimostra un'architettura Multi-Agente Enterprise nel verticale <b>Financial Services &amp; Anti-Money Laundering (AML)</b> "
            "progettata per rispondere ai requisiti di sicurezza, governance, osservabilità e protezione dei dati su Google Cloud.",
            body_style,
        )
    )

    story.append(Spacer(1, 2))
    story.append(build_architecture_diagram())
    story.append(Spacer(1, 4))

    story.append(Paragraph("1.1 Scelta dello Stack Tecnologico e Giustificazione", h2_style))
    story.append(
        Paragraph(
            "• <b>Frontend (React + Vite + Tailwind CSS + Apache ECharts)</b>: Interfaccia SaaS con tema Light/Dark, topologia live a 6 hop, "
            "ispettore profondo dei pacchetti JSON-RPC A2A/MCP, Stress Tester concorrente e Data Explorer con pannello di indagine laterale.",
            bullet_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>Backend &amp; Orchestration Gateway (Python FastAPI)</b>: Espone il proxy di mediazione Apigee + Cloud Model Armor (collegato live "
            "alle API REST di Model Armor su GCP), l'Orchestratore Gemini Enterprise, i 2 server A2A conformi allo standard (<i>/.well-known/agent.json</i>) "
            "e l'integrazione nativa con BigQuery MCP.",
            bullet_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>Agenti ADK &amp; Protocolli Standard (A2A + MCP)</b>: Il Root Agent su Gemini Enterprise delega in fan-out parallelo via protocollo "
            "<b>Agent-to-Agent (A2A)</b> a due sub-agenti specialistici: <i>transaction_risk_analytics_agent</i> e <i>compliance_customer_portfolio_agent</i>, "
            "che interrogano BigQuery esclusivamente tramite il tool MCP <i>execute_sql_readonly</i>.",
            bullet_style,
        )
    )

    # SECTION 2: DEPLOYED ARGOLIS ENVIRONMENT
    story.append(Paragraph("2. Risorse Live Deployate su Argolis (cvisco-agentic-demo)", h1_style))
    story.append(
        Paragraph(
            "L'intera infrastruttura demo è stata provisionata e verificata con l'utenza <b>admin@cviscontino.altostrat.com</b> "
            "sul progetto Argolis <b>cvisco-agentic-demo</b> (Project Number: <b>1070899805958</b>, Region: <b>europe-west1</b>).",
            body_style,
        )
    )

    raw_rows = [
        ("Cloud Run Demo App", "https://agentic-fsi-demo-1070899805958.europe-west1.run.app", "ATTIVO (200 OK)"),
        ("Server Locale Demo", "http://localhost:8000", "ATTIVO (200 OK)"),
        ("Console BigQuery", "https://console.cloud.google.com/bigquery?project=cvisco-agentic-demo", "ATTIVO"),
        ("BigQuery Dataset", "cvisco-agentic-demo.agentic_fsi_fraud_demo (Location: US)", "POPOLATO"),
        ("Tabella BQ #1 (A2A #1)", "transactions_ledger (12 transazioni SWIFT/SEPA/API con Risk Score)", "POPOLATA"),
        ("Tabella BQ #2 (A2A #2)", "customer_portfolios (8 clienti corporate/private banking, PEP, OFAC)", "POPOLATA"),
        ("Tabella BQ #3 (A2A #2)", "aml_compliance_alerts (6 alert normativi EU_AMLD6, FATF, PSD3)", "POPOLATA"),
        ("Cloud Model Armor", "projects/cvisco-agentic-demo/locations/europe-west1/templates/fsi-agent-armor-strict", "ATTIVO (Live API)"),
        ("A2A AgentCard #1", "/a2a/transaction-risk/.well-known/agent.json", "ESPOSTA"),
        ("A2A AgentCard #2", "/a2a/compliance-portfolio/.well-known/agent.json", "ESPOSTA"),
    ]

    env_table_data = [
        [
            Paragraph("Componente GCP", cell_header_style),
            Paragraph("Identificativo Risorsa / URL Live", cell_header_style),
            Paragraph("Stato", cell_header_style),
        ]
    ]
    for c1, c2, c3 in raw_rows:
        env_table_data.append(
            [
                Paragraph(f"<b>{c1}</b>", cell_body_style),
                Paragraph(c2, cell_body_style),
                Paragraph(c3, cell_status_style),
            ]
        )

    t = Table(env_table_data, colWidths=[42 * mm, 104 * mm, 32 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(t)

    story.append(PageBreak())

    # SECTION 3: STEP-BY-STEP CE DEMO USAGE GUIDE
    story.append(Paragraph("3. Istruzioni di Utilizzo e Storyboard per la Demo Cliente", h1_style))
    story.append(
        Paragraph(
            "Apri nel browser l'URL Cloud Run (<b>https://agentic-fsi-demo-1070899805958.europe-west1.run.app</b>) "
            "oppure l'istanza locale (<b>http://localhost:8000</b>). Segui questi 5 passaggi per condurre la demo:",
            body_style,
        )
    )

    story.append(Paragraph("Passo 1 — Mostrare la Discovery A2A e le Policy Apigee + Model Armor", h2_style))
    story.append(
        Paragraph(
            "• In alto a destra nella barra di navigazione, clicca su <b>A2A AgentCards</b> per mostrare il manifesto JSON ufficiale "
            "(<i>/.well-known/agent.json</i>) dei due sub-agenti (<b>transaction_risk_analytics_agent</b> e <b>compliance_customer_portfolio_agent</b>) "
            "con i relativi <i>mcpBindings</i> verso BigQuery MCP.",
            bullet_style,
        )
    )
    story.append(
        Paragraph(
            "• Clicca su <b>Policy Apigee &amp; Armor</b> per mostrare l'endpoint del proxy Apigee, l'ID del template Cloud Model Armor "
            "(<i>fsi-agent-armor-strict</i>), la soglia di SpikeArrest (15 req/min), il Semantic Caching e il mascheramento automatico SDP degli IBAN.",
            bullet_style,
        )
    )

    story.append(Paragraph("Passo 2 — Eseguire una Chiamata Corretta (Multi-Agente GE + 2x A2A + BigQuery MCP)", h2_style))
    story.append(
        Paragraph(
            "• Nella <b>Console Esecuzione Chiamate Demo</b> (colonna sinistra), seleziona il tab <b>1. Chiamate Corrette</b>, scegli uno dei 3 scenari "
            "(es. <i>Indagine Cross-Border Structuring &amp; Alert AML</i>) e clicca sul pulsante verde <b>Invia Chiamata al Multi-Agente GE (A2A + BQ MCP)</b>.",
            bullet_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>Cosa mostrare al cliente</b>:<br/>"
            "  1. Nella <b>Topologia Live a 6 Hop</b> tutti i 6 nodi diventano verdi (<i>HTTP 200</i>).<br/>"
            "  2. Nel pannello di destra (<b>Ispettore Telemetria &amp; Payload</b>), esplora i 4 tab:<br/>"
            "     - <b>Tab 1 (Risposta GE &amp; Sintesi)</b>: report esecutivo sintetizzato da Gemini Enterprise con IBAN mascherati (<i>IT60••••••••••3456</i>).<br/>"
            "     - <b>Tab 2 (Verdetto Model Armor)</b>: mostra <i>filterMatchState: NO_MATCH_FOUND</i> e <i>live_gcp_api_called: true</i>.<br/>"
            "     - <b>Tab 3 (Protocollo A2A)</b>: mostra le 2 chiamate parallele JSON-RPC 2.0 (<i>tasks/send</i>) inviate ai due sub-agenti.<br/>"
            "     - <b>Tab 4 (Query BigQuery MCP)</b>: mostra le query GoogleSQL reali eseguite tramite <i>execute_sql_readonly</i> con il Job ID BigQuery.",
            bullet_style,
        )
    )

    story.append(Paragraph("Passo 3 — Eseguire le Chiamate Bloccate da Cloud Model Armor (HTTP 422)", h2_style))
    story.append(
        Paragraph(
            "• Nella Console di sinistra, seleziona il tab <b>2. Stop Model Armor</b>, scegli uno dei 4 scenari di attacco e clicca sul pulsante rosso "
            "<b>Invia Attacco (Verifica Blocco Model Armor)</b>:<br/>"
            "  - <b>Prompt Injection &amp; System Override</b>: tentativo di attivare <i>DAN mode</i> e forzare lo stato <i>SETTLED</i> sul bonifico bloccato <i>TX-90802</i>.<br/>"
            "  - <b>Esfiltrazione Massiva PII / IBAN + Codice Fiscale</b>: intercettato dal filtro <i>Sensitive Data Protection (SDP)</i>.<br/>"
            "  - <b>Malicious URI &amp; SQL Injection</b>: tentativo di eseguire <i>DROP TABLE aml_compliance_alerts</i> verso un URL esterno malevolo.<br/>"
            "  - <b>Facilitazione Riciclaggio (RAI)</b>: richiesta su come strutturare bonifici sotto soglia per eludere la normativa EU AMLD6.",
            bullet_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>Cosa mostrare al cliente</b>: Nella barra topologica il nodo <b>2. Model Armor</b> si illumina in <b>Rosso (422 MATCH_FOUND)</b>, "
            "mentre i nodi a valle (<i>Gemini Enterprise</i>, <i>A2A Agent #1/#2</i>, <i>BigQuery MCP</i>) restano grigi con stato <b>Protetto (Non invocato)</b>. "
            "Il tab <b>2. Verdetto Model Armor</b> mostra la risposta reale dell'API Cloud Model Armor.",
            bullet_style,
        )
    )

    story.append(Paragraph("Passo 4 — Eseguire lo Stress Test Concorrente su Apigee X (HTTP 429 &amp; Cache)", h2_style))
    story.append(
        Paragraph(
            "• Passa al tab <b>3. Stress Test (429)</b>, imposta <b>24 richieste</b> e soglia <b>SpikeArrest 15 req/min</b>, quindi clicca su <b>Lancia Stress Test</b>.<br/>"
            "• <b>Cosa mostrare al cliente</b>: I 4 contatori sintetici e il grafico Apache ECharts mostrano la ripartizione tra <b>200 A2A+MCP</b>, "
            "<b>200 Cache Hit</b> (~26ms), <b>422 Armor Block</b> e <b>429 Throttled</b> (~5ms), evidenziando i Token LLM risparmiati e le Query BigQuery evitate.",
            bullet_style,
        )
    )

    story.append(Paragraph("Passo 5 — Esploratore Dati BigQuery &amp; Pannello Laterale di Indagine Analista", h2_style))
    story.append(
        Paragraph(
            "• Nella tabella <b>Esploratore Dati Live BigQuery MCP</b>, filtra per <i>Stato</i> / <i>Canale</i> / <i>Tipologia Frode</i> e clicca su una riga "
            "(es. <b>TX-90801</b>): si apre a destra il <b>Dossier Indagine Transazione &amp; AML</b> da cui puoi interrogare i 2 agenti A2A sul cliente o cliccare "
            "su <b>Approva (SETTLED)</b> / <b>Blocca &amp; SAR (BLOCKED)</b>.",
            bullet_style,
        )
    )

    # SECTION 4: CLI COMMANDS & REPOSITORY FILES
    story.append(Paragraph("4. Struttura della Codebase e Comandi Utili", h1_style))
    cli_block = (
        "cd /Users/cviscontino/jetski_projects/agentic-apigee-model-armor-demo\n"
        "./start_demo.sh                         # 1. Avvia server locale (http://localhost:8000)\n"
        "./.venv/bin/python deploy_argolis.py    # 2. Provisiona BigQuery + Template Model Armor\n"
        "./deploy_to_argolis.sh                  # 3. Rideploya su Cloud Run (cvisco-agentic-demo)\n"
        "|-- backend/main.py                              # FastAPI Gateway + Model Armor Live + A2A + BQ MCP\n"
        "|-- frontend/dist/index.html                     # React 18 + Tailwind + ECharts UI\n"
        "|-- agents/orchestrator_ge/agent.py              # Root Multi-Agent ADK per Gemini Enterprise\n"
        "|-- agents/a2a_transaction_risk/agent.py         # Sub-Agente A2A #1 (Transaction & Risk + BQ MCP)\n"
        "|-- agents/a2a_compliance_portfolio/agent.py     # Sub-Agente A2A #2 (Compliance & Portfolio + BQ MCP)\n"
        "|-- infra/apigee/apiproxy/                       # Bundle Apigee X (SpikeArrest, Quota, ServiceCallout)\n"
        "+-- infra/model_armor/template_fsi_strict.json   # Configurazione Template Cloud Model Armor"
    )
    story.append(Preformatted(cli_block, code_style))

    doc.build(story)
    print(f"PDF generated successfully at: {OUTPUT_PDF}")


if __name__ == "__main__":
    generate_pdf()
