# -*- coding: utf-8 -*-
import qi
import time

NAO_IP = "192.168.0.1"  # Înlocuiește cu adresa IP a robotului tău
NAO_PORT = 9559           # Portul standard NAOqi


def macarena(session):
    """
    Funcția face robotul să danseze Macarena.
    """
    try:
        # Obține proxy-urile pentru serviciile ALMotion și ALRobotPosture
        motion_service = session.service("ALMotion")
        posture_service = session.service("ALRobotPosture")

        # Trezim robotul (activăm motoarele)
        motion_service.wakeUp()

        # Setăm postura de bază (StandInit)
        posture_service.goToPosture("StandInit", 0.5)

        # Definim mișcările pentru Macarena
        steps = [
            # 1. Brațul drept în față
            (["RShoulderPitch"], [0.0], [1.0]),
            # 2. Brațul stâng în față
            (["LShoulderPitch"], [0.0], [1.0]),
            # 3. Brațul drept la umăr
            (["RShoulderPitch", "RElbowYaw"], [1.0, 1.5], [1.0, 1.0]),
            # 4. Brațul stâng la umăr
            (["LShoulderPitch", "LElbowYaw"], [1.0, -1.5], [1.0, 1.0]),
            # 5. Brațul drept la ceafă
            (["RShoulderPitch", "RElbowYaw"], [1.5, 0.5], [1.0, 1.0]),
            # 6. Brațul stâng la ceafă
            (["LShoulderPitch", "LElbowYaw"], [1.5, -0.5], [1.0, 1.0]),
            # 7. Brațul drept pe șold
            (["RShoulderPitch", "RElbowRoll"], [1.5, 0.0], [1.0, 1.0]),
            # 8. Brațul stâng pe șold
            (["LShoulderPitch", "LElbowRoll"], [1.5, 0.0], [1.0, 1.0]),
            # 9. Mișcare a șoldurilor (dreapta-stânga)
            (["RHipRoll", "LHipRoll"], [-0.3, 0.3], [1.0, 1.0]),
            (["RHipRoll", "LHipRoll"], [0.3, -0.3], [1.0, 1.0]),
            (["RHipRoll", "LHipRoll"], [0.0, 0.0], [1.0, 1.0]),
        ]

        # Executăm fiecare pas al dansului
        for step in steps:
            names, angles, times = step
            motion_service.angleInterpolation(names, angles, times, True)
            time.sleep(0.5)  # Pauză între mișcări pentru sincronizare

        # Revenim la postura inițială
        posture_service.goToPosture("StandInit", 0.5)

        # Oprim robotul (deactivăm motoarele)
        motion_service.rest()

        print("Robotul a dansat Macarena!")
    except Exception as e:
        print("Eroare la efectuarea mișcărilor: {}".format(e))


def main():
    try:
        # Creăm sesiunea și ne conectăm la robot
        session = qi.Session()
        session.connect("tcp://{}:{}".format(NAO_IP, NAO_PORT))
        print("Conexiune reușită la robot!")

        # Executăm dansul Macarena
        macarena(session)
    except Exception as e:
        print("Eroare conexiune: {}".format(e))


if __name__ == "__main__":
    main()
