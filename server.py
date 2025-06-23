# -*- coding: utf-8 -*-
import qi
from naoqi import ALProxy
import numpy as np
import cv2
import threading
import time
from flask import Flask, request, jsonify, Response, send_file, send_from_directory
import os
from werkzeug.utils import secure_filename
import paramiko  # Pentru transferul fișierelor către robot
import pygame
import requests
import json
from flask_cors import CORS
import webbrowser


NAO_IP = "192.168.0.1"  # Adresa IP a robotului
NAO_PORT = 9559         # Portul NAOqi (în mod normal 9559)
ROBOT_USERNAME = "nao"
ROBOT_PASSWORD = "nao"  # Setează parola corectă
ROBOT_AUDIO_PATH = "/home/nao/audio/"  # Director unde salvăm fișierele pe robot

# Inițializăm Flask
app = Flask(__name__, static_folder='build')
CORS(app)  # ✅ Activează accesul din React

# Configurăm sesiunea cu robotul
try:
    session = qi.Session()
    session.connect("tcp://{}:{}".format(NAO_IP, NAO_PORT))
    print("Conexiune reușită la robot!")
except Exception as e:
    print("Eroare conexiune: {}".format(e))
    session = None


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')


# Creează proxy pentru modul audio al robotului
audio_proxy = ALProxy("ALAudioDevice", NAO_IP, NAO_PORT)

@app.route('/set_volume', methods=['POST'])
def set_volume():
    try:
        # Obține volumul din corpul cererii
        data = request.json
        if 'volume' in data:
            volume = data['volume']

            # Asigură-te că volumul este în intervalul 0-100
            if 0 <= volume <= 100:
                # Setează volumul robotului
                audio_proxy.setOutputVolume(volume)
                return jsonify({"message": "Volumul robotului a fost setat la {volume}%"}), 200
            else:
                return jsonify({"error": "Volumul trebuie să fie între 0 și 100"}), 400
        else:
            return jsonify({"error": "Parametru 'volume' lipsă"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/get_volume', methods=['GET'])
def get_volume():
    try:
        current_volume = audio_proxy.getOutputVolume()
        return jsonify({"volume": current_volume}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/move", methods=["POST"])
def move():
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    posture_service = session.service("ALRobotPosture")
    posture_service.goToPosture("Stand", 1.0)

    data = request.get_json()

    if not data:
        return jsonify({"error": "Datele JSON nu au fost trimise corespunzător"}), 400

    direction = data.get("direction")
    distance = data.get("distance", 0.2)

    try:
        motion_service = session.service("ALMotion")
        if direction == "forward":
            motion_service.moveTo(distance, 0, 0)
        elif direction == "backward":
            motion_service.moveTo(-distance, 0, 0)
        elif direction == "left":
            motion_service.moveTo(0, distance, 0)
        elif direction == "right":
            motion_service.moveTo(0, -distance, 0)
        else:
            return jsonify({"error": "Direcție necunoscută"}), 400

        return jsonify({"status": "Mișcare completă"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/speak", methods=["POST"])
def speak():
    """
    Face robotul să rostească un mesaj.
    Parametri POST:
      - text: mesajul de rostit
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    data = request.get_json()

    if not data:
        return jsonify({"error": "Datele JSON nu au fost trimise corect"}), 400

    text = data.get("text", "")

    if not text:
        return jsonify({"error": "Mesajul nu poate fi gol"}), 400

    try:
        tts = session.service("ALTextToSpeech")
        tts.say(text)
        return jsonify({"status": "Mesaj rostit"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/battery", methods=["GET"])
def sensors():
    """
    Citește informațiile de la senzorii robotului.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        memory_service = session.service("ALMemory")
        battery = memory_service.getData("Device/SubDeviceList/Battery/Charge/Sensor/Value")

        return jsonify({
            "battery_level": battery
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/all_sensors", methods=["GET"])
def all_sensors():
    """
    Returnează starea tuturor senzorilor de pe robotul NAO.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        memory_service = session.service("ALMemory")

        # Lista senzorilor de interes
        sensors = {
            "battery": "Device/SubDeviceList/Battery/Charge/Sensor/Value",
            "touch_head_front": "Device/SubDeviceList/Head/Touch/Front/Sensor/Value",
            "touch_head_middle": "Device/SubDeviceList/Head/Touch/Middle/Sensor/Value",
            "touch_head_rear": "Device/SubDeviceList/Head/Touch/Rear/Sensor/Value",
            "left_hand_touch": "Device/SubDeviceList/LHand/Touch/Back/Sensor/Value",
            "right_hand_touch": "Device/SubDeviceList/RHand/Touch/Back/Sensor/Value",
            "left_foot_bumper": "Device/SubDeviceList/LFoot/Bumper/Left/Sensor/Value",
            "right_foot_bumper": "Device/SubDeviceList/RFoot/Bumper/Right/Sensor/Value",
            "sonar_left": "Device/SubDeviceList/US/Left/Sensor/Value",
            "sonar_right": "Device/SubDeviceList/US/Right/Sensor/Value"
        }

        sensor_data = {}
        for sensor_name, sensor_path in sensors.items():
            sensor_data[sensor_name] = memory_service.getData(sensor_path)

        return jsonify(sensor_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/stand_up", methods=["POST"])
def stand_up():
    """
    Face robotul să stea în picioare.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        posture_service = session.service("ALRobotPosture")
        posture_service.goToPosture("Stand", 1.0)
        return jsonify({"status": "Robotul stă în picioare"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/sit_down", methods=["POST"])
def sit_down():
    """
    Face robotul să stea în fund.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        posture_service = session.service("ALRobotPosture")
        posture_service.goToPosture("Sit", 1.0)
        return jsonify({"status": "Robotul stă în fund"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/rest", methods=["POST"])
def rest():
    """
    Face robotul să intre în modul de repaus.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        motion_service = session.service("ALMotion")
        motion_service.rest()
        return jsonify({"status": "Robotul este acum în repaus"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/wake_up", methods=["POST"])
def wake_up():
    """
    Face robotul să iasă din modul de repaus și să devină activ.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        motion_service = session.service("ALMotion")
        motion_service.wakeUp()
        return jsonify({"status": "Robotul este acum activ"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/hello", methods=["POST"])
def hello():
    """
    Face robotul să salute verbal și să fluture mâna deasupra capului.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        tts = session.service("ALTextToSpeech")
        posture_service = session.service("ALRobotPosture")
        posture_service.goToPosture("Stand", 1.0)

        behavior_manager = session.service("ALBehaviorManager")
        hello_behavior = 'animations/Stand/Emotions/Neutral/Hello_1'  # Numele comportamentului din Choregraphe
        if behavior_manager.isBehaviorInstalled(hello_behavior):
            if not behavior_manager.isBehaviorRunning(hello_behavior):
                behavior_manager.startBehavior(hello_behavior)
                tts.say("Hello! Nice to meet you!")
                return jsonify({"status": "Robotul salută"})
            else:
                return jsonify({"status": "Salutul este deja în execuție"})
        else:
            return jsonify({"error": "Comportamentul {hello_behavior} nu este instalat"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/scratch_head", methods=["POST"])
def wipe_forehead():
    """
    Face robotul să se scarpine in cap
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        behavior_manager = session.service("ALBehaviorManager")
        wipe_behavior = 'animations/Stand/Waiting/ScratchHead_1'  # Numele comportamentului din Choregraphe
        if behavior_manager.isBehaviorInstalled(wipe_behavior):
            if not behavior_manager.isBehaviorRunning(wipe_behavior):
                behavior_manager.startBehavior(wipe_behavior)
                return jsonify({"status": "Robotul se scarpină in cap"})
            else:
                return jsonify({"status": "Scărpinatul capului este deja în execuție "})
        else:
            return jsonify({"error": "Comportamentul {wipe_behavior} nu este instalat"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/headbang", methods=["POST"])
def clap():
    """
    Face robotul să dea din cap ca la rock.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        behavior_manager = session.service("ALBehaviorManager")
        clap_behavior = 'animations/Stand/Waiting/Headbang_1'  # Numele comportamentului din Choregraphe
        if behavior_manager.isBehaviorInstalled(clap_behavior):
            if not behavior_manager.isBehaviorRunning(clap_behavior):
                behavior_manager.startBehavior(clap_behavior)
                return jsonify({"status": "Robotul dă din cap rock"})
            else:
                return jsonify({"status": "Datul din cap este deja în execuție "})
        else:
            return jsonify({"error": "Comportamentul {clap_behavior} nu este instalat"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/stand_zero", methods=["POST"])
def stand_zero():
    """
    Face robotul să adopte poziția neutră 'Stand Zero'.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        posture_service = session.service("ALRobotPosture")

        # Trezirea robotului
        motion_service = session.service("ALMotion")
        motion_service.wakeUp()

        # Poziția Stand Zero
        success = posture_service.goToPosture("StandZero", 1.0)

        if success:
            return jsonify({"status": "Robotul este acum în poziția Stand Zero"})
        else:
            return jsonify({"error": "Eroare la adoptarea poziției Stand Zero"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/tai_chi", methods=["POST"])
def tai_chi():
    """
    Face robotul să execute mișcări de dans Tai Chi.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        behavior_manager = session.service("ALBehaviorManager")
        tai_chi_behavior = 'taichidance-29e0c1/behavior_1'  # Numele comportamentului din Choregraphe
        if behavior_manager.isBehaviorInstalled(tai_chi_behavior):
            if not behavior_manager.isBehaviorRunning(tai_chi_behavior):
                behavior_manager.startBehavior(tai_chi_behavior)
                return jsonify({"status": "Robotul dansează Tai Chi"})
            else:
                return jsonify({"status": "Tai Chi este deja în execuție"})
        else:
            return jsonify({"error": "Comportamentul {tai_chi_behavior} nu este instalat"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/set_eye_color", methods=["POST"])
def set_eye_color():
    """
    Schimbă culoarea ochilor robotului.
    Parametri POST:
      - color: Culoarea dorită în format HEX (#RRGGBB) sau nume standard (ex. "red").
      - eye: "left", "right" sau "both" (implicit).
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        data = request.json
        color = data.get("color", "").strip()
        eye = data.get("eye", "both").lower()

        # Verificăm dacă formatul HEX este valid (#RRGGBB)
        if color.startswith("#") and len(color) == 7:
            try:
                red = int(color[1:3], 16) / 255.0
                green = int(color[3:5], 16) / 255.0
                blue = int(color[5:7], 16) / 255.0
            except ValueError:
                return jsonify({"error": "Culoarea HEX este invalidă"}), 400
        # Verificăm dacă este un nume de culoare suportat
        elif color.lower() in COLOR_MAP:
            red, green, blue = COLOR_MAP[color.lower()]
        else:
            return jsonify({"error": "Culoarea nu este recunoscută"}), 400

        # Transformăm în format RGB pentru NAO
        rgb_value = int(red * 255) << 16 | int(green * 255) << 8 | int(blue * 255)

        # Selectăm ochiul/o ochii corespunzători
        leds_service = session.service("ALLeds")
        if eye == "left":
            leds_service.fadeRGB("LeftFaceLeds", rgb_value, 1.0)  # Ochiul stâng
        elif eye == "right":
            leds_service.fadeRGB("RightFaceLeds", rgb_value, 1.0)  # Ochiul drept
        elif eye == "both":
            leds_service.fadeRGB("FaceLeds", rgb_value, 1.0)  # Ambii ochi
        else:
            return jsonify({"error": "Valoare invalidă pentru 'eye'. Trebuie să fie 'left', 'right' sau 'both'."}), 400

        return jsonify({"status": "Culoarea ochilor {eye} a fost schimbată la {color}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Dicționar de culori comune
COLOR_MAP = {
    "red": (1.0, 0.0, 0.0),
    "green": (0.0, 1.0, 0.0),
    "blue": (0.0, 0.0, 1.0),
    "yellow": (1.0, 1.0, 0.0),
    "cyan": (0.0, 1.0, 1.0),
    "magenta": (1.0, 0.0, 1.0),
    "white": (1.0, 1.0, 1.0),
    "black": (0.0, 0.0, 0.0)  # LED-urile se sting
}


video_service = session.service("ALVideoDevice")
for client in video_service.getSubscribers():
    video_service.unsubscribe(client)


@app.route("/stream_camera", methods=["GET"])
def stream_camera():
    """
    Stream live video de la camera robotului NAO.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        video_service = session.service("ALVideoDevice")

        # Setăm parametrii camerei
        resolution = 1  # 640x480 (VGA)
        color_space = 13  # BGR (recomandat pentru OpenCV)
        fps = 30
        client_name = video_service.subscribe("flask_camera", resolution, color_space, fps)

        def generate():
            while True:
                image = video_service.getImageRemote(client_name)
                if image is None:
                    print("Eroare: Nu am primit imagine de la camera.")
                    break

                try:
                    width = image[0]
                    height = image[1]
                    array = image[6]  # Datele imaginii brute

                    if array is None:
                        print("Eroare: Datele imaginii sunt None.")
                        continue

                    frame = np.frombuffer(array, dtype=np.uint8).reshape((height, width, 3))

                    # Convertim imaginea în format JPEG
                    _, jpeg = cv2.imencode('.jpg', frame)
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')

                except Exception as e:
                    print("Eroare la procesarea imaginii: {}".format(e))
                    break

        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

    except Exception as e:
        print("Eroare la conectarea la camera: {}".format(e))
        return jsonify({"error": str(e)}), 500


@app.route("/bow", methods=["POST"])
def bow():
    """
    Face robotul să execute o plecăciune.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        motion_service = session.service("ALMotion")
        posture_service = session.service("ALRobotPosture")

        # Robotul se ridică în poziția inițială
        posture_service.goToPosture("StandInit", 0.5)

        # Mișcare de plecaciune: îndoirea bazinului
        names = [
            "LHipPitch", "RHipPitch",
            "LKneePitch", "RKneePitch",
            "LAnklePitch", "RAnklePitch"
        ]
        angles = [-1.2, -1.2, 0.0, 0.0, 0.2, 0.2]  # Unghiuri pentru fiecare articulație
        times = [2.0] * 6  # Timp de tranziție pentru toate articulațiile
        motion_service.angleInterpolation(names, angles, times, True)

        # Revine în poziția inițială
        posture_service.goToPosture("StandInit", 0.5)

        return jsonify({"status": "Robotul a făcut o plecaciune"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/squat", methods=["POST"])
def squat():
    """
    Face robotul să execute o genuflexiune.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        # Obținem serviciul ALMotion
        motion_service = session.service("ALMotion")
        posture_service = session.service("ALRobotPosture")

        # Citim numărul de repetări din parametrii POST
        data = request.json
        repetitions = data.get("repetitions", 1)

        # Validăm numărul de repetări
        if not isinstance(repetitions, int) or repetitions <= 0:
            return jsonify({"error": "Numărul de repetări trebuie să fie un număr pozitiv"}), 400

        # Robotul se ridică în poziția inițială
        posture_service.goToPosture("StandZero", 0.5)

        # Articulațiile implicate pentru a pune robotul în odihnă
        angles = {
            "RHipYawPitch": 0.1,
            "LHipYawPitch": -0.1,
            "RAnklePitch": -0.6,  # Flexia gleznei piciorului drept
            "LAnklePitch": -0.6, # Flexia gleznei piciorului stâng
            "RHipPitch": -1.1,  # Flexia șoldului drept
            "LHipPitch": -1.1,  # Flexia șoldului stâng
            "RKneePitch": 1.8,  # Genunchiul drept îndoit
            "LKneePitch": 1.8   # Genunchiul stâng îndoit
        }

        for _ in range(repetitions):
            # Realizăm mișcarea pentru a pune robotul în odihnă
            motion_service.angleInterpolation(angles.keys(), list(angles.values()), 1.5, True)

            # Revine în poziția inițială
            posture_service.goToPosture("StandZero", 0.5)
        if repetitions==1:
            return jsonify({"status": "Robotul a făcut o genuflexiune"}), 200
        else:
            return jsonify({"status": "Robotul a făcut "+ str(repetitions) + " genuflexiuni"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Variabilă globală pentru a controla rularea evitării obstacolelor
obstacle_avoidance_running = False

@app.route("/obstacle_avoidance", methods=["POST"])
def obstacle_avoidance():
    """
    Activează evitarea obstacolelor pentru robotul NAO.
    Robotul va merge înainte, detectând și ocolind obstacolele.
    """
    global obstacle_avoidance_running  # Accesăm variabila globală

    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    data = request.json
    action = data.get("action", "").lower()

    if action == "start":
        if obstacle_avoidance_running:
            return jsonify({"error": "Evitarea obstacolelor este deja activă"}), 400

        obstacle_avoidance_running = True

        def avoid_obstacles():
            global obstacle_avoidance_running  # Necesită această declarație pentru a modifica variabila globală
            try:
                # Obținem serviciile necesare
                motion_service = session.service("ALMotion")
                sonar_service = session.service("ALSonar")
                memory_service = session.service("ALMemory")
                posture_service = session.service("ALRobotPosture")

                # Robotul se ridică în poziția inițială
                posture_service.goToPosture("StandInit", 0.5)

                # Pornim sonar-ul pentru detectarea obstacolelor
                sonar_service.subscribe("SonarApp")
                print("Sonarul a fost activat.")

                # Setăm robotul în modul de mișcare autonomă
                motion_service.moveInit()

                # Viteza inițială a robotului
                speed = 0.3

                while obstacle_avoidance_running:
                    # Citim datele de la senzorii sonar
                    left_distance = memory_service.getData("Device/SubDeviceList/US/Left/Sensor/Value")
                    right_distance = memory_service.getData("Device/SubDeviceList/US/Right/Sensor/Value")

                    print("Distanța stânga: "+ str(left_distance) +" , Distanța dreapta: "+str(right_distance))

                    # Distanța minimă acceptabilă (în metri)
                    min_distance = 0.5

                    if left_distance < min_distance or right_distance < min_distance:
                        # Dacă un obstacol este detectat, ne oprim și ocolim
                        print("Obstacol detectat! Încercăm să evităm.")
                        motion_service.stopMove()

                        # Determinăm direcția de evitare
                        if left_distance < right_distance:
                            # Ocolim pe dreapta
                            motion_service.moveTo(0, -0.2, -0.6)
                        else:
                            # Ocolim pe stânga
                            motion_service.moveTo(0, 0.2, 0.6)
                    else:
                        # Continuăm să mergem înainte
                        motion_service.moveToward(speed, 0, 0)

                    time.sleep(0.1)  # Pauză între verificări

                # Oprim mișcarea și dezactivăm sonar-ul
                motion_service.stopMove()
                sonar_service.unsubscribe("SonarApp")
                print("Mișcarea a fost oprită.")

            except Exception as e:
                # Opriți mișcarea în cazul unei erori
                motion_service.stopMove()
                sonar_service.unsubscribe("SonarApp")
                print("Eroare la evitarea obstacolelor: {e}")
                obstacle_avoidance_running = False

        # Pornim evitarea obstacolelor într-un thread separat
        thread = threading.Thread(target=avoid_obstacles)
        thread.setDaemon(True)  # Setăm thread-ul ca daemon
        thread.start()

        return jsonify({"status": "Evitarea obstacolelor a fost pornită"}), 200

    elif action == "stop":
        if not obstacle_avoidance_running:
            return jsonify({"error": "Evitarea obstacolelor nu este activă"}), 400

        # Oprim evitarea obstacolelor
        obstacle_avoidance_running = False
        return jsonify({"status": "Evitarea obstacolelor a fost oprită"}), 200

    else:
        return jsonify({"error": "Parametru invalid. Folosiți 'start' sau 'stop'."}), 400


@app.route("/robot_pose", methods=["GET"])
def robot_pose():
    """
    Returnează pozițiile articulațiilor robotului NAO.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        # Obține serviciul ALMotion
        motion_service = session.service("ALMotion")

        # Listează articulațiile robotului
        joint_names = motion_service.getBodyNames("Body")

        # Obține pozițiile articulațiilor în coordonate spațiale (world coordinates)
        joint_positions = []
        for joint in joint_names:
            position = motion_service.getPosition(joint, 1, True)  # 1 = world frame
            joint_positions.append({
                "name": joint,
                "position": position[:3]  # X, Y, Z
            })

        return jsonify(joint_positions)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/robot_velocity", methods=["GET"])
def robot_velocity():
    """
    Returnează viteza actuală a robotului NAO.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        # Obține serviciul ALMotion
        motion_service = session.service("ALMotion")

        # Obține viteza actuală a robotului
        velocity = motion_service.getRobotVelocity()

        return jsonify({
            "linear_velocity": velocity[0],
            "angular_velocity": velocity[1]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Endpoint pentru încărcarea și redarea unui fișier audio
@app.route("/upload_and_play", methods=["POST"])
def upload_and_play():
    """
    Încărcă un fișier audio pe robot și îl redă.
    Trimite fișierul prin 'multipart/form-data' cu key-ul 'file'.
    """
    if "file" not in request.files:
        return jsonify({"error": "Fișierul nu a fost trimis"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "Numele fișierului nu este valid"}), 400

    # Salvăm temporar fișierul pe server
    filename = secure_filename(file.filename)
    temp_path = os.path.join("C:\\Users\\Andrei\\Desktop\\Proiect Licenta\\temp", filename)  # Creează un folder "temp"
    file.save(temp_path)

    # Transferăm fișierul pe robot
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(NAO_IP, username=ROBOT_USERNAME, password=ROBOT_PASSWORD)

        sftp = ssh.open_sftp()

        try:
            sftp.stat(ROBOT_AUDIO_PATH)  # Verifică dacă există directorul pe robot
        except IOError:
            sftp.mkdir(ROBOT_AUDIO_PATH)  # Dacă nu există, creează-l

        remote_path = os.path.join(ROBOT_AUDIO_PATH, filename)
        sftp.put(temp_path, remote_path)
        sftp.close()
        ssh.close()
    except Exception as e:
        return jsonify({"error": "Eroare la transferul fișierului: "+str(e)}), 500

    # Ștergem fișierul local
    os.remove(temp_path)

    # Redăm fișierul pe robot
    try:
        audio_player = session.service("ALAudioPlayer")
        audio_player.playFile(remote_path)
        return jsonify({"status": "Fișierul audio a fost redat"}), 200
    except Exception as e:
        return jsonify({"error": "Eroare la redare: {str(e)}"}), 500


@app.route("/stop_audio", methods=["POST"])
def stop_audio():
    """
    Oprește redarea tuturor fișierelor audio de pe robotul NAO.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        audio_player = session.service("ALAudioPlayer")
        audio_player.stopAll()
        return jsonify({"status": "Redarea audio a fost oprită"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/start_recording", methods=["POST"])
def start_recording():
    """
    Pornește înregistrarea audio pe robotul NAO.
    Fișierul va fi salvat pe robot la /home/nao/recorded_audio.wav.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        audio_recorder = session.service("ALAudioRecorder")
        audio_recorder.startMicrophonesRecording("/home/nao/recorded_audio.wav", "wav", 16000, [1, 0, 0, 0])
        return jsonify({"status": "Înregistrare audio pornită"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/stop_and_save_recording", methods=["POST"])
def stop_and_save_recording():
    """
    Oprește înregistrarea audio și salvează fișierul pe robot, apoi îl descarcă pe computer.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        audio_recorder = session.service("ALAudioRecorder")
        audio_recorder.stopMicrophonesRecording()

        # Calea fișierului audio pe robot
        robot_audio_file = "/home/nao/recorded_audio.wav"
        local_audio_file = "recorded_audio.wav"  # Unde îl salvezi pe computer

        # Conectează-te la robot prin SFTP
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(NAO_IP, username=ROBOT_USERNAME, password=ROBOT_PASSWORD)

        sftp = ssh.open_sftp()
        sftp.get(robot_audio_file, local_audio_file)  # Transferă fișierul pe computer
        sftp.close()
        ssh.close()

        return jsonify({"status": "Înregistrarea a fost salvată pe computer"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Conexiunea la Nao
motion_proxy = ALProxy("ALMotion", NAO_IP, NAO_PORT)
posture_proxy = ALProxy("ALRobotPosture", NAO_IP, NAO_PORT)

# Prag pentru a evita mișcări involuntare ale joystick-ului
DEAD_ZONE = 0.1


# Variabile globale pentru a controla rularea manuală
control_thread = None
is_controlling = False

# D-pad butoane
D_PAD_UP = 11
D_PAD_DOWN = 12
D_PAD_LEFT = 13
D_PAD_RIGHT = 14

# Funcție pentru a inițializa controller-ul
def init_controller():
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("Nu există controllere conectate!")
        exit()

    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print("Controller conectat: {joystick.get_name()}")
    return joystick

# Funcție pentru a apela cele patru endpointuri
def call_endpoint(direction):
    url_mapping = {
        "up": "http://127.0.0.1:5000/hello",
        "down": "http://127.0.0.1:5000/scratch_head",
        "left": "http://127.0.0.1:5000/tai_chi",
        "right": "http://127.0.0.1:5000/bow",
    }

    if direction in url_mapping:
        try:
            response = requests.post(url_mapping[direction])
            if response.status_code == 200:
                print("Apel la {direction} a fost realizat cu succes.")
            else:
                print("Eroare la apelul {direction}: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print("Eroare la apelul {direction}: {e}")

# Funcție pentru a controla robotul pe baza input-ului
def control_robot():
    joystick = init_controller()

    # Activează controlul motoriilor
    motion_proxy.wakeUp()
    posture_proxy.goToPosture("StandInit", 0.5)  # Poziție inițială

    try:
        while is_controlling:
            for event in pygame.event.get():
                # Citire axe joystick
                x_axis = joystick.get_axis(0)  # Stânga/Dreapta
                y_axis = joystick.get_axis(1)  # Față/Spate
                head_x_axis = joystick.get_axis(2)  # Joystick drept stânga/dreapta
                head_y_axis = joystick.get_axis(3)  # Joystick drept sus/jos

                # Aplică DEAD_ZONE pentru a evita zgomotul
                x_axis = x_axis if abs(x_axis) > DEAD_ZONE else 0
                y_axis = y_axis if abs(y_axis) > DEAD_ZONE else 0
                head_x_axis = head_x_axis if abs(head_x_axis) > DEAD_ZONE else 0
                head_y_axis = head_y_axis if abs(head_y_axis) > DEAD_ZONE else 0

                # Calcul viteză de mers în funcție de axa verticală
                forward_speed = -y_axis * 0.9  # Valoare negativă = mers înainte

                # Calcul viteză de rotație doar pe axa X
                turn_speed = -x_axis * 0.9  # Rotire stânga/dreapta

                # Control cap
                motion_proxy.setAngles("HeadYaw", -head_x_axis * 2.0, 0.1)  # Rotire cap stânga/dreapta
                motion_proxy.setAngles("HeadPitch", head_y_axis * 0.7, 0.1)  # Ridicare/coborâre cap

                # Aplică vitezele la robot
                motion_proxy.setWalkTargetVelocity(forward_speed, 0.0, turn_speed, 0.5)
                print("Forward speed: {forward_speed}, Turn speed: {turn_speed}, HeadYaw: {head_x_axis}, HeadPitch: {head_y_axis}")

                # Apăsare butoane
                if event.type == pygame.JOYBUTTONDOWN:
                    if event.button == 0:  # Butonul X
                        motion_proxy.rest()  # Robotul intră în repaus
                    elif event.button == 1:  # Butonul O
                        posture_proxy.goToPosture("StandInit", 0.5)
                    elif event.button == 2:  # Butonul pătrat
                        posture_proxy.goToPosture("Sit", 0.5)
                    elif event.button == 3:  # Butonul triunghi
                        posture_proxy.goToPosture("StandZero", 0.5)

                    if event.button == D_PAD_UP:
                        call_endpoint("up")
                    elif event.button == D_PAD_DOWN:
                        call_endpoint("down")
                    elif event.button == D_PAD_LEFT:
                        call_endpoint("left")
                    elif event.button == D_PAD_RIGHT:
                        call_endpoint("right")

    except KeyboardInterrupt:
        print("Controlul robotului oprit.")
        motion_proxy.rest()  # Oprește robotul în siguranță
    finally:
        pygame.quit()

# Endpoint pentru a începe controlul manual
@app.route("/manual_control/start", methods=["POST"])
def start_manual_control():
    global control_thread, is_controlling

    if is_controlling:
        return jsonify({"error": "Controlul manual este deja activ"}), 400

    # Setăm flag-ul pentru control
    is_controlling = True
    control_thread = threading.Thread(target=control_robot)
    control_thread.start()

    return jsonify({"message": "Control manual a fost pornit"}), 200


# Endpoint pentru a opri controlul manual
@app.route("/manual_control/stop", methods=["POST"])
def stop_manual_control():
    global is_controlling, control_thread

    if not is_controlling:
        return jsonify({"error": "Controlul manual nu este activ"}), 400

    # Setăm flag-ul pentru oprire
    is_controlling = False
    control_thread.join()  # Așteptăm să termine thread-ul curent
    motion_proxy.rest()  # Oprește robotul în siguranță

    return jsonify({"message": "Control manual a fost oprit"}), 200


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

@app.route('/stop_all', methods=['POST'])
def stop_all():
    try:
        # Oprește mișcarea
        motion = ALProxy("ALMotion", NAO_IP, NAO_PORT)
        if motion.moveIsActive():
            motion.stopMove()
            motion.rest()  # Pune robotul într-o poziție sigură

        # Oprește toate sunetele
        audio = ALProxy("ALAudioPlayer", NAO_IP, NAO_PORT)
        audio.stopAll()

        tts = ALProxy("ALTextToSpeech", NAO_IP, NAO_PORT)
        tts.stopAll()

        return jsonify({"status": "success", "message": "Mișcările și sunetele au fost oprite"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# try:
#     behavior_manager = session.service("ALBehaviorManager")
#     installed_behaviors = behavior_manager.getInstalledBehaviors()
#     print("Comportamente instalate:", installed_behaviors)
# except Exception as e:
#     print("Eroare la obținerea comportamentelor:", e)


if __name__ == "__main__":
    webbrowser.open_new('http://localhost:5000')
    # Pornim serverul Flask pe portul 5000
    app.run(host="0.0.0.0", port=5000)
