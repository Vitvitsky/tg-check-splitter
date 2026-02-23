# Agent Factory — Multi-Agent Orchestration

AI-агенты работают конвейером: от сырой идеи до ретроспективы. Каждая фаза опциональна — можно начать с любой.

Три способа управления:
- **Bash-скрипты** — `phase.sh`, `queue.sh`, `launch.sh`
- **MCP-сервер** — 17 tools для Claude Code, Cursor, и любого MCP-клиента
- **Cursor rules** — `.mdc` правила для каждого агента

---

## Pipeline

```
[Идея]
  │
  Phase 0: Discovery     — Business Analyst → BRD, Product Manager → PRD
  Phase 1: Design         — Architect → ADR, system-design, GOAL.md
  Phase 2: Planning       — Primary Planner → backlog, Sub-Planner → tasks
  Phase 3: Build          — Workers → код + тесты, Judge → review + commit
  Phase 4: Validate       — QA Engineer → qa-report, баги → Phase 3
  Phase 5: Retrospective  — Analyst → retrospective, рекомендации
```

Человек одобряет артефакты между фазами (checkpoint).

---

## Установка

```bash
# Скопируй в свой проект (без node_modules и build)
rsync -a --exclude node_modules --exclude build .agent-factory/ /path/to/your-project/.agent-factory/
cp CLAUDE.md .mcp.json /path/to/your-project/
cp -r .cursor/ /path/to/your-project/

# Собери MCP-сервер
cd /path/to/your-project/.agent-factory/mcp-server
npm install && npm run build
```

MCP-сервер подхватится автоматически через `.mcp.json` (Claude Code) или `.cursor/mcp.json` (Cursor).

---

## Quick Start

### Вариант 1: Полный pipeline (с Phase 0)

```bash
# Запусти Discovery
bash .agent-factory/scripts/phase.sh start 0
bash .agent-factory/scripts/launch.sh business-analyst    # → BRD
bash .agent-factory/scripts/launch.sh product-manager     # → PRD

# Одобри и переходи к Design
bash .agent-factory/scripts/phase.sh complete 0
bash .agent-factory/scripts/launch.sh architect            # → ADR + GOAL.md

# Одобри и переходи к Planning
bash .agent-factory/scripts/phase.sh complete 1
bash .agent-factory/scripts/launch.sh primary-planner      # → домены
bash .agent-factory/scripts/launch.sh sub-planner          # → задачи

# Build
bash .agent-factory/scripts/phase.sh complete 2
WORKER_ID=worker-1 bash .agent-factory/scripts/launch.sh worker
bash .agent-factory/scripts/launch.sh judge
```

### Вариант 2: Классический (с GOAL.md)

Если уже знаешь что строить — пропусти Discovery и Design:

```bash
# Напиши GOAL.md вручную
vim .agent-factory/GOAL.md

# Пропусти первые фазы
bash .agent-factory/scripts/phase.sh skip 0
bash .agent-factory/scripts/phase.sh skip 1

# Начни с Planning
bash .agent-factory/scripts/phase.sh start 2
bash .agent-factory/scripts/launch.sh primary-planner
bash .agent-factory/scripts/launch.sh sub-planner

# Build
WORKER_ID=worker-1 bash .agent-factory/scripts/launch.sh worker
bash .agent-factory/scripts/launch.sh judge
```

---

## Команды

### Управление фазами

```bash
bash .agent-factory/scripts/phase.sh status          # текущая фаза и прогресс
bash .agent-factory/scripts/phase.sh start <N>       # начать фазу N (0-5)
bash .agent-factory/scripts/phase.sh complete <N>    # завершить фазу (авто-переход)
bash .agent-factory/scripts/phase.sh skip <N>        # пропустить фазу
bash .agent-factory/scripts/phase.sh reset <N>       # сбросить фазу
bash .agent-factory/scripts/phase.sh agents <N>      # список агентов фазы
```

### Управление очередью (Phase 3)

```bash
bash .agent-factory/scripts/queue.sh status              # обзор очереди
bash .agent-factory/scripts/queue.sh list todo            # список доступных задач
bash .agent-factory/scripts/queue.sh claim <file>         # взять задачу (worker)
bash .agent-factory/scripts/queue.sh submit <file>        # отправить на ревью (worker)
bash .agent-factory/scripts/queue.sh reject <file>        # отклонить (judge)
bash .agent-factory/scripts/queue.sh done <file>          # одобрить (judge)
```

---

## Агенты

| Phase | Агент | Что делает | Артефакт |
|-------|-------|------------|----------|
| 0 | Business Analyst | Задаёт уточняющие вопросы, исследует рынок | BRD.md |
| 0 | Product Manager | Пишет user stories, определяет MVP | PRD.md |
| 1 | Architect | Проектирует архитектуру, выбирает стек | ADR/, system-design.md, GOAL.md |
| 2 | Primary Planner | Декомпозирует проект на домены | backlog/*.md |
| 2 | Sub-Planner | Разбивает домены на атомарные задачи | todo/*.md |
| 3 | Worker (N штук) | Пишет код и тесты | код |
| 3 | Judge | Ревьюит, тестирует, коммитит | git commits |
| 4 | QA Engineer | Проверяет покрытие по PRD | qa-report.md |
| 5 | Retrospective Analyst | Анализирует метрики, извлекает уроки | retrospective.md |

---

## MCP-сервер

TypeScript MCP-сервер предоставляет 17 tools. Работает параллельно с bash-скриптами — оба читают и пишут одни и те же файлы.

**Сборка:** `cd .agent-factory/mcp-server && npm install && npm run build`

**Подключение:** автоматически через `.mcp.json` (Claude Code) или `.cursor/mcp.json` (Cursor).

| Группа | Tools |
|--------|-------|
| Phase (6) | `phase_status`, `phase_start`, `phase_complete`, `phase_skip`, `phase_reset`, `phase_agents` |
| Queue (7) | `queue_status`, `queue_list`, `task_claim`, `task_submit`, `task_reject`, `task_done`, `task_return` |
| Agent (4) | `agent_list`, `agent_get_prompt`, `get_goal`, `create_artifact` |

Когда MCP подключен, AI-клиент может управлять фазами и очередью напрямую через tools — без bash.

---

## Cursor IDE

`.cursor/rules/` содержит `.mdc` правила для каждого агента. Запуск через Composer (Cmd+I) в режиме Agent:

```
@business-analyst.mdc Act as Business Analyst. Read the raw idea and produce BRD.
@product-manager.mdc Act as Product Manager. Read BRD and produce PRD.
@architect.mdc Act as Architect. Read PRD and produce ADR + system-design + GOAL.md.
@primary-planner.mdc Act as Primary Planner. Read GOAL.md and decompose into domains.
@sub-planner.mdc Act as Sub-Planner. Read backlog/ and create atomic tasks.
@worker.mdc Act as Worker. Find and claim a task from the queue.
@judge.mdc Act as Judge. Check review/ queue and evaluate completed tasks.
@qa-engineer.mdc Act as QA Engineer. Validate the build against PRD.
@retrospective-analyst.mdc Act as Retrospective Analyst. Analyze and produce retrospective.
```

---

## Структура проекта

```
project-root/
├── .agent-factory/
│   ├── phases/
│   │   ├── phase.config.md          # состояние фаз
│   │   ├── 0-discovery/
│   │   │   ├── agents/              # business-analyst.md, product-manager.md
│   │   │   ├── artifacts/           # BRD.md, PRD.md (генерируются)
│   │   │   └── templates/           # шаблоны
│   │   ├── 1-design/
│   │   │   ├── agents/              # architect.md
│   │   │   ├── artifacts/           # ADR/, system-design.md
│   │   │   └── templates/
│   │   ├── 2-planning/
│   │   │   └── agents/              # primary-planner.md, sub-planner.md
│   │   ├── 3-build/
│   │   │   ├── agents/              # worker.md, judge.md
│   │   │   └── queue -> ../../queue
│   │   ├── 4-validate/
│   │   │   ├── agents/              # qa-engineer.md
│   │   │   ├── artifacts/           # qa-report.md
│   │   │   └── templates/
│   │   └── 5-retrospective/
│   │       ├── agents/              # retrospective-analyst.md
│   │       ├── artifacts/           # retrospective.md
│   │       └── templates/
│   ├── queue/                       # backlog/ todo/ in-progress/ review/ done/
│   ├── mcp-server/                  # TypeScript MCP-сервер
│   │   ├── src/                     # исходники
│   │   ├── build/                   # JS (gitignored)
│   │   └── package.json
│   ├── scripts/
│   │   ├── phase.sh                 # управление фазами
│   │   ├── queue.sh                 # управление очередью
│   │   └── launch.sh               # запуск агентов
│   ├── GOAL.md                      # цели проекта
│   └── README.md                    # этот файл
├── .cursor/
│   ├── rules/                       # .mdc правила (10 файлов)
│   └── mcp.json                     # MCP конфиг для Cursor
├── .mcp.json                        # MCP конфиг для Claude Code
└── CLAUDE.md                        # инструкции для AI-агентов
```

---

## Ключевые принципы

- **GOAL.md** — источник правды. Все агенты читают его.
- **Атомарные операции** — `mkdir` как лок, два воркера не возьмут одну задачу.
- **Judge = gatekeeper** — только Judge коммитит код.
- **Параллельные воркеры** — каждый берёт свою задачу.
- **Checkpoints** — человек одобряет артефакты между фазами.
- **Hybrid** — bash и MCP работают с одними файлами, используй что удобнее.

## Tips

1. **Начни последовательно.** Planner → Sub-Planner → 1 Worker → Judge.
2. **Держи GOAL.md актуальным.** Это твоя панель управления.
3. **Следи за Judge.** Он покажет когда что-то ломается.
4. **Маленькие задачи лучше.** Если воркер буксует — задача слишком большая.
5. **`phase.sh status` и `queue.sh status`** — используй часто.
