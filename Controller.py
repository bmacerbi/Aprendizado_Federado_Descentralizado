import time
import json
import random
import numpy as np

class FedServer():
    def __init__(self, mqtt_client, n_round_clients, min_clients, max_rounds, acc_target, broker_adress):
        self.mqtt_client = mqtt_client
        self.round = 0
        self.n_round_clients = n_round_clients
        self.min_clients = min_clients
        self.max_rounds = max_rounds
        self.acc_target = acc_target
        self.broker_adress = broker_adress

        self.weights_clients_list = []
        self.sample_size_list = []
        self.acc_list = []
        self.move_round = False
        self.weights_clients_dict = {}


    def on_connect(self, client, userdata, flags, rc):
        print(f"Controller conectado ao broker MQTT")
        self.mqtt_client.subscribe("sd/RoundMsg")
        self.mqtt_client.subscribe("sd/EvaluationMsg")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        data = json.loads(payload)

        if topic == "sd/RoundMsg":
            cid = data['cid']
            msg_id = data['msgId']
            self.weights_clients_dict.setdefault(cid, []).append({'weights': data['weights'], 
                                                                    'sample': data['sample'],
                                                                        'id': msg_id})

            if len(self.weights_clients_dict) == self.n_round_clients:
                for cid in self.weights_clients_dict:
                    if len(self.weights_clients_dict[cid]) != 1000:
                        return
                    
                for cid in self.weights_clients_dict:
                    weights = []
                    sample = None
                    for msg in self.weights_clients_dict[cid]:
                        for number in msg['weights']:
                            weights.append(number)
                        sample = msg['sample']

                    self.weights_clients_list.append(weights)
                    self.sample_size_list.append(sample)
                global_weights = self.__FedAvg()
                weights_sections = np.array_split(global_weights, 1000)
                i = 0
                for weight in weights_sections:
                    msg = {
                        'global_weights': weight.tolist(),
                        'msgId': i
                    }
                    self.mqtt_client.publish("sd/AggregationMsg", json.dumps(msg))
                    i+=1

        elif topic == "sd/EvaluationMsg":
            self.acc_list.append(data['accuracy'])

            if len(self.acc_list) == self.min_clients - 1:
                acc_global = sum(self.acc_list)/len(self.acc_list)
                print(f"Round: {self.round} / Accuracy Mean: {acc_global}\n")

                if acc_global >= self.acc_target:
                    print("Accuracy Target has been achieved! Ending process")
                    self.mqtt_client.publish("sd/FinishMsg", json.dumps({}))
                    self.round = self.max_rounds

                self.__preperNewRound()        
                
    def __preperNewRound(self):
        self.round += 1
        self.sample_size_list = []
        self.weights_clients_list = []
        self.acc_list = []
        self.move_round = True
        self.weights_clients_dict = {}
    
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

        self.mqtt_client.connect(self.broker_adress)
        time.sleep(3)
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