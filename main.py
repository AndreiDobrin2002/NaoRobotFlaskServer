# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
import naoqi
from naoqi import ALProxy
import json
import requests

app = Flask(__name__)

# Config NAO
NAO_IP = "192.168.0.1"  # modifică cu IP-ul real dacă e pe alt dispozitiv
NAO_PORT = 9559

tts = ALProxy("ALTextToSpeech", NAO_IP, NAO_PORT)
# Endpoint LM Studio
LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"
HEADERS = {"Content-Type": "application/json"}

# Endpoint pentru a pune o întrebare
@app.route('/ask', methods=['POST'])
def ask_nao():
    try:
        data = request.get_json()
        question = data.get("question", "")

        if not question:
            return jsonify({"error": "No question provided"}), 400

        # Construim payload-ul pentru LM Studio
        payload = {
            "messages": [
                {"role": "user", "content": question}
            ],
            "temperature": 0.7,
            "max_tokens": 512
        }

        # Trimitem cererea către LM Studio
        response = requests.post(LM_STUDIO_URL, headers=HEADERS, data=json.dumps(payload))
        if response.status_code != 200:
            return jsonify({"error": "LLM request failed"}), 500

        result = response.json()
        full_answer = result["choices"][0]["message"]["content"]

        # Extrage doar ce e după </think>
        if "</think>" in full_answer:
            answer = full_answer.split("</think>", 1)[1].strip()
        else:
            answer = full_answer.strip()

        # NAO rostește răspunsul
        tts.say(answer.encode('utf-8'))

        return jsonify({"answer": answer})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
