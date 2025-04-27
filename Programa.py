
#segredos chaves
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
acoes = ["VALE3.SA","PETR4.SA", "ITSA4.SA","BBAS3.SA","BBDC4.SA","CSMG3.SA","SAPR11.SA","TAEE11.SA", "CMIG4.SA"]

melhores_para_compra = []
melhores_para_venda = []
rsi_hoje_lista = []
alertas_acao = {}  # Dicionário para armazenar os alertas de ações
acoes_movimento = []  # Para guardar (ação, movimento, percentual)


# Função assíncrona para enviar foto e mensagem (adaptada para aceitar outros bots/chat_ids)
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


# === Processar cada ação ===
async def analisar_acoes():
    hojedata = datetime.now()
    await enviar_telegram(None, f"🎯 Início da análise de {hojedata.strftime('%d/%m/%Y')}.")
    alerta_final = f"📋 Resumo Final de {hojedata.strftime('%d/%m/%Y')}:\n\n"  # Inicializando a variável alerta_final no início da função ou do bloco relevante
    alerta_urgente_sinal = 0
    alerta_urgente = f"🚨 Alerta Urgente de {hojedata.strftime('%d/%m/%Y')}:\n\n"
    for acao in acoes:
        print(f"🔄 Analisando {acao}...")
        await enviar_telegram(None, f"📊 Análise de {acao}:")


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
        ax2.plot(df.index, df['RSI'], label='RSI (14)', color='blue')
        ax2.axhline(70, color='red', linestyle='--', alpha=0.5)
        ax2.axhline(30, color='green', linestyle='--', alpha=0.5)
        ax2.set_title('RSI - Índice de Força Relativa, Limites de RSI em 70 e 30')
        ax2.set_ylim(0, 100)
        ax2.grid(True)
        ax2.legend()

        # Gráfico de MACD
        ax3.plot(df.index, df['MACD'], label='MACD', color='blue')
        ax3.plot(df.index, df['MACD_signal'], label='Linha de Sinal', color='orange', linestyle='--')
        ax3.bar(df.index, df['MACD'] - df['MACD_signal'], label='Histograma MACD', color='gray', alpha=0.3)
        ax3.set_title('Moving Average Convergence Divergence, se MACD cruza acima da linha de sinal: compra. Histograma, mostra força, acima de zero é tendência de alta')
        ax3.grid(True)
        ax3.legend()

        ax3.xaxis.set_major_locator(mdates.MonthLocator())
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%b-%Y'))
        ax3.tick_params(axis='x', rotation=45)
        ax3.set_xlabel('Mês')

        # Ajuste do layout para garantir que tudo fique bem posicionado
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.15) # Ajusta o espaço inferior para não cortar os rótulos do eixo X

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
            alerta_urgente_sinal = 1
            #alerta_urgente +=  f"📈 Ação {acao} está em condição de COMPRA, deve subir em breve.\n"
            #print(f"📈 Ação {acao} está em condição de COMPRA, deve subir em breve.")

        # Verificar condição de venda
        if rsi_hoje > 70 and float(ultima['Close'].iloc[0]) > float(ultima['bb_upper'].iloc[0]):  # Corrigido aqui
            melhores_para_venda.append(nome_acao)
            alerta_urgente_sinal = 1
            #alerta_urgente +=  f"📉 Ação {acao} está em condição de VENDA, deve cair em breve.\n"
            #print(f"📉 Ação {acao} está em condição de VENDA, deve cair em breve.")

        # Verificar subida ou queda nos últimos 7 dias consecutivos
        if len(df) >= 3:  # Precisa de pelo menos 3 dias para começar
            dias_consecutivos = 1  # Começa contando o último par
            preco_fechamento_primeiro_dia = None
            preco_fechamento_ultimo_dia = None

            hoje = df.iloc[-1]  # Linha de hoje
            ontem = df.iloc[-2]  # Linha de ontem

            #Acessando os valores de abertura (Open) e fechamento (Close) para garantir que estamos pegando valores escalares
            preco_abertura_hoje = hoje['Open']  # Preço de abertura
            preco_fechamento_hoje = hoje['Close']  # Preço de fechamento
            preco_abertura_ontem = ontem['Open']  # Preço de abertura ontem
            preco_fechamento_ontem = ontem['Close']  # Preço de fechamento ontem
            # Corrigindo a comparação para valores escalares
            preco_abertura_hoje = preco_abertura_hoje.iloc[0]
            preco_fechamento_hoje = preco_fechamento_hoje.iloc[0]
            preco_abertura_ontem  = preco_abertura_ontem .iloc[0]
            preco_fechamento_ontem  = preco_fechamento_ontem .iloc[0]

                # Primeiro comparar hoje com ontem
            if (preco_fechamento_hoje > preco_abertura_hoje) and (preco_fechamento_ontem > preco_abertura_ontem):
                movimento = 'subida'
            elif (preco_fechamento_hoje < preco_abertura_hoje) and (preco_fechamento_ontem < preco_abertura_ontem):
                movimento = 'queda'
            else:
                movimento = None
                # Se movimento for detectado, continuar comparando para trás
            if movimento:
                preco_fechamento_primeiro_dia = preco_fechamento_ontem
                preco_fechamento_ultimo_dia = preco_fechamento_hoje
                for i in range(len(df) - 2, len(df) - 8, -1):  # Começa no penúltimo dia e vai até 7 dias atrás
                    if i - 1 < 0:
                        break  # Evita acessar índice negativo
                    dia_atual = df.iloc[i]
                    dia_anterior = df.iloc[i - 1]
                    # Acessando os valores de abertura (Open) e fechamento (Close) para garantir que estamos pegando valores escalares
                    preco_abertura_dia_atual = dia_atual['Open']  # Preço de abertura
                    preco_fechamento_dia_atual = dia_atual['Close']  # Preço de fechamento
                    preco_abertura_dia_anterior = dia_anterior['Open']  # Preço de abertura ontem
                    preco_fechamento_dia_anterior = dia_anterior['Close']  # Preço de fechamento ontem
                    # Corrigindo a comparação para valores escalares
                    preco_abertura_dia_atual = preco_abertura_dia_atual.iloc[0]
                    preco_fechamento_dia_atual = preco_fechamento_dia_atual.iloc[0]
                    preco_abertura_dia_anterior = preco_abertura_dia_anterior.iloc[0]
                    preco_fechamento_dia_anterior = preco_fechamento_dia_anterior.iloc[0]

                    if movimento == 'subida' and (preco_fechamento_dia_atual > preco_abertura_dia_atual) and (preco_fechamento_dia_anterior > preco_abertura_dia_anterior):
                        dias_consecutivos += 1
                        preco_fechamento_primeiro_dia = preco_fechamento_dia_anterior
                    elif movimento == 'queda' and (preco_fechamento_dia_atual < preco_abertura_dia_atual) and (preco_fechamento_dia_anterior < preco_abertura_dia_anterior):
                        dias_consecutivos += 1
                        preco_fechamento_primeiro_dia = preco_fechamento_dia_anterior
                    else:
                        break  # Se a sequência quebrou, para
                # Se teve sequência de 2 ou mais
            if movimento and dias_consecutivos >= 2:
                percentual_movimento = (preco_fechamento_ultimo_dia - preco_fechamento_primeiro_dia) / preco_fechamento_primeiro_dia * 100
                acoes_movimento.append((acao, movimento, percentual_movimento, dias_consecutivos))  # <= Aqui guardamos


        # Enviar gráfico e resultados para o Telegram
        await enviar_telegram(f"{acao.replace('.SA','')}_analise_tecnica.png", f"----------------------------------")
        for alerta in alertas_acao.values():
            print(alerta)

    # Ordenar pela maior variação percentual (absoluta)
    acoes_movimento.sort(key=lambda x: abs(x[2]), reverse=True)
    # Criar uma string final para o alerta
    alerta_movimentos = "\n📊 Ações ordenadas por maior variação percentual:\n"
    for acao, movimento, percentual, dias in acoes_movimento:
        if movimento == 'subida':
            alerta_movimentos += f"📈 {acao} subiu {percentual:.2f}% em {dias} dias consecutivos.\n"
        elif movimento == 'queda':
            alerta_movimentos += f"📉 {acao} caiu {percentual:.2f}% em {dias} dias consecutivos.\n"

    print(alerta_movimentos)  # Também imprime no console
    alerta_final += alerta_movimentos

    # Ordenar as ações com base no RSI em ordem crescente
    rsi_hoje_lista.sort(key=lambda x: x[1], reverse=True)

    # Criar lista final com as ações e seus RSI
    lista_rsi = "\n📶 Ações ordenadas por RSI:\n"
    for acao, rsi_valor in rsi_hoje_lista:
        lista_rsi += f"{acao}: RSI = {rsi_valor:.2f}\n"

    # Enviar o alerta final
    alerta_final += lista_rsi

    # Enviar o alerta final para o Telegram
    await enviar_telegram(None, alerta_final)

    # Enviar o alerta urgente para o Telegram, caso tenha
    if alerta_urgente_sinal == 1:
        # Ordenar pelo maior RSI
        #rsi_hoje_lista.sort(key=lambda x: x[1], reverse=True)
        alerta_urgente = f"🚨 Alerta Urgente de {hojedata.strftime('%d/%m/%Y')}:\n\n"
        for acao, rsi_valor in rsi_hoje_lista:
            if acao in melhores_para_compra:
                alerta_urgente += f"📈 {acao} em CONDIÇÃO DE COMPRA, deve subir em breve (RSI={rsi_valor:.2f}).\n\n"
            elif acao in melhores_para_venda:
                alerta_urgente += f"📉 {acao} em CONDIÇÃO DE VENDA, deve cair em breve (RSI={rsi_valor:.2f}).\n\n"

        # Enviar alerta urgente também para o outro bot
        outro_token = os.environ["OUTRO_TELEGRAM_TOKEN"]
        outro_chat_id = os.environ["OUTRO_TELEGRAM_CHAT_ID"]
        outro_bot = telegram.Bot(token=outro_token)
        await enviar_telegram(None, alerta_urgente, bot_param=outro_bot, chat_id_param=outro_chat_id)


# Rodar a análise
asyncio.run(analisar_acoes())
