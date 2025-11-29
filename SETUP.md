# Local Setup Instructions

## 1. Create and Activate a Virtual Environment

From a terminal (recommended within VS Code), navigate to the project root directory and create the virtual environment:

```bash
python -m venv .venv
```

Activate the environment:

**Mac/Linux:**
```bash
source .venv/bin/activate
```

**Windows:**
```powershell
.venv\Scripts\activate
```

*Note: On Windows, if script execution is disabled, run:*
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## 2. Install Dependencies

With the virtual environment activated, install the required dependencies:

```bash
pip install -r requirements.txt
```

## 3. Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env-example .env
   ```
   *(On Windows, use `copy .env-example .env`)*

2. Open `.env` and configure the following:
   - `DATABASE_URL`: Your PostgreSQL connection string.
   - `JWT_SECRET`: A secure random string.
   - `OPENAI_API_KEY` / `GEMINI_API_KEY`: Your AI provider keys.

## 4. Initialize the Database

Ensure your PostgreSQL server is running and you have created a database (e.g., `eventecho`).

Run the schema script to create tables:

```bash
psql -d eventecho -f backend/database/schema.sql
```
*Replace `eventecho` with your database name. You may need to provide your database username/password if not using default credentials.*

Alternatively, you can run the SQL commands in `backend/database/schema.sql` using a database tool like pgAdmin or DBeaver.

## 5. Start the Server

**Backend:**
Open a new terminal (with `.venv` activated) and run:
```bash
python -m backend.gateway.server
```

**Frontend:**
In another terminal window, navigate to the frontend directory and run:
```bash
cd frontend
python -m http.server 8080
```

## 6. Access the Site

Open your browser and navigate to:
http://localhost:8080
