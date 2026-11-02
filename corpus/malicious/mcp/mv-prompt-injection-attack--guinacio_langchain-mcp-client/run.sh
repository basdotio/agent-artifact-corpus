#!/bin/bash

# Function to handle process termination
cleanup() {
  echo "Stopping processes..."
  kill $MCP_PID $STREAMLIT_PID
  exit 0
}

# Set up trap for SIGINT (Ctrl+C)
trap cleanup SIGINT

# Activate the virtual environment
source venv/bin/activate

# Start the MCP server
echo "Starting MCP Weather Server..."
python weather_server.py &
MCP_PID=$!

# Wait a moment for the server to start
sleep 2

# Start the Streamlit app
echo "Starting Streamlit application..."
streamlit run app.py &
STREAMLIT_PID=$!

# Wait for both processes
echo "Services started!"
echo "- MCP Server: http://localhost:8000/sse"
echo "- Streamlit App: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop all services"

wait $MCP_PID $STREAMLIT_PID