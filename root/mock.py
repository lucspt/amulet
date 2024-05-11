from numbers import Number
from root.model.tools import ModelTools
from root.model.model import Model
from openai import OpenAI
from config import Config
from datetime import datetime
from typing import Callable
# from root.device.audio import AudioTools
import numpy as np

TOOLS = [
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "calculate_emissions",
    #         "description": "Calculate the emissions of an activity or item, and optionally update the user's emissions status with the result.",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "activity": {
    #                     "type": "string",
    #                     "description": "A sequence of words describing the activity/item you want to calculation emissions for.",
    #                 },
    #                 "activity_value": {
    #                     "type": "number",
    #                     "description": "The amount of activity you would like to calculate emissions for. For example, if you would like to calculate emissions for 20 dollars worth of an item, the value would be 20.",
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
    #                     "description": "Specifies the metric that `activity_value` represents. If `activity_value` is a currency amount then pass money, if it is the weight of something pass the correct metric.",
    #                 },
    #                 "update_user_emissions": {
    #                     "type": "boolean",
    #                     "description": "If True, the function will update the user's emissions status with the result of the calculation. Defaults to False."
    #                 }
    #             },
    #             "required": ["activity", "activity_value", "activity_unit"],
    #         },
    #     },
    # }, 
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "get_user_emissions",
    #         "description": "Get the amount of emissions a user has emitted since a given time",
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
    #                     "description": "Passing `current` will return the user's current emissions with respect to their budget, `historical` will return the user's total emissions to date, and `today`, `month`, `year` and `week` all return a value for the respective period.",
    #                 },
    #                 "time_range": {
    #                     "type": "object",
    #                     "description": "Example usage: {minutes: 0, days: 2, weeks: 1, years: 0} would return emissions for the past 1 week and 2 days. Use this to specify a more specific time frame, when `period` can't. Do NOT use both this and `period`",
    #                 },
    #             },
    #         },
    #     },
    # },
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
                        "description": "The activity the user is pledging to refrain from"
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
                        "enum": ["day", "week", "year"],
                        "description": "A string specifying whether the user is pledging to avoid `activity` daily, weekly or yearly. For example, if the user is pledging to buy two less shirts a week you would pass week"
                    },
                    "activity_value": {
                        "type": "number",
                        "description": "The amount of `activity` that the user is pledging to refrain from each `pledge_frequency`. For example, if they pledge to buy two less shirts every day, the `activity_value` would be 2."
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
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "get_pledge_impacts",
    #         "description": "Get the impact of one or all pledges that the user has made",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "pledge_name": {
    #                     "type": "string",
    #                     "description": "The name of the pledge you would like to calculate the impact of. This must be exact. Leave blank to include all pledges."
    #                 },
    #             }
    #         }
    #     }
    # },
]

PROMPTS = {
    "chat": "You are a supportive partner helping a user to lower their carbon footprint and emissions. Combine your knowledge and the tools you have to answer the user's requests. Whenever you don't understand a request, before continuing, ask the user for more information. Respond in one to two sentences, with simple vocabulary, and as concisely and naturally as possible.",
    # "chat": "You are a supportive partner helping a user to track and lower their carbon footprint and emissions. Given a query or request from the user call the most appropriate function to complete your response. DO NOT assume what values to pass into functions, instead either ask the user for more information. When you aren't certain you understand the user's request, you can ask them to validate your interpretation. Keep your responses as short as possible. Your goal is to help the user live more environmentally friendly.",
    # "chat": "You are a supportive partner helping a user to track and lower their carbon footprint and emissions. Given a query or request from the user call the most appropriate function to complete your response. Whenever you don't understand a request ask the user for more information. Respond as concisely and naturally as possible, with basic wording, and in only one to two sentences. Your goal is to help the user live more environmentally friendly.",
    "audio": 'The audio will likely be about climate change, containing words like "emissions", "carbon footprint", "impact" and "pledges"',
}

class TempModelTools(ModelTools):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompts = PROMPTS
        self.tools = TOOLS
            

    def cosine_similarity(self, x, y):
        norm_x = np.linalg.norm(x)
        norm_y = np.linalg.norm(y)
        return np.dot(x, y) / norm_x * norm_y
    

    def get_emission_factor(self, activity: str, activity_unit_type: str) -> dict:
        """Performs a vector search on a database containing
        the info needed to call emission factor api"""

        query_embeddings = self.get_embeddings(text=activity)
        similarities = []
        for factor in self.db.emission_factors.find({"unit_types": activity_unit_type}):
            factor["similarity"] = self.cosine_similarity(
                factor["embeddings"], query_embeddings
            )
            similarities.append(factor)
        return max(similarities, key=lambda x: x["similarity"])
    
    # def _calculate(self, *args, **kwargs) -> dict:
    #     import random 
    #     return {
    #         **kwargs,
    #         "co2e": random.randint(0, 100),
    #         "activity_id": "test_activity_id",
    #         "co2e_unit": "kg",
    #         "tool_call_query": "testing"
    #     }
        

    

class TempModel(Model):
    def __init__(self, savior_id: str, amulet_tools: dict[str, Callable]):
        self.client = OpenAI()
        model_tools = TempModelTools(
            embeddings_generator=np.random.randn(1536), savior_id=savior_id
        )
        helpers = model_tools.helpers
        self.tools, tools_to_functions, self.prompts = helpers
        self.tools_to_functions = {**tools_to_functions, **amulet_tools}
        self.tts_voice = model_tools.savior["tts_voice"]
        config = Config() #do we even need this config class?
        self.chat_temperate = config.chat_temperature
        self.vision_temperature = config.vision_temperature
        self.max_vision_tokens = config.max_vision_tokens
        self.audio_input_file = config.audio_input_file
        self.audio_output_file = config.audio_output_file
        self._current_thread = {"last_interaction": datetime.now(), "thread": []}
        
    def moderate(self, text: str) -> bool:
        return False


# class TempAudioTools(AudioTools):

#     def record_query(self, duration) -> str:
#         """Records and writes audio to an output file"""

#         channels, sample_rate = (
#             self.channels,
#             self.sample_rate,
#         )
#         format, p, chunk = self.format, self.p, self.record_chunk
#         stream = p.open(
#             format=self.format,
#             channels=self.channels,
#             rate=sample_rate,
#             frames_per_buffer=self.record_chunk,
#             input=True,
#         )

#         audio = []
#         count = 0
#         while count < duration:
#             for _ in range(0, int(sample_rate / chunk)):
#                 data = stream.read(2)
#                 audio.append(data)
#             count += 1
#         stream.stop_stream()
#         stream.close()
#         p.terminate()
#         output_file = self.write_audio(
#             audio=audio,
#             channels=channels,
#             sample_rate=sample_rate,
#             sample_width=p.get_sample_size(format),
#         )
#         return output_file


#    {
#         "type": "function",
#         "function": {
#             "name": "calculate_emissions",
#             "description": "Calculate the emissions of an activity or item.",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "activity": {
#                         "type": "string",
#                         "description": "A sequence of words describing the activity/item you want to retrieve an emission factor for.",
#                     },
#                     "activity_value": {
#                         "type": "number",
#                         "description": "The amount of activity you would like to calculate emissions for. For example, if you would like to calculate emissions for 20 dollars worth of an item, the value would be 20.",
#                     },
#                     "activity_unit": {
#                         "type": "string",
#                         "enum": [
#                             "money",
#                             "kg",
#                             "lb",
#                             "g",
#                             "ton",
#                             "t",
#                         ],
#                         "description": "Specifies the metric that the value of `activity_value` represents. If `activity_value` is a currency amount then pass money, if it is the weight of something pass the correct metric.",
#                     },
#                 },
#                 "required": ["activity", "activity_value", "activity_unit"],
#             },
#         },
#     },
#     {
#         "type": "function",
#         "function": {
#             "name": "update_user_emissions",
#             "description": "Update the user's emissions with a given activity and it's corresponding value.",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "activity": {
#                         "type": "string",
#                         "description": "A sequence of words describing the activity/item to calculate emissions for when updating. E.g. buying fruit",
#                     },
#                     "activity_value": {
#                         "type": "number",
#                         "description": "The amount of activity done by the user. For example, if the user bought 10 dollars worth of fruit, you would pass 10",
#                     },
#                     "activity_unit": {
#                         "type": "string",
#                         "enum": [
#                             "money",
#                             "kg",
#                             "lb",
#                             "g",
#                             "ton",
#                             "t",
#                         ],
#                         "description": "Specifies what metric the value of `activity_value` represents. If `activity_value` is a currency amount then pass money, if it is the weight of something pass the correct metric.",
#                     },
#                 },
#                 "required": ["activity", "activity_value", "activity_unit"],
#             },
#         },
#     },