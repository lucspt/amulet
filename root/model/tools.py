import os
import pymongo
from numbers import Number
from functools import cached_property
from datetime import datetime, timedelta, timezone
from root.impacts.emissions import GHGCalculator
from typing import Callable
from bson import ObjectId

#let user choose their name
PROMPTS =  lambda name: {
    "vision": "The user will provide you with an image of either an item or activity taking place, without any context. Give your best description of the activity. For example if the item is a plastic water bottle, simply respond with plastic water bottle. If it is a plate of food, mention the main ingredients of the dish, e.g. beef or chicken. Keep your responses no longer than a few words.",
    "chat": f"You are a supportive partner helping a user named {name} to track and lower their carbon footprint and emissions. Given a query or request from the user, call the most appropriate function to complete your response. DO NOT assume what values to pass into functions, instead ask the user for more information. When you aren't certain you understand a request feel free to ask for clarification. Respond as concisely and naturally as possible, with basic wording, and in only one to two sentences. Your goal is to help the user live more environmentally friendly.",
    "audio": "The audio is about climate change, and contains words like emissions, carbon footprint, impact, pledges, sustainability, and carbon budget.",
    "mql": "You are an expert at translating natural language into efficient MongoDB queries to get the desired results from a database and its collections."
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate_emissions",
            "description": "Calculate the emissions of an activity or item, and optionally update the user's emissions status with the result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "activity": {
                        "type": "string",
                        "description": "A sequence of words describing the activity/item you want to calculation emissions for.",
                    },
                    "activity_value": {
                        "type": "number",
                        "description": "The amount of activity you would like to calculate emissions for. For example, if you would like to calculate emissions for 20 dollars worth of an item, the value would be 20.",
                    },
                    "activity_unit": {
                        "type": "string",
                        "enum": [
                            "money",
                            "kg",
                            "lb",
                            "g",
                            "ton",
                            "t",
                        ],
                        "description": "Specifies the metric that `activity_value` represents. If `activity_value` is a currency amount then pass money, if it is the weight of something pass the correct metric.",
                    },
                    "update_user_emissions": {
                        "type": "boolean",
                        "description": "If True, the function will update the user's emissions status with the result of the calculation. Defaults to False."
                    }
                },
                "required": ["activity", "activity_value", "activity_unit"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_emissions",
            "description": "Get the kilograms of CO2e that a user has emitted since a given time",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "enum": [
                            "current",
                            "historical",
                            "today",
                            "week",
                            "month",
                            "year",
                        ],
                        "description": "Passing `current` will return the user's current emissions with respect to their budget, `historical` will return the user's total emissions, and `today`, `month`, `year` and `week` all return a value for the respective period.",
                    },
                    # "time_range": {
                    #     "type": "object",
                    #     "description": "Use this INSTEAD OF `period` to specify a MORE SPECIFIC time frame to get emissions from. Pass an object mapping minutes, days, weeks, and years to their units. Example usage: {minutes: 0, days: 2, weeks: 1, years: 0} would return emissions for the past 1 week and 2 days.",
                    #     # "type": "string",
                    #     # "description": "A string specifying how many weeks, days, hours and or years ago to start finding emissions from, SEPERATED BY COMMAS. Example: `2 weeks, 2 days`".
                    # },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_user_view",
            "description": "Get a description of what the user is currently seeing. Useful when a user requests a calculation, but doesn't specify the activity.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "make_pledge",
            "description": "Call this when the user wants to make a pledge to refrain from an emitting activity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "activity": {
                        "type": "string",
                        "description": "The activity the user is pledging to refrain from."
                    },
                    "activity_unit": {
                        "type": "string",
                        "enum": [
                            "money",
                            "kg",
                            "lb",
                            "g",
                            "ton",
                            "t",
                        ],
                        "description": "Specifies what the metric of `activity` is. If the user is pledging to avoid spending money on the activity pass money, otherwise pass the correct weight metric. IT CAN ONLY BE `money` OR a valid weight metric"
                    },
                    "pledge_frequency": {
                        "type": "string",
                        "enum": ["day", "week", "month", "year"],
                        "description": "A string specifying whether the user is pledging to avoid `activity` daily, weekly, monthly or yearly. For example, if the user is pledging to buy 2 less shirts a week you would pass week"
                    },
                    "activity_value": {
                        "type": "number",
                        "description": "The amount of `activity` that the user is pledging to refrain from, each `pledge_frequency`. For example, if they pledge to buy 2 less shirts every day, the `activity_value` would be 2."
                    },
                    "pledge_name": {
                        "type": "string",
                        "description": "What the user chooses to name the pledge."
                    }

                },
                "required": [
                    "activity", "activity_unit", "pledge_frequency", "activity_value", "pledge_name"
                ]
            }
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_active_pledges",
            "description": "Get the active pledges that the user has made, and their impacts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pledge_names": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "An array listing the names of all the pledges you would like to get impacts of. Leave blank to include all pledges."
                    },
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_emitting_activities",
            "description": "Get the user's most-emitting activites. Useful for informing the user and suggesting pledges.",
            "parameters": {"type": "object", "properties": {}}
        },
    },
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "get_user_info",
    #         "description": "Get useful information about the user, such as the carbon budget they have set, and things you wrote down with `remember`.",
    #         "parameters": {"type": "object", "properties": {}},
    #     }   
    # }, don't think we need this here but it's implemented if we do.
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "remember",
    #         "description": "Write  down something the user tells you, so that you can later retreive it through the function `get_user_info`",
    #         "parameters": {"type": "object", "properties": {}}
    #     }
    # }
]

class ModelTools:
    __slots__ = (
        "savior_id",
        "ghg_calculator",
        "tools",
        "saviors",
        "emission_factors",
        "emission_logs",
        "pledges",
        "prompts",
        "get_embeddings",
        "tools_to_functions",
    )
    

    def __init__(self, savior_id: str, embeddings_generator: Callable):
        connection_string = os.environ.get("MONGO_URI")
        db = pymongo.MongoClient(connection_string).spt
        self.savior_id = savior_id
        self.emission_factors = db.emission_factors
        self.emission_logs = db.logs
        self.pledges = db.pledges
        self.saviors = db.saviors
        self.tools = TOOLS
        self.prompts = PROMPTS
        savior = self.savior
        self.ghg_calculator = GHGCalculator(
            region=savior["region"], currency=savior["currency"]
        )
        self.get_embeddings = embeddings_generator
        
    @property
    def valid_metrics(self):
        return ["kWh", "g", "kg", "lb", "t", "ton"]

    @property
    def helpers(self):
        self.tools_to_functions = {
            "get_user_emissions": self.get_user_emissions,
            "calculate_emissions": self.calculate_emissions,
            "make_pledge": self.make_pledge,
            "get_active_pledges": self.get_active_pledges,
            "get_emitting_activities": lambda: str(self.emitting_activities), 
            #string instead of object for the model
            "get_user_info": lambda: str(self.user_info)
        }

        return self.tools, self.tools_to_functions, self.prompts
    
    def make_response(self, value: Number) -> str:
        #TODO: HOW SHOULD WE GO ABOUT THIS AND MAKING SURE WE HAVE TO CORRECT UNIT ? 
        return f"{round(value, 2)} Kilograms CO2e"
    
    #Emissions
    @cached_property
    def emitting_activities(self) -> list | str:
        """The summed emissions of the user, grouped by activity"""
        pipeline_start = {
            "savior_id": self.savior_id, "activity": {"$nin": self.active_pledges}
        }
        pipeline_group = {
                    "$group": {
                        "_id": "$activity",
                        "activity": {"$first": "$activity"},
                        "Total Kilograms CO2e caused": {"$sum": "$co2e"},
                        "activity_unit_type": {"$first": "$activity_unit_type"},
                        # "last_emitted": {"$last": "$date"}
                    }
                }
        pipeline = [
            {"$match": pipeline_start},
            pipeline_group,
            # {"$match": {"emissions": {"$gt": 1}}},
            {"$unset": "_id"},
            {"$sort": {"emissions": -1}},
            {"$limit": 5}
        ]
        # if min_co2:
        #     pipeline.append({"$match": {"emissions": {"$gt": min_co2}}})
        contributers = list(self.emission_logs.aggregate(pipeline=pipeline))
        return contributers or "No emitting activites found"
    
    @property
    def savior(self):
        return self.saviors.find_one({"savior_id": self.savior_id})
    
    @property
    def user_info(self):
        savior = self.savior
        budget = savior["emissions_budget"]
        return {
            "emission_frequency": "day",
            "emissions_budget": self.make_response(budget)
        }

    def log_emissions(self, document: dict) -> tuple:
        """Logs a new emitting activity to the collection
        and returns new current emissions
        
        Args:
            document: A dictionary to log to the collection
        """
        previous_emissions = self.get_user_emissions("current", from_tool_call=False)
        co2e = document["co2e"]
        new_total = previous_emissions + co2e
        
        self.emission_logs.insert_one(
            {
                "savior_id": self.savior_id,
                "created": datetime.now(tz=timezone.utc), 
                **document
            }
        )
        return co2e, new_total
        

    def get_emission_factor(self, activity: str, activity_unit_type: str) -> dict:
        """Get an emission factor from the database given a sequency of words (query)
        and the unit type to search for. The emission factor is retreived through
        semantic search
        
        Args:
            activity: A query or sequence of descriptive words to match emission
            factors against while vector searching the database
            
            activity_unit_type: One of "money" or a weight metric signifying
            whether to search for a spend-based or activity-based emission factor
            
        Returns: A dictionary containing info needed to calculate emissions
        """
        query_embeddings = self.get_embeddings(text=activity)

        result = self.emission_factors.aggregate(
            [
                {
                    "$vectorSearch": {
                        "queryVector": query_embeddings,
                        "path": "INSERT PATH HERE",
                        "numCandidates": 20,
                        "index": "emissionFactorsSimilarity",
                        "limit": 1,
                        "filter": {"unit_types": activity_unit_type, "source": "partners"}
                    }
                },
            ]
        )
        return result
    
    # def aggregate_logs(self, match: dict) -> Number:
    #     """Helper to aggregate logs with a $match selection"""
    #     emissions = self.emission_logs.aggregate(
    #         [
    #             match,
    #             {
    #                 "$group": {
    #                     "_id": None,
    #                     "emissions": {"$sum": "$co2e"},
    #                 }
    #             },
    #         ]
    #     )
    #     emissions = emissions.next()["emissions"] if emissions.alive else 0
    #     return emissions
    
    def _calculate(
        self, activity: str, activity_value: Number, activity_unit: str
    ) -> dict:
        """Calls emission factor api and performs calculation after getting needed info
        
        Args:
            activity: the emission-causing item / activity
            activity_value: the amount of `activity` done, as a number
            activity_unit: the metric of `activity_value`
            
        Returns: A dictionary with info to log to the database or inform the model
        """
        if activity_unit == "money":
            activity_unit_type = "money"
            activity_unit = self.savior["currency"]
        elif activity_unit not in ["kWh", "g", "kg", "lb", "t", "ton"]:
            raise ValueError(
                "The unit for activity must be `money` or a valid weight metric"
            )
        else: 
            activity_unit_type = "weight"
            
        emission_factor = self.get_emission_factor(
            activity=activity, activity_unit_type=activity_unit_type
        )
        activity_id = emission_factor["activity_id"]
        emissions = self.ghg_calculator(
            value=activity_value,
            activity_id=activity_id,
            unit_type=activity_unit_type,
            unit=activity_unit,
        )
        return {
            **emissions, 
            "activity_unit_type": activity_unit_type,
            "activity_id": activity_id,
            "activity": emission_factor["activity"],
            "activity_unit": activity_unit,
            "activity_value": activity_value,
            "tool_call_query": activity
        }

    def calculate_emissions(
        self,
        activity: str,
        activity_value: Number,
        activity_unit: str,
        update_user_emissions: bool = False,
    ) -> str:
        """Calculation function for the model, with an option to update user emissions
        with the result
        
        Args: 
            same as `_calculate`
            update_user_emissions: Whether or not to upate the user's emission logs.
        
        Returns: a string for the model to respond to the user with
        """
        emissions = self._calculate(
            activity=activity, 
            activity_unit=activity_unit,
            activity_value=activity_value
        )
        emissions_budget = self.savior["emissions_budget"]
        if update_user_emissions:
            co2e, new_total = self.log_emissions(emissions)
            budget_left = self.make_response(emissions_budget - new_total)
            return (f"Emissions updated: {self.make_response(co2e)}. " 
                    # f"New current emissions: {self.make_response(new_total)}, "
                    f"CO2e Budget left: {budget_left}")
        else:
            co2e = emissions["co2e"]
            curr_emissions = self.get_user_emissions("current", from_tool_call=False)
            remaining_budget = self.make_response(
                emissions_budget - (co2e + curr_emissions)
            )
            return (f"Emissions calculated: {self.make_response(co2e)}. "
                    f"User's leftover budget if activity is taken: {remaining_budget}")

    def get_user_emissions(
        self,
        period: str | None = None,
        time_delta: dict | None = None,
        from_tool_call: bool = True,
    ) ->  str | dict:
        """Get emissions over a given range of time

        Args:
            period: a simple string specifying when to start totalling emissions from
            time_delta: same as period, but kwargs access to time delta for more complex time queries
        
        Returns: The user's total emissions since the specified time
        """

        if period:
            if period == "current": 
                tracking_freq = self.savior["emission_frequency"] 
                return self.get_user_emissions(
                    period=tracking_freq, from_tool_call=from_tool_call
                )
            elif period == "historical":
                date_start = datetime.min
            else:
                now = datetime.now(tz=timezone.utc)
                if period in ["today", "day"]:
                    date_start = datetime(
                        year=now.year, 
                        day=now.day, 
                        month=now.month, 
                        tzinfo=timezone.utc
                    )
                elif period == "week":
                    date_start = now - timedelta(days=now.weekday() % 7)
                    date_start -= timedelta(
                        hours=now.hour, minutes=now.minute, seconds=now.second
                    )
                elif period == "month":
                    date_start = datetime(
                        year=now.year, month=now.month, day=1, tzinfo=timezone.utc
                    )
                elif period == "year":
                    date_start = datetime(
                        year=now.year, month=1, day=1, tzinfo=timezone.utc
                    )
                else:
                    raise ValueError(
                        "That is NOT a valid function call, "
                        "ask the user what time period to search for emissions from"
                    )
        elif time_delta:
            # time_delta = {
            #     (time + "s" if not time.endswith("s") else time): float(val)
            #     for val, time in [
            #         x.split(" ") for x in time_delta.split(", ")
            #     ]
            # }
            date_start = datetime.now(tz=timezone.utc) - timedelta(**time_delta)
            
        emissions = self.emission_logs.aggregate(
            [
                {"$match": {"savior_id": self.savior_id, "date": {"$gt": date_start}}},
                {
                    "$group": {
                        "_id": None,
                        "emissions": {"$sum": "$co2e"},
                    }
                },
            ]
        )
        emissions = emissions.next()["emissions"] if emissions.alive else 0
        if from_tool_call:
            return self.make_response(emissions)
        else:
            return emissions
    
    #Pledges
    @property
    def active_pledges(self):
        return self.pledges.find({"savior_id": self.savior_id}).distinct("pledge_name")
    
    def make_pledge(
        self, 
        activity: str, 
        activity_unit: str,
        activity_value: Number,
        pledge_frequency: str,
        pledge_name: str,
    ) -> str:
        # {
        #     (time + "s" if not time.endswith("s") else time): float(time_length) 
        #     for time_length, time in [pledge_frequency.split(" ")] or [pledge_frequency.split(" every ")] 
        # }
        """Log and initiate a pledge for the user to refrain
        from an emitting activity
        
        Args:
            activity: The activity the user is pledging to refrain from
            activity_unit: The unit of `activity` e.g. money, kg, g
            pledge_frequency: How often the pledge will be honored;
            can be daily, weekly, monthly or yearly 
            activity_value: the amount of `activity` done
            pledge_name: A unique name for the pledge            
        """
        if pledge_name in self.active_pledges:
            raise ValueError(f"That pledge name is taken already. " 
                             "Kindly ask the user to specify another name")
        calculation = self._calculate(
            activity=activity, 
            activity_value=activity_value,
            activity_unit=activity_unit 
        )
        calculation.pop("activity_value")
        co2e_factor = calculation.pop("co2e")

        now = datetime.now(tz=timezone.utc)
        pledge = {
            "last_updated": now,
            "created": now,
            "impact": 0,
            "activity_unit_type": calculation["activity_unit_type"],
            "activity": calculation["activity"],
            "pledge_name": pledge_name.lower(),
            "co2e_factor": co2e_factor,
            "pledge_frequency": pledge_frequency,
            "pledge_streak": 1,
            "savior_id": self.savior_id,
            "tool_call_query": activity,
        }
        self.pledges.insert_one(pledge)
        impact = self.make_response(co2e_factor)
        return (f"Success. Pledge name: {pledge_name}, "
                f"Emissions avoided every {pledge_frequency}: {impact}")

    def get_active_pledges(self, pledge_names: list[str] = []) -> list:
        """Get the active pledges of the user along with their total impacts,
        grouped by name
        
        Args: 
            pledge_name: The pledge(s) to get the impact of. If none all pledges 
            will be returned
        """
        
        #TODO: maybe we should not identify them by pledge names 
        # but instead by activity, so you can just say how's my plastic pledge doing and query it by activity
        match = {"savior_id": self.savior_id}
        if pledge_names: 
            match["pledge_name"] = {
                "$in": [name.lower() for name in pledge_names]
            }
            # if not all(map(lambda x: x in self.active_pledges, pledge_names)):
                # raise ValueError(f"Recieved invalid pledge names.")
        
        pledge_impacts = list(self.pledges.aggregate(
            [
                {"$match": match},
                {
                    "$group": {
                        "_id": "$pledge_name",
                        "pledge_name": {"$first": "$pledge_name"},
                        "Total impact (Kilograms CO2e)": {"$sum": "$impact"},
                    },
                },
                {"$unset": "_id"}
            ]
        ))
        
        return str(pledge_impacts) or (f"No pledges with names {pledge_names} were found. " 
                                        "Try listing the user's active pledges to them")
        
    # def add_to_memory(self, to_remember: str) -> None:
    #     memory_notes = self.savior.get("memory_notes", [])
    #     memory_notes.append(to_remember)
    #     self.saviors.update_one(
    #         {
    #             "savior_id": self.savior_id,
    #             "$set": {"memory_notes": memory_notes}
    #         }
    #     )
        
    # @property
    # def memory(self):
    #     memory_notes = self.savior.get("memory_notes", [])
    #     return " ".join(memory_notes)