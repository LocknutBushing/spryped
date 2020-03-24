"""
Copyright (C) 2013 Travis DeWolf
Copyright (C) 2020 Benjamin Bokser

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import control

import numpy as np


class Control(control.Control):
    """
    A controller that implements operational space control.
    Controls the (x,y) position of the end-effector.
    """

    def __init__(self, null_control=True, **kwargs):
        """
        null_control boolean: apply second controller in null space or not
        """

        super(Control, self).__init__(**kwargs)

        self.DOF = 3  # task space dimensionality
        self.null_control = null_control

    def control(self, robot, x_dd_des=None):
        """
        Generates a control signal to move the
        joints to the specified target.

        robot Robot: the robot model being controlled
        des list: the desired system position
        x_dd_des np.array: desired task-space acceleration,
                        system goes to self.target if None
        """

        # calculate desired end-effector acceleration
        if x_dd_des is None:
            self.x = robot.x
            x_dd_des = self.kp * (self.target - self.x)

        # print("x=")
        # print(self.x)
        # print("target=")
        # print(self.target)
        # generate the mass matrix in end-effector space
        Mq = robot.gen_Mq()
        Mx = robot.gen_Mx()
        # print("Mx = ")
        # print(Mx)
        # print("x_dd_des = ")
        # print(x_dd_des)
        # calculate force
        Fx = np.dot(Mx, x_dd_des)
        # calculate the Jacobian
        # print("Fx = ", Fx)
        JEE = robot.gen_jacEE()
        # tau = J^T * Fx + tau_grav, but gravity = 0
        # add in velocity compensation in GC space for stability
        self.u = (np.dot(JEE.T, Fx).reshape(-1, ) -
                  np.dot(Mq, self.kv * robot.dq).flatten())
        print("u = ")
        print(self.u)
        # print("first term = ")
        # print(np.dot(JEE.T, Fx).reshape(-1, ))
        # print("second term = ")
        # print(np.dot(Mq, self.kv * robot.dq).flatten())

        # if null_control is selected and the task space has
        # fewer DOFs than the robot, add a control signal in the
        # null space to try to move the robot to its resting state
        # if self.null_control and self.DOF < len(robot.L):

        # calculate our secondary control signal
        # calculated desired joint angle acceleration
        # prop_val = ((robot.rest_angles - robot.q) + np.pi) % (np.pi*2) - np.pi
        # q_des = (self.kp * prop_val + \
        #          self.kv * -robot.dq).reshape(-1,)

        # Mq = robot.gen_Mq()
        # u_null = np.dot(Mq, q_des)

        # calculate the null space filter
        # Jdyn_inv = np.dot(Mx, np.dot(JEE, np.linalg.inv(Mq)))
        # null_filter = np.eye(len(robot.L)) - np.dot(JEE.T, Jdyn_inv)

        # null_signal = np.dot(null_filter, u_null).reshape(-1,)

        # self.u += null_signal

        # if self.write_to_file is True:
        # feed recorders their signals
        #     self.u_recorder.record(0.0, self.u)
        #     self.xy_recorder.record(0.0, self.x)
        #     self.dist_recorder.record(0.0, self.target - self.x)

        # add in any additional signals
        for addition in self.additions:
            self.u += addition.generate(self.u, robot)

        return self.u

    def gen_target(self, robot):
        # Generate a random target
        # gain = np.sum(robot.L) * .75
        # bias = -np.sum(robot.L) * 0

        # self.target = np.random.random(size=(3,)) * gain + bias

        self.target = np.array([0.5, 0.86, 0])

        return self.target.tolist()
