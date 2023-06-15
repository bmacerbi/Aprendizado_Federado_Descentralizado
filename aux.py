from imutils import paths
import numpy as np
import os
import cv2
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPool2D,Flatten,Dense
from tensorflow.keras.optimizers import SGD
from keras.utils import to_categorical
import random

def load_mnist_byCid(cid):
    data = []
    labels = []

    path = f"mnist_data/client_{cid}"
    img_paths = list(paths.list_images(path))

    for (i, imgpath) in enumerate(img_paths):
        # load the image and extract the class labels
        img_grayscale = cv2.imread(imgpath, cv2.IMREAD_GRAYSCALE)

        #reshape in 3D array and normalize
        img = np.expand_dims(img_grayscale, axis=-1) / 255.0

        #get label from img name based on the folder
        label = imgpath.split(os.path.sep)[-2]

        # append to data and labels lists
        data.append(img)
        labels.append(label)

    return np.array(data), np.array(labels)

def define_model(input_shape,num_classes):
    model = Sequential()
    model.add(Conv2D(32, (3, 3), activation='relu', kernel_initializer='he_uniform', input_shape=input_shape))
    model.add(MaxPool2D((2, 2)))
    model.add(Flatten())
    model.add(Dense(100, activation='relu', kernel_initializer='he_uniform'))
    model.add(Dense(num_classes, activation='softmax'))
    # compile model
    opt = SGD(learning_rate=0.01, momentum=0.9)
    model.compile(optimizer=opt, loss='categorical_crossentropy', metrics=['accuracy'])
    
    return model

def setWeightSingleList(weights):
    # Flatten each array of weights into a 1D list of floats
    weights_flat = [w.flatten() for w in weights]

    # Concatenate all of the weight lists into a single list
    weights = np.concatenate(weights_flat).tolist()

    return weights

def reshapeWeight(server_weight, client_weight):
    reshape_weight = []

    # iterate through the weights in the model and reshape the corresponding sublist of the concatenated weight list
    for layer_weights in client_weight:
        n_weights = np.prod(layer_weights.shape)
        reshape_weight.append(np.array(server_weight[:n_weights]).reshape(layer_weights.shape))
        server_weight = server_weight[n_weights:]

    return reshape_weight

def createRandomClientList(clients_dictionary, n_round_clients):
    keys = list(clients_dictionary.keys())
    return random.sample(keys, n_round_clients)