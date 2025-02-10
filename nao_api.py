# -*- coding: utf-8 -*-
import pygame
from naoqi import ALProxy
import math

# Configurații pentru Nao
NAO_IP = "192.168.0.1"  # Înlocuiește cu IP-ul robotului Nao
NAO_PORT = 9559

# Conexiunea la Nao
motion_proxy = ALProxy("ALMotion", NAO_IP, NAO_PORT)
posture_proxy = ALProxy("ALRobotPosture", NAO_IP, NAO_PORT)

# Prag pentru a evita mișcări involuntare ale joystick-ului
DEAD_ZONE = 0.1


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


# Funcție pentru a controla robotul pe baza input-ului
def control_robot(joystick):
    # Activează controlul motoriilor
    motion_proxy.wakeUp()
    posture_proxy.goToPosture("StandInit", 0.5)  # Poziție inițială

    try:
        while True:
            for event in pygame.event.get():
                print(event)

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

    except KeyboardInterrupt:
        print("Controlul robotului oprit.")
        motion_proxy.rest()  # Oprește robotul în siguranță
    finally:
        pygame.quit()


# Inițializează controller-ul și pornește controlul
if __name__ == "__main__":
    joystick = init_controller()
    control_robot(joystick)
