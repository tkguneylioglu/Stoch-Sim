import DiscreteEventSimulation as DES
import random
import numpy as np


class Customer:
    def __init__(self, arrival_time=None, request_time=None, counter=None):
        self.arrival_time = arrival_time
        self.request_time = request_time
        self.appointment_time = None
        self.waiting_time = None
        self.waited_outside = 0
        self.counter = counter


class Emergency(Customer):
    pass


class Inpatient(Customer):
    def __init__(self, arrival_time=None, request_time=None, counter=None):
        super().__init__(arrival_time, request_time, counter)
        self.requested_office_hours = False
        self.scanned_same_office_hours = 0


class Outpatient(Customer):
    pass


class State:
    def __init__(self, t0=0):
        self.t0 = t0
        self.inpatient_queue = []
        self.waiting_queue = []
        self.outpatient_schedule = [0 for _ in range(5)]
        self.outpatient_schedule += [[]]
        self.free_scanners = self.runningScanners(t0)
        self.occupied_scanners = 0
        self.bed_tripping = False

        # Metrics tracking
        self.outpatients_data = {}  # [request time, appointment time, arrival time, waited outside]
        self.inpatients_data = {}   # [request time, appointment time, arrival time, waited outside]
        self.emergency_data = {}    # [request time, appointment time, arrival time, waited outside]
        self.emergency_waiting_times = {}
        self.outpatient_waiting_times = {}
        self.outpatient_access_times = {}
        self.inpatient_scanned_same_office_hours = {}
        self.total_waited_outside = 0
        self.total_inpatient_ssof = 0  # scanned in the same office hour
        self.regeneration_points = []

        # Counters
        self.out_counter = 1
        self.in_counter = 1
        self.em_counter = 1

    def dayTime(self, t):
        return (self.t0 + t) % 1440, ((self.t0 + t) // 1440) % 7, (self.t0 + t) // 1440

    def runningScanners(self, t):
        day_time = self.dayTime(t)
        if 8 < day_time[0] / 60 < 16 and day_time[1] < 5:
            return 2
        else:
            return 1


def f(x):
    return 1/160 + 0.05 + 0.05 * np.sin(np.pi / 90 * (x - 45))


def stopping_criterium():
    return DES.currSimTime >= 14 * 1440


state = State()


class EmergencyArrival(DES.Event):
    def execute(self):
        current_customer = Emergency(arrival_time=self.Time, counter=state.em_counter)
        state.em_counter += 1
        state.emergency_data[current_customer.counter] = [None, None, current_customer.arrival_time]
        i = 0

        while i < len(state.waiting_queue) and isinstance(state.waiting_queue[i], Emergency):
            i += 1

        state.waiting_queue.insert(i, current_customer)
        if i > 3:
            current_customer.waited_outside = 1
            state.total_waited_outside += 1

        state.emergency_data[current_customer.counter].append(current_customer.waited_outside)
        DES.insertEvent(EmergencyArrival(self.Time + random.expovariate(1 / 60)))
        if state.free_scanners > 0:
            startService(self.Time, current_customer)


class InpatientRequest(DES.Event):
    def execute(self):
        current_customer = Inpatient(request_time=self.Time, counter=state.in_counter)
        state.in_counter += 1
        state.inpatient_queue.append(current_customer)
        state.inpatients_data[current_customer.counter] = [current_customer.request_time, None]

        if state.runningScanners(self.Time) == 2:
            current_customer.requested_office_hours = True

        found = any(isinstance(i, Inpatient) for i in state.waiting_queue)
        if not found and not state.bed_tripping:
            startInpatientTrip(self.Time, state.inpatient_queue[0])

        day_time = state.dayTime(self.Time)
        if day_time[0] <= 540 or day_time[0] >= 900 or day_time[1] >= 5:
            DES.insertEvent(InpatientRequest(self.Time + random.expovariate(1/160)))

        else:
            DES.insertEvent(InpatientRequest(self.Time + random.expovariate(f(day_time[0]))))


class InpatientArrival(DES.Event):
    def __init__(self, tm, customer):
        super().__init__(tm)
        self.customer = customer

    def execute(self):
        state.waiting_queue.append(self.customer)
        if len(state.waiting_queue) > 3:
            self.customer.waited_outside = 1
            state.total_waited_outside += 1

        self.customer.arrival_time = self.Time
        state.inpatients_data[self.customer.counter].append(self.customer.arrival_time)
        state.inpatients_data[self.customer.counter].append(self.customer.waited_outside)
        state.bed_tripping = False

        if state.free_scanners > 0:
            startService(self.Time, self.customer)


class OutpatientRequest(DES.Event):
    def execute(self):
        day_time = state.dayTime(self.Time)
        current_customer = Outpatient(request_time=self.Time, counter=state.out_counter)
        state.out_counter += 1
        state.outpatients_data[current_customer.counter] = [self.Time]
        i = int(day_time[1]) + 1

        while i < 6:
            if i == 5:
                state.outpatient_schedule[i].append(current_customer)

            elif state.outpatient_schedule[i] < 28:
                state.outpatient_schedule[i] += 1

                if state.outpatient_schedule[i] <= 16:
                    appointment_time = self.Time - day_time[0] + (i - day_time[1]) * 1440 + 8 * 60 + (state.outpatient_schedule[i] - 1) * 15

                else:
                    appointment_time = self.Time - day_time[0] + (i - day_time[1]) * 1440 + 12 * 60 + (state.outpatient_schedule[i] - 17) * 20

                state.outpatients_data[current_customer.counter].append(appointment_time)
                state.outpatient_access_times[current_customer.counter] = state.dayTime(appointment_time)[2] - state.dayTime(current_customer.request_time)[2]
                DES.insertEvent(OutpatientArrival(
                    appointment_time, current_customer
                ))

                break

            i += 1

        next_request = self.Time + random.expovariate(23/480)
        if 480 <= state.dayTime(next_request)[0] <= 960:
            DES.insertEvent(OutpatientRequest(next_request))

        elif state.dayTime(self.Time)[1] == 4:
            DES.insertEvent(OutpatientRequest(next_request + 16 * 60 + 2 * 1440))

        else:
            DES.insertEvent(OutpatientRequest(next_request + 16 * 60))


class FridaySchedule(DES.Event):
    def execute(self):
        day_time = state.dayTime(self.Time)

        for j in range(5):
            state.outpatient_schedule[j] = 0

        superbreak = False
        while len(state.outpatient_schedule[-1]) > 0:
            if superbreak:
                break

            i = 0
            current_customer = state.outpatient_schedule[-1].pop(0)

            while i < 6:

                if i == 5:
                    superbreak = True
                    break

                elif state.outpatient_schedule[i] < 28:
                    state.outpatient_schedule[i] += 1

                    if state.outpatient_schedule[i] <= 16:
                        appointment_time = self.Time - day_time[0] + (i + 3) * 1440 + 8 * 60 + (state.outpatient_schedule[i] - 1) * 15

                    else:
                        appointment_time = self.Time - day_time[0] + (i + 3) * 1440 + 12 * 60 + (state.outpatient_schedule[i] - 17) * 20

                    state.outpatients_data[current_customer.counter].append(appointment_time)
                    state.outpatient_access_times[current_customer.counter] = state.dayTime(appointment_time)[2] - state.dayTime(current_customer.request_time)[2]
                    DES.insertEvent(OutpatientArrival(
                        appointment_time, current_customer
                    ))

                    break

                i += 1
        DES.insertEvent(FridaySchedule(self.Time + 7 * 1440))


class OutpatientArrival(DES.Event):
    def __init__(self, tm, customer):
        super().__init__(tm)
        self.customer = customer

    def execute(self):
        arrival_decision = np.random.binomial(1, 0.84)
        if arrival_decision:
            self.customer.arrival_time = self.Time
            state.waiting_queue.append(self.customer)
            if len(state.waiting_queue) > 3:
                self.customer.waited_outside = 1
                state.total_waited_outside += 1

            if state.free_scanners > 0:
                startService(self.Time, self.customer)

        else:
            self.customer.waited_outside = None

        state.outpatients_data[self.customer.counter].append(self.customer.arrival_time)
        state.outpatients_data[self.customer.counter].append(self.customer.waited_outside)


class Departure(DES.Event):
    def execute(self):
        state.free_scanners += 1
        state.occupied_scanners -= 1
        target = state.runningScanners(self.Time)
        if target < state.free_scanners + state.occupied_scanners:
            state.free_scanners -= 1

        if state.waiting_queue and state.free_scanners > 0:
            startService(self.Time, state.waiting_queue[0])


def startService(t, customer):
    service_time = random.uniform(10, 19)
    day_time = state.dayTime(t)
    state.waiting_queue.pop(0)
    state.free_scanners -= 1
    state.occupied_scanners += 1
    waiting_time = t - customer.arrival_time
    customer.waiting_time = waiting_time

    if isinstance(customer, Inpatient) and state.inpatient_queue:
        startInpatientTrip(t, state.inpatient_queue[0])
        if customer.requested_office_hours and day_time[2] == state.dayTime(customer.request_time)[2]:
            if day_time[0] <= 16 * 60:
                customer.scanned_same_office_hours = 1
                state.total_inpatient_ssof += 1

        state.inpatient_scanned_same_office_hours[customer.counter] = customer.scanned_same_office_hours

    elif isinstance(customer, Emergency):
        state.emergency_waiting_times[customer.counter] = waiting_time

    elif isinstance(customer, Outpatient):
        state.outpatient_waiting_times[customer.counter] = waiting_time

    DES.insertEvent(Departure(t + service_time))


def startInpatientTrip(t, customer):
    service_time = random.uniform(9, 15)
    state.inpatient_queue.pop(0)
    state.bed_tripping = True
    DES.insertEvent(InpatientArrival(t + service_time, customer))


class UpdateRunningScanners(DES.Event):
    def execute(self):
        if state.runningScanners(self.Time) > state.free_scanners + state.occupied_scanners:
            state.free_scanners = state.runningScanners(self.Time) - state.occupied_scanners
            if len(state.waiting_queue) > state.free_scanners:
                for _ in range(state.free_scanners):
                    startService(self.Time, state.waiting_queue[0])

            else:
                for _ in range(len(state.waiting_queue)):
                    startService(self.Time, state.waiting_queue[0])

        elif state.runningScanners(self.Time) < state.free_scanners + state.occupied_scanners:
            while state.runningScanners(self.Time) < state.free_scanners + state.occupied_scanners and state.free_scanners > 0:
                state.free_scanners -= 1

        if len(state.waiting_queue) == 0 and len(state.inpatient_queue) == 0 and state.occupied_scanners == 0 and state.outpatient_schedule[0] == 23 and state.dayTime(self.Time)[1] == 0 and state.dayTime(self.Time)[0] == 8 * 60 and not state.bed_tripping:
            state.regeneration_points.append(self.Time)
            print("Found")

        DES.insertEvent(UpdateRunningScanners(self.Time + 8 * 60))


DES.insertEvent(EmergencyArrival(random.expovariate(1 / 60)))
DES.insertEvent(InpatientRequest(random.expovariate(1/160)))
DES.insertEvent(OutpatientRequest(8 * 60 + random.expovariate(23/480)))
DES.insertEvent(FridaySchedule(5 * 1440 - 1))
DES.insertEvent(UpdateRunningScanners(8 * 60))
DES.runSimulation(StopCriterium=stopping_criterium)
