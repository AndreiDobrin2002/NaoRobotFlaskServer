# -*- coding: utf-8 -*-
import qi

NAO_IP = "192.168.0.1"  # Asigură-te că aceasta este adresa IP corectă a robotului
NAO_PORT = 9559           # Portul standard NAOqi (în mod normal 9559)

def salut_robot(session):
    """
    Funcția face robotul să efectueze o mișcare de salut.
    """
    try:
        # Obține proxy-ul pentru serviciul ALMotion
        motion_service = session.service("ALMotion")
        posture_service = session.service("ALRobotPosture")

        # Trezim robotul (activăm motoarele)
        motion_service.wakeUp()

        # Setăm postura de bază (StandInit)
        posture_service.goToPosture("StandInit", 0.5)

        # Mișcarea brațului drept (salut)
        names = ["RShoulderPitch", "RShoulderRoll", "RElbowYaw", "RElbowRoll", "RWristYaw"]
        angles = [0.5, -0.3, 1.5, 1.0, 0.3]  # Unghiuri în radiani
        times = [1.0, 1.0, 1.0, 1.0, 1.0]    # Timpul în care să finalizeze mișcarea
        motion_service.angleInterpolation(names, angles, times, True)

        # Pauză pentru ca salutul să fie vizibil
        import time
        time.sleep(2)

        # Revenim la postura inițială
        posture_service.goToPosture("StandInit", 0.5)

        # Oprim robotul (deactivăm motoarele)
        motion_service.rest()

        print("Mișcarea de salut a fost efectuată cu succes!")
    except Exception as e:
        print("Eroare la efectuarea mișcării: {}".format(e))


def main():
    try:
        # Creăm sesiunea și ne conectăm la robot
        session = qi.Session()
        session.connect("tcp://{}:{}".format(NAO_IP, NAO_PORT))
        print("Conexiune reușită la robot!")

        # Executăm mișcarea de salut
        salut_robot(session)
    except Exception as e:
        print("Eroare conexiune: {}".format(e))


if __name__ == "__main__":
    main()
