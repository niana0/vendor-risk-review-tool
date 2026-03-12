# Quick Start — Vendor Security Assessment Tool

## Run in 3 Steps

### 1. Open Terminal and Navigate

```bash
cd "/Users/ana.ni/Documents/Obsidian Vault/Claude Code projects/Vendor Review Tool v1.0"
```

### 2. Activate Environment

```bash
source venv/bin/activate
```

### 3. Run the App

```bash
streamlit run app.py
```

Browser opens automatically at **http://localhost:8501**

---

## First Time Setup

```bash
cd "/Users/ana.ni/Documents/Obsidian Vault/Claude Code projects/Vendor Review Tool v1.0"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Create a `.env` file in the project root:
```
OPENAI_API_KEY=your_openai_api_key_here
```

---

## Using the App

### Step 1 (optional but recommended)
Run `/vendor-risk-review <ticket-id>` in Claude Code. The initial review appears in the app automatically.

### Step 2 — Choose a review tab

| Tab | Use when you have... | Output |
|---|---|---|
| **Vendor Documentation Review** | SOC 2, pen test, policy PDFs | Final Risk Review + Security Doc Review (Word) |
| **Completed Questionnaire Review** | Vendor-answered Excel | Annotated Excel with findings flagged |
| **Auto-Fill Questionnaire** | Vendor docs + blank questionnaire | Answered questionnaire (Excel) |

### Step 3
Click the process button, review results, download reports.

Click **Start New Review** to reset for the next vendor.

---

## Stop the App

```bash
Ctrl + C
```

---

## Quick Troubleshooting

**Port already in use?**
```bash
lsof -ti:8501 | xargs kill -9
streamlit run app.py
```

**Module not found?**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**Browser didn't open?**
Go to: http://localhost:8501
