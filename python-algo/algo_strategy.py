import gamelib
import random
import math
import warnings
from sys import maxsize
import json


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.
Advanced strategy tips:
  - You can analyze action frames by modifying on_action_frame function
  - The GameState.map object can be manually manipulated to create hypothetical
  board states. Though, we recommended making a copy of the map to preserve
  the actual current map state.
"""

counter = 2
cycle = 0
enemy_change = False
last_breach = False
last_index = 0
breachnum = 0
last_hp = 30

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """
        Read in config and perform any initial setup here
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global FILTER, ENCRYPTOR, DESTRUCTOR, PING, EMP, SCRAMBLER, BITS, CORES
        FILTER = config["unitInformation"][0]["shorthand"]
        ENCRYPTOR = config["unitInformation"][1]["shorthand"]
        DESTRUCTOR = config["unitInformation"][2]["shorthand"]
        PING = config["unitInformation"][3]["shorthand"]
        EMP = config["unitInformation"][4]["shorthand"]
        SCRAMBLER = config["unitInformation"][5]["shorthand"]
        BITS = 1
        CORES = 0
        # This is a good place to do initial setup
        self.scored_on_locations = []

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        self.strategy(game_state)

        game_state.submit_turn()


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """

    def strategy(self, game_state):
        """
        For defense we will use a spread out layout and some Scramblers early on.
        We will place destructors near locations the opponent managed to score on.
        For offense we will use long range EMPs if they place stationary units near the enemy's front.
        If there are no stationary units to attack in the front, we will send Pings to try and score quickly.
        """
        global cycle, counter
        # First, place basic defenses
        self.build_defences(game_state)
        # Now build reactive defenses based on where the enemy scored
        self.build_reactive_defense(game_state)

        # If the turn is less than 5, stall with Scramblers and wait to see enemy's base
        if game_state.turn_number < 5:
            self.stall_with_scramblers(game_state)
        else:
            # Now let's analyze the enemy base to see where their defenses are concentrated.
            # If they have many units in the front we can build a line for our EMPs to attack them at long range.

            # They don't have many units in the front so lets figure out their least defended area and send Pings there.
            # Only spawn Ping's every other turn
            # Sending more at once is better since attacks can only hit a single ping at a time
            if self.detect_enemy_unit(game_state, unit_type=None, valid_x=None, valid_y=[14, 15]) > 15:
                self.emp_line_strategy(game_state)
            # elif self.detect_enemy_unit(game_state, unit_type=None, valid_x=[22, 23, 24, 25, 26, 27], valid_y = [14, 15]) > 6:
            #     game_state.attempt_spawn(SCRAMBLER, [24, 11])
            if cycle % counter == (counter - 1):
                # To simplify we will just check sending them from back left and right
                self.build_emp_ping_combo(game_state)

            cycle += 1
            # Lastly, if we have spare cores, let's build some Encryptors to boost our Pings' health.
            encryptor_locations = [[5, 10], [6, 10], [7, 10], [6, 9], [7, 9]]
            game_state.attempt_spawn(ENCRYPTOR, encryptor_locations)

    def build_emp_ping_combo(self, game_state):
        global enemy_change, last_breach, last_index, counter, breachnum, last_hp
        # build emp one to the right and up of the pings
        ping_spawn_location_options = [[8, 5], [23, 9]]
        # new_breach = True
        new_breach = (last_hp - game_state.enemy_health) > 2
        """
        if not enemy_change:
            if last_breach and not new_breach:
                enemy_change = True
        """
        if cycle // counter > 4:
            if not new_breach and not last_breach and counter < 4:
                counter += 1
                return

        """if enemy_change:
            best_index = 1 - last_index
        else:"""
        if new_breach:
            best_index = last_index
        else:
            best_index = 1 - last_index

        best_location = ping_spawn_location_options[best_index]

        emp_count = int(game_state.get_resource(BITS) // 13)
        if emp_count == 0:
            emp_count = 1
        ping_count = int(game_state.get_resource(BITS) - 3 * emp_count)

        if best_location[0] < 14:
            game_state.attempt_spawn(PING, best_location, ping_count)
            game_state.attempt_spawn(EMP, [best_location[0]+1, best_location[1]-1], emp_count)
        else:
            game_state.attempt_spawn(PING, best_location, ping_count)
            game_state.attempt_spawn(EMP, [best_location[0]+1, best_location[1]+1], emp_count)

        last_index = best_index
        last_breach = new_breach
        last_hp = game_state.enemy_health

    def build_defences(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy EMPs can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        # Place destructors that attack enemy units
        destructors = [[2, 13], [25, 13], [9, 11], [18, 11]]
        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        game_state.attempt_spawn(DESTRUCTOR, destructors)

        # Place filters in front of destructors to soak up damage for them
        mid_filters = [[10, 11], [11, 11], [12, 11], [13, 11], [14, 11], [15, 11], [16, 11], [17, 11]]
        left_filters = [[5, 11], [6, 11], [7, 11]]
        right_filters = [[20, 11], [21, 11], [22, 11], [23, 11], [23, 12]]
        game_state.attempt_spawn(FILTER, mid_filters)
        game_state.attempt_spawn(FILTER, right_filters)
        game_state.attempt_spawn(FILTER, left_filters)

        destructors2 = [[2, 12], [25, 12], [1, 12], [23, 11]]
        game_state.attempt_spawn(DESTRUCTOR, destructors2)

        # Extra defenses later game
        left_filters2 = [[8, 11], [0, 13], [1, 13], [3, 13], [3, 12]]
        right_filters2 = [[19, 11], [27, 13], [26, 13], [24, 13], [24, 12]]
        game_state.attempt_spawn(FILTER, right_filters2)
        game_state.attempt_spawn(FILTER, left_filters2)

        # upgrade filters so they soak more damage
        game_state.attempt_upgrade(right_filters)
        game_state.attempt_upgrade(left_filters)

        destructors3 = [[2, 11], [24, 11], [20, 10], [21, 10]]
        game_state.attempt_spawn(DESTRUCTOR, destructors3)

        game_state.attempt_upgrade(destructors)

        encryptors = [[5, 10], [6, 10], [7, 10], [6, 9], [7, 9]]
        game_state.attempt_spawn(ENCRYPTOR, encryptors)

        game_state.attempt_upgrade(destructors2)
        game_state.attempt_upgrade(destructors3)

        destructors4 = [[12, 10], [15, 10]]
        game_state.attempt_spawn(DESTRUCTOR, destructors4)
        game_state.attempt_upgrade(destructors4)

    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames
        as shown in the on_action_frame function
        """
        for location in self.scored_on_locations:
            # Build destructor one space above so that it doesn't block our own edge spawn locations
            build_location = [location[0], location[1]+2]
            game_state.attempt_spawn(DESTRUCTOR, build_location)

    def stall_with_scramblers(self, game_state):
        """
        Send out Scramblers at random locations to defend our base from enemy moving units.
        """
        # We can spawn moving units on our edges so a list of all our edge locations
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)

        # Remove locations that are blocked by our own firewalls
        # since we can't deploy units there.
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)

        # While we have remaining bits to spend lets send out scramblers randomly.
        while game_state.get_resource(BITS) >= game_state.type_cost(SCRAMBLER)[BITS] and len(deploy_locations) > 0:
            # Choose a random deploy location.
            deploy_index = random.randint(0, len(deploy_locations) - 1)
            deploy_location = deploy_locations[deploy_index]

            game_state.attempt_spawn(SCRAMBLER, deploy_location)
            """
            We don't have to remove the location since multiple information
            units can occupy the same space.
            """

    def emp_line_strategy(self, game_state):
        """
        Build a line of the cheapest stationary unit so our EMP's can attack from long range.
        """
        # First let's figure out the cheapest unit
        # We could just check the game rules, but this demonstrates how to use the GameUnit class
        stationary_units = [FILTER, DESTRUCTOR, ENCRYPTOR]
        cheapest_unit = FILTER
        for unit in stationary_units:
            unit_class = gamelib.GameUnit(unit, game_state.config)
            if unit_class.cost[game_state.BITS] < gamelib.GameUnit(cheapest_unit, game_state.config).cost[game_state.BITS]:
                cheapest_unit = unit

        # Now let's build out a line of stationary units. This will prevent our EMPs from running into the enemy base.
        # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
        for x in range(24, 5, -1):
            if x != 9:
                game_state.attempt_spawn(cheapest_unit, [x, 11])

        # Now spawn EMPs next to the line
        # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
        game_state.attempt_spawn(EMP, [24, 10], 1000)

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy destructors that can attack the final location and multiply by destructor damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(DESTRUCTOR, game_state.config).damage_i
            damages.append(damage)

        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units

    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def on_action_frame(self, turn_string):
        global breachnum
        breachcount = 0
        """
        This is the action frame of the game. This function could be called
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at: https://docs.c1games.com/json-docs.html
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly,
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))
            else:
                breachcount += 1

        breachnum = breachcount


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
