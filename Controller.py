import threading
from concurrent import futures
import queue
import aux
import time
import sys
import json
import random

class FedServer():
    def __init__(self, mqtt_client, n_round_clients, min_clients, max_rounds, acc_target, broker_address):
        self.mqtt_client = mqtt_client
        self.round = 0
        self.n_round_clients = n_round_clients
        self.min_clients = min_clients
        self.max_rounds = max_rounds
        self.acc_target = acc_target
        self.broker_address = broker_address

        self.weights_clients_list = []
        self.sample_size_list = []
        self.acc_list = []
        self.move_round = False


    def on_connect(self, client, userdata, flags, rc):
        print(f"Controller connected with MQTT broker")
        self.mqtt_client.subscribe("sd/RoundMsg")
        self.mqtt_client.subscribe("sd/EvaluationMsg")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        data = json.loads(payload)

        if topic == "sd/RoundMsg":
            self.weights_clients_list.append(data['weights'])
            self.sample_size_list.append(data['sample'])

            if len(self.weights_clients_list) == self.n_round_clients:
                global_weights = self.__FedAvg()

                ##publica global_weights
                global_weights_msg = {
                    'global_weights': global_weights,
                }   
                self.mqtt_client.publish("sd/AggregationMsg", json.dumps(global_weights_msg))

        elif topic == "sd/EvaluationMsg":
            self.acc_list.append(data['accuracy'])

            if len(self.acc_list) == self.min_clients - 1:
                acc_global = sum(self.acc_list)/len(self.acc_list)
                print(f"Round: {self.round} / Accuracy Mean: {acc_global}\n")

                if acc_global >= self.acc_target:
                    print("Accuracy Target has been achieved! Ending process")
                    self.mqtt_client.publish("sd/FinishMsg", json.dumps({}))
                    self.round = self.max_rounds

                self.__prepareNewRound()        
                
    def __prepareNewRound(self):
        self.round += 1
        self.sample_size_list = []
        self.weights_clients_list = []
        self.acc_list = []
        self.move_round = True
    
    def __FedAvg(self):
        aggregated_weights = []
        for j in range(len(self.weights_clients_list[0])):
            element = 0.0
            sample_sum = 0.0
            for i in range(self.n_round_clients):
                sample_sum += self.sample_size_list[i]
                element += self.weights_clients_list[i][j] * self.sample_size_list[i]
            aggregated_weights.append(element/sample_sum)  
        
        return aggregated_weights
    
    def startServer(self, clients_list):
        print("\n----------------------------------------------------------\n")
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_connect = self.on_connect

        self.mqtt_client.connect(self.broker_address)
        time.sleep(5)
        while self.round < self.max_rounds:
            choose_clients = random.sample(clients_list, self.n_round_clients)
            choose_clients_msg = {
                'chooseIds': choose_clients
            }
            print(f"Round: {self.round} / Call Training")
            self.mqtt_client.publish("sd/TrainingMsg", json.dumps(choose_clients_msg))

            while self.move_round == False:
                continue

            self.move_round = False