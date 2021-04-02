'''
# This module is a simulation environment, which provides different-level (from easy to hard)
# simulation benchmark environments and animation facilities for the user to test their learning algorithm.
# This environment is versatile to use, e.g. the user can arbitrarily:
# set the parameters for the dynamics and objective function,
# obtain the analytical dynamics models, as well as the differentiations.
# define and modify the control cost function
# animate the motion of the system.

# Do NOT distribute without written permission from Wanxin Jin
# Do NOT use it for any commercial purpose

# Contact email: wanxinjin@gmail.com
# Last update: May. 15, 2020

#

'''

#!/usr/bin/env python3
import os
import sys
sys.path.append(os.getcwd()+'/lib')
from casadi import *
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as patches
from mpl_toolkits.mplot3d import Axes3D
import scipy.integrate as integrate
import mpl_toolkits.mplot3d.art3d as art3d
from matplotlib.patches import Circle, PathPatch
import math
import time
from dataclasses import dataclass, field
from QuadStates import QuadStates


# inverted pendulum
class SinglePendulum:
    def __init__(self, project_name='single pendlumn system'):
        self.project_name = project_name

    def initDyn(self, l=None, m=None, damping_ratio=None):
        # set parameter
        g = 10

        # declare system parameter
        parameter = []
        if l is None:
            self.l = SX.sym('l')
            parameter += [self.l]
        else:
            self.l = l

        if m is None:
            self.m = SX.sym('m')
            parameter += [self.m]
        else:
            self.m = m

        if damping_ratio is None:
            self.damping_ratio = SX.sym('damping_ratio')
            parameter += [self.damping_ratio]
        else:
            self.damping_ratio = damping_ratio

        self.dyn_auxvar = vcat(parameter)

        # set variable
        self.q, self.dq = SX.sym('q'), SX.sym('dq')
        self.X = vertcat(self.q, self.dq)
        U = SX.sym('u')
        self.U = U
        I = 1 / 3 * self.m * self.l * self.l
        self.f = vertcat(self.dq,
                         (self.U - self.m * g * self.l * sin(
                             self.q) - self.damping_ratio * self.dq) / I)  # continuous state-space representation

    def initCost(self, wq=None, wdq=None, wu=0.001):
        parameter = []
        if wq is None:
            self.wq = SX.sym('wq')
            parameter += [self.wq]
        else:
            self.wq = wq

        if wdq is None:
            self.wdq = SX.sym('wdq')
            parameter += [self.wdq]
        else:
            self.wdq = wdq

        self.cost_auxvar = vcat(parameter)

        # control goal
        x_goal = [math.pi, 0, 0, 0]

        # cost for q
        self.cost_q = (self.q - x_goal[0]) ** 2
        # cost for dq
        self.cost_dq = (self.dq - x_goal[1]) ** 2
        # cost for u
        self.cost_u = dot(self.U, self.U)

        self.path_cost = self.wq * self.cost_q + self.wdq * self.cost_dq + wu * self.cost_u
        self.final_cost = self.wq * self.cost_q + self.wdq * self.cost_dq

    def get_pendulum_position(self, len, state_traj):

        position = np.zeros((state_traj.shape[0], 2))
        for t in range(state_traj.shape[0]):
            q = state_traj[t, 0]
            pos_x = len * sin(q)
            pos_y = -len * cos(q)
            position[t, :] = np.array([pos_x, pos_y])
        return position

    def play_animation(self, len, dt, state_traj, state_traj_ref=None, save_option=0):

        # get the position of cart pole
        position = self.get_pendulum_position(len, state_traj)
        horizon = position.shape[0]
        if state_traj_ref is not None:
            position_ref = self.get_pendulum_position(len, state_traj_ref)
        else:
            position_ref = np.zeros_like(position)
        assert position.shape[0] == position_ref.shape[0], 'reference trajectory should have the same length'

        # set figure
        fig = plt.figure()
        ax = fig.add_subplot(111, autoscale_on=False, xlim=(-4, 4), ylim=(-4, 4), )
        ax.set_aspect('equal')
        ax.grid()
        ax.set_ylabel('Vertical (m)')
        ax.set_xlabel('Horizontal (m)')
        ax.set_title('Pendulum system')
        time_template = 'time = %.1fs'
        time_text = ax.text(0.05, 0.9, '', transform=ax.transAxes)

        # set lines
        cart_h, cart_w = 0.5, 1
        line, = ax.plot([], [], 'o-', lw=2)
        line_ref, = ax.plot([], [], color='lightgray', marker='o', lw=1)

        def init():
            line.set_data([], [])
            line_ref.set_data([], [])
            time_text.set_text('')
            return line, line_ref, time_text

        def animate(i):
            seg_x = [0, position[i, 0]]
            seg_y = [0, position[i, 1]]
            line.set_data(seg_x, seg_y)

            seg_x_ref = [0, position_ref[i, 0]]
            seg_y_ref = [0, position_ref[i, 1]]
            line_ref.set_data(seg_x_ref, seg_y_ref)

            time_text.set_text(time_template % (i * dt))

            return line, line_ref, time_text

        ani = animation.FuncAnimation(fig, animate, np.size(state_traj, 0),
                                      interval=50, init_func=init)

        if save_option != 0:
            Writer = animation.writers['ffmpeg']
            writer = Writer(fps=10, metadata=dict(artist='Me'), bitrate=-1)
            ani.save('Pendulum.mp4', writer=writer)
            print('save_success')

        plt.show()


# robot arm environment
class RobotArm:

    def __init__(self, project_name='two-link robot arm'):
        self.project_name = project_name

    def initDyn(self, l1=None, m1=None, l2=None, m2=None, g=10):

        # declare system parameters
        parameter = []
        if l1 is None:
            self.l1 = SX.sym('l1')
            parameter += [self.l1]
        else:
            self.l1 = l1

        if m1 is None:
            self.m1 = SX.sym('m1')
            parameter += [self.m1]
        else:
            self.m1 = m1

        if l2 is None:
            self.l2 = SX.sym('l2')
            parameter += [self.l2]
        else:
            self.l2 = l2

        if m2 is None:
            self.m2 = SX.sym('m2')
            parameter += [self.m2]
        else:
            self.m2 = m2

        self.dyn_auxvar = vcat(parameter)

        # set variable
        self.q1, self.dq1, self.q2, self.dq2 = SX.sym('q1'), SX.sym('dq1'), SX.sym('q2'), SX.sym('dq2')
        self.X = vertcat(self.q1, self.q2, self.dq1, self.dq2)
        u1, u2 = SX.sym('u1'), SX.sym('u2')
        self.U = vertcat(u1, u2)

        # Declare model equations (discrete-time)
        r1 = self.l1 / 2
        r2 = self.l2 / 2
        I1 = self.l1 * self.l1 * self.m1 / 12
        I2 = self.l2 * self.l2 * self.m2 / 12
        M11 = self.m1 * r1 * r1 + I1 + self.m2 * (self.l1 * self.l1 + r2 * r2 + 2 * self.l1 * r2 * cos(self.q2)) + I2
        M12 = self.m2 * (r2 * r2 + self.l1 * r2 * cos(self.q2)) + I2
        M21 = M12
        M22 = self.m2 * r2 * r2 + I2
        M = vertcat(horzcat(M11, M12), horzcat(M21, M22))
        h = self.m2 * self.l1 * r2 * sin(self.q2)
        C1 = -h * self.dq2 * self.dq2 - 2 * h * self.dq1 * self.dq2
        C2 = h * self.dq1 * self.dq1
        C = vertcat(C1, C2)
        G1 = self.m1 * r1 * g * cos(self.q1) + self.m2 * g * (r2 * cos(self.q1 + self.q2) + self.l1 * cos(self.q1))
        G2 = self.m2 * g * r2 * cos(self.q1 + self.q2)
        G = vertcat(G1, G2)
        ddq = mtimes(pinv(M), -C - G + self.U)  # joint acceleration
        self.f = vertcat(self.dq1, self.dq2, ddq)  # continuous state-space representation

    def initCost_WeightedDistance(self, wq1=None, wq2=None, wdq1=None, wdq2=None, wu=0.1):
        # declare system parameters
        parameter = []
        if wq1 is None:
            self.wq1 = SX.sym('wq1')
            parameter += [self.wq1]
        else:
            self.wq1 = wq1

        if wq2 is None:
            self.wq2 = SX.sym('wq2')
            parameter += [self.wq2]
        else:
            self.wq2 = wq2

        if wdq1 is None:
            self.wdq1 = SX.sym('wdq1')
            parameter += [self.wdq1]
        else:
            self.wdq1 = wdq1

        if wdq2 is None:
            self.wdq2 = SX.sym('wdq2')
            parameter += [self.wdq2]
        else:
            self.wdq2 = wdq2

        self.cost_auxvar = vcat(parameter)

        # control goal
        x_goal = [math.pi / 2, 0, 0, 0]

        # cost for q1
        self.cost_q1 = (self.q1 - x_goal[0]) ** 2
        # cost for q2
        self.cost_q2 = (self.q2 - x_goal[1]) ** 2
        # cost for dq1
        self.cost_dq1 = (self.dq1 - x_goal[2]) ** 2
        # cost for q2
        self.cost_dq2 = (self.dq2 - x_goal[3]) ** 2
        # cost for u
        self.cost_u = dot(self.U, self.U)

        self.path_cost = self.wq1 * self.cost_q1 + self.wq2 * self.cost_q2 + \
                         self.wdq1 * self.cost_dq1 + self.wdq2 * self.cost_dq2 + wu * self.cost_u
        self.final_cost = self.wq1 * self.cost_q1 + self.wq2 * self.cost_q2 + \
                          self.wdq1 * self.cost_dq1 + self.wdq2 * self.cost_dq2

    def initCost_Polynomial(self, wu=0.1):

        parameter = []

        #  goal state
        x_goal = [math.pi / 2, 0, 0, 0]
        # cost for q1
        self.cost_goal_q1 = (self.q1 - x_goal[0]) ** 2
        # cost for q2
        self.cost_goal_q2 = (self.q2 - x_goal[1]) ** 2
        # cost for dq1
        self.cost_goal_dq1 = (self.dq1 - x_goal[2]) ** 2
        # cost for q2
        self.cost_goal_dq2 = (self.dq2 - x_goal[3]) ** 2
        # cost for u
        self.cost_u = dot(self.U, self.U)

        # feature for q1
        self.w_q1_sq = SX.sym('w_q1_sq')
        self.feature_q1_sq = 0.5 * self.q1 * self.q1
        parameter += [self.w_q1_sq]
        self.w_q1 = SX.sym('w_q1')
        self.feature_q1 = self.q1
        parameter += [self.w_q1]

        # feature for q2
        self.w_q2_sq = SX.sym('w_q2_sq')
        self.feature_q2_sq = 0.5 * self.q2 * self.q2
        parameter += [self.w_q2_sq]
        self.w_q2 = SX.sym('w_q2')
        self.feature_q2 = self.q2
        parameter += [self.w_q2]

        self.path_cost = self.w_q1 * self.feature_q1 + self.w_q1_sq * self.feature_q1_sq + \
                         self.w_q2 * self.feature_q2 + self.w_q2_sq * self.feature_q2_sq + \
                         wu * self.cost_u
        self.final_cost = 100 * self.cost_goal_q1 + 100 * self.cost_goal_q2 + \
                          100 * self.cost_goal_dq1 + 100 * self.cost_goal_dq2

        self.cost_auxvar = vcat(parameter)

    def play_animation(self, l1, l2, dt, state_traj, state_traj_ref=None, save_option=0):

        # get the position of each link
        position = self.get_arm_position(l1, l2, state_traj)
        horizon = position.shape[0]

        if state_traj_ref is not None:
            position_ref = self.get_arm_position(l1, l2, state_traj_ref)
        else:
            position_ref = np.zeros_like(position)

        assert position.shape[0] == position_ref.shape[0], 'reference trajectory should have the same length'

        # set figure
        fig = plt.figure()
        ax = fig.add_subplot(111, autoscale_on=False, xlim=(-5, 5), ylim=(-5, 5), )
        ax.set_aspect('equal')
        ax.grid()
        ax.set_ylabel('Vertical (m)')
        ax.set_xlabel('Horizontal (m)')
        ax.set_title('Robot arm vertical reaching')
        time_template = 'time = %.1fs'
        time_text = ax.text(0.05, 0.9, '', transform=ax.transAxes)

        # set lines
        line, = ax.plot([], [], 'o-', lw=3)
        line_ref, = ax.plot([], [], color='lightgray', marker='o', lw=1)
        ax.plot(0, 2, 'r^')

        # ax.text(-2, 2.3, 'target end-effector position')

        def init():
            line.set_data([], [])
            line_ref.set_data([], [])
            time_text.set_text('')
            return line, line_ref, time_text

        def animate(i):
            seg_x = [0, position[i, 0], position[i, 2]]
            seg_y = [0, position[i, 1], position[i, 3]]
            line.set_data(seg_x, seg_y)

            seg_x_ref = [0, position_ref[i, 0], position_ref[i, 2]]
            seg_y_ref = [0, position_ref[i, 1], position_ref[i, 3]]
            line_ref.set_data(seg_x_ref, seg_y_ref)

            time_text.set_text(time_template % (i * dt))
            return line, line_ref, time_text

        ani = animation.FuncAnimation(fig, animate, horizon,
                                      interval=100, blit=True, init_func=init)

        # save
        if save_option != 0:
            Writer = animation.writers['ffmpeg']
            writer = Writer(fps=10, metadata=dict(artist='Me'), bitrate=-1)
            ani.save('robot_arm3.mp4', writer=writer)
            print('save_success')

        plt.show()

    def play_animation_ex(self, l1, l2, dt, state_traj, state_traj_ref=None, save_option=0, horizon=1):

        # plot
        params = {'axes.labelsize': 24,
                  'axes.titlesize': 24,
                  'xtick.labelsize': 24,
                  'ytick.labelsize': 24,
                  'legend.fontsize': 12}
        plt.rcParams.update(params)

        # get the position of each link
        position = self.get_arm_position(l1, l2, state_traj)
        horizon_step = position.shape[0]
        interval=float(horizon/horizon_step)

        # set figure
        # fig = plt.figure()
        fig = plt.figure(figsize=(8, 8))
        ax = fig.add_subplot(111, autoscale_on=False, )
        ax.set_aspect('equal')
        ax.grid()
        ax.set_ylabel('Y (m)')
        ax.set_xlabel('X (m)')
        ax.set_ylim(-3, 3)
        ax.set_xlim(-3, 3)
        ax.set_xticks(np.arange(-2, 2.1, 2))
        ax.set_yticks(np.arange(-2, 2.1, 2))
        ax.set_title('Control with learned objective function', pad=30)
        time_template = 'time = %.1fs'
        time_text = ax.text(0.05, 0.9, '', transform=ax.transAxes, fontsize=15)
        plt.subplots_adjust(top=0.90, bottom=0.12, left=0.16, right=0.90)

        q1 = -pi / 4
        q2 = 2 * pi / 3
        x1 = 1 * cos(q1)
        y1 = 1 * sin(q1)
        x2 = 1 * cos(q1 + q2) + x1
        y2 = 1 * sin(q1 + q2) + y1
        alpha = 0.5
        line_waypoint1,=ax.plot([ ], [ ], linewidth=15, marker='o', color='gray', markersize=20, markerfacecolor='black',
                markeredgecolor='red', markeredgewidth=5, zorder=100, alpha=alpha)
        line_waypoint2,=ax.plot([], [], linewidth=15, marker="o", color='gray', markersize=20, alpha=alpha)
        line_waypoint1.set_data([0, x1], [0, y1])
        line_waypoint2.set_data([x1, x2], [y1, y2])

        # set lines
        ax.scatter(0, 2, marker='*', s=500, color='red')
        ax.text(0, 2.3, 'Target', fontsize=18, color='red', weight='bold')
        ax.plot([1.5, 1.5], [-1, 1], linewidth=40, color='#D95319')
        ax.text(2., -.5, 'Obstacle', fontsize=18, rotation='vertical', c='#D95319', weight='bold')
        ax.scatter(0, 0, s=100, c='red')

        line1, = ax.plot([], [], linewidth=15, marker='o', color='#0072BD', markersize=20,markerfacecolor='black', markeredgecolor='red', markeredgewidth=5, zorder=10000, alpha=1)
        line2, = ax.plot([], [], linewidth=15, marker="o", color='#0072BD', markersize=20,alpha=1, zorder=1000)
        line3, = ax.plot([], [], color='#7E2F8E', linestyle='--', linewidth=2, alpha=0.7)
        line4, = ax.plot([], [], color='#7E2F8E', linestyle='--', linewidth=2, alpha=0.7)

        ax.plot([1.5, 1.5], [-1, 1], linewidth=10, color='#D95319')

        def init():
            line1.set_data([], [])
            line2.set_data([],[])
            line3.set_data([],[])
            line4.set_data([],[])
            time_text.set_text('')
            return line1, line2, line3, line4, time_text

        def animate(i):
            seg_x = [0, position[i, 0]]
            seg_y = [0, position[i, 1]]
            line1.set_data(seg_x, seg_y)
            seg_x = [position[i, 0], position[i, 2]]
            seg_y = [ position[i, 1], position[i, 3]]
            line2.set_data(seg_x, seg_y)
            line3.set_data(position[:i,2],position[:i,3])
            line4.set_data(position[:i,0],position[:i,1])



            time_text.set_text(time_template % (i * interval))
            return line1, line2, line3, line4, time_text

        ani = animation.FuncAnimation(fig, animate, horizon_step,
                                      interval=100, blit=True, init_func=init)

        # save
        if save_option != 0:
            Writer = animation.writers['ffmpeg']
            writer = Writer(fps=10, metadata=dict(artist='Me'), bitrate=-1)
            ani.save('robot_arm3.mp4', writer=writer, dpi=300)
            print('save_success')

        plt.show()

    def get_arm_position(self, l1, l2, state_traj):

        position = np.zeros((state_traj.shape[0], 4))
        for t in range(np.size(state_traj, 0)):
            q1 = state_traj[t, 0]
            q2 = state_traj[t, 1]
            x1 = l1 * cos(q1)
            y1 = l1 * sin(q1)
            x2 = l2 * cos(q1 + q2) + x1
            y2 = l2 * sin(q1 + q2) + y1
            position[t, :] = np.array(([x1, y1, x2, y2]))

        return position


# Cart Pole environment
class CartPole:

    def __init__(self, project_name='cart-pole-system'):
        self.project_name = project_name

    def initDyn(self, mc=None, mp=None, l=None):
        # set the global parameters
        g = 10

        # declare system parameters
        parameter = []
        if mc is None:
            self.mc = SX.sym('mc')
            parameter += [self.mc]
        else:
            self.mc = mc

        if mp is None:
            self.mp = SX.sym('mp')
            parameter += [self.mp]
        else:
            self.mp = mp
        if l is None:
            self.l = SX.sym('l')
            parameter += [self.l]
        else:
            self.l = l
        self.dyn_auxvar = vcat(parameter)

        # Declare system variables
        self.x, self.q, self.dx, self.dq = SX.sym('x'), SX.sym('q'), SX.sym('dx'), SX.sym('dq')
        self.X = vertcat(self.x, self.q, self.dx, self.dq)
        self.U = SX.sym('u')
        ddx = (self.U + self.mp * sin(self.q) * (self.l * self.dq * self.dq + g * cos(self.q))) / (
                self.mc + self.mp * sin(self.q) * sin(self.q))  # acceleration of x
        ddq = (-self.U * cos(self.q) - self.mp * self.l * self.dq * self.dq * sin(self.q) * cos(self.q) - (
                self.mc + self.mp) * g * sin(
            self.q)) / (
                      self.l * self.mc + self.l * self.mp * sin(self.q) * sin(self.q))  # acceleration of theta
        self.f = vertcat(self.dx, self.dq, ddx, ddq)  # continuous dynamics

    def initCost(self, wx=None, wq=None, wdx=None, wdq=None, wu=0.001):
        # declare system parameters
        parameter = []
        if wx is None:
            self.wx = SX.sym('wx')
            parameter += [self.wx]
        else:
            self.wx = wx

        if wq is None:
            self.wq = SX.sym('wq')
            parameter += [self.wq]
        else:
            self.wq = wq
        if wdx is None:
            self.wdx = SX.sym('wdx')
            parameter += [self.wdx]
        else:
            self.wdx = wdx

        if wdq is None:
            self.wdq = SX.sym('wdq')
            parameter += [self.wdq]
        else:
            self.wdq = wdq
        self.cost_auxvar = vcat(parameter)

        X_goal = [0.0, math.pi, 0.0, 0.0]

        self.path_cost = self.wx * (self.x - X_goal[0]) ** 2 + self.wq * (self.q - X_goal[1]) ** 2 + self.wdx * (
                self.dx - X_goal[2]) ** 2 + self.wdq * (
                                 self.dq - X_goal[3]) ** 2 + wu * (self.U * self.U)
        self.final_cost = self.wx * (self.x - X_goal[0]) ** 2 + self.wq * (self.q - X_goal[1]) ** 2 + self.wdx * (
                self.dx - X_goal[2]) ** 2 + self.wdq * (
                                  self.dq - X_goal[3]) ** 2  # final cost

    def play_animation(self, pole_len, dt, state_traj, state_traj_ref=None, save_option=0, title='Cart-pole system'):

        # get the position of cart pole
        position = self.get_cartpole_position(pole_len, state_traj)
        horizon = position.shape[0]
        if state_traj_ref is not None:
            position_ref = self.get_cartpole_position(pole_len, state_traj_ref)
            cart_h_ref, cart_w_ref = 0.5, 1
        else:
            position_ref = np.zeros_like(position)
            cart_h_ref, cart_w_ref = 0, 0
        assert position.shape[0] == position_ref.shape[0], 'reference trajectory should have the same length'

        # set figure
        fig = plt.figure()
        ax = fig.add_subplot(111, autoscale_on=False, xlim=(-10, 10), ylim=(-5, 5), )
        ax.set_aspect('equal')
        # ax.grid()
        ax.set_ylabel('Vertical (m)')
        ax.set_xlabel('Horizontal (m)')
        ax.set_title(title)
        # ax.tick_params(right= False,top= False,left= False, bottom= False, labelbottom=False, labelleft=False)
        time_template = 'time = %.1fs'
        time_text = ax.text(0.05, 0.9, '', transform=ax.transAxes)

        # set lines
        cart_h, cart_w = 0.5, 1
        line, = ax.plot([], [], lw=3)
        line_ref, = ax.plot([], [], color='gray', lw=3, alpha=0.3)
        patch = patches.Rectangle((0, 0), cart_w, cart_h, fc='y')
        patch_ref = patches.Rectangle((0, 0), cart_w_ref, cart_h_ref, fc='gray', alpha=0.3)

        # customize
        if state_traj_ref is not None:
            plt.legend([line, line_ref], ['learned', 'real'], ncol=1, loc='best',
                       bbox_to_anchor=(0.4, 0.4, 0.6, 0.6))

        def init():
            line.set_data([], [])
            line_ref.set_data([], [])
            ax.add_patch(patch)
            ax.add_patch(patch_ref)
            ax.axhline(lw=2, c='k')
            time_text.set_text('')
            return line, line_ref, patch, patch_ref, time_text

        def animate(i):
            seg_x = [position[i, 0], position[i, 2]]
            seg_y = [position[i, 1], position[i, 3]]
            line.set_data(seg_x, seg_y)

            seg_x_ref = [position_ref[i, 0], position_ref[i, 2]]
            seg_y_ref = [position_ref[i, 1], position_ref[i, 3]]
            line_ref.set_data(seg_x_ref, seg_y_ref)

            patch.set_xy([position[i, 0] - cart_w / 2, position[i, 1] - cart_h / 2])
            patch_ref.set_xy([position_ref[i, 0] - cart_w / 2, position_ref[i, 1] - cart_h / 2])

            time_text.set_text(time_template % (i * dt))

            return line, line_ref, patch, patch_ref, time_text

        ani = animation.FuncAnimation(fig, animate, np.size(state_traj, 0),
                                      interval=50, init_func=init)

        if save_option != 0:
            Writer = animation.writers['ffmpeg']
            writer = Writer(fps=10, metadata=dict(artist='Me'), bitrate=-1)
            ani.save(title + '.mp4', writer=writer, dpi=300)
            print('save_success')

        plt.show()

    def get_cartpole_position(self, pole_len, state_traj):
        position = np.zeros((state_traj.shape[0], 4))
        for t in range(state_traj.shape[0]):
            x = state_traj[t, 0]
            q = state_traj[t, 1]
            cart_pos_x = x
            cart_pos_y = 0
            pole_pos_x = x + pole_len * sin(q)
            pole_pos_y = -pole_len * cos(q)
            position[t, :] = np.array([cart_pos_x, cart_pos_y, pole_pos_x, pole_pos_y])
        return position

# quadrotor (UAV) environment
class Quadrotor:
    def __init__(self, project_name='my UAV'):
        self.project_name = 'my uav'

        # define the state of the quadrotor
        rx, ry, rz = SX.sym('rx'), SX.sym('ry'), SX.sym('rz')
        self.r_I = vertcat(rx, ry, rz)
        vx, vy, vz = SX.sym('vx'), SX.sym('vy'), SX.sym('vz')
        self.v_I = vertcat(vx, vy, vz)
        # quaternions attitude of B w.r.t. I
        q0, q1, q2, q3 = SX.sym('q0'), SX.sym('q1'), SX.sym('q2'), SX.sym('q3')
        self.q = vertcat(q0, q1, q2, q3)
        wx, wy, wz = SX.sym('wx'), SX.sym('wy'), SX.sym('wz')
        self.w_B = vertcat(wx, wy, wz)
        # define the quadrotor input
        f1, f2, f3, f4 = SX.sym('f1'), SX.sym('f2'), SX.sym('f3'), SX.sym('f4')
        self.T_B = vertcat(f1, f2, f3, f4)

    def initDyn(self, Jx=None, Jy=None, Jz=None, mass=None, l=None, c=None):
        # global parameter
        g = 9.81

        # parameters settings
        parameter = []
        if Jx is None:
            self.Jx = SX.sym('Jx')
            parameter += [self.Jx]
        else:
            self.Jx = Jx

        if Jy is None:
            self.Jy = SX.sym('Jy')
            parameter += [self.Jy]
        else:
            self.Jy = Jy

        if Jz is None:
            self.Jz = SX.sym('Jz')
            parameter += [self.Jz]
        else:
            self.Jz = Jz

        if mass is None:
            self.mass = SX.sym('mass')
            parameter += [self.mass]
        else:
            self.mass = mass

        if l is None:
            self.l = SX.sym('l')
            parameter += [self.l]
        else:
            self.l = l

        if c is None:
            self.c = SX.sym('c')
            parameter += [self.c]
        else:
            self.c = c

        self.dyn_auxvar = vcat(parameter)

        # Angular moment of inertia
        self.J_B = diag(vertcat(self.Jx, self.Jy, self.Jz))
        # Gravity
        self.g_I = vertcat(0, 0, -g)
        # Mass of rocket, assume is little changed during the landing process
        self.m = self.mass

        # total thrust in body frame
        thrust = self.T_B[0] + self.T_B[1] + self.T_B[2] + self.T_B[3]
        self.thrust_B = vertcat(0, 0, thrust)
        # total moment M in body frame
        Mx = -self.T_B[1] * self.l / 2 + self.T_B[3] * self.l / 2
        My = -self.T_B[0] * self.l / 2 + self.T_B[2] * self.l / 2
        Mz = (self.T_B[0] - self.T_B[1] + self.T_B[2] - self.T_B[3]) * self.c
        self.M_B = vertcat(Mx, My, Mz)

        # cosine directional matrix
        C_B_I = self.dir_cosine(self.q)  # inertial to body
        C_I_B = transpose(C_B_I)  # body to inertial

        # Newton's law
        dr_I = self.v_I
        dv_I = 1 / self.m * mtimes(C_I_B, self.thrust_B) + self.g_I
        # Euler's law
        dq = 1 / 2 * mtimes(self.omega(self.w_B), self.q)
        dw = mtimes(pinv(self.J_B), self.M_B - mtimes(mtimes(self.skew(self.w_B), self.J_B), self.w_B))

        self.X = vertcat(self.r_I, self.v_I, self.q, self.w_B)
        self.U = self.T_B
        self.f = vertcat(dr_I, dv_I, dq, dw)

    def initCost(self, QuadDesiredStates: QuadStates, wr=None, wv=None, wq=None, ww=None, wthrust=0.1):

        # load the goal states
        goal_r_I = np.array(QuadDesiredStates.position)
        goal_v_I = np.array(QuadDesiredStates.velocity)
        goal_q = QuadDesiredStates.attitude_quaternion
        goal_w_B = QuadDesiredStates.angular_velocity

        parameter = []
        if wr is None:
            self.wr = SX.sym('wr')
            parameter += [self.wr]
        else:
            self.wr = wr

        if wv is None:
            self.wv = SX.sym('wv')
            parameter += [self.wv]
        else:
            self.wv = wv

        if wq is None:
            self.wq = SX.sym('wq')
            parameter += [self.wq]
        else:
            self.wq = wq

        if ww is None:
            self.ww = SX.sym('ww')
            parameter += [self.ww]
        else:
            self.ww = ww

        self.cost_auxvar = vcat(parameter)

        # goal position in the world frame
        self.cost_r_I = dot(self.r_I - goal_r_I, self.r_I - goal_r_I)

        # goal velocity
        self.cost_v_I = dot(self.v_I - goal_v_I, self.v_I - goal_v_I)

        # final attitude error
        goal_R_B_I = self.dir_cosine(goal_q)
        R_B_I = self.dir_cosine(self.q)
        self.cost_q = trace(np.identity(3) - mtimes(transpose(goal_R_B_I), R_B_I))

        # auglar velocity cost
        self.cost_w_B = dot(self.w_B - goal_w_B, self.w_B - goal_w_B)

        # the thrust cost
        self.cost_thrust = dot(self.T_B, self.T_B)

        self.path_cost = self.wr * self.cost_r_I + \
                         self.wv * self.cost_v_I + \
                         self.ww * self.cost_w_B + \
                         self.wq * self.cost_q + \
                         wthrust * self.cost_thrust
        self.final_cost = self.wr * self.cost_r_I + \
                          self.wv * self.cost_v_I + \
                          self.ww * self.cost_w_B + \
                          self.wq * self.cost_q

    def initCost2(self, QuadDesiredStates: QuadStates, wthrust=0.1):

        # load the goal states
        goal_r_I = np.array(QuadDesiredStates.position)
        goal_v_I = np.array(QuadDesiredStates.velocity)
        goal_q = QuadDesiredStates.attitude_quaternion
        goal_w_B = QuadDesiredStates.angular_velocity

        parameter = []

        self.wrx = SX.sym('wrx')
        parameter += [self.wrx]
        self.wry = SX.sym('wry')
        parameter += [self.wry]
        self.wrz = SX.sym('wrz')
        parameter += [self.wrz]

        self.wvx = SX.sym('wvx')
        parameter += [self.wvx]
        self.wvy = SX.sym('wvy')
        parameter += [self.wvy]
        self.wvz = SX.sym('wvz')
        parameter += [self.wvz]

        self.wwx = SX.sym('wwx')
        parameter += [self.wwx]
        self.wwy = SX.sym('wwy')
        parameter += [self.wwy]
        self.wwz = SX.sym('wwz')
        parameter += [self.wwz]

        self.wq = SX.sym('wq')
        parameter += [self.wq]

        self.cost_auxvar = vcat(parameter)

        # goal position in the world frame
        self.cost_r_I_x = (self.r_I[0] - goal_r_I[0]) ** 2
        self.cost_r_I_y = (self.r_I[1] - goal_r_I[1]) ** 2
        self.cost_r_I_z = (self.r_I[2] - goal_r_I[2]) ** 2

        # goal velocity
        self.cost_v_I_x = (self.v_I[0] - goal_v_I[0]) ** 2
        self.cost_v_I_y = (self.v_I[1] - goal_v_I[1]) ** 2
        self.cost_v_I_z = (self.v_I[2] - goal_v_I[2]) ** 2

        # final attitude error
        goal_R_B_I = self.dir_cosine(goal_q)
        R_B_I = self.dir_cosine(self.q)
        self.cost_q = trace(np.identity(3) - mtimes(transpose(goal_R_B_I), R_B_I))

        # auglar velocity cost
        self.cost_w_B_x = (self.w_B[0] - goal_w_B[0]) ** 2
        self.cost_w_B_y = (self.w_B[1] - goal_w_B[1]) ** 2
        self.cost_w_B_z = (self.w_B[2] - goal_w_B[2]) ** 2

        # the thrust cost
        self.cost_thrust = dot(self.T_B, self.T_B)

        self.path_cost = self.wrx * self.cost_r_I_x + self.wry * self.cost_r_I_y + self.wrz * self.cost_r_I_z + \
                         self.wvx * self.cost_v_I_x + self.wvy * self.cost_v_I_y + self.wvz * self.cost_v_I_z + \
                         self.wwx * self.cost_w_B_x + self.wwy * self.cost_w_B_y + self.wwz * self.cost_w_B_z + \
                         self.wq * self.cost_q + \
                         wthrust * self.cost_thrust
        self.final_cost = self.wrx * self.cost_r_I_x + self.wry * self.cost_r_I_y + self.wrz * self.cost_r_I_z + \
                          self.wvx * self.cost_v_I_x + self.wvy * self.cost_v_I_y + self.wvz * self.cost_v_I_z + \
                          self.wwx * self.cost_w_B_x + self.wwy * self.cost_w_B_y + self.wwz * self.cost_w_B_z + \
                          self.wq * self.cost_q

    def initCost_Polynomial(self, QuadDesiredStates: QuadStates, w_thrust=0.1):

        # load the goal states
        goal_r_I = np.array(QuadDesiredStates.position)
        goal_v_I = np.array(QuadDesiredStates.velocity)
        goal_q = QuadDesiredStates.attitude_quaternion
        goal_w_B = QuadDesiredStates.angular_velocity

        parameter = []
        # goal aspect
        self.cost_goal_r = dot(self.r_I - goal_r_I, self.r_I - goal_r_I)

        # velocity aspect
        self.cost_goal_v = dot(self.v_I - goal_v_I, self.v_I - goal_v_I)

        # orientation aspect
        goal_R_B_I = self.dir_cosine(goal_q)
        R_B_I = self.dir_cosine(self.q)
        self.cost_goal_q = trace(np.identity(3) - mtimes(transpose(goal_R_B_I), R_B_I))

        # angular aspect
        self.cost_goal_w = dot(self.w_B - goal_w_B, self.w_B - goal_w_B)

        # thrust aspect
        self.cost_thrust = dot(self.T_B, self.T_B)

        # features for x
        self.w_xsq = SX.sym('w_xsq')
        self.feature_xsq = 0.5 * self.r_I[0] * self.r_I[0]
        parameter += [self.w_xsq]
        self.w_x = SX.sym('w_x')
        self.feature_x = self.r_I[0]
        parameter += [self.w_x]

        # features for y
        self.w_ysq = SX.sym('w_ysq')
        self.feature_ysq = 0.5 * self.r_I[1] * self.r_I[1]
        parameter += [self.w_ysq]
        self.w_y = SX.sym('w_y')
        self.feature_y = self.r_I[1]
        parameter += [self.w_y]

        # features for z
        self.w_zsq = SX.sym('w_zsq')
        self.feature_zsq = 0.5 * self.r_I[2] * self.r_I[2]
        parameter += [self.w_zsq]
        self.w_z = SX.sym('w_z')
        self.feature_z = self.r_I[2]
        parameter += [self.w_z]

        # # feature for xy
        # self.w_xy = SX.sym('w_xy')
        # self.feature_xy = self.r_I[0] * self.r_I[1]
        # parameter += [self.w_xy]

        self.path_cost = self.w_xsq * self.feature_xsq + self.w_x * self.feature_x + \
                         self.w_ysq * self.feature_ysq + self.w_y * self.feature_y + \
                         self.w_zsq * self.feature_zsq + self.w_z * self.feature_z + \
                         w_thrust * self.cost_thrust

        # tune weights for final cost
        self.final_cost = 1 * self.cost_goal_r + \
                          11 * self.cost_goal_v + \
                          100 * self.cost_goal_q + \
                          10 * self.cost_goal_w


        self.cost_auxvar = vcat(parameter)

    def get_quadrotor_position(self, wing_len, state_traj):

        # thrust_position in body frame
        r1 = vertcat(wing_len / 2, 0, 0)
        r2 = vertcat(0, -wing_len / 2, 0)
        r3 = vertcat(-wing_len / 2, 0, 0)
        r4 = vertcat(0, wing_len / 2, 0)

        # horizon
        horizon = np.size(state_traj, 0)
        position = np.zeros((horizon, 15))
        for t in range(horizon):
            # position of COM
            rc = state_traj[t, 0:3]
            # altitude of quaternion
            q = state_traj[t, 6:10]

            # q here is a 1D list, no matter which type state_traj is (numpy 2d array or 2d list)
            if abs(np.linalg.norm(q)) > 1e-6:
                q = np.array(q) / np.linalg.norm(q)

            # direction cosine matrix from body to inertial
            CIB = np.transpose(self.dir_cosine(q).full())

            # position of each rotor in inertial frame
            r1_pos = rc + mtimes(CIB, r1).full().flatten()
            r2_pos = rc + mtimes(CIB, r2).full().flatten()
            r3_pos = rc + mtimes(CIB, r3).full().flatten()
            r4_pos = rc + mtimes(CIB, r4).full().flatten()

            # store
            position[t, 0:3] = rc
            position[t, 3:6] = r1_pos
            position[t, 6:9] = r2_pos
            position[t, 9:12] = r3_pos
            position[t, 12:15] = r4_pos

        return position

    def play_animation(self, wing_len, state_traj, waypoints_animation: list, ObsList: list, space_limits: list,
                       file_name_prefix: str, save_option: bool, state_traj_ref=None, dt=0.1, title='UAV Maneuvering', horizon=1):

        # plot
        # params = {'axes.labelsize': 25,
        #           'axes.titlesize': 25,
        #           'xtick.labelsize': 20,
        #           'ytick.labelsize': 20,
        #           'legend.fontsize': 16}
        # plt.rcParams.update(params)

        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.set_xlabel('X (m)', fontsize=15, labelpad=15)
        ax.set_ylabel('Y (m)', fontsize=15, labelpad=15)
        ax.set_zlabel('Z (m)', fontsize=15, labelpad=15)
        self.set_axes_equal_all(ax, space_limits)
        ax.set_title('UAV manuvering', pad=15, fontsize=20)
        time_template = 'wrapped time = %.1fs'
        time_text = ax.text2D(0.20, 0.80, "time", transform=ax.transAxes, fontsize=15)

        # plot obstacles
        plot_linear_cube(ax, ObsList)

        # set legends
        colors = ["green", "violet", "blue"]
        marker_list = ["o", "o", "o"]
        labels = ["start", "goal", "waypoints"]
        def f(marker_type, color_type): return plt.plot([], [], marker=marker_type, color=color_type, ls="none")[0]
        handles = [f(marker_list[i], colors[i]) for i in range(len(labels))]

        # add legend about path
        handles.append(plt.plot([], [], c="C0", linewidth=2)[0])
        handles.append(patches.Patch(color="red", alpha=0.75))
        labels.extend(["Trajectory", "Obstacles"])
        plt.legend(handles, labels, bbox_to_anchor=(1, 1), loc='upper left', framealpha=1)

        # parse waypoints to plot, from start to goal
        ax.scatter(waypoints_animation[0][0], waypoints_animation[0][1], waypoints_animation[0][2], color="green")
        for i in range(1, len(waypoints_animation) - 1):
            ax.scatter(waypoints_animation[i][0], waypoints_animation[i][1], waypoints_animation[i][2], c="C0")
        ax.scatter(waypoints_animation[-1][0], waypoints_animation[-1][1], waypoints_animation[-1][2], color="violet")

        # fig = plt.figure(figsize=(7,6))
        # ax = fig.add_subplot(1, 1, 1, projection='3d', )
        # ax.set_xlabel('X', fontsize=40, labelpad=10)
        # ax.set_ylabel('Y', fontsize=40, labelpad=10)
        # ax.set_xticks([])
        # ax.set_yticks([])
        # ax.set_zticks([])
        # ax.set_ylim(-9, 9)
        # ax.set_xlim(-9, 9)
        # ax.set_xticks(np.arange(-8, 9, 4))
        # ax.set_yticks(np.arange(-8, 9, 8))
        # ax.tick_params(labelbottom=False, labelright=False, labelleft=False)
        # ax.view_init(elev=88, azim=-90)
        # ax.set_title('Top view', fontsize=40, pad=-25)
        # ax.set_position([-0.17, -0.12, 1.30, 1.15])
        # time_template = 'time = %.1fs'
        # time_text = ax.text2D(0.55, 0.20, "time", transform=ax.transAxes, fontsize=0)

        # fig = plt.figure(figsize=(7,6))
        # ax = fig.add_subplot(1, 1, 1, projection='3d', )
        # ax.set_xlabel('X', fontsize=40, labelpad=10)
        # ax.set_zlabel('Z', fontsize=40, labelpad=10)
        # ax.set_xticks([])
        # ax.set_yticks([])
        # ax.set_zticks([])
        # ax.set_ylim(-9, 9)
        # ax.set_xlim(-9, 9)
        # ax.set_zlim(0, 8)
        # ax.set_zticks(np.arange(0, 8, 2))
        # ax.set_xticks(np.arange(-8, 9, 4))
        # # ax.set_yticks(np.arange(-8, 9, 8))
        # ax.tick_params(labelbottom=False, labelright=False, labelleft=False)
        # # ax.view_init(elev=0, azim=-90)
        # ax.set_title('Front view', fontsize=40, pad=-25)
        # ax.set_position([-0.17, -0.12, 1.30, 1.15])
        # time_template = 'time = %.1fs'
        # time_text = ax.text2D(0.55, 0.20, "time", transform=ax.transAxes, fontsize=0)

        # draw the obstacles
        # bar2_back = ax.bar3d([-1], [-3], [0], dx=[0.5], dy=[0.5], dz=[4.5], color='#D95319')
        # bar2_top = ax.bar3d([-1], [-3], [4], dx=[0.5], dy=[-3.5], dz=[0.5], color='#D95319')
        # bar2_front = ax.bar3d([-1], [-6.5], [4.5], dx=[0.5], dy=[0.5], dz=[-4.5], color='#D95319')
        #
        # bar1_front = ax.bar3d([2.5], [2], [1.5], dx=[0.5], dy=[0.5], dz=[4.5], color='#D95319')
        # bar1_bottom = ax.bar3d([2.5], [2], [1.5], dx=[0.5], dy=[4.5], dz=[0.5], color='#D95319')
        # bar1_top = ax.bar3d([2.5], [2.5], [5.5], dx=[0.5], dy=[4.5], dz=[0.5], color='#D95319')
        # bar1_back = ax.bar3d([2.5], [6.5], [6.0], dx=[0.5], dy=[0.5], dz=[-4.5], color='#D95319')

        # data
        position = self.get_quadrotor_position(wing_len, state_traj)
        sim_horizon = np.size(position, 0)
        time_interval = float(horizon / sim_horizon)

        if state_traj_ref is None:
            position_ref = self.get_quadrotor_position(0, numpy.zeros_like(position))
        else:
            position_ref = self.get_quadrotor_position(wing_len, state_traj_ref)

        # animation
        line_traj, = ax.plot(position[:1, 0], position[:1, 1], position[:1, 2])
        c_x, c_y, c_z = position[0, 0:3]
        r1_x, r1_y, r1_z = position[0, 3:6]
        r2_x, r2_y, r2_z = position[0, 6:9]
        r3_x, r3_y, r3_z = position[0, 9:12]
        r4_x, r4_y, r4_z = position[0, 12:15]
        line_arm1, = ax.plot(np.array([c_x, r1_x]), np.array([c_y, r1_y]), np.array([c_z, r1_z]),
            linewidth=4, color='blue', marker='o', markersize=4, markerfacecolor='black')
        line_arm2, = ax.plot(np.array([c_x, r2_x]), np.array([c_y, r2_y]), np.array([c_z, r2_z]),
            linewidth=4, color='red', marker='o', markersize=4, markerfacecolor='black')
        line_arm3, = ax.plot(np.array([c_x, r3_x]), np.array([c_y, r3_y]), np.array([c_z, r3_z]),
            linewidth=4, color='blue', marker='o', markersize=4, markerfacecolor='black')
        line_arm4, = ax.plot(np.array([c_x, r4_x]), np.array([c_y, r4_y]), np.array([c_z, r4_z]),
            linewidth=4, color='red', marker='o', markersize=4, markerfacecolor='black')

        line_traj_ref, = ax.plot(position_ref[:1, 0], position_ref[:1, 1], position_ref[:1, 2], color='gray', alpha=0.5)
        c_x_ref, c_y_ref, c_z_ref = position_ref[0, 0:3]
        r1_x_ref, r1_y_ref, r1_z_ref = position_ref[0, 3:6]
        r2_x_ref, r2_y_ref, r2_z_ref = position_ref[0, 6:9]
        r3_x_ref, r3_y_ref, r3_z_ref = position_ref[0, 9:12]
        r4_x_ref, r4_y_ref, r4_z_ref = position_ref[0, 12:15]
        line_arm1_ref, = ax.plot(np.array([c_x_ref, r1_x_ref]), np.array([c_y_ref, r1_y_ref]), np.array([c_z_ref, r1_z_ref]),
            linewidth=2, color='gray', marker='o', markersize=3, alpha=0.7)
        line_arm2_ref, = ax.plot(np.array([c_x_ref, r2_x_ref]), np.array([c_y_ref, r2_y_ref]), np.array([c_z_ref, r2_z_ref]),
            linewidth=2, color='gray', marker='o', markersize=3, alpha=0.7)
        line_arm3_ref, = ax.plot(np.array([c_x_ref, r3_x_ref]), np.array([c_y_ref, r3_y_ref]), np.array([c_z_ref, r3_z_ref]),
            linewidth=2, color='gray', marker='o', markersize=3, alpha=0.7)
        line_arm4_ref, = ax.plot(np.array([c_x_ref, r4_x_ref]), np.array([c_y_ref, r4_y_ref]), np.array([c_z_ref, r4_z_ref]),
            linewidth=2, color='gray', marker='o', markersize=3, alpha=0.7)

        # customize
        if state_traj_ref is not None:
            plt.legend([line_traj, line_traj_ref], ['learned', 'OC solver'], ncol=1, loc='best',
                       bbox_to_anchor=(0.35, 0.25, 0.5, 0.5))

        def update_traj(num):

            # customize
            time_text.set_text(time_template % (num * time_interval))

            # trajectory
            line_traj.set_data(position[:num, 0], position[:num, 1])
            line_traj.set_3d_properties(position[:num, 2])

            # uav
            c_x, c_y, c_z = position[num, 0:3]
            r1_x, r1_y, r1_z = position[num, 3:6]
            r2_x, r2_y, r2_z = position[num, 6:9]
            r3_x, r3_y, r3_z = position[num, 9:12]
            r4_x, r4_y, r4_z = position[num, 12:15]

            line_arm1.set_data(np.array([c_x, r1_x]), np.array([c_y, r1_y]))
            line_arm1.set_3d_properties([c_z, r1_z])

            line_arm2.set_data(np.array([c_x, r2_x]), np.array([c_y, r2_y]))
            line_arm2.set_3d_properties([c_z, r2_z])

            line_arm3.set_data(np.array([c_x, r3_x]), np.array([c_y, r3_y]))
            line_arm3.set_3d_properties([c_z, r3_z])

            line_arm4.set_data(np.array([c_x, r4_x]), np.array([c_y, r4_y]))
            line_arm4.set_3d_properties([c_z, r4_z])

            # trajectory ref
            num = sim_horizon - 1
            line_traj_ref.set_data(position_ref[:num, 0], position_ref[:num, 1])
            line_traj_ref.set_3d_properties(position_ref[:num, 2])

            # uav ref
            c_x_ref, c_y_ref, c_z_ref = position_ref[num, 0:3]
            r1_x_ref, r1_y_ref, r1_z_ref = position_ref[num, 3:6]
            r2_x_ref, r2_y_ref, r2_z_ref = position_ref[num, 6:9]
            r3_x_ref, r3_y_ref, r3_z_ref = position_ref[num, 9:12]
            r4_x_ref, r4_y_ref, r4_z_ref = position_ref[num, 12:15]

            line_arm1_ref.set_data(np.array([c_x_ref, r1_x_ref]), np.array([c_y_ref, r1_y_ref]))
            line_arm1_ref.set_3d_properties([c_z_ref, r1_z_ref])

            line_arm2_ref.set_data(np.array([c_x_ref, r2_x_ref]), np.array([c_y_ref, r2_y_ref]))
            line_arm2_ref.set_3d_properties([c_z_ref, r2_z_ref])

            line_arm3_ref.set_data(np.array([c_x_ref, r3_x_ref]), np.array([c_y_ref, r3_y_ref]))
            line_arm3_ref.set_3d_properties([c_z_ref, r3_z_ref])

            line_arm4_ref.set_data(np.array([c_x_ref, r4_x_ref]), np.array([c_y_ref, r4_y_ref]))
            line_arm4_ref.set_3d_properties([c_z_ref, r4_z_ref])

            return line_traj, line_arm1, line_arm2, line_arm3, line_arm4, \
                   line_traj_ref, line_arm1_ref, line_arm2_ref, line_arm3_ref, line_arm4_ref, time_text

        ani = animation.FuncAnimation(fig, update_traj, sim_horizon, interval=80, blit=True, cache_frame_data=False)

        if save_option == True:
            Writer = animation.writers['ffmpeg']
            writer = Writer(fps=10, metadata=dict(artist='Me'), bitrate=-1)
            ani.save(file_name_prefix + '.gif', writer=writer, dpi=300)
        plt.show()

    def dir_cosine(self, q):
        C_B_I = vertcat(
            horzcat(1 - 2 * (q[2] ** 2 + q[3] ** 2), 2 * (q[1] * q[2] + q[0] * q[3]), 2 * (q[1] * q[3] - q[0] * q[2])),
            horzcat(2 * (q[1] * q[2] - q[0] * q[3]), 1 - 2 * (q[1] ** 2 + q[3] ** 2), 2 * (q[2] * q[3] + q[0] * q[1])),
            horzcat(2 * (q[1] * q[3] + q[0] * q[2]), 2 * (q[2] * q[3] - q[0] * q[1]), 1 - 2 * (q[1] ** 2 + q[2] ** 2))
        )
        return C_B_I

    def skew(self, v):
        v_cross = vertcat(
            horzcat(0, -v[2], v[1]),
            horzcat(v[2], 0, -v[0]),
            horzcat(-v[1], v[0], 0)
        )
        return v_cross

    def omega(self, w):
        omeg = vertcat(
            horzcat(0, -w[0], -w[1], -w[2]),
            horzcat(w[0], 0, w[2], -w[1]),
            horzcat(w[1], -w[2], 0, w[0]),
            horzcat(w[2], w[1], -w[0], 0)
        )
        return omeg

    def quaternion_mul(self, p, q):
        return vertcat(p[0] * q[0] - p[1] * q[1] - p[2] * q[2] - p[3] * q[3],
                       p[0] * q[1] + p[1] * q[0] + p[2] * q[3] - p[3] * q[2],
                       p[0] * q[2] - p[1] * q[3] + p[2] * q[0] + p[3] * q[1],
                       p[0] * q[3] + p[1] * q[2] - p[2] * q[1] + p[3] * q[0]
                       )


    def set_axes_equal_all(self, ax, space_limits: list):
        '''
        Make axes of 3D plot have equal scale so that spheres appear as spheres,
        cubes as cubes, etc..  This is one possible solution to Matplotlib's
        ax.set_aspect('equal') and ax.axis('equal') not working for 3D.
        Reference: https://stackoverflow.com/questions/13685386/matplotlib-equal-unit-length-with-equal-aspect-ratio-z-axis-is-not-equal-to

        Input
        ax: a matplotlib axis, e.g., as output from plt.gca().
        '''

        x_limits = space_limits[0]
        y_limits = space_limits[1]
        z_limits = space_limits[2]

        x_range = abs(x_limits[1] - x_limits[0])
        x_middle = np.mean(x_limits)
        y_range = abs(y_limits[1] - y_limits[0])
        y_middle = np.mean(y_limits)
        z_range = abs(z_limits[1] - z_limits[0])
        z_middle = np.mean(z_limits)

        # The plot bounding box is a sphere in the sense of the infinity
        # norm, hence I call half the max range the plot radius.
        plot_radius = 0.5*max([x_range, y_range, z_range])

        ax.set_xlim3d([x_middle - plot_radius, x_middle + plot_radius])
        ax.set_ylim3d([y_middle - plot_radius, y_middle + plot_radius])
        ax.set_zlim3d([z_middle - plot_radius, z_middle + plot_radius])



# Rocket environment
class Rocket:
    def __init__(self, project_name='rocket powered landing'):
        self.project_name = project_name

        # define the rocket states
        rx, ry, rz = SX.sym('rx'), SX.sym('ry'), SX.sym('rz')
        self.r_I = vertcat(rx, ry, rz)
        vx, vy, vz = SX.sym('vx'), SX.sym('vy'), SX.sym('vz')
        self.v_I = vertcat(vx, vy, vz)
        # quaternions attitude of B w.r.t. I
        q0, q1, q2, q3 = SX.sym('q0'), SX.sym('q1'), SX.sym('q2'), SX.sym('q3')
        self.q = vertcat(q0, q1, q2, q3)
        wx, wy, wz = SX.sym('wx'), SX.sym('wy'), SX.sym('wz')
        self.w_B = vertcat(wx, wy, wz)
        # define the rocket input
        ux, uy, uz = SX.sym('ux'), SX.sym('uy'), SX.sym('uz')
        self.T_B = vertcat(ux, uy, uz)

    def initDyn(self, Jx=None, Jy=None, Jz=None, mass=None, l=None):
        # global parameter
        g = 10

        # parameters settings
        parameter = []
        if Jx is None:
            self.Jx = SX.sym('Jx')
            parameter += [self.Jx]
        else:
            self.Jx = Jx

        if Jy is None:
            self.Jy = SX.sym('Jy')
            parameter += [self.Jy]
        else:
            self.Jy = Jy

        if Jz is None:
            self.Jz = SX.sym('Jz')
            parameter += [self.Jz]
        else:
            self.Jz = Jz

        if mass is None:
            self.mass = SX.sym('mass')
            parameter += [self.mass]
        else:
            self.mass = mass

        if l is None:
            self.l = SX.sym('l')
            parameter += [self.l]
        else:
            self.l = l

        self.dyn_auxvar = vcat(parameter)

        # Angular moment of inertia
        self.J_B = diag(vertcat(self.Jx, self.Jy, self.Jz))
        # Gravity
        self.g_I = vertcat(-g, 0, 0)
        # Vector from thrust point to CoM
        self.r_T_B = vertcat(-self.l / 2, 0, 0)
        # Mass of rocket, assume is little changed during the landing process
        self.m = self.mass

        C_B_I = self.dir_cosine(self.q)
        C_I_B = transpose(C_B_I)

        dr_I = self.v_I
        dv_I = 1 / self.m * mtimes(C_I_B, self.T_B) + self.g_I

        dq = 1 / 2 * mtimes(self.omega(self.w_B), self.q)
        dw = mtimes(pinv(self.J_B),
                    mtimes(self.skew(self.r_T_B), self.T_B) -
                    mtimes(mtimes(self.skew(self.w_B), self.J_B), self.w_B))

        self.X = vertcat(self.r_I, self.v_I, self.q, self.w_B)
        self.U = self.T_B
        self.f = vertcat(dr_I, dv_I, dq, dw)

    def initCost(self, wr=None, wv=None, wtilt=None, ww=None, wsidethrust=None, wthrust=1.0):

        parameter = []
        if wr is None:
            self.wr = SX.sym('wr')
            parameter += [self.wr]
        else:
            self.wr = wr

        if wv is None:
            self.wv = SX.sym('wv')
            parameter += [self.wv]
        else:
            self.wv = wv

        if wtilt is None:
            self.wtilt = SX.sym('wtilt')
            parameter += [self.wtilt]
        else:
            self.wtilt = wtilt

        if wsidethrust is None:
            self.wsidethrust = SX.sym('wsidethrust')
            parameter += [self.wsidethrust]
        else:
            self.wsidethrust = wsidethrust

        if ww is None:
            self.ww = SX.sym('ww')
            parameter += [self.ww]
        else:
            self.ww = ww

        self.cost_auxvar = vcat(parameter)

        # goal position in the world frame
        goal_r_I = np.array([0, 0, 0])
        self.cost_r_I = dot(self.r_I - goal_r_I, self.r_I - goal_r_I)

        # goal velocity
        goal_v_I = np.array([0, 0, 0])
        self.cost_v_I = dot(self.v_I - goal_v_I, self.v_I - goal_v_I)

        # tilt angle upward direction of rocket should be close to upward of earth
        C_I_B = transpose(self.dir_cosine(self.q))
        nx = np.array([1., 0., 0.])
        ny = np.array([0., 1., 0.])
        nz = np.array([0., 0., 1.])
        proj_ny = dot(ny, mtimes(C_I_B, nx))
        proj_nz = dot(nz, mtimes(C_I_B, nx))
        self.cost_tilt = proj_ny ** 2 + proj_nz ** 2

        # the sides of the thrust should be zeros
        self.cost_side_thrust = (self.T_B[1] ** 2 + self.T_B[2] ** 2)

        # the thrust cost
        self.cost_thrust = dot(self.T_B, self.T_B)

        # auglar velocity cost
        goal_w_B = np.array([0, 0, 0])
        self.cost_w_B = dot(self.w_B - goal_w_B, self.w_B - goal_w_B)

        self.path_cost = self.wr * self.cost_r_I + \
                         self.wv * self.cost_v_I + \
                         self.ww * self.cost_w_B + \
                         self.wtilt * self.cost_tilt + \
                         self.wsidethrust * self.cost_side_thrust + \
                         wthrust * self.cost_thrust
        self.final_cost = self.wr * self.cost_r_I + \
                          self.wv * self.cost_v_I + \
                          self.ww * self.cost_w_B + \
                          self.wtilt * self.cost_tilt

    def initCost2(self, wthrust=0.1):
        parameter = []
        self.wrx = SX.sym('wrx')
        parameter += [self.wrx]
        self.wry = SX.sym('wry')
        parameter += [self.wry]
        self.wrz = SX.sym('wrz')
        parameter += [self.wrz]

        self.wvx = SX.sym('wvx')
        parameter += [self.wvx]
        self.wvy = SX.sym('wvy')
        parameter += [self.wvy]
        self.wvz = SX.sym('wvz')
        parameter += [self.wvz]

        self.wwx = SX.sym('wwx')
        parameter += [self.wwx]
        self.wwy = SX.sym('wwy')
        parameter += [self.wwy]
        self.wwz = SX.sym('wwz')
        parameter += [self.wwz]

        self.wsidethrust = SX.sym('wsidethrust')
        parameter += [self.wsidethrust]

        self.wtilt = SX.sym('wtilt')
        parameter += [self.wtilt]
        self.cost_auxvar = vcat(parameter)

        # goal position in the world frame
        goal_r_I = np.array([0, 0, 0])
        self.cost_r_I_x = (self.r_I[0] - goal_r_I[0]) ** 2
        self.cost_r_I_y = (self.r_I[1] - goal_r_I[1]) ** 2
        self.cost_r_I_z = (self.r_I[2] - goal_r_I[2]) ** 2

        # goal velocity
        goal_v_I = np.array([0, 0, 0])
        self.cost_v_I_x = (self.v_I[0] - goal_v_I[0]) ** 2
        self.cost_v_I_y = (self.v_I[1] - goal_v_I[1]) ** 2
        self.cost_v_I_z = (self.v_I[2] - goal_v_I[2]) ** 2

        # tilt angle upward direction of rocket should be close to upward of earth
        C_I_B = transpose(self.dir_cosine(self.q))
        nx = np.array([1., 0., 0.])
        ny = np.array([0., 1., 0.])
        nz = np.array([0., 0., 1.])
        proj_ny = dot(ny, mtimes(C_I_B, nx))
        proj_nz = dot(nz, mtimes(C_I_B, nx))
        self.cost_tilt = proj_ny ** 2 + proj_nz ** 2

        # the sides of the thrust should be zeros
        self.cost_side_thrust = (self.T_B[1] ** 2 + self.T_B[2] ** 2)

        # the thrust cost
        self.cost_thrust = dot(self.T_B, self.T_B)

        # auglar velocity cost
        goal_w_B = np.array([0, 0, 0])
        self.cost_w_B_x = (self.w_B[0] - goal_w_B[0]) ** 2
        self.cost_w_B_y = (self.w_B[1] - goal_w_B[1]) ** 2
        self.cost_w_B_z = (self.w_B[2] - goal_w_B[2]) ** 2

        self.path_cost = self.wrx * self.cost_r_I_x + self.wry * self.cost_r_I_y + self.wrz * self.cost_r_I_z + \
                         self.wvx * self.cost_v_I_x + self.wvy * self.cost_v_I_y + self.wvz * self.cost_v_I_z + \
                         self.wwx * self.cost_w_B_x + self.wwy * self.cost_w_B_y + self.wwz * self.cost_w_B_z + \
                         self.wtilt * self.cost_tilt + \
                         self.wsidethrust * self.cost_side_thrust + \
                         wthrust * self.cost_thrust
        self.final_cost = self.wrx * self.cost_r_I_x + self.wry * self.cost_r_I_y + self.wrz * self.cost_r_I_z + \
                          self.wvx * self.cost_v_I_x + self.wvy * self.cost_v_I_y + self.wvz * self.cost_v_I_z + \
                          self.wwx * self.cost_w_B_x + self.wwy * self.cost_w_B_y + self.wwz * self.cost_w_B_z + \
                          self.wtilt * self.cost_tilt

    def initCost_Ex(self, wthrust=0.1):

        parameter = []

        self.wrx = SX.sym('wrx')
        parameter += [self.wrx]
        self.wry = SX.sym('wry')
        parameter += [self.wry]
        self.wrz = SX.sym('wrz')
        parameter += [self.wrz]

        self.wvx = SX.sym('wvx')
        parameter += [self.wvx]
        self.wvy = SX.sym('wvy')
        parameter += [self.wvy]
        self.wvz = SX.sym('wvz')
        parameter += [self.wvz]

        self.wwx = SX.sym('wwx')
        parameter += [self.wwx]
        self.wwy = SX.sym('wwy')
        parameter += [self.wwy]
        self.wwz = SX.sym('wwz')
        parameter += [self.wwz]

        self.wtilt = SX.sym('wtilt')
        parameter += [self.wtilt]

        self.wsidethrust = SX.sym('wsidethrust')
        parameter += [self.wsidethrust]

        self.cost_auxvar = vcat(parameter)

        # goal position in the world frame
        goal_r_I = np.array([0, 0, 0])
        self.cost_r_I_x = (self.r_I[0] - goal_r_I[0]) ** 2
        self.cost_r_I_y = (self.r_I[1] - goal_r_I[1]) ** 2
        self.cost_r_I_z = (self.r_I[2] - goal_r_I[2]) ** 2

        # goal velocity
        goal_v_I = np.array([0, 0, 0])
        self.cost_v_I_x = (self.v_I[0] - goal_v_I[0]) ** 2
        self.cost_v_I_y = (self.v_I[1] - goal_v_I[1]) ** 2
        self.cost_v_I_z = (self.v_I[2] - goal_v_I[2]) ** 2

        # auglar velocity cost
        goal_w_B = np.array([0, 0, 0])
        self.cost_w_B_x = (self.w_B[0] - goal_w_B[0]) ** 2
        self.cost_w_B_y = (self.w_B[1] - goal_w_B[1]) ** 2
        self.cost_w_B_z = (self.w_B[2] - goal_w_B[2]) ** 2

        # tilt angle upward direction of rocket should be close to upward of earth
        C_I_B = transpose(self.dir_cosine(self.q))
        nx = np.array([1., 0., 0.])
        ny = np.array([0., 1., 0.])
        nz = np.array([0., 0., 1.])
        proj_ny = dot(ny, mtimes(C_I_B, nx))
        proj_nz = dot(nz, mtimes(C_I_B, nx))
        self.cost_tilt = proj_ny ** 2 + proj_nz ** 2

        # the sides of the thrust should be zeros
        self.cost_side_thrust = (self.T_B[1] ** 2 + self.T_B[2] ** 2)

        # the thrust cost
        self.cost_thrust = dot(self.T_B, self.T_B)

        self.path_cost = self.wrx * self.cost_r_I_x + self.wry * self.cost_r_I_y + self.wrz * self.cost_r_I_z + \
                         self.wvx * self.cost_v_I_x + self.wvy * self.cost_v_I_y + self.wvz * self.cost_v_I_z + \
                         self.wwx * self.cost_w_B_x + self.wwy * self.cost_w_B_y + self.wwz * self.cost_w_B_z + \
                         self.wtilt * self.cost_tilt + \
                         self.wsidethrust * self.cost_side_thrust + \
                         wthrust * self.cost_thrust
        self.final_cost = self.wrx * self.cost_r_I_x + self.wry * self.cost_r_I_y + self.wrz * self.cost_r_I_z + \
                          self.wvx * self.cost_v_I_x + self.wvy * self.cost_v_I_y + self.wvz * self.cost_v_I_z + \
                          self.wwx * self.cost_w_B_x + self.wwy * self.cost_w_B_y + self.wwz * self.cost_w_B_z + \
                          self.wtilt * self.cost_tilt + \
                          self.wsidethrust * self.cost_side_thrust

    def dir_cosine(self, q):
        C_B_I = vertcat(
            horzcat(1 - 2 * (q[2] ** 2 + q[3] ** 2), 2 * (q[1] * q[2] + q[0] * q[3]), 2 * (q[1] * q[3] - q[0] * q[2])),
            horzcat(2 * (q[1] * q[2] - q[0] * q[3]), 1 - 2 * (q[1] ** 2 + q[3] ** 2), 2 * (q[2] * q[3] + q[0] * q[1])),
            horzcat(2 * (q[1] * q[3] + q[0] * q[2]), 2 * (q[2] * q[3] - q[0] * q[1]), 1 - 2 * (q[1] ** 2 + q[2] ** 2))
        )
        return C_B_I

    def skew(self, v):
        v_cross = vertcat(
            horzcat(0, -v[2], v[1]),
            horzcat(v[2], 0, -v[0]),
            horzcat(-v[1], v[0], 0)
        )
        return v_cross

    def omega(self, w):
        omeg = vertcat(
            horzcat(0, -w[0], -w[1], -w[2]),
            horzcat(w[0], 0, w[2], -w[1]),
            horzcat(w[1], -w[2], 0, w[0]),
            horzcat(w[2], w[1], -w[0], 0)
        )
        return omeg

    def play_animation(self, rocket_len, state_traj, control_traj, state_traj_ref=None, control_traj_ref=None,
                       save_option=0, dt=0.1,
                       title='Rocket Powered Landing'):
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.set_xlabel('East (m)')
        ax.set_ylabel('North (m)')
        ax.set_zlabel('Upward (m)')
        ax.set_zlim(0, 10)
        ax.set_ylim(-8, 8)
        ax.set_xlim(-8, 8)
        ax.set_title(title, pad=20, fontsize=15)

        # target landing point
        p = Circle((0, 0), 3, color='g', alpha=0.3)
        ax.add_patch(p)
        art3d.pathpatch_2d_to_3d(p, z=0, zdir="z")

        # data
        position = self.get_rocket_body_position(rocket_len, state_traj, control_traj)
        sim_horizon = np.size(position, 0)
        for t in range(np.size(position, 0)):
            x = position[t, 0]
            if x < 0:
                sim_horizon = t
                break
        # animation
        line_traj, = ax.plot(position[:1, 1], position[:1, 2], position[:1, 0])
        xg, yg, zg, xh, yh, zh, xf, yf, zf = position[0, 3:]
        line_rocket, = ax.plot([yg, yh], [zg, zh], [xg, xh], linewidth=5, color='black')
        line_force, = ax.plot([yg, yf], [zg, zf], [xg, xf], linewidth=2, color='red')

        # reference data
        if state_traj_ref is None or control_traj_ref is None:
            position_ref = numpy.zeros_like(position)
            sim_horizon_ref = sim_horizon
        else:
            position_ref = self.get_rocket_body_position(rocket_len, state_traj_ref, control_traj_ref)
            sim_horizon_ref = np.size((position_ref, 0))
            for t in range(np.size(position_ref, 0)):
                x = position_ref[t, 0]
                if x < 0:
                    sim_horizon_ref = t
                    break
        # animation
        line_traj_ref, = ax.plot(position_ref[:1, 1], position_ref[:1, 2], position_ref[:1, 0], linewidth=2,
                                 color='gray', alpha=0.5)
        xg_ref, yg_ref, zg_ref, xh_ref, yh_ref, zh_ref, xf_ref, yf_ref, zf_ref = position_ref[0, 3:]
        line_rocket_ref, = ax.plot([yg_ref, yh_ref], [zg_ref, zh_ref], [xg_ref, xh_ref], linewidth=5, color='gray',
                                   alpha=0.5)
        line_force_ref, = ax.plot([yg_ref, yf_ref], [zg_ref, zf_ref], [xg_ref, xf_ref], linewidth=2, color='red',
                                  alpha=0.2)

        # time label
        time_template = 'time = %.1fs'
        time_text = ax.text2D(0.66, 0.55, "time", transform=ax.transAxes)
        # time_text = ax.text2D(0.66, 0.65, "time", transform=ax.transAxes)
        # time_text = ax.text2D(0.50, 0.65, "time", transform=ax.transAxes)

        # customize
        if state_traj_ref is not None or control_traj_ref is not None:
            plt.legend([line_traj, line_traj_ref], ['learned', 'truth'], ncol=1, loc='best',
                       bbox_to_anchor=(0.35, 0.25, 0.5, 0.5))

        def update_traj(num):
            # customize
            time_text.set_text(time_template % (num * dt))

            # trajectory
            if num > sim_horizon:
                t = sim_horizon
            else:
                t = num
            line_traj.set_data(position[:t, 1], position[:t, 2])
            line_traj.set_3d_properties(position[:t, 0])

            # rocket
            xg, yg, zg, xh, yh, zh, xf, yf, zf = position[t, 3:]
            line_rocket.set_data([yg, yh], [zg, zh])
            line_rocket.set_3d_properties([xg, xh])
            line_force.set_data([yg, yf], [zg, zf])
            line_force.set_3d_properties([xg, xf])

            # reference
            if num > sim_horizon_ref:
                t_ref = sim_horizon_ref
            else:
                t_ref = num
            line_traj_ref.set_data(position_ref[:t_ref, 1], position_ref[:t_ref, 2])
            line_traj_ref.set_3d_properties(position_ref[:t_ref, 0])

            # rocket
            xg_ref, yg_ref, zg_ref, xh_ref, yh_ref, zh_ref, xf_ref, yf_ref, zf_ref = position_ref[num, 3:]
            line_rocket_ref.set_data([yg_ref, yh_ref], [zg_ref, zh_ref])
            line_rocket_ref.set_3d_properties([xg_ref, xh_ref])
            line_force_ref.set_data([yg_ref, yf_ref], [zg_ref, zf_ref])
            line_force_ref.set_3d_properties([xg_ref, xf_ref])

            return line_traj, line_rocket, line_force, line_traj_ref, line_rocket_ref, line_force_ref, time_text

        ani = animation.FuncAnimation(fig, update_traj, max(sim_horizon, sim_horizon_ref), interval=20, blit=True)

        if save_option != 0:
            Writer = animation.writers['ffmpeg']
            writer = Writer(fps=10, metadata=dict(artist='Me'), bitrate=-1)
            ani.save(title + '.mp4', writer=writer, dpi=300)
            print('save_success')

        plt.show()

    def get_rocket_body_position(self, rocket_len, state_traj, control_traj):

        # thrust_position in body frame
        r_T_B = vertcat(-rocket_len / 2, 0, 0)

        # horizon
        horizon = np.size(control_traj, 0)
        # for normalization in the plot
        norm_f = np.linalg.norm(control_traj, axis=1);
        max_f = np.amax(norm_f)
        position = np.zeros((horizon, 12))
        for t in range(horizon):
            # position of COM
            rc = state_traj[t, 0:3]
            # altitude of quaternion
            q = state_traj[t, 6:10]
            q = q / np.linalg.norm(q)
            # thrust force
            f = control_traj[t, 0:3]

            # direction cosine matrix from body to inertial
            CIB = np.transpose(self.dir_cosine(q).full())

            # position of gimbal point (rocket tail)
            rg = rc + mtimes(CIB, r_T_B).full().flatten()
            # position of rocket tip
            rh = rc - mtimes(CIB, r_T_B).full().flatten()

            # direction of force
            df = np.dot(CIB, f) / max_f
            rf = rg - df

            # store
            position[t, 0:3] = rc
            position[t, 3:6] = rg
            position[t, 6:9] = rh
            position[t, 9:12] = rf

        return position


# converter to quaternion from (angle, direction)
def toQuaternion(angle, dir):
    if type(dir) == list:
        dir = numpy.array(dir)
    dir = dir / numpy.linalg.norm(dir)
    quat = numpy.zeros(4)
    quat[0] = math.cos(angle / 2)
    quat[1:] = math.sin(angle / 2) * dir
    return quat.tolist()


# normalized verctor
def normalizeVec(vec):
    if type(vec) == list:
        vec = np.array(vec)
    vec = vec / np.linalg.norm(vec)
    return vec


def quaternion_conj(q):
    conj_q = q
    conj_q[1] = -q[1]
    conj_q[2] = -q[2]
    conj_q[3] = -q[3]
    return conj_q

def plot_linear_cube(ax_3d, ObsList: list, color='red', alpha=0.75):
    """
    Plot obstacles in 3D space.
    """

    # plot obstacles
    num_obs = len(ObsList)
    if num_obs > 0:
        for i in range(0, num_obs):
            x = ObsList[i].center[0] - 0.5 * ObsList[i].length
            y = ObsList[i].center[1] - 0.5 * ObsList[i].width
            z = ObsList[i].center[2] - 0.5 * ObsList[i].height

            dx = ObsList[i].length
            dy = ObsList[i].width
            dz = ObsList[i].height

            xx = [x, x, x+dx, x+dx, x]
            yy = [y, y+dy, y+dy, y, y]
            kwargs = {'alpha': alpha, 'color': color}
            ax_3d.plot3D(xx, yy, [z]*5, **kwargs)
            ax_3d.plot3D(xx, yy, [z+dz]*5, **kwargs)
            ax_3d.plot3D([x, x], [y, y], [z, z+dz], **kwargs)
            ax_3d.plot3D([x, x], [y+dy, y+dy], [z, z+dz], **kwargs)
            ax_3d.plot3D([x+dx, x+dx], [y+dy, y+dy], [z, z+dz], **kwargs)
            ax_3d.plot3D([x+dx, x+dx], [y, y], [z, z+dz], **kwargs)
