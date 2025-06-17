import DiscreteEventSimulation as DES
import random
import numpy as np
from matplotlib import pyplot as plt


class Customer: 
    def __init__(self, arrival_time=None, request_time=None, start_service=None):
        self.arrival_time = arrival_time
        self.request_time = request_time
        self.start_service = start_service


class Emergency(Customer):
    pass


class Inpatient(Customer):
    pass


class Outpatient(Customer):
    pass


class EmergencyArrival(DES.Event):
    def execute(self):
        global waiting_queue, free_scanners

        current_customer = Emergency(self.Time)
        i = 0

        while i < len(waiting_queue) and type(waiting_queue[i]) == Emergency:
            i += 1

        waiting_queue.insert(i, current_customer)
        DES.insertEvent(EmergencyArrival(self.Time + random.expovariate(1 / 60)))

        if free_scanners > 0:
            startService(self.Time, current_customer)


class InpatientRequest(DES.Event):
    def execute(self):
        global inpatient_queue, waiting_queue, inpatient_tripping

        current_customer = Inpatient(self.Time)
        inpatient_queue += [current_customer]

        # print("At time", dayTime(self.Time))
        # print(waiting_queue, "WAITING ROOM")
        # print(inpatient_queue, "INPATIENTS")

        found = False

        for i in waiting_queue:
            if type(i) == Inpatient:
                found = True
                break


        if found == inpatient_tripping == False:
            startInpatientTrip(self.Time)

        day_time = dayTime(self.Time)

        if day_time[0] <= 540 or day_time[0] >= 900:
            DES.insertEvent(InpatientRequest(self.Time + random.expovariate(1 / 160)))

        else:
            DES.insertEvent(InpatientRequest(self.Time + random.expovariate(f(day_time[0]))))


class InpatientArrival(DES.Event):
    def __init__(self, tm, customer):
        super().__init__(tm)
        self.customer = customer

    def execute(self):
        global waiting_queue, inpatient_tripping

        waiting_queue += [self.customer]
        inpatient_tripping = False

        # print("At time", dayTime(self.Time))
        # print(waiting_queue, "WAITING ROOM")
        # print(inpatient_queue, "INPATIENTS")

        if free_scanners > 0:
            startService(self.Time, self.customer)


class OutpatientRequest(DES.Event):
    def execute(self):
        global outpatient_schedule

        day_time = dayTime(self.Time)
        current_customer = Outpatient(request_time=self.Time)
        i = int(day_time[1]) + 1

        while i < 6:
            if i == 5:
                outpatient_schedule[i] += [current_customer]

            elif outpatient_schedule[i] < 28:
                outpatient_schedule[i] += 1

                if outpatient_schedule[i] <= 16:
                    arrival_time = self.Time - day_time[0] + (i - day_time[1]) * 1440 + 8 * 60 + (outpatient_schedule[i] - 1) * 15
                    DES.insertEvent(OutpatientArrival(arrival_time, current_customer))

                else:
                    arrival_time = self.Time - day_time[0] + (i - day_time[1]) * 1440 + 12 * 60 + (outpatient_schedule[i] - 17) * 20
                    DES.insertEvent(OutpatientArrival(arrival_time, current_customer))

                break

            i += 1

        next_request = self.Time + random.expovariate(23/480)
        # print("At time", dayTime(self.Time))
        # print(outpatient_schedule)

        if 480 <= dayTime(next_request)[0] <= 960:
            DES.insertEvent(OutpatientRequest(next_request))

        elif dayTime(self.Time)[1] == 4:
            DES.insertEvent(OutpatientRequest(self.Time - dayTime(self.Time)[0] + 1440 * 3 + 8 * 60 + np.random.exponential(23/480)))

        else:
            DES.insertEvent(OutpatientRequest(self.Time - dayTime(self.Time)[0] + 1440 + 8 * 60 + np.random.exponential(23/480)))


class OutpatientArrival(DES.Event):
    def __init__(self, tm, customer):
        super().__init__(tm)
        self.customer = customer

    def execute(self):
        global waiting_queue, outpatients_data, outpatient_number

        arrival_decision = np.random.binomial(1, 0.84)

        if arrival_decision:
            self.customer.arrival_time = self.Time
            waiting_queue += [self.customer]
            # print("At time", dayTime(self.Time))
            # print(waiting_queue, "WAITING ROOM")
            # print(inpatient_queue, "INPATIENTS")

            if free_scanners > 0:
                startService(self.Time, self.customer)

        outpatients_data[outpatient_number] = self.customer
        outpatient_number += 1


class Departure(DES.Event):
    def __init__(self, tm, customer):
        super().__init__(tm)
        self.customer = customer

    def execute(self):
        global waiting_queue, free_scanners, occupied_scanners
        free_scanners += 1
        occupied_scanners -= 1

        while runningScanners(self.Time) < free_scanners + occupied_scanners:
            free_scanners -= 1

        if len(waiting_queue) > 0 and free_scanners > 0:
            startService(self.Time, waiting_queue[0])


class FridaySchedule(DES.Event):
    def execute(self):
        global outpatient_schedule

        day_time = dayTime(self.Time)

        for j in range(5):
            outpatient_schedule[j] = 0

        superbreak = False

        while len(outpatient_schedule[-1]) > 0:

            i = 0

            if superbreak:
                break

            current_customer = outpatient_schedule[-1].pop(0)

            while i < 6:

                if i == 5:
                    superbreak = True
                    break

                elif outpatient_schedule[i] < 28:
                    outpatient_schedule[i] += 1

                    if outpatient_schedule[i] <= 16:
                        arrival_time = self.Time - day_time[0] + (i + 3) * 1440 + 8 * 60 + (outpatient_schedule[i] - 1) * 15
                        DES.insertEvent(OutpatientArrival(arrival_time, current_customer))

                    else:
                        arrival_time = self.Time - day_time[0] + (i + 3) * 1440 + 12 * 60 + (outpatient_schedule[i] - 17) * 20
                        DES.insertEvent(OutpatientArrival(arrival_time, current_customer))

                    break

                i += 1

        DES.insertEvent(FridaySchedule(self.Time + 7 * 1440))


class UpdateRunningScanners(DES.Event):
    def execute(self):
        global free_scanners, outpatient_schedule

        # print("NEW DAY", dayTime(self.Time)[1])

        if runningScanners(self.Time) > free_scanners + occupied_scanners:

            free_scanners = runningScanners(self.Time) - occupied_scanners

            if len(waiting_queue) > free_scanners:
                for i in range(free_scanners):
                    startService(self.Time + i, waiting_queue[i])

            else:
                for i in range(len(waiting_queue)):
                    startService(self.Time + i, waiting_queue[i])

        elif runningScanners(self.Time) < free_scanners + occupied_scanners:

            while runningScanners(self.Time) < free_scanners + occupied_scanners:
                free_scanners -= 1

        if len(waiting_queue) == 0 and len(inpatient_queue) == 0 and occupied_scanners == 0 and outpatient_schedule[0] == 23 and dayTime(self.Time)[1] == 0 and dayTime(self.Time)[0] == 8 * 60 and not inpatient_tripping:
            regenerationPoint(self.Time)
            print("Found")

        DES.insertEvent(UpdateRunningScanners(self.Time + 8 * 60))


def startService(t, customer):
    global waiting_queue, free_scanners, occupied_scanners
    customer.start_service = t
    service_time = random.uniform(10, 19)
    waiting_queue.pop(0)
    free_scanners -= 1
    occupied_scanners += 1

    # print("At time", dayTime(t))
    # print(waiting_queue, "WAITING ROOM")
    # print(inpatient_queue, "INPATIENTS")


    if isinstance(customer, Inpatient):
        if len(inpatient_queue) > 0:
            startInpatientTrip(t)

    DES.insertEvent(Departure(t + service_time, customer))


def startInpatientTrip(t):
    global inpatient_queue, inpatient_tripping
    service_time = random.uniform(9, 15)
    current_customer = inpatient_queue.pop(0)
    inpatient_tripping = True

    DES.insertEvent(InpatientArrival(t + service_time, current_customer))


def runningScanners(t):
    day_time = dayTime(t)

    if 8 < day_time[0] / 60 < 16 and day_time[1] < 5:
        return 2

    else:
        return 1


def dayTime(t):
    return (t0 + t) % 1440, (t0 + t) // 1440 % 7, (t0 + t) // 1440


def f(x):
    return 1/160 + 0.05 + 0.05 * np.sin(np.pi / 90 * (x - 45))


def stopping_criterium():
    return outpatient_schedule[1] == 28


def regenerationPoint(t):
    pass


def after_every_event():
    global inpatient_queue, waiting_queue, outpatient_schedule
    # print("inpatient queue: ", inpatient_queue)
    # print("waiting queue: ", waiting_queue)
    # print("outpatient schedule: ", outpatient_schedule)
    # print("----------------")


t0 = 0
inpatient_queue = []
waiting_queue = []
outpatient_schedule = [0 for _ in range(5)] + [[]]
free_scanners = runningScanners(t0)
occupied_scanners = 0
inpatient_tripping = False
outpatients_data = {}
outpatient_number = 1



DES.insertEvent(EmergencyArrival(0))
DES.insertEvent(InpatientRequest(0))
DES.insertEvent(OutpatientRequest(8 * 60))
DES.insertEvent(FridaySchedule(5 * 1440 - 1))
DES.insertEvent(UpdateRunningScanners(8 * 60))
DES.runSimulation(ExecuteAfterEveryEvent=after_every_event)

print(outpatients_data)


arrivals = []


for customer in outpatients_data.values():
    if customer.arrival_time is None:
        arrivals += [None]

    else:
        arrivals += [dayTime(customer.arrival_time)[0]]

print(arrivals)
