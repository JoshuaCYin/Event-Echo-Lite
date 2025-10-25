# Local Setup Instructions
## 1. Create and Activate a Virtual Environment

From a terminal (recommended within VS Code), navigate to the project root directory and create the virtual environment:
```
python -m venv .venv
```

Activate the environment:

**Mac/Linux:**
```
source .venv/bin/activate
```

**Windows:**
```
.venv\Scripts\activate
```

Note: On Windows, script execution may be disabled by default. If you encounter issues, enable script execution by running the following command in each terminal session you will use:
```
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
## 2. Install Dependencies

With the virtual environment activated, install the required dependencies by running:
```
pip install -r requirements.txt
```
## 3. Start the Server

To run the server, open a new terminal (ensuring the virtual environment is active) and execute the following command from the project root (Event-Echo or Event-Echo-Lite):
```
python -m backend.gateway.server
```

Next, in another terminal window, navigate to the frontend directory and run:
```
cd frontend
python -m http.server 8080
```
## 4. Access the Site

Once both the backend and frontend servers are running, open your browser and navigate to:

http://localhost:8080

