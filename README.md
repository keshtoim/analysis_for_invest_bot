# Analysis for Invest Bot

Telegram-бот для инвесторов, который проводит анализ компаний по открытым источникам
(новости, отчётность, публичные данные) с помощью ИИ (ChatGPT / Claude).

## Что делает бот

Пользователь отправляет боту название компании — бот собирает информацию из проверенных
открытых источников и с помощью нейросети формирует структурированный анализ компании
по одному или нескольким аналитическим фреймворкам (например, по типу SWOT), помогая
пользователю принять взвешенное инвестиционное решение.

Функциональность бота (набор кнопок, доступные виды анализа и т.д.) находится в разработке
и будет расширяться.

## MVP-сценарий

1. Пользователь запускает бота (`/start`) → бот сохраняет юзера
2. Пользователь отправляет название компании
3. Бот проверяет анти-флуд
4. ↓
5. Бот показывает кнопки выбора вида анализа (SWOT / PESTEL / 5 сил Портера / мультипликаторы)
6. Пользователь выбирает один или несколько видов анализа
7. ↓
8. Бот проверяет кэш данных о компании
9a. Данные свежие в кэше → берём их
9b. Данных нет / устарели → собираем из открытых источников и новостей, кладём в кэш
10. ↓
11. Бот отправляет данные в AI-провайдера (Claude / ChatGPT) отдельно по каждому выбранному виду анализа
12. Бот собирает и отправляет пользователю готовый анализ

## Ключевые возможности

| Область | Что умеет |
|---|---|
| Взаимодействие с ботом | `/start`, отправка названия компании, выбор вида анализа кнопками |
| Виды анализа | SWOT (на старте); PESTEL, 5 сил Портера, финансовые мультипликаторы — в разработке |
| Сбор данных | Новости + открытые источники о компании, агрегация под конкретный запрос |
| Кэш данных | Сырые данные о компании кэшируются с TTL — не дёргаем источники повторно |
| AI-анализ | Генерация анализа через Claude или ChatGPT, провайдер переключается конфигом |
| Хранение | Локальная SQLite: пользователи, кэш данных о компаниях |
| Анти-флуд | Защита от спам-запросов (в разработке) |
| Деплой | Docker / docker-compose для развёртывания на сервере |

## Архитектура системы

```mermaid
graph TD
    U[Пользователь Telegram]

    subgraph TG["Telegram"]
        API[Telegram Bot API]
    end

    subgraph APP["Бот-приложение (aiogram, Docker)"]
        H[Handlers / Routers]
        AF[Анти-флуд middleware]
        AS[Analysis Service]
        CDS[Company Data Service<br/>+ кэш с TTL]
        AIP[AI Provider Adapter<br/>OpenAI / Anthropic]
    end

    subgraph EXT["Внешние источники"]
        NEWS[Новостные API]
        OPEN[Открытые данные о компаниях]
        AI[Claude / ChatGPT API]
    end

    DB[(SQLite<br/>users, company_cache)]

    U <--> API
    API <--> H
    H --> AF
    H --> AS
    AS --> CDS
    AS --> AIP
    CDS --> NEWS
    CDS --> OPEN
    CDS --> DB
    AIP --> AI
    H --> DB
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

Таблицы не связаны между собой — кэш компаний общий для всех пользователей, не привязан
к конкретному юзеру.

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
    }

    class AnalysisRequest {
        +str company_name
        +list~AnalysisType~ types
    }

    class AnalysisResult {
        +str company_name
        +dict~AnalysisType, str~ sections
    }

    class AnalysisService {
        +run(request: AnalysisRequest) AnalysisResult
    }

    class CompanyDataService {
        +get_company_data(company_name: str) CompanyData
    }

    class CompanyData {
        +str company_name
        +dict raw_data
        +datetime fetched_at
    }

    class AIProvider {
        <<interface>>
        +generate_analysis(data: CompanyData, type: AnalysisType) str
    }

    class OpenAIProvider
    class AnthropicProvider

    class DataSource {
        <<interface>>
        +fetch(company_name: str) dict
    }

    class NewsDataSource
    class OpenDataSource

    AnalysisService --> CompanyDataService
    AnalysisService --> AIProvider
    AnalysisService --> AnalysisRequest
    AnalysisService --> AnalysisResult
    AIProvider <|.. OpenAIProvider
    AIProvider <|.. AnthropicProvider
    CompanyDataService --> DataSource
    CompanyDataService --> CompanyData
    DataSource <|.. NewsDataSource
    DataSource <|.. OpenDataSource
    AnalysisRequest --> AnalysisType
    AnalysisResult --> AnalysisType
```

## Жизненный цикл обращения (Activity Diagram)

```mermaid
flowchart TD
    Start([Пользователь отправляет название компании]) --> Flood{Анти-флуд:<br/>не спамит?}
    Flood -- нет --> Wait[Сообщение: подождите] --> End1([Конец])
    Flood -- да --> Menu[Показать кнопки выбора вида анализа]
    Menu --> Choice[Пользователь выбирает<br/>один или несколько видов анализа]
    Choice --> Cache{Данные о компании<br/>есть в кэше и не устарели?}
    Cache -- да --> UseCache[Взять данные из кэша]
    Cache -- нет --> Fetch[Запросить данные:<br/>новости + открытые источники]
    Fetch --> SaveCache[Сохранить в кэш с TTL]
    SaveCache --> UseCache
    UseCache --> Loop[Для каждого выбранного вида анализа]
    Loop --> AI[Запрос к AI-провайдеру<br/>Claude/ChatGPT]
    AI --> Collect[Собрать результаты]
    Collect --> Send[Отправить анализ пользователю]
    Send --> End2([Конец])
```

## Карта прецедентов (Use Case Diagram)

```mermaid
flowchart LR
    Investor((Инвестор))
    News[/Внешние источники данных/]
    AIExt[/AI-провайдер/]

    UC1([Запросить анализ компании])
    UC2([Выбрать вид анализа:<br/>SWOT / PESTEL / 5 сил Портера / мультипликаторы])
    UC3([Получить справку])

    Investor --> UC1
    Investor --> UC3
    UC1 -.включает.-> UC2
    UC1 -.использует.-> News
    UC1 -.использует.-> AIExt
```
