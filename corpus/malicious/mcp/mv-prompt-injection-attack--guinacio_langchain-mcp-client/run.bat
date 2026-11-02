@echo off
echo Starting MCP Weather Server and Streamlit App...

call "venv\Scripts\activate"

:: Start the MCP server in a new window
start "MCP Weather Server" cmd /c "python weather_server.py"

:: Wait a moment for the server to start
timeout /t 2 /nobreak > NUL

:: Start the Streamlit app in a new window
start "Streamlit App" cmd /c "streamlit run app.py"

echo Services started!
echo - MCP Server: http://localhost:8000/sse
echo - Streamlit App: http://localhost:8501
echo.
echo Close the command windows to stop the services

:: Keep this window open
pause