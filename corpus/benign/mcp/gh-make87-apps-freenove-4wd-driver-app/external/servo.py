from app.external.PCA9685 import PCA9685


class Servo:
    def __init__(self):
        self.PwmServo = PCA9685(0x40, debug=True)
        self.PwmServo.setPWMFreq(50)
        self.PwmServo.setServoPulse(8, 1500)
        self.PwmServo.setServoPulse(9, 1500)

    def setServoPwm(self, channel, angle, error=10):
        angle = int(angle)
        if channel == '0':
            self.PwmServo.setServoPulse(8, 2500 - int((angle + error) / 0.09))
        elif channel == '1':
            self.PwmServo.setServoPulse(9, 500 + int((angle + error) / 0.09))
        elif channel == '2':
            self.PwmServo.setServoPulse(10, 500 + int((angle + error) / 0.09))
        elif channel == '3':
            self.PwmServo.setServoPulse(11, 500 + int((angle + error) / 0.09))
        elif channel == '4':
            self.PwmServo.setServoPulse(12, 500 + int((angle + error) / 0.09))
        elif channel == '5':
            self.PwmServo.setServoPulse(13, 500 + int((angle + error) / 0.09))
        elif channel == '6':
            self.PwmServo.setServoPulse(14, 500 + int((angle + error) / 0.09))
        elif channel == '7':
            self.PwmServo.setServoPulse(15, 500 + int((angle + error) / 0.09))


# Main program logic follows:
if __name__ == '__main__':
    import time

    print("Use arrow keys to adjust the servos.")
    print("Up/Down arrows control servo channel 0.")
    print("Left/Right arrows control servo channel 1.")
    print("Press 'Esc' to exit.")

    pwm = Servo()  # Assuming Servo class is defined elsewhere

    servo0_pos = 90  # Initial position for servo channel 0
    servo1_pos = 90  # Initial position for servo channel 1

    def adjust_servo0(delta):
        global servo0_pos
        servo0_pos += delta
        servo0_pos = max(0, min(150, servo0_pos))  # Limit between 0 and 180 degrees
        pwm.setServoPwm('0', servo0_pos)
        print(f"Servo 0 position: {servo0_pos}°")

    def adjust_servo1(delta):
        global servo1_pos
        servo1_pos += delta
        servo1_pos = max(110, min(160, servo1_pos))
        pwm.setServoPwm('1', servo1_pos)
        print(f"Servo 1 position: {servo1_pos}°")

    try:
        while True:
            inp = input()
            if inp == "d":
                adjust_servo0(10)
                time.sleep(0.1)  # Delay to prevent rapid changes
            elif inp == "a":
                adjust_servo0(-10)
                time.sleep(0.1)
            elif inp == "s":
                adjust_servo1(-10)
                time.sleep(0.1)
            elif inp == "w":
                adjust_servo1(10)
                time.sleep(0.1)
            else:
                time.sleep(0.01)  # Small delay to reduce CPU usage
    except KeyboardInterrupt:
        print("\nEnd of program")