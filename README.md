# Honeypot Checker

## О проекте

**Honeypot Checker** — это инструмент для анализа криптовалютных токенов и проверки их на скам. Скрипт собирает данные о введенном адресе токена и предоставляет сводную информацию о возможных рисках.

Основные функции:
- Проверка смарт-контрактов на открытость исходного кода.
- Анализ концентрации средств среди владельцев токена.
- Оценка газовых лимитов и налогов на транзакции.
- Выявление подозрительных кошельков и проверка на Honeypot-ловушки.

## Начало работы

### Предварительные требования

Для запуска проекта необходимо:
1. Установленный Python 3.8 или новее.
2. Аккаунт на Etherscan с API-ключом.
3. Web3-провайдер (например, Infura или Alchemy).

### Установка

1. Клонируйте репозиторий:
   ```bash
   git clone <URL вашего репозитория>
   cd honeypot_checker
   ```

2. Установите виртуальное окружение и активируйте его:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

4. Настройте переменные окружения:
   - Скопируйте пример файла `.env`:
     ```bash
     cp .env.example .env
     ```
   - Заполните `.env`:
     ```text
     ETHERSCAN_API_KEY=ваш_api_ключ
     WEB3_PROVIDER_URL=ваш_web3_провайдер
     ```

### Использование

Запустите скрипт, передав адрес токена в качестве аргумента:
```bash
python src/honeypot_checker.py <ethereum_address>
```

Пример:
```bash
python src/honeypot_checker.py 0xdAC17F958D2ee523a2206206994597C13D831ec7
```

Вывод будет содержать анализ адреса токена в формате JSON.

## Структура проекта

```
src/
├── honeypot_checker.py       # Главный скрипт анализа
├── utils.py                  # Утилиты (валидация адресов и др.)
├── helpers/
│   ├── etherscan_api.py      # Работа с API Etherscan
├── analysis/
│   ├── contracts_analyzer.py # Анализ смарт-контрактов
│   ├── wallet_analyzer.py    # Анализ владельцев токенов
```

## Основные методы

### HoneypotChecker
- `analyze_address(address: str) -> dict`: Проводит полный анализ токена.
- `analyze_from_outer_scope(address: str)`: Сбор данных из внешних источников.

### EtherscanAPI
- `get_contract_abi(address: str) -> dict`: Получение ABI контракта.
- `is_contract_verified(address: str) -> bool`: Проверка на верификацию контракта.

### WalletAnalyzer
- `analyze_holders(address: str) -> dict`: Анализ кошельков

### ContractsAnalyzer
- `analyze_contract(abi: dict, address: str) -> dict`: Анализ контракта на налоги и ограничения.

## Пример вывода

```json
{
    "token_address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "source_code_status": "open_source",
    "buy_tax": 0.5,
    "sell_tax": 1.0,
    "transfer_tax": 0.2,
    "holders_analyzed": 1500,
    "siphoned_wallets": 10,
    "is_honeypot": false
}
```