import time
test = time.time()+5
while time.time() < test:
    print("WAITING")
    time.sleep(0.5)
    pass
