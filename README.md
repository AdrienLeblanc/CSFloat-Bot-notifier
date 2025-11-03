# CSFloat Bot notifier

## Description
CSFloat Bot notifier is a simple Python script that sends notifications to a specified Discord channel using a Discord bot.

It watches specific filters and sends a message to the Discord channel whenever a new item matching the filters is found.

## Configuration
Before running the script, you need to configure the following variables in .env.secrets file:
- `DISCORD_WEBHOOK`: The webhook URL of your Discord channel.
- `DISCORD_USER_ID`: The user ID to be mentioned in the notification.
- `CSFLOAT_TOKEN`: Your CSFloat API token.
- `OPEN_EXCHANGE_RATES_TOKEN` : Your Open Exchange Rates API token.

## Run
To run the script, use the following command:
```bash
python bot.py
```

## Build
To build a standalone executable using PyInstaller, use the following command:
```bash
python build_exe.py
```

## Application
You can run the built executable from the `dist` folder:

To display some statistics over the last 24h, press `S`

