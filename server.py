# -*- coding: utf-8 -*-
import qi
import numpy as np
import cv2
import threading
import time
from flask import Flask, request, jsonify, Response, send_file
import io
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D


NAO_IP = "192.168.0.1"  # Adresa IP a robotului
NAO_PORT = 9559         # Portul NAOqi (în mod normal 9559)

# Inițializăm Flask
app = Flask(__name__)

# Configurăm sesiunea cu robotul
try:
    session = qi.Session()
    session.connect("tcp://{}:{}".format(NAO_IP, NAO_PORT))
    print("Conexiune reușită la robot!")
except Exception as e:
    print("Eroare conexiune: {}".format(e))
    session = None


@app.route("/")
def index():
    return "Serverul API NAO este activ!"


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


@app.route("/sensors", methods=["GET"])
def sensors():
    """
    Citește informațiile de la senzorii robotului.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        memory_service = session.service("ALMemory")
        battery = memory_service.getData("Device/SubDeviceList/Battery/Charge/Sensor/Value")
        touch_head = memory_service.getData("Device/SubDeviceList/Head/Touch/Front/Sensor/Value")

        return jsonify({
            "battery_level": battery,
            "touch_head": "pressed" if touch_head > 0.5 else "not_pressed"
        })
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


@app.route("/robot_pose_3d", methods=["GET"])
def robot_pose_3d():
    """
    Generează o reprezentare 3D a poziției curente a robotului NAO.
    Returnează un grafic 3D care arată pozițiile articulațiilor robotului.
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
            joint_positions.append(position[:3])  # X, Y, Z

        # Conversie în array pentru procesare ușoară
        joint_positions = np.array(joint_positions)

        # Pregătește graficul 3D
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        # Adaugă articulațiile robotului pe grafic
        ax.scatter(joint_positions[:, 0], joint_positions[:, 1], joint_positions[:, 2], c='blue', label='Articulații')
        for i, joint in enumerate(joint_names):
            ax.text(joint_positions[i, 0], joint_positions[i, 1], joint_positions[i, 2], joint, fontsize=8)

        # Configurează axele graficului
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")
        ax.set_title("Reprezentarea 3D a poziției robotului NAO")

        # Adaugă linii de conexiune între articulații (schelet simplificat)
        for i in range(len(joint_positions) - 1):
            ax.plot([joint_positions[i, 0], joint_positions[i + 1, 0]],
                    [joint_positions[i, 1], joint_positions[i + 1, 1]],
                    [joint_positions[i, 2], joint_positions[i + 1, 2]], c='gray')

        # Salvează graficul într-un buffer de memorie
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close(fig)

        # Trimite graficul ca răspuns HTTP
        return send_file(buf, mimetype='image/png')

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/robot_pose_2d", methods=["GET"])
def robot_pose_2d():
    """
    Generează o reprezentare 2D a pozițiilor articulațiilor robotului NAO.
    Returnează un grafic 2D care arată pozițiile articulațiilor robotului.
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
            joint_positions.append(position[:2])  # X, Y

        # Conversie în array pentru procesare ușoară
        joint_positions = np.array(joint_positions)

        # Pregătește graficul 2D
        fig, ax = plt.subplots()
        ax.scatter(joint_positions[:, 0], joint_positions[:, 1], c='red', label='Articulații')
        for i, joint in enumerate(joint_names):
            ax.text(joint_positions[i, 0], joint_positions[i, 1], joint, fontsize=8)

        # Configurează axele graficului
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_title("Reprezentarea 2D a poziției robotului NAO")

        # Salvează graficul într-un buffer de memorie
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close(fig)

        # Trimite graficul ca răspuns HTTP
        return send_file(buf, mimetype='image/png')

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/robot_pose_2d_video", methods=["GET"])
def robot_pose_2d_video():

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
            joint_positions.append(position[:2])  # X, Y

        # Conversie în array pentru procesare ușoară
        joint_positions = np.array(joint_positions)

        # Pregătește graficul 2D
        fig, ax = plt.subplots()
        ax.scatter(joint_positions[:, 0], joint_positions[:, 1], c='red', label='Articulații')
        for i, joint in enumerate(joint_names):
            ax.text(joint_positions[i, 0], joint_positions[i, 1], joint, fontsize=8)

        # Configurează axele graficului
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_title("Reprezentarea 2D a poziției robotului NAO")

        # Salvează graficul într-un buffer de memorie
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close(fig)

        # Trimite graficul ca răspuns HTTP
        return send_file(buf, mimetype='image/png')

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/robot_pose_3d_video", methods=["GET"])
def robot_pose_3d_video():
    """
    Generează un videoclip 3D animat al pozițiilor articulațiilor robotului NAO.
    Returnează un videoclip 3D animat care arată pozițiile articulațiilor robotului.
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
            joint_positions.append(position[:3])  # X, Y, Z

        # Conversie în array pentru procesare ușoară
        joint_positions = np.array(joint_positions)

        # Pregătește graficul 3D
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        # Adaugă articulațiile robotului pe grafic
        ax.scatter(joint_positions[:, 0], joint_positions[:, 1], joint_positions[:, 2], c='blue', label='Articulații')
        for i, joint in enumerate(joint_names):
            ax.text(joint_positions[i, 0], joint_positions[i, 1], joint_positions[i, 2], joint, fontsize=8)

        # Configurează axele graficului
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")
        ax.set_title("Reprezentarea 3D a poziției robotului NAO")

        # Adaugă linii de conexiune între articulații (schelet simplificat)
        for i in range(len(joint_positions) - 1):
            ax.plot([joint_positions[i, 0], joint_positions[i + 1, 0]],
                    [joint_positions[i, 1], joint_positions[i + 1, 1]],
                    [joint_positions[i, 2], joint_positions[i + 1, 2]], c='gray')

        # Salvează graficul într-un buffer de memorie
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close(fig)

        # Trimite graficul ca răspuns HTTP
        return send_file(buf, mimetype='image/png')

    except Exception as e:
        return jsonify({"error": str(e)}), 500


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


@app.route("/robot_acceleration", methods=["GET"])
def robot_acceleration():
    """
    Returnează accelerația actuală a robotului NAO.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        # Obține serviciul ALMotion
        motion_service = session.service("ALMotion")

        # Obține accelerația actuală a robotului
        acceleration = motion_service.getRobotAcceleration()

        return jsonify({
            "linear_acceleration": acceleration[0],
            "angular_acceleration": acceleration[1]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/robot_stiffness", methods=["GET", "POST"])
def robot_stiffness():
    """
    Setează sau obține rigiditatea articulațiilor robotului NAO.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    if request.method == "GET":
        try:
            # Obține serviciul ALMotion
            motion_service = session.service("ALMotion")

            # Obține rigiditatea actuală a robotului
            stiffnesses = motion_service.getStiffnesses("Body")

            return jsonify(stiffnesses)

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == "POST":
        try:
            data = request.json
            stiffness = data.get("stiffness", 1.0)

            # Validăm valoarea rigidității
            if not isinstance(stiffness, (int, float)) or stiffness < 0 or stiffness > 1:
                return jsonify({"error": "Valoarea rigidității trebuie să fie un număr între 0 și 1"}), 400

            # Obține serviciul ALMotion
            motion_service = session.service("ALMotion")

            # Setează rigiditatea pentru toate articulațiile robotului
            motion_service.setStiffnesses("Body", stiffness)

            return jsonify({"status": "Rigiditatea articulațiilor a fost setată la {}".format(stiffness)})

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    else:
        return jsonify({"error": "Metoda HTTP nu este suportată"}), 405


@app.route("/play_sound", methods=["POST"])
def play_sound():
    """
    Reproduce un fișier audio pe robotul NAO.
    Parametri POST:
      - file: Calea către fișierul audio de redat.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    data = request.get_json()

    if not data:
        return jsonify({"error": "Datele JSON nu au fost trimise corect"}), 400

    file_path = data.get("file")

    if not file_path:
        return jsonify({"error": "Calea către fișierul audio nu a fost specificată"}), 400

    try:
        audio_player = session.service("ALAudioPlayer")
        audio_player.playFile(file_path)
        return jsonify({"status": "Fișierul audio a fost redat"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/stop_sound", methods=["POST"])
def stop_sound():
    """
    Oprește redarea fișierului audio pe robotul NAO.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    try:
        audio_player = session.service("ALAudioPlayer")
        audio_player.stopAll()
        return jsonify({"status": "Redarea fișierului audio a fost oprită"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/play_animation", methods=["POST"])

def play_animation():
    """
    Reproduce o animație pe robotul NAO.
    Parametri POST:
      - animation: Numele animației de redat.
    """
    if not session:
        return jsonify({"error": "Conexiune la robot eșuată"}), 500

    data = request.get_json()

    if not data:
        return jsonify({"error": "Datele JSON nu au fost trimise corect"}), 400

    animation = data.get("animation")

    if not animation:
        return jsonify({"error": "Numele animației nu a fost specificat"}), 400

    try:
        behavior_manager = session.service("ALBehaviorManager")
        if behavior_manager.isBehaviorInstalled(animation):
            if not behavior_manager.isBehaviorRunning(animation):
                behavior_manager.startBehavior(animation)
                return jsonify({"status": "Animația a fost redată"})
            else:
                return jsonify({"status": "Animația este deja în execuție"})
        else:
            return jsonify({"error": "Animația {animation} nu este instalată"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# try:
#     behavior_manager = session.service("ALBehaviorManager")
#     installed_behaviors = behavior_manager.getInstalledBehaviors()
#     print("Comportamente instalate:", installed_behaviors)
# except Exception as e:
#     print("Eroare la obținerea comportamentelor:", e)


if __name__ == "__main__":
    # Pornim serverul Flask pe portul 5000
    app.run(host="0.0.0.0", port=5000)
