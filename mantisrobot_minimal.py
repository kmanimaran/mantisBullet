import pybullet as p
import pybullet_utils.bullet_client as bc
import pybullet
import pybullet_data
import time
import math
import os
import atexit
import threading
import numpy as np
import socket
import copy
from bulletHelper import *
import socket


# https://github.com/4ndreas/Mantis-Robot-Arm 
# 
# more infos at:
# https://hackaday.io/project/3800-3d-printable-robot-arm


p.connect(p.GUI_SERVER)
p.configureDebugVisualizer(p.COV_ENABLE_GUI,0)
p.setAdditionalSearchPath(pybullet_data.getDataPath())


# create room
planeId = p.loadURDF("plane.urdf", useMaximalCoordinates=False)

# create robot
mantis_robot = p.loadURDF("./mantis/MantisRobot.urdf", useMaximalCoordinates=False, globalScaling=10.0)

# create target 
target = p.loadURDF("./mantis/pixel.urdf", useMaximalCoordinates=False, globalScaling=1.0)

# Joint damping coefficents. Using large values for the joints that we don't want to move.
jd = [100.0, 100.0, 100.0, 100.0, 100.0, 0.5]

# for now we just send an udp packet with the target positions for the motors 
transfer_ip = "192.168.2.210"
transfer_port = 8888
transfer_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# bullet index of the robot
body = 0


def endProgramm():
  print("exit now")


def makePositve(value):
  if value < 0:
    return (4096 + value)
  else:
    return value

def scale(value):
  value = value / (2 * math.pi)
  value *= 4096
  return makePositve( int((value + 2048)) ) 

def main():
  p.setRealTimeSimulation(1)
  p.setGravity(0, 0, -1) # we don't use gravity yet


  # debug colors only for show
  colors = [[1, 0, 0, 1], [0, 1, 0, 1], [0, 0, 1, 1], [1, 1, 1, 1], [0, 0, 0, 1] ]
  currentColor = 0

  try:

    body = p.getBodyUniqueId(mantis_robot)
    EndEffectorIndex = p.getNumJoints(body) -1
    print("EndEffectorIndex %i" % EndEffectorIndex)

    tx = 0
    ty = 5
    tz = 3
    tj = 0
    tp = 0
    tr = math.pi / 2

    orn = p.getQuaternionFromEuler([tj,tp,tr])

    jointT = p.calculateInverseKinematics(body, EndEffectorIndex, [tx, ty,tz], orn, jointDamping=jd)

    p.setJointMotorControlArray(body,[1,2,3,4,5,6] , controlMode=p.POSITION_CONTROL , targetPositions=jointT )
    print("x:%f y:%f z:%f j:%f p:%f r:%f " % (tx,ty,tz,tj,tp,tr))
    print(jointT)
    p.resetBasePositionAndOrientation(target, [tx, ty, tz ], orn)

    loop = 0
    hasPrevPose = 0
    trailDuration = 15

    distance = 5
    yaw = 90

    motorDir = [1,-1,1,1,1,1]

    while (p.isConnected()):
      time.sleep(1. / 240.)  # set to 40 fps
      p.stepSimulation()
       

      # get target positon
      targetPos, targetOrn = p.getBasePositionAndOrientation(target)
      # do Inverse Kinematics
      # jointT = p.calculateInverseKinematics(body, EndEffectorIndex, targetPos, targetOrn)
      jointT = p.calculateInverseKinematics(body, EndEffectorIndex, targetPos, orn)
      # set Robot Joints
      p.setJointMotorControlArray(body,[1,2,3,4,5,6] , controlMode=p.POSITION_CONTROL , targetPositions=jointT )
      # p.resetBasePositionAndOrientation(target, [tx, ty, tz ], orn)
          

      # generates the trail for debug only
      # optional
      loop +=1
      if loop > 10:
        loop = 0

        data_string = ""
        for i in range ( 1, EndEffectorIndex):
          jt = p.getJointState(body, i )
          data_string += "motor%i:%i\r\n" % ( i,  scale(motorDir[i-1] * jt[0]))

        transfer_socket.sendto(bytes(data_string, "utf-8"), (transfer_ip, transfer_port))

        ls = p.getLinkState(body, EndEffectorIndex)
        targetPos, targetOrn = p.getBasePositionAndOrientation(target)
        if (hasPrevPose):
          p.addUserDebugLine(prevPose, targetPos, [0, 0, 0.3], 1, trailDuration)
          p.addUserDebugLine(prevPose1, ls[4], [1, 0, 0], 1, trailDuration)
        prevPose = targetPos
        prevPose1 = ls[4]
        hasPrevPose = 1

      # get mouse events
      # changes color of the object clickt on and prints some info
      # optional
      mouseEvents = p.getMouseEvents()
      for e in mouseEvents:
        if ((e[0] == 2) and (e[3] == 0) and (e[4] & p.KEY_WAS_TRIGGERED)):
          mouseX = e[1]
          mouseY = e[2]
          rayFrom, rayTo = getRayFromTo(mouseX, mouseY)
          rayInfo = p.rayTest(rayFrom, rayTo)
          for l in range(len(rayInfo)):
            hit = rayInfo[l]
            objectUid = hit[0]
            jointUid = hit[1]
            if (objectUid >= 1):
              # this is for debug click on an object to get id 
              # oject will change color this has no effect
              print("obj %i joint %i" % (objectUid , jointUid))

              p.changeVisualShape(objectUid, jointUid, rgbaColor=colors[currentColor])
              currentColor += 1
              if (currentColor >= len(colors)):
                currentColor = 0


  except KeyboardInterrupt:
    print("KeyboardInterrupt has been caught.")
  finally:
    endProgramm()

if __name__ == "__main__":
  main()