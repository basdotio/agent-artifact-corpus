#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import rospy
import json
import uuid
import argparse
import time
from iscas_msgs.msg import BasicControlReq, BasicControlResp, VehicleStatus

# 强制指定网络环境
os.environ['ROS_IP'] = '172.16.15.28'
os.environ['ROS_MASTER_URI'] = 'http://172.16.15.20:11311'

def drone_takeoff(target_altitude):
    rospy.init_node('zeroclaw_takeoff_worker', anonymous=True)
    pub = rospy.Publisher('/bh_tree/basic_control/req', BasicControlReq, queue_size=10)
    
    uav_status = {"altitude": 0.0, "flight_state": "UNKNOWN", "armed": False}
    
    def status_callback(msg):
        curr_z = msg.localization_status.position.z
        # 相对地面高度修正 (GROUND_Z = -0.3)
        uav_status["altitude"] = round(curr_z + 0.3, 2)
        if uav_status["altitude"] < 0.1: uav_status["altitude"] = 0.0
        uav_status["armed"] = msg.armed
        
        if not msg.armed:
            uav_status["flight_state"] = "LOCKED"
        else:
            uav_status["flight_state"] = "FLYING" if uav_status["altitude"] > 0.3 else "ARMED"

    rospy.Subscriber('/bh_tree/vehicle_status', VehicleStatus, status_callback)
    
    # 1. 等待连接
    while pub.get_num_connections() == 0 and not rospy.is_shutdown():
        rospy.sleep(0.1)
    
    # 2. 发送解锁并起飞
    request_id = str(uuid.uuid4())
    arm_req = BasicControlReq(command=3, request_id=request_id+"_arm") # CMD_ARM
    pub.publish(arm_req)
    rospy.sleep(0.5)
    
    takeoff_req = BasicControlReq(command=0, request_id=request_id, height=target_altitude) # CMD_TAKEOFF
    pub.publish(takeoff_req)
    
    # 3. 内部轮询监控 (关键改进)
    timeout = 45
    start_time = time.time()
    
    while (time.time() - start_time) < timeout and not rospy.is_shutdown():
        # 实时打印当前状态给 Zeroclaw
        # 注意：使用 RUNNING 状态，AI 会看到进度
        print(json.dumps({
            "status": "RUNNING", 
            "altitude": uav_status["altitude"], 
            "state": uav_status["flight_state"]
        }))
        sys.stdout.flush() # 确保实时输出

        # 判断是否到达终态
        if uav_status["flight_state"] == "FLYING" and uav_status["altitude"] >= (target_altitude - 0.4):
            print(json.dumps({
                "status": "SUCCESS", 
                "message": "Target altitude reached.", 
                "final_altitude": uav_status["altitude"]
            }))
            return

        rospy.sleep(1.0)
    
    print(json.dumps({"status": "FAILURE", "error": "Takeoff timeout or check vehicle status."}))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--alt", type=float, default=3.0)
    args, unknown = parser.parse_known_args() # 忽略 ROS 重映射参数
    try:
        drone_takeoff(args.alt)
    except Exception as e:
        print(json.dumps({"status": "ERROR", "message": str(e)}))
