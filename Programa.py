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

# === Definir locale para português (Windows) ===
try:
    locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil')
except locale.Error:
    print("⚠️ Locale 'Portuguese_Brazil' não disponível. Verifique suporte no sistema.")

# Configuração do Telegram
import os
token = os.environ["TELEGRAM_TOKEN"]
chat_id = os.environ["TELEGRAM_CHAT_ID"]

bot = telegram.Bot(token=token)

# Lista de ações para analisar
acoes = ["VALE3.SA", "ITSA4.SA", "CMIG4.SA"]

melhores_para_compra = []
rsi_hoje_lista = []

# Função assíncrona para enviar foto e mensagem
async def enviar_telegram(imagem_path, mensagem):
    if imagem_path:
        # Enviar foto apenas se imagem_path for válido
        with open(imagem_path, 'rb') as f:
            await bot.send_photo(chat_id=chat_id, photo=f)
    # Enviar a mensagem
    await bot.send_message(chat_id=chat_id, text=mensagem)

# === Processar cada ação ===
async def analisar_acoes():
    for acao in acoes:
        print(f"🔄 Analisando {acao}...")

        # Baixar dados da ação
        df = yf.download(acao, period="13mo", interval="1d")
        df.dropna(inplace=True)

        # Cálculo da MA20
        df['MA20'] = df['Close'].rolling(window=20).mean()

        # Cálculo do RSI
        rsi = RSIIndicator(close=df['Close'].squeeze(), window=14)
        df['RSI'] = rsi.rsi()

        # Cálculo das Bandas de Bollinger
        bb = BollingerBands(close=df['Close'].squeeze(), window=20, window_dev=2)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()

        # Cálculo do MACD
        macd = MACD(df['Close'].squeeze(), window_slow=26, window_fast=12, window_sign=9)
        df['MACD'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()

        df.dropna(inplace=True)

        # === Plot ===
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 15), sharex=True)

        # Gráfico de Preço
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

        # RSI
        ax2.plot(df.index, df['RSI'], label='RSI (14)', color='purple')
        ax2.axhline(70, color='red', linestyle='--', alpha=0.5)
        ax2.axhline(30, color='green', linestyle='--', alpha=0.5)
        ax2.set_title('RSI - Índice de Força Relativa')
        ax2.set_ylim(0, 100)
        ax2.grid(True)
        ax2.legend()

        # Gráfico de MACD
        ax3.plot(df.index, df['MACD'], label='MACD', color='blue')
        ax3.plot(df.index, df['MACD_signal'], label='Linha de Sinal', color='orange', linestyle='--')
        ax3.bar(df.index, df['MACD'] - df['MACD_signal'], label='Histograma MACD', color='gray', alpha=0.3)
        ax3.set_title('MACD - Moving Average Convergence Divergence')
        ax3.grid(True)
        ax3.legend()

        ax3.xaxis.set_major_locator(mdates.MonthLocator())
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%b-%Y'))
        ax3.tick_params(axis='x', rotation=45)
        ax3.set_xlabel('Mês')

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.15)

        filename = f"{acao.replace('.SA','')}_analise_tecnica.png"
        plt.savefig(filename)
        plt.close()

        print(f"✅ Gráfico para {acao} gerado com sucesso!")

        # Coleta do RSI de hoje
        ultima = df.tail(1).squeeze()
        rsi_hoje = float(ultima['RSI'].iloc[0])  # Corrigido aqui
        nome_acao = acao.replace(".SA", "")
        rsi_hoje_lista.append((nome_acao, rsi_hoje))

        # Verificar condição de compra
        if rsi_hoje < 30 and float(ultima['Close'].iloc[0]) < float(ultima['bb_lower'].iloc[0]):  # Corrigido aqui
            melhores_para_compra.append(nome_acao)

        # Verificar condição de venda
        if rsi_hoje > 70 and float(ultima['Close'].iloc[0]) > float(ultima['bb_upper'].iloc[0]):  # Corrigido aqui
            print(f"🔴 Alerta! Ação {acao} está em condição de VENDA.")

        # Enviar gráfico e resultados para o Telegram
        await enviar_telegram(filename, f"📊 Análise para {acao}: ")

    # Mostrar resultados finais
    print("\n📊 Resultados do dia:")
    if melhores_para_compra:
        print("🟢 Ações com boa condição de COMPRA hoje: ")
        for acao in melhores_para_compra:
            print(f"➡️ {acao}")
    else:
        print("⚠️ Nenhuma ação com condição clara de compra hoje.")

    print("\n📉 RSI de hoje (em ordem crescente):")
    for nome, rsi_valor in rsi_hoje_lista:
        print(f"{nome}: RSI = {rsi_valor:.2f}")

    # Enviar os resultados para o Telegram
    mensagem = "📊 Resultados do dia:\n"

    if melhores_para_compra:
        mensagem += "\n🟢 Ações com boa condição de COMPRA hoje: \n"
        for acao in melhores_para_compra:
            mensagem += f"➡️ {acao}\n"
    else:
        mensagem += "⚠️ Nenhuma ação com condição clara de compra hoje.\n"

    mensagem += "\n📉 RSI de hoje (em ordem crescente):\n"
    for nome, rsi_valor in rsi_hoje_lista:
        mensagem += f"{nome}: RSI = {rsi_valor:.2f}\n"

    # Adicionar mensagem de boa noite no final
    mensagem += "\n🌙 Boa noite-do github!"

    # Enviar a mensagem final com "Boa noite!" para o Telegram
    await enviar_telegram(None, mensagem)

# Rodar o loop assíncrono
asyncio.run(analisar_acoes())
