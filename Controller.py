import threading
from concurrent import futures
import queue
import aux
import time
import sys
import json
import random

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


    def on_connect(self, client, userdata, flags, rc):
        print(f"Client {self.id} conectado ao broker MQTT")
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

            if len(self.acc_list) == self.min_clients:
                acc_global = sum(self.acc_list)/len(self.acc_list)
                print(f"Round: {self.round} / Accuracy Mean: {acc_global}")

                if acc_global >= self.acc_target:
                    print("Accuracy Target has been achieved! Ending process")
                    self.mqtt_client.publish("sd/FinishMsg")
                    sys.exit()

                self.__preperNewRound()        
                
    def __preperNewRound(self):
        self.round += 1
        self.sample_size_list = []
        self.weights_clients_list = []
        self.acc_list = []
        self.move_round = True

    # Inicia treinamento de determinado clientes
    def __callClientLearning(self, client_ip, q):
        channel = grpc.insecure_channel(client_ip)
        client = fed_grpc_pb2_grpc.FederatedServiceStub(channel)

        weight_list = client.startLearning(fed_grpc_pb2.void()).weight
        sample_size = client.getSampleSize(fed_grpc_pb2.void()).size

        q.put([weight_list, sample_size])

    # Teste para nova lista de pesos global
    def __callModelValidation(self, aggregated_weights):
        acc_list = []
        for cid in self.clients:
            channel = grpc.insecure_channel(self.clients[cid])

            client = fed_grpc_pb2_grpc.FederatedServiceStub(channel)
            acc_list.append(client.modelValidation(fed_grpc_pb2.weightList(weight = (aggregated_weights))).acc)

        return acc_list
    
    # Calcula a média ponderada dos pesos resultantes do treino
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
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_connect = self.on_connect

        self.mqtt_client.connect(self.broker_adress)
        self.mqtt_client.loop_start()


        while self.round < self.max_rounds:
            choosem_clients = random.sample(clients_list, self.n_round_clients)
            ## gera lista de escolhidos
            # publica lista de clients esclhidos

            while self.move_round == False:
                continue

            self.move_round = False



            # #Verificando se o mínimo de clientes foi estabelecido
            # if len(self.clients) < min_clients:
            #     print("Waiting for the minimum number of clients to connect...")
            #     while len(self.clients) < min_clients:
            #         continue

            #     print("The minimum number of clients has been reached.")
            
            # # Sincronização para admitir a entrada de novos clientes após início do server
            # self.avalable_for_register = True
            # time.sleep(0.5)

            # self.round += 1
            # self.avalable_for_register = False
            # self.__sendRound()

            # # Criando lista de clientes alvo
            # cid_targets = aux.createRandomClientList(self.clients, n_round_clients)

            # # Inicializando chamada de aprendizado para os clients
            # thread_list = []
            # q = queue.Queue()
            # for i in range(n_round_clients):
            #     thread = threading.Thread(target=self.__callClientLearning, args=(self.clients[cid_targets[i]], q))
            #     thread_list.append(thread)
            #     thread.start()
            # for thread in thread_list:
            #     thread.join()

            # # Capturando lista de pesos resultantes do treinamento
            # weights_clients_list = []
            # sample_size_list = []
            # while not q.empty():
            #     thread_results = q.get()

            #     weights_clients_list.append(thread_results[0])
            #     sample_size_list.append(thread_results[1])

            # # Agregando lista de pesos
            # aggregated_weights = self.__FedAvg(n_round_clients, weights_clients_list, sample_size_list)

            # # Validando o modelo global
            # acc_list = self.__callModelValidation(aggregated_weights)
    
            # acc_global = sum(acc_list)/len(acc_list)
            # print(f"Round: {self.round} / Accuracy Mean: {acc_global}")
            # if acc_global >= acc_target:
            #     print("Accuracy Target has been achieved! Ending process")
            #     break

# if __name__ == "__main__":
#     try:
#         n_round_clients = int(sys.argv[1])
#         min_clients = int(sys.argv[2])
#         max_rounds = int(sys.argv[3])
#         acc_target = float(sys.argv[4])

#     except IndexError:
#         print("Missing argument! You need to pass: (clientsRound, minClients, maxRounds, accuracyTarget)")
#         exit()

#     fed_server = FedServer()

#     #creating grpc server at ip [::]:8080
#     grpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
#     fed_grpc_pb2_grpc.add_FederatedServiceServicer_to_server(fed_server, grpc_server)
#     grpc_server.add_insecure_port('[::]:8080')
#     grpc_server.start()

#     fed_server.startServer(n_round_clients, min_clients, max_rounds, acc_target)
#     fed_server.killClients()