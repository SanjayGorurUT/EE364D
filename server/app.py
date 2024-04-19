from flask import Flask, render_template, jsonify, request
from typing import List, Tuple
import json
from flwr.common import Metrics
from flask_cors import CORS
import wandb
import numpy as np
import subprocess
import os

app = Flask(__name__)
CORS(app)

METRICS_FILE = "metrics.json"

# Load initial metrics from the file
try:
    with open(METRICS_FILE, "r") as file:
        metricList = json.load(file)
except FileNotFoundError:
    metricList = []

@app.route("/")
def index():
    return render_template("index.html")

# Define metric aggregation function
def weighted_average(metrics: List[Tuple[int, Metrics]]) -> Metrics:
    # Multiply accuracy of each client by the number of examples used
    #print(metrics)
    accuracies = [num_examples * m["accuracy"] for num_examples, m in metrics]
    losses = [num_examples * m["loss"] for num_examples, m in metrics]
    models = [num_examples * m["model"] for num_examples, m in metrics]
    examples = [num_examples for num_examples, _ in metrics]
    
    model = ""
    if "CNN" in models[0]:
        model = "CNN"
    else:
        model = "ResNet"
    
    # Aggregate and return custom metric (weighted average)
    metric = {"accuracy": sum(accuracies) / sum(examples), "loss": sum(losses) / sum(examples), "model": model}
    print(metric)
    wandb.log(metric)
    metricList.append(metric)
    
    # Save the updated metrics to the file
    with open(METRICS_FILE, "w") as file:
        json.dump(metricList, file)
    
    return metricList[-1]  # Return the latest metric as a dictionary

@app.route('/start-experiment', methods=['POST'])
def start_experiment():
    if os.path.exists(METRICS_FILE):
        os.remove(METRICS_FILE)
    
    data = request.json
    print(data)
    model = data.get('model')
    num = data.get('num')
    subprocess.Popen(['python3', 'server.py'])

    if num == 0:
        subprocess.Popen(['python3', '../client/client.py', '--node-id', '0', '--has_parent', '0', '--model', model])
        subprocess.Popen(['python3', '../client/client.py', '--node-id', '0', '--has_parent', '0', '--model', model])

    elif num == 1:
        subprocess.Popen(['python3', '../client/dual_client.py', '--node-id', '0', '--num_clients', '1', '--port', '81'])
        subprocess.Popen(['python3', '../client/client.py', '--node-id', '1', '--has_parent', '0', '--model', model])
        subprocess.Popen(['python3', '../client/client.py', '--node-id', '2', '--parent_ip', '127.0.0.1', '--parent_port', '81', '--has_parent', '1','--model', model])
    
    return 'Experiment started successfully'

@app.route('/metrics', methods=['GET'])
def get_metrics():
    try:
        with open(METRICS_FILE, "r") as file:
            metricList = json.load(file)
    except FileNotFoundError:
        metricList = []
    return metricList


if __name__ == "__main__":
    app.run(debug=True, port=80)