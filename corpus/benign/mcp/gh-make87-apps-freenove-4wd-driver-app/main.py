import threading
import time
from threading import Thread
import logging
from typing import Optional

import mcp.server
import numpy as np
import cv2
import zenoh
from make87.interfaces.zenoh import ZenohInterface

from make87_messages.core.empty_pb2 import Empty
from make87_messages.core.header_pb2 import Header
from make87_messages.tensor.vector_2_pb2 import Vector2
from make87_messages.tensor.vector_3_pb2 import Vector3
from make87_messages.image.compressed.image_jpeg_pb2 import ImageJPEG

import make87 as m87
from app.external.Motor import Motor
from app.external.servo import Servo


class Vehicle:
    def __init__(self, servo: Optional[Servo] = None, motor: Optional[Motor] = None):
        pass
        self.motor = motor if motor else Motor()
        self.camera_servo = servo if servo else Servo()
        self.last_image_lock = threading.Lock()
        self.last_image = None

        # Initial camera angles
        self.pitch = 135.0  # midway between 111 and 159
        self.yaw = 75.0  # midway between 1 and 149
        self.camera_servo.setServoPwm("1", self.pitch)
        self.camera_servo.setServoPwm("0", self.yaw)

    @staticmethod
    def compute_wheel_speeds(x: float, y: float, max_speed=1000):
        """Convert BEV vector to left/right wheel speeds.

        Positive x → right turn (left wheel faster)
        Positive y → forward
        """
        # Clamp vector magnitude to 1 (optional safety)
        vector = np.array([x, y])
        mag = np.linalg.norm(vector)
        if mag > 1:
            vector /= mag

        turn = vector[0]  # right is positive
        speed = vector[1]  # forward

        # Corrected mixing:
        left = speed + turn  # Right turn: left wheel goes faster
        right = speed - turn  # Right turn: right wheel slows down

        # Normalize if needed to avoid exceeding [-1, 1]
        max_val = max(abs(left), abs(right))
        if max_val > 1:
            left /= max_val
            right /= max_val

        return int(left * max_speed), int(right * max_speed)

    def run_drive_instruction(self, x: float, y: float, duration: float):
        left_motor, right_motor = self.compute_wheel_speeds(x, y)

        self.motor.setMotorModel(
            front_left=left_motor,
            rear_left=left_motor,
            front_right=right_motor,
            rear_right=right_motor,
        )

        time.sleep(max(0.0, duration))
        self.motor.setMotorModel(front_left=0, rear_left=0, front_right=0, rear_right=0)

    def handle_drive_instruction(self, query: zenoh.Query):
        message = m87.encodings.ProtobufEncoder(message_type=Vector3).decode(
            query.payload
        )
        self.run_drive_instruction(x=message.x, y=message.y, duration=message.z)

        message_encoded = m87.encodings.ProtobufEncoder(message_type=Empty).encode(
            Empty()
        )
        query.reply(key_expr=query.key_expr, payload=message_encoded)

    def set_camera_direction(self, delta_x: float, delta_y: float):
        """Set camera direction based on delta angles."""
        # x = yaw delta (clockwise = right)
        # y = pitch delta (clockwise = down)

        self.yaw = max(1.0, min(149.0, self.yaw + delta_x))
        self.pitch = max(111.0, min(159.0, self.pitch + delta_y))

        self.camera_servo.setServoPwm("0", self.yaw)
        self.camera_servo.setServoPwm("1", self.pitch)

    def handle_set_camera_direction(self, query: zenoh.Query):
        delta = m87.encodings.ProtobufEncoder(message_type=Vector2).decode(
            query.payload
        )

        self.set_camera_direction(delta_x=delta.x, delta_y=delta.y)

        message_encoded = m87.encodings.ProtobufEncoder(message_type=Empty).encode(
            Empty()
        )
        query.reply(key_expr=query.key_expr, payload=message_encoded)

    def get_latest_camera_image(self) -> bytes:
        """Get the latest camera image as bytes."""
        with self.last_image_lock:
            if self.last_image is not None:
                return self.last_image
            else:
                return b""

    def handle_get_latest_camera_image(self, query: zenoh.Query):
        # This method is not implemented in the original code
        # You can implement it if needed
        img_msg = self.get_latest_camera_image()

        header = Header(entity_path="/picamera")
        header.timestamp.GetCurrentTime()
        img_msg = ImageJPEG(data=img_msg, header=header)

        message_encoded = m87.encodings.ProtobufEncoder(message_type=ImageJPEG).encode(
            img_msg
        )
        query.reply(key_expr=query.key_expr, payload=message_encoded)

    def publish_camera_image(self):
        from picamera2.picamera2 import Picamera2

        config = m87.config.load_config_from_env()
        zenoh_interface = ZenohInterface(name="zenoh-client", make87_config=config)

        topic = zenoh_interface.get_publisher(name="IMAGE")

        try:
            picam2 = Picamera2()
            video_config = picam2.create_video_configuration(
                main={"size": (640, 480), "format": "RGB888"}
            )
            picam2.configure(video_config)
            picam2.start()
        except Exception as e:
            logging.error(f"Cannot initialize camera: {e}")
            return

        while True:
            try:
                frame = picam2.capture_array()
                ret, frame_jpeg = cv2.imencode(".jpeg", frame)
                if not ret:
                    logging.error("Error: Could not encode frame to JPEG.")
                    break
                frame_jpeg_bytes = frame_jpeg.tobytes()
                header = Header(entity_path="/picamera")
                message = ImageJPEG(data=frame_jpeg_bytes, header=header)
                with self.last_image_lock:
                    self.last_image = message.data
                payload = m87.encodings.ProtobufEncoder(message_type=ImageJPEG).encode(
                    message
                )
                topic.put(payload=payload)
            except Exception as e:
                logging.error(f"Error while capturing or publishing image: {e}")
                break

        picam2.stop()

    def run(self):
        config = m87.config.load_config_from_env()
        zenoh_interface = ZenohInterface(name="zenoh-client", make87_config=config)

        camera_thread = Thread(target=self.publish_camera_image)
        camera_thread.start()

        drive_prv = zenoh_interface.get_provider(
            name="SET_DRIVE_DIRECTION", handler=self.handle_drive_instruction
        )
        cam_dir_prv = zenoh_interface.get_provider(
            name="SET_CAMERA_DIRECTION", handler=self.handle_set_camera_direction
        )

        cam_img_prv = zenoh_interface.get_provider(
            name="GET_CAMERA_IMAGE", handler=self.handle_get_latest_camera_image
        )

        mcp_server = self.get_mcp_server()

        mcp_server.run(transport="streamable-http")
        camera_thread.join()

    def get_mcp_server(self) -> mcp.server.FastMCP:
        server = mcp.server.FastMCP(name="vehicle", host="0.0.0.0", port=9988)

        server.add_tool(
            fn=self.run_drive_instruction,
            name="run_drive_instruction",
            description="Run a drive instruction with x, y, duration parameters.",
        )
        server.add_tool(
            fn=self.set_camera_direction,
            name="set_camera_direction",
            description="Set camera direction based on delta angles (x: yaw, y: pitch).",
        )
        server.add_tool(
            fn=self.get_latest_camera_image,
            name="get_latest_camera_image",
            description="Get the latest camera image as jpeg bytes.",
        )
        return server


def main():
    vehicle = Vehicle()
    vehicle.run()


if __name__ == "__main__":
    main()
