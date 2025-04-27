import os
import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import locale
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from ta.trend import MACD
import telegram
from telegram import InputFile
import asyncio
from datetime import datetime

# === Definir locale para português (Windows) ===
try:
    locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil')
except locale.Error:
    print("⚠️ Locale 'Portuguese_Brazil' não disponível. Verifique suporte no sistema.")

# === Configuração do Telegram usando variáveis de ambiente ===
token = os.environ["TELEGRAM_TOKEN"]
chat_id = os.environ["TELEGRAM_CHAT_ID"]

bot = telegram.Bot(token=token)

# Lista de ações para analisar
acoes = ["VALE3.SA", "PETR4.SA", "ITSA4.SA", "BBAS3.SA", "BBDC4.SA", "CSMG3.SA", "SAPR11.SA", "TAEE11.SA", "CMIG4.SA"]

melhores_para_compra = []
melhores_para_venda = []
rsi_hoje_lista = []
alertas_acao = {}
acoes_movimento = []

# === Função assíncrona para enviar foto e mensagem ===
async def enviar_telegram(imagem_path, mensagem, bot_param=None, chat_id_param=None):
    if bot_param is None:
        bot_param = bot
    if chat_id_param is None:
        chat_id_param = chat_id

    if imagem_path:
        with open(imagem_path, 'rb') as f:
            await bot_param.send_photo(chat_id=chat_id_param, photo=f)

    await bot_param.send_message(chat_id=chat_id_param, text=mensagem)
    print(mensagem)

# === Função principal de análise ===
async def analisar_acoes():
    hojedata = datetime.now()
    await enviar_telegram(None, f"🎯 Início da análise de {hojedata.strftime('%d/%m/%Y')}. Enviado pelo GitHub.")

    alerta_final = f"📋 Resumo Final de {hojedata.strftime('%d/%m/%Y')}:\n\n"
    alerta_urgente_sinal = 0

    for acao in acoes:
        print(f"🔄 Analisando {acao}...")
        await enviar_telegram(None, f"📊 Análise de {acao}:")

        df = yf.download(acao, period="13mo", interval="1d")
        df.dropna(inplace=True)

        df['MA20'] = df['Close'].rolling(window=20).mean()
        rsi = RSIIndicator(close=df['Close'].squeeze(), window=14)
        df['RSI'] = rsi.rsi()
        bb = BollingerBands(close=df['Close'].squeeze(), window=20, window_dev=2)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()
        macd = MACD(df['Close'].squeeze(), window_slow=26, window_fast=12, window_sign=9)
        df['MACD'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()

        df.dropna(inplace=True)

        # === Plot ===
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 15), sharex=True)

        ax1.plot(df.index, df['Close'], label='Fechamento', color='blue')
        ax1.plot(df.index, df['MA20'], label='MA20', color='orange')
        ax1.plot(df.index, df['bb_upper'], label='Banda Superior', linestyle='--', color='green')
        ax1.plot(df.index, df['bb_lower'], label='Banda Inferior', linestyle='--', color='red')
        ax1.fill_between(df.index, df['bb_lower'], df['bb_upper'], color='gray', alpha=0.1)
        ax1.set_title(f'{acao} - Fechamento, MA20 e Bandas de Bollinger')
        ax1.legend()
        ax1.grid(True)
        ax1.xaxis.set_major_locator(mdates.MonthLocator())
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b-%Y'))
        ax1.tick_params(axis='x', labelbottom=True)

        ax2.plot(df.index, df['RSI'], label='RSI (14)', color='blue')
        ax2.axhline(70, color='red', linestyle='--', alpha=0.5)
        ax2.axhline(30, color='green', linestyle='--', alpha=0.5)
        ax2.set_title('RSI - Índice de Força Relativa')
        ax2.set_ylim(0, 100)
        ax2.grid(True)
        ax2.legend()

        ax3.plot(df.index, df['MACD'], label='MACD', color='blue')
        ax3.plot(df.index, df['MACD_signal'], label='Linha de Sinal', color='orange', linestyle='--')
        ax3.bar(df.index, df['MACD'] - df['MACD_signal'], label='Histograma MACD', color='gray', alpha=0.3)
        ax3.set_title('MACD - Convergência/Divergência de Médias')
        ax3.grid(True)
        ax3.legend()
        ax3.xaxis.set_major_locator(mdates.MonthLocator())
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%b-%Y'))
        ax3.tick_params(axis='x', rotation=45)
        ax3.set_xlabel('Mês')

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.15)

        filename = f"{acao.replace('.SA', '')}_analise_tecnica.png"
        plt.savefig(filename)
        plt.close()

        print(f"✅ Gráfico para {acao} gerado com sucesso!")

        ultima = df.tail(1).squeeze()
        rsi_hoje = ultima['RSI']
        nome_acao = acao.replace(".SA", "")
        rsi_hoje_lista.append((nome_acao, rsi_hoje))

        if rsi_hoje < 30 and ultima['Close'] < ultima['bb_lower']:
            melhores_para_compra.append(nome_acao)
            alerta_urgente_sinal = 1

        if rsi_hoje > 70 and ultima['Close'] > ultima['bb_upper']:
            melhores_para_venda.append(nome_acao)
            alerta_urgente_sinal = 1

        # Enviar gráfico e resultados para o Telegram
        await enviar_telegram(filename, f"----------------------------------")

    # Ordenar pela maior variação RSI
    rsi_hoje_lista.sort(key=lambda x: x[1], reverse=True)

    lista_rsi = "\n📶 Ações ordenadas por RSI:\n"
    for acao, rsi_valor in rsi_hoje_lista:
        lista_rsi += f"{acao}: RSI = {rsi_valor:.2f}\n"

    alerta_final += lista_rsi
    await enviar_telegram(None, alerta_final)

    if alerta_urgente_sinal == 1:
        alerta_urgente = f"🚨 Alerta Urgente de {hojedata.strftime('%d/%m/%Y')}:\n\n"
        for acao, rsi_valor in rsi_hoje_lista:
            if acao in melhores_para_compra:
                alerta_urgente += f"📈 {acao} em CONDIÇÃO DE COMPRA (RSI={rsi_valor:.2f})\n\n"
            elif acao in melhores_para_venda:
                alerta_urgente += f"📉 {acao} em CONDIÇÃO DE VENDA (RSI={rsi_valor:.2f})\n\n"

        # Enviar alerta urgente também para o outro bot
        outro_token = os.environ["OUTRO_TELEGRAM_TOKEN"]
        outro_chat_id = os.environ["OUTRO_TELEGRAM_CHAT_ID"]
        outro_bot = telegram.Bot(token=outro_token)
        await enviar_telegram(None, alerta_urgente, bot_param=outro_bot, chat_id_param=outro_chat_id)

# === Rodar a análise ===
asyncio.run(analisar_acoes())
