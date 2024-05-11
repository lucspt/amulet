

from datetime import timedelta, datetime, timezone
from numbers import Number
from multiprocessing import Process
import time, math
import pymongo

"""
Don't think this should be run on the amulet directly, because it could eventually consume too much.
if anything it should just be an api call that sends it to another resource
"""


class PledgeKeeper:
    __slots__ = (
        "pledge", "pledges", "pledge_name", "caught_up"
        )
    
    def __init__(self, pledge_name: str):
        self.pledge_name = pledge_name
        self.caught_up = False
    
    def init_pledge(self):
        pledges = pymongo.MongoClient().edge.pledges
        pledge = pledges.find_one({"pledge_name": self.pledge_name})
        self.pledge = pledge
        self.pledges = pledges
        freq = timedelta(**pledge["pledge_frequency"])
        pledge_frequency = freq.total_seconds()
        return pledge["last_updated"], pledge_frequency
        
        
    def update_pledge(self) -> dict:
        """Update's a pledge in the db"""
        pledge = self.pledge
        pledge_name = pledge["pledge_name"]
        updated_impact = pledge["impact"] + pledge["co2e_factor"]
        updated_streak = pledge["pledge_streak"] + 1
        now = datetime.now(tz=timezone.utc)
        update = {
            "impact": updated_impact,
            "pledge_streak": updated_streak,
            "last_updated": now
        }
        self.pledges.update_one({"pledge_name": pledge_name}, {"$set": update})
        self.pledge = {**pledge, **update}
        if self.caught_up: self._keep_pledge()
    
    @staticmethod
    def seconds_diff(last_updated: datetime):
        """Seconds difference since last updated"""
        return (datetime.now(tz=timezone.utc) - last_updated).total_seconds()
    
    #NOTE: maybe this is overdoing it? accounting for even the days they have not powered on
    def check_lag(self, last_updated: datetime, pledge_frequency: Number):
        """Account for the passed pledge frequencies which did not get updated"""
        waited = self.seconds_diff(last_updated) 
        seconds, lagged = math.modf(waited / pledge_frequency)
        for _ in range(int(lagged)):
            print("catching up", _)
            self.update_pledge()
        remainder = pledge_frequency - (pledge_frequency * seconds)
        print("now remainder", remainder)
        self.caught_up = True
        time.sleep(remainder)
        self.update_pledge()
    
    def _keep_pledge(self):
        """A loop that simply sleeps until a pledge should be updated.
        There is a one second delay to avoid troublesome comparisons"""
        last_updated, pledge_frequency = self.init_pledge()
        if not self.caught_up: 
            self.check_lag(
                last_updated=last_updated, pledge_frequency=pledge_frequency
            )
        print("ok caught up now")
        while (wait := self.seconds_diff(last_updated)) < pledge_frequency:
            wait_time = pledge_frequency - wait
            print("waiting", wait_time)
            time.sleep(wait_time + 1.3)
        print("updating")
        self.update_pledge()
        
    def keep_pledge(self):
        """Monitor a pledge and keep updating it as a 
        non blocking task."""
        process = Process(
            target=self._keep_pledge, daemon=True
        )
        process.start()

# import time, math
# from numbers import Number
# class PledgeKeeper:
#     __slots__ = (
#         "pledge", "pledges", "pledge_frequency", "pledge_name", "caught_up"
#     )
    
#     def __init__(self, pledge_name: str):
#         self.pledge_name = pledge_name
#         self.caught_up = False
    
#     def init_pledge(self):
#         pledges = pymongo.MongoClient().edge.pledges
#         pledge = pledges.find_one({"pledge_name": self.pledge_name})
#         self.pledge = pledge
#         self.pledges = pledges
#         last_updated = pledge["last_updated"]
#         since_last = (datetime.now() - last_updated).total_seconds()
#         freq = timedelta(**pledge["pledge_frequency"])
#         self.pledge_frequency = freq
#         self.check_lag(
#             since_last=since_last, pledge_frequency=freq.total_seconds()
#         )
        
        
#     def update_pledge(self) -> dict:
#         pledge = self.pledge
#         pledge_name, last_updated = pledge["pledge_name"], pledge["last_updated"]
#         updated_impact = pledge["impact"] + pledge["co2e_factor"]
#         updated_streak = pledge["pledge_streak"] + 1
#         now = datetime.now()
#         update = {
#             "impact": updated_impact,
#             "pledge_streak": updated_streak,
#             "last_updated": now,
#         }
#         self.pledges.update_one({"pledge_name": pledge_name}, {"$set": update})
#         self.pledge = {**pledge, **update}
#         next_update = now + self.pledge_frequency
        
#         if self.caught_up: self._keep_pledge(next_update=next_update)
    
#     def check_lag(self, since_last, pledge_frequency):
#         lag = since_last / pledge_frequency
#         seconds, lagged = math.modf(lag)
#         print(lag)
#         for _ in range(int(lagged)):
#             print("cathing up", _)
#             self.update_pledge()
#         remainder = pledge_frequency - (seconds * pledge_frequency)
#         print("remainder now", remainder)
#         time.sleep(remainder)
#         print("waited now caught up")
#         self.caught_up = True
#         self.update_pledge()
        
#     def _keep_pledge(self, next_update: Number | None = None):
#         if not self.caught_up: self.init_pledge()
#         while (wait_time := (next_update - datetime.now()).total_seconds()) > 0:
#             print("waiting", wait_time)
#             time.sleep(wait_time + 1.3)
#         print("updating")
#         self.update_pledge()
    
