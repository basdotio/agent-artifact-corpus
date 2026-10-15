# HeadHunter MCP Server

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-1.0+-green.svg)](https://modelcontextprotocol.io/)
[![HeadHunter API](https://img.shields.io/badge/HeadHunter-API%20v3-orange.svg)](https://dev.hh.ru/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English](#english) | [Русский](#russian)

---

## English

**MCP (Model Context Protocol) server for integrating HeadHunter API with Claude Code and other MCP clients.**

HeadHunter (hh.ru) is the largest job search platform in Russia and CIS countries. This MCP server provides seamless integration with HeadHunter API, enabling AI assistants to search vacancies, manage resumes, and apply to jobs on your behalf.

### Features

- 🔍 **Advanced Vacancy Search** - Filter by location, salary, experience, employment type
- 📄 **Resume Management** - View and manage your HeadHunter resumes
- ✉️ **Job Applications** - Apply to vacancies with custom cover letters
- 🏢 **Company Information** - Get detailed employer data
- 📊 **Application Tracking** - Monitor your job application history
- 🤖 **AI-Powered Agent** - Automated vacancy hunter with intelligent matching
- 🔐 **OAuth 2.0** - Secure authorization with HeadHunter

### Available Tools (10)

1. **hh_search_vacancies** - Search for job vacancies
2. **hh_get_vacancy** - Get detailed vacancy information
3. **hh_get_employer** - Get company/employer details
4. **hh_get_similar** - Find similar vacancies
5. **hh_get_areas** - Get list of regions/cities
6. **hh_get_dictionaries** - Get reference data (experience, employment types, etc.)
7. **hh_get_resumes** - Get your resumes list
8. **hh_get_resume** - Get detailed resume information
9. **hh_apply_to_vacancy** - Apply to a vacancy (requires OAuth)
10. **hh_get_negotiations** - Get application history (requires OAuth)

### Quick Start

#### 1. Installation

```bash
git clone https://github.com/yourusername/headhunter-mcp-server.git
cd headhunter-mcp-server
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 2. Get HeadHunter API Credentials

1. Register your application at [https://dev.hh.ru/admin](https://dev.hh.ru/admin)
2. Get Client ID, Client Secret, and App Token
3. Copy `.env.example` to `.env` and fill in your credentials

```bash
cp .env.example .env
# Edit .env with your credentials
```

#### 3. Configure Claude Code

Add to your `~/.claude.json`:

```json
{
  "mcpServers": {
    "headhunter": {
      "type": "stdio",
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/headhunter-mcp-server/server.py"],
      "env": {
        "HH_CLIENT_ID": "your_client_id",
        "HH_CLIENT_SECRET": "your_client_secret",
        "HH_APP_TOKEN": "your_app_token",
        "HH_REDIRECT_URI": "https://your-domain.com/oauth/callback"
      }
    }
  }
}
```

#### 4. OAuth Authorization (Optional)

For job applications and resume management:

```bash
python examples/oauth_flow.py
```

Follow the instructions to authorize and get access tokens.

### Usage Examples

```bash
# Search for Python jobs in Moscow
Find 10 Python developer vacancies in Moscow with salary from 200000

# View your resumes
Show my resumes

# Get vacancy details
Show details for vacancy 126209046

# Apply to a job (after OAuth)
Apply to vacancy 126209046 with resume [resume_id] and cover letter: "Hello..."
```

### Vacancy Hunter Agent

Automated agent for intelligent vacancy search and analysis. See [docs/vacancy-hunter-agent.md](docs/vacancy-hunter-agent.md) for details.

**Features:**
- Analyzes multiple resumes simultaneously
- Scores vacancies by relevance (0-30 points)
- Generates CSV reports with AI-powered recommendations
- Focuses on Moscow region only

**Usage:**
```bash
Run vacancy-hunter agent
```

### Project Structure

```
headhunter-mcp-server/
├── server.py              # MCP server (10 tools)
├── hh_client.py           # HeadHunter API client
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variables template
├── examples/
│   └── oauth_flow.py      # OAuth authorization script
└── docs/
    └── vacancy-hunter-agent.md  # Agent documentation
```

### Requirements

- Python 3.10+
- Claude Code or any MCP-compatible client
- HeadHunter API credentials

### Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### License

MIT License - see [LICENSE](LICENSE) file for details.

### Links

- [HeadHunter API Documentation](https://dev.hh.ru/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code)

---

## Russian

**MCP сервер для интеграции HeadHunter API с Claude Code и другими MCP клиентами.**

HeadHunter (hh.ru) — крупнейшая платформа по поиску работы в России и странах СНГ. Этот MCP сервер обеспечивает бесшовную интеграцию с API HeadHunter, позволяя AI ассистентам искать вакансии, управлять резюме и откликаться на вакансии от вашего имени.

### Возможности

- 🔍 **Расширенный поиск вакансий** - Фильтрация по местоположению, зарплате, опыту, типу занятости
- 📄 **Управление резюме** - Просмотр и управление вашими резюме на HeadHunter
- ✉️ **Отклики на вакансии** - Подача заявок с персонализированными сопроводительными письмами
- 🏢 **Информация о компаниях** - Получение детальных данных о работодателях
- 📊 **Отслеживание откликов** - Мониторинг истории ваших откликов
- 🤖 **AI-агент** - Автоматизированный поиск вакансий с умным сопоставлением
- 🔐 **OAuth 2.0** - Безопасная авторизация через HeadHunter

### Доступные инструменты (10)

1. **hh_search_vacancies** - Поиск вакансий
2. **hh_get_vacancy** - Детальная информация о вакансии
3. **hh_get_employer** - Информация о компании/работодателе
4. **hh_get_similar** - Поиск похожих вакансий
5. **hh_get_areas** - Список регионов/городов
6. **hh_get_dictionaries** - Справочные данные (опыт, типы занятости и т.д.)
7. **hh_get_resumes** - Список ваших резюме
8. **hh_get_resume** - Детальная информация о резюме
9. **hh_apply_to_vacancy** - Откликнуться на вакансию (требует OAuth)
10. **hh_get_negotiations** - История откликов (требует OAuth)

### Быстрый старт

#### 1. Установка

```bash
git clone https://github.com/yourusername/headhunter-mcp-server.git
cd headhunter-mcp-server
python -m venv venv
source venv/bin/activate  # В Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 2. Получение credentials HeadHunter API

1. Зарегистрируйте приложение на [https://dev.hh.ru/admin](https://dev.hh.ru/admin)
2. Получите Client ID, Client Secret и App Token
3. Скопируйте `.env.example` в `.env` и заполните свои credentials

```bash
cp .env.example .env
# Отредактируйте .env своими credentials
```

#### 3. Настройка Claude Code

Добавьте в `~/.claude.json`:

```json
{
  "mcpServers": {
    "headhunter": {
      "type": "stdio",
      "command": "/путь/к/venv/bin/python",
      "args": ["/путь/к/headhunter-mcp-server/server.py"],
      "env": {
        "HH_CLIENT_ID": "ваш_client_id",
        "HH_CLIENT_SECRET": "ваш_client_secret",
        "HH_APP_TOKEN": "ваш_app_token",
        "HH_REDIRECT_URI": "https://ваш-домен.com/oauth/callback"
      }
    }
  }
}
```

#### 4. OAuth авторизация (опционально)

Для откликов на вакансии и управления резюме:

```bash
python examples/oauth_flow.py
```

Следуйте инструкциям для авторизации и получения токенов доступа.

### Примеры использования

```bash
# Поиск Python вакансий в Москве
Найди 10 вакансий Python разработчика в Москве с зарплатой от 200000

# Просмотр резюме
Покажи мои резюме

# Детали вакансии
Покажи детали вакансии 126209046

# Отклик на вакансию (после OAuth)
Откликнись на вакансию 126209046 резюме [resume_id] с письмом: "Здравствуйте..."
```

### Vacancy Hunter Agent

Автоматизированный агент для умного поиска и анализа вакансий. Подробности в [docs/vacancy-hunter-agent.md](docs/vacancy-hunter-agent.md).

**Возможности:**
- Анализирует несколько резюме одновременно
- Оценивает релевантность вакансий (0-30 баллов)
- Генерирует CSV отчёты с AI рекомендациями
- Фокусируется только на регионе Москва

**Использование:**
```bash
Запусти агента vacancy-hunter
```

### Структура проекта

```
headhunter-mcp-server/
├── server.py              # MCP сервер (10 инструментов)
├── hh_client.py           # HeadHunter API клиент
├── requirements.txt       # Python зависимости
├── .env.example           # Шаблон переменных окружения
├── examples/
│   └── oauth_flow.py      # Скрипт OAuth авторизации
└── docs/
    └── vacancy-hunter-agent.md  # Документация агента
```

### Требования

- Python 3.10+
- Claude Code или любой MCP-совместимый клиент
- HeadHunter API credentials

### Участие в разработке

Приветствуются любые вклады! Не стесняйтесь отправлять Pull Request.

### Лицензия

MIT License - подробности в файле [LICENSE](LICENSE).

### Ссылки

- [Документация HeadHunter API](https://dev.hh.ru/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Документация Claude Code](https://docs.claude.com/en/docs/claude-code)

---

**Made with ❤️ for the HeadHunter and MCP community**
