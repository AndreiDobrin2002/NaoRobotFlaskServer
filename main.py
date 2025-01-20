# -*- coding: utf-8 -*-
import qi

NAO_IP = "192.168.0.1"  # Asigură-te că aceasta este adresa IP corectă a robotului
NAO_PORT = 9559           # Portul standard NAOqi (în mod normal 9559)

try:
    session = qi.Session()
    session.connect("tcp://{}:{}".format(NAO_IP, NAO_PORT))  # Înlocuiește cu adresa IP și portul corect
    print("Conexiune reușită la robot!")
except Exception as e:
    print("Eroare conexiune: {}".format(e))
