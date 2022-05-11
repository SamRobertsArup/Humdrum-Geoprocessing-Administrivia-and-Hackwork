import pyautogui
import datetime
import time
import os

print("Koffee keeps your computer awake whilst you sleep, handy for overnight scripts")

cmd = 'mode 30,10'
os.system(cmd)
val = input("Enter shutdown'o'clock? (hh:mm)\n")
minsIdle = 0

pyautogui.PAUSE = 0.5
while True:
    x, y = pyautogui.position()
    time.sleep(60)
    curX, curY = pyautogui.position()
    if (x, y) == (curX, curY):
        minsIdle +=1
        pyautogui.press("shift")
        pyautogui.move(1,0)
        pyautogui.move(-1,0)
        print(str(datetime.datetime.now())+" "+str(minsIdle))
    else:
        minsIdle = 0
        
    if str(datetime.datetime.now().strftime("%H:%M")) == val:  #"17:30":
        print("works over!!")
        os.system("shutdown -s")
