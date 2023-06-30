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
    def __init__(self, id, broker_address, min_clients):
        self.id = id
        self.min_clients = min_clients
        self.clients_list = []
        self.clients_list.append(self.id)

        self.vote_table = {}
        self.controller_id = -1 
        
        self.mqtt_client = mqtt.Client(str(self.id))
        self.broker_address = broker_address

    def on_connect(self, client, userdata, flags, rc):
        print(f"Client {self.id} conected with MQTT broker")
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
            self.vote_table[client_id] = data['Vote']

            if self.min_clients == len(self.vote_table):
                self.__countVote()

    def __vote(self):
        vote_msg = {
            'ClientID': self.id,
            'Vote': random.randint(0, 65335)
        }
        self.mqtt_client.publish("sd/voting", json.dumps(vote_msg))

    def __countVote(self):
        winner_vote = -1
        winner_id = -1
        for client in self.vote_table:
            if self.vote_table[client] > winner_vote:
                winner_id = client
                winner_vote = self.vote_table[client]

        self.controller_id = winner_id
        print(f"Vote table for client {self.id}: {self.vote_table} // Winner: {self.controller_id}")

    def runClient(self, n_round_clients, max_rounds, acc_target):
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_connect = self.on_connect

        self.mqtt_client.connect(self.broker_address)
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
                                        self.broker_address)
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
                                y_train, y_test, model, self.broker_address, 
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

    broker_address = "localhost"
    client = Client(id= id, broker_address=broker_address, min_clients=min_clients)
    client.runClient(n_round_clients,max_rounds,acc_target)

