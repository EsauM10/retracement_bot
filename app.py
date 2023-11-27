from typing import Any
import webbrowser

from flask import Flask, jsonify, render_template, request, redirect
from flask_socketio import SocketIO

from api.repository import Repository
from api.services.bot import BotHandler
from api.services.events import FrontendChannels

app = Flask(__name__)
socketio    = SocketIO(app)
repository  = Repository()
frontend    = FrontendChannels(socketio)
bot_handler = BotHandler(frontend, repository)


@app.route('/', methods=['GET'])
def index():
    if(bot_handler.is_connected):
        return redirect('/dashboard/home')
    return redirect('/login')


@app.route('/login', methods=['GET'])
def login_page():
    if(bot_handler.is_connected):
        return redirect('/dashboard/home') 
    return render_template('login/login.html')


@app.route('/login', methods=['POST'])
def handle_login():
    try:
        json  = request.get_json()
        email = str(json['email'])
        password = str(json['password'])
        bot_handler.connect(email, password)
        return jsonify({'content': 'Logged In'}), 200

    except Exception as ex:
        return jsonify({'error': f'{ex}'}), 500


@app.route('/dashboard/home', methods=['GET'])
def home_page():
    if(not bot_handler.is_connected):
        return redirect('/login')
    return render_template('dashboard/home.html')


@app.route('/dashboard/settings', methods=['GET'])
def settings_page():
    return render_template('dashboard/settings.html')

# ================================== Events ================================== #
@socketio.on('alerts')
def handle_alerts(data: dict[str, Any]):
    method = str(data['method'])
    payload: dict[str, Any] = data['payload']

    if(method == 'POST'):
        asset_name = str(payload['asset_name'])
        price = float(payload['price'])
        alert = repository.create_alert(asset_name, price)
        frontend.add_alert(alert)
    elif(method == 'DELETE'):
        alert_id = int(payload['alert_id'])
        repository.delete_alert(alert_id)
        frontend.delete_alert(alert_id)


@socketio.on('updateData')
@bot_handler.login_required
def get_data(): 
    open_assets = []
    try:
        open_assets = bot_handler.exchange.get_open_assets()
    except Exception as ex:
        print(ex)
    else:
        account_balance = bot_handler.exchange.balance()
        repository.create_assets(open_assets)
        
        if(repository.selected_asset == ''):
            repository.selected_asset = open_assets[0]

        asset = repository.get_asset_by_name(repository.selected_asset)
        asset.price = bot_handler.exchange.get_current_price(asset.name)

        frontend.update_open_assets(asset.name, open_assets)
        frontend.update_account_balance(account_balance)
        frontend.update_transactions(repository.transactions)
        frontend.update_asset_data(asset)
        frontend.update_asset_alerts(asset)


@socketio.on('updateSelectedAsset')
def update_selected_asset(asset_name: str):
    asset = repository.get_asset_by_name(asset_name)
    asset.price = bot_handler.exchange.get_current_price(asset.name)
    frontend.update_asset_data(asset)
    frontend.update_asset_alerts(asset)


@socketio.on('startBot')
def start_bot(asset_name: str):
    bot_handler.start(asset_name)


@socketio.on('stopBot')
def stop_bot():
    bot_handler.stop()
    

# ============================================================================ #
if(__name__ == '__main__'):
    debug = True
    
    if(not debug):
        webbrowser.open('http://localhost:5000')
    
    socketio.run(app, debug=debug, use_reloader=debug, log_output=True)

'''
tradinbot:
- Criar um logger para dar a opção de desativar as mensagens de log ou redirecionar o output
- Modificar as mensagens de log: parar de printar uma linha em branco

iqoption_bot:
- Mover a lógica dos channels handle_alerts, get_data e update_selected_asset para a class BotHandler
- Substituir o logger do TradinBot para permitir a redirecionamento dos logs do bot para a interface 
- Implementar a lógica da rota setting_page para permitir configurar o TradingSetup
'''