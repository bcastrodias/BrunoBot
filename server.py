from fastapi import FastAPI, HTTPException
import requests
import time
import hmac
import hashlib
import os

app = FastAPI()

# 🔐 Configurações de segurança e API (Definidas no ambiente do Render)
SECRET_KEY = os.getenv("WEBHOOK_SECRET", "776wHZXU2cMOUNs0KdI63RxVA9uIz5QT")  
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "SUA_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "SEU_API_SECRET")
BYBIT_BASE_URL = "https://api-testnet.bybit.com"  # Testnet da Bybit

# 🛠️ Função para gerar assinatura HMAC SHA256 exigida pela Bybit
def generate_signature(api_secret, params):
    sorted_params = sorted(params.items())  # Ordenar parâmetros
    query_string = "&".join(f"{key}={value}" for key, value in sorted_params)
    signature = hmac.new(api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return signature

# 📡 Endpoint fixo do webhook no Render
@app.post("/webhooks/tradeview")
async def webhook(data: dict):
    try:
        print(f"📩 Recebido: {data}")

        # 🔍 Validação do segredo (auth)
        if data.get("secret") != SECRET_KEY:
            raise HTTPException(status_code=403, detail="🚨 Acesso negado! Secret inválido.")

        # Pegando os parâmetros do TradingView
        action = data.get("action")  # "long", "short", "exit"
        symbol = data.get("symbol", "ETHUSDT")
        quantity = float(data.get("quantity", 0.01))
        leverage = data.get("leverage", "3")  # Padrão 3x

        if action not in ["long", "short", "exit"]:
            raise HTTPException(status_code=400, detail="🚨 Ação inválida!")

        # 🚀 Definir alavancagem antes de enviar ordens
        set_leverage(symbol, leverage)

        # 🔥 Enviar ordem para a Bybit Testnet
        order_response = place_order(symbol, action, quantity)

        return {"status": "success", "order_response": order_response}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 📌 Função para definir alavancagem (Requerido para futuros perpétuos)
def set_leverage(symbol, leverage):
    """ Define a alavancagem antes de operar nos futuros perpétuos """
    
    params = {
        "api_key": BYBIT_API_KEY,
        "symbol": symbol,
        "leverage": leverage,
        "timestamp": int(time.time() * 1000),
    }

    params["sign"] = generate_signature(BYBIT_API_SECRET, params)
    
    url = f"{BYBIT_BASE_URL}/v2/private/position/leverage"
    response = requests.post(url, data=params)
    
    print(f"🔧 Definição de alavancagem: {response.json()}")

# 🏦 Função para enviar a ordem de mercado para a Bybit
def place_order(symbol, action, quantity):
    """ Envia ordem para o mercado de contratos futuros perpétuos na Bybit Testnet """
    
    side = "Buy" if action == "long" else "Sell"

    order_params = {
        "api_key": BYBIT_API_KEY,
        "symbol": symbol,
        "side": side,
        "category": "futures",  # Define que estamos operando futuros perpétuos
        "order_type": "Market",
        "qty": quantity,
        "time_in_force": "GoodTillCancel",
        "reduce_only": False,  # Somente para fechar posições (ajustável)
        "close_on_trigger": False,
        "timestamp": int(time.time() * 1000),
    }

    # 🔐 Gerar assinatura para autenticação
    order_params["sign"] = generate_signature(BYBIT_API_SECRET, order_params)

    # 📡 Enviar requisição para a Testnet da Bybit
    url = f"{BYBIT_BASE_URL}/v2/private/order/create"
    response = requests.post(url, data=order_params)

    return response.json()

# 🚀 Executar o servidor
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
