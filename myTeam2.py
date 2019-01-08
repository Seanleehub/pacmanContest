# myTeam.py
# ---------
# Licensing Information:  You are free to use or extend these projects for
# educational purposes provided that (1) you do not distribute or publish
# solutions, (2) you retain this notice, and (3) you provide clear
# attribution to UC Berkeley, including a link to http://ai.berkeley.edu.
#
# Attribution Information: The Pacman AI projects were developed at UC Berkeley.
# The core projects and autograders were primarily created by John DeNero
# (denero@cs.berkeley.edu) and Dan Klein (klein@cs.berkeley.edu).
# Student side autograding was added by Brad Miller, Nick Hay, and
# Pieter Abbeel (pabbeel@cs.berkeley.edu).


from captureAgents import CaptureAgent
import random
import time
import util
from game import Directions
import game
import distanceCalculator

#################
# Team creation #
#################


def createTeam(firstIndex, secondIndex, isRed,
               first='DefensiveAgent', second='DefensiveAgent'):
    """
    This function should return a list of two agents that will form the
    team, initialized using firstIndex and secondIndex as their agent
    index numbers.  isRed is True if the red team is being created, and
    will be False if the blue team is being created.

    As a potentially helpful development aid, this function can take
    additional string-valued keyword arguments ("first" and "second" are
    such arguments in the case of this function), which will come from
    the --redOpts and --blueOpts command-line arguments to capture.py.
    For the nightly contest, however, your team will be created without
    any extra arguments, so you should make sure that the default
    behavior is what you want for the nightly contest.
    """

    # The following line is an example only; feel free to change it.
    return [eval(first)(firstIndex), eval(second)(secondIndex)]

##########
# Agents #
##########


class DefensiveAgent(CaptureAgent):

    ###

    def debug(self, function, message):
        if not self.DEBUG:
            return
        print('{} Agent {} ({}) {}'.format(self.movesTaken, self.index, function, message))

    def pause(self):
        if not self.DEBUG:
            return
        print('PAUSE {}'.format(self.movesTaken))
        util.pause()

    ####

    def registerInitialState(self, gameState):

        self.DEBUG = False  # <----- DISABLE WHEN GOING LIVE
        CaptureAgent.registerInitialState(self, gameState)

        self.distancer = distanceCalculator.Distancer(gameState.data.layout)
        self.distancer.getMazeDistances()
        self.width = gameState.data.layout.width
        self.height = gameState.data.layout.height
        self.half_width = self.width / 2
        self.half_height = self.height / 2
        self.enemyIndices = self.getOpponents(gameState)
        self.teamIndices = self.getTeam(gameState)
        self.allyIndices = filter(lambda x: x != self.index, self.teamIndices)

        self.isRed = True if self.enemyIndices[0] == 1 else False

        if self.isRed:
            self.start = gameState.getAgentPosition(0)
        else:
            self.start = gameState.getAgentPosition(1)

        # self.start = gameState.getAgentPosition(self.index)
        self.enemyStart = (self.width - 2, self.height - 2) if self.isRed else (1, 1)
        self.walls = gameState.getWalls().asList()
        self.friendlyBoundary, self.enemyBoundary = self.getBoundaries(gameState)
        self.directions = [Directions.NORTH, Directions.EAST, Directions.SOUTH, Directions.WEST, Directions.STOP]
        self.oppAgent = self.teamIndices[0] if self.index == self.teamIndices[0] else self.teamIndices[1]

        # Variables that are changed each action taken
        self.defaultDefendPositionNone = None
        self.enemyCapsules = self.getCapsulesYouAreDefending(gameState)
        self.enemyCapsuleTimer = 0
        self.capsules = self.getCapsules(gameState)
        self.capsulesTimer = 0
        self.foodEaten = 0
        self.movesRemaining = 300
        self.movesTaken = 0
        self.score = 0
        self.distanceToDefencePos = self.getMazeDistance(self.start, self.getDefaultDefendPosition(gameState))

        # 0 = no, 1 = invade, 2 = retreat
        self.gettingEasyFood = 0

        self.enemyPositions = {}

        self.debug('registerInitialState', 'allies {}'.format(self.allyIndices))
        self.pause()

        # Only print once
        if self.index <= 1:
            self.debug('registerInitialState', 'width = {}, height = {}'.format(self.width, self.height))
            self.debug('registerInitialState', 'teamIndices {}, enemyIndices {}'.format(self.teamIndices, self.enemyIndices))
            self.debug('registerInitialState', 'isRed {}'.format(self.isRed))
            self.debug('registerInitialState', 'start = {}, enemy start = {}'.format(self.start, self.enemyStart))
            self.debug('registerInitialState', 'friendlyBoundary {}'.format(self.friendlyBoundary, self.enemyBoundary))
            self.debug('registerInitialState', 'enemyBoundary {}'.format(self.enemyBoundary))
            self.debug('registerInitialState', 'oppAgent {}'.format(self.oppAgent))

            for location in self.friendlyBoundary:
                self.debugDraw(location, (255, 255, 255))
            for location in self.enemyBoundary:
                self.debugDraw(location, (255, 255, 255))
            self.pause()
            self.debugClear()

    def chooseAction(self, gameState):
        try:
            return self.chooseActionMain(gameState)
        except Exception as e:
            self.debug('main', e)
            return self.getRandomLegalAction(gameState)

    def chooseActionMain(self, gameState):
        start = time.time()

        # Current position of the agent
        pos = gameState.getAgentPosition(self.index)

        # Monitor the number of moves remaining/taken
        self.movesRemaining -= 1
        self.movesTaken += 1

        # Reset food eaten counter
        if self.isOnHomeSide(pos):
            self.gettingEasyFood = 0
            self.foodEaten = 0
        else:
            if self.foodEaten >= 3 or len(self.getFood(gameState).asList()) <= 2:
                self.debug('chooseAction', 'falling back to retreat')
                return self.retreat(gameState, pos)

        # If we eat a food, add to counter
        if self.movesTaken > 1 and (pos in self.getFood(self.getPreviousObservation()).asList()):
            self.foodEaten += 1
        if hasattr(self, 'closestCapsule') and self.closestCapsule is not None:
            self.debug('main', self.closestCapsule)
            if self.getMazeDistance(pos, self.closestCapsule) == 0:
                self.foodEaten += 1

        # Update the enemy positions
        self.enemyPositions = self.getEnemyPositions(gameState, pos)
        self.debug('enemyPositions', self.enemyPositions)
        # self.pause()
        if len(self.enemyPositions) > 0:
            self.debug('chooseAction', 'enemyPositions {}'.format(self.enemyPositions))

        # If theres anything we can grab easily, get them
        if self.gettingEasyFood == 1 and pos == self.closestFood:
            self.debug('chooseAction', 'got my easy food')
            self.gettingEasyFood = 2

        self.closestFood = self.getClosestFood(gameState, pos)
        self.distToFood = self.getMazeDistance(pos, self.closestFood)
        try:
            self.closestCapsule = self.getClosestCapsule(gameState, pos)
            self.distToCapsule = self.getMazeDistance(pos, self.closestCapsule)
        except:
            self.closestCapsule = None
            self.distToCapsule = 9999
        # enemyDistToFood = self.getMazeDistance(self.enemyStart, self.closestFood)
        # # enemyDistToCapsule = self.getMazeDistance(self.enemyStart, self.closestCapsule)
        # if self.teamIndices[0] == self.index:
        #     if self.distToCapsule < enemyDistToFood and self.movesTaken <= self.distToCapsule:
        #         return self.invade(gameState, pos)
        #     if self.distToFood < enemyDistToFood and self.movesTaken <= self.distToFood:
        #         return self.invade(gameState, pos)

        # scaredTimer = True
        for enemy in self.enemyIndices:
            timer = gameState.getAgentState(enemy).scaredTimer
            if timer > 10 and not self.enemyOnOurSide():
                return self.invade(gameState, pos)

        # print 'eval time for agent %d: %.4f' % (self.index, time.time() - start)

        if self.index <= 1:
            if self.movesTaken > 200 and self.score <= 0:
                return self.invade(gameState, pos)
            try:
                return self.easy_food(gameState, pos)
            except Exception as e:
                self.debug('chooseAction easy_food', e)
                return self.defend(gameState, pos)
        else:
            if self.score <= 10:
                return self.invade(gameState, pos)
            return self.defend(gameState, pos)

    def easy_food(self, gameState, pos):
        # if we got the food, run away
        if self.gettingEasyFood == 2:
            self.debug('easy_food', 'I got my easy food, I am retreating')
            return self.retreat(gameState, pos)

        for enemy in self.enemyPositions.values():
            self.debug('easy_food', 'considering the enemy {}'.format(enemy))
            if self.isOnHomeSide(enemy):
                raise Exception('Not going for easy food while enemy is on home turf')
            if self.getMazeDistance(pos, enemy) <= self.distToFood:
                raise Exception('Enemy is too close, not worth it')

        # if we already decided to invade, continue plan of action
        if self.gettingEasyFood == 1:
            self.debug('easy_food', 'I am executing my plan of action')
            return self.pathFinder(gameState, pos, self.closestFood)

        if not self.isOnHomeSide(pos):
            raise Exception('Currently invading (but not just for the easy food)')
        if self.distToFood > 4:
            raise Exception('Food is too far away')

        self.debug('easy_food', 'I think {} is easy food'.format(self.closestFood))
        self.gettingEasyFood = 1
        return self.pathFinder(gameState, pos, self.closestFood)

    def invade(self, gameState, pos):
        """ Returns the action that will maximize our score """
        target = self.closestFood
        if self.distToCapsule < self.distToFood and self.distToCapsule > 0:
            target = self.closestCapsule

        for enemy in self.enemyIndices:
            if enemy in self.enemyPositions.values():
                timer = gameState.getAgentState(enemy).scaredTimer
                if timer >= 2 and self.getMazeDistance(self.enemyPositions.get(enemy), pos) <= 2:
                    target = enemy

        self.debug('invade', 'invading target = {}'.format(target))

        # Check to see that if we go to the next position, we will be able to return safely
        distance = 999
        for action in gameState.getLegalActions(self.index):
            successorState = self.getSuccessor(gameState, action)
            successorPosition = successorState.getAgentPosition(self.index)
            delta = self.getMazeDistance(successorPosition, target)
            if delta < distance:
                distance = delta
                nextState = successorState
                nextPosition = successorPosition

        if distance == 999:
            self.debug('invade', 'Shit, this didnt work... run away')
            return self.retreat(gameState, pos)

        # Check that is has a way out
        try:
            self.pathFinder(nextState, nextPosition, self.start, retreating=True)
            return self.pathFinder(gameState, pos, target)
        except Exception as e:
            self.debug('invade', e)
            return self.retreat(gameState, pos)

    def retreat(self, gameState, pos):
        """ Returns the action that will help us successfully deposit our food """
        # Find the closest boundary from the current positions and get back to it
        exit = self.getClosestExit(gameState, pos)
        self.debug('retreat', exit)
        try:
            return self.pathFinder(gameState, pos, exit, retreating=True)
        except Exception as e:
            self.debug('retreat', e)
            return self.getRandomLegalAction(gameState)

    def defend(self, gameState, pos):
        """ Returns the action that will help to successfully stop enemy scoring """
        # If we're sitting on our boundary and cant see anyone, try nab a pellet
        # if len(self.enemyPositions) == 0 and self.movesTaken > self.getMazeDistance(self.start, self.getDefaultDefendPosition(gameState)):
        #     return self.invade(gameState, pos)

        # If only 1 on our side, and we're closer we should purse
        distance, closestAgent = 999, None
        for enemy in self.enemyPositions.values():
            if self.isOnHomeSide(enemy):
                for team in self.teamIndices:
                    delta = self.getMazeDistance(gameState.getAgentPosition(team), enemy)
                    if delta < distance:
                        distance = delta
                        closestAgent = team
                        enemyPosition = enemy
        if self.index == closestAgent:
            return self.pathFinder(gameState, pos, enemyPosition)

        # The agent closest to the enemy blocks
        if len(self.enemyPositions) == 1:
            for enemy in self.enemyPositions.values():
                agentOne_distToEnemyOne = self.getMazeDistance(pos, enemy)
                agentTwo = self.teamIndices[0] if self.index == self.teamIndices[1] else self.teamIndices[1]
                pos2 = gameState.getAgentPosition(agentTwo)
                agentTwo_distToEnemyOne = self.getMazeDistance(pos2, enemy)
                if agentOne_distToEnemyOne > agentTwo_distToEnemyOne:
                    return self.invade(gameState, pos)
                if agentOne_distToEnemyOne <= agentTwo_distToEnemyOne:
                    boundary = self.getClosestExit(gameState, enemy)
                    if pos == boundary:
                        return self.bodyBlock(gameState, pos, enemy)
                    else:
                        return self.pathFinder(gameState, pos, boundary)

        # Body block the enemy agent thats closest to your and furthest from team-mate
        if len(self.enemyPositions) == 2:
            agentOne_distToEnemyOne = self.getMazeDistance(pos, self.enemyPositions[self.enemyIndices[0]])
            agentOne_distToEnemyTwo = self.getMazeDistance(pos, self.enemyPositions[self.enemyIndices[1]])
            agentTwo = self.teamIndices[0] if self.index == self.teamIndices[1] else self.teamIndices[1]
            pos2 = gameState.getAgentPosition(agentTwo)
            agentTwo_distToEnemyOne = self.getMazeDistance(pos2, self.enemyPositions[self.enemyIndices[0]])
            agentTwo_distToEnemyTwo = self.getMazeDistance(pos2, self.enemyPositions[self.enemyIndices[1]])
            agentOne_total = agentOne_distToEnemyOne + agentOne_distToEnemyTwo
            agentTwo_total = agentTwo_distToEnemyOne + agentTwo_distToEnemyTwo
            if agentOne_total > agentTwo_total:
                # Defend against the closer enemy to you
                distance = 999
                for enemy in self.enemyPositions.values():
                    delta = self.getMazeDistance(pos, enemy)
                    if delta < distance:
                        distance = delta
                        closestEnemy = enemy
            if agentOne_total < agentTwo_total:
                # Defend against the closer enemy to you
                distance = -999
                for enemy in self.enemyPositions.values():
                    delta = self.getMazeDistance(pos, enemy)
                    if delta > distance:
                        distance = delta
                        closestEnemy = enemy
            if agentOne_total == agentTwo_total:
                # Defend against youre respective agent
                for enemy in self.enemyPositions.values():
                    closestEnemy = enemy

            boundary = self.getClosestExit(gameState, closestEnemy)
            if pos == boundary:
                return self.bodyBlock(gameState, pos, closestEnemy)
            else:
                return self.pathFinder(gameState, pos, boundary)

        # Doesn't know what to do, go to default defence position
        try:
            return self.pathFinder(gameState, pos, self.getDefaultDefendPosition(gameState))
        except Exception as e:
            self.debug('defend', e)
            return self.retreat(gameState, pos)

    def getDefaultDefendPosition(self, gameState):
        # Get the team boundary avoiding the walls
        boundary_list = []

        if self.isRed:
            for y in range(self.height):
                boundary_list.append((self.half_width-1, y)) if (self.half_width-1, y) not in self.walls else None
        else:
            for y in range(self.height):
                boundary_list.append((self.half_width, y)) if (self.half_width, y) not in self.walls else None

        # Find the indices and positions of the agents of the same team
        for ind in self.teamIndices:
            if ind == self.index:
                currentAgentIndex = ind
                currentAgentPosition = gameState.getAgentPosition(currentAgentIndex)
            else:
                otherAgentIndex = ind
                otherAgentPosition = gameState.getAgentPosition(otherAgentIndex)

        # Find if border is already guarded
        # For the other agent
        isGuardFlag = False
        # For the same agent
        agentOnBorder = False

        if self.isRed:
            if otherAgentPosition[0] == self.half_width-1:
                isGuardFlag = True
        else:
            if otherAgentPosition[0] == self.half_width:
                isGuardFlag = True

        if self.isRed:
            if currentAgentPosition[0] == self.half_width - 1:
                agentOnBorder = True
        else:
            if currentAgentPosition[0] == self.half_width:
                agentOnBorder = True

        #Find the top and bottom most entrance to the grid
        for border in boundary_list:
            if border not in self.walls:
                bottomEntrance = border
                break
        for border in reversed(boundary_list):
            if border not in self.walls:
                topEntrance = border
                break


        # If border is not guarded by any agent then move to the closest border index
        if not isGuardFlag:
            if not agentOnBorder:
                currentAgentDefencePosition = self.getClosestBorder(gameState, currentAgentPosition, boundary_list)
                return currentAgentDefencePosition
            else:
                currentAgentDefencePosition = (self.half_width-1 if self.isRed else self.half_width, 0)
                minDiff = 9999

                for y in range(0, self.height):
                    if (currentAgentDefencePosition[0], y) not in self.walls:
                        dist = abs(game.manhattanDistance((currentAgentDefencePosition[0], y), topEntrance) -
                               game.manhattanDistance((currentAgentDefencePosition[0], y), bottomEntrance))
                        if dist < minDiff:
                            minDiff = dist
                            currentAgentDefencePosition = (currentAgentDefencePosition[0], y)
                return currentAgentDefencePosition

        else:
            if agentOnBorder:
                currentAgentDefencePosition = currentAgentPosition

                if self.getMazeDistance(currentAgentDefencePosition, otherAgentPosition) > 5 &\
                        game.manhattanDistance(currentAgentDefencePosition, otherAgentPosition) > 5:
                    if otherAgentPosition[1] > currentAgentDefencePosition[1] &\
                            game.manhattanDistance(currentAgentDefencePosition, bottomEntrance) < 4:
                        for y in range(currentAgentPosition[1]+1, self.height):
                            if (currentAgentPosition[0], y) not in self.walls:
                                currentAgentDefencePosition[1] = y
                                break
                    elif otherAgentPosition[1] < currentAgentDefencePosition[1] &\
                            game.manhattanDistance(currentAgentDefencePosition, topEntrance) < 4:
                        for y in range(self.height-1, currentAgentPosition[1], -1):
                            if (currentAgentPosition[0], y) not in self.walls:
                                currentAgentDefencePosition[1] = y
                                break
                    return currentAgentDefencePosition

            else:
                otherAgentToTopEntranceDist = game.manhattanDistance(otherAgentPosition, topEntrance)
                otherAgentToBottomEntranceDist = game.manhattanDistance(otherAgentPosition, bottomEntrance)

                if otherAgentToTopEntranceDist < otherAgentToBottomEntranceDist:
                    currentAgentDefencePosition = (otherAgentPosition[0], otherAgentPosition[1] - 1)
                    for y in range(bottomEntrance[1]+3, otherAgentPosition[1]):
                        if (currentAgentDefencePosition[0], y) not in self.walls:
                            currentAgentDefencePosition = (currentAgentDefencePosition[0], y)
                            break
                else:
                    currentAgentDefencePosition = (otherAgentPosition[0], otherAgentPosition[1] + 1)
                    for y in range(topEntrance[1]-3, otherAgentPosition[1], -1):
                        if (currentAgentDefencePosition[0], y) not in self.walls:
                            currentAgentDefencePosition = (currentAgentDefencePosition[0], y)
                            break
        return currentAgentDefencePosition

    def getBoundaries(self, gameState):
        """ Returns the lists of friendly and enemy cross-over positions """
        redBoundary, blueBoundary = [], []
        for height in range(self.height):
            if (self.half_width - 1, height) not in self.walls:
                redBoundary.append((self.half_width - 1, height))
            if (self.half_width, height) not in self.walls:
                blueBoundary.append((self.half_width, height))

        # Assign the boundary to either friendly or enemy
        if self.isRed:
            return redBoundary, blueBoundary
        else:
            return blueBoundary, redBoundary

    def bodyBlock(self, gameState, pos, target):
        """ Returns the action that follows an enemy up and down the boundary without crossing over """
        actions = gameState.getLegalActions(self.index)
        bestAction = None

        # If scared enemy next to us, just eat them
        for enemy in self.enemyIndices:
            if enemy in self.enemyPositions:
                if gameState.getAgentState(enemy).scaredTimer > 1 and self.getMazeDistance(pos, self.enemyPositions[enemy]) == 1:
                    target = self.enemyPositions[enemy]

        # Move the shortest path to the enemy
        boundary = self.getClosestExit(gameState, target)
        bestAction = self.pathFinder(gameState, pos, boundary)

        # If we're on the boundary, with enemy on the opposite side, step back
        dontDoAction = Directions.EAST if self.isRed else Directions.WEST
        for action in actions:
            successor = self.getSuccessor(gameState, action)
            newPos = successor.getAgentPosition(self.index)
            if not self.isOnEnemyBoundary(newPos) and pos not in self.walls:
                delta = self.getMazeDistance(newPos, target)
                if delta <= 2 and action != dontDoAction:
                    distance = delta
                    bestAction = action
        return bestAction

    def getEnemyPositions(self, gameState, pos):
        """ Returns the enemies positions. Assumes enemies are chasing us if we're
        invading , and assumes enemies are looking to score when defending """
        exactPositions = {}

        # If team mate ate an enemy, remove their location
        if self.movesRemaining < 299:
            for enemy in self.enemyIndices:
                if enemy in self.enemyPositions:
                    prevPos = self.getPreviousObservation().getAgentPosition(self.index)
                    if self.getMazeDistance(self.enemyPositions[enemy], pos) <= 5:
                        del self.enemyPositions[enemy]

        # See if we can see any definite enemy thats close to us
        obs = self.getCurrentObservation()
        for enemy in self.enemyIndices:
            if obs.getAgentPosition(enemy) != None:
                exactPositions[enemy] = obs.getAgentPosition(enemy)
            if len(exactPositions) == 2:
                return exactPositions

        # If we can see any enemy from missing food on the map
        if self.movesRemaining < 299:
            # Compare the previous food grid with the current
            prevFoodList = self.getFoodYouAreDefending(self.getPreviousObservation()).asList()
            currFoodList = self.getFoodYouAreDefending(gameState).asList()

            missingPellets = [x for x in currFoodList + prevFoodList if x not in currFoodList or x not in prevFoodList]

            if len(missingPellets) > 0 and len(missingPellets) <= 2:
                for enemy in self.enemyIndices:
                    # Dont add the same enemy index to the list twice
                    if enemy not in exactPositions:
                        # Dont add the same location to list twice
                        for missingPellet in missingPellets:
                            exactPositions[enemy] = missingPellet
                if len(exactPositions) == 2:
                    return exactPositions

        # If we can see any enemy from missing capsules on the map
        if self.movesRemaining < 299:
            # Compare the previous food grid with the current
            prevCapsuleList = self.getCapsulesYouAreDefending(self.getPreviousObservation())
            currCapsuleList = self.getCapsulesYouAreDefending(gameState)

            missingCapsules = [x for x in currCapsuleList + prevCapsuleList if x not in currCapsuleList or x not in prevCapsuleList]

            if len(missingCapsules) > 0:
                for enemy in self.enemyIndices:
                    # Dont add the same enemy index to the list twice
                    if enemy not in exactPositions:
                        # Dont add the same location to list twice
                        for missingCapsule in missingCapsules:
                            exactPositions[enemy] = missingCapsule
                if len(exactPositions) == 2:
                    return exactPositions

        # Keep their location as wherever we last saw them
        for enemy in self.enemyIndices:
            if enemy in self.enemyPositions:
                if enemy not in exactPositions:
                    exactPositions[enemy] = self.enemyPositions[enemy]

        # If we ate an enemy, reset their position to the start
        if self.movesRemaining < 299:
            for enemy in self.enemyIndices:
                if enemy in self.enemyPositions:
                    prevPos = self.getPreviousObservation().getAgentPosition(self.index)
                    if pos == self.enemyPositions[enemy] or prevPos == self.enemyPositions[enemy]:
                        del exactPositions[enemy]

        return exactPositions

    def getSuccessor(self, gameState, action):
        """ Finds the next successor which is a grid position (location tuple) """
        successor = gameState.generateSuccessor(self.index, action)
        pos = successor.getAgentState(self.index).getPosition()
        if pos != util.nearestPoint(pos):
            # Only half a grid position was covered
            return successor.generateSuccessor(self.index, action)
        else:
            return successor

    def isOnHomeSide(self, pos):
        """ Returns true if the given position is on our side of the map """
        if self.isRed:
            return pos[0] < self.half_width
        else:
            return pos[0] >= self.half_width

    def isOnEnemySide(self, pos):
        """ Returns true if the given position is on the enemy side of the map """
        return not self.isOnHomeSide(pos)

    def enemyOnOurSide(self):
        """ Returns true is there is enemy on our side of the map """
        for enemy in self.enemyIndices:
            if enemy in self.enemyPositions:
                position = self.enemyPositions[enemy]
                if position != None:
                    if self.isOnHomeSide(position):
                        return True
        return False

    def isOnEnemyBoundary(self, pos):
        if self.isRed:
            return pos[0] == self.half_width
        else:
            return pos[0] == self.half_width - 1

    def isOnHomeBoundary(self, pos):
        pass

    def getClosestBorder(self, gameState, currentAgentPosition, boundary_list):
        min_dist = 999

        for border in boundary_list:
            mazeDist = self.getMazeDistance(currentAgentPosition, border)
            if mazeDist < min_dist:
                min_dist = mazeDist
                minDistBorder = border

        return minDistBorder

    def getClosestExit(self, gameState, pos, invert=False, secondExit=False):
        """ Returns the closest exit from a given position (invert for enemy exit, secondExit to get second closest) """
        if not invert:
            boundaryList = self.friendlyBoundary
        else:
            boundaryList = self.enemyBoundary

        distance = 999
        distancesList = []
        for boundary in boundaryList:
            delta = self.getMazeDistance(pos, boundary)
            distancesList.append(delta)
            if delta < distance:
                distance = delta
                closestExit = boundary

        if not secondExit:
            return closestExit
        else:
            minDist = min(distancesList)
            distance = 999
            for x in range(len(distancesList)):
                if distancesList[x] < distance and minDist != distance:
                    index = x

            return boundaryList[index]

    def getClosestFood(self, gameState, pos, invert=False):
        """ Returns the closest food from a given position (invert for food we're defending) """
        if not invert:
            foodList = self.getFood(gameState).asList()
        else:
            foodList = self.getFoodYouAreDefending(gameState).asList()

        # distance = 999

        f = {}
        for food in foodList:
            try:
                f[food] = self.getMazeDistance(pos, food)
            except:
                f[food] = 999
        s = sorted(f, key=f.get)
        for food in s:
            stop = False
            for ally in self.allyIndices:
                if self.getMazeDistance(gameState.getAgentPosition(ally), food) < f[food]:
                    stop = True
            if not stop:
                self.debug('closestFood', 'going for food {} which is {} distance'.format(food, f[food]))
                return food
        self.debug('closestFood', 'defaulting to food {} which is {} distance'.format(s[1], f[s[1]]))
        return s[1]

        # closestDistance = 999
        # closestFood = None
        # backupDistance = 999
        # backupFood = None
        # for food in foodList:
        #     f[food] = self.getMazeDistance(pos, food)
        #     delta = self.getMazeDistance(pos, food)
        #     if delta < backupDistance:
        #         stop = False

        #         for ally in self.allyIndices:
        #             if self.getMazeDistance(gameState.getAgentPosition(ally), food) <= delta + 1:
        #                 self.debug('getClosestFood', 'considered {} but Agent {} is closer'.format(food, ally))
        #                 stop = True

        #         if not stop:
        #             try:
        #                 self.pathFinder(gameState, pos, food)
        #                 if closestFood is not None:
        #                     backupFood = closestFood
        #                     backupDistance = closestDistance
        #                 else:
        #                     backupDistance = delta
        #                 closestFood = food
        #                 closestDistance = delta
        #             except:
        #                 pass
        #         else:
        #             backupFood = food
        #             backupDistance = delta

        # if closestFood is None:
        #     self.debug('getClosestFood', 'backup choice food is {}'.format(backupFood))
        #     return backupFood
        # self.debug('getClosestFood', 'primary choice food is {}'.format(closestFood))
        # return closestFood

    def getClosestCapsule(self, gameState, pos, invert=False):
        """ Returns the closest capsule from a given positon (invert for capsules we're defending) """
        closestCapsule = None

        if not invert:
            capsules = self.getCapsules(gameState)
        else:
            capsules = self.getCapsulesYouAreDefending(gameState)

        distance = 999
        for capsule in capsules:
            delta = self.getMazeDistance(pos, capsule)
            if delta < distance:
                distance = delta
                closestCapsule = capsule
        return closestCapsule

    def getLegalSurroundingPositions(self, pos, depth):
        """ Returns the list of legal moves given the position """
        legalPositions = []
        # Dont need to go any deeper
        if depth == 2:
            return

        for direction in self.directions:
            if direction == Directions.NORTH:
                position = (pos[0], pos[1] + 1)
            elif direction == Directions.EAST:
                position = (pos[0] + 1, pos[1])
            elif direction == Directions.SOUTH:
                position = (pos[0], pos[1] - 1)
            elif direction == Directions.WEST:
                position = (pos[0] - 1, pos[1])
            else:
                position = (pos[0], pos[1])

            if position not in self.walls and not self.isOnHomeSide(position):
                legalPositions.append(position)
        if depth == 0:
            for position in legalPositions:
                legalPositions = legalPositions + self.getLegalSurroundingPositions(position, depth + 1)
        return legalPositions

    def getRandomLegalAction(self, gameState):
        actions = gameState.getLegalActions(self.index)
        if len(actions) == 0:  # if only STOP
            return actions[0]
        random.shuffle(actions)
        for action in actions:
            if action == Directions.STOP:
                continue
            self.debug('randomLegalAction', action)
            return action

    def pathFinder(self, gameState, start, goal, retreating=False):
        """ Find the path between a starting position and a goal position. """

        # Keep track of the path to the goal
        queue = util.PriorityQueue()
        queue.push((gameState, [], []), 0)

        # Track the cells we have visited
        visitedPositions = []

        walls = []
        # Assume the area around an enemy is a wall
        for enemy in self.enemyPositions.values():
            # self.debug('pathfinder', enemy)
            # self.pause()
            legalPositions = self.getLegalSurroundingPositions(enemy, 0)
            for position in legalPositions:
                if not self.isOnHomeSide(position):
                    walls.append(position)

        # Iterate through all actions and find a path to the goal
        while not queue.isEmpty():
            currentState, actions, positions = queue.pop()
            currentPosition = currentState.getAgentPosition(self.index)

            # If the current position is the goal, return the first action that gets here
            if currentPosition == goal or retreating and currentPosition in self.friendlyBoundary:
                # self.debugClear()
                # for wall in walls:
                    #self.debugDraw(wall, (100, 100, 100))
                # for path in positions:
                    # if retreating:
                        #self.debugDraw(path, (255, 100, 100))
                    # else:
                        #self.debugDraw(path, (100, 255, 100))
                #self.debugDraw(currentPosition, (255, 255, 255))
                if len(actions) > 0:
                    return actions[0]

            # Enemy can't kill us, we can ignore their 'walls'
            scaredTimer = 40
            for enemy in self.enemyIndices:
                timer = currentState.getAgentState(enemy).scaredTimer
                if timer < 0:
                    scaredTimer = timer

            # If the current position hasnt already been visited, move there
            if currentPosition not in visitedPositions:
                if scaredTimer == 0 and currentPosition not in walls:
                    for action in currentState.getLegalActions(self.index):
                        successorState = currentState.generateSuccessor(self.index, action)
                        successorPosition = currentState.getAgentPosition(self.index)

                        # Add the next gameState and action there to the queue
                        queue.push((successorState, actions + [action], positions + [successorPosition]), 0)

                        # Add the successor position to the visited list
                        visitedPositions.append(successorPosition)
                else:
                    for action in currentState.getLegalActions(self.index):
                        successorState = currentState.generateSuccessor(self.index, action)
                        successorPosition = currentState.getAgentPosition(self.index)

                        # Add the next gameState and action there to the queue
                        queue.push((successorState, actions + [action], positions + [successorPosition]), 0)

                        # Add the successor position to the visited list
                        visitedPositions.append(successorPosition)

        # No viable path to target
        # return Directions.STOP
        raise Exception('No valid path')
