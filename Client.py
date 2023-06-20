import random
import json
import time
import paho.mqtt.client as mqtt
from sklearn.model_selection import train_test_split
from keras.utils import to_categorical
from Controller import FedServer
from FedClient import FedClient
import sys
import aux

class Client():
    def __init__(self, id, broker_adress, min_clients):
        self.id = id
        self.min_clients = min_clients
        self.clients_list = []
        self.clients_list.append(self.id)

        self.vote_table = {}
        self.controller_id = -1 
        
        self.mqtt_client = mqtt.Client(str(self.id))
        self.broker_adress = broker_adress

    def on_connect(self, client, userdata, flags, rc):
        print(f"Client {self.id} conectado ao broker MQTT")
        self.mqtt_client.subscribe("sd/init")
        self.mqtt_client.subscribe("sd/voting")
    
    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        data = json.loads(payload)
        client_id = data['ClientID']

        if topic == "sd/init" and client_id != self.id:
            self.clients_list.append(int(data['ClientID']))
            if self.min_clients == len(self.clients_list):
                self.__vote()

        elif topic == "sd/voting":
            self.vote_table[client_id] = data['VoteID']

            if self.min_clients == len(self.vote_table):
                self.__countVote()

    def __vote(self):
        vote = random.randint(0, len(self.clients_list)-1)
        vote_msg = {
            'ClientID': self.id,
            'VoteID': self.clients_list[vote]
        }
        self.mqtt_client.publish("sd/voting", json.dumps(vote_msg))

    def __countVote(self):
        vote_counter = {}

        for client_id in self.vote_table:
            if self.vote_table[client_id] not in vote_counter:
                vote_counter[self.vote_table[client_id]] = 1
            else:
                vote_counter[self.vote_table[client_id]] += 1

        winner_votes = -1
        winner_id = -1
        for client in vote_counter:
            if vote_counter[client] > winner_votes:
                winner_votes = vote_counter[client]
                winner_id = client
            elif vote_counter[client] == winner_votes:
                if client > winner_id:
                    winner_id = client

        self.controller_id = winner_id
        print(f"Tabela de votos do client {self.id}: {self.vote_table} // Vencedor: {self.controller_id}")

    def runClient(self, n_round_clients, max_rounds, acc_target):
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_connect = self.on_connect

        self.mqtt_client.connect(self.broker_adress)
        self.mqtt_client.loop_start()

        #esperando para que todos assinem as funções
        time.sleep(5)
        self.mqtt_client.publish("sd/init", json.dumps({"ClientID": self.id}))

        #esperando resultado da eleição
        while self.controller_id == -1:
            continue

        if self.id == self.controller_id:
            self.startController(n_round_clients, max_rounds, acc_target)
        else:
            self.startFedClient(max_rounds)

    def startController(self, n_round_clients, max_rounds, acc_target):
        fed_server = FedServer(self.mqtt_client, n_round_clients, 
                                    self.min_clients, max_rounds, acc_target, 
                                        self.broker_adress)
        self.clients_list.remove(self.id)
        fed_server.startServer(self.clients_list)

    def startFedClient(self, max_rounds):
        input_shape = (28, 28, 1)
        num_classes = 10

        # Carregando e dividindo dataSet
        x_train, y_train = aux.load_mnist_byCid(self.id)
        x_train, x_test, y_train, y_test = train_test_split(x_train, y_train, test_size=0.2, random_state=42)

        # One-hot encode labels
        y_train = to_categorical(y_train, num_classes)
        y_test = to_categorical(y_test, num_classes)

        model = aux.define_model(input_shape,num_classes)

        fed_client = FedClient(self.id, x_train, x_test, 
                                y_train, y_test, model, self.broker_adress, 
                                    self.mqtt_client)
        fed_client.runClient(max_rounds)

if __name__ == "__main__":
    try:
        n_round_clients = int(sys.argv[1])
        min_clients = int(sys.argv[2])
        max_rounds = int(sys.argv[3])
        acc_target = float(sys.argv[4])
        id = int(sys.argv[5])

    except IndexError:
        print("Missing argument! You need to pass: n_round_clients/min_clients/max_rounds/acc_target/clientId")
        exit()

    broker_adress = "localhost"
    client = Client(id= id, broker_adress=broker_adress, min_clients=min_clients)
    client.runClient(n_round_clients,max_rounds,acc_target)

