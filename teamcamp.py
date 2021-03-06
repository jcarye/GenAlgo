##########################################################################
# The following python code is an implementation of a genetic algorithm
# that seeks to create a near-optimal schedule for a basketball camp.
# Details of the scenario can be seen in TeamCamp.pdf. A companion 
# SCHEDULE.TXT document should be placed in the same directory this 
# script is run from, which will give daily start and end times for each
# team, the team's rank (1-3), and whether it's varsity or JV or both.
##########################################################################

import random
import numpy 
import array

from deap import algorithms
from deap import base
from deap import creator
from deap import tools

# USER EDITABLE VARIABLES
# HyperParameters for GA:
num_of_gens = 50
pop_size = 500
tour_size = 3
mutpb = 0.15 
cxpb = 0.2

# Schedule Parameters:
day1_start = 8 # Time in 24hr format by the hour
day1_end = 23 # Time start of last game is this -1
day2_start = 8
day2_end = 23

# Number of courts available in each location
loc1_courts = 5 # Main courts located @ mercer
loc2_courts = 2 # Ingleside courts
loc3_courts = 1 # Vineville Methodist Court
loc4_courts = 1 # Vineville Baptist Court

########################################################################
# DO NOT EDIT BELOW
# Required global variables for our functions to work
########################################################################

num_of_teams = 0 # Default to 0, populate later
num_of_conflicts = 0 # Incremented as we gain more conflicts
tot_courts = loc1_courts + loc2_courts + loc3_courts + loc4_courts
day1_slots = day1_end - day1_start
day2_slots = day2_end - day2_start
tot_slots = day1_slots + day2_slots

lvl_and_rank = [] # Store if V or JV, and rank of team
glo_conf_list = [] # Store conflict list globally for CX to access

########################################################################
# Custom Crossover Function. 
# Typical crossover functions will not work well for our structure, so 
# a custom way to breed 2 schedules is desired. Explanation provided at
# end of function.
########################################################################
def schedule_cx(schedule1, schedule2):
    # This will follow a similar structure to our initial schedule
    # generation, using the input of two schedules.
    # Indexes to our population are as follows:
    # schedule[TimeSegment][Court][TeamSide]

    # Create references to schedules 1 and 2
    sch1 = schedule1
    sch2 = schedule2

    # print("Schedule 1: \n", schedule1)
    # print("Schedule 2: \n", schedule2)

    # Extract a team order from each parent schedule
    sch1_order = []
    sch2_order = []
    for x in sch1:
        for y in x:
            for z in y:
                if not z == 0:
                    if z not in sch1_order:
                        sch1_order.append(z)
    for x in sch2:
        for y in x:
            for z in y:
                if not z == 0:
                    if z not in sch2_order:
                        sch2_order.append(z)

    # print("Sch1: \n", sch1_order)
    # print("Sch2: \n", sch2_order)

    child1_order = []
    child2_order = []
    # Switch between 1 and 2, and select the first teams that show up,
    # until we have a new team order to populate a schedule with
    count = 0
    which_sch = 1
    while count < num_of_teams:
        if which_sch == 1:
            for x in sch1_order:
                if x not in child1_order:
                    child1_order.append(x)
                    which_sch = 2
                    count += 1
                    break
        elif which_sch == 2:
            for x in sch2_order:
                if x not in child1_order:
                    child1_order.append(x)
                    which_sch = 1
                    count += 1
                    break

    count = 0
    which_sch = 2
    while count < num_of_teams:
        if which_sch == 1:
            for x in sch1_order:
                if x not in child2_order:
                    child2_order.append(x)
                    which_sch = 2
                    count += 1
                    break
        elif which_sch == 2:
            for x in sch2_order:
                if x not in child2_order:
                    child2_order.append(x)
                    which_sch = 1
                    count += 1
                    break
    # print("Child 1 New Order: \n", child1_order)
    # print("Child 2 New Order: \n", child2_order)

    # ZERO OUT our original schedules to prepare them for population
    for i, x in enumerate(sch1):
        for j, y in enumerate(x):
            for k, z in enumerate(y):
                sch1[i][j][k] = 0
                sch2[i][j][k] = 0

    # Now iterate through schedule 1 and 2, changing their order
    # into our new team orders child1 and child2 respectively

    # CHILD 1!!!
    # List to hold already scheduled teams for conflict
    already_scheduled = []
    # Start iterating through team_order_list and populating schedule
    for team in child1_order:
        # Team may have already been scheduled due to conflict, check list
        if team not in already_scheduled: 
            # Check if team is in our conflict list. If so, schedule its 
            # conflict at the same time for simplicity
            conflicting = 0
            for match in glo_conf_list:
                if team in match:
                    if team == match[0]:
                        conflicting = match[1]
                    else:
                        conflicting = match[0]
            if (conflicting != 0):
                # print("Conflict exists for team: ", team, " and is: ", conflicting)
                already_scheduled.append(team)
                already_scheduled.append(conflicting)
                # Schedule 3 games per conflicting team
                rem_mat_team = 3
                rem_mat_conf = 3
                pick_t_or_c = 1
                prev_played_team = []
                prev_played_conf = []
                # Find spots to place teams in the schedule
                for x,i in enumerate(sch1):
                    if rem_mat_conf == 0:
                        # All 6 games have been scheduled, break
                        break
                    for y,j in enumerate(i):
                        if j[0] == 0:
                            #Empty slot, schedule game here
                            if pick_t_or_c == 1:
                                sch1[x][y][0] = team
                                rem_mat_team -= 1
                                pick_t_or_c = 2
                                break
                            elif pick_t_or_c == 2:
                                sch1[x][y][0] = conflicting
                                rem_mat_conf -= 1
                                pick_t_or_c = 1
                                break
                        elif j[1] == 0:
                            #Finish team matchup, schedule here
                            if pick_t_or_c == 1:
                                # Only match if team wasn't previously played
                                if j[0] not in prev_played_team:
                                    sch1[x][y][1] = team
                                    # Keep track of previously played teams
                                    prev_played_team.append(j[0])
                                    rem_mat_team -= 1
                                    pick_t_or_c = 2
                                    break
                            elif pick_t_or_c == 2:
                                # Only match if conf wasn't previously played
                                if j[0] not in prev_played_conf:
                                    sch1[x][y][1] = conflicting
                                    # Keep track of previously played teams
                                    prev_played_conf.append(j[0])
                                    rem_mat_conf -= 1
                                    pick_t_or_c = 1
                                    break
            else:
                # print("No conflict for team: ", team)
                # No need to append to already_scheduled since singular
                rem_mat_team = 3
                prev_played = []
                for x,i in enumerate(sch1):
                    if rem_mat_team == 0:
                        # All 3 games have been scheduled, break
                        break
                    for y, j in enumerate(i):
                        if j[0] == 0:
                            #Empty slot, schedule game here
                            sch1[x][y][0] = team
                            rem_mat_team -= 1
                            break
                        elif j[1] == 0:
                            # Only match if previously unplayed team
                            if j[0] not in prev_played:
                                #Finish team matchup, schedule here
                                sch1[x][y][1] = team
                                prev_played.append(j[0])
                                rem_mat_team -= 1
                                break
        # else:
            # print("Team already scheduled: ", team)
    # print("New Child 1: \n", sch1)


    # CHILD 2!!!
    # List to hold already scheduled teams for conflict
    already_scheduled = []
    # Start iterating through team_order_list and populating schedule
    for team in child2_order:
        # Team may have already been scheduled due to conflict, check list
        if team not in already_scheduled: 
            # Check if team is in our conflict list. If so, schedule its 
            # conflict at the same time for simplicity
            conflicting = 0
            for match in glo_conf_list:
                if team in match:
                    if team == match[0]:
                        conflicting = match[1]
                    else:
                        conflicting = match[0]
            if (conflicting != 0):
                # print("Conflict exists for team: ", team, " and is: ", conflicting)
                already_scheduled.append(team)
                already_scheduled.append(conflicting)
                # Schedule 3 games per conflicting team
                rem_mat_team = 3
                rem_mat_conf = 3
                pick_t_or_c = 1
                prev_played_team = []
                prev_played_conf = []
                # Find spots to place teams in the schedule
                for x,i in enumerate(sch2):
                    if rem_mat_conf == 0:
                        # All 6 games have been scheduled, break
                        break
                    for y,j in enumerate(i):
                        if j[0] == 0:
                            #Empty slot, schedule game here
                            if pick_t_or_c == 1:
                                sch2[x][y][0] = team
                                rem_mat_team -= 1
                                pick_t_or_c = 2
                                break
                            elif pick_t_or_c == 2:
                                sch2[x][y][0] = conflicting
                                rem_mat_conf -= 1
                                pick_t_or_c = 1
                                break
                        elif j[1] == 0:
                            #Finish team matchup, schedule here
                            if pick_t_or_c == 1:
                                # Only match if team wasn't previously played
                                if j[0] not in prev_played_team:
                                    sch2[x][y][1] = team
                                    # Keep track of previously played teams
                                    prev_played_team.append(j[0])
                                    rem_mat_team -= 1
                                    pick_t_or_c = 2
                                    break
                            elif pick_t_or_c == 2:
                                # Only match if conf wasn't previously played
                                if j[0] not in prev_played_conf:
                                    sch2[x][y][1] = conflicting
                                    # Keep track of previously played teams
                                    prev_played_conf.append(j[0])
                                    rem_mat_conf -= 1
                                    pick_t_or_c = 1
                                    break
            else:
                # print("No conflict for team: ", team)
                # No need to append to already_scheduled since singular
                rem_mat_team = 3
                prev_played = []
                for x,i in enumerate(sch2):
                    if rem_mat_team == 0:
                        # All 3 games have been scheduled, break
                        break
                    for y, j in enumerate(i):
                        if j[0] == 0:
                            #Empty slot, schedule game here
                            sch2[x][y][0] = team
                            rem_mat_team -= 1
                            break
                        elif j[1] == 0:
                            # Only match if previously unplayed team
                            if j[0] not in prev_played:
                                #Finish team matchup, schedule here
                                sch2[x][y][1] = team
                                prev_played.append(j[0])
                                rem_mat_team -= 1
                                break
    # print("New Child 2: \n", sch2)

    return sch1, sch2
    # Extract sequence of teams from both parent schedules. To generate
    # a new sequence for each child, swich between the two parents,
    # making sure not to repeat any teams already added. Once both child
    # sequences are created, zero out schedule 1 and 2 to prepare them
    # for population, then generate their new respective schedules.

########################################################################
# Similar to CX, mutation needs to be a custom function to prevent
# completely breaking a schedule. We will keep mutation simple:
# pick two teams and swap their schedules.
# WARNING: This can cause conflicting teams to play at same time,
# punish that in fitness function
########################################################################
def schedule_mut(schedule):
    # pick 2 teams randomly
    # Create reference to schedule
    mutating_local = schedule
    team_order_list = random.sample(range(1,num_of_teams+1,1), k=2)
    # print("Before MUT: \n", mutating_local)
    # swap them
    for i, x in enumerate(mutating_local):
        for j, y in enumerate(x):
            for k, z in enumerate(y):
                if z == team_order_list[0]:
                    # print("z was: ", z, id(z))
                    mutating_local[i][j][k] = int(team_order_list[1])
                elif z == team_order_list[1]:
                    # print("z was: ", z, id(z))
                    mutating_local[i][j][k] = int(team_order_list[0])
    # print("After MUT: \n", mutating_local)
    return mutating_local,

########################################################################
# Our Fitness Function, determines how fit an individual is. Punish
# unwanted but legal matchups lightly, and reward ideal matchups. 
# Heavily punish illegal and incomplete schedules.
########################################################################
def calc_fitness(individual):
    # Placeholder return for testing...
    # total_fit = individual[0][0][0] + individual[0][0][1]
    # return total_fit,
    # Iterate through each individual team and calculate fitness. 
    # Fitness is based on details below.
    total_fit = 0
    # If there are any incomplete matches, penalize
    for i in individual:
        for j in i:
            if (j[0] != 0) and (j[1] ==  0):
                total_fit -= 50
    for i in range(1,num_of_teams+1,1):
        # Find i's matchup and determine if it's a good match.
        # +5 if it's an exact level match, +2 if it's only one
        # above or below. lvl_and_rank[i-1][0] = v or jv
        # lvl_and_rank[i-1][1] = rank
        count = 3
        # Keep track of all teams previously played. Penalize
        # if we play the same team again. Reward if team has
        # not been played yet. 
        prev_played = []
        for x in individual:
            if count == 0:
                break
            # See if we already found a match in this time slot, same team
            # cannot play at same time
            in_this_time_slot = False
            for y in x:
                if y[0] == i:
                    # Determine level and rank of i and y[1]
                    if (lvl_and_rank[i-1][0] == lvl_and_rank[y[1]-1][0]):
                        # Both V or JV, now check level matchup
                        if (lvl_and_rank[i-1][1] == lvl_and_rank[y[1]-1][1]):
                            # Perfect match, maximum reward
                            total_fit += 5
                        else:
                            comp_lvl_1 = lvl_and_rank[i-1][1] 
                            comp_lvl_2 = lvl_and_rank[y[1]-1][1]
                            if abs(comp_lvl_1 - comp_lvl_2) <= 1:
                                # Only one rank off, give small reward
                                total_fit += 2
                            else:
                                # Bad match, but same level. Minor penalty
                                total_fit -= 1
                    else:
                        if(lvl_and_rank[i-1][0] == 1):
                            # i is the V team, check if its rank 3 and y is rank 1
                            # Award 2 points if so, else minus 1 for poor match
                            if (lvl_and_rank[i-1][1] == 3) and (lvl_and_rank[y[1]-1][1] == 1):
                                total_fit += 1
                            else:
                                total_fit -= 5
                        else:
                            # y is V team, check if it's rank 3 and i is rank 1
                            if (lvl_and_rank[i-1][1] == 1) and (lvl_and_rank[y[1]-1][1] == 3):
                                total_fit += 1
                            else:
                                total_fit -= 5
                    count -= 1
                    if in_this_time_slot == False:
                        # We have not run into this team during this time slot, set flag
                        # to true and do nothing else.
                        in_this_time_slot = True
                    else:
                        # Big trouble: Same team scheduled to play at same time, penalize
                        total_fit -= 50
                    # Check if opponent was played before, if so penalize
                    if y[1] in prev_played:
                        total_fit -= 50
                    # Store opponent if it's not 0, for which penalty has already been applied
                    elif y[1] != 0:
                        prev_played.append(y[1])
                        total_fit += 5
                elif y[1] == i:
                    # Determine level and rank of i and y[0]
                    if (lvl_and_rank[i-1][0] == lvl_and_rank[y[0]-1][0]):
                        # Both V or JV, now check level matchup
                        if (lvl_and_rank[i-1][1] == lvl_and_rank[y[0]-1][1]):
                            # Perfect match, maximum reward
                            total_fit += 5
                        else:
                            comp_lvl_1 = lvl_and_rank[i-1][1] 
                            comp_lvl_2 = lvl_and_rank[y[0]-1][1]
                            if abs(comp_lvl_1 - comp_lvl_2) <= 1:
                                # Only one rank off, give small reward
                                total_fit += 2
                            else:
                                # Bad match, but same level. Minor penalty
                                total_fit -= 1
                    else:
                        if(lvl_and_rank[i-1][0] == 1):
                            # i is the V team, check if its rank 3 and y is rank 1
                            # Award 2 points if so, else minus 1 for poor match
                            if (lvl_and_rank[i-1][1] == 3) and (lvl_and_rank[y[0]-1][1] == 1):
                                total_fit += 1
                            else:
                                total_fit -= 5
                        else:
                            # y is V team, check if it's rank 3 and i is rank 1
                            if (lvl_and_rank[i-1][1] == 1) and (lvl_and_rank[y[0]-1][1] == 3):
                                total_fit += 1
                            else:
                                total_fit -= 5
                    count -= 1
                    if in_this_time_slot == False:
                        # We have not run into this team during this time slot, set flag
                        # to true and do nothing else.
                        in_this_time_slot = True
                    else:
                        # Big trouble: Same team scheduled to play at same time, penalize
                        total_fit -= 50
                    # Penalize if played before
                    if y[0] in prev_played:
                        total_fit -= 50
                    # Store opponent if it's not 0, for which penalty has already been applied
                    # Reward for unique matchup
                    elif y[0] != 0:
                        prev_played.append(y[1])
                        total_fit += 5
    return total_fit,
    # Psuedocode: Iterate through all the teams and figure out
    # the fitness of each. Sum up total fitness to calculate the
    # final schedule fitness. Staying at same facility, having
    # single hour gaps between games, and no scheduling conflicts
    # will yield a higer fitness.

########################################################################
# Used during initial blank schedule creation, creates one time
# slot worth of courts to schedule games on
########################################################################
def single_slot():
    one_match = [0,0]
    one_timeslot = []
    for i in range(tot_courts):
        one_timeslot.append(one_match[:])
    return one_timeslot[:]

########################################################################
# Generate a random schedule for each member of the population. 
# This is done only during initialization.
########################################################################
def generate_schedule(population, team_list, conflict_list):
    # Create a reference to our population to easily edit it
    scheduled_pop = population
    # Create global reference to conflict_list for CX access
    global glo_conf_list
    glo_conf_list = conflict_list
    # Indexes to our population are as follows:
    # pop[Individual][TimeSegment][Court][TeamSide]
    for h in range(pop_size):
        # Generate order of teams to populate schedule randomly
        team_order_list = random.sample(range(1,num_of_teams+1,1), k=num_of_teams)
        # print("Team Order List Is: ", team_order_list)
        # print("h is: ", h)
        # print("Conflict list: ", conflict_list)
        # List to hold already scheduled teams for conflict
        already_scheduled = []
        # Helps us keep track of where to place teams
        last_scheduled_ts = 0
        last_scheduled_court = 0
        last_scheduled_side = 0
        # Start iterating through team_order_list and populating schedule
        for team in team_order_list:
            # Team may have already been scheduled due to conflict, check list
            if team not in already_scheduled: 
                # Check if team is in our conflict list. If so, schedule its 
                # conflict at the same time for simplicity
                conflicting = 0
                for match in conflict_list:
                    if team in match:
                        if team == match[0]:
                            conflicting = match[1]
                        else:
                            conflicting = match[0]
                if (conflicting != 0):
                    # print("Conflict exists for team: ", team, " and is: ", conflicting)
                    already_scheduled.append(team)
                    already_scheduled.append(conflicting)
                    # Schedule 3 games per conflicting team
                    rem_mat_team = 3
                    rem_mat_conf = 3
                    pick_t_or_c = 1
                    # Find spots to place teams in the schedule
                    for i in scheduled_pop[h]:
                        if rem_mat_conf == 0:
                            # All 6 games have been scheduled, break
                            break
                        for j in i:
                            if j[0] == 0:
                                #Empty slot, schedule game here
                                if pick_t_or_c == 1:
                                    j[0] = team
                                    rem_mat_team -= 1
                                    pick_t_or_c = 2
                                    break
                                elif pick_t_or_c == 2:
                                    j[0] = conflicting
                                    rem_mat_conf -= 1
                                    pick_t_or_c = 1
                                    break
                            elif j[1] == 0:
                                #Finish team matchup, schedule here
                                if pick_t_or_c == 1:
                                    j[1] = team
                                    rem_mat_team -= 1
                                    pick_t_or_c = 2
                                    break
                                elif pick_t_or_c == 2:
                                    j[1] = conflicting
                                    rem_mat_conf -= 1
                                    pick_t_or_c = 1
                                    break
                else:
                    # print("No conflict for team: ", team)
                    # No need to append to already_scheduled since singular
                    rem_mat_team = 3
                    for i in scheduled_pop[h]:
                        if rem_mat_team == 0:
                            # All 3 games have been scheduled, break
                            break
                        for j in i:
                            if j[0] == 0:
                                #Empty slot, schedule game here
                                j[0] = team
                                rem_mat_team -= 1
                                break
                            elif j[1] == 0:
                                #Finish team matchup, schedule here
                                j[1] = team
                                rem_mat_team -= 1
                                break
            # else:
                # print("Team already scheduled: ", team)
    return scheduled_pop

########################################################################
# Repair a schedule. This will be run after CX or MUT, to turn the
# schedule legal. No teams playing themselves or at 2 courts
# at the same time. No back to back games at different facilities.
# All teams within arrival and departure time. Also checks 
# conflicting_teams to make sure V and JV of same team isn't 
# scheduled during same time if this option was requested.
########################################################################
def repair_schedule(schedule):
    return schedule
    # Was never used but could be helpful during expansion of program.

########################################################################
# Main driver function.
########################################################################
def main():
    # Seed our random number generator
    random.seed(random.SystemRandom().random())
    # We start by importing SCHEDULE.txt with each team specifics.
    print ("Importing team schedules")
    teams_to_schedule = []  # Master list of teams to schedule
    conflicting_teams = []  # Master list of teams that can't play at same time
    general_population = [] # Holds our current population of schedules
    with open("SCHEDULE.txt","r") as input_file:
        team_number = 1
        for line in input_file:
            if(len(line.strip()) == 0):
                continue
            single_data_line=line.strip().split("-")
            schedule_write = [] # Single line list to add to master list after setting

            # String has been split. Check if we're adding 1 or 2 teams to the schedule.
            # Teams with both a V and JV require two separate teams
            # Each team needs a unique number, issued by team_number

            if (single_data_line[1] == '1') or (single_data_line[1] == '2'):
                # Single Team Case
                if single_data_line[1] == '1':
                    single_data_line[0] = single_data_line[0] + " V"
                else:
                    single_data_line[0] = single_data_line[0] + " JV"
                # print (single_data_line[0], " has just a V or JV to play")
                schedule_write.append(single_data_line[0]) # Team Name
                schedule_write.append(team_number) # Unique Team Number
                schedule_write.append(int(single_data_line[1])) # 1 for V, 2 for JV
                schedule_write.append(int(single_data_line[3])) # Rank from 1-3
                schedule_write.append(int(single_data_line[4])) # Start time
                schedule_write.append(int(single_data_line[5])) # End time
                # print ("Importing :", schedule_write)
                teams_to_schedule.append(schedule_write)
                cop_to_rank = [int(single_data_line[1]),int(single_data_line[3])]
                lvl_and_rank.append(cop_to_rank[:]) # Specify copy
            elif single_data_line[1] == '3':
                # Varsity and JV team, [2] will be Y if they can play at the same time
                if (single_data_line[2] == 'N') or (single_data_line[2] == 'n'):
                    # Add team numbers to conflict pool
                    add_conflict = []
                    add_conflict.append(team_number)
                    add_conflict.append(team_number+1)
                    conflicting_teams.append(add_conflict)
                    global num_of_conflicts
                    num_of_conflicts += 1
                # Parse rank structure for later addition to schedule_write
                parsed_rank=single_data_line[3].strip().split(",")
                # Create varsity team first
                temp_name_string = single_data_line[0] + " V"
                schedule_write.append(temp_name_string) # Team Name
                schedule_write.append(team_number) # Unique Team Number
                schedule_write.append(int(1)) # 1 for V, 2 for JV
                schedule_write.append(int(parsed_rank[0])) # Rank from 1-3
                schedule_write.append(int(single_data_line[4])) # Start time
                schedule_write.append(int(single_data_line[5])) # End time
                teams_to_schedule.append(schedule_write)
                cop_to_rank = [int(1),int(parsed_rank[0])]
                lvl_and_rank.append(cop_to_rank[:]) # Specify copy
                # print ("Importing :", schedule_write)
                team_number +=1 # Increment our team counter for special case
                schedule_write = [] # Clear out our list to create 2nd JV team
                temp_name_string = single_data_line[0] + " JV"
                schedule_write.append(temp_name_string) # Team Name
                schedule_write.append(team_number) # Unique Team Number
                schedule_write.append(int(2)) # 1 for V, 2 for JV
                schedule_write.append(int(parsed_rank[1])) # Rank from 1-3
                schedule_write.append(int(single_data_line[4])) # Start time
                schedule_write.append(int(single_data_line[5])) # End time
                teams_to_schedule.append(schedule_write)
                cop_to_rank = [int(2),int(parsed_rank[1])]
                lvl_and_rank.append(cop_to_rank[:]) # Specify copy
                # print ("Importing :", schedule_write)
                # print (single_data_line[0], " has both V and JV to play")
            else:
                print ("Problem with SCHEDULE.txt, please fix team named:",single_data_line[0])
                exit()
            # store off current team number (also # of teams imported)
            global num_of_teams
            num_of_teams = team_number
            # increment our team_number counter
            team_number += 1
    print("Import successful. Starting Genetic Algorithm.")
    print("Number of teams to schedule: ", num_of_teams)
    # We are done reading our file in...
    # print("\n\nOur conflicting teams: ")
    # print(conflicting_teams)
    print("Our individual teams: ")
    print(teams_to_schedule)

    # Time to set up our Genetic Algo. We have a single objective for fitness,
    # which is to maximize it.
    creator.create("FitnessMax", base.Fitness, weights=(1.0,))

    # Our individual is a list (with nested lists, needs not be specified)
    creator.create("Individual", list, fitness=creator.FitnessMax)

    # Initialize our toolbox
    toolbox = base.Toolbox()

    # Register our individual and population, call custom individual creation function.
    # Single_help is used to prevent the same ID being used, and creates individual
    # hourly time slots for all courts
    toolbox.register("single_help", single_slot)
    toolbox.register("individual", tools.initRepeat, creator.Individual, 
           toolbox.single_help, tot_slots)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    # Register custom evaluate, mutate, and crossover. Use tournament selection.
    toolbox.register("evaluate", calc_fitness)
    toolbox.register("mate", schedule_cx)
    toolbox.register("mutate", schedule_mut)
    toolbox.register("select", tools.selTournament, tournsize=tour_size)
    
    pop = toolbox.population(n=pop_size)
    # References to our population are as follows:
    # pop[Individual][TimeSegment][Court][TeamSide]
    # eg pop[4][0][0][0] would reference the 5th individual schedule, first time
    # slot, first court, and the first team scheduled for that court.
    generate_schedule(pop, teams_to_schedule, conflicting_teams)
    print("Initial population successfully generated")
    print("Population Size: ", pop_size, "   Number of Generations: ", num_of_gens)
    print("Mutation Prob: ", mutpb, "   Crossover Prob: ", cxpb)
    print("BEGIN GENETIC ALGORITHM")
    # print("Member 1: \n", pop[0])
    hof = tools.HallOfFame(1)

    # After everything has been set, register stats and run gen algo
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", numpy.mean)
    stats.register("std", numpy.std)
    stats.register("min", numpy.min)
    stats.register("max", numpy.max)

    pop, log = algorithms.eaSimple(pop, toolbox, cxpb=cxpb, mutpb=mutpb, ngen=num_of_gens,
            stats=stats, halloffame=hof, verbose=True)

    print("Best last iteration: \n", hof)
    print("Level and rank: \n", lvl_and_rank)
    # print("Our individual teams: ")
    # print(teams_to_schedule)
    return pop, log, hof

if __name__ == "__main__":
    main()
