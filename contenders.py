# MQL 

import pymongo, json
MQL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "find",
            "description": "Find document(s) from a collection in the database",
            "parameters": {
                "type": "object",
                "properties": {
                    "collection_name": {
                        "type": "string",
                        "enum": ["pledges", "emissions"],
                        "description": "The name of the collection to query"
                    },
                    "filter": {
                        "type": "object",
                        "description": "A python dictionary specifying the query to be performed"
                    },
                    "many": {
                        "type": "boolean",
                        "description": "Whether or not to find many documents from the query. If false the result will be only the first match."
                    }
                }
            },
            "required": ["collection_name", "filter", "many"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update",
            "description": "Update document(s) from a collection in the database",
            "parameters": {
                "type": "object",
                "properties": {
                    "collection_name": {
                        "type": "string",
                        "enum": ["pledges", "emissions"],
                        "description": "The name of the DB collection"
                    },
                    "filter": {
                        "type": "object",
                        "description": "A dictionary specifying the query to be performed"
                    },
                    "update": {
                        "type": "object",
                        "description": "A dictionary containing the update to perform"
                    },
                    "many": {
                        "type": "boolean",
                        "description": "True means update many, False means update just one document"
                    }
                }
            },
            "required": ["collection_name", "filter", "update", "many"]
        }
    }
]
    
class MQLTools:
    __slots__ = (
        "prompt", "tools", "tools_to_functions", "collections", "savior_id"
    )
    
    def __init__(
        self, 
        savior_id: str,
        prompt: str,
    ) -> None:
        self.db = pymongo.MongoClient().edge
        # logs, pledges = db.logs, db.pledges
        self.prompt = prompt 
        self.tools = MQL_TOOLS
        self.savior_id = savior_id
        self.tools_to_functions = {"perform_query": self.perform_query}
        # self.collections = {"user_emissions": logs, "user_pledges": pledges}

    @property
    def helpers(self):
        return self.tools, self.tools_to_functions, self.prompt
    
    def prepare_op(self, collection_name: str, filter: dict) -> tuple:
        collection = self.db[collection_name]
        return collection, {"savior_id": self.savior_id, **filter}
        
    def find(self, collection_name: str, filter: dict, many: bool) -> str:
        collection, filter = self.prepare_op(collection_name, filter)
        if many:
            res = list(collection.find_many(filter=filter))
        else: 
            res = collection.find_one(filter=filter)
        return repr(res)
            
    def update(
        self, collection_name: str, filter: dict, update: dict, many: bool
    ) -> str:
        collection, filter = self.prepare_op(collection_name, filter)
        if many:
            res = collection.update_many(filter, update, upsert=False)
        else: 
            res = collection.update(filter, update, upsert=False)
        return f"Num Documents updated: {res.modified_count}"
    
    def delete(self, collection_name: str, filter: dict, many: bool) -> str:
        collection, filter = self.prepare_op(collection_name, filter)
        if many: 
            res = collection.delete_one(filter)
        else:
            res = collection.delete_many(filter)
        return f"Num Documents deleted: {res.deleted_count}"
    
    def aggregate(self, collection_name: str, aggregation: list) -> str:
        collection = self.db[collection_name]
        aggregation = [{"$match": {"savior_id": self.savior_id}}] + aggregation
        result = list(collection.aggregate(aggregation))
        return repr(result)
    
    #     {
    #     "type": "function",
    #     "function": {
    #         "name": "get_emissions_avoided",
    #         "description": "Get the total amount of emissions the user has avoided since a given time",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "period": {
    #                     "type": "string",
    #                     "enum": [
    #                         "current",
    #                         "historical",
    #                         "today",
    #                         "week",
    #                         "month",
    #                         "year",
    #                     ],
    #                     "description": "Passing `current` will return the user's current emissions avoided with respect to their budget, `historical` will return the user's total avoided emissions to date, and `today`, `month`, `year` and `week` all return a value for the respective period.",
    #                 },
    #                 "time_range": {
    #                     "type": "object",
    #                     "description": "Use this to specify a more specific time frame. ONLY USE WHEN `period` DOES NOT SUFFICE. Example usage: {minutes: 20, days: 2, weeks: 1, years: 0}.",
    #                 },
    #             },
    #         },
    #     },
    # },
    
    #     {
    #     "type": "function",
    #     "function": {
    #         "name": "update_user_emissions",
    #         "description": "Update the user's emissions with a given activity and it's corresponding value.",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "activity": {
    #                     "type": "string",
    #                     "description": "A sequence of words describing the activity/item to calculate emissions for when updating. E.g. buying fruit",
    #                 },
    #                 "activity_value": {
    #                     "type": "number",
    #                     "description": "The amount of activity done by the user. For example, if the user bought 10 dollars worth of fruit, you would pass 10",
    #                 },
    #                 "activity_unit": {
    #                     "type": "string",
    #                     "enum": [
    #                         "money",
    #                         "kg",
    #                         "lb",
    #                         "g",
    #                         "ton",
    #                         "t",
    #                     ],
    #                     "description": "Specifies what metric the value of `activity_value` represents. If `activity_value` is a currency amount then pass money, if it is the weight of something pass the correct metric.",
    #                 },
    #             },
    #             "required": ["activity", "activity_value", "activity_unit"],
    #         },
    #     },
    # },
    
    

from root.model.tools import MQLTools
from root.model.model import Model
class ModelWithMQL(Model):
    __slots__ = ("mql_prompt", "mql_tool", "client")
    def __init__(self):
        mql_tools = MQLTools()
        self.tools, self.tools_to_functions, self.prompt = mql_tools.helpers
        
        
    def call_tool(self, tool_call) -> list: 
        function_name = tool_call.function.name
        function_call = self.tools_to_functions[function_name]
        arguments = json.loads(tool_call.function.arguments)
        function_response = function_call(**arguments)
        return function_response
        
    def get_mql_completion(self, mql_query: str) -> list:
        """Another model solely for turning natural language into mongodb queries
        we just only give it tool calls for mongodb operations
        """
        messages = self.format_inputs(content=mql_query, prompt=self.prompt)
        response = self.get_chat_completion(messages=messages, tools=self.tools)
        tool_call = response.choices[0].message.tool_calls
        
        result = self.call_tool(tool_calls=tool_call)
        return repr(result)
        
        

