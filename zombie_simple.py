import logging
import os
import sys
import pathlib
import time
from datetime import datetime
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


##################################################
#   Global Definitions
##################################################
#----- Program Config -----#
# Global unique run ID
RUN_ID = datetime.now().strftime('%Y%m%d%H%M%S')

# RUN_ID file
RUN_ID_FILE = pathlib.Path('.', 'RUN_ID')

# Stages
# TODO
#   Set to `False` to opt out a stage
# -- Simulation Stage
EN_SIM = True
# -- Plotting Stage
EN_PLOT = True

# Output folder:
# TODO
#   The output folder can be changed.
OUT_FOLDER = pathlib.Path(pathlib.Path.cwd(), 'out', RUN_ID)
if not OUT_FOLDER.exists():
    OUT_FOLDER.mkdir(parents=True)
else:
    raise Exception('Output Folder %s already existed.' % OUT_FOLDER)

# Config summary file
CONFIG_SUM_FILE = pathlib.Path(OUT_FOLDER, 'config_%s.json' % RUN_ID)

# Output files
# Format of CSV:
#   - No header.
#   - Fields: Time, Agent ID, State, Energy
H_PROF_FMT = 'h_prof_%s.csv'
D_PROF_FMT = 'd_prof_%s.csv'
Z_PROF_FMT = 'z_prof_%s.csv'

H_PROF_FILE = pathlib.Path(OUT_FOLDER, H_PROF_FMT % RUN_ID)
D_PROF_FILE = pathlib.Path(OUT_FOLDER, D_PROF_FMT % RUN_ID)
Z_PROF_FILE = pathlib.Path(OUT_FOLDER, Z_PROF_FMT % RUN_ID)

# Log level
# TODO
#   Adjust the log level according to your need.
# LOG_LEVEL = logging.DEBUG
LOG_LEVEL = logging.INFO

# Log file
# TODO
#   Set to 'None' to disable log file.
LOG_FILE = pathlib.Path(OUT_FOLDER, '%s.log' % RUN_ID)

#----- Game Config -----#
# Max iterations
# TODO
#   Change it.
MAX_ITER = 2000

# Total number of agents
# TODO
#   Change it.
NUM_AGENTS = 500

# Agent types
HUMAN = 1
DOCTOR = 2
ZOMBIE = 4

# Number of neighbors for each agent
# TODO
#   Change it.
#   NOTE: Only applicable to cases of a constant number of neighbors.
NUM_NEIG = 10

# Probabilities of agents
# TODO
#   Change them.
H_PROB = 0.3
D_PROB = 0.3
Z_PROB = 0.4

# Initial energies
# TODO
#   Change them.
H_ENERGY = 100
D_ENERGY = 100
Z_ENERGY = 80

# Agent states
ALIVE = 1
INFECTED = 2
DEAD = 4

# TODO
#   Change the following parameters.
#----- Zombie Config -----#
BITE_PROB = 0.5
# The energy increase from a bite.
BITE_GAIN = 10
# The energy change of being a Zombie
Z_DECAY = -1

#----- Human Config -----#
# The energy change caused by a bite.
BITE_HURT = -5
# The energy change due to the infection.
H_DECAY = -1
# The energy increase due to the healing.
LIFE_GAIN = 1

#----- Doctor Config -----#
BITE_EFF = 5


##################################################
#   Simulation Class Definition
##################################################
class ZombieGameSim:
    # The list of Humans.
    m_l_humans = None
    m_l_doctors = None
    m_l_zombies = None
    # The current moment
    m_cur_moment = None
    # Logger
    m_logger = None

    def __init__(self):
        # Generate the counts of agents.
        nd_agent_cnt = np.random.multinomial(NUM_AGENTS, pvals=[H_PROB, D_PROB, Z_PROB])
        # Create humans
        h_start_id = 0
        self.m_l_humans = [Human(h_start_id + i, H_ENERGY, self) for i in range(nd_agent_cnt[0])]
        # Create doctors
        d_start_id = len(self.m_l_humans)
        self.m_l_doctors = [Doctor(d_start_id + i, D_ENERGY, self) for i in range(nd_agent_cnt[1])]
        # Create zombies
        z_start_id = d_start_id + len(self.m_l_doctors)
        self.m_l_zombies = [Zombie(z_start_id + i, Z_ENERGY, self) for i in range(nd_agent_cnt[2])]
        # Initialize logger
        self.m_logger = GameLog(self)
        self.m_logger.config_summary()
        self.m_logger.info('%s Humans, %s Doctors, and %s Zombies have joined the game.'
                      % (len(self.m_l_humans), len(self.m_l_doctors), len(self.m_l_zombies)))

    def start(self):
        self.m_logger.info('Game Started...')
        # Simulation iterations
        start_time = time.time()
        self.m_cur_moment = 0
        while True:
            if self.m_cur_moment >= MAX_ITER:
                break
            # TODO
            #   The order of updates matters!
            #   This order can be customized. Though, changing the order may lead to significantly different results.
            for human in self.m_l_humans:
                human.update()
                human.profile()
            for doctor in self.m_l_doctors:
                doctor.update()
                doctor.profile()
            for zombie in self.m_l_zombies:
                zombie.update()
                zombie.profile()
            self.m_cur_moment += 1
            if self.m_cur_moment % 100 == 0:
                self.m_logger.info('Elapse: %s' % (time.time() - start_time))

        # Output time series of profiles
        self.__output_ts_profile()

        # Output RUN_ID
        with open(RUN_ID_FILE, 'w') as out_fd:
            out_fd.write(RUN_ID)
        self.m_logger.info('Game Over. Overall Elapse: %s' % (time.time() - start_time))

    def __output_ts_profile(self):
        """
        Output three time series profile data files for Humans, Doctors, and Zombies respectively.
        Each file is a 2D-ndarray.
        :return: None.
        """
        self.m_logger.info('Output starts...')
        start_time = time.time()
        l_h_ts_prof = [human.get_ts_profile() for human in self.m_l_humans]
        nd_h_ts_prof = np.concatenate(l_h_ts_prof, axis=0, dtype=np.int16)
        np.savetxt(H_PROF_FILE, nd_h_ts_prof, delimiter=',')
        l_d_ts_prof = [doctor.get_ts_profile() for doctor in self.m_l_doctors]
        nd_d_ts_prof = np.concatenate(l_d_ts_prof, axis=0, dtype=np.int16)
        np.savetxt(D_PROF_FILE, nd_d_ts_prof, delimiter=',')
        l_z_ts_prof = [zombie.get_ts_profile() for zombie in self.m_l_zombies]
        nd_z_ts_prof = np.concatenate(l_z_ts_prof, axis=0, dtype=np.int16)
        np.savetxt(Z_PROF_FILE, nd_z_ts_prof, delimiter=',', fmt=['%d', '%d', '%d', '%d'])
        self.m_logger.info('Output done in %s sec.' % (time.time() - start_time))

    def get_all_humans(self):
        return self.m_l_humans

    def get_all_doctors(self):
        return self.m_l_doctors

    def get_all_zombies(self):
        return self.m_l_zombies

    def get_cur_moment(self):
        return self.m_cur_moment



##################################################
#   Agent Class Definitions
##################################################
class AbsAgent:
    # Agent unique ID
    m_agent_id = None
    # Agent role
    m_role = None
    # Agent state
    m_state = None
    # Agent full energy
    m_full_energy = None
    # Agent energy
    m_energy = None
    # The reference of ZombieGameSim
    m_ref_sim = None
    # The time series of profiles of this agent.
    m_ts_profile = None
    # The logger
    m_logger = None

    def __init__(self, agent_id, init_energy, ref_sim):
        """
        Constructor.
        :param agent_id: (int) >=0 Unique agent ID.
        :param init_energy: (int) >0 Initial energy for this agent.
        :param ref_sim: (ZombieGameSim) The reference of the instance of ZombieGameSim.
        """
        # TODO
        #   If anything needs to be initialized.
        self.m_agent_id = agent_id
        self.m_state = ALIVE
        if init_energy <= 0:
            self.m_logger.error('`init_energy` needs to be a positive integer.')
            return
        self.m_full_energy = init_energy
        self.m_energy = init_energy
        if ref_sim is None or not isinstance(ref_sim, ZombieGameSim):
            self.m_logger.error('`ref_sim` needs to be an instance of `ZombieGameSim`.')
        self.m_ref_sim = ref_sim
        self.m_ts_profile = []
        self.m_logger = GameLog(ref_sim)

    def _set_role(self, role):
        """
        Set the agent role. Every child class needs to set this.
        :param role: (int) Agent type, taking values from the global agent types.
        :return: None
        """
        if role is None or type(role) != int or role & (HUMAN|DOCTOR|ZOMBIE) == 0:
            self.m_logger.error('`role`:%s is invalid.' % role)
            return
        self.m_role = role

    def get_role(self):
        return self.m_role

    def get_agent_id(self):
        return self.m_agent_id

    def get_state(self):
        return self.m_state

    def _change_state(self, new_state):
        if new_state is None or type(new_state) != int or new_state < ALIVE or new_state > DEAD:
            self.m_logger.error('`new_state` = %s is invalid!' % new_state)
            return
        self.m_state = new_state

    def get_energy(self):
        return self.m_energy

    def _change_energy(self, energy_change):
        """
        Update the energy of this agent if it can be applied. Also, update the agent state if necessary.
        :param energy_change: (int) Positive integers for life gain, and negative integers for life decay.
        :return: None.
        """
        if self.get_state() == DEAD:
            return
        if energy_change is None or type(energy_change) != int or not np.isfinite(energy_change):
            self.m_logger.error('`energy_change` = %s is invalid!' % energy_change)
            return

        new_energy = self.get_energy() + energy_change
        if new_energy < 0:
            new_energy = 0
        elif new_energy > self.get_full_energy():
            new_energy = self.get_full_energy()

        self.m_energy = new_energy

        if self.get_energy() == 0:
            self._change_state(DEAD)

    def get_full_energy(self):
        return self.m_full_energy

    def _get_life_decay_amount(self):
        """
        The amount of energy to be decreased.
        :return: (int) <= 0.
        """
        return H_DECAY

    def life_decay(self):
        """
        Decrease agent's energy.
        :return: None.
        """
        self._change_energy(self._get_life_decay_amount())

    def _get_life_gain_amount(self):
        """
        The amount of energy to be increased.
        :return: (int) >= 0
        """
        # TODO
        #   Could be more fun.
        return LIFE_GAIN

    def life_gain(self):
        """
        Increase agent's energy.
        :return: None.
        """
        self._change_energy(self._get_life_gain_amount())

    def __get_num_neig(self):
        """
        Update the desired number of neighbors for this agent.
        :return: (int) The number of neighbors.
        """
        # TODO
        #   Could be more fun.
        return NUM_NEIG

    def _select_neighbors(self, agent_type=HUMAN|DOCTOR|ZOMBIE):
        """
        Randomly select a specific number of agents as the neighbors.
        :return: (list of agent instances) The current neighbors.
        """
        if agent_type is None or type(agent_type) != int:
            self.m_logger.error('`agent_type`:%s is invalid!' % agent_type)
            return

        num_neig = self.__get_num_neig()
        l_agents = []
        if agent_type & HUMAN > 0:
            l_agents += self.m_ref_sim.get_all_humans()
        if agent_type & DOCTOR > 0:
            l_agents += self.m_ref_sim.get_all_doctors()
        if agent_type & ZOMBIE > 0:
            l_agents += self.m_ref_sim.get_all_zombies()

        if len(l_agents) <= 0:
            self.m_logger.error('`agent_type`:%s corresponds to no agents!' % agent_type)
            return

        l_neig_idx = np.random.choice(list(range(len(l_agents))), size=num_neig)
        l_neig = [l_agents[idx] for idx in range(len(l_agents)) if idx in l_neig_idx]
        np.random.shuffle(l_neig)
        return l_neig

    def update(self):
        """
        Update the state as well as the energy, if necessary.
        :return: None.
        """
        # TODO
        #   Override this function.
        pass

    def _profile_to_str(self):
        role = self.get_role()
        role_str = None
        if role == HUMAN:
            role_str = 'H'
        elif role == DOCTOR:
            role_str = 'D'
        elif role == ZOMBIE:
            role_str = 'Z'

        state = self.get_state()
        state_str = None
        if state == ALIVE:
            state_str = 'A'
        elif state == INFECTED:
            state_str = 'I'
        elif state == DEAD:
            state_str = 'D'
        return '(ID:%s R:%s S:%s E:%s/%s)' % (self.get_agent_id(), role_str, state_str, self.get_energy(),
                                              self.get_full_energy())

    def profile(self):
        """
        Profile the status of this agent at the current moment.
        Append an 1D-ndarray to `m_ts_profile`.
        Profile Format: [Time, Agent ID, State, Energy]
        :return: None.
        """
        nd_prof = np.array([self.m_ref_sim.get_cur_moment(), self.m_agent_id, self.m_state, self.m_energy],
                           dtype=np.int16)
        self.m_ts_profile.append(nd_prof)

    def get_ts_profile(self):
        """
        Output the time series of profiles.
        :return: (2D-ndarray) Row: Profile at each time point.
        """
        if self.m_ts_profile is None:
            self.m_logger.error('No profile yet.')
            return
        return np.array(self.m_ts_profile, dtype=np.int16)

class Human(AbsAgent):
    def __init__(self, agent_id, init_energy, ref_sim):
        super().__init__(agent_id, init_energy, ref_sim)
        self._set_role(HUMAN)

    def bitten(self, zombie):
        """
        If this human is ALIVE, change its state to INFECTED, and decay its life.
        :param zombie: (Zombie) The Zombie who bit this Human.
        :return: None
        """
        if self.get_state() == ALIVE:
            self.m_logger.debug('Bitten %s by %s' % (self._profile_to_str(), zombie._profile_to_str()))
            self._change_state(INFECTED)
            self.get_state()

    def treated(self, doctor):
        """
        Treated by a Doctor. Change the state back to ALIVE, and gain an energy increase.
        :param doctor: (Doctor) The Doctor who treated this Human.
        :return: None.
        """
        if self.get_state() == INFECTED:
            self.m_logger.debug('Treated %s by %s' % (self._profile_to_str(), doctor._profile_to_str()))
            self._change_state(ALIVE)
            self._healing()

    def _healing(self):
        if self.get_state() == ALIVE and self.get_energy() < self.get_full_energy():
            self.life_gain()
            self.m_logger.debug('Healing %s' % self._profile_to_str())

    def _degenerating(self):
        if self.get_state() == INFECTED:
            self.life_decay()
            self.m_logger.debug('Degenerating %s' % self._profile_to_str())

    def update(self):
        """
        Update the state and energy of this agent.
        :return: None.
        """
        self._degenerating()
        self._healing()


class Doctor(Human):
    # The moment a bite becomes effective.
    m_bite_start = None

    def __init__(self, agent_id, init_energy, ref_sim):
        super().__init__(agent_id, init_energy, ref_sim)
        self._set_role(DOCTOR)

    def bitten(self, zombie):
        """
        Record the moment of a bite.
        :return: None.
        """
        super().bitten(zombie)
        self.m_bite_start = self.m_ref_sim.get_cur_moment()

    def cure(self):
        """
        Randomly select an infected Human neighbor, and treat it.
        :return: None.
        """
        if self.get_state() == DEAD:
            return

        l_neig = self._select_neighbors(HUMAN)
        for neig in l_neig:
            if neig.get_state() == INFECTED:
                self.m_logger.debug('%s treated %s. Neighbors: %s'
                                    % (self._profile_to_str(), neig._profile_to_str(),
                                       [a._profile_to_str() for a in l_neig]))
                neig.treated(self)
                break

    def update(self):
        # Check if it will treat itself.
        if self.get_state() == INFECTED:
            cur_moment = self.m_ref_sim.get_cur_moment()
            bite_len = cur_moment - self.m_bite_start
            if bite_len > BITE_EFF:
                self.m_logger.debug('Treated itself %s' % self._profile_to_str())
                self.treated(self)
                self.m_bite_start = None
        super().update()
        self.cure()


class Zombie(AbsAgent):
    def __init__(self, agent_id, init_energy, ref_sim):
        super().__init__(agent_id, init_energy, ref_sim)
        self._set_role(ZOMBIE)

    def _get_life_decay_amount(self):
        # TODO
        #   Could be more fun.
        return Z_DECAY

    def _get_life_gain_amount(self):
        # TODO
        #   Could be more fun.
        return BITE_GAIN

    def _evolved(self):
        # TODO
        #   Could be more fun.
        # Gain some energy from the bite.
        self.life_gain()
        self.m_logger.debug('Evolved %s' % self._profile_to_str())

    def _degenerating(self):
        self.life_decay()
        self.m_logger.debug('Degenerating %s' % self._profile_to_str())

    def bite(self):
        """
        Randomly select an alive Human/Doctor neighbor, and bite it with a probability.
        :return: None.
        """
        if self.get_state() == DEAD:
            return

        # Succeeds by chance.
        bite_success = np.random.binomial(n=1, p=BITE_PROB)
        if bite_success == 0:
            self.m_logger.debug('Bite failed %s' % self._profile_to_str())
            return

        l_neig = self._select_neighbors(HUMAN|DOCTOR)
        for neig in l_neig:
            if neig.get_state() != ALIVE:
                continue
            self.m_logger.debug('%s bit %s. Neighbors: %s'
                                % (self._profile_to_str(), neig._profile_to_str(),
                                   [a._profile_to_str() for a in l_neig]))
            neig.bitten(self)
            self._evolved()
            break

    def update(self):
        # TODO
        #   Could be more fun.
        self.bite()
        self._degenerating()


##################################################
#   Utility Classes
##################################################
class GameLog:
    m_ref_sim = None

    def __init__(self, ref_sim):
        if LOG_FILE is not None:
            logging.basicConfig(filename=LOG_FILE, format='%(message)s', level=LOG_LEVEL)
        else:
            logging.basicConfig(format='%(message)s', level=LOG_LEVEL)
        self.m_ref_sim = ref_sim

    def config_summary(self):
        """
        Summarize all configurations in a JSON file.
        :return: None.
        """
        d_config = {
            'MAX_ITER': MAX_ITER,
            'NUM_AGENTS': NUM_AGENTS,
            'NUM_NEIG': NUM_NEIG,
            'H_PROB': H_PROB,
            'D_PROB': D_PROB,
            'Z_PROB': Z_PROB,
            'H_ENERGY': H_ENERGY,
            'D_ENERGY': D_ENERGY,
            'Z_ENERGY': Z_ENERGY,
            'BITE_PROB': BITE_PROB,
            'BITE_GAIN': BITE_GAIN,
            'Z_DECAY': Z_DECAY,
            'BITE_HURT': BITE_HURT,
            'H_DECAY': H_DECAY,
            'LIFE_GAIN': LIFE_GAIN,
            'BITE_EFF': BITE_EFF
        }
        with open(CONFIG_SUM_FILE, 'w') as out_fd:
            json.dump(d_config, out_fd, indent=4)
        logging.info('Log [GameLog:config_summary] Done writing config summary file: %s' % CONFIG_SUM_FILE)

    def __compose_log(self, msg):
        class_name = sys._getframe(2).f_locals['self'].__class__.__name__ \
            if 'self' in sys._getframe(2).f_locals else None
        func_name = sys._getframe(2).f_code.co_name
        full_func_name = '%s:%s' % (class_name, func_name) if class_name is not None else func_name
        if self.m_ref_sim.get_cur_moment() is None:
            log_str = 'Init [%s] %s' % (full_func_name, msg)
        else:
            log_str = 'T:%s [%s] %s' % (self.m_ref_sim.get_cur_moment(), full_func_name, msg)
        return log_str

    def debug(self, msg):
        logging.debug(self.__compose_log(msg))

    def info(self, msg):
        logging.info(self.__compose_log(msg))

    def error(self, msg):
        logging.error(self.__compose_log(msg))


class GamePlot:
    def load_ts_profiles(self, run_id):
        """
        Load time series of profiles for Human, Doctor, and Zombie.
        :param run_id: (int) Given run ID.
        :return: (DataFrame, DataFrame, DataFrame) for Human, Doctor, and Zombie respectively.
            Columns: 'tick', 'aid', 'state', 'energy'
        """
        h_ts_prof_file = pathlib.Path(OUT_FOLDER, H_PROF_FMT % run_id)
        if not pathlib.Path(h_ts_prof_file).exists():
            logging.error('Plot [GamePlot:load_ts_profiles] No Human profile file for `run_id`: %s' % run_id)
            return
        col_names = ['tick', 'aid', 'state', 'energy']
        df_h_ts_prof = pd.read_csv(h_ts_prof_file, names=col_names, dtype={col:np.int16 for col in col_names})

        d_ts_prof_file = pathlib.Path(OUT_FOLDER, D_PROF_FMT % run_id)
        if not pathlib.Path(d_ts_prof_file).exists():
            logging.error('Plot [GamePlot:load_ts_profiles] No Doctor profile file for `run_id`: %s' % run_id)
            return
        df_d_ts_prof = pd.read_csv(d_ts_prof_file, names=col_names, dtype={col:np.int16 for col in col_names})

        z_ts_prof_file = pathlib.Path(OUT_FOLDER, Z_PROF_FMT % run_id)
        if not pathlib.Path(z_ts_prof_file).exists():
            logging.error('Plot [GamePlot:load_ts_profiles] No Zombie profile file for `run_id`: %s' % run_id)
            return
        df_z_ts_prof = pd.read_csv(z_ts_prof_file, names=col_names, dtype={col:np.int16 for col in col_names})
        return df_h_ts_prof, df_d_ts_prof, df_z_ts_prof

    def plot_ts_state(self, run_id, title_prefix, df_ts_state, states=ALIVE|INFECTED|DEAD, out_folder=None):
        logging.info('Plot [GamePlot:plot_ts_state] Starts...')
        nd_tick = np.array(sorted(list(set(df_ts_state['tick']))))
        l_ts_alive = []
        l_ts_infected = []
        l_ts_dead = []

        l_states = []
        if states & ALIVE != 0:
            l_states.append(ALIVE)
        if states & INFECTED != 0:
            l_states.append(INFECTED)
        if states & DEAD:
            l_states.append(DEAD)

        for tick in nd_tick:
            all_state_cnts = df_ts_state[df_ts_state['tick'] == tick]['state'].value_counts()
            if states & ALIVE != 0:
                if ALIVE in all_state_cnts:
                    l_ts_alive.append(all_state_cnts[ALIVE])
                else:
                    l_ts_alive.append(0)
            if states & INFECTED != 0:
                if INFECTED in all_state_cnts:
                    l_ts_infected.append(all_state_cnts[INFECTED])
                else:
                    l_ts_infected.append(0)
            if states & DEAD:
                if DEAD in all_state_cnts:
                    l_ts_dead.append(all_state_cnts[DEAD])
                else:
                    l_ts_dead.append(0)

        fig, ax = plt.subplots()
        width = np.round(1 / (max(l_states).bit_length() + 2), decimals=2)
        fig_width = len(nd_tick) * (len(l_states) + 2) * width
        if fig_width > 20:
            fig_width = 20
        fig.set_figwidth(fig_width)
        offset = 0
        if states & ALIVE != 0:
            ax.bar(nd_tick + offset, l_ts_alive, width=width, label='ALIVE')
            offset += width
        if states & INFECTED != 0:
            ax.bar(nd_tick + offset, l_ts_infected, width=width, label='INFECTED')
            offset += width
        if states & DEAD != 0:
            ax.bar(nd_tick + offset, l_ts_dead, width=width, label='DEAD')
        # ax.set_xticks(nd_tick)
        ax.set_ylim(0, max(l_ts_alive) + 2)
        ax.legend(ncols=3)
        ax.set_title('%s %s' % (title_prefix, run_id))

        if out_folder is not None and os.path.exists(out_folder):
            out_name = pathlib.Path(out_folder, '%s_%s.png' % ('_'.join(title_prefix.split()), run_id))
            plt.savefig(out_name, format='png')
            logging.info('Plot [GamePlot:plot_ts_state] Done output figure: %s' % out_name.name)
        else:
            plt.show()


##################################################
#   Simulation Main Body
##################################################
if __name__ == '__main__':
    if EN_SIM:
        ins_game = ZombieGameSim()
        ins_game.start()

    if EN_PLOT:
        with open(RUN_ID_FILE, 'r') as in_fd:
            run_id = in_fd.readline().strip()
        ins_plot = GamePlot()
        df_h_ts_prof, df_d_ts_prof, df_z_ts_prof = ins_plot.load_ts_profiles(run_id)
        title_prefix = 'HUMAN STATE TIME SERIES'
        ins_plot.plot_ts_state(run_id, title_prefix, df_h_ts_prof, states=ALIVE|INFECTED|DEAD, out_folder=OUT_FOLDER)
        title_prefix = 'DOCTOR STATE TIME SERIES'
        ins_plot.plot_ts_state(run_id, title_prefix, df_d_ts_prof, states=ALIVE|INFECTED|DEAD, out_folder=OUT_FOLDER)
        title_prefix = 'ZOMBIE STATE TIME SERIES'
        ins_plot.plot_ts_state(run_id, title_prefix, df_z_ts_prof, states=ALIVE|DEAD, out_folder=OUT_FOLDER)

