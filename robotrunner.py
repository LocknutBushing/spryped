"""
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
import contact
import simulationbridge
import leg
import wbc
import mpc
import statemachine
import qvis

import time
import sys
import curses

import transforms3d
import numpy as np
from scipy.interpolate import CubicSpline

np.set_printoptions(suppress=True, linewidth=np.nan)


class Runner:

    def __init__(self, dt=1e-3):

        self.dt = dt
        self.u_l = np.zeros(4)
        self.u_r = np.zeros(4)

        left = 1
        right = 0

        self.leg_left = leg.Leg(dt=dt, leg=left)
        self.leg_right = leg.Leg(dt=dt, leg=right)
        controller_class = wbc
        self.controller_left = controller_class.Control(dt=dt)
        self.controller_right = controller_class.Control(dt=dt)
        self.force = mpc.Mpc(dt=dt)
        self.contact_left = contact.Contact(leg=self.leg_left, dt=dt)
        self.contact_right = contact.Contact(leg=self.leg_right, dt=dt)
        self.simulator = simulationbridge.Sim(dt=dt)
        self.state_left = statemachine.Char()
        self.state_right = statemachine.Char()

        # gait scheduler values
        self.target_init = np.array([0, 0, -0.8325])  # , self.init_alpha, self.init_beta, self.init_gamma])
        self.target_l = self.target_init
        self.target_r = self.target_init
        self.sh_l = 1  # estimated contact state (left)
        self.sh_r = 1  # estimated contact state (right)
        self.dist_force_l = np.array([0, 0, 0])
        self.dist_force_r = np.array([0, 0, 0])
        self.t_p = 0.5  # gait period, seconds
        self.phi_switch = 0.75  # switching phase, must be between 0 and 1. Percentage of gait spent in contact.
        self.gait_left = Gait(controller=self.controller_left, robotleg=self.leg_left,
                              t_p=self.t_p, phi_switch=self.phi_switch, dt=dt)
        self.gait_right = Gait(controller=self.controller_right, robotleg=self.leg_right,
                               t_p=self.t_p, phi_switch=self.phi_switch, dt=dt)

        self.target = None

        # footstep planner values
        self.omega_d = np.array([0, 0, 0])  # desired angular acceleration for footstep planner
        self.k_f = 0.5  # Raibert heuristic gain
        self.h = np.array([0, 0, 0.8325])  # height, assumed to be constant
        self.r_l = np.array([0, 0, 0])  # initial footstep planning position
        self.r_r = np.array([0, 0, 0])  # initial footstep planning position

    def run(self):

        steps = 0
        t = 0  # time

        t0_l = t  # starting time, left leg
        t0_r = t0_l + self.t_p / 2  # starting time, right leg. Half a period out of phase with left

        prev_state_l = str("init")
        prev_state_r = prev_state_l
        prev_contact_l = False
        prev_contact_r = False

        while 1:
            time.sleep(self.dt)
            # update target after specified period of time passes
            steps += 1
            t = t + self.dt
            # print(t)
            # run simulator to get encoder and IMU feedback
            # put an if statement here once we have hardware bridge too
            q, b_orient = self.simulator.sim_run(u_l=self.u_l, u_r=self.u_r)

            q_left = q[0:4]
            q_left[1] *= -1
            q_left[2] *= -1
            q_left[3] *= -1

            q_right = q[4:8]
            q_right[3] *= -1

            # enter encoder values into leg kinematics/dynamics
            self.leg_left.update_state(q_in=q_left)
            self.leg_right.update_state(q_in=q_right)

            # gait scheduler
            s_l = self.gait_scheduler(t, t0_l)
            s_r = self.gait_scheduler(t, t0_r)
            sh_l = self.gait_estimator(self.dist_force_l[2])
            sh_r = self.gait_estimator(self.dist_force_r[2])

            state_l = self.state_left.FSM.execute(s_l, sh_l)
            state_r = self.state_right.FSM.execute(s_r, sh_r)
            # print(state_l, sh_l, self.dist_force_l[2])
            # forward kinematics
            pos_l = np.dot(b_orient, self.leg_left.position()[:, -1])
            pos_r = np.dot(b_orient, self.leg_right.position()[:, -1])

            # omega = transforms3d.euler.quat2euler(self.simulator.omega, axes='szyx')

            v = np.array(self.simulator.v)

            phi = transforms3d.euler.mat2euler(b_orient, axes='szyx')[0]
            c_phi = np.cos(phi)
            s_phi = np.sin(phi)
            # rotation matrix Rz(phi)
            rz_phi = np.zeros((3, 3))
            rz_phi[0, 0] = c_phi
            rz_phi[0, 1] = s_phi
            rz_phi[1, 0] = -c_phi
            rz_phi[1, 1] = s_phi
            rz_phi[2, 2] = 1

            if state_l == ('stance' or 'early'):
                contact_l = True
            else:
                contact_l = False

            if state_r == ('stance' or 'early'):
                contact_r = True
            else:
                contact_r = False

            if contact_l is True and prev_contact_l is False:
                self.r_l = self.footstep(robotleg=1, rz_phi=rz_phi, v=v, v_d=0)

            if contact_r is True and prev_contact_r is False:
                self.r_r = self.footstep(robotleg=0, rz_phi=rz_phi, v=v, v_d=0)

            # forces = self.force.mpcontrol(rz_phi=rz_phi, r1=self.r_l, r2=self.r_r, xs=1)

            # calculate wbc control signal
            self.u_l = self.gait_left.u(state=state_l,
                                        prev_state=prev_state_l, r_in=pos_l, r_d=self.r_l,
                                        b_orient=b_orient)  # just standing for now

            self.u_r = self.gait_right.u(state=state_r,
                                         prev_state=prev_state_r, r_in=pos_r, r_d=self.r_r,
                                         b_orient=b_orient)  # just standing for now

            # receive disturbance torques
            dist_tau_l = self.contact_left.disturbance_torque(Mq=self.controller_left.Mq,
                                                              dq=self.leg_left.dq,
                                                              tau_actuated=-self.u_l,
                                                              grav=self.controller_left.grav)
            dist_tau_r = self.contact_right.disturbance_torque(Mq=self.controller_right.Mq,
                                                               dq=self.leg_right.dq,
                                                               tau_actuated=-self.u_r,
                                                               grav=self.controller_right.grav)
            # convert disturbance torques to forces
            self.dist_force_l = np.dot(np.linalg.pinv(np.transpose(self.leg_left.gen_jacEE()[0:3])),
                                       np.array(dist_tau_l))
            self.dist_force_r = np.dot(np.linalg.pinv(np.transpose(self.leg_right.gen_jacEE()[0:3])),
                                       np.array(dist_tau_r))

            prev_state_l = state_l
            prev_state_r = state_r

            prev_contact_l = contact_l
            prev_contact_r = contact_r

            # -------------------------quaternion-visualizer-animation--------------------------------- #
            # q_e = self.controller_left.q_e
            # qvis.animate(q_e)
            # ----------------------------------------------------------------------------------------- #

            # print(self.dist_force_l[2])
            # print(self.reaction_torques()[0:4])

            # tau_d_left = self.contact_left.contact(leg=self.leg_left, g=self.leg_left.grav)

            # fw kinematics
            # print(np.transpose(np.append(np.dot(b_orient, self.leg_left.position()[:, -1]),
            #                              np.dot(b_orient, self.leg_right.position()[:, -1]))))
            # joint velocity
            # print("vel = ", self.leg_left.velocity())
            # encoder feedback
            # print(np.transpose(np.append(self.leg_left.q, self.leg_right.q)))

            # sys.stdout.write("\033[F")  # back to previous line
            # sys.stdout.write("\033[K")  # clear line

    def gait_scheduler(self, t, t0):
        # Add variable period later
        phi = np.mod((t - t0) / self.t_p, 1)

        if phi > self.phi_switch:
            s = 0  # scheduled swing
        else:
            s = 1  # scheduled stance

        return s

    def gait_estimator(self, dist_force):
        # Determines whether foot is actually in contact or not

        if dist_force >= 50:
            sh = 1  # stance
        else:
            sh = 0  # swing

        return sh

    def footstep(self, robotleg, rz_phi, v, v_d):
        # plans next footstep locatleg, ion
        if robotleg == 1:
            l_i = 0.144  # left hip length
        else:
            l_i = -0.144  # right hip length

        p_hip = np.dot(rz_phi, np.array([0, l_i, 0]))
        t_stance = self.t_p * self.phi_switch
        p_symmetry = t_stance * 0.5 * v + self.k_f * (v - v_d)
        p_cent = 0.5 * np.sqrt(self.h / 9.807) * np.cross(v, self.omega_d)

        return p_hip + p_symmetry + p_cent


class Gait:
    def __init__(self, controller, robotleg, t_p, phi_switch, dt=1e-3, **kwargs):

        self.swing_steps = 0
        self.trajectory = None
        self.t_p = t_p
        self.phi_switch = phi_switch
        self.dt = dt
        self.init_alpha = -np.pi / 2
        self.init_beta = 0  # can't control, ee Jacobian is zeros in that row
        self.init_gamma = 0
        self.controller = controller
        self.robotleg = robotleg

    def u(self, state, prev_state, r_in, r_d, b_orient):

        if state == 'swing':
            if prev_state != state:
                self.swing_steps = 0
                self.trajectory = self.traj(x_prev=r_in[0], x_d=r_d[0], y_prev=r_in[1], y_d=r_d[1])

            # set target position
            target = self.trajectory[:, self.swing_steps]
            target = np.hstack(np.append(target,
                                         np.array([self.init_alpha, self.init_beta, self.init_gamma])))

            self.swing_steps += 1
            # calculate wbc control signal
            u = -self.controller.control(leg=self.robotleg, target=target, b_orient=b_orient)

        elif state == 'stance' or state == 'early':
            # execute MPC
            force = 3
            # u = force
            # calculate wbc control signal
            target = np.array([0, 0, -0.8235, self.init_alpha, self.init_beta, self.init_gamma])
            u = -self.controller.control(leg=self.robotleg, target=target, b_orient=b_orient)

        elif state == 'late':  # position command should freeze at last target position
            target = np.array([0, 0, -0.8235, self.init_alpha, self.init_beta, self.init_gamma])
            # calculate wbc control signal
            u = -self.controller.control(leg=self.robotleg, target=target, b_orient=b_orient)

        else:
            u = None  # this'll throw an error if state machine is haywire or something

        return u

    def traj(self, x_prev, x_d, y_prev, y_d):
        # Generates cubic spline curve trajectory for foot swing

        # number of time steps allotted for swing trajectory

        timesteps = self.t_p * (1 - self.phi_switch) / self.dt
        if not timesteps.is_integer():
            print("Error: period and timesteps are not divisible")  # if t_p is variable
        path = np.zeros(int(timesteps))

        horizontal = np.array([0.0, timesteps / 2, timesteps])
        vertical = np.array([-0.8325, -0.7, -0.8325])  # z position assumed constant body height and flat floor
        cs = CubicSpline(horizontal, vertical)

        # create evenly spaced sample points of desired trajectory
        for t in range(int(timesteps)):
            path[t] = cs(t)
        z_traj = path
        x_traj = np.linspace(x_prev, x_d, timesteps)
        y_traj = np.linspace(y_prev, y_d, timesteps)

        return np.array([x_traj.T, y_traj.T, z_traj.T])