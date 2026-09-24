# Analysis for Invest Bot

Telegram-бот для инвесторов, который проводит анализ компаний по открытым источникам
(новости, биржевые данные) с помощью ИИ (Claude, в том числе через OpenAI-совместимые
шлюзы вроде Timeweb AI Gateway).

## Что делает бот

Пользователь отправляет боту название компании — бот собирает данные из открытых
источников (новости по компании и по её сектору, котировки и капитализация с MOEX)
и с помощью нейросети формирует структурированный анализ по одному из пяти
фреймворков: SWOT, PESTEL, 5 сил Портера, финансовые мультипликаторы или обзор
сектора. Сектор компании ИИ определяет сам и учитывает его контекст во всех видах
анализа, а не только в отдельном «Обзоре сектора».

Для новых пользователей есть отдельная ветка онбординга («Только начинаю» /
«Уже инвестирую») с базовой информацией о том, как вообще начать инвестировать —
без ИИ, статический текст. Бот везде явно указывает, что выдаёт только аналитику,
а не индивидуальные инвестиционные рекомендации.

## MVP-сценарий

1. Пользователь запускает бота (`/start`) → бот сохраняет юзера, показывает
   приветствие с дисклеймером и reply-кнопку «Начать»
2. «Начать» → бот спрашивает про опыт: «Только начинаю» / «Уже инвестирую»
3a. **Новичок** → инлайн-меню: «С чего начать» (статический текст: с 18 лет,
    брокерский счёт, ИИС — с кнопкой «Понял, дальше») или сразу «Анализ компаний»
3b. **Опытный** → инлайн-меню: «Анализ компаний» или «Виды анализа» (описание
    всех пяти фреймворков)
4. Пользователь отправляет название компании → бот показывает меню видов анализа
   с кратким описанием каждого и эмодзи
5. Пользователь выбирает вид анализа → бот проверяет анти-флуд (кулдаун именно на
   этом действии, не на каждом сообщении — дорогая операция это сбор данных + ИИ,
   а не сама переписка)
6. Бот проверяет кэш данных о компании (SQLite, TTL)
6a. Данные свежие в кэше → берёт их (компания + новости сектора уже внутри)
6b. Данных нет / устарели → собирает: новости по компании (Google News RSS),
    котировки и капитализация (MOEX ISS API), затем отдельным коротким запросом
    к ИИ определяет сектор и подтягивает новости уже по нему; если сектор
    определить не удалось — анализ компании всё равно идёт, просто без него
7. Бот отправляет собранные данные в AI-провайдера (Claude напрямую или через
   OpenAI-совместимый шлюз) с промптом под выбранный вид анализа
8. Бот отправляет юзеру заголовок + текст анализа + дисклеймер, затем предлагает
   выбрать ещё один вид анализа для той же компании (без повторного ввода названия)

## Ключевые возможности

| Область | Что умеет |
|---|---|
| Онбординг | `/start` → reply-кнопки → ветка «новичок»/«опытный» → инлайн-меню под каждую |
| Виды анализа | SWOT, PESTEL, 5 сил Портера, финансовые мультипликаторы, обзор сектора — все реализованы |
| Учёт сектора | ИИ сам определяет отрасль компании, новости по сектору попадают во все виды анализа |
| Сбор данных | Google News RSS (компания + сектор) + MOEX ISS API (котировки, капитализация) |
| Кэш данных | Компания + сектор кэшируются вместе в SQLite с TTL — не дёргаем источники повторно |
| AI-анализ | Claude — напрямую (Anthropic API) или через OpenAI-совместимый шлюз, провайдер переключается конфигом |
| Форматирование | Telegram HTML с эмодзи по разделам, заголовок и дисклеймер в каждом ответе, fallback на обычный текст если Telegram не принял разметку |
| Анти-флуд | Кулдаун именно на запуске анализа (дорогая операция), не на сообщениях/кнопках онбординга |
| Устойчивость к сбоям | Ретраи при сетевых обрывах Telegram, понятная ошибка вместо тишины при недоступности ИИ/источников |
| Compliance | Единый дисклеймер («аналитика, не инвестрекомендация») во всех аналитических и справочных текстах |
| Хранение | Локальная SQLite: пользователи, кэш данных о компаниях |
| Тесты | pytest, 36 тестов на кэш/анти-флуд/выбор бумаги на MOEX/сборку промптов/healthcheck |
| Деплой | Docker + docker-compose, heartbeat-healthcheck, `cloud-init.sh` для чистого сервера, CI на GitHub Actions (сборка образа + тесты на каждый push/PR) |

## Архитектура системы

```mermaid
graph TD
    U[Пользователь Telegram]

    subgraph TG["Telegram"]
        API[Telegram Bot API]
    end

    subgraph APP["Бот-приложение (aiogram, Docker)"]
        H[Handlers: onboarding / analysis / common]
        AF[Анти-флуд<br/>на выборе вида анализа]
        CDS[Company Data Service<br/>+ кэш с TTL]
        AIP[AI Provider Adapter<br/>Anthropic API /<br/>OpenAI-совместимый шлюз]
        HB[Heartbeat loop]
    end

    subgraph EXT["Внешние источники"]
        NEWS[Google News RSS<br/>компания + сектор]
        MOEX[MOEX ISS API]
        AI[Claude<br/>напрямую или через шлюз]
    end

    DB[(SQLite<br/>users, company_cache)]

    U <--> API
    API <--> H
    H --> AF
    H --> CDS
    H --> AIP
    CDS --> NEWS
    CDS --> MOEX
    CDS --> AIP
    AIP --> AI
    CDS --> DB
    H --> DB
    HB --> DB2[(data/heartbeat)]
    HC[Docker HEALTHCHECK] -.читает.-> DB2
```

## Схема базы данных (ER Diagram)

Только то, что реально персистится (истории запросов нет, анти-флуд — в памяти):

```mermaid
erDiagram
    USERS {
        int user_id PK
        string username
        string first_name
        datetime joined_at
    }

    COMPANY_CACHE {
        int id PK
        string company_query
        string source
        json raw_data
        datetime fetched_at
        datetime expires_at
    }
```

Таблицы не связаны между собой — кэш компаний общий для всех пользователей, не
привязан к конкретному юзеру. `raw_data` — единый JSON-блок: новости компании,
данные MOEX и вложенный объект сектора (`{name, news}`) — отдельной таблицы под
сектор нет, он живёт внутри той же строки кэша.

## Доменная модель (Class Diagram)

```mermaid
classDiagram
    class User {
        +int user_id
        +str username
        +str first_name
        +datetime joined_at
    }

    class AnalysisType {
        <<enumeration>>
        SWOT
        PESTEL
        PORTER_FIVE_FORCES
        FINANCIAL_MULTIPLES
        SECTOR_OVERVIEW
    }

    class CompanyData {
        +str company_name
        +list~dict~ news
        +dict moex
        +SectorInfo sector
    }

    class SectorInfo {
        +str name
        +list~dict~ news
    }

    class CompanyDataService {
        +get_company_data(company_name: str) CompanyData
    }

    class AIProvider {
        <<interface>>
        +generate_analysis(data: CompanyData, type: AnalysisType) str
        +identify_sector(company_name: str) str
    }

    class AnthropicProvider
    class OpenAICompatibleProvider

    class DataSource {
        <<interface>>
        +fetch(query: str) dict
    }

    class GoogleNewsSource
    class MoexSource

    class HealthcheckService {
        +is_alive() bool
    }

    CompanyDataService --> DataSource
    CompanyDataService --> CompanyData
    CompanyDataService --> AIProvider : identify_sector
    CompanyData --> SectorInfo
    AIProvider <|.. AnthropicProvider
    AIProvider <|.. OpenAICompatibleProvider
    DataSource <|.. GoogleNewsSource
    DataSource <|.. MoexSource
    CompanyData --> AnalysisType
```

## Жизненный цикл обращения (Activity Diagram)

```mermaid
flowchart TD
    Start([Пользователь отправляет название компании]) --> Menu[Показать меню видов анализа с описаниями]
    Menu --> Choice[Пользователь выбирает вид анализа]
    Choice --> Flood{Анти-флуд:<br/>не спамит именно анализом?}
    Flood -- да --> WaitMsg[Короткое уведомление: подожди] --> End1([Конец])
    Flood -- нет --> Cache{Данные о компании<br/>есть в кэше и не устарели?}
    Cache -- да --> UseCache[Взять компанию + сектор из кэша]
    Cache -- нет --> Fetch[Новости компании + MOEX]
    Fetch --> Sector{Удалось определить сектор?}
    Sector -- да --> SectorNews[Подтянуть новости сектора]
    Sector -- нет --> NoSector[Сектор = null, идём дальше]
    SectorNews --> SaveCache[Сохранить в кэш с TTL]
    NoSector --> SaveCache
    SaveCache --> UseCache
    UseCache --> AI[Промпт под выбранный тип -> AI-провайдер]
    AI --> Send[Заголовок + текст + дисклеймер]
    Send --> Offer[Предложить ещё один вид анализа для той же компании]
    Offer --> End2([Конец])
```

## Карта прецедентов (Use Case Diagram)

```mermaid
flowchart LR
    Investor((Инвестор))
    News[/Google News RSS/]
    Moex[/MOEX ISS API/]
    AIExt[/AI-провайдер/]

    UC1([Запросить анализ компании])
    UC2([Выбрать вид анализа:<br/>SWOT / PESTEL / 5 сил Портера /<br/>мультипликаторы / обзор сектора])
    UC3([Получить справку по боту])
    UC4([Пройти онбординг:<br/>новичок / уже инвестирую])
    UC5([Узнать, с чего начать инвестировать])

    Investor --> UC1
    Investor --> UC3
    Investor --> UC4
    UC4 -.включает для новичка.-> UC5
    UC1 -.включает.-> UC2
    UC1 -.использует.-> News
    UC1 -.использует.-> Moex
    UC1 -.использует.-> AIExt
```
