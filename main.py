import DiscreteEventSimulation as DES
import random
import numpy as np


class Customer:
    def __init__(self, arrival_time=None, request_time=None, counter=None):
        self.arrival_time = arrival_time
        self.request_time = request_time
        self.appointment_time = None
        self.service_time = None
        self.waited_outside = False
        self.counter = counter


class Emergency(Customer):
    pass


class Inpatient(Customer):
    pass


class Outpatient(Customer):
    pass


class EmergencyArrival(DES.Event):
    def execute(self):
        global waiting_queue, free_scanners, em_counter, emergency_data

        current_customer = Emergency(arrival_time=self.Time, counter=em_counter)
        em_counter += 1
        emergency_data[current_customer.counter] = [None, None, current_customer.arrival_time]
        i = 0

        while i < len(waiting_queue) and isinstance(waiting_queue[i], Emergency):
            i += 1

        waiting_queue.insert(i, current_customer)
        if waiting_queue.index(current_customer) > 3:
            current_customer.waited_outside = True

        emergency_data[current_customer.counter].append(current_customer.waited_outside)
        DES.insertEvent(EmergencyArrival(
            self.Time + random.expovariate(1 / 60)
        ))

        if free_scanners > 0:
            startService(self.Time, current_customer)


class InpatientRequest(DES.Event):
    def execute(self):
        global inpatient_queue, waiting_queue, bed_tripping, in_counter

        current_customer = Inpatient(request_time=self.Time, counter=in_counter)
        in_counter += 1
        found = False
        inpatient_queue.append(current_customer)
        inpatients_data[current_customer.counter] = [current_customer.request_time, None]

        for i in waiting_queue:
            if isinstance(i, Inpatient):
                found = True
                break

        if found is False and bed_tripping is False:
            startInpatientTrip(self.Time, inpatient_queue[0])

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
        global waiting_queue, bed_tripping, inpatients_data

        waiting_queue.append(self.customer)
        if waiting_queue.index(self.customer) > 3:
            self.customer.waited_outside = True

        self.customer.arrival_time = self.Time
        inpatients_data[self.customer.counter].append(self.customer.arrival_time)
        inpatients_data[self.customer.counter].append(self.customer.waited_outside)
        bed_tripping = False

        if free_scanners > 0:
            startService(self.Time, waiting_queue[0])


class OutpatientRequest(DES.Event):
    def execute(self):
        global outpatient_schedule, out_counter, outpatients_data

        day_time = dayTime(self.Time)
        current_customer = Outpatient(request_time=self.Time, counter=out_counter)
        out_counter += 1
        outpatients_data[current_customer.counter] = [self.Time]
        i = int(day_time[1]) + 1

        while i < 6:
            if i == 5:
                outpatient_schedule[i].append(current_customer)

            elif outpatient_schedule[i] < 28:
                outpatient_schedule[i] += 1

                if outpatient_schedule[i] <= 16:
                    appointment_time = self.Time - day_time[0] + (i - day_time[1]) * 1440 + 8 * 60 + (outpatient_schedule[i] - 1) * 15
                    outpatients_data[current_customer.counter].append(appointment_time)
                    outpatient_access_times[current_customer.counter] = dayTime(appointment_time)[2] - dayTime(current_customer.request_time)[2]
                    DES.insertEvent(OutpatientArrival(
                        appointment_time, current_customer
                    ))

                else:
                    appointment_time = self.Time - day_time[0] + (i - day_time[1]) * 1440 + 12 * 60 + (outpatient_schedule[i] - 1) * 20
                    outpatients_data[current_customer.counter].append(appointment_time)
                    outpatient_access_times[current_customer.counter] = dayTime(appointment_time)[2] - dayTime(current_customer.request_time)[2]
                    DES.insertEvent(OutpatientArrival(
                        appointment_time, current_customer
                    ))

                break

            i += 1

        next_request = self.Time + random.expovariate(23/480)
        if 480 <= dayTime(next_request)[0] <= 960:
            DES.insertEvent(OutpatientRequest(next_request))

        elif dayTime(self.Time)[1] == 4:
            DES.insertEvent(OutpatientRequest(self.Time - dayTime(self.Time)[0] + 1440 * 3 + 8 * 60 + np.random.exponential(23/480)))

        else:
            DES.insertEvent(OutpatientRequest(self.Time - dayTime(self.Time)[0] + 1440 + 8 * 60 + np.random.exponential(23/480)))


class FridaySchedule(DES.Event):
    def execute(self):
        global outpatient_schedule

        day_time = dayTime(self.Time)

        for j in range(5):
            outpatient_schedule[j] = 0

        superbreak = False
        while len(outpatient_schedule[-1]) > 0:
            if superbreak:
                break

            i = 0
            current_customer = outpatient_schedule[-1].pop(0)

            while i < 6:

                if i == 5:
                    superbreak = True
                    break

                elif outpatient_schedule[i] < 28:
                    outpatient_schedule[i] += 1

                    if outpatient_schedule[i] <= 16:
                        appointment_time = self.Time - day_time[0] + (i + 3) * 1440 + 8 * 60 + (outpatient_schedule[i] - 1) * 15
                        outpatients_data[current_customer.counter].append(appointment_time)
                        outpatient_access_times[current_customer.counter] = dayTime(appointment_time)[2] - dayTime(current_customer.request_time)[2]
                        DES.insertEvent(OutpatientArrival(
                            appointment_time, current_customer
                        ))

                    else:
                        appointment_time = self.Time - day_time[0] + (i + 3) * 1440 + 12 * 60 + (outpatient_schedule[i] - 1) * 20
                        outpatients_data[current_customer.counter].append(appointment_time)
                        outpatient_access_times[current_customer.counter] = dayTime(appointment_time)[2] - dayTime(current_customer.request_time)[2]
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
        global waiting_queue, outpatients_data, outpatient_number

        arrival_decision = np.random.binomial(1, 0.84)

        if arrival_decision:
            self.customer.arrival_time = self.Time
            waiting_queue.append(self.customer)
            if waiting_queue.index(self.customer) > 3:
                self.customer.waited_outside = True

            if free_scanners > 0:
                startService(self.Time, self.customer)

        else:
            self.customer.waited_outside = None

        outpatients_data[self.customer.counter].append(self.customer.arrival_time)
        outpatients_data[self.customer.counter].append(self.customer.waited_outside)


class Departure(DES.Event):
    def execute(self):
        global waiting_queue, free_scanners, occupied_scanners
        free_scanners += 1
        occupied_scanners -= 1

        while runningScanners(self.Time) < free_scanners + occupied_scanners:
            free_scanners -= 1

        if runningScanners(self.Time) > free_scanners + occupied_scanners:
            free_scanners = runningScanners(self.Time) - occupied_scanners

        if len(waiting_queue) > 0 and free_scanners > 0:
            startService(self.Time, waiting_queue[0])


def startService(t, customer):
    global waiting_queue, free_scanners, occupied_scanners, emergency_waiting_times, outpatient_waiting_times
    service_time = random.uniform(10, 19)
    waiting_queue.pop(0)
    free_scanners -= 1
    occupied_scanners += 1

    if isinstance(customer, Inpatient):
        if len(inpatient_queue) > 0:
            startInpatientTrip(t, inpatient_queue[0])

    elif isinstance(customer, Emergency):
        emergency_waiting_times[customer.counter] = t - customer.arrival_time

    else:
        outpatient_waiting_times[customer.counter] = t - customer.arrival_time

    DES.insertEvent(Departure(t + service_time))


def startInpatientTrip(t, customer):
    global inpatient_queue, bed_tripping
    service_time = random.uniform(9, 15)
    inpatient_queue.pop(0)
    bed_tripping = True

    DES.insertEvent(InpatientArrival(t + service_time, customer))


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
    return DES.currSimTime >= 14 * 1440


t0 = 0
inpatient_queue = []
waiting_queue = []
outpatient_schedule = [0 for _ in range(5)]
outpatient_schedule += [[]]
free_scanners = runningScanners(t0)
occupied_scanners = 0
bed_tripping = False
outpatients_data = {}  # [request time, appointment time, arrival time, waited outside]
inpatients_data = {}   # [request time, appointment time, arrival time, waited outside]
emergency_data = {}    # [request time, appointment time, arrival time, waited outside]
emergency_waiting_times = {}
outpatient_waiting_times = {}
outpatient_access_times = {}
out_counter = 1
in_counter = 1
em_counter = 1


DES.insertEvent(EmergencyArrival(0))
DES.insertEvent(InpatientRequest(0))
DES.insertEvent(OutpatientRequest(8 * 60))
DES.insertEvent(FridaySchedule(5 * 1440 - 1))
DES.runSimulation(StopCriterium=stopping_criterium)
