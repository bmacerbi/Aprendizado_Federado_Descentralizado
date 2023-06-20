import aux
import json
import sys


class FedClient():
    def __init__(self, cid, x_train, x_test, y_train, y_test, model, broker_adress, mqtt_client):
        self.round = 0
        self.cid = cid
        self.x_train = x_train
        self.x_test = x_test
        self.y_train = y_train
        self.y_test = y_test
        self.model = model
        self.broker_adress = broker_adress
        self.mqtt_client = mqtt_client
    
    def on_connect(self, client, userdata, flags, rc):
        print(f"FedClient conectado ao broker MQTT")
        self.mqtt_client.subscribe("sd/TrainingMsg")
        self.mqtt_client.subscribe("sd/AggregationMsg")
        self.mqtt_client.subscribe("sd/FinishMsg")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        data = json.loads(payload)

        if topic == "sd/TrainingMsg":
            choose_clients = data['chooseIds']
            if self.cid in choose_clients:
                self.startLearning()
        elif topic == "sd/AggregationMsg":
            global_weights = data['global_weights']
            self.modelValidation(global_weights)
        elif topic == "sd/FinishMsg":
            print("Accuracy target has been achieved!")
            self.round = sys.maxsize

    def startLearning(self):
        print(f"Round: {self.round} / Start Learning")
        self.model.fit(self.x_train, self.y_train, epochs=1, verbose=2)

        weights_list = aux.setWeightSingleList(self.model.get_weights())
        learning_results = {
            'weights': weights_list,
            'sample' : len(self.x_train)
        }
        self.mqtt_client.publish("sd/RoundMsg", json.dumps(learning_results))


    def modelValidation(self, global_weights):
        self.model.set_weights(aux.reshapeWeight(global_weights, self.model.get_weights()))
        accuracy = self.model.evaluate(self.x_test, self.y_test, verbose=0)[1]

        print(f"Round: {self.round} / Local accuracy with global weights: {accuracy}\n")

        self.round += 1
        
        accuracy_msg = {
            'accuracy': accuracy,
        }
        self.mqtt_client.publish("sd/EvaluationMsg", json.dumps(accuracy_msg))


    def runClient(self, max_rounds):
        print("\n----------------------------------------------------------\n")
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_connect = self.on_connect

        self.mqtt_client.connect(self.broker_adress)

        while self.round < max_rounds:
            continue
