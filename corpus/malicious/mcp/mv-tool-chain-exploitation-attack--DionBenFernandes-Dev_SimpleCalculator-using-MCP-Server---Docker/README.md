# SimpleCalculator using Model Context Protocol (MCP) Server & Docker

A demonstration of custom Model Context Protocol (MCP) implementation for arithmetic operations, containerized with Docker for seamless deployment.

---

## Features

- **MCP Implementation**: Custom protocol handling for mathematical operations
- **Core Operations**: Addition, Subtraction, Multiplication, Division
- **Containerized Architecture**: Docker-based deployment
- **Dependency Management**: Modern Python packaging with `pyproject.toml` and `uv.lock`
- **Protocol Security**: Basic communication security through container isolation

---

## Project Structure

```
.
├── src/                # MCP server implementation
├── Dockerfile          # Container build instructions
├── compose.yaml        # Orchestration configuration
├── requirements.txt    # Python dependencies
├── pyproject.toml      # Project metadata
├── uv.lock             # Dependency lock file
├── .gitignore
├── LICENSE.md
└── README.md
```

---

## Getting Started

### Prerequisites
- Docker

### Installation
```bash
git clone https://github.com/DionBenFernandes-Dev/SimpleCalculator-using-MCP-Server---Docker.git
cd SimpleCalculator-using-MCP-Server---Docker
```

### Deployment
```bash
docker compose up --build
```

---

## Protocol Implementation

The MCP server handles calculations through a custom protocol implementation. Operations are processed using the following pattern:

1. **Connection**: Client establishes connection to MCP server
2. **Request Format**: 
```bash
Available tools:
  - add: Add 2 numbers
  - sub: Subtract 2 numbers
  - mul: Multiply 2 numbers
  - div: Divide 2 numbers

Enter the tool you want to use: add

Enter 1st Number: 3
Enter 2nd Number: 4
```
3. **Response Format**:
```bash
Result:: 3 + 4 = 7
```

---

## Configuration

Modify environment variables in `compose.yaml` to adjust:
- Server port binding
- Logging verbosity
- Protocol timeouts

---

## Development

1. **Local Setup**:
```bash
pip install uv # recommended

uv venv

uv add -r requirements.txt

uv run ./src/server.py
```

2. **Testing**:
```bash
uv run .\src\client.py
```

3. **Output**:
```bash
Available tools:
  - add: Add 2 numbers
  - sub: Subtract 2 numbers
  - mul: Multiply 2 numbers
  - div: Divide 2 numbers

Enter the tool you want to use: add

Enter 1st Number: 3
Enter 2nd Number: 4

Result:: 3 + 4 = 7
```
---

## License

MIT License - See [LICENSE.md](LICENSE.md)

---

## Contribution

1. Fork the repository
2. Create feature branch (`git checkout -b feature/NewOperation`)
3. Commit changes (`git commit -m 'Add modulo operation'`)
4. Push to branch (`git push origin feature/NewOperation`)
5. Open Pull Request

---

## Maintainer

Dion Ben Fernandes - [GitHub Profile](https://github.com/DionBenFernandes-Dev)

---

**Note**: This implementation demonstrates a custom MCP architecture pattern. For production use, consider implementing proper protocol security measures and validation layers.
