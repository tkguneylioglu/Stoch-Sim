import sys
import heapq


# --------------- basic event -----------------
class Event(object):
    """
    This basic class is used for all other event types
    --- redefine execute for every type of event
    --- add extra
    """

    def description(self):
        return 'do nothing'

    def execute(self):
        pass

    def __init__(self, tm):
        self.Time = tm

    def __lt__(self,ev):
        return self.Time<ev.Time
            

    def __str__(self):
        return '@' + str(self.Time) + '  = > ' + self.description()


# --------------- standard events ----------------
class EndOfTime(Event):
    """ Error: the simulation did not end"""

    def description(self):
        return 'end of eventList'

    def execute(self):
        global stopSimulation
        print(' EMPTY EVENTLIST ')
        stopSimulation = True


class EndOfSimulationRun(Event):
    """ Time to collect statistics """

    def description(self):
        return 'end of simulation run'

    def execute(self):
        global stopSimulation
        stopSimulation = True

# --------------- standard variables ----------------
def resetEventList():
    global eventList
    eventList = [EndOfTime(float("inf"))]

stopSimulation =  False
prevSimTime = -float("inf")
currSimTime= prevSimTime
currEvent= Event(currSimTime)

def showEventList(GetInput= True):
    """ default is to wait for input, give False as parameter to continue without waiting """
    print( '>>>show list ')  
    for ev in sorted(eventList): # just for printing
         print(ev)
    if GetInput:  #to interrupt the program every time the list is shown
        inString= input('show eventlist (use s to stop) ')
        if len(inString)>0 and (inString[0]=='s' or inString[0]=='S'):
            sys.exit(0)

def insertEvent(ev):
    heapq.heappush(eventList,ev)

def executeBeforeEveryEvent():
    pass

def executeAfterEveryEvent():
    pass

def stopCriterium():
    pass



def runSimulation(StopCriterium= stopCriterium,
                  ExecuteBeforeEveryEvent=executeBeforeEveryEvent, 
                  ExecuteAfterEveryEvent=executeAfterEveryEvent):
    global eventList,stopSimulation, prevSimTime, currSimTime, currEvent
    prevSimTime = 0
    stopSimulation = False
    while not ( StopCriterium() ):
        currEvent = heapq.heappop(eventList)
        currSimTime = currEvent.Time
        ExecuteBeforeEveryEvent()
        currEvent.execute()       
        ExecuteAfterEveryEvent()
        prevSimTime = currSimTime
# ----------------------- end general structure ----------------

# ----------------------- initialization -----------------------
resetEventList()
