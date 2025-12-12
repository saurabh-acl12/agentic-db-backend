---

# 🧠 AI Database Agent
---
## 🚀 Quick Start

### 1️⃣ Create Environment

```bash
python -m venv venv
venv\Scripts\activate   # On Windows
# or
source venv/bin/activate  # On macOS/Linux
```

### 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Configure `.env`

```bash
GOOGLE_API_KEY=your_gemini_api_key_here
DB_PATH=./data/db.sqlite

FEEDBACK_DB_TYPE=sqlite
FEEDBACK_DB_PATH=./feedback.sqlite

LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-flash-latest
GEMINI_EMBEDDING_MODEL=models/text-embedding-004
```

### 4️⃣ Run the Server (Running First Time / changed LLM_PROVIDER or EMBEDDING MODEL / The old vector store (ChromaDB) contains embeddings from the old model/provider which are incompatible with the new one.)
```bash
python -m src.vector.ingest
uvicorn src.main:app --reload
```

### 4️⃣ Run the Server

```bash
uvicorn src.main:app --reload
```

Then open 👉 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 💡 Example Request

```json
{
  "question": "Show the top 5 courses with the most students"
}
```

**Response**

```json
{
  "sql": "SELECT course_name, COUNT(user_pk) AS num_students ...",
  "result": [
    {"course_name": "Course 1", "num_students": 15},
    {"course_name": "Course 2", "num_students": 12}
  ]
}
```

---

## 🧱 Tech Stack

* **FastAPI** – REST API framework
* **LangChain + Gemini** – Natural language → SQL
* **SQLite** – Local database (`db.sqlite`)

---

## 📂 Structure

```
src/
├── agents/        # SQL generation logic
├── chains/        # LLM prompt templates
├── db/            # DB connection + schema introspection
├── utils/         # Helpers (env loader, etc.)
└── main.py        # FastAPI entrypoint
```

---

## 🧩 Example Questions

* “List all courses and their start dates”
* “Show top 5 courses by enrollments”
* “Find average score per course”
* “List users enrolled in more than one course”
